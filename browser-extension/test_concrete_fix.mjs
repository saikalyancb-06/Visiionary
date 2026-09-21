import { scanTextForPII, sanitizeTextForPII, luhnCheck, verhoeffCheck } from './src/privacy/detector.js';
import { verifyPostRedactionPrivacy, collectTextEntriesForPrivacyScan } from './src/privacy/redactor.js';
import { validatePayloadSchema } from './src/egress/gate.js';
import { initVault, setSecret } from './src/vault/vault.js';

console.log('--- Running Concrete Bug Fix Regression Tests ---');
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

// Test 1: Payload containing a screenshot data_url with a base64 string containing six consecutive digits MUST NOT fail because of PIN_CODE.
const base64WithDigits = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP349201948201948201948201948201948201948201948201';
const payloadWithScreenshot = {
  session_id: 'test_base64_001',
  step: 1,
  instruction_sanitized: 'search for shoes',
  page: {
    url_sanitized: 'https://www.amazon.in',
    title_sanitized: 'Online Shopping site in India: Shop Online for Mobiles, Books, Watches, Shoes and More - Amazon.in'
  },
  screenshot: {
    format: 'jpeg',
    data_url: base64WithDigits
  },
  elements: [
    { id: 'twotabsearchtextbox', role: 'input', label: 'Search Amazon.in' }
  ],
  redactions: [],
  privacy_report: { detected: 0, sensitive: 0, redacted: 0, uncertain_redacted: 0, verification: 'PASS', gate: 'PASS' },
  history: []
};

const res1 = verifyPostRedactionPrivacy(payloadWithScreenshot);
assert(res1.safe === true, 'Test 1: Payload with base64 screenshot digits is NOT blocked by PIN_CODE');

// Test 2: Real PIN_CODE in page.title_sanitized MUST be redacted before egress, or if present raw MUST be flagged.
const rawTitle = 'Delivery to New Delhi 110001';
const sanitizedTitle = sanitizeTextForPII(rawTitle);
assert(sanitizedTitle === 'Delivery to New Delhi [REDACTED_PIN_CODE]', 'Test 2a: sanitizeTextForPII redacts PIN_CODE');

const unredactedPinPayload = {
  session_id: 'test_pin_002',
  step: 1,
  instruction_sanitized: 'Deliver order',
  page: {
    url_sanitized: 'https://www.amazon.in',
    title_sanitized: 'Delivery to New Delhi 110001'
  },
  elements: [],
  redactions: [],
  privacy_report: { detected: 0, sensitive: 0, redacted: 0, uncertain_redacted: 0, verification: 'PASS', gate: 'PASS' },
  history: []
};
const res2 = verifyPostRedactionPrivacy(unredactedPinPayload);
assert(res2.safe === false, 'Test 2b: Unredacted PIN_CODE in page.title_sanitized is caught by post-redaction verification');
assert(res2.violations.some(v => v.type === 'PIN_CODE' && v.field === 'page.title_sanitized'), 'Test 2c: Diagnostic logging correctly attributes field to page.title_sanitized');

// Test 3: Real phone/email/card/Aadhaar/Bank Account must still be blocked if it remains unredacted.
const unredactedPhonePayload = {
  session_id: 'test_phone_003',
  step: 1,
  instruction_sanitized: 'Call support at +91 98451 23091',
  page: {
    url_sanitized: 'https://example.com',
    title_sanitized: 'Support'
  },
  elements: [],
  redactions: [],
  privacy_report: { detected: 0, sensitive: 0, redacted: 0, uncertain_redacted: 0, verification: 'PASS', gate: 'PASS' },
  history: []
};
const res3 = verifyPostRedactionPrivacy(unredactedPhonePayload);
assert(res3.safe === false, 'Test 3a: Real unredacted phone number is blocked');
assert(res3.violations.some(v => v.type === 'PHONE' && v.field === 'instruction_sanitized'), 'Test 3b: Correctly identifies unredacted phone in instruction_sanitized');

// Test 3c: Bank account redaction
const rawBankText = 'Transfer to Account 982344120091';
const sanitizedBank = sanitizeTextForPII(rawBankText);
assert(sanitizedBank.includes('[REDACTED_BANK_ACCOUNT]'), 'Test 3c: sanitizeTextForPII redacts BANK_ACCOUNT');

// Test 4: Raw vault secret must still be blocked.
await initVault();
await setSecret('user.bank_pin', 'VaultSecret999!');

const vaultLeakingPayload = {
  session_id: 'test_vault_004',
  step: 1,
  instruction_sanitized: 'Enter VaultSecret999!',
  page: {
    url_sanitized: 'https://bank.example.com',
    title_sanitized: 'Bank Portal'
  },
  elements: [],
  redactions: [],
  privacy_report: { detected: 0, sensitive: 0, redacted: 0, uncertain_redacted: 0, verification: 'PASS', gate: 'PASS' },
  history: []
};
const res4 = verifyPostRedactionPrivacy(vaultLeakingPayload);
assert(res4.safe === false, 'Test 4: Raw vault secret is blocked across payload');

// Test 5: A normal public webpage containing prices, IDs, timestamps and base64 image data must pass if there is no actual PII.
const publicPagePayload = {
  session_id: 'test_public_005',
  step: 1,
  instruction_sanitized: 'search for black shirts',
  page: {
    url_sanitized: 'https://www.amazon.in/s?k=black+shirts',
    title_sanitized: 'Amazon.in : black shirts'
  },
  screenshot: {
    format: 'jpeg',
    data_url: 'data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
  },
  elements: [
    { id: 'twotabsearchtextbox', role: 'input', label: 'Search Amazon.in' },
    { id: 'nav-search-submit-button', role: 'button', label: 'Go' },
    { id: 'product_price_1', role: 'span', label: '₹1,499.00 (50% off) M.R.P: ₹2,999.00' },
    { id: 'rating_badge', role: 'span', label: '4.2 out of 5 stars (1,234 ratings)' }
  ],
  redactions: [],
  privacy_report: { detected: 0, sensitive: 0, redacted: 0, uncertain_redacted: 0, verification: 'PASS', gate: 'PASS' },
  history: []
};
const res5 = verifyPostRedactionPrivacy(publicPagePayload);
assert(res5.safe === true, 'Test 5: Public page with prices, ratings, and base64 screenshot passes verification cleanly');

console.log(`\nTests Completed: ${passed} Passed, ${failed} Failed`);
if (failed > 0) process.exit(1);
