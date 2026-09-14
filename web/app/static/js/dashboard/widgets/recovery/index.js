import { RecoveryAPI } from "../../modals/recovery/api.js";
import { recoveryState } from "./state.js";
import { renderRecoveryWidget } from "./render.js";
let userId = null;
function resolveUserId() {
    if (userId !== null) {
        return userId;
    }
    const source = document.getElementById("dashboard-open-recovery");
    const rawUserId = source?.getAttribute("data-user-id");
    if (!rawUserId) {
        return null;
    }
    const parsed = Number(rawUserId);
    if (!Number.isFinite(parsed)) {
        return null;
    }
    userId = parsed;
    return userId;
}
export async function refreshRecoveryWidget() {
    const currentUserId = resolveUserId();
    if (currentUserId === null) {
        recoveryState.snapshot = null;
        recoveryState.loading = false;
        recoveryState.error =
            "Recovery user id is not available";
        renderRecoveryWidget(recoveryState);
        return;
    }
    recoveryState.loading = true;
    recoveryState.error = null;
    try {
        const [snapshot, userHabits] = await Promise.all([
            RecoveryAPI.getSnapshot(currentUserId),
            RecoveryAPI.getUserHabits(currentUserId)
        ]);
        if (snapshot) {
            snapshot.habits =
                Array.isArray(snapshot.habits)
                    ? snapshot.habits
                    : userHabits;
        }
        else if (userHabits.length > 0) {
            recoveryState.snapshot = {
                habits: userHabits
            };
            recoveryState.error =
                null;
            return;
        }
        recoveryState.snapshot =
            snapshot;
        recoveryState.error = null;
    }
    catch (error) {
        recoveryState.snapshot = null;
        recoveryState.error =
            error instanceof Error
                ? error.message
                : "Failed to load recovery data";
    }
    finally {
        recoveryState.loading = false;
        renderRecoveryWidget(recoveryState);
    }
}
export function initRecoveryWidget() {
    void refreshRecoveryWidget();
}
