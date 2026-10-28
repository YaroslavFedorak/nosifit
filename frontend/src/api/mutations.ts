import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useT } from "../i18n";
import { api } from "../lib/api";
import { toast } from "../lib/toast";
import { sessionPayload } from "./session";
import type { Habit, LoggedExercise, MealCategory, RecoverySnapshot } from "./types";

type Root = "dashboard" | "training" | "nutrition" | "recovery";

const refresh = (client: QueryClient, ...roots: Root[]): Promise<unknown> =>
  Promise.all(roots.map((root) => client.invalidateQueries({ queryKey: [root] })));

/** Shared by every mutation: refresh what changed and tell the user if it failed. */
function useMutationDefaults(...roots: Root[]) {
  const client = useQueryClient();
  const { t } = useT();
  return {
    onSuccess: () => refresh(client, ...roots, "dashboard"),
    onError: () => toast(t("common.failed"), "error"),
  };
}

/* Training */

export function useSaveSession() {
  return useMutation({
    mutationFn: ({ sessionId, exercises }: { sessionId: number | null; exercises: LoggedExercise[] }) =>
      api.post<{ id: number }>("/api/training/sessions/complete", sessionPayload(sessionId, exercises)),
    ...useMutationDefaults("training"),
  });
}

/* Nutrition */

export function useLogFood() {
  return useMutation({
    mutationFn: (input: { category: MealCategory; productId: number; amount: number; unit: string }) =>
      api.post("/api/nutrition/log", {
        category: input.category,
        items: [{ product_id: input.productId, amount: input.amount, unit: input.unit }],
      }),
    ...useMutationDefaults("nutrition"),
  });
}

export function useUpdateEntry() {
  return useMutation({
    mutationFn: (input: { id: number; amount: number; unit: string }) =>
      api.patch(`/api/nutrition/entries/${input.id}`, { amount: input.amount, unit: input.unit }),
    ...useMutationDefaults("nutrition"),
  });
}

export function useDeleteEntry() {
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/nutrition/entries/${id}`),
    ...useMutationDefaults("nutrition"),
  });
}

export function useAddWater() {
  return useMutation({
    mutationFn: (liters: number) => api.post("/api/nutrition/water", { amount: liters }),
    ...useMutationDefaults("nutrition"),
  });
}

export function useSetWeight() {
  return useMutation({
    mutationFn: (kg: number) => api.post("/api/nutrition/weight", { weight: kg }),
    ...useMutationDefaults("nutrition"),
  });
}

/* Recovery */

export function useLogSleep() {
  return useMutation({
    mutationFn: ({ start, end }: { start: Date; end: Date }) =>
      api.post("/api/recovery/sleep", { sleep_start: start.toISOString(), sleep_end: end.toISOString() }),
    ...useMutationDefaults("recovery"),
  });
}

/** Ticks a habit at once and rolls back if the server says no. */
export function useToggleHabit() {
  const client = useQueryClient();
  const { t } = useT();
  const key = ["recovery", "snapshot"];
  return useMutation({
    mutationFn: (habit: Habit) =>
      habit.completed
        ? api.del(`/api/recovery/habits/logs/${habit.user_habit_id}`)
        : api.post("/api/recovery/habits/logs", { user_habit_id: habit.user_habit_id }),
    onMutate: async (habit) => {
      await client.cancelQueries({ queryKey: key });
      const previous = client.getQueryData<RecoverySnapshot>(key);
      if (previous) {
        client.setQueryData<RecoverySnapshot>(key, {
          ...previous,
          habits: previous.habits.map((item) =>
            item.user_habit_id === habit.user_habit_id ? { ...item, completed: !item.completed } : item,
          ),
        });
      }
      return { previous };
    },
    onError: (_error, _habit, context) => {
      if (context?.previous) client.setQueryData(key, context.previous);
      toast(t("common.failed"), "error");
    },
    onSettled: () => refresh(client, "recovery", "dashboard"),
  });
}

export function useAddHabit() {
  return useMutation({
    mutationFn: (habitId: number) => api.post(`/api/recovery/habits/add/${habitId}`),
    ...useMutationDefaults("recovery"),
  });
}

export function useRemoveHabit() {
  return useMutation({
    mutationFn: (userHabitId: number) => api.del(`/api/recovery/habits/${userHabitId}`),
    ...useMutationDefaults("recovery"),
  });
}
