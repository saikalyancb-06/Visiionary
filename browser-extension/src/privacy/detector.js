/**
 * PII Validator and Pattern Matcher
 * Layer 1 (Regex & Algorithmic Checksums) & Layer 2 (DOM Attribute Analysis)
 */

export const PII_PATTERNS = {
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

/**
 * Luhn checksum algorithm for Credit/Debit card numbers
 */
export function luhnCheck(numStr) {
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

/**
 * Verhoeff checksum algorithm for 12-digit Indian Aadhaar numbers
 */
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

export function verhoeffCheck(numStr) {
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

/**
 * Simple non-reversible token hash for safe diagnostic audit logging (Zero Raw PII Leakage)
 */
export function hashToken(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return 'fp_' + Math.abs(hash).toString(16).substring(0, 8);
}

/**
 * Generic string sanitizer: detects genuine PII in text and replaces it with safe placeholders.
 */
export function sanitizeTextForPII(text) {
  if (!text || typeof text !== 'string') return text;
  let sanitized = text;

  // 1. Email
  sanitized = sanitized.replace(PII_PATTERNS.EMAIL, '[REDACTED_EMAIL]');
  // 2. UPI
  sanitized = sanitized.replace(PII_PATTERNS.UPI, (m) => m.includes('REDACTED') ? m : '[REDACTED_UPI]');
  // 3. PAN
  sanitized = sanitized.replace(PII_PATTERNS.PAN, '[REDACTED_PAN]');
  // 4. IFSC
  sanitized = sanitized.replace(PII_PATTERNS.IFSC, '[REDACTED_IFSC]');
  // 5. Card with Luhn validation
  sanitized = sanitized.replace(PII_PATTERNS.CARD_NUMBER, (m) => luhnCheck(m) ? '[REDACTED_CARD]' : m);
  // 6. Aadhaar with Verhoeff validation
  sanitized = sanitized.replace(PII_PATTERNS.AADHAAR, (m) => verhoeffCheck(m) ? '[REDACTED_AADHAAR]' : m);
  // 7. Phone
  sanitized = sanitized.replace(PII_PATTERNS.PHONE, '[REDACTED_PHONE]');

  return sanitized;
}

/**
 * Scans a text string for sensitive PII patterns.
 * Validates algorithmic checksums (Luhn, Verhoeff) to prevent false positives on random 16 or 12 digit numbers.
 * Returns array of safe match metadata: { type, index, length, fingerprint }
 */
export function scanTextForPII(text) {
  if (!text || typeof text !== 'string') return [];
  const found = [];

  for (const [type, regex] of Object.entries(PII_PATTERNS)) {
    regex.lastIndex = 0;
    let m;
    while ((m = regex.exec(text)) !== null) {
      const val = m[0];
      if (val.includes('REDACTED')) continue;

      // Algorithmic validation gates
      if (type === 'CARD_NUMBER' && !luhnCheck(val)) {
        continue; // Not a valid card number, don't falsely classify
      }
      if (type === 'AADHAAR' && !verhoeffCheck(val)) {
        continue; // Not a valid Aadhaar number, don't falsely classify
      }

      found.push({
        type,
        index: m.index,
        length: val.length,
        fingerprint: hashToken(val)
      });
    }
  }

  return found;
}

/**
 * DOM-based sensitive region detector (Phase 5)
 */
export function detectSensitiveDOM(documentObj) {
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
    '[id*="account"]',
    '[id*="balance"]',
    '[id*="pan"]',
    '[id*="aadhaar"]',
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

      const textVal = el.value || el.innerText || '';

      sensitiveRegions.push({
        id: `dom_${Math.random().toString(36).substring(2, 7)}`,
        type: piiType,
        text: textVal,
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

/**
 * Region Fusion (Phase 5 & 6)
 * Merges DOM-derived sensitive regions with visual ONNX detections.
 * Resolves overlapping bounding boxes via union (IoU/overlap merge).
 */
export function fuseRegions(domRegions, visualDetections) {
  const fused = [];

  // Add all DOM regions
  for (const dr of domRegions) {
    fused.push({
      id: dr.id || `fused_${fused.length}`,
      type: dr.type || 'DOM_SENSITIVE',
      bbox: [...dr.bbox],
      source: 'dom'
    });
  }

  // Merge or add visual detections
  for (const vd of visualDetections) {
    const vBox = [vd.x1, vd.y1, vd.x2, vd.y2];
    let merged = false;

    for (const f of fused) {
      const fBox = f.bbox;
      // Check intersection
      const xA = Math.max(fBox[0], vBox[0]);
      const yA = Math.max(fBox[1], vBox[1]);
      const xB = Math.min(fBox[2], vBox[2]);
      const yB = Math.min(fBox[3], vBox[3]);

      const interArea = Math.max(0, xB - xA) * Math.max(0, yB - yA);
      if (interArea > 0) {
        // Expand bounding box to envelop both
        f.bbox[0] = Math.min(fBox[0], vBox[0]);
        f.bbox[1] = Math.min(fBox[1], vBox[1]);
        f.bbox[2] = Math.max(fBox[2], vBox[2]);
        f.bbox[3] = Math.max(fBox[3], vBox[3]);
        f.source = 'dom+visual_fusion';
        merged = true;
        break;
      }
    }

    if (!merged) {
      fused.push({
        id: `vis_${fused.length}`,
        type: vd.class || 'VISUAL_PII',
        bbox: vBox,
        source: 'visual_model',
        confidence: vd.confidence
      });
    }
  }

  return fused;
}
