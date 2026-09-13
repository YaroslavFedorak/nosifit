export interface RecoveryHabit {
    user_habit_id: number | string;
    name?: string;
    category?: string;
    icon?: string;
    points?: number;
    completed?: boolean;
}

export interface RecoverySnapshot {
    date?: string;
    sleep_duration_minutes?: number | null;
    sleep_start?: string | null;
    sleep_end?: string | null;
    habits?: RecoveryHabit[];
}

export interface RecoveryState {
    snapshot: RecoverySnapshot | null;
    loading: boolean;
    error: string | null;
}

export const recoveryState: RecoveryState = {
    snapshot: null,
    loading: false,
    error: null
};