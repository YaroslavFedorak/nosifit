export function formatDateIso(iso) {
    try {
        const date = new Date(iso);
        return date.toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric"
        });
    }
    catch (_) {
        return iso;
    }
}
