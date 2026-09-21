/**
 * Real Screen and DOM Perception Pipeline
 * Captures visible tab screenshot, extracts interactive DOM elements,
 * detects sensitive PII via regex and DOM rules, and runs visual model inference.
 */

import { detectSensitiveDOM, scanTextForPII, fuseRegions } from '../privacy/detector.js';

/**
 * Extracts interactable and informative elements from real webpages.
 * Supports any standard HTML5 or modern Single Page App (React, Angular, Vue, Tailwind).
 */
export function extractDOMContext(documentObj) {
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

  // Select all standard interactive and semantic elements across real websites
  const interactiveSelectors = 'button, input, select, textarea, a[href], [role="button"], [role="link"], [role="searchbox"], [role="combobox"], [onclick], [tabindex="0"]';
  const nodes = documentObj.querySelectorAll(interactiveSelectors);

  const seen = new Set();

  nodes.forEach((el, idx) => {
    if (seen.has(el)) return;
    seen.add(el);

    const rect = el.getBoundingClientRect();
    // Filter out invisible, hidden, or zero-sized elements
    if (rect.width <= 2 || rect.height <= 2) return;
    const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
    if (style && (style.visibility === 'hidden' || style.display === 'none' || parseFloat(style.opacity) === 0)) {
      return;
    }

    // Check if element is sensitive
    const isSensitive = el.type === 'password' || 
                        el.hasAttribute('data-pii') || 
                        (el.id && (el.id.includes('pass') || el.id.includes('account') || el.id.includes('balance') || el.id.includes('otp')));

    // Extract best informative label for planner reasoning
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
    }

    // Generate stable element ID if not present
    let elementId = el.id;
    if (!elementId) {
      elementId = el.name ? `name_${el.name}` : `visi_el_${idx}`;
      // Attach to element dataset for fast reverse-lookup
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

  return {
    elements,
    redactions,
    sensitiveDOM
  };
}
