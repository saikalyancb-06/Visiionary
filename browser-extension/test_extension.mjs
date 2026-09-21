/**
 * Browser Extension Tests (Node --test)
 * Tests:
 * 1. PII Patterns & Algorithmic Validators (Luhn, Verhoeff)
 * 2. Region Fusion (DOM + Visual ONNX detections)
 * 3. Local Vault (secret_ref storage, resolution, leak detection)
 * 4. Egress Gate (fail-closed defense, schema validation, leak rejection)
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import { scanTextForPII, luhnCheck, verhoeffCheck, fuseRegions } from './src/privacy/detector.js';
import { initVault, setSecret, resolveSecret, containsVaultSecret } from './src/vault/vault.js';
import { validatePayloadSchema, sendSanitizedContextToGate, EgressGateViolationError } from './src/egress/gate.js';

test('Luhn Card Checksum Validator', () => {
  assert.equal(luhnCheck('4532 0150 9283 4917'), true);
  assert.equal(luhnCheck('4532 0150 9283 0000'), false);
});

test('Verhoeff Aadhaar Checksum Validator', () => {
  assert.equal(verhoeffCheck('5481 9201 3846'), true);
  assert.equal(verhoeffCheck('1234 5678 9012'), false);
});

test('PII Scanner Identifies Sensitive Patterns', () => {
  const text = 'User Ananya Sharma, email ananya.sharma@example.in, card 4532015092834917, phone +91 98451 23091, pan ABCDE1234F';
  const matches = scanTextForPII(text);
  const types = matches.map(m => m.type);
  assert.ok(types.includes('EMAIL'));
  assert.ok(types.includes('CARD_NUMBER'));
  assert.ok(types.includes('PHONE'));
  assert.ok(types.includes('PAN'));
});

test('Region Fusion merges overlapping visual & DOM regions', () => {
  const domRegions = [
    { id: 'd1', type: 'password', bbox: [100, 100, 200, 150] }
  ];
  const visualDetections = [
    { class: 'PASSWORD', confidence: 0.95, x1: 90, y1: 95, x2: 210, y2: 155 },
    { class: 'PERSON_NAME', confidence: 0.90, x1: 300, y1: 50, x2: 450, y2: 80 }
  ];
  const fused = fuseRegions(domRegions, visualDetections);
  assert.equal(fused.length, 2);
  assert.equal(fused[0].bbox[0], 90);
  assert.equal(fused[0].bbox[2], 210);
  assert.equal(fused[0].source, 'dom+visual_fusion');
});

test('Credential Vault handles secret_ref and protects raw secrets', async () => {
  await initVault();
  await setSecret('test.apikey', 'sk-super-secret-key-12345');
  assert.equal(resolveSecret('test.apikey'), 'sk-super-secret-key-12345');

  const safeText = '{"action": "type", "value": {"secret_ref": "test.apikey"}}';
  assert.equal(containsVaultSecret(safeText).leak, false);

  const leakedText = '{"action": "type", "value": "sk-super-secret-key-12345"}';
  assert.equal(containsVaultSecret(leakedText).leak, true);
});

test('Egress Gate validates schema and rejects malformed payloads', () => {
  assert.throws(() => validatePayloadSchema(null), EgressGateViolationError);
  assert.throws(() => validatePayloadSchema({ session_id: '123' }), EgressGateViolationError);

  const validPayload = {
    session_id: 's1',
    step: 1,
    instruction_sanitized: 'test',
    page: { url_sanitized: 'http://test.com', title_sanitized: 'Test', viewport: {} },
    elements: [],
    redactions: [],
    privacy_report: { detected: 0, sensitive: 0, redacted: 0, verification: 'PASS', gate: 'PASS' }
  };
  assert.equal(validatePayloadSchema(validPayload), true);
});

test('Egress Gate blocks payloads containing raw PII (Fail-Closed)', async () => {
  const leakyPayload = {
    session_id: 's1',
    step: 1,
    instruction_sanitized: 'Email me at leak.user@example.com immediately',
    page: { url_sanitized: 'http://test.com', title_sanitized: 'Test', viewport: {} },
    elements: [],
    redactions: [],
    privacy_report: { detected: 0, sensitive: 0, redacted: 0, verification: 'PASS', gate: 'PASS' }
  };

  await assert.rejects(
    async () => {
      await sendSanitizedContextToGate(leakyPayload, 'http://127.0.0.1:8080');
    },
    (err) => {
      assert.ok(err instanceof EgressGateViolationError);
      return true;
    }
  );
});
