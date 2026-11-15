import { Plus } from "lucide-react";
import { NavLink } from "react-router";
import { useLog } from "../features/log/LogProvider";
import { useT } from "../i18n";
import { cn } from "../lib/cn";
import { MAIN_NAV, type NavItem } from "./nav";

function Tab({ item }: { item: NavItem }) {
  const { t } = useT();
  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        cn(
          "relative flex h-tabbar min-w-0 flex-1 flex-col items-center justify-center gap-1 text-xs font-medium transition-colors duration-150 tracking-[-0.01em] max-[23rem]:text-[0.6875rem]",
          isActive ? "text-ink" : "text-muted",
        )
      }
    >
      {({ isActive }) => (
        <>
          <span className={cn("absolute top-0 h-0.5 w-8 rounded-pill bg-accent transition-opacity duration-150", isActive ? "opacity-100" : "opacity-0")} aria-hidden="true" />
          <item.icon size={22} aria-hidden="true" />
          <span className="max-w-full truncate">{t(item.label)}</span>
        </>
      )}
    </NavLink>
  );
}

/**
 * The phone's navigation: two places on each side of the one action the app
 * is opened for, recording something.
 */
export function TabBar() {
  const { t } = useT();
  const log = useLog();
  const [today, nutrition, training, recovery] = MAIN_NAV;
  return (
    <nav aria-label={t("nav.label")} className="fixed inset-x-0 bottom-0 z-[300] border-t border-rule bg-paper pb-[env(safe-area-inset-bottom)] tab:hidden">
      <div className="mx-auto flex max-w-xl items-stretch">
        {today && <Tab item={today} />}
        {nutrition && <Tab item={nutrition} />}
        <div className="flex w-14 shrink-0 items-center justify-center">
          <button
            type="button"
            onClick={() => log.open({ kind: "menu" })}
            aria-label={t("log.add")}
            aria-haspopup="dialog"
            className="press grid size-12 place-items-center rounded-pill bg-accent text-accent-ink hover:bg-accent-2"
          >
            <Plus size={24} aria-hidden="true" />
          </button>
        </div>
        {training && <Tab item={training} />}
        {recovery && <Tab item={recovery} />}
      </div>
    </nav>
  );
}
