import { createContext, use, type ReactNode } from "react";
import type { Tone } from "../design/tokens";

/**
 * The module a part of the screen belongs to. Sheets render outside the page in the DOM, so they
 * read the module from here to wear its colour.
 */
const ToneContext = createContext<Tone | undefined>(undefined);

export const useTone = (): Tone | undefined => use(ToneContext);

export function ToneScope({ tone, className, children }: { tone?: Tone; className?: string; children: ReactNode }) {
  return (
    <ToneContext value={tone}>
      <div data-tone={tone} className={className}>
        {children}
      </div>
    </ToneContext>
  );
}
