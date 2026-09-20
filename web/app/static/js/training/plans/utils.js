export function formatSets(list) {
    return list.reduce((total, exercise) => total +
        Number(exercise.sets || 0), 0);
}
export function formatCount(list) {
    return list.length;
}
