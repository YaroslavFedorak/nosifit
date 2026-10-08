"""Exercise search by localized name, English name and slug.

The catalog is small (a few hundred exercises) and localized names live in
translation files, not in the database, so ranking happens in Python:

1. the whole name equals the query;
2. the name starts with the query;
3. every query word starts a word of the name ("жим леж" → "Жим штанги лежачи");
4. the name contains the query ("жим" inside "віджимання" ranks below 3);
5. fuzzy: every query word is close to some word of the name (typos).

Within one kind of match, exercises the user has already done come first.
"""

import re
from difflib import SequenceMatcher
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

MAX_QUERY_LENGTH = 64
FUZZY_MIN_RATIO = 0.75
FUZZY_MIN_WORD = 2
# Exercises the user has done before win ties within the same match kind.
HISTORY_BOOST = 5.0

_SEPARATORS_RE = re.compile(r"[\s\-_/.,()+]+")
_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "`": "'", "ё": "е"})


def normalize(text: Optional[str]) -> str:
    text = (text or "").casefold().translate(_APOSTROPHES)
    return " ".join(part for part in _SEPARATORS_RE.split(text) if part)


def _score_name(query: str, words: Sequence[str], name: str) -> float:
    if not name:
        return 0.0
    if name == query:
        return 100.0
    if name.startswith(query):
        return 90.0
    name_words = name.split()
    if all(any(w.startswith(q) for w in name_words) for q in words):
        return 80.0
    if query in name:
        return 60.0

    fuzzy_words = [q for q in words if len(q) >= FUZZY_MIN_WORD]
    if not fuzzy_words or len(fuzzy_words) != len(words):
        return 0.0
    ratios = []
    for q in fuzzy_words:
        best = max(
            # A typo in the beginning of a longer word: compare with its prefix too.
            max(
                SequenceMatcher(None, q, w).ratio(),
                SequenceMatcher(None, q, w[: len(q)]).ratio(),
            )
            for w in name_words
        )
        if best < FUZZY_MIN_RATIO:
            return 0.0
        ratios.append(best)
    return 40.0 * sum(ratios) / len(ratios)


def rank_exercises(
    exercises: Iterable,
    localized_names: Mapping[str, str],
    query: str,
    done_ids: Optional[set] = None,
) -> List[Tuple[float, object]]:
    """(score, exercise) pairs that match ``query``, best first."""
    done_ids = done_ids or set()
    query = normalize(query)[:MAX_QUERY_LENGTH]
    if not query:
        return []
    words = query.split()

    ranked = []
    for exercise in exercises:
        slug = getattr(exercise, "slug", None) or ""
        local = normalize(localized_names.get(slug))
        candidates = (
            local,
            normalize(getattr(exercise, "name", None)),
            normalize(slug),
        )
        score = max(_score_name(query, words, name) for name in candidates)
        if score > 0:
            if getattr(exercise, "id", None) in done_ids:
                score += HISTORY_BOOST
            ranked.append((score, len(local or candidates[1]), local or candidates[1], exercise))

    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [(score, exercise) for score, _, _, exercise in ranked]


def search_exercises(
    exercises: Iterable,
    localized_names: Mapping[str, str],
    query: str,
    limit: int = 8,
    offset: int = 0,
    done_ids: Optional[set] = None,
) -> list:
    ranked = rank_exercises(exercises, localized_names, query, done_ids)
    return [exercise for _, exercise in ranked[offset: offset + limit]]
