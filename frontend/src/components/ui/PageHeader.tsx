import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { Accent } from "./Card";

export function PageHeader({
  title,
  subtitle,
  icon: Icon,
  accent,
  action,
}: {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  accent?: Accent;
  action?: ReactNode;
}) {
  return (
    <header className="flex items-center justify-between gap-3 pb-4 pt-1 tab:pb-6">
      <div className="flex min-w-0 items-center gap-3">
        {Icon && (
          <span
            data-accent={accent}
            className="grid size-11 shrink-0 place-items-center rounded-xl border border-accent-soft bg-accent-soft text-accent"
            aria-hidden="true"
          >
            <Icon size={22} />
          </span>
        )}
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold leading-tight tracking-tight text-balance">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-fg-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </header>
  );
}
