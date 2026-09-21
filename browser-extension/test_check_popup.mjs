import { chromium } from 'playwright';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const extPath = 'd:\\webman\\browser-extension';

async function run() {
  const ctx = await chromium.launchPersistentContext('', {
    executablePath: CHROME_PATH,
    headless: true,
    args: [
      `--disable-extensions-except=${extPath}`,
      `--load-extension=${extPath}`
    ]
  });

  let [backgroundPage] = ctx.serviceWorkers();
  if (!backgroundPage) {
    backgroundPage = await ctx.waitForEvent('serviceworker');
  }
  const extId = backgroundPage.url().split('/')[2];
  console.log('Extension ID:', extId);

  const popupPage = await ctx.newPage();
  await popupPage.goto(`chrome-extension://${extId}/src/ui/popup.html`);
  const text = await popupPage.innerText('body');
  console.log('Popup Body Text:\n' + text);

  await ctx.close();
  console.log('SUCCESS: Popup loaded in Chrome!');
}

run().catch(console.error);
