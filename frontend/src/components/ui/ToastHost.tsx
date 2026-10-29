import { CircleCheck, TriangleAlert } from "lucide-react";
import { cn } from "../../lib/cn";
import { useToasts } from "../../lib/toast";

export function ToastHost() {
  const items = useToasts();
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 top-[max(0.75rem,env(safe-area-inset-top))] z-[60] flex flex-col items-center gap-2 px-4"
    >
      {items.map((item) => (
        <div
          key={item.id}
          className={cn(
            "anim-rise pointer-events-auto flex max-w-md items-center gap-2 rounded-xl border bg-surface-3/95 px-4 py-3 text-sm font-medium shadow-xl backdrop-blur",
            item.tone === "ok" ? "border-ok/30" : "border-danger/40",
          )}
        >
          {item.tone === "ok" ? (
            <CircleCheck className="shrink-0 text-ok" size={18} aria-hidden="true" />
          ) : (
            <TriangleAlert className="shrink-0 text-danger" size={18} aria-hidden="true" />
          )}
          {item.text}
        </div>
      ))}
    </div>
  );
}
