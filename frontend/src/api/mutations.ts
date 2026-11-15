import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { planDayPayload, sessionPayload } from "../domain/training";
import { useT } from "../i18n";
import { api } from "../lib/api";
import { bootstrap } from "../lib/bootstrap";
import { toast } from "../lib/toast";
import type {
  AccountProfile,
  AccountSummary,
  Dish,
  FoodUnit,
  Habit,
  LoggedExercise,
  MealCategory,
  NewProduct,
  Plan,
  PlanDraft,
  PlanEntry,
  Product,
  Weekday,
} from "./types";

type Root = "dashboard" | "training" | "nutrition" | "recovery" | "account";

const refresh = (client: QueryClient, ...roots: Root[]): Promise<unknown> =>
  Promise.all(roots.map((root) => client.invalidateQueries({ queryKey: [root] })));

/** Shared by the mutations: refresh what changed and say so when it failed. */
function useDefaults(...roots: Root[]) {
  const client = useQueryClient();
  const { t } = useT();
  return {
    onSuccess: () => refresh(client, ...roots, "dashboard"),
    onError: () => toast(t("common.failed"), "error"),
  };
}

const locale = (): string => bootstrap.locale;

/* Training */

export function useSaveSession() {
  return useMutation({
    mutationFn: ({ sessionId, exercises }: { sessionId: number | null; exercises: LoggedExercise[] }) =>
      api.post<{ id: number | null }>("/api/training/sessions/complete", sessionPayload(sessionId, exercises)),
    ...useDefaults("training", "recovery"),
  });
}

export function useSavePlan() {
  return useMutation({
    mutationFn: (input: { id?: number; name?: string; days?: Partial<Record<Weekday, PlanEntry[]>>; active?: boolean }) => {
      const body = {
        ...(input.name !== undefined ? { name: input.name } : {}),
        ...(input.active !== undefined ? { is_active: input.active } : {}),
        ...(input.days
          ? { days: Object.fromEntries(Object.entries(input.days).map(([key, entries]) => [key, planDayPayload(entries ?? [])])) }
          : {}),
      };
      return input.id ? api.put<Plan>(`/api/training/plans/${input.id}`, body) : api.post<Plan>("/api/training/plans", body);
    },
    ...useDefaults("training"),
  });
}

export function useDeletePlan() {
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/training/plans/${id}`),
    ...useDefaults("training"),
  });
}

/** A recommended week as an unsaved draft; the caller saves it as a plan. */
export function useGeneratePlan() {
  const { t } = useT();
  return useMutation({
    mutationFn: (trainingDays: number) => api.post<PlanDraft>("/api/training/plans/generate", { training_days: trainingDays }),
    onError: () => toast(t("common.failed"), "error"),
  });
}

/** Records the planned workout of a weekday as done. Repeating it is safe. */
export function useCompletePlanDay() {
  return useMutation({
    mutationFn: ({ planId, day }: { planId: number; day: Weekday }) => api.post(`/api/training/plans/${planId}/days/${day}/complete`),
    ...useDefaults("training", "recovery"),
  });
}

/* Nutrition */

export interface FoodLine {
  productId: number;
  amount: number;
  unit: FoodUnit;
}

export function useLogFood() {
  return useMutation({
    mutationFn: (input: { category: MealCategory; date?: string; items?: FoodLine[]; dishId?: number }) =>
      api.post<{ ids: number[] }>("/api/nutrition/log", {
        category: input.category,
        locale: locale(),
        ...(input.date ? { date: input.date } : {}),
        ...(input.dishId != null ? { dish_id: input.dishId } : {}),
        ...(input.items ? { items: input.items.map((item) => ({ product_id: item.productId, amount: item.amount, unit: item.unit })) } : {}),
      }),
    ...useDefaults("nutrition"),
  });
}

export function useUpdateEntry() {
  return useMutation({
    mutationFn: (input: { id: number; amount: number; unit: FoodUnit }) =>
      api.patch(`/api/nutrition/entries/${input.id}`, { amount: input.amount, unit: input.unit, locale: locale() }),
    ...useDefaults("nutrition"),
  });
}

export function useDeleteEntry() {
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/nutrition/entries/${id}`),
    ...useDefaults("nutrition"),
  });
}

export function useCopyYesterday() {
  return useMutation({
    mutationFn: () => api.post("/api/nutrition/copy-yesterday"),
    ...useDefaults("nutrition"),
  });
}

export function useAddWater() {
  return useMutation({
    mutationFn: ({ liters, date }: { liters: number; date?: string }) => api.post("/api/nutrition/water", { amount: liters, ...(date ? { date } : {}) }),
    ...useDefaults("nutrition"),
  });
}

export function useSetWeight() {
  return useMutation({
    mutationFn: (kg: number) => api.post("/api/nutrition/weight", { weight: kg }),
    ...useDefaults("nutrition", "account"),
  });
}

export function useCreateProduct() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (product: NewProduct) => api.post<Product>("/api/nutrition/products", { ...product, locale: locale() }),
    onSuccess: () => refresh(client, "nutrition"),
  });
}

export function useDeleteProduct() {
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/nutrition/products/${id}`),
    ...useDefaults("nutrition"),
  });
}

export function useFavorite() {
  const client = useQueryClient();
  const { t } = useT();
  return useMutation({
    mutationFn: ({ id, favorite }: { id: number; favorite: boolean }) =>
      api.post<Product>(`/api/nutrition/products/${id}/favorite`, { favorite, locale: locale() }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["nutrition", "products"] }),
    onError: () => toast(t("common.failed"), "error"),
  });
}

export function useCreateDish() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; items: FoodLine[] }) =>
      api.post<Dish>("/api/nutrition/dishes", {
        name: input.name,
        locale: locale(),
        items: input.items.map((item) => ({ product_id: item.productId, amount: item.amount, unit: item.unit })),
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["nutrition", "dishes"] }),
  });
}

export function useDeleteDish() {
  const client = useQueryClient();
  const { t } = useT();
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/nutrition/dishes/${id}`),
    onSuccess: () => client.invalidateQueries({ queryKey: ["nutrition", "dishes"] }),
    onError: () => toast(t("common.failed"), "error"),
  });
}

export function useImportBarcode() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      api.post<{ product: Product }>(`/api/nutrition/products/barcode/${encodeURIComponent(code)}/import`, { locale: locale() }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["nutrition", "products"] }),
  });
}

/* Recovery */

export function useLogSleep() {
  return useMutation({
    mutationFn: ({ start, end }: { start: Date; end: Date }) =>
      api.post("/api/recovery/sleep", { sleep_start: start.toISOString(), sleep_end: end.toISOString() }),
    ...useDefaults("recovery"),
  });
}

/** Ticks a habit at once and rolls back if the server says no. */
export function useToggleHabit() {
  const client = useQueryClient();
  const { t } = useT();
  const key = ["recovery", "habits"];
  return useMutation({
    mutationFn: (habit: Habit) =>
      habit.completed
        ? api.del(`/api/recovery/habits/logs/${habit.user_habit_id}`)
        : api.post("/api/recovery/habits/logs", { user_habit_id: habit.user_habit_id }),
    onMutate: async (habit) => {
      await client.cancelQueries({ queryKey: key });
      const previous = client.getQueryData<Habit[]>(key);
      if (previous) {
        client.setQueryData<Habit[]>(
          key,
          previous.map((item) => (item.user_habit_id === habit.user_habit_id ? { ...item, completed: !item.completed } : item)),
        );
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
    ...useDefaults("recovery"),
  });
}

export function useRemoveHabit() {
  return useMutation({
    mutationFn: (userHabitId: number) => api.del(`/api/recovery/habits/${userHabitId}`),
    ...useDefaults("recovery"),
  });
}

/* Account */

export type ProfileInput = Omit<AccountProfile, "wants_nutrition" | "wants_recovery"> & { username: string };

const text = (value: string | number | null): string => (value == null ? "" : String(value));

/** Saves the profile through the form route; the nutrition targets are recalculated on the server. */
export function useUpdateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: ProfileInput) =>
      api.postForm<{ status: string; account: AccountSummary }>("/profile/update_full", {
        username: input.username,
        age: text(input.age),
        height: text(input.height),
        weight: text(input.weight),
        workouts_per_week: text(input.workouts_per_week),
        gender: text(input.gender),
        activity: text(input.activity),
        goal: text(input.goal),
        experience: text(input.experience),
        training_location: text(input.training_location),
      }),
    onSuccess: (data) => {
      if (data?.account) client.setQueryData(["account"], data.account);
      return refresh(client, "nutrition", "dashboard");
    },
  });
}

/** Which modules the user wants. The other two fields of the route are sent back unchanged. */
export function useSaveModules() {
  const client = useQueryClient();
  const { t } = useT();
  return useMutation({
    mutationFn: (input: { training_location: string | null; wants_nutrition: boolean; wants_recovery: boolean }) =>
      api.post("/api/onboarding/profile", { ...input, training_location: input.training_location ?? "home" }),
    onSuccess: () => refresh(client, "account"),
    onError: () => toast(t("common.failed"), "error"),
  });
}

export const useChangePassword = () =>
  useMutation({
    mutationFn: (input: { current: string; next: string }) =>
      api.postForm("/profile/change_password", { current_password: input.current, new_password: input.next, confirm_password: input.next }),
  });

export const useRequestEmailChange = () =>
  useMutation({
    mutationFn: (input: { email: string; password: string }) => api.post("/profile/change_email", { new_email: input.email, password: input.password }),
  });

export function useConfirmEmailChange() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api.post("/profile/confirm_email", { code }),
    onSuccess: () => refresh(client, "account"),
  });
}

export function useDisconnectProvider() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (provider: "google" | "github") => api.postForm("/profile/oauth_disconnect", { provider }),
    onSuccess: () => refresh(client, "account"),
  });
}

export const useTelegramCode = () => useMutation({ mutationFn: () => api.post("/profile/telegram/disconnect/request") });

export function useDisconnectTelegram() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (proof: { password?: string; code?: string }) => api.post("/profile/telegram/disconnect", proof),
    onSuccess: () => refresh(client, "account"),
  });
}

export const useDeleteAccountCode = () => useMutation({ mutationFn: () => api.post("/profile/delete/request") });

export const useDeleteAccountConfirm = () => useMutation({ mutationFn: (code: string) => api.post("/profile/delete/confirm", { code }) });

export const useDeleteAccount = () =>
  useMutation({
    mutationFn: (input: { email: string; password: string }) => api.post("/profile/delete/final", input),
  });
