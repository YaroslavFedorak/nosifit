import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { diaryFromPast, diaryFromToday, type DiaryDay } from "../domain/nutrition";
import { api } from "../lib/api";
import { bootstrap } from "../lib/bootstrap";
import { isoDay } from "../lib/format";
import type {
  AccountSummary,
  DashboardDay,
  DashboardRecommendation,
  DashboardToday,
  Dish,
  ExerciseOption,
  Habit,
  HabitCatalogItem,
  NutritionHeatmapDay,
  NutritionPastDay,
  NutritionStats,
  NutritionTip,
  NutritionToday,
  Plan,
  PlanWeek,
  Product,
  RecoveryDayDetails,
  RecoveryHeatmapDay,
  RecoverySnapshot,
  TrainingDayDetails,
  TrainingHeatmapDay,
  TrainingRecommendations,
  TrainingSession,
  TrainingToday,
  WaterDay,
  WeeklyMuscle,
  WeightInfo,
} from "./types";

const locale = (): string => bootstrap.locale;
const userId = (): number => bootstrap.user?.id ?? 0;

/**
 * Heatmap endpoints answer one calendar year at a time. In January and
 * February recent weeks reach into the previous year, so fetch both.
 */
async function recentYears<T>(path: (year: number) => string): Promise<T[]> {
  const now = new Date();
  const years = now.getMonth() < 2 ? [now.getFullYear() - 1, now.getFullYear()] : [now.getFullYear()];
  const parts = await Promise.all(years.map((year) => api.get<{ days: T[] }>(path(year))));
  return parts.flatMap((part) => part.days);
}

/* Dashboard */

export const useDashboardToday = () =>
  useQuery({ queryKey: ["dashboard", "today"], queryFn: () => api.get<DashboardToday>("/api/dashboard/today") });

export const useDashboardHeatmap = () =>
  useQuery({
    queryKey: ["dashboard", "heatmap"],
    queryFn: async () => (await api.get<{ days: DashboardDay[] }>("/api/dashboard/heatmap")).days,
  });

export const useDashboardRecommendation = () =>
  useQuery({
    queryKey: ["dashboard", "recommendation"],
    queryFn: () => api.get<DashboardRecommendation>("/api/dashboard/recommendation"),
  });

/* Training */

export const useTrainingSession = () =>
  useQuery({
    queryKey: ["training", "session"],
    queryFn: async () => (await api.get<{ session: TrainingSession | null }>(`/api/training/sessions/today?locale=${locale()}`)).session,
  });

export const useTrainingToday = () =>
  useQuery({ queryKey: ["training", "today"], queryFn: () => api.get<TrainingToday>("/api/training/today") });

export const usePlans = () => useQuery({ queryKey: ["training", "plans"], queryFn: () => api.get<Plan[]>("/api/training/plans") });

export const usePlanWeek = (planId: number | null | undefined) =>
  useQuery({
    queryKey: ["training", "plans", "week", planId],
    queryFn: () => api.get<PlanWeek>(`/api/training/plans/${planId}/week`),
    enabled: planId != null,
  });

export const useWeeklySets = (enabled = true) =>
  useQuery({
    queryKey: ["training", "weekly"],
    queryFn: async () =>
      (await api.get<{ weekly_sets?: { muscles: WeeklyMuscle[] } | null }>("/api/training/analytics")).weekly_sets?.muscles ?? [],
    enabled,
  });

export const useTrainingRecommendations = (enabled = true) =>
  useQuery({
    queryKey: ["training", "recommendations"],
    queryFn: () => api.get<TrainingRecommendations>("/api/training/recommendations"),
    enabled,
  });

export const useTrainingHeatmap = () =>
  useQuery({
    queryKey: ["training", "heatmap"],
    queryFn: () => recentYears<TrainingHeatmapDay>((year) => `/api/training/heatmap?year=${year}`),
  });

export const useExerciseOptions = (query: string, enabled: boolean) =>
  useQuery({
    queryKey: ["training", "exercises", query],
    queryFn: async () =>
      (
        await api.get<{ items: ExerciseOption[] }>(
          query
            ? `/api/training/exercises/search?q=${encodeURIComponent(query)}&limit=20&locale=${locale()}`
            : `/api/training/exercises/recent?limit=12&locale=${locale()}`,
        )
      ).items,
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

export const useTrainingDay = (date: string, enabled: boolean) =>
  useQuery({
    queryKey: ["training", "day", date],
    queryFn: () => api.get<TrainingDayDetails>(`/api/training/day/${date}`),
    enabled,
  });

/* Nutrition */

/** One day of the diary. Today and past days come from two endpoints with one shape here. */
export const useDiaryDay = (date: string = isoDay()) =>
  useQuery<DiaryDay>({
    queryKey: ["nutrition", "day", date],
    queryFn: async () =>
      date === isoDay()
        ? diaryFromToday(await api.get<NutritionToday>(`/api/nutrition/day?locale=${locale()}`))
        : diaryFromPast(await api.get<NutritionPastDay>(`/api/nutrition/day/${date}?locale=${locale()}`)),
    placeholderData: keepPreviousData,
  });

export const useNutritionTips = (enabled = true) =>
  useQuery({
    queryKey: ["nutrition", "tips"],
    queryFn: async () =>
      (await api.get<{ recommendations: NutritionTip[] }>(`/api/nutrition/recommendations?locale=${locale()}`)).recommendations,
    enabled,
  });

export const useWater = (date: string = isoDay()) =>
  useQuery({
    queryKey: ["nutrition", "water", date],
    queryFn: () => api.get<WaterDay>(`/api/nutrition/water?date=${date}`),
  });

export const useWeight = () => useQuery({ queryKey: ["nutrition", "weight"], queryFn: () => api.get<WeightInfo>("/api/nutrition/weight") });

export const useNutritionStats = (days = 7) =>
  useQuery({
    queryKey: ["nutrition", "stats", days],
    queryFn: () => api.get<NutritionStats>(`/api/nutrition/stats?days=${days}`),
  });

export const useNutritionHeatmap = (enabled = true) =>
  useQuery({
    queryKey: ["nutrition", "heatmap"],
    queryFn: () => recentYears<NutritionHeatmapDay>((year) => `/api/nutrition/heatmap?year=${year}`),
    enabled,
  });

export type ProductSource = "search" | "recent" | "favorites" | "mine";

const PRODUCT_URL: Record<ProductSource, (query: string) => string> = {
  search: (query) => `/api/nutrition/products?q=${encodeURIComponent(query)}&limit=30&locale=${locale()}`,
  recent: () => `/api/nutrition/products/recent?locale=${locale()}`,
  favorites: () => `/api/nutrition/products/favorites?locale=${locale()}`,
  mine: () => `/api/nutrition/products/mine?locale=${locale()}`,
};

export const useProducts = (source: ProductSource, query: string, enabled: boolean) =>
  useQuery({
    queryKey: ["nutrition", "products", source, source === "search" ? query : ""],
    queryFn: async () => (await api.get<{ products: Product[] }>(PRODUCT_URL[source](query))).products,
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });

export const useDishes = (enabled: boolean) =>
  useQuery({
    queryKey: ["nutrition", "dishes"],
    queryFn: async () => (await api.get<{ dishes: Dish[] }>(`/api/nutrition/dishes?limit=50&locale=${locale()}`)).dishes,
    enabled,
  });

/* Recovery */

/** null when nothing has been recorded yet: the server has no snapshot to send. */
export const useRecoverySnapshot = () =>
  useQuery({
    queryKey: ["recovery", "snapshot"],
    queryFn: async () => {
      const data = await api.get<RecoverySnapshot | { snapshot: null }>(`/api/recovery/snapshot/${userId()}`);
      return "date" in data ? data : null;
    },
    retry: false,
  });

/** The user's habits with today's ticks. Works before the first snapshot exists. */
export const useHabits = () =>
  useQuery({
    queryKey: ["recovery", "habits"],
    queryFn: () => api.get<Habit[]>(`/api/recovery/habits/user/${userId()}`),
  });

export const useRecoveryHeatmap = (enabled = true) =>
  useQuery({
    queryKey: ["recovery", "heatmap"],
    queryFn: async () => (await api.get<{ days: RecoveryHeatmapDay[] }>(`/api/recovery/heatmap/${userId()}`)).days,
    enabled,
  });

export const useHabitCatalog = (enabled: boolean) =>
  useQuery({
    queryKey: ["recovery", "catalog"],
    queryFn: () => api.get<HabitCatalogItem[]>("/api/recovery/habits/list"),
    enabled,
    staleTime: 5 * 60_000,
  });

export const useRecoveryDay = (date: string, enabled: boolean) =>
  useQuery({
    queryKey: ["recovery", "day", date],
    queryFn: () => api.get<RecoveryDayDetails>(`/api/recovery/day-details/${userId()}?date=${date}`),
    enabled,
  });

/* Account */

export const useAccount = (enabled = true) =>
  useQuery({
    queryKey: ["account"],
    queryFn: () => api.get<AccountSummary>("/profile/summary"),
    enabled,
    staleTime: 60_000,
  });
