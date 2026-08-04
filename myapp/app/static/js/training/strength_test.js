import { TrainingAPI } from "./api.js";
import { renderStrengthTestResults } from "./dashboard.js";
import { getLevel, getProgress } from "./utils/strength_levels.js";
import { ICONS } from "../icons/index.js";

function getNumber(id) {
    return Number(document.getElementById(id)?.value) || 0;
}

export function injectIcons() {
    document.querySelectorAll(".tr-strength-icon")?.forEach(el => {
        el.innerHTML = ICONS.exercise;
    });
}

export function setupArrows() {
    document.querySelectorAll(".tr-arrow-up").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.inc;
            const input = document.getElementById(id);
            input.value = Number(input.value || 0) + 1;
        });
    });

    document.querySelectorAll(".tr-arrow-down").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.dec;
            const input = document.getElementById(id);
            const v = Number(input.value || 0);
            input.value = v > 0 ? v - 1 : 0;
        });
    });
}

export function initStrengthTest() {
    const openBtn = document.getElementById("tr-strength-open");
    const modal = document.getElementById("tr-modal-strength");
    const closeBtns = document.querySelectorAll("[data-close-strength]");
    const submitBtn = document.getElementById("strength-test-submit");
    const successBlock = document.getElementById("strength-success");
    const errorBlock = document.getElementById("strength-error");

    injectIcons();
    setupArrows();

    openBtn?.addEventListener("click", () => {
        modal?.classList.add("open");
        successBlock?.classList.add("hidden");
        errorBlock?.classList.add("hidden");
    });

    closeBtns.forEach(btn => {
        btn.addEventListener("click", () => modal?.classList.remove("open"));
    });

    ["st_pushups", "st_squats", "st_situps"].forEach(id => {
        const el = document.getElementById(id);
        el?.addEventListener("input", () => errorBlock?.classList.add("hidden"));
    });

    submitBtn?.addEventListener("click", () => {
        const pushups = getNumber("st_pushups");
        const squats = getNumber("st_squats");
        const situps = getNumber("st_situps");

        if (pushups === 0 && squats === 0 && situps === 0) {
            errorBlock.textContent = "Введіть хоча б один результат";
            errorBlock.classList.remove("hidden");
            return;
        }

        const text = submitBtn.querySelector(".btn-text");
        const loader = submitBtn.querySelector(".btn-loader");

        text?.classList.add("hidden");
        loader?.classList.remove("hidden");

        TrainingAPI.strengthTest({ pushups, squats, situps })
            .then(res => {
                const perf = res?.raw_performance || res || {};

                const result = {
                    ...perf,
                    pushups_level: getLevel("pushups", perf.pushups),
                    squats_level: getLevel("squats", perf.squats),
                    situps_level: getLevel("situps", perf.situps),
                    pushups_progress: getProgress("pushups", perf.pushups),
                    squats_progress: getProgress("squats", perf.squats),
                    situps_progress: getProgress("situps", perf.situps)
                };

                renderStrengthTestResults(result);
                successBlock?.classList.remove("hidden");

                if (modal) {
                    setTimeout(() => modal.classList.remove("open"), 800);
                }
            })
            .catch(() => {
                errorBlock.textContent = "Не вдалося зберегти результати";
                errorBlock.classList.remove("hidden");
            })
            .finally(() => {
                loader?.classList.add("hidden");
                text?.classList.remove("hidden");
            });
    });
}
