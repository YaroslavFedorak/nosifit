import {
  BookOpen,
  CalendarRange,
  ChevronRight,
  Crown,
  LayoutTemplate,
  LogOut,
  PlayCircle,
  ShieldCheck,
  User,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router";
import { useT } from "../../i18n";
import { LOCALES, bootstrap, switchLocale, type Locale } from "../../lib/bootstrap";
import { cn } from "../../lib/cn";
import { buttonClass } from "../ui/Button";

const LANGUAGE_NAMES: Record<Locale, string> = {
  en: "English",
  uk: "Українська",
  pl: "Polski",
  ru: "Русский",
};

const ROW =
  "flex min-h-tap items-center gap-3 px-4 py-2.5 text-sm font-medium text-fg transition hover:bg-white/5 active:bg-white/8";

function Row({ icon: Icon, children }: { icon: LucideIcon; children: string }) {
  return (
    <>
      <Icon size={18} className="shrink-0 text-fg-muted" aria-hidden="true" />
      <span className="flex-1">{children}</span>
      <ChevronRight size={16} className="shrink-0 text-fg-soft" aria-hidden="true" />
    </>
  );
}

/**
 * Everything that is not one of the four modules. Used in the "More" sheet on
 * phones and tablets and at the bottom of the sidebar on desktop. Pages that
 * are not finished yet (tracker, equipment) are deliberately not listed.
 */
export function MoreMenu({ onNavigate, compact = false }: { onNavigate?: () => void; compact?: boolean }) {
  const { t } = useT();

  return (
    <div className="space-y-5 pt-2">
      <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface-2/50">
        <li>
          <a href="/profile/" className={ROW}>
            <Row icon={User}>{t("more.profile")}</Row>
          </a>
        </li>
        <li>
          <a href="/training/" className={ROW}>
            <Row icon={CalendarRange}>{t("more.plan")}</Row>
          </a>
        </li>
        <li>
          <a href="/premium" className={ROW}>
            <Row icon={Crown}>{t("more.premium")}</Row>
          </a>
        </li>
        <li>
          <Link to="/how-it-works" className={ROW} onClick={onNavigate}>
            <Row icon={BookOpen}>{t("more.how")}</Row>
          </Link>
        </li>
        <li>
          <a href="/demo" className={ROW}>
            <Row icon={PlayCircle}>{t("more.demo")}</Row>
          </a>
        </li>
        <li>
          <a href="/privacy" className={ROW}>
            <Row icon={ShieldCheck}>{t("more.privacy")}</Row>
          </a>
        </li>
        <li>
          <a href="/dashboard/" className={ROW}>
            <Row icon={LayoutTemplate}>{t("more.classic")}</Row>
          </a>
        </li>
      </ul>

      <section aria-label={t("more.language")}>
        <h3 className="mb-2 px-1 text-xs font-medium text-fg-muted">{t("more.language")}</h3>
        <div className={cn("grid gap-2", compact ? "grid-cols-4" : "grid-cols-2")}>
          {LOCALES.map((locale) => (
            <button
              key={locale}
              type="button"
              aria-pressed={locale === bootstrap.locale}
              aria-label={LANGUAGE_NAMES[locale]}
              onClick={() => locale !== bootstrap.locale && switchLocale(locale)}
              className={cn(
                "min-h-tap rounded-xl border px-2 text-sm font-semibold transition",
                locale === bootstrap.locale
                  ? "border-fg/30 bg-surface-3 text-fg"
                  : "border-line bg-surface-2/50 text-fg-muted hover:text-fg",
              )}
            >
              {compact ? locale.toUpperCase() : LANGUAGE_NAMES[locale]}
            </button>
          ))}
        </div>
      </section>

      {!compact && (
        <a href="/auth/logout" className={buttonClass({ variant: "danger", block: true })}>
          <LogOut size={18} aria-hidden="true" />
          {t("more.logout")}
        </a>
      )}
    </div>
  );
}
