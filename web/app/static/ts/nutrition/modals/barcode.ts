/**
 * Barcode scanner for the food picker (Nutrition page + Dashboard).
 *
 * The camera is read in the browser only: frames are decoded locally with
 * the native BarcodeDetector or, where there is none (e.g. Safari, Firefox),
 * the self-hosted zxing WebAssembly reader. No frame is uploaded anywhere;
 * only the decoded digits go to NosiFit, which runs the same lookup as the
 * Telegram bot (catalog → cache → Open Food Facts).
 *
 * The camera stops as soon as a code is read, the modal closes or the page
 * is hidden. Typing the digits under the barcode always works as a fallback.
 */
import { NutritionAPI } from "../api.js";
import { describeError } from "../errors.js";
import { getLocale, nutrition_t } from "../../i18n/index.js";
import type { BarcodeLookupResult, BarcodePreview, NutritionUnit, Product } from "../types.js";
import { closeModal, onClick, openModal, setBusy, setModalError, setValue } from "./modal.js";

const SCANNER_ID = "modal-scan-barcode";
// Self-hosted copy of zxing-wasm (see the README in that folder).
const BARCODE_VENDOR = "/static/vendor/zxing-wasm-3.1.4/";
const NATIVE_FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e"];
const WASM_FORMATS = ["EAN13", "EAN8", "UPCA", "UPCE"];
const SCAN_INTERVAL_MS = 200;
const MAX_FRAME_SIDE = 1280;

const NUTRIENT_ROWS: Array<[keyof BarcodePreview, string, string]> = [
    ["kcal_per_100g", "fields.calories", "units.kcal"],
    ["protein_per_100g", "fields.protein", "units.grams"],
    ["fat_per_100g", "fields.fat", "units.grams"],
    ["carbs_per_100g", "fields.carbs", "units.grams"],
    ["sugar_per_100g", "fields.sugar", "units.grams"],
    ["fiber_per_100g", "fields.fiber", "units.grams"],
    ["saturated_fat_per_100g", "barcode.saturatedFat", "units.grams"],
    ["salt_per_100g", "barcode.salt", "units.grams"],
];

/** Values for "My product" when the scanned data must be completed by hand. */
export interface OwnProductPrefill {
    barcode: string;
    name?: string | null;
    brand?: string | null;
    unit?: NutritionUnit;
    values?: Partial<Record<keyof BarcodePreview, number | null>>;
}

export interface ScannerHandlers {
    /** A catalog product to select in the picker. */
    onProduct(product: Product): void | Promise<void>;
    /** Open "My product" prefilled with what is known. */
    onCreateOwn(prefill: OwnProductPrefill): void;
}

interface Detected {
    text: string;
    upce: boolean;
}

type Detect = (video: HTMLVideoElement) => Promise<Detected | null>;

interface BarcodeDetectorLike {
    detect(source: CanvasImageSource): Promise<Array<{ rawValue: string; format: string }>>;
}

interface BarcodeDetectorClass {
    new (options: { formats: string[] }): BarcodeDetectorLike;
    getSupportedFormats(): Promise<string[]>;
}

interface ZXingReadResult {
    text: string;
    format: string;
    isValid: boolean;
}

interface ZXingReader {
    prepareZXingModule(options: {
        overrides: { locateFile: (path: string, prefix: string) => string };
        fireImmediately: true;
    }): Promise<unknown>;
    readBarcodes(input: ImageData, options: Record<string, unknown>): Promise<ZXingReadResult[]>;
}

let handlers: ScannerHandlers | null = null;
let stream: MediaStream | null = null;
let scanTimer: number | undefined;
// Bumped on every open/close: async work of an older scan stops itself.
let session = 0;
let detectorPromise: Promise<Detect> | null = null;
let current: BarcodeLookupResult | null = null;

/* ---------- Barcode digits ---------- */

function checkDigit(body: string): number {
    let total = 0;
    for (let index = 0; index < body.length; index += 1) {
        const digit = Number(body[body.length - 1 - index]);
        total += digit * (index % 2 === 0 ? 3 : 1);
    }
    return (10 - (total % 10)) % 10;
}

/** Digits of a retail barcode with a valid check digit, else null. */
export function cleanBarcode(raw: string): string | null {
    const code = raw.replace(/[\s-]+/g, "");
    if (!/^\d+$/.test(code) || ![8, 12, 13, 14].includes(code.length)) return null;
    return checkDigit(code.slice(0, -1)) === Number(code[code.length - 1]) ? code : null;
}

/** UPC-E (8 digits) is a compressed UPC-A; the database knows the long form. */
function expandUpcE(code: string): string {
    if (!/^\d{8}$/.test(code)) return code;
    const [system, body, check] = [code[0], code.slice(1, 7), code[7]];
    const last = body[5];
    let middle: string;
    if ("012".includes(last)) middle = body.slice(0, 2) + last + "0000" + body.slice(2, 5);
    else if (last === "3") middle = body.slice(0, 3) + "00000" + body.slice(3, 5);
    else if (last === "4") middle = body.slice(0, 4) + "00000" + body[4];
    else middle = body.slice(0, 5) + "0000" + last;
    return system + middle + check;
}

/* ---------- Decoders ---------- */

async function nativeDetector(): Promise<Detect | null> {
    const Detector = (window as unknown as { BarcodeDetector?: BarcodeDetectorClass }).BarcodeDetector;
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
    if (!scope.ZXingWASM) await loadScript(BARCODE_VENDOR + "zxing-reader.iife.js");
    const reader = scope.ZXingWASM;
    if (!reader) throw new Error("decoder unavailable");

    // Never the library's CDN default: the WASM file is served by NosiFit.
    await reader.prepareZXingModule({
        overrides: {
            locateFile: (path, prefix) => (path.endsWith(".wasm") ? BARCODE_VENDOR + "zxing_reader.wasm" : prefix + path),
        },
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
        const results = await reader.readBarcodes(
            context.getImageData(0, 0, canvas.width, canvas.height),
            { formats: WASM_FORMATS, tryHarder: true, maxNumberOfSymbols: 1 },
        );
        const hit = results.find((result) => result.isValid);
        return hit ? { text: hit.text, upce: hit.format === "UPCE" } : null;
    };
}

function getDetector(): Promise<Detect> {
    if (!detectorPromise) {
        detectorPromise = (async () => (await nativeDetector()) ?? (await wasmDetector()))();
        detectorPromise.catch(() => {
            detectorPromise = null;
        });
    }
    return detectorPromise;
}

/* ---------- Camera ---------- */

function element<T extends HTMLElement>(id: string): T | null {
    return document.getElementById(id) as T | null;
}

function setStatus(key: string | null): void {
    const status = element<HTMLElement>("barcode-status");
    if (!status) return;
    status.textContent = key ? nutrition_t(key) : "";
    status.hidden = !key;
}

function stopCamera(): void {
    window.clearTimeout(scanTimer);
    scanTimer = undefined;
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
    const video = element<HTMLVideoElement>("barcode-video");
    if (video) {
        video.pause();
        video.srcObject = null;
    }
    const camera = element<HTMLElement>("barcode-camera");
    if (camera) camera.hidden = true;
}

async function startCamera(token: number): Promise<void> {
    if (!window.isSecureContext) {
        setStatus("barcode.insecure");
        return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
        setStatus("barcode.cameraUnavailable");
        return;
    }

    setStatus("barcode.starting");
    let media: MediaStream;
    try {
        media = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
        });
    } catch (error) {
        if (token !== session) return;
        const name = error instanceof DOMException ? error.name : "";
        setStatus(name === "NotAllowedError" || name === "SecurityError" ? "barcode.cameraDenied" : "barcode.cameraUnavailable");
        return;
    }

    if (token !== session) {
        // Closed while the permission prompt was open.
        media.getTracks().forEach((track) => track.stop());
        return;
    }

    stream = media;
    const video = element<HTMLVideoElement>("barcode-video");
    const camera = element<HTMLElement>("barcode-camera");
    if (!video || !camera) {
        stopCamera();
        return;
    }
    video.srcObject = media;
    camera.hidden = false;
    await video.play().catch(() => undefined);

    let detect: Detect;
    try {
        detect = await getDetector();
    } catch {
        if (token !== session) return;
        stopCamera();
        setStatus("barcode.decoderFailed");
        return;
    }
    if (token !== session) return;
    setStatus("barcode.scanning");

    const tick = async (): Promise<void> => {
        if (token !== session || !stream) return;
        try {
            const hit = await detect(video);
            const code = hit ? cleanBarcode(hit.upce ? expandUpcE(hit.text) : hit.text) : null;
            if (code && token === session) {
                stopCamera();
                navigator.vibrate?.(60);
                await lookup(code, token);
                return;
            }
        } catch {
            // A frame that cannot be read: try the next one.
        }
        if (token === session && stream) scanTimer = window.setTimeout(tick, SCAN_INTERVAL_MS);
    };
    void tick();
}

/* ---------- Result ---------- */

function formatValue(value: number | null | undefined, unitKey: string): string {
    if (value === null || value === undefined) return "—";
    const rounded = Number.isInteger(value) ? String(value) : value.toFixed(value < 1 ? 2 : 1);
    return `${rounded} ${nutrition_t(unitKey)}`;
}

function textElement(tag: string, className: string, text: string): HTMLElement {
    const node = document.createElement(tag);
    node.className = className;
    node.textContent = text;
    return node;
}

function fieldList(fields: string[]): string {
    return fields.map((field) => nutrition_t(`barcode.fields.${field}`)).join(", ");
}

function renderValues(values: Record<string, number | null | undefined>, basisKey: string): HTMLElement {
    const wrap = document.createElement("div");
    wrap.className = "nf-scan-values";
    wrap.appendChild(textElement("span", "nf-scan-basis", nutrition_t(basisKey)));
    const list = document.createElement("dl");
    NUTRIENT_ROWS.forEach(([field, labelKey, unitKey]) => {
        const row = document.createElement("div");
        row.append(
            textElement("dt", "", nutrition_t(labelKey)),
            textElement("dd", values[field] === null || values[field] === undefined ? "is-unknown" : "", formatValue(values[field], unitKey)),
        );
        list.appendChild(row);
    });
    wrap.appendChild(list);
    return wrap;
}

function renderResult(result: BarcodeLookupResult): void {
    const container = element<HTMLElement>("barcode-result");
    const confirm = element<HTMLButtonElement>("barcode-confirm");
    const createOwn = element<HTMLButtonElement>("barcode-create-own");
    const rescan = element<HTMLButtonElement>("barcode-rescan");
    if (!container || !confirm || !createOwn || !rescan) return;

    container.innerHTML = "";
    container.hidden = false;
    rescan.hidden = false;
    confirm.hidden = true;
    createOwn.hidden = true;
    setStatus(null);

    const header = document.createElement("div");
    header.className = "nf-scan-product";
    const code = textElement("span", "nf-scan-code", result.barcode);

    if (result.product) {
        const product = result.product;
        header.append(
            textElement("strong", "nf-scan-name", product.name),
            textElement("span", "nf-scan-brand", product.brand ?? ""),
            code,
        );
        container.append(
            header,
            textElement("p", "nf-scan-source", nutrition_t(product.is_own ? "barcode.ownProduct" : "barcode.inCatalog")),
            renderValues(
                product as unknown as Record<string, number | null>,
                product.default_unit === "ml" ? "barcode.perBasis100ml" : "barcode.perBasis100g",
            ),
        );
        confirm.textContent = nutrition_t("barcode.select");
        confirm.hidden = false;
        return;
    }

    const preview = result.preview;
    if (!preview) {
        header.append(code);
        container.append(header, textElement("p", "nf-scan-note", nutrition_t("barcode.notFound")));
        createOwn.textContent = nutrition_t("barcode.createOwn");
        createOwn.hidden = false;
        return;
    }

    header.append(
        textElement("strong", "nf-scan-name", preview.name ?? "—"),
        textElement("span", "nf-scan-brand", preview.brand ?? ""),
        code,
    );
    container.append(
        header,
        textElement("p", "nf-scan-source is-unverified", nutrition_t("barcode.external")),
        renderValues(
            preview as unknown as Record<string, number | null>,
            preview.basis === "100ml" ? "barcode.perBasis100ml" : "barcode.perBasis100g",
        ),
    );

    const notes: string[] = preview.warnings
        .map((warning) => nutrition_t(`barcode.warnings.${warning}`))
        .filter((text) => !text.startsWith("barcode."));
    if (result.stale) notes.push(nutrition_t("barcode.stale"));
    if (notes.length) {
        const list = document.createElement("ul");
        list.className = "nf-scan-warnings";
        notes.forEach((note) => list.appendChild(textElement("li", "", note)));
        container.appendChild(list);
    }

    const problems: string[] = [];
    if (preview.missing.length) problems.push(nutrition_t("barcode.missing", { fields: fieldList(preview.missing) }));
    const invalid = Object.keys(preview.invalid);
    if (invalid.length) problems.push(nutrition_t("barcode.invalid", { fields: fieldList(invalid) }));
    if (!preview.importable) problems.push(nutrition_t("barcode.notImportable"));
    problems.forEach((problem) => container.appendChild(textElement("p", "nf-scan-problem", problem)));

    container.appendChild(textElement("p", "nf-scan-attribution", nutrition_t("barcode.attribution")));

    confirm.textContent = nutrition_t("barcode.addProduct");
    confirm.hidden = !preview.importable;
    createOwn.textContent = nutrition_t(preview.importable ? "barcode.enterFromLabel" : "barcode.createOwn");
    createOwn.hidden = false;
}

async function lookup(code: string, token: number): Promise<void> {
    setStatus("barcode.searching");
    setModalError(SCANNER_ID, null);
    setValue("barcode-manual", code);
    try {
        const result = await NutritionAPI.lookupBarcode(code, getLocale());
        if (token !== session) return;
        current = result;
        renderResult(result);
    } catch (error) {
        if (token !== session) return;
        setStatus(null);
        setModalError(SCANNER_ID, describeError(error));
        const rescan = element<HTMLButtonElement>("barcode-rescan");
        if (rescan) rescan.hidden = false;
    }
}

function resetResult(): void {
    current = null;
    const container = element<HTMLElement>("barcode-result");
    if (container) {
        container.innerHTML = "";
        container.hidden = true;
    }
    ["barcode-confirm", "barcode-create-own", "barcode-rescan"].forEach((id) => {
        const button = element<HTMLButtonElement>(id);
        if (button) button.hidden = true;
    });
    setModalError(SCANNER_ID, null);
}

function prefillFrom(result: BarcodeLookupResult): OwnProductPrefill {
    const preview = result.preview;
    if (!preview) return { barcode: result.barcode };
    const values: OwnProductPrefill["values"] = {};
    NUTRIENT_ROWS.forEach(([field]) => {
        const value = preview[field];
        // Only values that passed validation; the rest stays for the label.
        if (typeof value === "number" && !(field in preview.invalid)) values[field] = value;
    });
    return {
        barcode: result.barcode,
        name: preview.name,
        brand: preview.brand,
        unit: preview.default_unit,
        values,
    };
}

/* ---------- Public API ---------- */

export function openBarcodeScanner(): void {
    session += 1;
    stopCamera();
    resetResult();
    setValue("barcode-manual", "");
    setStatus("barcode.hint");
    openModal(SCANNER_ID, "#barcode-manual");
    void startCamera(session);
}

export function setupBarcodeScanner(scannerHandlers: ScannerHandlers): void {
    handlers = scannerHandlers;
    const modal = element<HTMLElement>(SCANNER_ID);
    if (!modal) return;

    onClick(["open-barcode-scanner"], () => openBarcodeScanner());
    onClick(["close-scan-barcode"], () => closeModal(SCANNER_ID));

    modal.addEventListener("nf-modal:closed", () => {
        session += 1;
        stopCamera();
    });

    // Never keep the camera on in a background tab.
    document.addEventListener("visibilitychange", () => {
        if (document.hidden && stream) {
            session += 1;
            stopCamera();
            setStatus(null);
            const rescan = element<HTMLButtonElement>("barcode-rescan");
            if (rescan) rescan.hidden = false;
        }
    });

    onClick(["barcode-rescan"], () => {
        session += 1;
        resetResult();
        setStatus("barcode.hint");
        void startCamera(session);
    });

    element<HTMLFormElement>("barcode-manual-form")?.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = element<HTMLInputElement>("barcode-manual");
        const code = cleanBarcode(input?.value ?? "");
        if (!code) {
            input?.setAttribute("aria-invalid", "true");
            setModalError(SCANNER_ID, nutrition_t("errors.invalid_barcode"));
            return;
        }
        input?.removeAttribute("aria-invalid");
        session += 1;
        stopCamera();
        resetResult();
        void lookup(code, session);
    });

    const confirm = element<HTMLButtonElement>("barcode-confirm");
    confirm?.addEventListener("click", async () => {
        const result = current;
        if (!result || !handlers) return;
        if (result.product) {
            closeModal(SCANNER_ID);
            await handlers.onProduct(result.product);
            return;
        }
        if (!result.preview?.importable) return;

        setBusy(confirm, true);
        setModalError(SCANNER_ID, null);
        try {
            const { product } = await NutritionAPI.importBarcode(result.barcode, getLocale());
            closeModal(SCANNER_ID);
            await handlers.onProduct(product);
        } catch (error) {
            setModalError(SCANNER_ID, describeError(error));
        } finally {
            setBusy(confirm, false);
        }
    });

    onClick(["barcode-create-own"], () => {
        const result = current;
        if (!result || !handlers) return;
        closeModal(SCANNER_ID);
        handlers.onCreateOwn(prefillFrom(result));
    });
}
