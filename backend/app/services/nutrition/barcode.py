"""Retail barcode (GTIN) validation and normalization.

Accepted: EAN-8, UPC-A (12 digits), EAN-13 and GTIN-14, each with a valid
GS1 check digit. One product can be printed as UPC-A or EAN-13 (the same
number with a leading 0), so every code is stored and looked up in one
canonical form:

- 8 digits stay 8 (EAN-8);
- 12, 13 and 14 digits become 13 when the extra leading digits are zeros
  (UPC-A ``0…`` / GTIN-14 ``0…``), otherwise they keep their length.

Anything else (letters, wrong length, bad check digit) is rejected before
any database or network work, so a typo never reaches Open Food Facts.
"""

from __future__ import annotations

import re

# Spaces and hyphens are common in typed codes ("4 820045 704529").
_SEPARATORS = re.compile(r"[\s\-]+")
_DIGITS = re.compile(r"\d+")

VALID_LENGTHS = frozenset({8, 12, 13, 14})
# Raw input is cut off long before regex work: nothing valid is near this.
MAX_RAW_LENGTH = 32


class InvalidBarcode(ValueError):
    pass


def gs1_check_digit(body: str) -> int:
    """Check digit for the digits before it (GS1 mod-10, weights 3/1 from the right)."""
    total = 0
    for position, char in enumerate(reversed(body)):
        total += int(char) * (3 if position % 2 == 0 else 1)
    return (10 - total % 10) % 10


def has_valid_check_digit(code: str) -> bool:
    return len(code) >= 2 and gs1_check_digit(code[:-1]) == int(code[-1])


def normalize_barcode(raw) -> str:
    """Canonical GTIN for ``raw`` or ``InvalidBarcode``."""
    if not isinstance(raw, str):
        raise InvalidBarcode("Barcode must be text")
    if len(raw) > MAX_RAW_LENGTH:
        raise InvalidBarcode("Barcode is too long")

    code = _SEPARATORS.sub("", raw.strip())
    if not _DIGITS.fullmatch(code or "x"):
        raise InvalidBarcode("Barcode must contain digits only")
    if len(code) not in VALID_LENGTHS:
        raise InvalidBarcode("Barcode must have 8, 12, 13 or 14 digits")
    if not has_valid_check_digit(code):
        raise InvalidBarcode("Barcode check digit is wrong")

    if len(code) == 12:
        code = "0" + code
    elif len(code) == 14 and code.startswith("0"):
        code = code[1:]
    return code


def barcode_variants(code: str) -> list[str]:
    """Spellings of one canonical code that older rows may use.

    Catalog rows written before normalization (e.g. ``source_ref`` of the
    seeded label products) may hold the UPC-A form without the leading 0.
    """
    variants = [code]
    if len(code) == 13 and code.startswith("0"):
        variants.append(code[1:])
    return variants


def looks_like_barcode(text: str | None) -> bool:
    """True for input that is meant as a barcode (only digits, 8-14 of them)."""
    if not text or len(text) > MAX_RAW_LENGTH:
        return False
    code = _SEPARATORS.sub("", text.strip())
    return bool(_DIGITS.fullmatch(code or "x")) and 8 <= len(code) <= 14
