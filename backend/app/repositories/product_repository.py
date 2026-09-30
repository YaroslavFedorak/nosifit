from __future__ import annotations

from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from backend.app.models import Meal, MealItem, Product, ProductFavorite


def get_product_for_user(user_id, product_id):
    return (
        Product.query
        .options(selectinload(Product.names))
        .filter(
            Product.id == product_id,
            Product.is_active.is_(True),
            or_(
                Product.owner_user_id.is_(None),
                Product.owner_user_id == user_id,
            ),
        )
        .first()
    )


def get_user_product(user_id, product_id):
    return (
        Product.query
        .options(selectinload(Product.names))
        .filter_by(
            id=product_id,
            owner_user_id=user_id,
            source="user",
        )
        .first()
    )


def is_favorite(user_id, product_id) -> bool:
    return (
        ProductFavorite.query
        .filter_by(
            user_id=user_id,
            product_id=product_id,
        )
        .first()
        is not None
    )


def get_recent_products(user_id, limit=12):
    entries = (
        MealItem.query
        .join(Meal)
        .options(
            selectinload(MealItem.product)
            .selectinload(Product.names)
        )
        .filter(
            Meal.user_id == user_id,
            MealItem.product_id.is_not(None),
            Meal.date <= date.today(),
        )
        .order_by(
            Meal.date.desc(),
            Meal.time.desc().nullslast(),
            MealItem.id.desc(),
        )
        .limit(limit * 4)
        .all()
    )

    products = []
    seen = set()

    for entry in entries:
        if entry.product_id in seen or entry.product is None:
            continue

        seen.add(entry.product_id)
        products.append(entry.product)

        if len(products) >= limit:
            break

    return products


def get_favorite_products(user_id, limit=50):
    return (
        Product.query
        .options(selectinload(Product.names))
        .join(ProductFavorite, ProductFavorite.product_id == Product.id)
        .filter(
            ProductFavorite.user_id == user_id,
            Product.is_active.is_(True),
        )
        .order_by(ProductFavorite.created_at.desc())
        .limit(limit)
        .all()
    )
