import { ArrowLeft, X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useT } from "../i18n";
import { cn } from "../lib/cn";
import type { Tone } from "../design/tokens";
import { IconButton } from "./Button";
import { useTone } from "./Tone";

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

export type SheetSize = "md" | "lg" | "tall";

/**
 * A sheet that rises from the bottom on a phone and a centred dialog from the
 * tablet width up. `tall` takes the whole phone screen, for search lists that
 * need the room. The body scrolls inside; the page behind is locked.
 */
export function Sheet({
  open,
  onClose,
  onBack,
  title,
  size = "md",
  tone,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  /** Shows a back arrow in place of nothing, for a second step inside the sheet. */
  onBack?: () => void;
  title: string;
  size?: SheetSize;
  /** The module whose colour the sheet wears; by default the one of the screen that opened it. */
  tone?: Tone;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const { t } = useT();
  const screenTone = useTone();
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    document.documentElement.classList.add("scroll-locked");
    // A field marked autoFocus keeps the focus; otherwise the panel takes it.
    if (!panel.current?.contains(document.activeElement)) panel.current?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        close.current();
        return;
      }
      if (event.key !== "Tab" || !panel.current) return;
      const items = panel.current.querySelectorAll<HTMLElement>(FOCUSABLE);
      const first = items[0];
      const last = items[items.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      // Another sheet may still be open underneath.
      if (document.querySelectorAll("[data-sheet]").length === 0) document.documentElement.classList.remove("scroll-locked");
      previous?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div data-sheet data-tone={tone ?? screenTone} className="fixed inset-0 z-[400] flex items-end justify-center tab:items-center tab:p-6">
      <div className="anim-fade absolute inset-0 bg-scrim" onClick={onClose} aria-hidden="true" />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          "anim-sheet relative flex w-full flex-col overflow-hidden rounded-t-[16px] border border-b-0 border-rule bg-paper-2 shadow-overlay outline-none tab:rounded-card tab:border-b",
          size === "tall" ? "h-[calc(100dvh-env(safe-area-inset-top)-0.75rem)] tab:h-auto tab:max-h-[min(86dvh,46rem)]" : "max-h-[92dvh] tab:max-h-[min(86dvh,46rem)]",
          size === "md" ? "tab:max-w-md" : "tab:max-w-2xl",
        )}
      >
        <div className="flex shrink-0 items-center gap-1 py-2 pl-2 pr-2">
          {onBack ? (
            <IconButton label={t("common.back")} onClick={onBack}>
              <ArrowLeft size={20} />
            </IconButton>
          ) : (
            <span className="w-2" aria-hidden="true" />
          )}
          <h2 id={titleId} className="min-w-0 flex-1 truncate text-lg">
            {title}
          </h2>
          <IconButton label={t("common.close")} onClick={onClose}>
            <X size={20} />
          </IconButton>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-4">{children}</div>
        {footer && (
          <div className="shrink-0 border-t border-rule bg-paper-2 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">{footer}</div>
        )}
      </div>
    </div>,
    document.body,
  );
}
