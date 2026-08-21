import { el } from "../utils/dom.js";

function formatLoad(value) {
    if (value == null) return "—";

    const number = Number(value);

    if (!Number.isFinite(number)) return "—";

    return Math.round(number).toString();
}

function formatDuration(value) {
    if (value == null) return "0 хв";

    const minutes = Number(value);

    if (!Number.isFinite(minutes) || minutes <= 0) {
        return "0 хв";
    }

    return `${Math.round(minutes)} хв`;
}

function formatRpe(value) {
    if (value == null || value === "") return "—";

    const number = Number(value);

    if (!Number.isFinite(number)) return String(value);

    return number % 1 === 0 ? String(number) : number.toFixed(1);
}

function getStatusLabel(status) {
    if (status === "finished") return "Завершено";
    if (status === "active") return "Активне";

    return "Немає даних";
}

function createMetric(label, value) {
    return el("div", { class: "db-session-metric" }, [
        el("span", {
            class: "db-session-metric-label",
            text: label
        }),
        el("strong", {
            class: "db-session-metric-value",
            text: value
        })
    ]);
}

function createExercise(exercise, index) {
    const name = exercise.exercise || `Вправа ${index + 1}`;

    const sets = exercise.sets != null
        ? String(exercise.sets)
        : "—";

    const reps = exercise.reps != null && exercise.reps !== ""
        ? String(exercise.reps)
        : "—";

    const load = exercise.load != null
        ? `${formatLoad(exercise.load)} кг`
        : "Власна вага";

    const rpe = exercise.rpe != null
        ? `RPE ${formatRpe(exercise.rpe)}`
        : "";

    return el("div", { class: "db-session-exercise" }, [
        el("div", {
            class: "db-session-exercise-index",
            text: String(index + 1)
        }),
        el("div", { class: "db-session-exercise-main" }, [
            el("div", {
                class: "db-session-exercise-name",
                text: name
            }),
            el("div", {
                class: "db-session-exercise-meta",
                text: `${sets} підходів · ${reps} повторень · ${load}${rpe ? ` · ${rpe}` : ""}`
            })
        ])
    ]);
}

function createMuscleList(muscles) {
    if (!muscles || typeof muscles !== "object") {
        return null;
    }

    const groups = [
        ["weak", "Потребують уваги"],
        ["balanced", "Збалансовані"],
        ["overloaded", "Перевантажені"]
    ];

    const visibleGroups = groups.filter(([key]) => {
        return Array.isArray(muscles[key]) && muscles[key].length;
    });

    if (!visibleGroups.length) {
        return null;
    }

    const content = [];

    for (const [key, title] of visibleGroups) {
        const values = muscles[key];

        content.push(
            el("div", { class: `db-session-muscles-group db-session-muscles-${key}` }, [
                el("div", {
                    class: "db-session-muscles-title",
                    text: title
                }),
                el("div", {
                    class: "db-session-muscles-values",
                    text: values.join(", ")
                })
            ])
        );
    }

    return el("div", { class: "db-session-muscles" }, content);
}

export function renderSession(container, training) {
    if (!container) return;

    container.innerHTML = "";

    const session = training && training.session
        ? training.session
        : null;

    const summary = training && training.summary
        ? training.summary
        : null;

    if (!session) {
        container.appendChild(
            el("div", { class: "db-session-empty" }, [
                el("div", {
                    class: "db-session-empty-title",
                    text: "Тренування сьогодні ще не розпочато"
                }),
                el("div", {
                    class: "db-session-empty-text",
                    text: "Розпочніть тренування, щоб побачити статистику."
                })
            ])
        );

        return;
    }

    const exerciseCount = summary?.exercise_count ?? session.exercise_count ?? 0;
    const duration = summary?.duration ?? session.duration ?? 0;
    const internalLoad = summary?.internal_load ?? session.internal_load ?? 0;
    const score = summary?.score;
    const rpe = session.rpe_avg;

    const header = el("div", { class: "db-session-widget-header" }, [
        el("div", { class: "db-session-widget-status" }, [
            el("span", {
                class: "db-session-status",
                text: getStatusLabel(session.status)
            })
        ])
    ]);

    const metrics = el("div", { class: "db-session-metrics" }, [
        createMetric("Вправи", String(exerciseCount)),
        createMetric("Тривалість", formatDuration(duration)),
        createMetric("Навантаження", formatLoad(internalLoad)),
        createMetric("RPE", formatRpe(rpe))
    ]);

    if (score != null) {
        metrics.appendChild(
            createMetric("Оцінка", formatLoad(score))
        );
    }

    const exercises = Array.isArray(session.exercises)
        ? session.exercises
        : [];

    const exerciseSection = el("div", {
        class: "db-session-exercises"
    });

    if (exercises.length) {
        exerciseSection.appendChild(
            el("div", {
                class: "db-session-section-title",
                text: "Вправи"
            })
        );

        const list = el("div", {
            class: "db-session-exercise-list"
        });

        exercises.forEach((exercise, index) => {
            list.appendChild(createExercise(exercise, index));
        });

        exerciseSection.appendChild(list);
    }

    const muscleList = createMuscleList(summary?.muscles);

    if (muscleList) {
        exerciseSection.appendChild(muscleList);
    }

    container.appendChild(header);
    container.appendChild(metrics);
    container.appendChild(exerciseSection);
}