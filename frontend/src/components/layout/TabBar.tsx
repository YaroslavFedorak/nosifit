import { Menu } from "lucide-react";
import { NavLink } from "react-router";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";
import { MAIN_NAV } from "./nav";

const ITEM =
  "relative flex h-tabbar w-full flex-col items-center justify-center gap-1 px-0.5 text-xs font-medium tracking-tight transition-colors";

/** Five tabs: the four modules and "More". Labels stay at 12px. */
export function TabBar({ onMore }: { onMore: () => void }) {
  const { t } = useT();
  return (
    <nav
      aria-label={t("nav.label")}
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-canvas/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl desk:hidden"
    >
      <ul className="mx-auto grid max-w-xl grid-cols-5">
        {MAIN_NAV.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              data-accent={item.accent}
              className={({ isActive }) => cn(ITEM, isActive ? "text-fg" : "text-fg-soft hover:text-fg-muted")}
            >
              {({ isActive }) => (
                <>
                  <span
                    className={cn("absolute top-0 h-0.5 w-8 rounded-full bg-accent transition-opacity", isActive ? "opacity-100" : "opacity-0")}
                    aria-hidden="true"
                  />
                  <item.icon size={22} className={cn(isActive && (item.accent ? "text-accent" : "text-fg"))} aria-hidden="true" />
                  <span className="whitespace-nowrap">{t(item.label)}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
        <li>
          <button type="button" onClick={onMore} aria-haspopup="dialog" className={cn(ITEM, "text-fg-soft hover:text-fg-muted")}>
            <Menu size={22} aria-hidden="true" />
            <span className="whitespace-nowrap">{t("nav.more")}</span>
          </button>
        </li>
      </ul>
    </nav>
  );
}
