import {
    getLocale,
    loadTranslations,
    translate,
} from "../i18n/index.js";

async function init() {
    try {
        await loadTranslations("demo");

        document.documentElement.lang = getLocale();

        document.querySelectorAll("[data-i18n]").forEach((element) => {
            element.textContent = translate(
                "demo",
                element.dataset.i18n
            );
        });
    } catch (error) {
        console.error("Failed to load demo translations:", error);
    }
}

init();
