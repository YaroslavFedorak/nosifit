export function renderCheckin(root, data) {
    root.innerHTML = `
        <div class="nf-checkin">
            <div class="nf-checkin-col">
                <h4>Recovery</h4>
                <div class="nf-checkin-row">Sleep: <strong>${data.recovery.sleep_hours ?? 0}h</strong></div>
                <div class="nf-checkin-row">Habits: <strong>${data.recovery.habits_completed ?? 0}/${data.recovery.habits_total ?? 0}</strong></div>
            </div>
            <div class="nf-checkin-col">
                <h4>Nutrition</h4>
                <div class="nf-checkin-row">Calories: <strong>${data.nutrition.calories ?? 0}</strong></div>
                <div class="nf-checkin-row">Protein: <strong>${data.nutrition.protein ?? 0}g</strong></div>
                <div class="nf-checkin-row">Water: <strong>${data.nutrition.water ?? 0}L</strong></div>
            </div>
            <div class="nf-checkin-col">
                <h4>Training</h4>
                <div class="nf-checkin-row">Workout: <strong>${data.training.completed ? "Yes" : "No"}</strong></div>
                <div class="nf-checkin-row">Duration: <strong>${data.training.duration ?? 0} min</strong></div>
                <div class="nf-checkin-row">Exercises: <strong>${data.training.exercise_count ?? 0}</strong></div>
            </div>
        </div>
    `;
}
