// Language picker: the server and the i18n loader both read this cookie,
// so a reload is all it takes to apply the new locale everywhere.
const LOCALE_COOKIE = "nosifit_locale";
const ONE_YEAR = 60 * 60 * 24 * 365;
for (const select of document.querySelectorAll("[data-locale-select]")) {
    select.addEventListener("change", () => {
        const secure = location.protocol === "https:" ? "; Secure" : "";
        document.cookie =
            `${LOCALE_COOKIE}=${encodeURIComponent(select.value)}; Path=/; Max-Age=${ONE_YEAR}; SameSite=Lax${secure}`;
        select.disabled = true;
        location.reload();
    });
}
export {};
