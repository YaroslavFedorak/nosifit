export function showTooltip(
    target: HTMLElement,
    content: string
): void {
    let tip =
        document.getElementById(
            "nf-heatmap-tooltip"
        );

    if (!tip) {
        tip =
            document.createElement(
                "div"
            );

        tip.id =
            "nf-heatmap-tooltip";

        tip.className =
            "nf-heatmap-tooltip";

        document.body.appendChild(
            tip
        );
    }

    tip.innerHTML = content;

    const rect =
        target.getBoundingClientRect();

    tip.style.left =
        `${rect.left + window.scrollX}px`;

    tip.style.top =
        `${rect.top + window.scrollY - rect.height - 8}px`;

    tip.classList.add("visible");
}

export function hideTooltip(): void {
    const tip =
        document.getElementById(
            "nf-heatmap-tooltip"
        );

    if (tip) {
        tip.classList.remove(
            "visible"
        );
    }
}