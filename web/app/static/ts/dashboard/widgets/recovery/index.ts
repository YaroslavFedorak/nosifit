import { recoveryState } from "./state";
import { renderRecovery } from "./render";
import { initSleepButton } from "./sleep";
import { bindHabitActions } from "./habits";

function getUserId(): string | null {
    const root =
        document.querySelector<HTMLElement>(".dashboard-page-wrapper");

    if (root?.dataset.userId) {
        return root.dataset.userId;
    }

    const recoveryRoot =
        document.getElementById("dashboard-recovery");

    if (recoveryRoot?.dataset.userId) {
        return recoveryRoot.dataset.userId;
    }

    const appRoot =
        document.querySelector<HTMLElement>("[data-user-id]");

    return appRoot?.dataset.userId || null;
}

async function loadSnapshot(): Promise<void> {
    const userId = getUserId();

    if (!userId) {
        recoveryState.error = "User ID not found";
        recoveryState.snapshot = null;
        renderRecovery(recoveryState);
        return;
    }

    recoveryState.loading = true;
    recoveryState.error = null;

    renderRecovery(recoveryState);

    try {
        const response = await fetch(
            `/api/recovery/snapshot/${encodeURIComponent(userId)}`
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        recoveryState.snapshot = await response.json();
    } catch (error) {
        recoveryState.snapshot = null;

        recoveryState.error =
            error instanceof Error
                ? error.message
                : "Failed to load recovery data";
    } finally {
        recoveryState.loading = false;
        renderRecovery(recoveryState);
    }
}

export async function refreshRecoveryWidget(): Promise<void> {
    await loadSnapshot();
}

export function initRecoveryWidget(): void {
    initSleepButton();

    bindHabitActions(
        refreshRecoveryWidget
    );

    loadSnapshot();
}

document.addEventListener("DOMContentLoaded", () => {
    const recoveryWidget =
        document.getElementById("dashboard-recovery");

    if (!recoveryWidget) {
        return;
    }

    initRecoveryWidget();
});