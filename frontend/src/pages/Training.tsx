import { useSearchParams } from "react-router";
import { Page } from "../app/Page";
import { HistoryTab } from "../features/training/HistoryTab";
import { PlanTab } from "../features/training/PlanTab";
import { TodayTab } from "../features/training/TodayTab";
import { useT } from "../i18n";
import { Tabs, type Option } from "../ui/Choice";

type TabId = "today" | "plan" | "history";
const TAB_IDS: TabId[] = ["today", "plan", "history"];

export default function Training() {
  const { t } = useT();
  const [params, setParams] = useSearchParams();
  const requested = params.get("tab");
  const tab: TabId = TAB_IDS.find((id) => id === requested) ?? "today";

  const options: Option<TabId>[] = [
    { id: "today", label: t("training.tab.today") },
    { id: "plan", label: t("training.tab.plan") },
    { id: "history", label: t("training.tab.history") },
  ];

  return (
    <Page title={t("nav.training")} tone="training">
      <Tabs options={options} value={tab} label={t("training.tabs")} onChange={(id) => setParams(id === "today" ? {} : { tab: id }, { replace: true })} className="mb-6" />
      <div role="tabpanel">
        {tab === "today" ? <TodayTab openPicker={params.get("sheet") === "exercise"} /> : tab === "plan" ? <PlanTab /> : <HistoryTab />}
      </div>
    </Page>
  );
}
