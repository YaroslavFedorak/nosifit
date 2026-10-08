import { profile_t } from "../i18n/index.js";

// Messages are shown with textContent only; the server decides everything.

const ERROR_KEYS: Record<string, string> = {
    wrong_password: "connected.errors.wrongPassword",
    wrong_code: "connected.errors.wrongCode",
    expired: "connected.errors.expired",
    last_method: "connected.errors.lastMethod",
    not_connected: "connected.errors.notConnected",
    send_failed: "connected.errors.sendFailed",
    rate_limited: "connected.errors.rateLimited",
};

const errorText = (message: unknown): string => {
    const key =
        typeof message === "string" && ERROR_KEYS[message]
            ? ERROR_KEYS[message]
            : "connected.errors.generic";
    return profile_t(key);
};

const showMessage = (
    element: HTMLElement | null,
    text: string
): void => {
    if (!element) {
        return;
    }
    element.textContent = text;
    element.hidden = false;
};

const readJson = async (
    response: Response
): Promise<Record<string, unknown>> => {
    try {
        const data: unknown = await response.json();
        return data && typeof data === "object"
            ? (data as Record<string, unknown>)
            : {};
    } catch {
        return {};
    }
};

const errorFrom = (
    response: Response,
    data: Record<string, unknown>
): string => {
    if (response.status === 429) {
        return errorText("rate_limited");
    }
    return errorText(data.message ?? data.error);
};

const bindOAuthDisconnect = (): void => {
    const message = document.querySelector<HTMLElement>(
        "[data-connected-message]"
    );

    document
        .querySelectorAll<HTMLButtonElement>("[data-oauth-disconnect]")
        .forEach((button) => {
            button.addEventListener("click", async () => {
                const provider = button.dataset.oauthDisconnect ?? "";

                if (!window.confirm(profile_t("connected.confirmDisconnect"))) {
                    return;
                }

                button.disabled = true;

                try {
                    const body = new FormData();
                    body.append("provider", provider);

                    const response = await fetch("/profile/oauth_disconnect", {
                        method: "POST",
                        credentials: "same-origin",
                        body,
                    });
                    const data = await readJson(response);

                    if (response.ok) {
                        window.location.reload();
                        return;
                    }

                    showMessage(message, errorFrom(response, data));
                } catch {
                    showMessage(message, errorText(null));
                } finally {
                    button.disabled = false;
                }
            });
        });
};

const bindTelegramDisconnect = (): void => {
    const modal = document.getElementById("modal-telegram-disconnect");
    const form = document.querySelector<HTMLFormElement>(
        "#telegram-disconnect-form"
    );

    if (!modal || !form) {
        return;
    }

    const message = modal.querySelector<HTMLElement>(
        "[data-telegram-disconnect-message]"
    );
    const sendCode = modal.querySelector<HTMLButtonElement>(
        "#telegram-disconnect-send-code"
    );

    modal.addEventListener("modal:reset", () => {
        form.reset();
        if (message) {
            message.hidden = true;
            message.textContent = "";
        }
    });

    sendCode?.addEventListener("click", async () => {
        sendCode.disabled = true;

        try {
            const response = await fetch(
                "/profile/telegram/disconnect/request",
                { method: "POST", credentials: "same-origin" }
            );
            const data = await readJson(response);

            showMessage(
                message,
                response.ok
                    ? profile_t("connected.codeSent")
                    : errorFrom(response, data)
            );
        } catch {
            showMessage(message, errorText(null));
        } finally {
            sendCode.disabled = false;
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const submit = form.querySelector<HTMLButtonElement>(
            'button[type="submit"]'
        );
        if (submit) {
            submit.disabled = true;
        }

        const fields = new FormData(form);
        const payload: Record<string, string> = {};
        const password = fields.get("password");
        const code = fields.get("code");
        if (typeof password === "string") {
            payload.password = password;
        }
        if (typeof code === "string") {
            payload.code = code.trim();
        }

        try {
            const response = await fetch("/profile/telegram/disconnect", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await readJson(response);

            if (response.ok && data.status === "disconnected") {
                window.location.reload();
                return;
            }

            showMessage(message, errorFrom(response, data));
        } catch {
            showMessage(message, errorText(null));
        } finally {
            if (submit) {
                submit.disabled = false;
            }
        }
    });
};

export const initConnectedAccounts = (): void => {
    bindOAuthDisconnect();
    bindTelegramDisconnect();
};
