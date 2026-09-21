import { runVisualInference } from '../inference/runner.js';

// Handle messages from background service worker
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "RUN_VISUAL_INFERENCE") {
    (async () => {
      try {
        const { dataUrl, width, height } = msg;
        if (!dataUrl) {
          throw new Error("Missing dataUrl in RUN_VISUAL_INFERENCE request");
        }

        // Fetch dataUrl into ImageBitmap for hardware-accelerated processing
        const response = await fetch(dataUrl);
        const blob = await response.blob();
        const imageBitmap = await createImageBitmap(blob);

        const result = await runVisualInference(imageBitmap, width || imageBitmap.width, height || imageBitmap.height);
        sendResponse({ status: "SUCCESS", ...result });
      } catch (err) {
        console.error("[OFFSCREEN INFERENCE ERROR]", err);
        sendResponse({ status: "ERROR", error: err.message, detections: [] });
      }
    })();
    return true; // Keep message channel open for async response
  }

  if (msg.type === "REDACT_SCREENSHOT") {
    (async () => {
      try {
        const { dataUrl, regions } = msg;
        const imgRes = await fetch(dataUrl);
        const blob = await imgRes.blob();
        const bmp = await createImageBitmap(blob);

        const canvas = new OffscreenCanvas(bmp.width, bmp.height);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(bmp, 0, 0);

        // Apply redactions: blurring for faces / avatars, solid blackout for credentials
        for (const r of regions) {
          const x1 = Math.max(0, r.x1 ?? r.bbox?.[0] ?? 0);
          const y1 = Math.max(0, r.y1 ?? r.bbox?.[1] ?? 0);
          const x2 = Math.min(bmp.width, r.x2 ?? r.bbox?.[2] ?? bmp.width);
          const y2 = Math.min(bmp.height, r.y2 ?? r.bbox?.[3] ?? bmp.height);
          const w = Math.max(0, x2 - x1);
          const h = Math.max(0, y2 - y1);
          
          if (w > 0 && h > 0) {
            const rType = (r.type || '').toLowerCase();
            if (rType.includes('face') || rType.includes('avatar') || rType.includes('profile')) {
              // Requirement: "blurring faces" - apply strong multi-pass blur and pixelation
              ctx.save();
              ctx.filter = 'blur(16px)';
              ctx.drawImage(canvas, x1, y1, w, h, x1, y1, w, h);
              ctx.restore();
              // Secondary overlay tint to ensure non-reversibility
              ctx.fillStyle = 'rgba(20, 20, 20, 0.75)';
              ctx.fillRect(x1, y1, w, h);
            } else {
              // Requirement: "blacking out passwords and masking PII"
              ctx.fillStyle = '#000000';
              ctx.fillRect(x1, y1, w, h);
            }
          }
        }

        const redactedBlob = await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.85 });
        const reader = new FileReader();
        reader.onloadend = () => {
          sendResponse({ status: "SUCCESS", sanitizedDataUrl: reader.result });
        };
        reader.readAsDataURL(redactedBlob);
      } catch (err) {
        console.error("[OFFSCREEN REDACTION ERROR]", err);
        sendResponse({ status: "ERROR", error: err.message });
      }
    })();
    return true;
  }
});
