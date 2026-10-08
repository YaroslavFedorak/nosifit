"""normalize meal categories to keys and add Russian product names

Revision ID: a9c3e5f7b1d2
Revises: f6a1c9d4e8b2
Create Date: 2026-10-05 20:00:00.000000

Meals used to store a Ukrainian label ("Сніданок") as both name and category,
so other interface languages showed Ukrainian text. They now store a
language-independent key (breakfast / lunch / dinner / snack) that clients
translate.

System catalog products were seeded without Russian names, so Russian users
saw English. This backfills them, matched by the English name.
"""

from alembic import op
import sqlalchemy as sa


revision = "a9c3e5f7b1d2"
down_revision = "f6a1c9d4e8b2"
branch_labels = None
depends_on = None


MEAL_CATEGORY_ALIASES = {
    "breakfast": ["сніданок", "śniadanie", "sniadanie", "завтрак"],
    "lunch": ["обід", "obiad", "обед"],
    "dinner": ["вечеря", "kolacja", "ужин"],
    "snack": ["перекус", "przekąska", "przekaska"],
}

RU_NAMES = {
    "Chicken breast": "Куриное филе",
    "Chicken thigh": "Куриное бедро",
    "Turkey breast": "Филе индейки",
    "Lean beef": "Говядина постная",
    "Lean pork": "Свинина постная",
    "Salmon": "Лосось",
    "Canned tuna": "Тунец консервированный",
    "Mackerel": "Скумбрия",
    "Shrimp": "Креветки",
    "Egg": "Яйцо",
    "Egg white": "Яичный белок",
    "Greek yogurt": "Греческий йогурт",
    "Plain yogurt": "Йогурт натуральный",
    "Cottage cheese 5%": "Творог 5%",
    "Cottage cheese 2%": "Творог 2%",
    "Hard cheese": "Твёрдый сыр",
    "Mozzarella": "Моцарелла",
    "Oatmeal": "Овсянка",
    "White rice, dry": "Рис белый сухой",
    "Brown rice, dry": "Рис коричневый сухой",
    "Buckwheat, dry": "Гречка сухая",
    "Quinoa, dry": "Киноа сухая",
    "Pasta, dry": "Макароны сухие",
    "Whole wheat pasta": "Цельнозерновые макароны",
    "White bread": "Хлеб пшеничный",
    "Whole grain bread": "Хлеб цельнозерновой",
    "Wheat tortilla": "Тортилья пшеничная",
    "Potato": "Картофель",
    "Sweet potato": "Батат",
    "Corn": "Кукуруза",
    "Red kidney beans, cooked": "Красная фасоль варёная",
    "Chickpeas, cooked": "Нут варёный",
    "Lentils, cooked": "Чечевица варёная",
    "Broccoli": "Брокколи",
    "Cauliflower": "Цветная капуста",
    "Spinach": "Шпинат",
    "Tomato": "Помидор",
    "Cucumber": "Огурец",
    "Carrot": "Морковь",
    "Bell pepper": "Болгарский перец",
    "Avocado": "Авокадо",
    "Apple": "Яблоко",
    "Banana": "Банан",
    "Orange": "Апельсин",
    "Strawberry": "Клубника",
    "Blueberries": "Черника",
    "Raspberries": "Малина",
    "Peanuts": "Арахис",
    "Almonds": "Миндаль",
    "Walnuts": "Грецкие орехи",
    "Peanut butter": "Арахисовая паста",
    "Olive oil": "Оливковое масло",
    "Honey": "Мёд",
    "Dark chocolate 70%": "Тёмный шоколад 70%",
    "Black coffee": "Кофе чёрный",
    "Espresso": "Эспрессо",
    "Americano": "Американо",
    "Black tea": "Чай чёрный",
    "Green tea": "Чай зелёный",
    "Herbal tea": "Травяной чай",
    "Iced tea, sweetened": "Холодный чай сладкий",
    "Milk 2.5%": "Молоко 2.5%",
    "Milk 1.5%": "Молоко 1.5%",
    "Kefir 2.5%": "Кефир 2.5%",
    "Ayran": "Айран",
    "Soy drink, unsweetened": "Соевый напиток без сахара",
    "Almond drink, unsweetened": "Миндальный напиток без сахара",
    "Coconut water": "Кокосовая вода",
    "Orange juice": "Апельсиновый сок",
    "Apple juice": "Яблочный сок",
    "Grape juice": "Виноградный сок",
    "Tomato juice": "Томатный сок",
    "Lemonade": "Лимонад",
    "Cola": "Кола",
    "Sports drink": "Спортивный напиток",
    "Energy drink": "Энергетический напиток",
    "Sparkling water": "Газированная вода",
    "Water": "Вода",
}


def upgrade():
    bind = op.get_bind()

    for key, labels in MEAL_CATEGORY_ALIASES.items():
        values = [key, *labels]
        bind.execute(
            sa.text(
                "UPDATE meals SET category = :key, name = :key "
                "WHERE lower(trim(category)) = ANY(:values) "
                "OR lower(trim(name)) = ANY(:values)"
            ),
            {"key": key, "values": values},
        )

    for en_name, ru_name in RU_NAMES.items():
        bind.execute(
            sa.text(
                "INSERT INTO nutrition_product_names (product_id, locale, name) "
                "SELECT n.product_id, 'ru', :ru_name "
                "FROM nutrition_product_names n "
                "JOIN nutrition_products p ON p.id = n.product_id "
                "WHERE n.locale = 'en' AND n.name = :en_name "
                "AND p.owner_user_id IS NULL "
                "AND NOT EXISTS ("
                "SELECT 1 FROM nutrition_product_names r "
                "WHERE r.product_id = n.product_id AND r.locale = 'ru')"
            ),
            {"en_name": en_name, "ru_name": ru_name},
        )


def downgrade():
    labels = {
        "breakfast": "Сніданок",
        "lunch": "Обід",
        "dinner": "Вечеря",
        "snack": "Перекус",
    }

    bind = op.get_bind()
    for key, label in labels.items():
        bind.execute(
            sa.text(
                "UPDATE meals SET category = :label, name = :label "
                "WHERE category = :key"
            ),
            {"key": key, "label": label},
        )

    # Russian product names stay: they are harmless and removing them could
    # also remove names that were added later by hand.
