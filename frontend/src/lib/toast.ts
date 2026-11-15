import { useSyncExternalStore } from "react";

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface ToastItem {
  id: number;
  tone: "info" | "error";
  text: string;
  action?: ToastAction;
}

const DWELL_MS = 5000;

let items: ToastItem[] = [];
let nextId = 1;
const listeners = new Set<() => void>();

const emit = (): void => listeners.forEach((listener) => listener());

export function dismissToast(id: number): void {
  items = items.filter((item) => item.id !== id);
  emit();
}

/**
 * For failures and for effects the screen cannot show. A change the user can
 * already see needs no toast.
 */
export function toast(text: string, tone: ToastItem["tone"] = "info", action?: ToastAction): void {
  const id = nextId++;
  items = [...items.slice(-2), { id, tone, text, action }];
  emit();
  window.setTimeout(() => dismissToast(id), action ? DWELL_MS * 1.6 : DWELL_MS);
}

export function useToasts(): ToastItem[] {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => items,
  );
}
