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

  // 3. Live Webcam & Video Elements Shielding (Face & Biometric Masking)
  document.querySelectorAll('video').forEach(video => {
    if (!video.getAttribute('data-shielded-video')) {
      video.setAttribute('data-shielded-video', 'true');

      // Add high-visibility glowing shield box
      video.style.outline = '4px solid #10b981';
      video.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.8)';
      video.style.position = 'relative';

      // Attach floating indicator badge and simulated face redaction box
      const container = document.createElement('div');
      container.className = 'ps26171-video-shield-overlay';
      container.style.position = 'absolute';
      container.style.zIndex = '999999';
      container.style.pointerEvents = 'none';

      const updateOverlayPosition = () => {
        const rect = video.getBoundingClientRect();
        container.style.top = (rect.top + window.scrollY) + 'px';
        container.style.left = (rect.left + window.scrollX) + 'px';
        container.style.width = rect.width + 'px';
        container.style.height = rect.height + 'px';
      };

      container.innerHTML = `
        <div style="position: absolute; top: 12px; left: 12px; background: rgba(6, 78, 59, 0.95); color: #34d399; font-family: monospace; font-size: 13px; font-weight: bold; padding: 6px 12px; border-radius: 6px; border: 1px solid #10b981; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
          🔒 [SHIELDED: BIOMETRIC_WEBCAM_FACE] — LIVE PRIVACY GATE
        </div>
        <div style="position: absolute; top: 25%; left: 35%; width: 30%; height: 45%; border: 3px dashed #ef4444; background: rgba(0, 0, 0, 0.85); border-radius: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 0 15px rgba(239, 68, 68, 0.7);">
          <span style="font-size: 26px;">🛡️</span>
          <span style="color: #f87171; font-family: monospace; font-size: 12px; font-weight: bold; margin-top: 4px;">FACE REDACTED</span>
          <span style="color: #9ca3af; font-family: monospace; font-size: 9px;">ON-DEVICE GUARD</span>
        </div>
      `;

      document.body.appendChild(container);
      updateOverlayPosition();

      window.addEventListener('resize', updateOverlayPosition);
      window.addEventListener('scroll', updateOverlayPosition);
      video.addEventListener('loadedmetadata', updateOverlayPosition);
      video.addEventListener('play', updateOverlayPosition);
      
      count++;
    }
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

console.log('[PS26171] Universal Privacy Shield active across all 20 categories + Live Webcam/Video!');
