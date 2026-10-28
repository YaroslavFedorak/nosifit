import { buttonClass } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Chip, type Tone } from "../components/ui/Chip";
import { useT } from "../i18n";
import type { TKey } from "../i18n/en";
import { bootstrap } from "../lib/bootstrap";
import { cn } from "../lib/cn";
import { useTitle } from "../lib/useTitle";
import { LandingFooter, LandingHeader } from "./landing/Chrome";

const DAYS: Array<{ day: TKey; chips: TKey[]; result: TKey; tone: Tone }> = [
  { day: "hw.context.a.day", chips: ["hw.context.a.sleep", "hw.context.a.kcal", "hw.context.a.ready"], result: "hw.context.a.result", tone: "ok" },
  { day: "hw.context.b.day", chips: ["hw.context.b.sleep", "hw.context.b.kcal", "hw.context.b.ready"], result: "hw.context.b.result", tone: "warn" },
];

const STEPS: Array<{ title: TKey; text: TKey }> = [
  { title: "hw.model.s1.t", text: "hw.model.s1.d" },
  { title: "hw.model.s2.t", text: "hw.model.s2.d" },
  { title: "hw.model.s3.t", text: "hw.model.s3.d" },
  { title: "hw.model.s4.t", text: "hw.model.s4.d" },
];

/** A decorative month of days; the real calendar lives in each module. */
const SAMPLE_LEVELS = [0, 2, 3, 0, 4, 1, 0, 3, 4, 2, 0, 0, 3, 1, 4, 3, 0, 2, 4, 0, 1, 0, 3, 4, 2, 0, 3, 3, 0, 4, 1, 2, 0, 3, 4];

function Eyebrow({ children }: { children: string }) {
  return <p className="text-xs font-semibold uppercase tracking-widest text-fg-muted">{children}</p>;
}

function Content() {
  const { t } = useT();
  return (
    <div className="mx-auto max-w-5xl space-y-14 px-4 py-8 tab:px-6 tab:py-12">
      <header>
        <h1 className="text-4xl font-semibold leading-tight tracking-tight text-balance">{t("hw.title")}</h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-fg-muted text-pretty">{t("hw.lead")}</p>
      </header>

      <section aria-labelledby="hw-context">
        <Eyebrow>{t("hw.context.eyebrow")}</Eyebrow>
        <h2 id="hw-context" className="mt-3 text-2xl font-semibold tracking-tight text-balance">
          {t("hw.context.title")}
        </h2>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-fg-muted text-pretty">{t("hw.context.text")}</p>
        <ul className="mt-6 grid gap-3 tab:grid-cols-2">
          {DAYS.map(({ day, chips, result, tone }) => (
            <Card as="li" key={day} accent="training" className="space-y-3">
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-sm font-semibold text-fg-muted">{t(day)}</span>
                <span className="text-sm font-medium">{t("hw.context.lift")}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {chips.map((chip) => (
                  <Chip key={chip}>{t(chip)}</Chip>
                ))}
              </div>
              <Chip tone={tone} className="text-sm">
                {t(result)}
              </Chip>
            </Card>
          ))}
        </ul>
      </section>

      <section aria-labelledby="hw-model">
        <Eyebrow>{t("hw.model.eyebrow")}</Eyebrow>
        <h2 id="hw-model" className="mt-3 text-2xl font-semibold tracking-tight text-balance">
          {t("hw.model.title")}
        </h2>
        <p className="mt-2 max-w-2xl text-base leading-relaxed text-fg-muted text-pretty">{t("hw.model.text")}</p>
        <ol className="mt-6 grid gap-2.5 tab:grid-cols-2">
          {STEPS.map((step, index) => (
            <li key={step.title} className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-surface-3 text-sm font-semibold tabular-nums text-fg-muted">
                {index + 1}
              </span>
              <span>
                <span className="block text-base font-semibold">{t(step.title)}</span>
                <span className="block text-sm text-fg-muted">{t(step.text)}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-fg-muted text-pretty">{t("hw.model.note")}</p>
      </section>

      <section aria-labelledby="hw-history" className="tab:grid tab:grid-cols-2 tab:items-center tab:gap-10">
        <div>
          <Eyebrow>{t("hw.history.eyebrow")}</Eyebrow>
          <h2 id="hw-history" className="mt-3 text-2xl font-semibold tracking-tight text-balance">
            {t("hw.history.title")}
          </h2>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-fg-muted text-pretty">{t("hw.history.text")}</p>
        </div>
        <div data-accent="training" className="mt-6 grid max-w-sm grid-cols-7 gap-1.5 tab:mt-0 tab:justify-self-end" aria-hidden="true">
          {SAMPLE_LEVELS.map((level, index) => (
            <span key={index} className={cn("aspect-square rounded-lg", `lv-${level}`)} />
          ))}
        </div>
      </section>

      <div className="flex flex-col gap-2.5 tab:flex-row">
        <a href="/demo" className={cn(buttonClass({ variant: "primary", size: "lg" }), "tab:min-w-52")}>
          {t("hw.cta.demo")}
        </a>
        {!bootstrap.user && (
          <a href="/auth/register" className={cn(buttonClass({ size: "lg" }), "tab:min-w-52")}>
            {t("hw.cta.signup")}
          </a>
        )}
      </div>
    </div>
  );
}

/** Public page; signed-in users get it inside the app frame (see App.tsx). */
export default function HowItWorks() {
  const { t } = useT();
  useTitle(t("hw.title"));
  if (bootstrap.user) return <Content />;
  return (
    <div className="min-h-dvh">
      <LandingHeader />
      <main>
        <Content />
      </main>
      <LandingFooter />
    </div>
  );
}
