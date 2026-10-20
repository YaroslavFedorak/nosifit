/*
 * Reloads page data when the user comes back to the tab or window, so an
 * entry made in the Telegram bot shows up without pressing F5.
 *
 * No timers and no open connections: an idle or hidden tab costs the server
 * nothing. A refresh runs only after the page was away for MIN_AWAY_MS, at
 * most once per MIN_GAP_MS, and never while a modal (form) is open.
 */

const MIN_AWAY_MS = 2000;
const MIN_GAP_MS = 5000;
const OPEN_MODAL = 'dialog[open], [class*="modal"].open, [class*="modal"].is-open';

export function onReturn(refresh: () => unknown): void {
    let awaySince: number | null = null;
    let lastRun = Date.now();

    const leave = (): void => {
        awaySince ??= Date.now();
    };

    const back = (): void => {
        if (awaySince === null) return;

        const now = Date.now();
        const away = now - awaySince;
        awaySince = null;

        if (away < MIN_AWAY_MS || now - lastRun < MIN_GAP_MS) return;
        if (document.querySelector(OPEN_MODAL)) return;

        lastRun = now;
        void refresh();
    };

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") leave();
        else back();
    });
    window.addEventListener("blur", leave);
    window.addEventListener("focus", back);
}
