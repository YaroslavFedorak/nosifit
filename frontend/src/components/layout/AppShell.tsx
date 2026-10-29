import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router";
import { useT } from "../../i18n";
import { ServerTextProvider } from "../../i18n/server";
import { Sheet } from "../ui/Sheet";
import { ToastHost } from "../ui/ToastHost";
import { MoreMenu } from "./MoreMenu";
import { Sidebar } from "./Sidebar";
import { TabBar } from "./TabBar";

/** Signed-in frame: sidebar on desktop, tab bar and "More" sheet everywhere else. */
export function AppShell() {
  const { t } = useT();
  const { pathname } = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    setMoreOpen(false);
  }, [pathname]);

  return (
    <ServerTextProvider>
      <div className="min-h-dvh desk:pl-64">
        <Sidebar />
        {/* On wide monitors the content grows to 88rem and the card grids add columns,
            instead of a narrow column between two empty margins. */}
        <main className="mx-auto w-full max-w-5xl px-4 pt-[max(1rem,env(safe-area-inset-top))] pb-[calc(var(--spacing-tabbar)+env(safe-area-inset-bottom)+1.5rem)] tab:px-6 desk:max-w-[88rem] desk:px-10 desk:pt-8 desk:pb-12">
          <Outlet />
        </main>
        <TabBar onMore={() => setMoreOpen(true)} />
        <Sheet open={moreOpen} onClose={() => setMoreOpen(false)} title={t("more.title")}>
          <MoreMenu onNavigate={() => setMoreOpen(false)} />
        </Sheet>
        <ToastHost />
      </div>
    </ServerTextProvider>
  );
}
