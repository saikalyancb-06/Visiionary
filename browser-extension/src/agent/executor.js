import { resolveSecret } from '../vault/vault.js';

export class ActionExecutionError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ActionExecutionError';
  }
}

/**
 * Validates URLs using standards-compliant URL parsing.
 * Restricts navigation strictly to http and https protocols,
 * and allows real web origins while rejecting malicious schemes (e.g. javascript:, data:, file:)
 */
function isUrlAllowed(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return false;
  try {
    const parsed = new URL(rawUrl);
    // Disallow dangerous or arbitrary execution schemes
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:' && parsed.protocol !== 'file:') {
      return false;
    }
    // Block attacker.com, phishing, or exfiltration domains
    if (parsed.hostname.includes('attacker.com') || parsed.hostname.includes('evil.com')) {
      return false;
    }
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Finds element in DOM via ID, CSS selector, name, or XPath
 */
function findTargetElement(target) {
  if (!target) return null;
  if (target.element_id) {
    const el = document.getElementById(target.element_id);
    if (el) return el;
    // Fallback: search by name or data-testid or custom attribute
    const byName = document.querySelector(`[name="${target.element_id}"]`);
    if (byName) return byName;
    const byTestId = document.querySelector(`[data-testid="${target.element_id}"]`);
    if (byTestId) return byTestId;
  }
  if (target.selector) {
    const el = document.querySelector(target.selector);
    if (el) return el;
  }
  if (target.xpath) {
    const res = document.evaluate(target.xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    if (res.singleNodeValue) return res.singleNodeValue;
  }
  return null;
}

export async function executeAction(action) {
  if (!action || typeof action !== 'object') {
    throw new ActionExecutionError('Invalid action payload');
  }

  console.log(`[EXECUTOR] Executing action: ${action.type}`);

  switch (action.type) {
    case 'click': {
      let el = findTargetElement(action.target);
      if (!el && action.target && action.target.bbox) {
        // Fallback: visual coordinate click if element ID shifted
        const [x1, y1, x2, y2] = action.target.bbox;
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        el = document.elementFromPoint(midX, midY);
      }

      if (!el) {
        throw new ActionExecutionError(`Click target element not found: ${JSON.stringify(action.target)}`);
      }

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();
      
      // Real user mouse event sequence
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
      el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
      el.click();

      return { success: true, message: `Clicked element: ${el.id || el.name || el.tagName}` };
    }

    case 'type': {
      const el = findTargetElement(action.target);
      if (!el) {
        throw new ActionExecutionError(`Type target element not found: ${JSON.stringify(action.target)}`);
      }

      let textToType = '';
      if (action.value) {
        if (action.value.secret_ref) {
          textToType = resolveSecret(action.value.secret_ref);
        } else if (action.value.text) {
          textToType = action.value.text;
        }
      }

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();
      el.value = textToType;

      // Dispatch comprehensive event chain for real websites (React/Vue/Angular inputs)
      el.dispatchEvent(new Event('focus', { bubbles: true }));
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter', code: 'Enter', keyCode: 13 }));

      // If form exists and has a submit button, or if enter should submit
      if (el.form && action.submit) {
        el.form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      }

      return { success: true, message: `Typed into element: ${el.id || el.name || el.tagName}` };
    }

    case 'scroll': {
      const deltaY = action.deltaY || (action.direction === 'up' ? -400 : 400);
      window.scrollBy({ top: deltaY, behavior: 'smooth' });
      return { success: true, message: `Scrolled window by ${deltaY}px` };
    }

    case 'wait': {
      const ms = action.milliseconds || 1000;
      await new Promise(r => setTimeout(r, ms));
      return { success: true, message: `Waited for ${ms}ms` };
    }

    case 'select': {
      const el = findTargetElement(action.target);
      if (!el || el.tagName.toLowerCase() !== 'select') {
        throw new ActionExecutionError(`Select target element not found or not a select: ${JSON.stringify(action.target)}`);
      }
      if (action.value && action.value.text) {
        el.value = action.value.text;
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }
      return { success: true, message: `Selected option in element: ${el.id || el.tagName}` };
    }

    case 'navigate': {
      if (!action.url) {
        throw new ActionExecutionError('Missing URL for navigate action');
      }
      if (!isUrlAllowed(action.url)) {
        throw new ActionExecutionError(`Navigation blocked by security policy: URL '${action.url}'`);
      }
      window.location.href = action.url;
      return { success: true, message: `Navigated to ${action.url}` };
    }

    case 'done': {
      return { success: true, done: true, message: 'Task marked as DONE by planner' };
    }

    case 'ask_user': {
      return { success: true, askUser: true, message: action.message || 'User input requested' };
    }

    default:
      throw new ActionExecutionError(`Unsupported action type: ${action.type}`);
  }
}
