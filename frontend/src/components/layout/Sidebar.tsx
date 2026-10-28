import { LogOut } from "lucide-react";
import { Link, NavLink } from "react-router";
import { useT } from "../../i18n";
import { bootstrap } from "../../lib/bootstrap";
import { cn } from "../../lib/cn";
import { MoreMenu } from "./MoreMenu";
import { MAIN_NAV } from "./nav";

/** Desktop navigation. Below the desktop breakpoint the tab bar replaces it. */
export function Sidebar() {
  const { t } = useT();
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col gap-6 overflow-y-auto border-r border-line bg-canvas px-4 py-6 desk:flex">
      <Link to="/dashboard" className="px-2" aria-label={t("app.name")}>
        <img src="/static/img/brand/nosifit-lockup-on-dark.svg" alt={t("app.name")} className="h-8 w-auto" />
      </Link>

      <nav aria-label={t("nav.label")}>
        <ul className="space-y-1">
          {MAIN_NAV.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                data-accent={item.accent}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-tap items-center gap-3 rounded-xl px-3 text-sm font-semibold transition",
                    isActive ? "bg-surface-2 text-fg" : "text-fg-muted hover:bg-white/5 hover:text-fg",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon size={20} className={cn(isActive && item.accent && "text-accent")} aria-hidden="true" />
                    {t(item.label)}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-auto space-y-3">
        <div className="flex items-center justify-between gap-2 pl-2">
          <p className="min-w-0 truncate text-sm font-medium text-fg-muted">{bootstrap.user?.name}</p>
          <a
            href="/auth/logout"
            aria-label={t("more.logout")}
            title={t("more.logout")}
            className="inline-grid size-tap shrink-0 place-items-center rounded-xl text-fg-muted transition hover:bg-white/5 hover:text-danger"
          >
            <LogOut size={18} aria-hidden="true" />
          </a>
        </div>
        <MoreMenu compact />
      </div>
    </aside>
  );
}
