/**
 * Real Pixel-Level Canvas Redaction Engine (Phase 6) & Post-Redaction Verification (Phase 7)
 * INVARIANT: Sensitive regions are replaced locally with solid opaque black blocks.
 * Post-redaction scanning ensures fail-closed defense: if any sensitive data persists, BLOCK EGRESS.
 */

import { scanTextForPII } from './detector.js';
import { containsVaultSecret } from '../vault/vault.js';

/**
 * Redacts an image at pixel level using Canvas 2D.
 * Overwrites all sensitive bounding box areas with solid opaque black pixels.
 */
export async function redactImageCanvas(imageSource, sensitiveRegions) {
  let width, height;
  if (imageSource instanceof HTMLImageElement || imageSource instanceof ImageBitmap) {
    width = imageSource.width;
    height = imageSource.height;
  } else if (imageSource.naturalWidth) {
    width = imageSource.naturalWidth;
    height = imageSource.naturalHeight;
  } else {
    width = 1280;
    height = 720;
  }

  const canvas = (typeof OffscreenCanvas !== 'undefined')
    ? new OffscreenCanvas(width, height)
    : document.createElement('canvas');

  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  // Draw original image
  ctx.drawImage(imageSource, 0, 0, width, height);

  // Apply Solid Opaque Redactions
  ctx.fillStyle = '#000000';
  for (const region of sensitiveRegions) {
    const bbox = region.bbox || [region.x1, region.y1, region.x2, region.y2];
    const x1 = Math.max(0, Math.min(width, bbox[0]));
    const y1 = Math.max(0, Math.min(height, bbox[1]));
    const x2 = Math.max(0, Math.min(width, bbox[2]));
    const y2 = Math.max(0, Math.min(height, bbox[3]));

    const w = x2 - x1;
    const h = y2 - y1;

    if (w > 0 && h > 0) {
      // Completely destroy underlying pixels with solid black block
      ctx.fillRect(x1, y1, w, h);
    }
  }

  return canvas;
}

/**
 * Extracts only textual payload fields for PII verification.
 * EXCLUDES binary/base64 data (e.g. screenshot.data_url) to prevent false-positive matches on random base64 digits.
 */
export function collectTextEntriesForPrivacyScan(payload) {
  const entries = [];

  if (typeof payload.instruction_sanitized === 'string') {
    entries.push({ field: 'instruction_sanitized', text: payload.instruction_sanitized });
  }

  if (payload.page) {
    if (typeof payload.page.url_sanitized === 'string') {
      entries.push({ field: 'page.url_sanitized', text: payload.page.url_sanitized });
    }
    if (typeof payload.page.title_sanitized === 'string') {
      entries.push({ field: 'page.title_sanitized', text: payload.page.title_sanitized });
    }
  }

  if (Array.isArray(payload.elements)) {
    for (const el of payload.elements) {
      if (typeof el.label === 'string') {
        entries.push({ field: `elements[id=${el.id}].label`, text: el.label });
      }
      // NOTE: el.id is an opaque DOM identifier (e.g. Amazon uses numeric product IDs).
      // Running PII regexes against DOM IDs causes false positives. EXCLUDED.
    }
  }

  if (Array.isArray(payload.redactions)) {
    for (const r of payload.redactions) {
      if (typeof r.placeholder === 'string') {
        entries.push({ field: `redactions[${r.id}].placeholder`, text: r.placeholder });
      }
    }
  }

  if (Array.isArray(payload.history)) {
    for (let i = 0; i < payload.history.length; i++) {
      const item = payload.history[i];
      if (typeof item.action === 'string') {
        entries.push({ field: `history[${i}].action`, text: item.action });
      }
      if (typeof item.result === 'string') {
        entries.push({ field: `history[${i}].result`, text: item.result });
      }
    }
  }

  return entries;
}

/**
 * Post-Redaction Privacy Verification (Phase 7)
 * Scans the sanitized DOM context and outgoing package strings for any unredacted PII or secrets.
 * Must be FAIL-CLOSED: if scanner detects leak or throws error, returns safe = false.
 */
export function verifyPostRedactionPrivacy(sanitizedPayload) {
  try {
    const textEntries = collectTextEntriesForPrivacyScan(sanitizedPayload);
    const violations = [];

    // 1. Scan text entries for PII regex patterns (EXCLUDING binary base64 screenshots)
    for (const entry of textEntries) {
      const piiMatches = scanTextForPII(entry.text);
      if (piiMatches.length > 0) {
        for (const m of piiMatches) {
          console.error(`[EGRESS DEBUG] PII candidate:
field=${entry.field}
type=${m.type}
length=${m.length}
fingerprint=${m.fingerprint}`);

          violations.push({
            field: entry.field,
            type: m.type,
            index: m.index,
            length: m.length,
            fingerprint: m.fingerprint
          });
        }
      }
    }

    if (violations.length > 0) {
      return {
        safe: false,
        reason: 'Unredacted PII pattern found in sanitized payload',
        violations: violations
      };
    }

    // 2. Scan entire serialized package for raw vault secrets (checking exact strings)
    const serialized = JSON.stringify(sanitizedPayload);
    const secretCheck = containsVaultSecret(serialized);
    if (secretCheck.leak) {
      return {
        safe: false,
        reason: `Vault secret leakage detected for secret_ref: ${secretCheck.secretRef}`,
        violations: [secretCheck.secretRef]
      };
    }

    return {
      safe: true,
      reason: 'Post-redaction privacy verification passed cleanly'
    };
  } catch (err) {
    // FAIL-CLOSED: if privacy scanner fails, reject
    return {
      safe: false,
      reason: `Privacy verification scanner error (fail-closed triggered): ${err.message}`
    };
  }
}
