import { loadTranslations, } from "../i18n/index.js";
import { ICONS } from "../icons/index.js";
import { initProgress } from "./progress.js";
import { initModals } from "./modals.js";
import { initDeleteAccount } from "./delete-account.js";
const initProfileIcon = () => {
    const iconElement = document.querySelector("[data-profile-icon]");
    if (!iconElement) {
        return;
    }
    const iconName = iconElement.dataset.profileIcon;
    if (!iconName) {
        return;
    }
    const icon = ICONS[iconName];
    if (!icon) {
        return;
    }
    iconElement.innerHTML = icon;
};
const initProfile = async () => {
    await loadTranslations("profile");
    initProfileIcon();
    initProgress();
    initModals();
    initDeleteAccount();
};
if (document.readyState ===
    "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        void initProfile();
    }, {
        once: true
    });
}
else {
    void initProfile();
}
