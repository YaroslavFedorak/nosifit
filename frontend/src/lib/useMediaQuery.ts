import { useSyncExternalStore } from "react";

/** True while the media query matches; follows resizes and rotations. */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Match the `tab:` and `desk:` breakpoints in tokens.css. */
export const TABLET = "(min-width: 48rem)";
export const DESKTOP = "(min-width: 68.75rem)";
