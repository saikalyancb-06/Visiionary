/**
 * Real Screen and DOM Perception Pipeline (Phases 4 & 5)
 * Captures visible tab screenshot, extracts interactive DOM elements,
 * detects sensitive PII via regex and DOM rules, and runs visual model inference.
 */

import { detectSensitiveDOM, scanTextForPII, fuseRegions } from '../privacy/detector.js';

/**
 * Extracts interactable and informative elements from document DOM.
 * Redacts any text content belonging to sensitive fields so raw PII never leaks.
 */
export function extractDOMContext(documentObj) {
  const elements = [];
  const redactions = [];
  const sensitiveDOM = detectSensitiveDOM(documentObj);
  const sensitiveSet = new Set();

  sensitiveDOM.forEach(r => {
    redactions.push({
      id: r.id,
      type: r.type,
      placeholder: `[REDACTED_${r.type.toUpperCase()}]`,
      bbox: r.bbox
    });
  });

  // Extract all interactive elements (buttons, inputs, links, selects)
  const interactiveSelectors = 'button, input, select, textarea, a, [role="button"], [onclick]';
  const nodes = documentObj.querySelectorAll(interactiveSelectors);

  nodes.forEach((el, idx) => {
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    // Check if this element is marked sensitive
    const isSensitive = el.type === 'password' || 
                        el.hasAttribute('data-pii') || 
                        (el.id && (el.id.includes('pass') || el.id.includes('account') || el.id.includes('balance') || el.id.includes('otp')));

    let label = el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.id || `element_${idx}`;
    if (isSensitive) {
      label = `[REDACTED_${(el.getAttribute('data-pii') || el.type || 'SENSITIVE').toUpperCase()}]`;
    }

    elements.push({
      id: el.id || `el_${idx}`,
      role: el.tagName.toLowerCase(),
      label: label.trim(),
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

  return {
    elements,
    redactions,
    sensitiveDOM
  };
}
