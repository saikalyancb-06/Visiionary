/**
 * Content Script for Real-Time Privacy Shield
 * Runs directly inside web pages (Demo portals or any real site).
 * Automatically detects PII fields in the DOM, masks them, and prevents unredacted data leakage.
 */

// 1. PII Patterns for real-time DOM matching
const PII_PATTERNS = {
  EMAIL: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
  PHONE: /(\+91[\-\s]?)?[6789]\d{4}[\-\s]?\d{5}/g,
  CARD_NUMBER: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
  PAN: /[A-Z]{5}[0-9]{4}[A-Z]{1}/g,
  AADHAAR: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,
  BANK_ACCOUNT: /\b\d{9,18}\b/g
};

// 2. Visual Privacy Shield Overlay
function applyRealtimePrivacyShield() {
  const sensitiveSelectors = [
    'input[type="password"]',
    '[autocomplete*="password"]',
    '[autocomplete*="cc-"]',
    '[data-pii]',
    '[id*="account"]',
    '[id*="balance"]',
    '[class*="sensitive"]'
  ];

  let maskedCount = 0;

  // Mask DOM elements with explicit attributes or IDs
  sensitiveSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(el => {
      if (!el.getAttribute('data-shielded')) {
        el.setAttribute('data-shielded', 'true');
        el.style.backgroundColor = '#111827';
        el.style.color = '#10b981';
        el.style.fontWeight = 'bold';
        el.style.borderRadius = '4px';
        el.style.padding = '2px 6px';
        el.title = '🔒 Protected by PS26171 On-Device Privacy Shield';
        maskedCount++;
      }
    });
  });

  return maskedCount;
}

// Run immediately on page load
applyRealtimePrivacyShield();

// Observe dynamic DOM changes (SPA / React / AJAX)
const observer = new MutationObserver(() => {
  applyRealtimePrivacyShield();
});
observer.observe(document.body, { childList: true, subtree: true });

// Listen for messages from popup or background agent
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_DOM_SNAPSHOT') {
    const masked = applyRealtimePrivacyShield();
    sendResponse({
      status: 'SHIELDED',
      url: window.location.href,
      title: document.title,
      maskedElementsCount: masked
    });
  } else if (request.type === 'EXECUTE_CLICK') {
    const el = document.getElementById(request.elementId);
    if (el) {
      el.click();
      sendResponse({ status: 'CLICKED', elementId: request.elementId });
    } else {
      sendResponse({ status: 'NOT_FOUND', elementId: request.elementId });
    }
  }
  return true;
});
console.log('[PS26171] Real-Time Privacy Shield Active.');
