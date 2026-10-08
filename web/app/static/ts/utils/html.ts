const HTML_ESCAPES: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
};

// Escape a value before putting it into an HTML template string. Use it for
// anything that comes from the API: product, meal and exercise names are
// typed by users.
export function escapeHtml(value: unknown): string {
    return String(value ?? "").replace(
        /[&<>"']/g,
        (char) => HTML_ESCAPES[char],
    );
}
