import { scanTextForPII, sanitizeTextForPII } from './src/privacy/detector.js';
import { validatePayloadSchema } from './src/egress/gate.js';
import { verifyPostRedactionPrivacy } from './src/privacy/redactor.js';
import { containsVaultSecret } from './src/vault/vault.js';

console.log('--- Starting PII Pipeline Generic Regression Tests ---');
let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`[PASS] ${message}`);
    passed++;
  } else {
    console.error(`[FAIL] ${message}`);
    failed++;
  }
}

// 1. Genuine PII Detection & Sanitization
const testEmail = 'Contact user at test.user@example.com for support.';
const sanitizedEmail = sanitizeTextForPII(testEmail);
assert(sanitizedEmail.includes('[REDACTED_EMAIL]'), 'Email is replaced with [REDACTED_EMAIL]');
assert(!sanitizedEmail.includes('test.user@example.com'), 'Raw email is completely removed');

const testPhone = 'Call +1-555-123-4567 or +91 9876543210 immediately.';
const sanitizedPhone = sanitizeTextForPII(testPhone);
assert(sanitizedPhone.includes('[REDACTED_PHONE]'), 'US & Indian Phone numbers replaced with [REDACTED_PHONE]');
assert(!sanitizedPhone.includes('9876543210'), 'Raw phone number is completely removed');

// 2. Non-Sensitive Content (False Positive Rejection)
const publicPrices = 'Price: $149.99 or ₹1,507.00. SKU: 849204810295. Order #12345.';
const piiInPrices = scanTextForPII(publicPrices);
assert(piiInPrices.length === 0, 'Prices, order IDs, and normal numeric SKUs produce zero false positives');

const publicNav = 'Hello, sign in Account & Lists nav-link-accountList';
const piiInNav = scanTextForPII(publicNav);
assert(piiInNav.length === 0, 'Navigation account identifiers produce zero false positives');

// 3. Algorithmic Checksum Validation (Luhn Check)
// Valid fake Visa test number: 4532015112830366 (Luhn passes)
const validCard = 'Payment card: 4532-0151-1283-0366';
const cardMatches = scanTextForPII(validCard);
assert(cardMatches.some(m => m.type === 'CARD_NUMBER'), 'Valid Luhn card number is flagged as PII');

// Invalid 16-digit number (Luhn fails)
const invalidCard = 'Random 16-digit tracking: 4532-0151-1283-0367';
const invalidCardMatches = scanTextForPII(invalidCard);
assert(!invalidCardMatches.some(m => m.type === 'CARD_NUMBER'), 'Invalid Luhn 16-digit number is rejected by algorithmic checksum');

// 4. Safe Diagnostic Metadata (Zero Raw Leaks)
cardMatches.forEach(m => {
  assert(m.fingerprint && m.fingerprint.startsWith('fp_'), 'Detection metadata contains non-reversible fingerprint');
  assert(!JSON.stringify(m).includes('4532'), 'Metadata never leaks raw card number');
});

// 5. Post-Redaction Privacy Verification & Schema Validation
// A: Valid sanitized payload
const cleanPayload = {
  session_id: 'test_session_123',
  step: 1,
  instruction_sanitized: 'Search for running shoes under $50',
  page: {
    url_sanitized: 'https://example.com/search?q=shoes',
    title: 'Running Shoes'
  },
  elements: [
    { id: 1, tag: 'input', label: 'Search' },
    { id: 2, tag: 'span', label: 'Price: $49.99' },
    { id: 3, tag: 'div', label: 'User: [REDACTED_EMAIL]' }
  ],
  sensitiveRegions: [
    { type: 'EMAIL', selector: '#user', text: '[REDACTED_EMAIL]' }
  ],
  privacy_report: {
    detected: 1,
    redacted: 1
  }
};

let schemaValid = false;
try {
  schemaValid = validatePayloadSchema(cleanPayload);
} catch (e) {
  schemaValid = false;
}
assert(schemaValid === true, 'Schema validation passes for valid SanitizedContextPackage');

const cleanVerification = verifyPostRedactionPrivacy(cleanPayload);
assert(cleanVerification.safe === true, 'Post-sanitization verifier PASSES cleanly sanitized payload');

// B: Dirty payload with unredacted PII (Must fail closed)
const dirtyPayload = {
  session_id: 'test_session_123',
  step: 1,
  instruction_sanitized: 'Pay with card',
  page: {
    url_sanitized: 'https://example.com/checkout',
    title: 'Checkout'
  },
  elements: [
    { id: 1, tag: 'input', label: 'Credit Card: 4532-0151-1283-0366' }
  ],
  privacy_report: {
    detected: 0,
    redacted: 0
  }
};

const dirtyVerification = verifyPostRedactionPrivacy(dirtyPayload);
assert(dirtyVerification.safe === false, 'Post-sanitization verifier FAILS on unredacted PII');
assert(dirtyVerification.violations.length > 0, 'Violations list captures detected unredacted item');
assert(dirtyVerification.violations[0].fingerprint.startsWith('fp_'), 'Violation metadata provides zero-leak fingerprint');

console.log(`\nRegression Suite Complete: ${passed} Passed, ${failed} Failed`);
if (failed > 0) process.exit(1);
