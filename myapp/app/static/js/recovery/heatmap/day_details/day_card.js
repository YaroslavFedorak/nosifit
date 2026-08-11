export function createMiniCard(name, value, status, barFill = 0) {
    const card = document.createElement("div");
    card.className = "rc-mini-card";

    card.innerHTML = `
        <div class="rc-mini-title">${name}</div>
        <div class="rc-mini-row">
            <div class="rc-mini-value">${value}</div>
            <div class="rc-mini-status">${status}</div>
        </div>
        <div class="rc-mini-bar">
            <div class="rc-mini-bar-fill" style="width:${barFill}%"></div>
        </div>
    `;

    return card;
}
