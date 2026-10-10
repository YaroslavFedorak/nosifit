// Year heatmaps scroll horizontally on phones. Start them at the right edge,
// where the current weeks are, until the user scrolls themselves.
const SELECTOR = [
    ".nutrition-heatmap-content",
    ".tr-heatmap-content",
    ".rc-heatmap-content",
].join(",");
export const initScrollEnd = () => {
    for (const element of document.querySelectorAll(SELECTOR)) {
        let touched = false;
        const stick = () => {
            if (!touched && element.scrollWidth > element.clientWidth) {
                element.scrollLeft = element.scrollWidth;
            }
        };
        element.addEventListener("pointerdown", () => { touched = true; }, { once: true });
        element.addEventListener("wheel", () => { touched = true; }, { once: true, passive: true });
        // Cells are rendered asynchronously after data loads.
        new MutationObserver(stick).observe(element, { childList: true, subtree: true });
        new ResizeObserver(stick).observe(element);
        stick();
    }
};
