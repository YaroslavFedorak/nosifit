// Step-by-step form: one group of fields at a time, validated before moving on.
// The form is still a single POST; the steps only change what is visible.
import { validators } from "./validation.js";

type Control = HTMLInputElement | HTMLSelectElement;

const form = document.querySelector<HTMLFormElement>("form[data-wizard]");

if (form) {
    const steps = Array.from(form.querySelectorAll<HTMLElement>("[data-step]"));
    const dots = Array.from(
        document.querySelectorAll<HTMLElement>(".wizard-progress > span"),
    );
    const back = form.querySelector<HTMLButtonElement>("[data-back]");
    const next = form.querySelector<HTMLButtonElement>("[data-next]");
    const nextLabel = form.dataset.nextLabel ?? "";
    const submitLabel = form.dataset.submitLabel ?? "";
    const validate = validators.get(form);

    let current = 0;

    const controlsOf = (step: HTMLElement): Control[] =>
        Array.from(step.querySelectorAll<Control>("input, select")).filter(
            (control) => control.willValidate,
        );

    const show = (index: number, focus = true): void => {
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
    form.addEventListener(
        "submit",
        (event) => {
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
        },
        true,
    );

    back?.addEventListener("click", () => show(Math.max(0, current - 1)));

    show(0, false);
}
