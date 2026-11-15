import { useEffect } from "react";
import { Outlet, useLocation } from "react-router";
import { LogProvider } from "../features/log/LogProvider";
import { useT } from "../i18n";
import { ServerTextProvider } from "../i18n/server";
import { ToastHost } from "../ui/Feedback";
import { Sidebar } from "./Sidebar";
import { TabBar } from "./TabBar";

/**
 * The signed-in frame. Navigation sits beside the content from the tablet
 * width up and under it on a phone; the content keeps one capped, centred
 * column whatever the screen.
 */
export function AppShell() {
  const { t } = useT();
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <ServerTextProvider>
      <LogProvider>
        <a href="#main" className="skip">
          {t("nav.skip")}
        </a>
        <Sidebar />
        <main
          id="main"
          tabIndex={-1}
          className="min-h-dvh pb-[calc(var(--tabbar)+env(safe-area-inset-bottom)+1.5rem)] pt-[max(1rem,env(safe-area-inset-top))] outline-none tab:pb-10 tab:pl-rail tab:pt-6 desk:pl-sidebar desk:pt-8"
        >
          <div className="page">
            <Outlet />
          </div>
        </main>
        <TabBar />
        <ToastHost />
      </LogProvider>
    </ServerTextProvider>
  );
}
