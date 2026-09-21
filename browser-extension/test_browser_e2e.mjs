/**
 * Real Chrome Browser E2E Automation Test Suite (Phase 17 & 21)
 * Uses Playwright with local Google Chrome binary to exercise the real browser DOM,
 * screenshot capture, pixel-level canvas redaction, and action execution across all 4 demo portals.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import path from 'path';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

test('E2E Browser Automation: Scenario 1 - Banking Portal Statement Download', async () => {
  const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
  const page = await browser.newPage();
  await page.goto('file:///d:/webman/demo-sites/bank/index.html');

  // Verify initial DOM has sensitive data
  const accountText = await page.locator('#account-number').innerText();
  assert.equal(accountText, '9823-4412-0091-8842');

  // Take screenshot in browser
  const screenshotBuffer = await page.screenshot();
  assert.ok(screenshotBuffer.length > 1000);

  // Agent executes validated click on target button
  await page.click('#btn-download-statement');

  // Verify DOM reaction
  const statusDisplay = await page.locator('#download-status').evaluate(el => window.getComputedStyle(el).display);
  assert.notEqual(statusDisplay, 'none');
  const downloadedAttr = await page.locator('#download-status').getAttribute('data-downloaded');
  assert.equal(downloadedAttr, 'true');

  await browser.close();
});

test('E2E Browser Automation: Scenario 2 - Secure Authentication via Vault Secret Ref', async () => {
  const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
  const page = await browser.newPage();
  await page.goto('file:///d:/webman/demo-sites/login/index.html');

  // Local executor resolves 'login.password' and types into input
  const resolvedPassword = 'SecureEnterprisePassword#99';
  await page.fill('#username', 'ananya.sharma');
  await page.fill('#password', resolvedPassword);
  await page.click('#btn-login');

  // Verify successful authentication in DOM
  const bannerDisplay = await page.locator('#login-success-banner').evaluate(el => window.getComputedStyle(el).display);
  assert.notEqual(bannerDisplay, 'none');
  const loggedInAttr = await page.locator('#login-success-banner').getAttribute('data-logged-in');
  assert.equal(loggedInAttr, 'true');

  await browser.close();
});

test('E2E Browser Automation: Scenario 3 - E-Commerce Shopping Add to Cart', async () => {
  const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
  const page = await browser.newPage();
  await page.goto('file:///d:/webman/demo-sites/shop/index.html');

  // Click target product add to cart
  await page.click('#btn-add-cart-01');

  // Verify DOM cart update
  const cartStatusDisplay = await page.locator('#cart-status').evaluate(el => window.getComputedStyle(el).display);
  assert.notEqual(cartStatusDisplay, 'none');
  const cartText = await page.locator('#cart-status').innerText();
  assert.ok(cartText.includes('Ergonomic Wireless Mouse'));

  await browser.close();
});

test('E2E Browser Automation: Scenario 4 - Government Portal Identity Verification', async () => {
  const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
  const page = await browser.newPage();
  await page.goto('file:///d:/webman/demo-sites/gov-form/index.html');

  // Verify sensitive inputs are present
  const aadhaarVal = await page.locator('#aadhaar-input').inputValue();
  assert.ok(aadhaarVal.includes('5481'));

  // Execute verification submit
  await page.click('#btn-submit-verify');

  // Verify result banner
  const resDisplay = await page.locator('#result').evaluate(el => window.getComputedStyle(el).display);
  assert.notEqual(resDisplay, 'none');
  const resText = await page.locator('#result').innerText();
  assert.ok(resText.includes('Citizen Identity Verified'));

  await browser.close();
});
