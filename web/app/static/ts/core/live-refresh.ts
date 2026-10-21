/*
 * Reloads page data when the user comes back to the tab or window, so an
 * entry made in the Telegram bot shows up without pressing F5, and when
 * another NosiFit tab of this browser saves something.
 *
 * No timers and no open connections: an idle or hidden tab costs the server
 * nothing. A refresh on return runs only after the page was away for
 * MIN_AWAY_MS, at most once per MIN_GAP_MS, and never while a modal (form)
 * is open. Tabs talk through BroadcastChannel, inside the browser.
 */

const MIN_AWAY_MS = 2000;
const MIN_GAP_MS = 5000;
// Several writes in a row (a meal with many items) end in one refresh.
const BROADCAST_DEBOUNCE_MS = 500;
const OPEN_MODAL = 'dialog[open], [class*="modal"].open, [class*="modal"].is-open';
const WRITE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

const channel: BroadcastChannel | null =
    typeof BroadcastChannel === "function"
        ? new BroadcastChannel("nosifit:data-changed")
        : null;

// Every successful write to the API of this origin tells the other tabs.
// The request and its response are passed through untouched.
if (channel) {
    const originalFetch = window.fetch.bind(window);

    window.fetch = async (input, init) => {
        const response = await originalFetch(input, init);

        const request = input instanceof Request ? input : null;
        const method = (init?.method || request?.method || "GET").toUpperCase();
        const url = new URL(request?.url ?? String(input), location.href);

        if (
            response.ok &&
            WRITE_METHODS.has(method) &&
            url.origin === location.origin &&
            url.pathname.startsWith("/api/")
        ) {
            channel.postMessage(url.pathname);
        }

        return response;
    };
}

function modalOpen(): boolean {
    return document.querySelector(OPEN_MODAL) !== null;
}

export function onReturn(refresh: () => unknown): void {
    let awaySince: number | null = null;
    let lastRun = Date.now();
    let broadcastTimer: number | undefined;
    // Another tab saved something while this one was hidden.
    let stale = false;

    const run = (): void => {
        stale = false;
        lastRun = Date.now();
        void refresh();
    };

    const leave = (): void => {
        awaySince ??= Date.now();
    };

    const back = (): void => {
        if (awaySince === null) return;

        const now = Date.now();
        const away = now - awaySince;
        awaySince = null;

        if (!stale && (away < MIN_AWAY_MS || now - lastRun < MIN_GAP_MS)) return;
        if (modalOpen()) return;

        run();
    };

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") leave();
        else back();
    });
    window.addEventListener("blur", leave);
    window.addEventListener("focus", back);

    // A hidden tab only notes it and refreshes when the user comes back.
    channel?.addEventListener("message", () => {
        if (document.visibilityState !== "visible") {
            stale = true;
            return;
        }

        window.clearTimeout(broadcastTimer);
        broadcastTimer = window.setTimeout(() => {
            if (!modalOpen()) run();
        }, BROADCAST_DEBOUNCE_MS);
    });
}
