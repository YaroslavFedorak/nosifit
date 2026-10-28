import { Dumbbell } from "lucide-react";
import { useSearchParams } from "react-router";
import { PageHeader } from "../components/ui/PageHeader";
import { Tabs, type TabItem } from "../components/ui/Tabs";
import { useT } from "../i18n";
import { useTitle } from "../lib/useTitle";
import { HistoryTab } from "./training/HistoryTab";
import { TipsTab } from "./training/TipsTab";
import { TodayTab } from "./training/TodayTab";

type TabId = "today" | "history" | "tips";
const TAB_IDS: TabId[] = ["today", "history", "tips"];

export default function Training() {
  const { t } = useT();
  useTitle(t("nav.training"));
  const [params, setParams] = useSearchParams();
  const requested = params.get("tab");
  const tab: TabId = TAB_IDS.find((id) => id === requested) ?? "today";

  const items: TabItem<TabId>[] = [
    { id: "today", label: t("tr.tab.today") },
    { id: "history", label: t("tr.tab.history") },
    { id: "tips", label: t("tr.tab.tips") },
  ];

  return (
    <div data-accent="training">
      <PageHeader title={t("tr.title")} subtitle={t("tr.subtitle")} icon={Dumbbell} accent="training" />
      <div className="tab:max-w-md">
        <Tabs
          items={items}
          value={tab}
          label={t("tr.tabs")}
          onChange={(id) => setParams(id === "today" ? {} : { tab: id }, { replace: true })}
        />
      </div>
      <div className="mt-4" role="tabpanel">
        {tab === "today" ? <TodayTab /> : tab === "history" ? <HistoryTab /> : <TipsTab />}
      </div>
    </div>
  );
}
