export interface RecoveryHabit {
    user_habit_id?: number | string;
    id?: number | string;
    name?: string;
    description?: string;
    category?: string;
    icon?: string;
    points?: number;
    completed?: boolean;
}

export interface RecoverySnapshot {
    id?: number;
    date?: string;
    sleep_score?: number | null;
    sleep_duration_minutes?: number | null;
    sleep_start?: string | null;
    sleep_end?: string | null;
    habit_score?: number;
    training_score?: number;
    energy_score?: number;
    recovery_score?: number;
    habits?: RecoveryHabit[];
    recommendations?: {
        total?: number;
        items?: unknown[];
    };
    [key: string]: unknown;
}

export interface RecoverySnapshotResponse {
    snapshot: RecoverySnapshot | null;
}

export interface RecoveryState {
    snapshot: RecoverySnapshot | null;
    loading: boolean;
    error: string | null;
}

export const recoveryState: RecoveryState = {
    snapshot: null,
    loading: true,
    error: null
};