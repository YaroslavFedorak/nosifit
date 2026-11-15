import { Link } from "react-router";
import { useT } from "../../i18n";
import { buttonClass } from "../../ui/Button";

/** Header of the public pages: the logo, then sign-in and sign-up. */
export function LandingHeader() {
  const { t } = useT();
  return (
    <header className="sticky top-0 z-[300] border-b border-rule bg-paper pt-[env(safe-area-inset-top)]">
      <div className="page flex h-16 items-center justify-between gap-3">
        <Link to="/welcome" aria-label={t("app.name")} className="inline-flex min-h-tap items-center">
          <img src="/static/img/brand/nosifit-lockup-on-dark.svg" alt="" className="h-7 w-auto" />
        </Link>
        <nav aria-label={t("lp.nav.label")} className="flex items-center gap-1">
          <a href="/auth/login" className={buttonClass({ variant: "quiet" })}>
            {t("lp.nav.login")}
          </a>
          <a href="/auth/register" className={buttonClass()}>
            {t("lp.nav.signup")}
          </a>
        </nav>
      </div>
    </header>
  );
}

const FOOTER_LINK = "inline-flex min-h-tap items-center text-sm text-ink-2 transition-colors duration-150 hover:text-ink";

export function LandingFooter() {
  const { t } = useT();
  return (
    <footer className="border-t border-rule pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <div className="page flex flex-col gap-2 py-6 tab:flex-row tab:items-center tab:justify-between">
        <nav aria-label={t("lp.footer.label")} className="flex flex-wrap gap-x-6">
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
        <p className="text-sm text-muted">{t("lp.footer.rights", { year: new Date().getFullYear() })}</p>
      </div>
    </footer>
  );
}
