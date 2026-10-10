import { initScrollEnd } from "./scroll-end.js";
// App navigation shell: desktop collapse, tablet overlay rail, mobile drawer.
// Layout lives in css/core/layout.css; this file only flips classes.
const COLLAPSED_KEY = "nf-nav-collapsed";
const DESKTOP = window.matchMedia("(min-width: 1200px)");
const root = document.documentElement;
const body = document.body;
const setStored = (collapsed) => {
    try {
        localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
    }
    catch {
        // Storage can be blocked; the state then lasts for this page only.
    }
};
const toggleButtons = () => Array.from(document.querySelectorAll("[data-nav-toggle]"));
const openButtons = () => Array.from(document.querySelectorAll("[data-nav-open]"));
const isRailNarrow = () => DESKTOP.matches ? root.classList.contains("nf-nav-collapsed") : !body.classList.contains("nf-nav-open");
const syncToggleLabels = () => {
    const narrow = isRailNarrow();
    for (const button of toggleButtons()) {
        const label = narrow ? button.dataset.labelExpand : button.dataset.labelCollapse;
        if (label) {
            button.setAttribute("aria-label", label);
            button.title = label;
        }
        button.setAttribute("aria-expanded", String(!narrow));
    }
    for (const button of openButtons()) {
        button.setAttribute("aria-expanded", String(body.classList.contains("nf-nav-open")));
    }
};
const openNav = () => {
    body.classList.add("nf-nav-open");
    syncToggleLabels();
    document
        .querySelector("#app-sidebar .cmp-sidebar-item.active, #app-sidebar .cmp-sidebar-item")
        ?.focus({ preventScroll: true });
};
const closeNav = () => {
    if (!body.classList.contains("nf-nav-open")) {
        return;
    }
    body.classList.remove("nf-nav-open");
    syncToggleLabels();
};
const toggleNav = () => {
    if (DESKTOP.matches) {
        const collapsed = !root.classList.contains("nf-nav-collapsed");
        root.classList.toggle("nf-nav-collapsed", collapsed);
        setStored(collapsed);
        syncToggleLabels();
        return;
    }
    if (body.classList.contains("nf-nav-open")) {
        closeNav();
    }
    else {
        openNav();
    }
};
const init = () => {
    for (const button of toggleButtons()) {
        button.addEventListener("click", toggleNav);
    }
    for (const button of openButtons()) {
        button.addEventListener("click", openNav);
    }
    for (const element of document.querySelectorAll("[data-nav-close]")) {
        element.addEventListener("click", closeNav);
    }
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeNav();
        }
    });
    // Leaving the overlay breakpoint must not leave a stale open drawer.
    DESKTOP.addEventListener("change", () => {
        body.classList.remove("nf-nav-open");
        syncToggleLabels();
    });
    syncToggleLabels();
    initScrollEnd();
};
init();
