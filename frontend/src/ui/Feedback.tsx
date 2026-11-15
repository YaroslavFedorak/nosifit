import { CircleAlert, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { useT } from "../i18n";
import { cn } from "../lib/cn";
import { dismissToast, useToasts } from "../lib/toast";

export function Spinner({ size = 18, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={cn("anim-spin keep-motion", className)} aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/** A placeholder in the shape of what is coming, so nothing jumps when it arrives. */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("anim-pulse rounded-control bg-paper-3", className)} />;
}

/** Rows of a list that is still loading. */
export function SkeletonRows({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)} aria-busy="true">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-12" />
      ))}
    </div>
  );
}

/** What broke and what to do about it, in place of the content that failed to load. */
export function ErrorNote({ onRetry, className }: { onRetry?: () => void; className?: string }) {
  const { t } = useT();
  return (
    <div role="alert" className={cn("flex flex-wrap items-center gap-x-4 gap-y-2 rounded-card bg-paper-2 px-4 py-3", className)}>
      <TriangleAlert size={18} className="text-warn" aria-hidden="true" />
      <p className="min-w-0 flex-1 text-sm text-ink-2">
        <span className="font-medium text-ink">{t("common.errorTitle")}.</span> {t("common.errorText")}
      </p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="press min-h-control rounded-control px-3 text-sm font-medium text-ink hover:bg-paper-3">
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}

/**
 * An empty region says what belongs in it and offers the one action that
 * fills it. It never shows a zero or an empty chart.
 */
export function Empty({ title, text, action, className }: { title: string; text?: string; action?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-start gap-3 py-2", className)}>
      <div>
        <p className="font-medium text-ink">{title}</p>
        {text && <p className="mt-1 max-w-[52ch] text-sm text-muted">{text}</p>}
      </div>
      {action}
    </div>
  );
}

/** Failures and effects the screen cannot show; newest at the bottom of the stack. */
export function ToastHost() {
  const { t } = useT();
  const items = useToasts();
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 top-[max(0.75rem,env(safe-area-inset-top))] z-[500] flex flex-col items-center gap-2 px-4"
    >
      {items.map((item) => (
        <div
          key={item.id}
          role={item.tone === "error" ? "alert" : "status"}
          className="anim-rise pointer-events-auto flex max-w-md items-center gap-3 rounded-control border border-rule bg-paper-4 py-2 pl-4 pr-2 text-sm text-ink shadow-overlay"
        >
          {item.tone === "error" && <CircleAlert size={18} className="text-error" aria-hidden="true" />}
          <span className="min-w-0 flex-1 py-1.5">{item.text}</span>
          {item.action ? (
            <button
              type="button"
              onClick={() => {
                item.action?.run();
                dismissToast(item.id);
              }}
              className="press min-h-9 rounded-control px-3 font-medium text-accent hover:bg-paper-3"
            >
              {item.action.label}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => dismissToast(item.id)}
              className="press min-h-9 rounded-control px-3 text-ink-2 hover:bg-paper-3 hover:text-ink"
            >
              {t("common.close")}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
