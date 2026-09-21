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
 * Post-Redaction Privacy Verification (Phase 7)
 * Scans the sanitized DOM context and outgoing package strings for any unredacted PII or secrets.
 * Must be FAIL-CLOSED: if scanner detects leak or throws error, returns safe = false.
 */
export function verifyPostRedactionPrivacy(sanitizedPayload) {
  try {
    const serialized = JSON.stringify(sanitizedPayload);

    // 1. Scan for PII regex patterns
    const piiMatches = scanTextForPII(serialized);
    if (piiMatches.length > 0) {
      return {
        safe: false,
        reason: 'Unredacted PII pattern found in sanitized payload',
        violations: piiMatches
      };
    }

    // 2. Scan for any raw vault secrets
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
