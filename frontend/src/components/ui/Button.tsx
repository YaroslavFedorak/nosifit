import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import { cn } from "../../lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "lg";

interface ButtonStyle {
  variant?: Variant;
  size?: Size;
  block?: boolean;
}

/** One class list for <button>, router links and plain anchors. */
export function buttonClass({ variant = "secondary", size = "md", block = false }: ButtonStyle = {}): string {
  return cn(
    "inline-flex select-none items-center justify-center gap-2 rounded-xl px-4 font-semibold transition duration-150 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
    size === "lg" ? "min-h-tap-lg text-base" : "min-h-tap text-sm",
    block && "w-full",
    variant === "primary" && "btn-hero",
    variant === "secondary" && "border border-line-strong bg-surface-2 text-fg hover:bg-surface-3",
    variant === "ghost" && "text-fg-muted hover:bg-white/5 hover:text-fg",
    variant === "danger" && "border border-danger/35 bg-danger/10 text-danger hover:bg-danger/15",
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & ButtonStyle & { icon?: ReactNode };

export function Button({ variant, size, block, icon, className, children, type = "button", ...rest }: ButtonProps) {
  return (
    <button type={type} className={cn(buttonClass({ variant, size, block }), className)} {...rest}>
      {icon}
      {children}
    </button>
  );
}

type ButtonLinkProps = LinkProps & ButtonStyle & { icon?: ReactNode };

export function ButtonLink({ variant, size, block, icon, className, children, ...rest }: ButtonLinkProps) {
  return (
    <Link className={cn(buttonClass({ variant, size, block }), className)} {...rest}>
      {icon}
      {children}
    </Link>
  );
}

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { label: string };

/** Square 44px button for icons; the label is what screen readers announce. */
export function IconButton({ label, className, children, type = "button", ...rest }: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "inline-grid size-tap shrink-0 place-items-center rounded-xl text-fg-muted transition hover:bg-white/5 hover:text-fg active:scale-95 disabled:opacity-40",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
