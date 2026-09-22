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
  sanitized = sanitized.replace(PII_PATTERNS.BANK_ACCOUNT, '[REDACTED_BANK_ACCOUNT]');
  sanitized = sanitized.replace(PII_PATTERNS.PIN_CODE, '[REDACTED_PIN_CODE]');
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
    '[class*="sensitive"]',
    // PS26171 requirement: "blurring faces" - detect user profile faces and avatars in DOM
    'img[alt*="avatar" i]',
    'img[alt*="profile" i]',
    'img[class*="avatar" i]',
    'img[class*="profile" i]',
    'img[id*="avatar" i]',
    'img[id*="profile" i]',
    '[aria-label*="profile photo" i]',
    '[aria-label*="user avatar" i]'
  ];

  const seenElements = new Set();
  sensitiveSelectors.forEach(sel => {
    documentObj.querySelectorAll(sel).forEach(el => {
      if (seenElements.has(el)) return;
      seenElements.add(el);

      const rect = el.getBoundingClientRect();
      if (rect.width < 10 || rect.height < 10) return;

      let piiType = el.getAttribute('data-pii');
      if (!piiType) {
        if (el.type === 'password') {
          piiType = 'password';
        } else if (el.id && el.id.includes('balance')) {
          piiType = 'balance';
        } else if (el.tagName === 'IMG' || el.getAttribute('class')?.includes('avatar') || el.getAttribute('alt')?.includes('avatar') || el.getAttribute('alt')?.includes('profile')) {
          piiType = 'face';
        } else {
          piiType = 'unknown_sensitive';
        }
      }

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

// ---------------------------------------------------------------------------
// SECTION 1b: ON-PAGE PRIVACY OVERLAY RENDERER
//
// Draws a visible red "🔒 ___ HIDDEN" box over EVERY piece of content the
// extension hides — whether it's in an input field, a paragraph, a link,
// a product description, a table cell, or anywhere else on the page.
//
// Two scanning passes run on each GET_DOM_SNAPSHOT:
//
//   Pass 1 — Sensitive DOM inputs
//     Password fields, OTP inputs, CVV fields, etc. detected by CSS selectors.
//     The entire input element is boxed.
//
//   Pass 2 — PII in page text (any text node, anywhere)
//     A TreeWalker visits every visible text node in document.body.
//     Each text node is checked against all PII_PATTERNS.
//     For every regex match, the Range API returns pixel-accurate coordinates
//     for EXACTLY those characters — so the box covers only the hidden text,
//     not the whole element.
//
// Implementation notes:
// - Shadow DOM host: page CSS cannot override or hide these boxes.
// - position:fixed: correct alignment even with CSS transforms and sticky headers.
// - pointer-events:none: boxes don't block user clicks.
// - Cleared + redrawn on every snapshot; cleared on pagehide (navigation).
// ---------------------------------------------------------------------------

const OVERLAY_HOST_ID = 'visiionary-overlay-root';

/** Human-readable label for each PII type shown inside the box */
function friendlyLabel(type) {
  const map = {
    password:          'PASSWORD',
    email:             'EMAIL',
    phone:             'PHONE NUMBER',
    card:              'CARD NUMBER',
    card_number:       'CARD NUMBER',
    pan:               'PAN CARD',
    aadhaar:           'AADHAAR',
    bank_account:      'BANK ACCOUNT',
    upi:               'UPI ID',
    ifsc:              'IFSC CODE',
    otp:               'OTP',
    cvv:               'CVV',
    balance:           'ACCOUNT BALANCE',
    face:              'FACE / AVATAR',
    unknown_sensitive: 'SENSITIVE DATA',
    sensitive:         'SENSITIVE DATA',
  };
  const key = (type || '').toLowerCase().replace(/[^a-z_]/g, '');
  return map[key] || (type || 'DATA').toUpperCase().replace(/_/g, ' ');
}

/** Get or create the shadow-DOM host so our boxes are isolated from page CSS. */
function getOverlayShadowRoot() {
  let host = document.getElementById(OVERLAY_HOST_ID);
  if (!host) {
    host = document.createElement('div');
    host.id = OVERLAY_HOST_ID;
    host.style.cssText = 'position:fixed;top:0;left:0;width:0;height:0;z-index:2147483647;pointer-events:none;';
    document.documentElement.appendChild(host);
  }
  if (!host.shadowRoot) {
    host.attachShadow({ mode: 'open' });
    const style = document.createElement('style');
    style.textContent = `
      .visi-box {
        position: fixed;
        box-sizing: border-box;
        background: rgba(170, 0, 0, 0.88);
        border: 2px solid #ff3333;
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        pointer-events: none;
        z-index: 2147483647;
      }
      .visi-label {
        color: #fff;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-align: center;
        padding: 1px 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-shadow: 0 1px 2px rgba(0,0,0,0.7);
        user-select: none;
      }
    `;
    host.shadowRoot.appendChild(style);
  }
  return host.shadowRoot;
}

/** Place one red box at rect covering the hidden content. */
function _placeBox(shadow, rect, type) {
  if (!rect || rect.width < 1 || rect.height < 1) return;
  if (rect.bottom < 0 || rect.top > window.innerHeight) return; // off-screen

  const box = document.createElement('div');
  box.className = 'visi-box';
  box.style.left   = `${Math.max(0, rect.left)}px`;
  box.style.top    = `${Math.max(0, rect.top)}px`;
  box.style.width  = `${rect.width}px`;
  box.style.height = `${Math.max(rect.height, 16)}px`; // min 16px so label is readable

  const lbl = document.createElement('span');
  lbl.className = 'visi-label';
  lbl.textContent = `🔒 ${friendlyLabel(type)} HIDDEN`;

  box.appendChild(lbl);
  shadow.appendChild(box);
}

/**
 * Pass 2 — Walk EVERY text node in document.body and box PII matches
 * at exact character-level precision using the Range API.
 *
 * Skips: <script>, <style>, <noscript>, <template>, our own overlay host,
 *        hidden elements (display:none / visibility:hidden / opacity:0).
 */
function _boxAllPIITextNodes(shadow) {
  if (!document.body) return;

  // Tags whose text should never be scanned
  const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'MATH']);

  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const p = node.parentElement;
        if (!p) return NodeFilter.FILTER_REJECT;
        if (SKIP_TAGS.has(p.tagName)) return NodeFilter.FILTER_REJECT;
        if (p.id === OVERLAY_HOST_ID) return NodeFilter.FILTER_REJECT;
        // Skip invisible elements
        const cs = window.getComputedStyle(p);
        if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );

  // For each PII pattern, which extra validation function to apply (if any)
  const VALIDATORS = {
    CARD_NUMBER: (m) => luhnCheck(m),
    AADHAAR:     (m) => verhoeffCheck(m),
  };

  let textNode;
  while ((textNode = walker.nextNode())) {
    const text = textNode.textContent;
    if (!text || text.trim().length < 4) continue;

    for (const [patternName, pattern] of Object.entries(PII_PATTERNS)) {
      // Clone the pattern so we don't mess up lastIndex state across calls
      const re = new RegExp(pattern.source, pattern.flags);
      let match;

      while ((match = re.exec(text)) !== null) {
        // Apply algorithmic validators where needed
        const validator = VALIDATORS[patternName];
        if (validator && !validator(match[0])) continue;

        // Get pixel coordinates of this exact substring using Range
        try {
          const range = document.createRange();
          range.setStart(textNode, match.index);
          range.setEnd(textNode, match.index + match[0].length);
          const rect = range.getBoundingClientRect();
          _placeBox(shadow, rect, patternName.toLowerCase());
        } catch (_) {
          // Range errors (e.g. detached node) — silently skip
        }
      }
    }
  }
}

/**
 * Main entry point — called on every GET_DOM_SNAPSHOT.
 * Clears old boxes, runs both passes, draws fresh boxes.
 *
 * @param {Array} sensitiveRegions  — from detectSensitiveDOM() (form inputs)
 * @param {Array} elements          — from extractDOMContext() (interactive elements)
 */
function renderPrivacyOverlays(sensitiveRegions, elements) {
  const shadow = getOverlayShadowRoot();

  // Clear all boxes from the previous snapshot
  shadow.querySelectorAll('.visi-box').forEach(el => el.remove());

  // PASS 1 — Sensitive form elements (password fields, PAN inputs, etc.)
  sensitiveRegions.forEach(r => {
    const [x1, y1, x2, y2] = r.bbox;
    _placeBox(shadow, { left: x1, top: y1, width: x2 - x1, height: y2 - y1 }, r.type);
  });

  // PASS 1b — Interactive elements whose entire label was redacted
  //           (e.g. a button whose aria-label contained a phone number)
  elements.forEach(el => {
    if (!el.label || !el.label.includes('[REDACTED_')) return;
    const domEl = document.getElementById(el.id);
    if (!domEl) return;
    const rect = domEl.getBoundingClientRect();
    const match = el.label.match(/\[REDACTED_([A-Z_]+)\]/);
    const type = match ? match[1].toLowerCase() : 'sensitive';
    _placeBox(shadow, rect, type);
  });

  // PASS 2 — Box PII found in ANY text node anywhere on the page
  _boxAllPIITextNodes(shadow);
}

/** Remove all overlay boxes (called on navigation). */
function clearPrivacyOverlays() {
  const host = document.getElementById(OVERLAY_HOST_ID);
  if (host && host.shadowRoot) {
    host.shadowRoot.querySelectorAll('.visi-box').forEach(el => el.remove());
  }
}

// Auto-clear when the page navigates away
window.addEventListener('pagehide', clearPrivacyOverlays);

// Continuous Dynamic Redaction: keep overlays updated on scroll & dynamic DOM changes
let _overlayDebounceTimer = null;
function scheduleDynamicOverlayRefresh() {
  if (_overlayDebounceTimer) clearTimeout(_overlayDebounceTimer);
  _overlayDebounceTimer = setTimeout(() => {
    try {
      const snapshot = extractDOMContext(document);
      renderPrivacyOverlays(snapshot.sensitiveDOM, snapshot.elements);
    } catch (_) {}
  }, 250);
}

window.addEventListener('scroll', scheduleDynamicOverlayRefresh, { passive: true });
window.addEventListener('resize', scheduleDynamicOverlayRefresh, { passive: true });

if (typeof MutationObserver !== 'undefined' && document.body) {
  const domObserver = new MutationObserver((mutations) => {
    // Only refresh if mutations are outside our overlay host
    const relevant = mutations.some(m => !m.target.closest || !m.target.closest(`#${OVERLAY_HOST_ID}`));
    if (relevant) scheduleDynamicOverlayRefresh();
  });
  domObserver.observe(document.body, { childList: true, subtree: true });
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

    // Extract safe navigation href for anchors without exposing raw secrets/tokens
    let safeHref = null;
    const anchorEl = el.closest('a[href]');
    if (anchorEl && anchorEl.href) {
      const rawHref = anchorEl.href.trim();
      if (rawHref.startsWith('http://') || rawHref.startsWith('https://')) {
        // Sanitize any PII in URL parameters
        safeHref = sanitizeTextForPII(rawHref);
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
      confidence: 1.0,
      href: safeHref
    });
  });

  // Evaluate current high-level screen state (headings, main section, active form)
  const headings = Array.from(documentObj.querySelectorAll('h1, h2, h3'))
    .map(h => sanitizeTextForPII(h.innerText?.trim()))
    .filter(Boolean)
    .slice(0, 5);

  const activeForm = documentObj.querySelector('form');
  const screenSummary = {
    main_headings: headings,
    has_form: Boolean(activeForm),
    form_inputs_count: activeForm ? activeForm.querySelectorAll('input, select, textarea').length : 0,
    total_interactive: elements.length,
    redactions_count: redactions.length
  };

  return { elements, redactions, sensitiveDOM, screenSummary };
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

      // Requirement 3: Resolve Clickable Ancestors
      // If the matched element is not itself an interactive tag (e.g. <h3> inside <a href="...">),
      // resolve the nearest clickable ancestor like a[href], button, [role="link"], [role="button"]
      const isClickableTag = (node) => {
        if (!node || !node.tagName) return false;
        const tag = node.tagName.toLowerCase();
        if (tag === 'a' && node.hasAttribute('href')) return true;
        if (tag === 'button') return true;
        const role = (node.getAttribute('role') || '').toLowerCase();
        if (role === 'button' || role === 'link' || role === 'tab') return true;
        if (node.hasAttribute('onclick')) return true;
        return false;
      };

      let targetToClick = el;
      if (!isClickableTag(el)) {
        const clickableAncestor = el.closest('a[href], button, [role="button"], [role="link"], [role="tab"], [onclick]');
        if (clickableAncestor) {
          targetToClick = clickableAncestor;
        }
      }

      targetToClick.scrollIntoView({ behavior: 'smooth', block: 'center' });
      targetToClick.focus();
      targetToClick.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
      targetToClick.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
      targetToClick.click();

      // If the target is an anchor with an href, ensure navigation triggers if click didn't navigate
      const href = targetToClick.tagName === 'A' ? targetToClick.href : (targetToClick.closest('a[href]')?.href);

      return {
        success: true,
        action_executed: true,
        target_found: true,
        clicked_id: targetToClick.id || el.id || '',
        clicked_tag: targetToClick.tagName,
        observed_href: href || null,
        message: `Clicked element: ${targetToClick.id || targetToClick.tagName} (resolved from ${el.tagName})`
      };
    }

    case 'open_link': {
      let el = findTargetElement(action.target);
      const targetHref = action.url || (el && (el.href || el.closest('a[href]')?.href));
      if (targetHref && (targetHref.startsWith('http://') || targetHref.startsWith('https://'))) {
        window.location.href = targetHref;
        return {
          success: true,
          action_executed: true,
          target_found: true,
          message: `Opened observed link: ${targetHref}`
        };
      }
      // Fallback to click if no href
      if (el) {
        el.click();
        return { success: true, action_executed: true, target_found: true, message: `Dispatched click for open_link on ${el.id || el.tagName}` };
      }
      return { success: false, action_executed: false, target_found: false, error: 'No target or valid URL for open_link' };
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

      // Safeguard against typing element IDs / internal tags into input
      const targetIdStr = typeof action.target === 'string' ? action.target : (action.target?.element_id || '');
      const isInternalId = /^(visi_el_\d+|red_\d+|element_\d+|name_[\w-]+)$/i.test(textToType.trim());
      if (!textToType.trim() || textToType === targetIdStr || isInternalId) {
        console.warn(`[CONTENT EXECUTOR] Refused to type element ID or empty text: "${textToType}"`);
        return {
          success: false,
          action_executed: false,
          target_found: true,
          error: `Refused to type internal identifier or empty value: "${textToType}"`
        };
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

    case 'search': {
      const el = findTargetElement(action.target);
      if (!el) throw new Error(`Search input element not found: ${JSON.stringify(action.target)}`);
      const textToType = action.value?.text || action.text || '';
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();
      el.value = textToType;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter', code: 'Enter', keyCode: 13 }));
      if (el.form && typeof el.form.requestSubmit === 'function') {
        try { el.form.requestSubmit(); } catch (_) {}
      }
      return { success: true, message: `Searched for "${textToType}" in element ${el.id || el.tagName}` };
    }

    case 'select': {
      const el = findTargetElement(action.target);
      if (!el) throw new Error(`Select element not found: ${JSON.stringify(action.target)}`);
      const optVal = action.option || action.value?.text || '';
      // Try matching value or option text
      let matched = false;
      if (el.options) {
        for (let i = 0; i < el.options.length; i++) {
          if (el.options[i].value === optVal || el.options[i].text.includes(optVal)) {
            el.selectedIndex = i;
            matched = true;
            break;
          }
        }
      }
      if (!matched) el.value = optVal;
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return { success: true, message: `Selected option "${optVal}" on ${el.id || el.tagName}` };
    }

    case 'download': {
      let el = findTargetElement(action.target);
      if (!el && action.target?.bbox) {
        const [x1, y1, x2, y2] = action.target.bbox;
        el = document.elementFromPoint((x1 + x2) / 2, (y1 + y2) / 2);
      }
      if (!el) throw new Error(`Download target element not found: ${JSON.stringify(action.target)}`);
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.click();
      return { success: true, message: `Triggered download on element ${el.id || el.tagName}` };
    }

    case 'go_back': {
      window.history.back();
      return { success: true, message: 'Navigated back in history' };
    }

    case 'go_forward': {
      window.history.forward();
      return { success: true, message: 'Navigated forward in history' };
    }

    case 'scroll': {
      const deltaY = action.amount || action.milliseconds || action.deltaY || 400;
      const dir = (action.direction || 'down').toLowerCase();
      const scrollAmt = dir === 'up' ? -Math.abs(deltaY) : Math.abs(deltaY);
      window.scrollBy({ top: scrollAmt, behavior: 'smooth' });
      return { success: true, message: `Scrolled window ${dir} by ${Math.abs(scrollAmt)}px` };
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
      return { success: true, askUser: true, message: action.question || action.url || 'User confirmation requested' };
    }

    case 'navigate': {
      if (action.url) {
        window.location.href = action.url;
        return { success: true, message: `Navigated to ${action.url}` };
      }
      return { success: false, error: 'No URL provided for navigate action' };
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

      // Draw visible overlay boxes on the page for every hidden element
      renderPrivacyOverlays(snapshot.sensitiveDOM, snapshot.elements);

      sendResponse({
        success: true,
        url: window.location.href,
        title: document.title,
        elements: snapshot.elements,
        redactions: snapshot.redactions,
        sensitiveRegions: snapshot.sensitiveDOM,
        screenSummary: snapshot.screenSummary
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
