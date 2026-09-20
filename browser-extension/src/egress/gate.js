/**
 * EGRESS GATE (Architectural Choke Point)
 * SECTION B2 TRUST BOUNDARY ENFORCEMENT
 *
 * The gate is the ONLY module permitted to invoke network fetch.
 * It enforces payload scans for unredacted PII and blocks on any violation (Fail-Closed).
 */
import { PII_PATTERNS } from '../privacy/detector.js';

export class EgressGateViolationError extends Error {
  constructor(message, violations) {
    super(message);
    this.name = 'EgressGateViolationError';
    this.violations = violations;
  }
}

export async function sendSanitizedContextToGate(sanitizedPayload, serverUrl, apiKey) {
  // 1. Final Safety Scan across all serialized fields (Fail-Closed)
  const violations = [];
  const serialized = JSON.stringify(sanitizedPayload);

  for (const [patternName, regex] of Object.entries(PII_PATTERNS)) {
    // Reset regex state
    regex.lastIndex = 0;
    const matches = serialized.match(regex);
    if (matches && matches.length > 0) {
      // Exclude placeholder tokens such as [REDACTED_EMAIL]
      const realLeaks = matches.filter(m => !m.includes('REDACTED'));
      if (realLeaks.length > 0) {
        violations.push({ pattern: patternName, matches: realLeaks });
      }
    }
  }

  if (violations.length > 0) {
    console.error('[EGRESS GATE] BLOCKED: Unredacted PII detected in outgoing payload!', violations);
    throw new EgressGateViolationError('Egress Gate blocked payload: sensitive data detected.', violations);
  }

  // 2. Transmit only verified sanitized payload
  const response = await fetch(`${serverUrl}/api/agent/plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey || ''
    },
    body: serialized
  });

  if (!response.ok) {
    throw new Error(`Server returned HTTP ${response.status}: ${await response.text()}`);
  }

  return await response.json();
}
