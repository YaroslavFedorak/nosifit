import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import { cn } from "../lib/cn";
import { Spinner } from "./Feedback";

/** `danger` is a quiet removal; `destructive` is the filled button of a dialog whose one action destroys something. */
export type ButtonVariant = "primary" | "secondary" | "quiet" | "danger" | "destructive";
export type ButtonSize = "md" | "lg";

interface ButtonStyle {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
}

/** One class list for <button>, router links and plain anchors. */
export function buttonClass({ variant = "secondary", size = "md", block = false }: ButtonStyle = {}): string {
  return cn(
    "press inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium disabled:cursor-not-allowed disabled:opacity-55 aria-busy:cursor-progress",
    size === "lg" ? "min-h-control-lg px-6 text-md" : "min-h-control px-4 text-sm",
    block && "w-full",
    variant === "primary" && "bg-accent text-accent-ink hover:bg-accent-2",
    variant === "secondary" && "bg-paper-3 text-ink hover:bg-paper-4",
    variant === "quiet" && "text-ink-2 hover:bg-paper-3 hover:text-ink",
    variant === "danger" && "text-error hover:bg-paper-3",
    variant === "destructive" && "bg-error text-paper hover:bg-warn",
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & ButtonStyle & { icon?: ReactNode; busy?: boolean };

export function Button({ variant, size, block, icon, busy = false, className, children, type = "button", disabled, ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonClass({ variant, size, block }), className)}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <Spinner size={16} /> : icon}
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

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { label: string; tonal?: boolean };

/** A square button for one icon; the label is what screen readers announce. */
export function IconButton({ label, tonal = false, className, children, type = "button", ...rest }: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "press inline-grid size-control shrink-0 place-items-center rounded-control disabled:cursor-not-allowed disabled:opacity-55",
        tonal ? "bg-paper-3 text-ink hover:bg-paper-4" : "text-ink-2 hover:bg-paper-3 hover:text-ink",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
