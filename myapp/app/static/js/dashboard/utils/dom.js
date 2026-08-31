export function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const key in attrs) {
        if (!Object.prototype.hasOwnProperty.call(attrs, key)) continue;
        const val = attrs[key];
        if (key === "class") {
            node.className = val;
        } else if (key === "text") {
            node.textContent = val;
        } else if (key === "html") {
            node.innerHTML = val;
        } else if (key === "ariaLabel") {
            node.setAttribute("aria-label", val);
        } else if (key === "type") {
            node.type = val;
        } else if (key === "value") {
            node.value = val;
        } else {
            node.setAttribute(key, String(val));
        }
    }
    if (Array.isArray(children)) {
        children.forEach(child => {
            if (child == null) return;
            if (typeof child === "string") {
                node.appendChild(document.createTextNode(child));
            } else {
                node.appendChild(child);
            }
        });
    }
    return node;
}
