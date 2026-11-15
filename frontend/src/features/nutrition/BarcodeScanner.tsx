import { useEffect, useRef, useState } from "react";
import type { BarcodeLookup, Product } from "../../api/types";
import { useImportBarcode } from "../../api/mutations";
import { cleanBarcode, expandUpcE } from "../../domain/barcode";
import { useT } from "../../i18n";
import type { TKey } from "../../i18n/en";
import { api } from "../../lib/api";
import { bootstrap } from "../../lib/bootstrap";
import { num } from "../../lib/format";
import { Button } from "../../ui/Button";
import { Spinner } from "../../ui/Feedback";
import { TextField } from "../../ui/Field";
import { getDetector } from "./barcodeDetector";

const SCAN_INTERVAL_MS = 200;

type CameraState = "starting" | "scanning" | "denied" | "unavailable" | "off";

const CAMERA_TEXT: Record<Exclude<CameraState, "scanning" | "off">, TKey> = {
  starting: "scan.starting",
  denied: "scan.denied",
  unavailable: "scan.unavailable",
};

/**
 * Point the camera at a barcode, or type its digits. A product already in the
 * catalog goes straight to the portion; one found outside it is shown first
 * and added to the catalog on request; an unknown code offers a product of
 * the user's own.
 */
export function BarcodeScanner({ onProduct, onCreate }: { onProduct: (product: Product) => void; onCreate: (barcode: string) => void }) {
  const { t } = useT();
  const video = useRef<HTMLVideoElement>(null);
  const importProduct = useImportBarcode();
  const [camera, setCamera] = useState<CameraState>("starting");
  const [manual, setManual] = useState("");
  const [looking, setLooking] = useState(false);
  const [result, setResult] = useState<BarcodeLookup | null>(null);
  const [failed, setFailed] = useState(false);
  const found = useRef<(code: string) => void>(() => undefined);

  const lookup = async (code: string) => {
    setLooking(true);
    setFailed(false);
    try {
      const data = await api.get<BarcodeLookup>(`/api/nutrition/products/barcode/${encodeURIComponent(code)}?locale=${bootstrap.locale}`);
      if (data.product) onProduct(data.product);
      else setResult({ ...data, barcode: code });
    } catch {
      setFailed(true);
    } finally {
      setLooking(false);
    }
  };
  found.current = (code) => void lookup(code);

  useEffect(() => {
    let alive = true;
    let stream: MediaStream | null = null;
    let timer: number | undefined;

    const stop = () => {
      window.clearTimeout(timer);
      stream?.getTracks().forEach((track) => track.stop());
      stream = null;
    };

    const start = async () => {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        setCamera("unavailable");
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
        });
      } catch (error) {
        const name = error instanceof DOMException ? error.name : "";
        if (alive) setCamera(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "unavailable");
        return;
      }
      // Closed while the permission prompt was open.
      if (!alive || !video.current) {
        stop();
        return;
      }
      video.current.srcObject = stream;
      await video.current.play().catch(() => undefined);

      let detect;
      try {
        detect = await getDetector();
      } catch {
        stop();
        if (alive) setCamera("unavailable");
        return;
      }
      if (!alive) return;
      setCamera("scanning");

      const tick = async (): Promise<void> => {
        if (!alive || !stream || !video.current) return;
        try {
          const hit = await detect(video.current);
          const code = hit ? cleanBarcode(hit.upce ? expandUpcE(hit.text) : hit.text) : null;
          if (code && alive) {
            stop();
            setCamera("off");
            navigator.vibrate?.(60);
            found.current(code);
            return;
          }
        } catch {
          // A frame that cannot be read: try the next one.
        }
        if (alive && stream) timer = window.setTimeout(tick, SCAN_INTERVAL_MS);
      };
      void tick();
    };

    void start();
    return () => {
      alive = false;
      stop();
    };
  }, []);

  const manualCode = cleanBarcode(manual);
  const preview = result?.preview;

  return (
    <div className="space-y-4">
      {camera !== "off" && (
        <div className="relative aspect-[4/3] overflow-hidden rounded-card bg-paper">
          <video ref={video} muted playsInline poster="/static/img/brand/nosifit-mark-on-dark.svg" className="h-full w-full object-cover" aria-label={t("scan.camera")} />
          {camera === "scanning" ? (
            <span className="pointer-events-none absolute inset-x-8 top-1/2 h-px bg-accent" aria-hidden="true" />
          ) : (
            <p className="absolute inset-0 grid place-items-center p-6 text-center text-sm text-ink-2" role="status">
              {t(CAMERA_TEXT[camera])}
            </p>
          )}
        </div>
      )}
      {camera === "scanning" && <p className="text-sm text-muted">{t("scan.hint")}</p>}

      {looking && (
        <p className="flex items-center gap-2 text-sm text-ink-2" role="status">
          <Spinner size={16} /> {t("scan.looking")}
        </p>
      )}
      {failed && (
        <p className="text-sm text-error" role="alert">
          {t("scan.failed")}
        </p>
      )}

      {result && !looking && (
        <div className="space-y-3 rounded-card bg-paper-3 p-4" aria-live="polite">
          {preview ? (
            <>
              <div>
                <p className="font-medium">{preview.name || t("scan.unnamed")}</p>
                <p className="mt-0.5 text-sm text-muted">
                  {[preview.brand, preview.kcal_per_100g != null ? `${num(preview.kcal_per_100g, 0)} ${t("unit.kcal")} ${t("food.per100")}` : null]
                    .filter(Boolean)
                    .join(", ")}
                </p>
              </div>
              <Button
                variant="primary"
                block
                busy={importProduct.isPending}
                onClick={() => importProduct.mutate(result.barcode, { onSuccess: (data) => onProduct(data.product), onError: () => setFailed(true) })}
              >
                {t("scan.import")}
              </Button>
            </>
          ) : (
            <p className="text-sm text-ink-2">{t("scan.notFound", { code: result.barcode })}</p>
          )}
          <Button block onClick={() => onCreate(result.barcode)}>
            {t("scan.createOwn")}
          </Button>
        </div>
      )}

      <form
        className="flex items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (manualCode) void lookup(manualCode);
        }}
      >
        <TextField
          className="flex-1"
          label={t("scan.manual")}
          inputMode="numeric"
          autoComplete="off"
          placeholder="4820000000000"
          value={manual}
          onChange={(event) => setManual(event.target.value)}
        />
        <Button type="submit" size="lg" disabled={!manualCode || looking}>
          {t("scan.find")}
        </Button>
      </form>
    </div>
  );
}
