import { chromium } from 'playwright';
import { scanTextForPII } from './src/privacy/detector.js';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

async function testAmazon() {
  const browser = await chromium.launch({ executablePath: CHROME_PATH, headless: true });
  const page = await browser.newPage();
  try {
    console.log('Navigating to amazon.in...');
    await page.goto('https://www.amazon.in', { waitUntil: 'domcontentloaded', timeout: 30000 });
    
    const extracted = await page.evaluate(() => {
      const nodes = document.querySelectorAll('button, input, select, textarea, a[href]');
      const items = [];
      nodes.forEach((el, idx) => {
        let raw = el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.getAttribute('title') || el.name || el.id || '';
        items.push({ id: el.id || ('el_' + idx), text: raw });
      });
      return items;
    });

    console.log('Extracted elements count:', extracted.length);
    for (const item of extracted) {
      const m = scanTextForPII(item.text);
      if (m.length > 0) {
        console.log(`PII MATCH on element ${item.id}:`, m, 'Text preview:', item.text.substring(0, 40));
      }
    }
  } finally {
    await browser.close();
  }
}
testAmazon().catch(e => console.error(e));
