import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { bootstrap } from "../lib/bootstrap";
import type {
  DashboardDay,
  DashboardRecommendation,
  DashboardToday,
  ExerciseOption,
  HabitCatalogItem,
  NutritionDay,
  NutritionHeatmapDay,
  NutritionTip,
  Product,
  ProductSource,
  RecoveryHeatmapDay,
  RecoverySnapshot,
  TrainingDayDetails,
  TrainingHeatmapDay,
  TrainingRecommendations,
  TrainingSession,
  TrainingToday,
  WeeklyMuscle,
} from "./types";

const locale = (): string => bootstrap.locale;
const userId = (): number => bootstrap.user?.id ?? 0;

/**
 * Heatmap endpoints answer one calendar year at a time. In January and
 * February the last five weeks reach into the previous year, so fetch both.
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
    queryFn: async () => (await api.get<{ session: TrainingSession | null }>("/api/training/sessions/today")).session,
  });

export const useTrainingToday = () =>
  useQuery({ queryKey: ["training", "today"], queryFn: () => api.get<TrainingToday>("/api/training/today") });

export const useWeeklySets = () =>
  useQuery({
    queryKey: ["training", "weekly"],
    queryFn: async () =>
      (await api.get<{ weekly_sets?: { muscles: WeeklyMuscle[] } | null }>("/api/training/analytics")).weekly_sets?.muscles ?? [],
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
          query ? `/api/training/exercises/search?q=${encodeURIComponent(query)}` : "/api/training/exercises/recent",
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

export const useNutritionDay = () =>
  useQuery({ queryKey: ["nutrition", "day"], queryFn: () => api.get<NutritionDay>(`/api/nutrition/day?locale=${locale()}`) });

export const useNutritionTips = () =>
  useQuery({
    queryKey: ["nutrition", "tips"],
    queryFn: async () =>
      (await api.get<{ recommendations: NutritionTip[] }>(`/api/nutrition/recommendations?locale=${locale()}`)).recommendations,
  });

export const useWater = () =>
  useQuery({
    queryKey: ["nutrition", "water"],
    queryFn: () => api.get<{ amount: number; recommended: number | null }>("/api/nutrition/water"),
  });

export const useWeight = () =>
  useQuery({ queryKey: ["nutrition", "weight"], queryFn: () => api.get<{ weight: number | null }>("/api/nutrition/weight") });

export const useNutritionHeatmap = () =>
  useQuery({
    queryKey: ["nutrition", "heatmap"],
    queryFn: () => recentYears<NutritionHeatmapDay>((year) => `/api/nutrition/heatmap?year=${year}`),
  });

const PRODUCT_URL: Record<ProductSource, (query: string) => string> = {
  all: (query) => `/api/nutrition/products?q=${encodeURIComponent(query)}&locale=${locale()}`,
  fav: () => `/api/nutrition/products/favorites?locale=${locale()}`,
  recent: () => `/api/nutrition/products/recent?locale=${locale()}`,
  mine: () => `/api/nutrition/products/mine?locale=${locale()}`,
};

export const useProducts = (source: ProductSource, query: string, enabled: boolean) =>
  useQuery({
    queryKey: ["nutrition", "products", source, source === "all" ? query : ""],
    queryFn: async () => (await api.get<{ products: Product[] }>(PRODUCT_URL[source](query))).products,
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

/* Recovery */

export const useRecoverySnapshot = () =>
  useQuery({
    queryKey: ["recovery", "snapshot"],
    queryFn: () => api.get<RecoverySnapshot>(`/api/recovery/snapshot/${userId()}`),
    retry: false,
  });

export const useRecoveryHeatmap = () =>
  useQuery({
    queryKey: ["recovery", "heatmap"],
    queryFn: async () => (await api.get<{ days: RecoveryHeatmapDay[] }>(`/api/recovery/heatmap/${userId()}`)).days,
  });

export const useHabitCatalog = (enabled: boolean) =>
  useQuery({
    queryKey: ["recovery", "catalog"],
    queryFn: () => api.get<HabitCatalogItem[]>("/api/recovery/habits/list"),
    enabled,
    staleTime: 5 * 60_000,
  });
