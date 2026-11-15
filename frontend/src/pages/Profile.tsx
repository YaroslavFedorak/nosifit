import { BookOpen, LogOut, Settings } from "lucide-react";
import { useState } from "react";
import { useAccount, useDiaryDay } from "../api/queries";
import { Page } from "../app/Page";
import { Avatar } from "../app/Sidebar";
import { ProfileSheet } from "../features/account/ProfileSheet";
import { useT } from "../i18n";
import { useServerText } from "../i18n/server";
import { dateText, num, parseDay } from "../lib/format";
import { Button } from "../ui/Button";
import { Empty, ErrorNote, Skeleton } from "../ui/Feedback";
import { Facts, Group, Panel, Row, Section } from "../ui/Layout";

export default function Profile() {
  const { t, locale } = useT();
  const text = useServerText();
  const account = useAccount();
  const diary = useDiaryDay();
  const [editing, setEditing] = useState(false);

  const data = account.data;
  const profile = data?.profile;
  const activityKey = data?.options.activities.find(([value]) => value === profile?.activity)?.[1];
  const location = profile?.training_location;

  const known: Array<{ label: string; value: string | number | null }> = profile
    ? [
        { label: t("profile.goal"), value: text.option("goals", profile.goal) },
        { label: t("profile.age"), value: profile.age },
        { label: t("profile.gender"), value: text.option("genders", profile.gender) },
        { label: t("profile.height"), value: profile.height != null ? `${num(profile.height)} ${t("unit.cm")}` : null },
        { label: t("profile.weight"), value: profile.weight != null ? `${num(profile.weight)} ${t("unit.kg")}` : null },
        { label: t("profile.activity"), value: text.option("activity", activityKey) },
        { label: t("profile.experience"), value: text.option("experience", profile.experience) },
        { label: t("profile.workouts"), value: profile.workouts_per_week },
        {
          label: t("profile.location"),
          value: location === "gym" || location === "home" || location === "outdoor" ? t(`profile.location.${location}`) : null,
        },
      ]
    : [];
  const facts = known.filter((fact): fact is { label: string; value: string | number } => fact.value != null && fact.value !== "");

  const day = diary.data;

  return (
    <Page title={t("nav.profile")}>
      {account.isError ? (
        <ErrorNote onRetry={() => void account.refetch()} />
      ) : !data ? (
        <div className="grid gap-6 desk:grid-cols-12" aria-busy="true">
          <Skeleton className="h-72 desk:col-span-7" />
          <Skeleton className="h-48 desk:col-span-5" />
        </div>
      ) : (
        <div className="grid gap-x-[var(--gap-columns)] gap-y-8 desk:grid-cols-12 desk:items-start">
          <div className="space-y-8 desk:col-span-7">
            <div className="flex items-center gap-4">
              <Avatar name={data.user.name} className="size-14 text-xl" />
              <div className="min-w-0">
                <h2 className="truncate text-xl">{data.user.name}</h2>
                <p className="truncate text-sm text-muted">{data.user.email}</p>
                {data.user.member_since && (
                  <p className="mt-0.5 text-sm text-muted">
                    {t("profile.since", { date: dateText(locale, parseDay(data.user.member_since), { day: "numeric", month: "long", year: "numeric" }) })}
                  </p>
                )}
              </div>
            </div>

            <Section title={t("profile.params")} action={facts.length > 0 ? <Button onClick={() => setEditing(true)}>{t("common.edit")}</Button> : undefined}>
              {facts.length <= 2 ? (
                <Panel>
                  <Empty
                    title={t("profile.empty")}
                    text={t("profile.emptyText")}
                    action={
                      <Button variant="primary" onClick={() => setEditing(true)}>
                        {t("profile.fill")}
                      </Button>
                    }
                  />
                </Panel>
              ) : (
                <Panel className="py-1.5">
                  <Facts items={facts} />
                </Panel>
              )}
            </Section>
          </div>

          <div className="space-y-8 desk:col-span-5">
            {day?.hasGoals && (
              <Section title={t("profile.targets")} note={t("profile.targetsNote")}>
                <Panel className="py-1.5">
                  <Facts
                    items={[
                      { label: t("food.energy"), value: `${num(day.kcalGoal, 0)} ${t("unit.kcal")}` },
                      { label: t("food.protein"), value: `${num(day.proteinGoal, 0)} ${t("unit.g")}` },
                      { label: t("food.fat"), value: `${num(day.fatGoal, 0)} ${t("unit.g")}` },
                      { label: t("food.carbs"), value: `${num(day.carbsGoal, 0)} ${t("unit.g")}` },
                      ...(day.waterGoal ? [{ label: t("water.title"), value: `${num(day.waterGoal)} ${t("unit.l")}` }] : []),
                    ]}
                  />
                </Panel>
              </Section>
            )}

            <Group>
              <Row leading={<Settings size={20} className="text-ink-2" aria-hidden="true" />} title={t("nav.settings")} subtitle={t("profile.settingsHint")} chevron to="/settings" />
              <Row leading={<BookOpen size={20} className="text-ink-2" aria-hidden="true" />} title={t("nav.how")} chevron to="/how-it-works" />
              <Row leading={<LogOut size={20} className="text-ink-2" aria-hidden="true" />} title={t("account.logout")} href="/auth/logout" />
            </Group>
          </div>
        </div>
      )}

      {editing && data && <ProfileSheet account={data} onClose={() => setEditing(false)} />}
    </Page>
  );
}
