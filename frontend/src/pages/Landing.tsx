import { CircleCheck, Droplets, Dumbbell, Flame, HeartPulse, Moon, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { buttonClass } from "../components/ui/Button";
import { Card, type Accent } from "../components/ui/Card";
import { Badge } from "../components/ui/Chip";
import { Ring } from "../components/ui/Ring";
import { useT } from "../i18n";
import type { TKey } from "../i18n/en";
import { useTitle } from "../lib/useTitle";
import { LandingFooter, LandingHeader } from "./landing/Chrome";

function ExampleRow({ icon: Icon, accent, label, value }: { icon: LucideIcon; accent: Accent; label: string; value: string }) {
  return (
    <li data-accent={accent} className="flex min-h-12 items-center gap-3 border-t border-line py-2">
      <Icon size={18} className="shrink-0 text-accent" aria-hidden="true" />
      <span className="flex-1 text-sm text-fg-muted">{label}</span>
      <span className="text-sm font-semibold tabular-nums">{value}</span>
    </li>
  );
}

const MODULES: Array<{ accent: Accent; icon: LucideIcon; title: TKey; text: TKey }> = [
  { accent: "training", icon: Dumbbell, title: "nav.training", text: "lp.mod.training" },
  { accent: "nutrition", icon: UtensilsCrossed, title: "nav.nutrition", text: "lp.mod.nutrition" },
  { accent: "recovery", icon: HeartPulse, title: "nav.recovery", text: "lp.mod.recovery" },
];

export default function Landing() {
  const { t } = useT();
  useTitle(t("lp.hero.title"));

  return (
    <div className="min-h-dvh">
      <LandingHeader />
      <main>
        {/* 1. Hero: one promise, one example day. */}
        <section className="mx-auto grid max-w-6xl gap-8 px-4 pb-14 pt-10 tab:grid-cols-2 tab:items-center tab:gap-10 tab:px-6 tab:pt-16">
          <div>
            <h1 className="text-[2.5rem] font-semibold leading-[1.08] tracking-tight text-balance tab:text-5xl">{t("lp.hero.title")}</h1>
            <p className="mt-4 text-base leading-relaxed text-fg-muted text-pretty">{t("lp.hero.text")}</p>
            <div className="mt-7 space-y-2.5 tab:max-w-xs">
              <a href="/auth/register" className={buttonClass({ variant: "primary", size: "lg", block: true })}>
                {t("lp.hero.cta")}
              </a>
              <a href="/demo" className={buttonClass({ block: true })}>
                {t("lp.hero.demo")}
              </a>
            </div>
            <p className="mt-3 text-sm text-fg-soft">{t("lp.hero.note")}</p>
          </div>

          <Card tone="hero" accent="training" aria-label={t("lp.card.label")}>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold">{t("lp.card.label")}</p>
              <Badge>{t("lp.card.badge")}</Badge>
            </div>
            <div className="mt-5 flex justify-center">
              <Ring value={0.72} size={150} stroke={12} glow label={`${t("lp.card.score")}: 72`}>
                <div>
                  <div className="text-5xl font-semibold leading-none tracking-tight tabular-nums">72</div>
                  <div className="mt-1.5 text-xs font-medium text-fg-muted">{t("lp.card.score")}</div>
                </div>
              </Ring>
            </div>
            <ul className="mt-5">
              <ExampleRow icon={Dumbbell} accent="training" label={t("lp.card.workout")} value={t("lp.card.workoutValue")} />
              <ExampleRow icon={Flame} accent="nutrition" label={t("lp.card.kcal")} value="560" />
              <ExampleRow icon={Moon} accent="recovery" label={t("lp.card.sleep")} value={t("lp.card.sleepValue")} />
            </ul>
          </Card>
        </section>

        {/* 2. The three modules. */}
        <section className="border-t border-line">
          <div className="mx-auto max-w-6xl px-4 py-14 tab:px-6">
            <h2 className="text-3xl font-semibold leading-tight tracking-tight text-balance">{t("lp.mod.title")}</h2>
            <ul className="mt-7 grid gap-3 tab:grid-cols-3">
              {MODULES.map(({ accent, icon: Icon, title, text }) => (
                <Card as="li" key={accent} accent={accent} strip>
                  <h3 className="flex items-center gap-3 text-lg font-semibold">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-accent-soft bg-accent-soft text-accent" aria-hidden="true">
                      <Icon size={20} />
                    </span>
                    {t(title)}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-fg-muted">{t(text)}</p>
                </Card>
              ))}
            </ul>
          </div>
        </section>

        {/* 3. Telegram. */}
        <section className="border-t border-line">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 tab:grid-cols-2 tab:items-center tab:gap-10 tab:px-6">
            <div>
              <h2 className="text-3xl font-semibold leading-tight tracking-tight text-balance">{t("lp.tg.title")}</h2>
              <p className="mt-3 text-base leading-relaxed text-fg-muted text-pretty">{t("lp.tg.text")}</p>
              <ul className="mt-5 space-y-3 text-sm text-fg-muted">
                {(["lp.tg.b1", "lp.tg.b2"] as const).map((key) => (
                  <li key={key} className="flex gap-3">
                    <CircleCheck size={18} className="mt-0.5 shrink-0 text-ok" aria-hidden="true" />
                    <span>{t(key)}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Card tone="glass" aria-label={t("lp.tg.bot")} className="space-y-4">
              <div className="flex items-center gap-3 border-b border-white/8 pb-3">
                <img src="/static/img/brand/nosifit-icon.svg" alt="" className="size-10 rounded-full" />
                <div>
                  <p className="text-sm font-semibold">{t("lp.tg.bot")}</p>
                  <p className="text-xs text-fg-muted">bot</p>
                </div>
                <Badge>{t("lp.card.badge")}</Badge>
              </div>
              <div className="flex justify-end">
                <span className="inline-flex items-center gap-2 rounded-2xl rounded-br-md border border-water/30 bg-water/12 px-4 py-2.5 text-sm font-medium">
                  <Droplets size={16} className="text-water" aria-hidden="true" />
                  {t("lp.tg.user")}
                </span>
              </div>
              <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-white/8 bg-white/5 px-4 py-3 text-sm">
                <p className="flex items-center gap-2 font-semibold">
                  <CircleCheck size={16} className="text-ok" aria-hidden="true" />
                  {t("lp.tg.reply")}
                </p>
                <p className="mt-1 text-fg-muted">{t("lp.tg.today")}</p>
              </div>
              <div className="grid grid-cols-4 gap-2" aria-hidden="true">
                {["+0.25", "+0.33", "+0.5", "+1"].map((amount) => (
                  <span key={amount} className="grid min-h-tap place-items-center rounded-xl border border-line-strong bg-surface-2 text-sm font-semibold tabular-nums">
                    {amount}
                  </span>
                ))}
              </div>
            </Card>
          </div>
        </section>

        {/* 4. Call to action. */}
        <section className="border-t border-line">
          <div className="mx-auto max-w-3xl px-4 py-16 text-center tab:px-6">
            <h2 className="text-3xl font-semibold leading-tight tracking-tight text-balance tab:text-4xl">{t("lp.cta.title")}</h2>
            <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-fg-muted text-pretty">{t("lp.cta.text")}</p>
            <div className="mx-auto mt-7 max-w-xs space-y-2.5">
              <a href="/auth/register" className={buttonClass({ variant: "primary", size: "lg", block: true })}>
                {t("lp.hero.cta")}
              </a>
              <a href="/demo" className={buttonClass({ block: true })}>
                {t("lp.hero.demo")}
              </a>
            </div>
          </div>
        </section>
      </main>
      <LandingFooter />
    </div>
  );
}
