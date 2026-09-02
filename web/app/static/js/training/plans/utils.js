export function formatSets(list) {
    return list.reduce((acc, ex) => acc + Number(ex.sets || 0), 0);
}

export function formatCount(list) {
    return list.length;
}
