/**
 * EGRESS GATE (Architectural Choke Point — Phase 8)
 * SECTION B2 TRUST BOUNDARY ENFORCEMENT
 *
 * INVARIANTS:
 * 1. The Egress Gate is the ONLY module in the extension permitted to invoke network fetch.
 * 2. It performs mandatory schema validation.
 * 3. It runs a deep post-redaction privacy scan for PII and raw vault secrets.
 * 4. It blocks on any violation (Fail-Closed).
 * 5. Detector or scanner errors trigger immediate BLOCK (Fail-Closed).
 */

import { verifyPostRedactionPrivacy } from '../privacy/redactor.js';
import { containsVaultSecret } from '../vault/vault.js';

export class EgressGateViolationError extends Error {
  constructor(message, violations = []) {
    super(message);
    this.name = 'EgressGateViolationError';
    this.violations = violations;
  }
}

/**
 * Validates outgoing schema conforms strictly to SanitizedContextPackage
 */
export function validatePayloadSchema(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new EgressGateViolationError('Payload must be a non-null object');
  }

  const requiredFields = ['session_id', 'step', 'instruction_sanitized', 'page', 'privacy_report'];
  for (const field of requiredFields) {
    if (!(field in payload)) {
      throw new EgressGateViolationError(`Missing required payload schema field: ${field}`);
    }
  }

  if (typeof payload.instruction_sanitized !== 'string') {
    throw new EgressGateViolationError('instruction_sanitized must be a string');
  }

  if (!payload.page || typeof payload.page.url_sanitized !== 'string') {
    throw new EgressGateViolationError('page.url_sanitized must be a valid string');
  }

  // Ensure elements is an array
  if (payload.elements && !Array.isArray(payload.elements)) {
    throw new EgressGateViolationError('elements must be an array');
  }

  // Ensure sensitive raw data is NOT passed in elements
  if (payload.elements) {
    for (const el of payload.elements) {
      if (el.sensitivity === 'sensitive_raw') {
        throw new EgressGateViolationError(`Unsanitized raw element detected in payload: ${el.id}`);
      }
    }
  }

  return true;
}

/**
 * The ONLY function authorized to communicate with the server/planner.
 */
export async function sendSanitizedContextToGate(sanitizedPayload, serverUrl = 'http://127.0.0.1:8080', apiKey = '') {
  // Step 1: Validate schema
  try {
    validatePayloadSchema(sanitizedPayload);
  } catch (schemaErr) {
    console.error('[EGRESS GATE] BLOCKED: Malformed payload schema:', schemaErr.message);
    throw schemaErr;
  }

  // Step 2: Post-Redaction Deep Privacy Scan (Fail-Closed)
  let verification;
  try {
    verification = verifyPostRedactionPrivacy(sanitizedPayload);
  } catch (scanErr) {
    console.error('[EGRESS GATE] BLOCKED: Detector failure (Fail-Closed triggered):', scanErr);
    throw new EgressGateViolationError('Privacy scanner failure: failing closed.', [scanErr.message]);
  }

  if (!verification.safe) {
    console.error('[EGRESS GATE] BLOCKED: Sensitive data detected in outgoing payload!', verification.violations);
    throw new EgressGateViolationError(`Egress Gate blocked payload: ${verification.reason}`, verification.violations);
  }

  // Step 3: Vault isolation check
  const serialized = JSON.stringify(sanitizedPayload);
  const vaultCheck = containsVaultSecret(serialized);
  if (vaultCheck.leak) {
    console.error(`[EGRESS GATE] BLOCKED: Vault secret '${vaultCheck.secretRef}' found in outgoing payload!`);
    throw new EgressGateViolationError(`Vault credential leak detected for ${vaultCheck.secretRef}`);
  }

  // Step 4: Transmit only verified sanitized payload
  const response = await fetch(`${serverUrl}/api/agent/plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey || ''
    },
    body: serialized
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Server returned HTTP ${response.status}: ${errText}`);
  }

  const planResponse = await response.json();
  return planResponse;
}
