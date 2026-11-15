/**
 * Reads a barcode from a camera frame with the browser's own BarcodeDetector
 * or, where there is none (Safari, Firefox), the self-hosted zxing
 * WebAssembly reader the classic pages use. No frame leaves the browser.
 */

// Resolved at run time from this module's URL (…/app/assets/), so it shares the versioned static
// path. The URL goes through a variable: the bundler would try to pack a literal pair as an asset.
const moduleUrl: string = import.meta.url;
const VENDOR = new URL("../../vendor/zxing-wasm-3.1.4/", moduleUrl).href;
const NATIVE_FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e"];
const WASM_FORMATS = ["EAN13", "EAN8", "UPCA", "UPCE"];
const MAX_FRAME_SIDE = 1280;

export interface Detected {
  text: string;
  upce: boolean;
}

export type Detect = (video: HTMLVideoElement) => Promise<Detected | null>;

interface NativeDetector {
  detect(source: CanvasImageSource): Promise<Array<{ rawValue: string; format: string }>>;
}

interface NativeDetectorClass {
  new (options: { formats: string[] }): NativeDetector;
  getSupportedFormats(): Promise<string[]>;
}

interface ZXingReader {
  prepareZXingModule(options: { overrides: { locateFile: (path: string, prefix: string) => string }; fireImmediately: true }): Promise<unknown>;
  readBarcodes(input: ImageData, options: Record<string, unknown>): Promise<Array<{ text: string; format: string; isValid: boolean }>>;
}

async function nativeDetector(): Promise<Detect | null> {
  const Detector = (window as unknown as { BarcodeDetector?: NativeDetectorClass }).BarcodeDetector;
  if (!Detector) return null;
  try {
    const supported = await Detector.getSupportedFormats();
    const formats = NATIVE_FORMATS.filter((format) => supported.includes(format));
    if (!formats.includes("ean_13")) return null;
    const detector = new Detector({ formats });
    return async (video) => {
      const [hit] = await detector.detect(video);
      return hit ? { text: hit.rawValue, upce: hit.format === "upc_e" } : null;
    };
  } catch {
    return null;
  }
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("decoder script failed to load"));
    document.head.appendChild(script);
  });
}

async function wasmDetector(): Promise<Detect> {
  const scope = window as unknown as { ZXingWASM?: ZXingReader };
  if (!scope.ZXingWASM) await loadScript(`${VENDOR}zxing-reader.iife.js`);
  const reader = scope.ZXingWASM;
  if (!reader) throw new Error("decoder unavailable");

  // Never the library's CDN default: the WASM file is served by NosiFit.
  await reader.prepareZXingModule({
    overrides: { locateFile: (path, prefix) => (path.endsWith(".wasm") ? `${VENDOR}zxing_reader.wasm` : prefix + path) },
    fireImmediately: true,
  });

  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("canvas unavailable");

  return async (video) => {
    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) return null;
    const scale = Math.min(1, MAX_FRAME_SIDE / Math.max(width, height));
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const results = await reader.readBarcodes(context.getImageData(0, 0, canvas.width, canvas.height), {
      formats: WASM_FORMATS,
      tryHarder: true,
      maxNumberOfSymbols: 1,
    });
    const hit = results.find((result) => result.isValid);
    return hit ? { text: hit.text, upce: hit.format === "UPCE" } : null;
  };
}

let detectorPromise: Promise<Detect> | null = null;

export function getDetector(): Promise<Detect> {
  if (!detectorPromise) {
    detectorPromise = (async () => (await nativeDetector()) ?? (await wasmDetector()))();
    detectorPromise.catch(() => {
      detectorPromise = null;
    });
  }
  return detectorPromise;
}
