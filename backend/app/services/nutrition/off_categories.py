"""NosiFit category of an Open Food Facts product, only when it is certain.

Open Food Facts describes a product with many hierarchical taxonomy tags
(``en:chocolates``, ``en:snacks``, ``en:sweet-snacks`` ...). Few of them
correspond to one of NosiFit's food categories, and a product usually carries
several, some of them generic or pointing elsewhere. So the category is taken
from an explicit table of exact tags, and only if every tag found in the table
agrees. Anything else - no tags, no tag in the table, or tags that point to
different categories - gives ``None`` and the product stays in ``other``. A
category is never guessed from the name or from nutrient values.

Deliberately absent: generic or ambiguous tags such as ``en:beverages`` (milk
carries it), ``en:meats`` (poultry too), ``en:fruits`` and ``en:vegetables``
(fresh, canned and candied alike), ``en:snacks`` (sweet or salty).
"""
from __future__ import annotations

from backend.app.services.nutrition.product_service import PRODUCT_CATEGORIES

OFF_CATEGORY_TAGS = {
    # drinks
    "en:sodas": "beverages",
    "en:carbonated-drinks": "beverages",
    "en:waters": "beverages",
    "en:fruit-juices": "beverages",
    "en:energy-drinks": "beverages",
    # sweets
    "en:chocolates": "sweets",
    "en:candies": "sweets",
    "en:confectioneries": "sweets",
    "en:biscuits-and-cakes": "sweets",
    "en:biscuits": "sweets",
    "en:cakes": "sweets",
    "en:ice-creams-and-sorbets": "sweets",
    "en:jams": "sweets",
    # snacks
    "en:salty-snacks": "snacks",
    "en:crisps": "snacks",
    # animal foods
    "en:sausages": "meat",
    "en:hams": "meat",
    "en:fishes": "fish",
    "en:seafood": "seafood",
    "en:eggs": "eggs",
    "en:milks": "dairy",
    "en:yogurts": "dairy",
    "en:cheeses": "cheese",
    # cereal foods
    "en:breads": "bread",
    "en:pastas": "pasta",
    "en:breakfast-cereals": "grains",
    # plant foods
    "en:legumes": "legumes",
    "en:nuts": "nuts",
    # fats and sauces
    "en:vegetable-oils": "oils",
    "en:olive-oils": "oils",
    "en:sauces": "sauces",
    "en:ketchup": "sauces",
    "en:mayonnaises": "sauces",
}

assert set(OFF_CATEGORY_TAGS.values()) <= PRODUCT_CATEGORIES


def category_from_tags(tags) -> str | None:
    """The one NosiFit category all recognised ``tags`` agree on, else ``None``.

    ``None`` means "no reliable category": the caller keeps the product in
    ``other``. Only string tags are looked at - a list, dict, number, ``None``
    or anything else inside ``tags`` (a damaged cache, an unexpected answer)
    is ignored, never an error - and anything that is not a list or tuple of
    tags gives ``None``.
    """
    if not isinstance(tags, (list, tuple)):
        return None
    found = {
        OFF_CATEGORY_TAGS[tag]
        for tag in tags
        if isinstance(tag, str) and tag in OFF_CATEGORY_TAGS
    }
    return found.pop() if len(found) == 1 else None
