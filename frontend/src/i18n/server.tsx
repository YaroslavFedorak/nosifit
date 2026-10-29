import { useQueries } from "@tanstack/react-query";
import { createContext, use, useMemo, type ReactNode } from "react";
import { api } from "../lib/api";
import { bootstrap } from "../lib/bootstrap";
import { interpolate, type Params } from "./index";

/**
 * The API sends recommendations as translation keys. Their texts live in the
 * namespaces the server already serves at /api/i18n/<locale>/<namespace>, so
 * the new interface shows exactly the same wording as the classic one.
 */
type Tree = { [key: string]: string | Tree };

const NAMESPACES = ["training", "nutrition", "recovery", "dashboard", "exercises"] as const;

export interface ServerText {
  ready: boolean;
  /** Text for a key such as "recommendations.training.reasons.undertrained". */
  text: (key: string | null | undefined, params?: Params) => string | null;
  exercise: (slug: string | null | undefined, fallback: string) => string;
  muscle: (key: string) => string;
}

const camel = (key: string): string => key.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());

function walk(tree: Tree | undefined, path: string[]): string | null {
  let node: string | Tree | undefined = tree;
  for (const part of path) {
    if (node === undefined || typeof node === "string") return null;
    node = node[part];
  }
  return typeof node === "string" ? node : null;
}

function build(trees: Array<Tree | undefined>): ServerText {
  const byName = Object.fromEntries(NAMESPACES.map((name, i) => [name, trees[i]])) as Record<
    (typeof NAMESPACES)[number],
    Tree | undefined
  >;
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
      const muscles = byName.training?.muscles;
      const names = typeof muscles === "object" ? muscles : undefined;
      const label = walk(names, [key]) ?? walk(names, [camel(key)]);
      return label ?? key.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());
    },
  };
}

const ServerTextContext = createContext<ServerText | null>(null);

export function ServerTextProvider({ children }: { children: ReactNode }) {
  const results = useQueries({
    queries: NAMESPACES.map((name) => ({
      queryKey: ["i18n", bootstrap.locale, name],
      queryFn: () => api.get<Tree>(`/api/i18n/${bootstrap.locale}/${name}`),
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
