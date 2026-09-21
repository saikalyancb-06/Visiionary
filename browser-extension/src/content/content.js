/**
 * Master Content Script with Real DOM Perception, Universal Privacy Shield & Action Execution
 */

import { extractDOMContext } from '../perception/capture.js';
import { executeAction } from '../agent/executor.js';

console.log('[PS26171] Privacy Agent Content Script initialized on page:', window.location.href);

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_DOM_SNAPSHOT') {
    try {
      const snapshot = extractDOMContext(document);
      sendResponse({
        success: true,
        url: window.location.href,
        title: document.title,
        elements: snapshot.elements,
        redactions: snapshot.redactions,
        sensitiveRegions: snapshot.sensitiveDOM
      });
    } catch (err) {
      console.error('[CONTENT SCRIPT] Error capturing DOM snapshot:', err);
      sendResponse({ success: false, error: err.message });
    }
    return true;
  }

  if (request.type === 'EXECUTE_ACTION') {
    (async () => {
      try {
        const result = await executeAction(request.action);
        sendResponse({ success: true, result });
      } catch (err) {
        console.error('[CONTENT SCRIPT] Action execution error:', err);
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }
});
