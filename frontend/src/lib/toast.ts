import { useSyncExternalStore } from "react";

export interface ToastItem {
  id: number;
  tone: "ok" | "error";
  text: string;
}

let items: ToastItem[] = [];
let nextId = 1;
const listeners = new Set<() => void>();

const emit = (): void => listeners.forEach((listener) => listener());

export function dismissToast(id: number): void {
  items = items.filter((item) => item.id !== id);
  emit();
}

export function toast(text: string, tone: ToastItem["tone"] = "ok"): void {
  const id = nextId++;
  items = [...items.slice(-2), { id, tone, text }];
  emit();
  window.setTimeout(() => dismissToast(id), 3600);
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
