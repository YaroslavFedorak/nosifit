import { RefreshCw, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";
import { Button } from "./Button";

/** Placeholder with the final size of the content, so nothing jumps when data arrives. */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-xl bg-white/6", className)} />;
}

export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  const { t } = useT();
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-2xl border border-line bg-surface px-6 py-8 text-center">
      <TriangleAlert className="text-warn" size={28} aria-hidden="true" />
      <div>
        <p className="font-semibold">{t("common.errorTitle")}</p>
        <p className="mt-1 text-sm text-fg-muted">{t("common.errorText")}</p>
      </div>
      {onRetry && (
        <Button onClick={onRetry} icon={<RefreshCw size={16} aria-hidden="true" />}>
          {t("common.retry")}
        </Button>
      )}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  text,
  action,
}: {
  icon: ReactNode;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-8 text-center">
      <span className="grid size-12 place-items-center rounded-2xl border border-line bg-surface-2 text-fg-muted" aria-hidden="true">
        {icon}
      </span>
      <div>
        <p className="font-semibold">{title}</p>
        {text && <p className="mx-auto mt-1 max-w-xs text-sm text-fg-muted">{text}</p>}
      </div>
      {action}
    </div>
  );
}
