/**
 * Real On-Device Visual Inference Runner using ONNX Runtime Web
 * Preprocesses screenshot image into [1, 3, 320, 320] float32 tensor,
 * runs model inference, and decodes bounding boxes & classes with confidence scores.
 */

export const PII_CLASSES = [
  "PERSON_NAME",
  "EMAIL",
  "PHONE",
  "ADDRESS",
  "PIN_CODE",
  "DATE_OF_BIRTH",
  "AADHAAR",
  "PAN",
  "PASSPORT",
  "VOTER_ID",
  "DRIVING_LICENSE",
  "BANK_ACCOUNT",
  "IFSC",
  "UPI_ID",
  "CARD_NUMBER",
  "PASSWORD",
  "OTP",
  "GSTIN",
  "FACE",
  "QR_BARCODE"
];

let ortSession = null;

export async function initInferenceSession(modelPath = null) {
  if (ortSession) return ortSession;

  const ort = window.ort;
  if (!ort) {
    throw new Error('ONNX Runtime Web (window.ort) is not loaded.');
  }

  // Configure WASM paths
  const ortWasmPath = chrome.runtime.getURL('public/ort/');
  ort.env.wasm.wasmPaths = ortWasmPath;
  ort.env.wasm.numThreads = 2;

  const resolvedModelUrl = modelPath || chrome.runtime.getURL('public/models/detector.onnx');

  try {
    // Try WebGPU first if supported
    ortSession = await ort.InferenceSession.create(resolvedModelUrl, {
      executionProviders: ['webgpu', 'wasm'],
      graphOptimizationLevel: 'all'
    });
    console.log('[INFERENCE] Loaded ONNX model with provider:', ortSession.executionProviders);
  } catch (gpuErr) {
    console.warn('[INFERENCE] WebGPU init failed, falling back to WASM:', gpuErr);
    ortSession = await ort.InferenceSession.create(resolvedModelUrl, {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all'
    });
    console.log('[INFERENCE] Loaded ONNX model with WASM fallback');
  }

  return ortSession;
}

/**
 * Preprocesses an image bitmap / canvas into a 1x3x320x320 float32 planar RGB tensor.
 */
export function preprocessImage(imageSource, targetW = 320, targetH = 320) {
  const canvas = new OffscreenCanvas(targetW, targetH);
  const ctx = canvas.getContext('2d');
  ctx.drawImage(imageSource, 0, 0, targetW, targetH);
  const imageData = ctx.getImageData(0, 0, targetW, targetH);
  const { data } = imageData; // RGBA uint8 array

  const floatData = new Float32Array(3 * targetW * targetH);
  const planeSize = targetW * targetH;

  for (let i = 0; i < planeSize; i++) {
    const r = data[i * 4] / 255.0;
    const g = data[i * 4 + 1] / 255.0;
    const b = data[i * 4 + 2] / 255.0;

    floatData[i] = r;
    floatData[planeSize + i] = g;
    floatData[2 * planeSize + i] = b;
  }

  const ort = window.ort;
  return new ort.Tensor('float32', floatData, [1, 3, targetH, targetW]);
}

/**
 * Executes real visual inference on an ImageBitmap, HTMLImageElement, or Canvas.
 * Returns array of detections: { class, confidence, x1, y1, x2, y2 }
 */
export async function runVisualInference(imageSource, originalWidth, originalHeight, confThreshold = 0.25) {
  const session = await initInferenceSession();
  const inputTensor = preprocessImage(imageSource, 320, 320);

  const feeds = { input_image: inputTensor };
  const startTime = performance.now();
  const results = await session.run(feeds);
  const inferenceMs = performance.now() - startTime;

  // Expected outputs: 'boxes' [1, 4] and 'logits' [1, 20]
  const boxesTensor = results.boxes || results.bboxes;
  const logitsTensor = results.logits;

  if (!boxesTensor || !logitsTensor) {
    throw new Error('ONNX inference failed: expected box and logit outputs not found.');
  }

  const boxData = boxesTensor.data;
  const logitData = logitsTensor.data;

  // Compute softmax probabilities over 20 classes
  const numClasses = PII_CLASSES.length;
  let maxLogit = -Infinity;
  for (let c = 0; c < numClasses; c++) {
    if (logitData[c] > maxLogit) maxLogit = logitData[c];
  }

  let expSum = 0;
  const expVals = new Float32Array(numClasses);
  for (let c = 0; c < numClasses; c++) {
    expVals[c] = Math.exp(logitData[c] - maxLogit);
    expSum += expVals[c];
  }

  let bestClassIdx = 0;
  let bestProb = 0;
  for (let c = 0; c < numClasses; c++) {
    const prob = expVals[c] / expSum;
    if (prob > bestProb) {
      bestProb = prob;
      bestClassIdx = c;
    }
  }

  const detections = [];
  // Decode bounding box: normalized [ymin, xmin, ymax, xmax] or [x1, y1, x2, y2]
  // Box head outputs sigmoid [0, 1]
  const rawX1 = Math.min(boxData[0], boxData[2]);
  const rawY1 = Math.min(boxData[1], boxData[3]);
  const rawX2 = Math.max(boxData[0], boxData[2]);
  const rawY2 = Math.max(boxData[1], boxData[3]);

  const x1 = Math.round(rawX1 * originalWidth);
  const y1 = Math.round(rawY1 * originalHeight);
  const x2 = Math.round(rawX2 * originalWidth);
  const y2 = Math.round(rawY2 * originalHeight);

  if (bestProb >= confThreshold && (x2 - x1 > 5) && (y2 - y1 > 5)) {
    detections.push({
      class: PII_CLASSES[bestClassIdx] || "SENSITIVE_REGION",
      class_index: bestClassIdx,
      confidence: parseFloat(bestProb.toFixed(4)),
      x1,
      y1,
      x2,
      y2,
      latency_ms: parseFloat(inferenceMs.toFixed(2))
    });
  }

  return {
    detections,
    latency_ms: parseFloat(inferenceMs.toFixed(2))
  };
}
