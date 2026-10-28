import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

/**
 * Expands in place. Nothing inside a card ever scrolls on its own: long lists
 * grow the page and the user decides with a "Show more" button.
 */
export function Collapse({ open, children, id }: { open: boolean; children: ReactNode; id?: string }) {
  return (
    <div
      id={id}
      className={cn("grid transition-[grid-template-rows] duration-200 ease-out", open ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}
    >
      <div className="min-h-0 overflow-hidden" inert={!open}>
        {children}
      </div>
    </div>
  );
}
