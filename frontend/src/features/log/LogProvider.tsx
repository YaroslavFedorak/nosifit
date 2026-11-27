import { createContext, lazy, Suspense, use, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type { MealCategory } from "../../api/types";
import { WeightSheet } from "../nutrition/WeightSheet";
import { SleepSheet } from "../recovery/SleepSheet";
import { QuickLogSheet } from "./QuickLogSheet";

// The food picker, with the barcode scanner and the product form, is the
// largest piece of the interface and opens only on demand: it is loaded on
// its own, after the page itself, while the browser is idle.
const loadFoodPicker = () => import("../nutrition/FoodPicker");
const FoodPicker = lazy(() => loadFoodPicker().then((module) => ({ default: module.FoodPicker })));

function whenIdle(task: () => void): () => void {
  if (typeof window.requestIdleCallback === "function") {
    const id = window.requestIdleCallback(task, { timeout: 5000 });
    return () => window.cancelIdleCallback(id);
  }
  const id = window.setTimeout(task, 2000);
  return () => window.clearTimeout(id);
}

/** What the user is about to record. One sheet per kind, shared by every screen. */
export type LogRequest =
  | { kind: "menu" }
  | { kind: "food"; category?: MealCategory; date?: string; scan?: boolean }
  | { kind: "sleep" }
  | { kind: "weight" };

interface LogApi {
  open: (request: LogRequest) => void;
  close: () => void;
}

const LogContext = createContext<LogApi | null>(null);

/**
 * Hosts the entry sheets. A screen never mounts its own copy of the food
 * picker or the sleep form: it asks for one here, so recording works the
 * same way from Today, from a module's page and from the "+" button.
 */
export function LogProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<LogRequest | null>(null);
  const close = useCallback(() => setRequest(null), []);
  const api = useMemo<LogApi>(() => ({ open: setRequest, close }), [close]);

  // Ready before the first tap, without delaying the page.
  useEffect(() => whenIdle(() => void loadFoodPicker().catch(() => undefined)), []);

  return (
    <LogContext value={api}>
      {children}
      {request?.kind === "menu" && <QuickLogSheet onClose={close} onPick={setRequest} />}
      {request?.kind === "food" && (
        <Suspense fallback={null}>
          <FoodPicker initialCategory={request.category} date={request.date} startWithScan={request.scan} onClose={close} />
        </Suspense>
      )}
      {request?.kind === "sleep" && <SleepSheet onClose={close} />}
      {request?.kind === "weight" && <WeightSheet onClose={close} />}
    </LogContext>
  );
}

export function useLog(): LogApi {
  const value = use(LogContext);
  if (!value) throw new Error("useLog must be used inside <LogProvider>");
  return value;
}
