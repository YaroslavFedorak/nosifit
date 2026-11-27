import { Plus, Settings } from "lucide-react";
import { Link, NavLink } from "react-router";
import { useLog } from "../features/log/LogProvider";
import { useT } from "../i18n";
import { bootstrap } from "../lib/bootstrap";
import { cn } from "../lib/cn";
import { MAIN_NAV } from "./nav";
import { brand } from "../brand";

const ITEM =
  "press flex min-h-tap items-center rounded-control font-medium flex-col justify-center gap-1 py-2 text-xs desk:flex-row desk:justify-start desk:gap-3 desk:px-3 desk:py-0 desk:text-sm";
const itemState = (active: boolean): string => (active ? "bg-paper-3 text-ink" : "text-muted hover:bg-paper-2 hover:text-ink");

export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span aria-hidden="true" className={cn("grid size-8 shrink-0 place-items-center rounded-pill bg-paper-4 text-sm font-semibold text-ink", className)}>
      {(name.trim()[0] ?? "?").toLocaleUpperCase()}
    </span>
  );
}

/**
 * Navigation from the tablet width up: a narrow rail with a label under each
 * icon, widening on a desktop to a sidebar with the labels beside them. On a
 * phone the tab bar takes its place.
 */
export function Sidebar() {
  const { t } = useT();
  const log = useLog();
  const name = bootstrap.user?.name ?? "";

  return (
    <aside className="fixed inset-y-0 left-0 z-[300] hidden w-rail flex-col gap-4 border-r border-rule bg-paper px-2 py-4 tab:flex desk:w-sidebar desk:px-4 desk:py-6">
      <Link to="/dashboard" aria-label={t("app.name")} className="flex h-10 items-center justify-center desk:justify-start desk:px-2">
        <img src={brand.mark} alt="" className="h-8 w-auto desk:hidden" />
        <img src={brand.lockup} alt="" className="hidden h-7 w-auto desk:block" />
      </Link>

      <button
        type="button"
        onClick={() => log.open({ kind: "menu" })}
        aria-haspopup="dialog"
        className="press flex min-h-control-lg flex-col items-center justify-center gap-0.5 rounded-control bg-accent text-xs font-medium text-accent-ink hover:bg-accent-2 desk:flex-row desk:gap-2 desk:text-sm"
      >
        <Plus size={20} aria-hidden="true" />
        {t("log.add")}
      </button>

      <nav aria-label={t("nav.label")}>
        <ul className="space-y-1">
          {MAIN_NAV.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} data-tone={item.tone} className={({ isActive }) => cn(ITEM, itemState(isActive))}>
                {({ isActive }) => (
                  <>
                    <item.icon size={20} className={cn(isActive && "text-accent")} aria-hidden="true" />
                    <span className="max-w-full truncate">{t(item.label)}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-auto space-y-1">
        <NavLink to="/settings" className={({ isActive }) => cn(ITEM, itemState(isActive))}>
          <Settings size={20} aria-hidden="true" />
          <span className="max-w-full truncate">{t("nav.settings")}</span>
        </NavLink>
        <NavLink to="/profile" className={({ isActive }) => cn(ITEM, itemState(isActive))}>
          <Avatar name={name} className="size-7 desk:size-8" />
          <span className="max-w-full truncate">{name || t("nav.profile")}</span>
        </NavLink>
      </div>
    </aside>
  );
}
