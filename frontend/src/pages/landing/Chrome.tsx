import { Link } from "react-router";
import { buttonClass } from "../../components/ui/Button";
import { useT } from "../../i18n";
import { cn } from "../../lib/cn";

/** Header of the public pages: logo on the left, sign-in and sign-up on the right. */
export function LandingHeader() {
  const { t } = useT();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/80 pt-[env(safe-area-inset-top)] backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 tab:px-6">
        <Link to="/welcome" aria-label={t("app.name")} className="inline-flex min-h-tap items-center">
          <img src="/static/img/brand/nosifit-lockup-on-dark.svg" alt={t("app.name")} className="h-8 w-auto" />
        </Link>
        <nav className="flex items-center gap-2">
          <a href="/auth/login" className={cn(buttonClass({ variant: "ghost" }), "px-3")}>
            {t("lp.nav.login")}
          </a>
          <a href="/auth/register" className={buttonClass({ variant: "secondary" })}>
            {t("lp.nav.signup")}
          </a>
        </nav>
      </div>
    </header>
  );
}

const FOOTER_LINK = "inline-flex min-h-tap min-w-tap items-center text-sm text-fg-muted transition hover:text-fg";

export function LandingFooter() {
  const { t } = useT();
  return (
    <footer className="border-t border-line pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 tab:flex-row tab:items-center tab:justify-between tab:px-6">
        <nav className="-mx-1 flex flex-wrap gap-x-5">
          <Link to="/how-it-works" className={FOOTER_LINK}>
            {t("lp.footer.how")}
          </Link>
          <a href="/demo" className={FOOTER_LINK}>
            {t("lp.footer.demo")}
          </a>
          <a href="/privacy" className={FOOTER_LINK}>
            {t("lp.footer.privacy")}
          </a>
          <a href="/contact" className={FOOTER_LINK}>
            {t("lp.footer.contact")}
          </a>
        </nav>
        <p className="text-sm text-fg-soft">{t("lp.footer.rights", { year: new Date().getFullYear() })}</p>
      </div>
    </footer>
  );
}
