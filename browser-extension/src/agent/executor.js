import { resolveSecret } from '../vault/vault.js';

export class ActionExecutionError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ActionExecutionError';
  }
}

// Restrict navigation strictly to allowed local demo origins or safe internal schemes
const ALLOWED_DEMO_ORIGINS = [
  'http://127.0.0.1',
  'http://localhost',
  'file://'
];

function isUrlAllowed(url) {
  if (!url || typeof url !== 'string') return false;
  return ALLOWED_DEMO_ORIGINS.some(allowed => url.startsWith(allowed));
}

function findTargetElement(target) {
  if (!target) return null;
  if (target.element_id) {
    const el = document.getElementById(target.element_id);
    if (el) return el;
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
      const el = findTargetElement(action.target);
      if (!el) {
        throw new ActionExecutionError(`Click target element not found: ${JSON.stringify(action.target)}`);
      }
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();
      
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
      el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
      el.click();
      return { success: true, message: `Clicked element: ${el.id || el.tagName}` };
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

      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return { success: true, message: `Typed into element: ${el.id || el.tagName}` };
    }

    case 'scroll': {
      const deltaY = action.deltaY || 300;
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
        throw new ActionExecutionError(`Navigation blocked: URL '${action.url}' outside allowed demo origins`);
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
