/**
 * Build script for PS26171 Chrome Extension
 * Prepares bundle and assets: onnxruntime-web WASM/JS binaries and ONNX model
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ROOT_DIR = path.resolve(__dirname, '..');
const EXT_DIR = __dirname;
const PUBLIC_DIR = path.join(EXT_DIR, 'public');
const ORT_DIST = path.join(EXT_DIR, 'node_modules', 'onnxruntime-web', 'dist');
const MODEL_SRC = path.join(ROOT_DIR, 'models', 'onnx', 'regularized_visual_pii_detector.onnx');
const PUBLIC_MODELS_DIR = path.join(PUBLIC_DIR, 'models');
const PUBLIC_ORT_DIR = path.join(PUBLIC_DIR, 'ort');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function copyFile(src, dest) {
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`[BUILD] Copied: ${path.basename(src)} -> ${dest}`);
  } else {
    console.warn(`[BUILD] Source not found: ${src}`);
  }
}

console.log('[BUILD] Starting extension asset compilation...');

ensureDir(PUBLIC_DIR);
ensureDir(PUBLIC_MODELS_DIR);
ensureDir(PUBLIC_ORT_DIR);

// 1. Copy ONNX model
if (fs.existsSync(MODEL_SRC)) {
  copyFile(MODEL_SRC, path.join(PUBLIC_MODELS_DIR, 'detector.onnx'));
} else {
  console.warn(`[BUILD] ONNX model source not found at: ${MODEL_SRC}`);
}

// 2. Copy ONNX Runtime Web bundle and WASM files
if (fs.existsSync(ORT_DIST)) {
  const ortFiles = [
    'ort.all.min.js',
    'ort.webgpu.min.js',
    'ort.wasm.min.js',
    'ort-wasm-simd-threaded.wasm',
    'ort-wasm-simd-threaded.mjs',
    'ort-wasm-simd-threaded.jsep.wasm',
    'ort-wasm-simd-threaded.jsep.mjs'
  ];

  for (const file of ortFiles) {
    const srcPath = path.join(ORT_DIST, file);
    if (fs.existsSync(srcPath)) {
      copyFile(srcPath, path.join(PUBLIC_ORT_DIR, file));
    }
  }
} else {
  console.warn('[BUILD] onnxruntime-web dist folder not found. Run npm install first.');
}

console.log('[BUILD] Chrome Extension assets built successfully.');
