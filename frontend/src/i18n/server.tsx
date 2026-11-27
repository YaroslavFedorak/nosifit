import { useQueries } from "@tanstack/react-query";
import { createContext, use, useMemo, type ReactNode } from "react";
import { ApiError } from "../lib/api";
import { bootstrap } from "../lib/bootstrap";
import { interpolate, type Params } from "./index";

/**
 * Texts the server owns: recommendations arrive as translation keys, and the
 * names of exercises, muscles, habits and profile choices live in the
 * namespaces served at /api/i18n/<locale>/<namespace>. Reading them from
 * there keeps this interface and the Telegram bot on the same wording, in
 * every language the server has.
 */
type Tree = { [key: string]: string | Tree };

const NAMESPACES = ["training", "nutrition", "recovery", "dashboard", "exercises", "common"] as const;

export type OptionGroup = "goals" | "activity" | "genders" | "experience";

export interface ServerText {
  ready: boolean;
  /** Text for a key such as "recommendations.training.reasons.undertrained". */
  text: (key: string | null | undefined, params?: Params) => string | null;
  exercise: (slug: string | null | undefined, fallback: string) => string;
  muscle: (key: string) => string;
  habit: (slug: string | null | undefined, fallback: string) => string;
  habitHint: (slug: string | null | undefined, fallback?: string) => string;
  habitCategory: (key: string) => string;
  /** The label of a profile choice: option("goals", "fat_loss"). */
  option: (group: OptionGroup, key: string | null | undefined) => string | null;
}

const camel = (key: string): string => key.replace(/[-_]([a-z])/g, (_, c: string) => c.toUpperCase());
const sentence = (key: string): string => key.replace(/[-_]/g, " ").replace(/^./, (c) => c.toUpperCase());

function walk(tree: Tree | undefined, path: string[]): string | null {
  let node: string | Tree | undefined = tree;
  for (const part of path) {
    if (node === undefined || typeof node === "string") return null;
    node = node[part];
  }
  return typeof node === "string" ? node : null;
}

function build(trees: Array<Tree | undefined>): ServerText {
  const byName = Object.fromEntries(NAMESPACES.map((name, i) => [name, trees[i]])) as Record<(typeof NAMESPACES)[number], Tree | undefined>;
  const searchable = [byName.training, byName.nutrition, byName.recovery, byName.dashboard];
  return {
    ready: trees.every(Boolean),
    text(key, params) {
      if (!key) return null;
      const path = key.split(".");
      for (const tree of searchable) {
        const found = walk(tree, path);
        if (found) return interpolate(found, params);
      }
      return null;
    },
    exercise(slug, fallback) {
      return (slug && walk(byName.exercises, [slug, "name"])) || fallback;
    },
    muscle(key) {
      const names = byName.training?.muscles;
      const tree = typeof names === "object" ? names : undefined;
      return walk(tree, [key]) ?? walk(tree, [camel(key)]) ?? sentence(key);
    },
    habit(slug, fallback) {
      return (slug && walk(byName.recovery, ["habits", slug, "name"])) || fallback;
    },
    habitHint(slug, fallback = "") {
      return (slug && walk(byName.recovery, ["habits", slug, "description"])) || fallback;
    },
    habitCategory(key) {
      return walk(byName.recovery, ["categories", key]) ?? sentence(key);
    },
    option(group, key) {
      if (!key) return null;
      return walk(byName.common, ["profileOptions", group, key]) ?? walk(byName.common, ["profileOptions", group, camel(key)]);
    },
  };
}

const ServerTextContext = createContext<ServerText | null>(null);

/**
 * With the texts' version in the URL (from the page, web/app/routes/spa/pages.py)
 * the server lets the browser keep the answer until a deploy changes the
 * texts, so after the first visit they come from the cache without a request.
 * That is why, unlike other API reads, this one is not sent with cache: "no-store".
 */
export function serverTextUrl(namespace: string): string {
  const path = `/api/i18n/${bootstrap.locale}/${namespace}`;
  return bootstrap.textVersion ? `${path}?v=${encodeURIComponent(bootstrap.textVersion)}` : path;
}

async function fetchTree(namespace: string): Promise<Tree> {
  const response = await fetch(serverTextUrl(namespace), { credentials: "same-origin" });
  if (!response.ok) throw new ApiError(`HTTP ${response.status}`, response.status);
  return (await response.json()) as Tree;
}

export function ServerTextProvider({ children }: { children: ReactNode }) {
  const results = useQueries({
    queries: NAMESPACES.map((name) => ({
      queryKey: ["i18n", bootstrap.locale, name],
      queryFn: () => fetchTree(name),
      staleTime: Infinity,
      gcTime: Infinity,
    })),
  });
  const stamp = results.map((result) => result.dataUpdatedAt).join(",");
  // `results` is a new array on every render; the timestamps say when the data really changed.
  const value = useMemo(() => build(results.map((result) => result.data)), [stamp]);
  return <ServerTextContext value={value}>{children}</ServerTextContext>;
}

export function useServerText(): ServerText {
  const value = use(ServerTextContext);
  if (!value) throw new Error("useServerText must be used inside <ServerTextProvider>");
  return value;
}
