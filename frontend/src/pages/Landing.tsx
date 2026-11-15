import { Dumbbell, HeartPulse, UtensilsCrossed, type LucideIcon } from "lucide-react";
import type { Tone } from "../design/tokens";
import { useT } from "../i18n";
import type { TKey } from "../i18n/en";
import { useTitle } from "../lib/useTitle";
import { buttonClass } from "../ui/Button";
import { LandingFooter, LandingHeader } from "./landing/Chrome";

const MODULES: Array<{ tone: Tone; icon: LucideIcon; title: TKey; text: TKey }> = [
  { tone: "nutrition", icon: UtensilsCrossed, title: "nav.nutrition", text: "lp.mod.nutrition" },
  { tone: "training", icon: Dumbbell, title: "nav.training", text: "lp.mod.training" },
  { tone: "recovery", icon: HeartPulse, title: "nav.recovery", text: "lp.mod.recovery" },
];

function Actions() {
  const { t } = useT();
  return (
    <div className="flex flex-wrap gap-2">
      <a href="/auth/register" className={buttonClass({ variant: "primary", size: "lg" })}>
        {t("lp.hero.cta")}
      </a>
      <a href="/demo" className={buttonClass({ size: "lg" })}>
        {t("lp.hero.demo")}
      </a>
    </div>
  );
}

export default function Landing() {
  const { t } = useT();
  useTitle(t("lp.hero.title"));

  return (
    <div className="flex min-h-dvh flex-col">
      <LandingHeader />
      <main className="flex-1">
        <section className="page grid gap-x-16 gap-y-12 py-12 desk:grid-cols-12 desk:items-center desk:py-24">
          <div className="desk:col-span-6">
            <h1 className="max-w-[16ch] text-3xl leading-[1.08] desk:text-[3.25rem]">{t("lp.hero.title")}</h1>
            <p className="mb-8 mt-5 max-w-[46ch] text-lg text-ink-2">{t("lp.hero.text")}</p>
            <Actions />
            <p className="mt-4 text-sm text-muted">{t("lp.hero.note")}</p>
          </div>

          <dl className="divide-y divide-rule border-y border-rule desk:col-span-6" aria-label={t("lp.mod.title")}>
            {MODULES.map(({ tone, icon: Icon, title, text }) => (
              <div key={title} data-tone={tone} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 py-6">
                <Icon size={24} className="mt-0.5 text-tone" aria-hidden="true" />
                <div>
                  <dt className="text-lg font-semibold tracking-[-0.01em]">{t(title)}</dt>
                  <dd className="mt-1.5 max-w-[48ch] text-ink-2">{t(text)}</dd>
                </div>
              </div>
            ))}
          </dl>
        </section>

        <section className="border-t border-rule bg-paper-2">
          <div className="page grid gap-x-16 gap-y-6 py-16 desk:grid-cols-12 desk:py-24">
            <h2 className="max-w-[18ch] text-2xl desk:col-span-5 desk:text-3xl">{t("lp.tg.title")}</h2>
            <div className="desk:col-span-7">
              <p className="max-w-[52ch] text-lg text-ink-2">{t("lp.tg.text")}</p>
              <ul className="mt-6 max-w-[52ch] space-y-3 border-t border-rule pt-6 text-ink-2">
                <li>{t("lp.tg.b1")}</li>
                <li>{t("lp.tg.b2")}</li>
              </ul>
            </div>
          </div>
        </section>

        <section className="page py-16 desk:py-24">
          <h2 className="max-w-[20ch] text-2xl desk:text-3xl">{t("lp.cta.title")}</h2>
          <p className="mb-8 mt-4 max-w-[48ch] text-lg text-ink-2">{t("lp.cta.text")}</p>
          <Actions />
        </section>
      </main>
      <LandingFooter />
    </div>
  );
}
