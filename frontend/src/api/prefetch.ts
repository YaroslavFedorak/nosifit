import type { QueryClient } from "@tanstack/react-query";
import { bootstrap } from "../lib/bootstrap";
import { isoDay } from "../lib/format";
import {
  dashboardHeatmapQuery,
  dashboardRecommendationQuery,
  diaryDayQuery,
  habitsQuery,
  nutritionStatsQuery,
  nutritionTipsQuery,
  plansQuery,
  recoverySnapshotQuery,
  trainingHeatmapQuery,
  trainingRecommendationsQuery,
  trainingSessionQuery,
  trainingTodayQuery,
  waterQuery,
  weightQuery,
} from "./queries";

type Prefetch = (client: QueryClient) => Promise<void>;

/**
 * What each page reads the moment it opens. Without this the requests start
 * only after the bundle has run, the page's code has loaded and React has
 * rendered it; started from main.tsx they go out right away, while the rest
 * is still being prepared. The page then finds the answers (or the requests
 * in flight) under the same keys and does not ask again.
 *
 * Only the default view of each page: a page opened on another day or tab
 * fetches what it needs itself.
 */
const PAGE_DATA: Record<string, () => Prefetch[]> = {
  "/dashboard": () => [
    (c) => c.prefetchQuery(diaryDayQuery(isoDay())),
    (c) => c.prefetchQuery(waterQuery(isoDay())),
    (c) => c.prefetchQuery(recoverySnapshotQuery()),
    (c) => c.prefetchQuery(habitsQuery()),
    (c) => c.prefetchQuery(trainingSessionQuery()),
    (c) => c.prefetchQuery(trainingTodayQuery()),
    (c) => c.prefetchQuery(dashboardHeatmapQuery()),
    (c) => c.prefetchQuery(dashboardRecommendationQuery()),
    (c) => c.prefetchQuery(nutritionStatsQuery(7)),
    (c) => c.prefetchQuery(trainingHeatmapQuery()),
    (c) => c.prefetchQuery(weightQuery()),
  ],
  "/nutrition": () => [
    (c) => c.prefetchQuery(diaryDayQuery(isoDay())),
    (c) => c.prefetchQuery(weightQuery()),
    (c) => c.prefetchQuery(nutritionTipsQuery()),
    (c) => c.prefetchQuery(waterQuery(isoDay())),
    (c) => c.prefetchQuery(nutritionStatsQuery(7)),
  ],
  "/training": () => [
    (c) => c.prefetchQuery(trainingSessionQuery()),
    (c) => c.prefetchQuery(trainingRecommendationsQuery()),
    (c) => c.prefetchQuery(plansQuery()),
  ],
  "/recovery": () => [(c) => c.prefetchQuery(recoverySnapshotQuery()), (c) => c.prefetchQuery(habitsQuery())],
};

/** Starts the requests of the page at ``location`` (signed-in pages only). */
export function prefetchPage(client: QueryClient, location: Location): void {
  if (!bootstrap.user) return;
  const params = new URLSearchParams(location.search);
  // Another day, tab or sheet: not the default view listed above.
  if (params.has("date") || params.has("tab")) return;
  const page = location.pathname.replace(/^\/app/, "").replace(/\/+$/, "");
  for (const start of PAGE_DATA[page]?.() ?? []) void start(client);
}
