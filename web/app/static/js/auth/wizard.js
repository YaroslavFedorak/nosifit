// Step-by-step form: one group of fields at a time, validated before moving on.
// The form is still a single POST; the steps only change what is visible.
import { validators } from "./validation.js";
const form = document.querySelector("form[data-wizard]");
if (form) {
    const steps = Array.from(form.querySelectorAll("[data-step]"));
    const dots = Array.from(document.querySelectorAll(".wizard-progress > span"));
    const back = form.querySelector("[data-back]");
    const next = form.querySelector("[data-next]");
    const nextLabel = form.dataset.nextLabel ?? "";
    const submitLabel = form.dataset.submitLabel ?? "";
    const validate = validators.get(form);
    let current = 0;
    const controlsOf = (step) => Array.from(step.querySelectorAll("input, select")).filter((control) => control.willValidate);
    const show = (index, focus = true) => {
        current = index;
        steps.forEach((step, i) => {
            step.hidden = i !== index;
        });
        dots.forEach((dot, i) => {
            dot.classList.toggle("is-done", i < index);
            dot.classList.toggle("is-current", i === index);
        });
        if (back) {
            back.hidden = index === 0;
        }
        if (next) {
            next.textContent = index === steps.length - 1 ? submitLabel : nextLabel;
        }
        form.classList.toggle("is-first", index === 0);
        if (focus) {
            controlsOf(steps[index])[0]?.focus({ preventScroll: true });
        }
    };
    // Runs before validation.js: a step is checked in order, so an error in an
    // earlier step brings the user back to it instead of failing out of sight.
    form.addEventListener("submit", (event) => {
        for (let i = 0; i < steps.length; i += 1) {
            if (validate && !validate(controlsOf(steps[i]))) {
                event.preventDefault();
                event.stopImmediatePropagation();
                show(i, false);
                controlsOf(steps[i]).find((control) => !control.checkValidity())?.focus();
                return;
            }
            if (i === current && i < steps.length - 1) {
                event.preventDefault();
                event.stopImmediatePropagation();
                show(i + 1);
                return;
            }
        }
    }, true);
    back?.addEventListener("click", () => show(Math.max(0, current - 1)));
    show(0, false);
}
