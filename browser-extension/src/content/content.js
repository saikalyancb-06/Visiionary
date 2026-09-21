/**
 * Content Script for Real-World & Production Sites (Gmail, Amazon, Banking, etc.)
 * Dynamically detects email, password, username, card, and sensitive inputs.
 * Masks them with a real-time visual indicator, collects sanitized elements, and executes actions.
 */

function applyRealtimePrivacyShield() {
  const sensitiveSelectors = [
    'input[type="password"]',
    'input[type="email"]',
    'input[type="tel"]',
    'input[name*="pass"]',
    'input[name*="email"]',
    'input[name*="user"]',
    'input[name*="identifier"]',
    'input[id*="identifier"]',
    'input[autocomplete*="password"]',
    'input[autocomplete*="username"]',
    'input[autocomplete*="email"]',
    'input[autocomplete*="cc-"]',
    '[data-pii]',
    '[id*="account"]',
    '[id*="balance"]',
    '[class*="sensitive"]'
  ];

  let maskedCount = 0;

  sensitiveSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(el => {
      if (!el.getAttribute('data-shielded')) {
        el.setAttribute('data-shielded', 'true');
        el.style.border = '2px solid #10b981';
        el.style.boxShadow = '0 0 8px rgba(16, 185, 129, 0.5)';
        el.title = '🔒 Protected by PS26171 On-Device Privacy Shield';
        maskedCount++;
      }
    });
  });

  return maskedCount;
}

// Initial run on load
applyRealtimePrivacyShield();

// Observe dynamic DOM changes (Gmail / React SPAs)
const observer = new MutationObserver(() => {
  applyRealtimePrivacyShield();
});
observer.observe(document.documentElement, { childList: true, subtree: true });

// Message Handler for Real-Time Execution
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_DOM_SNAPSHOT') {
    const masked = applyRealtimePrivacyShield();
    
    // Collect interactive elements safely
    const elements = [];
    const redactions = [];
    
    // Scan buttons and links
    document.querySelectorAll('button, a, input[type="submit"]').forEach((el, idx) => {
      const rect = el.getBoundingClientRect();
      const text = el.innerText || el.value || el.ariaLabel || '';
      if (rect.width > 0 && rect.height > 0 && text.trim().length > 0) {
        elements.push({
          id: el.id || `el_${idx}`,
          role: el.tagName.toLowerCase() === 'button' ? 'button' : 'link',
          label: text.trim().substring(0, 50),
          bbox: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
          interactable: true,
          sensitivity: 'safe',
          source: 'dom',
          confidence: 1.0
        });
      }
    });

    // Scan sensitive masked inputs
    document.querySelectorAll('[data-shielded="true"]').forEach((el, idx) => {
      const rect = el.getBoundingClientRect();
      redactions.push({
        id: `redact_${idx}`,
        type: el.type === 'password' ? 'PASSWORD' : 'PII',
        placeholder: el.type === 'password' ? '[[PASSWORD_1]]' : '[[IDENTIFIER_1]]',
        bbox: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)]
      });
    });

    sendResponse({
      status: 'SHIELDED',
      url: window.location.origin + window.location.pathname,
      title: document.title,
      maskedElementsCount: masked,
      elements: elements.slice(0, 30),
      redactions: redactions
    });
  } else if (request.type === 'EXECUTE_CLICK') {
    let target = document.getElementById(request.elementId);
    if (!target) {
      // Fallback search by text
      document.querySelectorAll('button, a').forEach(el => {
        if ((el.innerText || '').includes(request.elementId)) {
          target = el;
        }
      });
    }
    if (target) {
      target.click();
      sendResponse({ status: 'CLICKED' });
    } else {
      sendResponse({ status: 'NOT_FOUND' });
    }
  }
  return true;
});

console.log('[PS26171] Privacy Shield active on:', window.location.hostname);
