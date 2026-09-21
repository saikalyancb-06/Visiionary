/**
 * Master Content Script with Real DOM Perception, Universal Privacy Shield & Action Execution
 * Self-contained for Chrome MV3 content script environment (no static ES module import errors in page context).
 */

// --- SECTION 1: PII REGEX & DOM PRIVACY DETECTOR ---
const PII_PATTERNS = {
  EMAIL: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
  PHONE: /\b(?:\+91[\-\s]?)?[6789]\d{4}[\-\s]?\d{5}\b/g,
  CARD_NUMBER: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
  PAN: /\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b/g,
  AADHAAR: /\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b/g,
  BANK_ACCOUNT: /\b(?:A\/C|Account|Acc)[\s:#-]*\d{9,18}\b/gi,
  UPI: /[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}/g,
  IFSC: /\b[A-Z]{4}0[A-Z0-9]{6}\b/g,
  PIN_CODE: /\b[1-9][0-9]{2}\s?[0-9]{3}\b/g
};

function luhnCheck(numStr) {
  const clean = numStr.replace(/\D/g, "");
  if (clean.length < 13 || clean.length > 19) return false;
  let sum = 0;
  let alt = false;
  for (let i = clean.length - 1; i >= 0; i--) {
    let digit = parseInt(clean.charAt(i), 10);
    if (alt) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    alt = !alt;
  }
  return sum % 10 === 0;
}

const VERHOEFF_D = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
  [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
  [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
  [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
  [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
  [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
];

const VERHOEFF_P = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
  [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
  [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
  [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
  [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
];

function verhoeffCheck(numStr) {
  const clean = numStr.replace(/\D/g, "");
  if (clean.length !== 12) return false;
  let c = 0;
  const reversed = clean.split("").reverse();
  for (let i = 0; i < reversed.length; i++) {
    const digit = parseInt(reversed[i], 10);
    c = VERHOEFF_D[c][VERHOEFF_P[i % 8][digit]];
  }
  return c === 0;
}

function sanitizeTextForPII(text) {
  if (!text || typeof text !== 'string') return text;
  let sanitized = text;
  sanitized = sanitized.replace(PII_PATTERNS.EMAIL, '[REDACTED_EMAIL]');
  sanitized = sanitized.replace(PII_PATTERNS.UPI, (m) => m.includes('REDACTED') ? m : '[REDACTED_UPI]');
  sanitized = sanitized.replace(PII_PATTERNS.PAN, '[REDACTED_PAN]');
  sanitized = sanitized.replace(PII_PATTERNS.IFSC, '[REDACTED_IFSC]');
  sanitized = sanitized.replace(PII_PATTERNS.CARD_NUMBER, (m) => luhnCheck(m) ? '[REDACTED_CARD]' : m);
  sanitized = sanitized.replace(PII_PATTERNS.AADHAAR, (m) => verhoeffCheck(m) ? '[REDACTED_AADHAAR]' : m);
  sanitized = sanitized.replace(PII_PATTERNS.PHONE, '[REDACTED_PHONE]');
  return sanitized;
}

function detectSensitiveDOM(documentObj) {
  const sensitiveRegions = [];
  const sensitiveSelectors = [
    'input[type="password"]',
    'input[autocomplete*="password"]',
    'input[autocomplete*="cc-"]',
    'input[autocomplete*="one-time-code"]',
    'input[name*="pass"]',
    'input[name*="otp"]',
    'input[name*="card"]',
    'input[name*="cvv"]',
    '[data-pii]',
    'input[id*="account"]',
    'input[id*="balance"]',
    'input[id*="pan"]',
    'input[id*="aadhaar"]',
    '[class*="sensitive"]'
  ];

  const seenElements = new Set();
  sensitiveSelectors.forEach(sel => {
    documentObj.querySelectorAll(sel).forEach(el => {
      if (seenElements.has(el)) return;
      seenElements.add(el);

      const rect = el.getBoundingClientRect();
      const piiType = el.getAttribute('data-pii') || 
                      (el.type === 'password' ? 'password' : 
                      (el.id && el.id.includes('balance')) ? 'balance' : 'unknown_sensitive');

      sensitiveRegions.push({
        id: `dom_${Math.random().toString(36).substring(2, 7)}`,
        type: piiType,
        text: `[REDACTED_${piiType.toUpperCase()}]`,
        bbox: [
          Math.max(0, Math.round(rect.left)),
          Math.max(0, Math.round(rect.top)),
          Math.round(rect.right),
          Math.round(rect.bottom)
        ],
        source: 'dom_rules'
      });
    });
  });

  return sensitiveRegions;
}

// --- SECTION 2: DOM PERCEPTION EXTRACTOR ---
function extractDOMContext(documentObj) {
  const elements = [];
  const redactions = [];
  const sensitiveDOM = detectSensitiveDOM(documentObj);

  sensitiveDOM.forEach(r => {
    redactions.push({
      id: r.id,
      type: r.type,
      placeholder: `[REDACTED_${r.type.toUpperCase()}]`,
      bbox: r.bbox
    });
  });

  const interactiveSelectors = 'button, input, select, textarea, a[href], [role="button"], [role="link"], [role="searchbox"], [role="combobox"], [onclick], [tabindex="0"]';
  const nodes = documentObj.querySelectorAll(interactiveSelectors);
  const seen = new Set();

  nodes.forEach((el, idx) => {
    if (seen.has(el)) return;
    seen.add(el);

    const rect = el.getBoundingClientRect();
    if (rect.width <= 2 || rect.height <= 2) return;
    const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
    if (style && (style.visibility === 'hidden' || style.display === 'none' || parseFloat(style.opacity) === 0)) {
      return;
    }

    const isSensitive = el.type === 'password' || 
                        el.hasAttribute('data-pii') || 
                        (el.id && (el.id.includes('pass') || el.id.includes('otp') || el.id.includes('cvv')));

    let rawLabel = el.innerText || 
                   el.value || 
                   el.placeholder || 
                   el.getAttribute('aria-label') || 
                   el.getAttribute('title') || 
                   el.name || 
                   el.id || 
                   `element_${idx}`;

    rawLabel = rawLabel.replace(/\s+/g, ' ').trim();
    if (isSensitive) {
      rawLabel = `[REDACTED_${(el.getAttribute('data-pii') || el.type || 'SENSITIVE').toUpperCase()}]`;
    } else {
      // Clean genuine PII out of visible labels generically
      rawLabel = sanitizeTextForPII(rawLabel);
    }

    let elementId = el.id;
    if (!elementId) {
      elementId = el.name ? `name_${el.name}` : `visi_el_${idx}`;
      if (el.setAttribute) {
        el.setAttribute('id', elementId);
      }
    }

    elements.push({
      id: elementId,
      role: el.tagName.toLowerCase(),
      label: rawLabel,
      bbox: [
        Math.max(0, Math.round(rect.left)),
        Math.max(0, Math.round(rect.top)),
        Math.round(rect.right),
        Math.round(rect.bottom)
      ],
      interactable: true,
      sensitivity: isSensitive ? 'redacted' : 'safe',
      source: 'dom+vision',
      confidence: 1.0
    });
  });

  return { elements, redactions, sensitiveDOM };
}

// --- SECTION 3: REAL ACTION EXECUTOR ---
function findTargetElement(target) {
  if (!target) return null;
  if (target.element_id) {
    const el = document.getElementById(target.element_id);
    if (el) return el;
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

const DEFAULT_DEMO_SECRETS = {
  "bank.password": "SuperSecretBankPass2026!",
  "login.password": "SecureEnterprisePassword#99",
  "gov.otp": "849201",
  "gov.aadhaar": "5481 9201 3847",
  "shop.card_cvv": "782"
};

function resolveSecretLocally(secretRef) {
  return DEFAULT_DEMO_SECRETS[secretRef] || '';
}

async function executeAction(action) {
  if (!action || typeof action !== 'object') {
    throw new Error('Invalid action payload');
  }

  console.log(`[CONTENT EXECUTOR] Executing action: ${action.type}`);

  switch (action.type) {
    case 'click': {
      let el = findTargetElement(action.target);
      if (!el && action.target && action.target.bbox) {
        const [x1, y1, x2, y2] = action.target.bbox;
        el = document.elementFromPoint((x1 + x2) / 2, (y1 + y2) / 2);
      }
      if (!el) {
        throw new Error(`Click target element not found: ${JSON.stringify(action.target)}`);
      }

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
      el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
      el.click();
      return { success: true, message: `Clicked element: ${el.id || el.tagName}` };
    }

    case 'type': {
      const el = findTargetElement(action.target);
      if (!el) {
        throw new Error(`Type target element not found: ${JSON.stringify(action.target)}`);
      }

      let textToType = '';
      if (action.value) {
        if (action.value.secret_ref) {
          textToType = resolveSecretLocally(action.value.secret_ref);
        } else if (action.value.text) {
          textToType = action.value.text;
        }
      }

      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();

      // Support React 16+ / Vue input value tracker
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        'value'
      )?.set;
      const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        'value'
      )?.set;

      if (el.tagName === 'INPUT' && nativeInputValueSetter) {
        nativeInputValueSetter.call(el, textToType);
      } else if (el.tagName === 'TEXTAREA' && nativeTextAreaValueSetter) {
        nativeTextAreaValueSetter.call(el, textToType);
      } else {
        el.value = textToType;
      }

      el.dispatchEvent(new Event('focus', { bubbles: true }));
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }));
      el.dispatchEvent(new KeyboardEvent('keypress', { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }));
      el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13, which: 13 }));

      // If inside a form and enter key is pressed, submit form if not already submitted
      if (el.form && typeof el.form.requestSubmit === 'function') {
        try {
          el.form.requestSubmit();
        } catch (_) {}
      }

      return { success: true, message: `Typed into element: ${el.id || el.tagName}` };
    }

    case 'scroll': {
      const deltaY = action.milliseconds || action.deltaY || 400;
      window.scrollBy({ top: deltaY, behavior: 'smooth' });
      return { success: true, message: `Scrolled window by ${deltaY}px` };
    }

    case 'wait': {
      const ms = action.milliseconds || 1000;
      await new Promise(r => setTimeout(r, ms));
      return { success: true, message: `Waited for ${ms}ms` };
    }

    case 'done': {
      return { success: true, done: true, message: 'Task marked as DONE' };
    }

    case 'ask_user': {
      return { success: true, askUser: true, message: action.url || 'User confirmation requested' };
    }

    default:
      throw new Error(`Unsupported action type: ${action.type}`);
  }
}

// --- SECTION 4: BACKGROUND MESSAGE LISTENER ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'PING') {
    sendResponse({ success: true, pong: true });
    return true;
  }

  if (request.type === 'GET_DOM_SNAPSHOT') {
    try {
      const snapshot = extractDOMContext(document);
      sendResponse({
        success: true,
        url: window.location.href,
        title: document.title,
        elements: snapshot.elements,
        redactions: snapshot.redactions,
        sensitiveRegions: snapshot.sensitiveDOM
      });
    } catch (err) {
      console.error('[CONTENT SCRIPT] Snapshot error:', err);
      sendResponse({ success: false, error: err.message });
    }
    return true;
  }

  if (request.type === 'EXECUTE_ACTION') {
    (async () => {
      try {
        const result = await executeAction(request.action);
        sendResponse({ success: true, result });
      } catch (err) {
        console.error('[CONTENT SCRIPT] Action error:', err);
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }
});

console.log('[PS26171] Privacy Agent Content Script initialized successfully on:', window.location.href);
