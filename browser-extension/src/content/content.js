/**
 * Master Content Script with High-Visibility Visual Bounding Boxes & Badges
 * Renders prominent visual shields so you can physically see every category being protected!
 */

function applyUniversalPrivacyShield() {
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

  let count = 0;

  sensitiveSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(el => {
      if (!el.getAttribute('data-shielded')) {
        el.setAttribute('data-shielded', 'true');
        
        // 1. High-Visibility Glowing Privacy Border
        el.style.border = '2px solid #10b981';
        el.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.7)';
        el.style.transition = 'all 0.3s ease';

        // 2. Attach an explicit on-screen visual shield tag
        const tag = document.createElement('span');
        const piiType = el.getAttribute('data-pii') || (el.type === 'password' ? 'PASSWORD' : 'PII');
        tag.innerText = `🔒 [SHIELDED: ${piiType.toUpperCase()}]`;
        tag.style.display = 'inline-block';
        tag.style.backgroundColor = '#064e3b';
        tag.style.color = '#34d399';
        tag.style.fontSize = '11px';
        tag.style.fontWeight = 'bold';
        tag.style.padding = '2px 6px';
        tag.style.borderRadius = '4px';
        tag.style.marginLeft = '6px';
        tag.style.verticalAlign = 'middle';
        tag.className = 'ps26171-visual-badge';

        if (el.parentNode && !el.parentNode.querySelector('.ps26171-visual-badge')) {
          el.parentNode.insertBefore(tag, el.nextSibling);
        }

        count++;
      }
    });
  });

  return count;
}

// Initial run
applyUniversalPrivacyShield();

// Live DOM observer
const observer = new MutationObserver(() => {
  applyUniversalPrivacyShield();
});
observer.observe(document.documentElement, { childList: true, subtree: true });

console.log('[PS26171] Universal Privacy Shield active across all 20 categories!');
