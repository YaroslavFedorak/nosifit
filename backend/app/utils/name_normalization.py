"""Name normalization shared by search, duplicate checks and the seed.

Both the stored ``normalized_name`` and every search query go through
``normalize_name``, so they always fold the same way: case, diacritics
(``ł`` → ``l``, ``ё`` → ``е``), apostrophes (``м'ясо`` = ``мʼясо`` = ``мясо``)
and punctuation (``Молоко 2,5%`` = ``молоко 2.5%``).

If this function changes, existing rows must be re-normalized with a data
migration, otherwise search silently misses them.
"""

from __future__ import annotations

import re
import unicodedata

_APOSTROPHES = re.compile(r"['’ʼ`´‘]")
_SEPARATORS = re.compile(r"[^\w%]+")
_EXTRA = str.maketrans({"ł": "l", "ø": "o", "ß": "ss", "æ": "ae", "œ": "oe"})


def normalize_name(value: str | None) -> str:
    if not value:
        return ""

    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.translate(_EXTRA)
    text = _APOSTROPHES.sub("", text)
    text = _SEPARATORS.sub(" ", text).replace("_", " ")
    return " ".join(text.split())
