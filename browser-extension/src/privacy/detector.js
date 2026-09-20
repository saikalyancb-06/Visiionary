/**
 * PII Validator and Pattern Matcher
 * Layer 1 & Layer 2 Sensitive Data Detection
 */
export const PII_PATTERNS = {
  EMAIL: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
  PHONE: /(\+91[\-\s]?)?[6789]\d{4}[\-\s]?\d{5}/g,
  CARD_NUMBER: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
  PAN: /[A-Z]{5}[0-9]{4}[A-Z]{1}/g,
  AADHAAR: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,
  BANK_ACCOUNT: /\b\d{9,18}\b/g,
  UPI: /[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}/g
};

export function luhnCheck(numStr) {
  const clean = numStr.replace(/\D/g, "");
  if (clean.length < 13 || clean.length > 19) return false;
  let sum = 0;
  let double = false;
  for (let i = clean.length - 1; i >= 0; i--) {
    let digit = parseInt(clean.charAt(i), 10);
    if (double) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    double = !double;
  }
  return sum % 10 === 0;
}

export function detectSensitiveDOM(documentObj) {
  const sensitiveRegions = [];
  
  // 1. Attribute & Selector Rules
  const sensitiveSelectors = [
    'input[type="password"]',
    '[autocomplete*="password"]',
    '[autocomplete*="cc-"]',
    '[data-pii]',
    '[id*="account"]',
    '[id*="balance"]',
    '[class*="sensitive"]'
  ];

  sensitiveSelectors.forEach(sel => {
    documentObj.querySelectorAll(sel).forEach(el => {
      const rect = el.getBoundingClientRect();
      const piiType = el.getAttribute('data-pii') || (el.type === 'password' ? 'password' : 'unknown_sensitive');
      sensitiveRegions.push({
        id: `dom_${Math.random().toString(36).substring(2, 7)}`,
        type: piiType,
        text: el.innerText || el.value || '',
        bbox: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
        source: 'dom_rules'
      });
    });
  });

  return sensitiveRegions;
}
