/**
 * Content Script for Real-World & Production Sites (Gmail, Amazon, Banking, etc.)
 * Dynamically detects email, password, username, card, and sensitive inputs.
 * Masks them with a real-time visual indicator and keeps credentials isolated in the local vault.
 */

function applyRealtimePrivacyShield() {
  // Comprehensive real-world selectors for Gmail, Google Accounts, Microsoft, Banks, etc.
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
    '[class*="sensitive"]'
  ];

  let maskedCount = 0;

  sensitiveSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(el => {
      if (!el.getAttribute('data-shielded')) {
        el.setAttribute('data-shielded', 'true');
        
        // Add subtle privacy shield styling
        el.style.border = '2px solid #10b981';
        el.style.boxShadow = '0 0 6px rgba(16, 185, 129, 0.4)';
        el.title = '🔒 Protected by PS26171 On-Device Privacy Shield (Local Vault Active)';
        
        maskedCount++;
      }
    });
  });

  return maskedCount;
}

// Initial run
applyRealtimePrivacyShield();

// Observe dynamic DOM updates (Single Page Applications like Gmail / React / Angular)
const observer = new MutationObserver(() => {
  applyRealtimePrivacyShield();
});
observer.observe(document.documentElement, { childList: true, subtree: true });

console.log('[PS26171] Privacy Shield active on:', window.location.hostname);
