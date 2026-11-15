import { createContext, use, useCallback, useMemo, useState, type ReactNode } from "react";
import type { MealCategory } from "../../api/types";
import { FoodPicker } from "../nutrition/FoodPicker";
import { WeightSheet } from "../nutrition/WeightSheet";
import { SleepSheet } from "../recovery/SleepSheet";
import { QuickLogSheet } from "./QuickLogSheet";

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

  return (
    <LogContext value={api}>
      {children}
      {request?.kind === "menu" && <QuickLogSheet onClose={close} onPick={setRequest} />}
      {request?.kind === "food" && <FoodPicker initialCategory={request.category} date={request.date} startWithScan={request.scan} onClose={close} />}
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
