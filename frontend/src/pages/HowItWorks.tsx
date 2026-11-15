import { useT } from "../i18n";
import type { TKey } from "../i18n/en";
import { bootstrap } from "../lib/bootstrap";
import { useTitle } from "../lib/useTitle";
import { buttonClass } from "../ui/Button";
import { LandingFooter, LandingHeader } from "./landing/Chrome";

const DAYS: Array<{ day: TKey; sleep: TKey; kcal: TKey; ready: TKey; result: TKey }> = [
  { day: "hw.context.a.day", sleep: "hw.context.a.sleep", kcal: "hw.context.a.kcal", ready: "hw.context.a.ready", result: "hw.context.a.result" },
  { day: "hw.context.b.day", sleep: "hw.context.b.sleep", kcal: "hw.context.b.kcal", ready: "hw.context.b.ready", result: "hw.context.b.result" },
];

const STEPS: Array<{ title: TKey; text: TKey }> = [
  { title: "hw.model.s1.t", text: "hw.model.s1.d" },
  { title: "hw.model.s2.t", text: "hw.model.s2.d" },
  { title: "hw.model.s3.t", text: "hw.model.s3.d" },
  { title: "hw.model.s4.t", text: "hw.model.s4.d" },
];

function Content() {
  const { t } = useT();
  return (
    <div className="max-w-3xl space-y-12 pb-8">
      <header>
        <h1 className="text-2xl desk:text-3xl">{t("hw.title")}</h1>
        <p className="mt-3 max-w-[56ch] text-lg text-ink-2">{t("hw.lead")}</p>
      </header>

      <section aria-labelledby="hw-context">
        <h2 id="hw-context" className="text-xl">
          {t("hw.context.title")}
        </h2>
        <p className="mb-5 mt-2 max-w-[60ch] text-ink-2">{t("hw.context.text")}</p>
        <table className="w-full border-collapse text-left text-sm">
          <caption className="mb-2 text-left text-muted">{t("hw.context.lift")}</caption>
          <thead>
            <tr className="border-b border-rule text-muted">
              <th scope="col" className="py-2 pr-3 font-normal">
                {t("hw.context.col.day")}
              </th>
              <th scope="col" className="hidden py-2 pr-3 font-normal tab:table-cell">
                {t("hw.context.col.sleep")}
              </th>
              <th scope="col" className="hidden py-2 pr-3 font-normal tab:table-cell">
                {t("hw.context.col.food")}
              </th>
              <th scope="col" className="py-2 pr-3 font-normal">
                {t("hw.context.col.ready")}
              </th>
              <th scope="col" className="py-2 font-normal">
                {t("hw.context.col.result")}
              </th>
            </tr>
          </thead>
          <tbody>
            {DAYS.map((row) => (
              <tr key={row.day} className="border-b border-rule align-baseline">
                <th scope="row" className="py-3 pr-3 font-medium">
                  {t(row.day)}
                </th>
                <td className="hidden py-3 pr-3 text-ink-2 tab:table-cell">{t(row.sleep)}</td>
                <td className="hidden py-3 pr-3 text-ink-2 tab:table-cell">{t(row.kcal)}</td>
                <td className="py-3 pr-3 text-ink-2">{t(row.ready)}</td>
                <td className="py-3 font-medium">{t(row.result)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-labelledby="hw-model">
        <h2 id="hw-model" className="text-xl">
          {t("hw.model.title")}
        </h2>
        <p className="mb-5 mt-2 max-w-[60ch] text-ink-2">{t("hw.model.text")}</p>
        <ol className="divide-y divide-rule border-y border-rule [counter-reset:step]">
          {STEPS.map((step) => (
            <li key={step.title} className="flex items-baseline gap-4 py-3 [counter-increment:step] before:w-5 before:shrink-0 before:text-sm before:text-muted before:content-[counter(step)]">
              <span className="min-w-0 flex-1 font-medium">{t(step.title)}</span>
              <span className="text-right text-sm text-ink-2">{t(step.text)}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 max-w-[60ch] text-sm text-muted">{t("hw.model.note")}</p>
      </section>

      <section aria-labelledby="hw-history">
        <h2 id="hw-history" className="text-xl">
          {t("hw.history.title")}
        </h2>
        <p className="mt-2 max-w-[60ch] text-ink-2">{t("hw.history.text")}</p>
      </section>

      <div className="flex flex-wrap gap-2">
        <a href="/demo" className={buttonClass({ variant: bootstrap.user ? "secondary" : "primary", size: "lg" })}>
          {t("hw.cta.demo")}
        </a>
        {!bootstrap.user && (
          <a href="/auth/register" className={buttonClass({ size: "lg" })}>
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
    <div className="flex min-h-dvh flex-col">
      <LandingHeader />
      <main className="page flex-1 py-10 desk:py-16">
        <Content />
      </main>
      <LandingFooter />
    </div>
  );
}
