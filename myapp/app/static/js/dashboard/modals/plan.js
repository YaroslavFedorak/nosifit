const state = {
    plan: null,
    startCallback: null
};

function getModal() {
    return document.getElementById(
        "db-plan-modal"
    );
}

function getContent() {
    return document.getElementById(
        "db-plan-content"
    );
}

function openModal() {
    const modal = getModal();

    if (!modal) {
        return;
    }

    modal.classList.add("open");

    modal.setAttribute(
        "aria-hidden",
        "false"
    );

    document.body.classList.add(
        "db-modal-open"
    );
}

function closeModal() {
    const modal = getModal();

    if (!modal) {
        return;
    }

    modal.classList.remove("open");

    modal.setAttribute(
        "aria-hidden",
        "true"
    );

    document.body.classList.remove(
        "db-modal-open"
    );
}

function normalizeExercise(
    exercise
) {
    return {
        name:
            exercise?.name ??
            exercise?.exercise ??
            "Без назви",

        sets:
            exercise?.sets ??
            "—",

        reps:
            exercise?.reps ??
            "—",

        load:
            exercise?.load ??
            null
    };
}

function renderPlan(plan) {
    const content =
        getContent();

    if (!content) {
        return;
    }

    content.innerHTML = "";

    if (!plan) {
        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "db-session-empty";

        empty.textContent =
            "План тренування відсутній.";

        content.appendChild(
            empty
        );

        return;
    }

    const title =
        plan.title ??
        plan.name ??
        "Тренування";

    const exercises =
        Array.isArray(
            plan.exercises
        )
            ? plan.exercises
            : [];

    const section =
        document.createElement(
            "div"
        );

    section.className =
        "db-session-section";

    const header =
        document.createElement(
            "div"
        );

    header.className =
        "db-session-section-header";

    const heading =
        document.createElement(
            "h3"
        );

    heading.className =
        "db-session-section-title";

    heading.textContent =
        title;

    header.appendChild(
        heading
    );

    section.appendChild(
        header
    );

    if (!exercises.length) {
        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "db-session-empty";

        empty.textContent =
            "У плані поки немає вправ.";

        section.appendChild(
            empty
        );

        content.appendChild(
            section
        );

        return;
    }

    const list =
        document.createElement(
            "div"
        );

    list.className =
        "db-session-plan-exercises";

    exercises.forEach(
        rawExercise => {
            const exercise =
                normalizeExercise(
                    rawExercise
                );

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "db-session-plan-exercise";

            const name =
                document.createElement(
                    "div"
                );

            name.className =
                "db-session-plan-exercise-name";

            name.textContent =
                exercise.name;

            const meta =
                document.createElement(
                    "div"
                );

            meta.className =
                "db-session-plan-exercise-meta";

            const load =
                exercise.load != null
                    ? `${exercise.load} кг`
                    : "Власна вага";

            meta.textContent =
                `${exercise.sets} підх. · ` +
                `${exercise.reps} повт. · ` +
                load;

            row.appendChild(
                name
            );

            row.appendChild(
                meta
            );

            list.appendChild(
                row
            );
        }
    );

    section.appendChild(
        list
    );

    content.appendChild(
        section
    );
}

export function openPlanModal(
    plan,
    startCallback
) {
    state.plan =
        plan || null;

    state.startCallback =
        typeof startCallback ===
        "function"
            ? startCallback
            : null;

    renderPlan(
        state.plan
    );

    openModal();
}

export function closePlanModal() {
    closeModal();
}

export function initPlanModal() {
    const modal = getModal();

    if (!modal) {
        return;
    }

    modal
        .querySelectorAll(
            "[data-close-plan-modal]"
        )
        .forEach(
            button => {
                button.addEventListener(
                    "click",
                    closeModal
                );
            }
        );

    modal.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                modal
            ) {
                closeModal();
            }
        }
    );

    const startButton =
        document.getElementById(
            "db-plan-start"
        );

    if (startButton) {
        startButton.addEventListener(
            "click",
            () => {
                if (
                    state.startCallback
                ) {
                    state.startCallback(
                        state.plan
                    );
                }

                closeModal();
            }
        );
    }
}