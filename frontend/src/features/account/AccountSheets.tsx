import { useState, type FormEvent } from "react";
import {
  useChangePassword,
  useConfirmEmailChange,
  useDeleteAccount,
  useDeleteAccountCode,
  useDeleteAccountConfirm,
  useDisconnectTelegram,
  useRequestEmailChange,
  useTelegramCode,
} from "../../api/mutations";
import type { AccountSummary } from "../../api/types";
import { useT, type I18n } from "../../i18n";
import type { TKey } from "../../i18n/en";
import { errorCode } from "../../lib/api";
import { toast } from "../../lib/toast";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";

const PASSWORD_MIN = 8;

/** What the server said went wrong, in the user's language. */
function reason(error: unknown, known: Record<string, TKey>, t: I18n["t"]): string | null {
  if (!error) return null;
  const code = errorCode(error);
  return t((code && known[code]) || "account.error.generic");
}

const COMMON: Record<string, TKey> = {
  rate_limited: "account.error.rate",
  too_many_attempts: "account.error.rate",
  send_failed: "account.error.send",
  expired: "account.error.expired",
  wrong: "account.error.code",
  wrong_code: "account.error.code",
  wrong_password: "account.error.password",
};

export function PasswordSheet({ onClose }: { onClose: () => void }) {
  const { t } = useT();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const tooShort = next.length > 0 && next.length < PASSWORD_MIN;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!current || next.length < PASSWORD_MIN) return;
    change.mutate(
      { current, next },
      {
        onSuccess: () => {
          toast(t("account.password.changed"));
          onClose();
        },
      },
    );
  };

  return (
    <Sheet open onClose={onClose} title={t("account.password.change")}>
      <form onSubmit={submit} className="space-y-4">
        <TextField
          label={t("account.password.current")}
          type="password"
          autoComplete="current-password"
          autoFocus
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
          error={errorCode(change.error) === "wrong_old" ? t("account.error.password") : null}
        />
        <TextField
          label={t("account.password.new")}
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(event) => setNext(event.target.value)}
          hint={t("account.password.hint", { n: PASSWORD_MIN })}
          error={tooShort || errorCode(change.error) === "weak" ? t("account.password.hint", { n: PASSWORD_MIN }) : errorCode(change.error) === "same" ? t("account.password.same") : null}
        />
        {change.isError && !["wrong_old", "weak", "same"].includes(errorCode(change.error) ?? "") && (
          <p role="alert" className="text-sm text-error">
            {reason(change.error, COMMON, t)}
          </p>
        )}
        <Button type="submit" variant="primary" size="lg" block disabled={!current || next.length < PASSWORD_MIN} busy={change.isPending}>
          {t("common.save")}
        </Button>
      </form>
    </Sheet>
  );
}

const EMAIL_ERRORS: Record<string, TKey> = {
  ...COMMON,
  missing_email: "account.email.invalid",
  same_email: "account.email.same",
  email_taken: "account.email.taken",
};

/** Two steps: the new address (with the password as proof), then the code sent to it. */
export function EmailSheet({ account, onClose }: { account: AccountSummary; onClose: () => void }) {
  const { t } = useT();
  const request = useRequestEmailChange();
  const confirm = useConfirmEmailChange();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const needsPassword = account.sign_in.has_password;

  if (sent) {
    return (
      <Sheet open onClose={onClose} onBack={() => setSent(false)} title={t("account.email.confirm")}>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (code.trim()) confirm.mutate(code.trim(), { onSuccess: onClose });
          }}
        >
          <p className="text-sm text-ink-2">{t("account.email.sent", { email })}</p>
          <TextField
            label={t("account.code")}
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            value={code}
            onChange={(event) => setCode(event.target.value)}
            error={reason(confirm.error, EMAIL_ERRORS, t)}
          />
          <Button type="submit" variant="primary" size="lg" block disabled={!code.trim()} busy={confirm.isPending}>
            {t("account.email.confirmCta")}
          </Button>
        </form>
      </Sheet>
    );
  }

  return (
    <Sheet open onClose={onClose} title={t("account.email.change")}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (email.trim()) request.mutate({ email: email.trim(), password }, { onSuccess: () => setSent(true) });
        }}
      >
        <p className="text-sm text-muted">{t("account.email.current", { email: account.user.email })}</p>
        <TextField label={t("account.email.new")} type="email" autoComplete="email" autoFocus value={email} onChange={(event) => setEmail(event.target.value)} />
        {needsPassword && (
          <TextField label={t("account.password.current")} type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        )}
        {request.isError && (
          <p role="alert" className="text-sm text-error">
            {reason(request.error, EMAIL_ERRORS, t)}
          </p>
        )}
        <Button type="submit" variant="primary" size="lg" block disabled={!email.trim() || (needsPassword && !password)} busy={request.isPending}>
          {t("account.email.send")}
        </Button>
      </form>
    </Sheet>
  );
}

const TELEGRAM_ERRORS: Record<string, TKey> = { ...COMMON, last_method: "account.signIn.last", not_connected: "account.error.generic" };

/** Disconnecting Telegram asks for the password, or for a code by email when the account has none. */
export function TelegramSheet({ account, onClose }: { account: AccountSummary; onClose: () => void }) {
  const { t } = useT();
  const sendCode = useTelegramCode();
  const disconnect = useDisconnectTelegram();
  const [proof, setProof] = useState("");
  const withPassword = account.sign_in.has_password;

  return (
    <Sheet open onClose={onClose} title={t("account.telegram.disconnect")}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (proof.trim()) disconnect.mutate(withPassword ? { password: proof } : { code: proof.trim() }, { onSuccess: onClose });
        }}
      >
        <p className="text-sm text-ink-2">{t("account.telegram.text")}</p>
        {!withPassword && (
          <Button busy={sendCode.isPending} onClick={() => sendCode.mutate(undefined, { onSuccess: () => toast(t("account.codeSent")) })}>
            {t("account.sendCode")}
          </Button>
        )}
        <TextField
          label={withPassword ? t("account.password.current") : t("account.code")}
          type={withPassword ? "password" : "text"}
          inputMode={withPassword ? undefined : "numeric"}
          autoComplete={withPassword ? "current-password" : "one-time-code"}
          value={proof}
          onChange={(event) => setProof(event.target.value)}
          error={reason(disconnect.error ?? sendCode.error, TELEGRAM_ERRORS, t)}
        />
        <Button type="submit" variant="destructive" size="lg" block disabled={!proof.trim()} busy={disconnect.isPending}>
          {t("account.disconnect")}
        </Button>
      </form>
    </Sheet>
  );
}

const DELETE_ERRORS: Record<string, TKey> = { ...COMMON, email_mismatch: "account.delete.mismatch" };

/**
 * Deleting the account takes three steps on purpose: a code sent by email,
 * the code typed back, then the address (and the password) typed by hand.
 */
export function DeleteAccountSheet({ account, onClose }: { account: AccountSummary; onClose: () => void }) {
  const { t } = useT();
  const sendCode = useDeleteAccountCode();
  const confirmCode = useDeleteAccountConfirm();
  const remove = useDeleteAccount();
  const [step, setStep] = useState<"intro" | "code" | "final">("intro");
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const needsPassword = account.sign_in.has_password;

  return (
    <Sheet open onClose={onClose} title={t("account.delete.title")}>
      {step === "intro" && (
        <div className="space-y-4">
          <p className="text-ink-2">{t("account.delete.text")}</p>
          <a href="/privacy/my-data" download className="inline-block font-medium text-ink underline underline-offset-4 hover:text-accent">
            {t("account.data.download")}
          </a>
          {sendCode.isError && (
            <p role="alert" className="text-sm text-error">
              {reason(sendCode.error, DELETE_ERRORS, t)}
            </p>
          )}
          <Button variant="danger" size="lg" block busy={sendCode.isPending} onClick={() => sendCode.mutate(undefined, { onSuccess: () => setStep("code") })}>
            {t("account.delete.send", { email: account.user.email })}
          </Button>
        </div>
      )}
      {step === "code" && (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (code.trim()) confirmCode.mutate(code.trim(), { onSuccess: () => setStep("final") });
          }}
        >
          <p className="text-sm text-ink-2">{t("account.email.sent", { email: account.user.email })}</p>
          <TextField
            label={t("account.code")}
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            value={code}
            onChange={(event) => setCode(event.target.value)}
            error={reason(confirmCode.error, DELETE_ERRORS, t)}
          />
          <Button type="submit" size="lg" block disabled={!code.trim()} busy={confirmCode.isPending}>
            {t("common.continue")}
          </Button>
        </form>
      )}
      {step === "final" && (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            remove.mutate({ email: email.trim(), password }, { onSuccess: () => window.location.assign("/") });
          }}
        >
          <p className="text-sm text-ink-2">{t("account.delete.final")}</p>
          <TextField label={t("account.delete.typeEmail")} type="email" autoComplete="off" autoFocus value={email} onChange={(event) => setEmail(event.target.value)} />
          {needsPassword && (
            <TextField label={t("account.password.current")} type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
          )}
          {remove.isError && (
            <p role="alert" className="text-sm text-error">
              {reason(remove.error, DELETE_ERRORS, t)}
            </p>
          )}
          <Button type="submit" variant="destructive" size="lg" block disabled={!email.trim() || (needsPassword && !password)} busy={remove.isPending}>
            {t("account.delete.confirm")}
          </Button>
        </form>
      )}
    </Sheet>
  );
}
