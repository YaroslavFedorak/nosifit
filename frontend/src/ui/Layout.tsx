import { ChevronRight } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";
import { Link } from "react-router";
import type { Tone } from "../design/tokens";
import { cn } from "../lib/cn";

/** The title of a screen, with the one or two actions that belong to the whole screen. */
export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <header className="flex min-h-tap items-end justify-between gap-4 pb-4 desk:pb-6">
      <div className="min-w-0">
        <h1>{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </header>
  );
}

/** A titled part of a screen. The title is a real heading; the action sits on its line. */
export function Section({
  title,
  action,
  note,
  tone,
  className,
  children,
  ...rest
}: Omit<HTMLAttributes<HTMLElement>, "title"> & { title?: string; action?: ReactNode; note?: ReactNode; tone?: Tone }) {
  return (
    <section data-tone={tone} className={cn("min-w-0", className)} {...rest}>
      {(title || action) && (
        <div className="mb-2 flex min-h-control items-center justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-md">{title}</h2>}
            {note && <p className="text-sm text-muted">{note}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

/** One raised surface holding rows of the same kind, parted by hairlines. */
export function Group({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("divide-y divide-rule overflow-hidden rounded-card bg-paper-2", className)} {...rest}>
      {children}
    </div>
  );
}

/** A plain raised surface for content that is not a list. */
export function Panel({ className, children, tone, ...rest }: HTMLAttributes<HTMLDivElement> & { tone?: Tone }) {
  return (
    <div data-tone={tone} className={cn("rounded-card bg-paper-2 p-4", className)} {...rest}>
      {children}
    </div>
  );
}

const ROW = "flex min-h-[3.25rem] w-full items-center gap-3 px-4 py-2 text-left";
const ROW_ACTIVE = "transition-colors duration-150 hover:bg-paper-3 active:bg-paper-3";

interface RowContent {
  leading?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  /** A value or a control at the row's end. */
  trailing?: ReactNode;
  /** A chevron: the row leads somewhere. */
  chevron?: boolean;
}

function RowBody({ leading, title, subtitle, trailing, chevron }: RowContent) {
  return (
    <>
      {leading}
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{title}</span>
        {subtitle && <span className="mt-0.5 block truncate text-sm text-muted">{subtitle}</span>}
      </span>
      {trailing && <span className="shrink-0 text-right text-sm text-ink-2">{trailing}</span>}
      {chevron && <ChevronRight size={18} className="text-muted" aria-hidden="true" />}
    </>
  );
}

/** A row of a group. With `to` it is a link, with `onClick` a button, otherwise plain text. */
export function Row({
  to,
  href,
  onClick,
  disabled,
  className,
  ...content
}: RowContent & { to?: string; href?: string; onClick?: () => void; disabled?: boolean; className?: string }) {
  if (to) {
    return (
      <Link to={to} className={cn(ROW, ROW_ACTIVE, className)}>
        <RowBody {...content} />
      </Link>
    );
  }
  if (href) {
    return (
      <a href={href} className={cn(ROW, ROW_ACTIVE, className)}>
        <RowBody {...content} />
      </a>
    );
  }
  if (onClick) {
    return (
      <button type="button" onClick={onClick} disabled={disabled} className={cn(ROW, ROW_ACTIVE, "disabled:cursor-not-allowed disabled:opacity-55", className)}>
        <RowBody {...content} />
      </button>
    );
  }
  return (
    <div className={cn(ROW, className)}>
      <RowBody {...content} />
    </div>
  );
}

/** A figure with its unit and what it counts. No icon, no box. */
export function Stat({ value, unit, label, className }: { value: ReactNode; unit?: string; label: string; className?: string }) {
  return (
    <div className={cn("min-w-0", className)}>
      <p className="figure whitespace-nowrap text-xl leading-none text-ink">
        {value}
        {unit && <span className="ml-1 text-sm font-normal tracking-normal text-muted">{unit}</span>}
      </p>
      <p className="mt-1.5 truncate text-sm text-muted">{label}</p>
    </div>
  );
}

/** Label and value pairs, as a description list. */
export function Facts({ items, className }: { items: Array<{ label: string; value: ReactNode }>; className?: string }) {
  return (
    <dl className={cn("divide-y divide-rule", className)}>
      {items.map((item) => (
        <div key={item.label} className="flex min-h-11 items-baseline justify-between gap-4 py-2.5">
          <dt className="text-sm text-muted">{item.label}</dt>
          <dd className="min-w-0 text-right font-medium">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
