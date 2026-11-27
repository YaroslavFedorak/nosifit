import { useState } from "react";
import { useDisconnectProvider } from "../api/mutations";
import { useAccount } from "../api/queries";
import { Page } from "../app/Page";
import { DeleteAccountSheet, EmailSheet, PasswordSheet, TelegramSheet } from "../features/account/AccountSheets";
import { useT } from "../i18n";
import { errorCode } from "../lib/api";
import { LANGUAGE_NAMES, LOCALES, bootstrap, switchLocale, type Locale } from "../lib/bootstrap";
import { toast } from "../lib/toast";
import { Button, buttonClass } from "../ui/Button";
import { Chips, type Option } from "../ui/Choice";
import { ErrorNote, Skeleton } from "../ui/Feedback";
import { Group, Row, Section } from "../ui/Layout";

type Dialog = "email" | "password" | "telegram" | "delete" | null;

export default function Settings() {
  const { t } = useT();
  const account = useAccount();
  const disconnect = useDisconnectProvider();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [confirming, setConfirming] = useState<"google" | "github" | null>(null);

  const languages: Option<Locale>[] = LOCALES.map((id) => ({ id, label: LANGUAGE_NAMES[id] }));
  const data = account.data;
  const signIn = data?.sign_in;

  const provider = (id: "google" | "github", name: string) => {
    if (!signIn) return null;
    const connected = signIn[id];
    return (
      <div key={id} className="flex min-h-[3.25rem] items-center gap-3 px-4 py-2">
        <div className="min-w-0 flex-1">
          <p className="font-medium">{name}</p>
          <p className="text-sm text-muted">{connected ? t("account.signIn.on") : t("account.signIn.off")}</p>
        </div>
        {connected &&
          (confirming === id ? (
            <div className="flex gap-2">
              <Button onClick={() => setConfirming(null)}>{t("common.cancel")}</Button>
              <Button
                variant="danger"
                busy={disconnect.isPending}
                onClick={() =>
                  disconnect.mutate(id, {
                    onSuccess: () => setConfirming(null),
                    onError: (error) => {
                      setConfirming(null);
                      toast(t(errorCode(error) === "last_method" ? "account.signIn.last" : "common.failed"), "error");
                    },
                  })
                }
              >
                {t("account.disconnect")}
              </Button>
            </div>
          ) : (
            <Button variant="quiet" onClick={() => setConfirming(id)}>
              {t("account.disconnect")}
            </Button>
          ))}
      </div>
    );
  };

  return (
    <Page title={t("nav.settings")}>
      <div className="grid gap-x-[var(--gap-columns)] gap-y-8 desk:grid-cols-12 desk:items-start">
        <div className="space-y-8 desk:col-span-7">
          <Section title={t("settings.language")} note={t("settings.languageNote")}>
            <Chips wrap label={t("settings.language")} options={languages} value={bootstrap.locale} onChange={(id) => id !== bootstrap.locale && switchLocale(id)} />
          </Section>

          {account.isError ? (
            <ErrorNote onRetry={() => void account.refetch()} />
          ) : !data || !signIn ? (
            <Skeleton className="h-64" />
          ) : (
            <>
              <Section title={t("settings.account")}>
                <Group>
                  <Row title={t("account.email")} subtitle={data.user.email} trailing={t("common.edit")} chevron onClick={() => setDialog("email")} />
                  {signIn.has_password ? (
                    <Row title={t("account.password")} subtitle={t("account.password.set")} trailing={t("common.edit")} chevron onClick={() => setDialog("password")} />
                  ) : (
                    <Row title={t("account.password")} subtitle={t("account.password.none")} trailing={t("account.password.create")} chevron href="/auth/reset" />
                  )}
                </Group>
              </Section>

              <Section title={t("settings.signIn")} note={t("settings.signInNote")}>
                <Group>
                  {provider("google", "Google")}
                  {provider("github", "GitHub")}
                  <div className="flex min-h-[3.25rem] items-center gap-3 px-4 py-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">Telegram</p>
                      <p className="text-sm text-muted">
                        {signIn.telegram
                          ? signIn.telegram_username
                            ? t("account.signIn.as", { name: `@${signIn.telegram_username}` })
                            : t("account.signIn.on")
                          : t("account.telegram.hint")}
                      </p>
                    </div>
                    {signIn.telegram ? (
                      <Button variant="quiet" onClick={() => setDialog("telegram")}>
                        {t("account.disconnect")}
                      </Button>
                    ) : signIn.telegram_connect_url ? (
                      <a href={signIn.telegram_connect_url} target="_blank" rel="noopener noreferrer" className={buttonClass()}>
                        {t("account.connect")}
                      </a>
                    ) : null}
                  </div>
                </Group>
              </Section>
            </>
          )}
        </div>

        <div className="space-y-8 desk:col-span-5">
          <Section title={t("settings.data")} note={t("settings.dataNote")}>
            <Group>
              <a href="/privacy/my-data" download className="flex min-h-[3.25rem] items-center px-4 py-2 font-medium transition-colors duration-150 hover:bg-paper-3">
                {t("account.data.download")}
              </a>
              <Row title={t("account.data.policy")} chevron href="/privacy" />
              <Row title={t("account.data.withdraw")} chevron href="/consent/withdraw" />
            </Group>
          </Section>

          <Section title={t("settings.session")}>
            <div className="flex flex-wrap gap-2">
              <a href="/auth/logout" className={buttonClass()}>
                {t("account.logout")}
              </a>
              {data && (
                <Button variant="danger" onClick={() => setDialog("delete")}>
                  {t("account.delete.title")}
                </Button>
              )}
            </div>
          </Section>

          {bootstrap.version && (
            <p className="text-sm text-muted">
              NosiFit {bootstrap.version}
              {bootstrap.stage && ` · ${t("app.stage.beta")}`}
            </p>
          )}
        </div>
      </div>

      {data && dialog === "email" && <EmailSheet account={data} onClose={() => setDialog(null)} />}
      {dialog === "password" && <PasswordSheet onClose={() => setDialog(null)} />}
      {data && dialog === "telegram" && <TelegramSheet account={data} onClose={() => setDialog(null)} />}
      {data && dialog === "delete" && <DeleteAccountSheet account={data} onClose={() => setDialog(null)} />}
    </Page>
  );
}
