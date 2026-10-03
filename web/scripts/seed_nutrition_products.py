from backend.app.extensions import db
from backend.app.models import Product, ProductName
from web.app import create_app


LIQUID_PRODUCTS = {
    "Water",
    "Sparkling water",
    "Black coffee",
    "Espresso",
    "Americano",
    "Black tea",
    "Green tea",
    "Herbal tea",
    "Iced tea, sweetened",
    "Milk 2.5%",
    "Milk 1.5%",
    "Kefir 2.5%",
    "Ayran",
    "Soy drink, unsweetened",
    "Almond drink, unsweetened",
    "Coconut water",
    "Orange juice",
    "Apple juice",
    "Grape juice",
    "Tomato juice",
    "Lemonade",
    "Cola",
    "Sports drink",
    "Energy drink",
}


PRODUCTS = [
    ("Куряче філе", "Chicken breast", "Pierś z kurczaka", 165, 31.0, 3.6, 0.0, 0.0, "g", 1),
    ("Куряче стегно", "Chicken thigh", "Udko z kurczaka", 209, 26.0, 10.9, 0.0, 0.0, "g", 1),
    ("Індиче філе", "Turkey breast", "Pierś z indyka", 135, 29.0, 1.6, 0.0, 0.0, "g", 1),
    ("Яловичина пісна", "Lean beef", "Chuda wołowina", 176, 26.0, 7.0, 0.0, 0.0, "g", 1),
    ("Свинина пісна", "Lean pork", "Chuda wieprzowina", 196, 27.0, 9.0, 0.0, 0.0, "g", 1),
    ("Лосось", "Salmon", "Łosoś", 208, 20.4, 13.4, 0.0, 0.0, "g", 1),
    ("Тунець консервований", "Canned tuna", "Tuńczyk w puszce", 116, 25.5, 0.8, 0.0, 0.0, "g", 1),
    ("Скумбрія", "Mackerel", "Makrela", 205, 18.6, 13.9, 0.0, 0.0, "g", 1),
    ("Креветки", "Shrimp", "Krewetki", 99, 24.0, 0.3, 0.2, 0.0, "g", 1),
    ("Яйце", "Egg", "Jajko", 143, 12.6, 9.5, 0.7, 0.0, "pcs", 50),
    ("Яєчний білок", "Egg white", "Białko jaja", 52, 10.9, 0.2, 0.7, 0.0, "g", 1),
    ("Грецький йогурт", "Greek yogurt", "Jogurt grecki", 73, 9.9, 2.0, 3.9, 0.0, "g", 1),
    ("Йогурт натуральний", "Plain yogurt", "Jogurt naturalny", 61, 3.5, 3.3, 4.7, 0.0, "g", 1),
    ("Сир кисломолочний 5%", "Cottage cheese 5%", "Twaróg 5%", 121, 17.0, 5.0, 3.0, 0.0, "g", 1),
    ("Сир кисломолочний 2%", "Cottage cheese 2%", "Twaróg 2%", 103, 18.0, 2.0, 3.0, 0.0, "g", 1),
    ("Твердий сир", "Hard cheese", "Ser żółty", 356, 25.0, 27.0, 2.0, 0.0, "g", 1),
    ("Моцарела", "Mozzarella", "Mozzarella", 280, 28.0, 17.0, 3.1, 0.0, "g", 1),
    ("Вівсянка", "Oatmeal", "Płatki owsiane", 389, 16.9, 6.9, 66.3, 10.6, "g", 1),
    ("Рис білий сухий", "White rice, dry", "Ryż biały, suchy", 365, 7.1, 0.7, 80.0, 1.3, "g", 1),
    ("Рис коричневий сухий", "Brown rice, dry", "Ryż brązowy, suchy", 370, 7.5, 2.7, 77.0, 3.5, "g", 1),
    ("Гречка суха", "Buckwheat, dry", "Kasza gryczana, sucha", 343, 13.3, 3.4, 71.5, 10.0, "g", 1),
    ("Кіноа суха", "Quinoa, dry", "Komosa ryżowa, sucha", 368, 14.1, 6.1, 64.2, 7.0, "g", 1),
    ("Паста суха", "Pasta, dry", "Makaron, suchy", 350, 12.5, 1.5, 70.0, 3.0, "g", 1),
    ("Цільнозернова паста", "Whole wheat pasta", "Makaron pełnoziarnisty", 348, 13.0, 2.5, 65.0, 9.0, "g", 1),
    ("Хліб пшеничний", "White bread", "Chleb pszenny", 266, 8.9, 3.2, 49.0, 2.7, "g", 1),
    ("Хліб цільнозерновий", "Whole grain bread", "Chleb pełnoziarnisty", 247, 13.0, 4.2, 41.0, 7.0, "g", 1),
    ("Тортилья пшенична", "Wheat tortilla", "Tortilla pszenna", 310, 8.0, 8.0, 52.0, 3.0, "g", 1),
    ("Картопля", "Potato", "Ziemniak", 77, 2.0, 0.1, 17.5, 2.2, "g", 1),
    ("Солодка картопля", "Sweet potato", "Bataty", 86, 1.6, 0.1, 20.1, 3.0, "g", 1),
    ("Кукурудза", "Corn", "Kukurydza", 86, 3.3, 1.4, 19.0, 2.7, "g", 1),
    ("Червона квасоля варена", "Red kidney beans, cooked", "Czerwona fasola, gotowana", 127, 8.7, 0.5, 22.8, 6.4, "g", 1),
    ("Нут варений", "Chickpeas, cooked", "Ciecierzyca, gotowana", 164, 8.9, 2.6, 27.4, 7.6, "g", 1),
    ("Сочевиця варена", "Lentils, cooked", "Soczewica, gotowana", 116, 9.0, 0.4, 20.1, 7.9, "g", 1),
    ("Броколі", "Broccoli", "Brokuły", 34, 2.8, 0.4, 6.6, 2.6, "g", 1),
    ("Цвітна капуста", "Cauliflower", "Kalafior", 25, 1.9, 0.3, 5.0, 2.0, "g", 1),
    ("Шпинат", "Spinach", "Szpinak", 23, 2.9, 0.4, 3.6, 2.2, "g", 1),
    ("Помідор", "Tomato", "Pomidor", 18, 0.9, 0.2, 3.9, 1.2, "pcs", 120),
    ("Огірок", "Cucumber", "Ogórek", 15, 0.7, 0.1, 3.6, 0.5, "pcs", 120),
    ("Морква", "Carrot", "Marchew", 41, 0.9, 0.2, 9.6, 2.8, "pcs", 60),
    ("Болгарський перець", "Bell pepper", "Papryka", 31, 1.0, 0.3, 6.0, 2.1, "pcs", 150),
    ("Авокадо", "Avocado", "Awokado", 160, 2.0, 14.7, 8.5, 6.7, "pcs", 150),
    ("Яблуко", "Apple", "Jabłko", 52, 0.3, 0.2, 13.8, 2.4, "pcs", 180),
    ("Банан", "Banana", "Banan", 89, 1.1, 0.3, 22.8, 2.6, "pcs", 120),
    ("Апельсин", "Orange", "Pomarańcza", 47, 0.9, 0.1, 11.8, 2.4, "pcs", 180),
    ("Полуниця", "Strawberry", "Truskawki", 32, 0.7, 0.3, 7.7, 2.0, "g", 1),
    ("Чорниця", "Blueberries", "Borówki", 57, 0.7, 0.3, 14.5, 2.4, "g", 1),
    ("Малина", "Raspberries", "Maliny", 52, 1.2, 0.7, 11.9, 6.5, "g", 1),
    ("Арахіс", "Peanuts", "Orzeszki ziemne", 567, 25.8, 49.2, 16.1, 8.5, "g", 1),
    ("Мигдаль", "Almonds", "Migdały", 579, 21.2, 49.9, 21.6, 12.5, "g", 1),
    ("Волоські горіхи", "Walnuts", "Orzechy włoskie", 654, 15.2, 65.2, 13.7, 6.7, "g", 1),
    ("Арахісова паста", "Peanut butter", "Masło orzechowe", 588, 25.1, 50.4, 20.0, 6.0, "g", 1),
    ("Оливкова олія", "Olive oil", "Oliwa z oliwek", 884, 0.0, 100.0, 0.0, 0.0, "ml", 0.92),
    ("Мед", "Honey", "Miód", 304, 0.3, 0.0, 82.4, 0.2, "g", 1),
    ("Темний шоколад 70%", "Dark chocolate 70%", "Czekolada gorzka 70%", 598, 7.8, 42.6, 45.9, 10.9, "g", 1),
    ("Кава чорна", "Black coffee", "Kawa czarna", 2, 0.3, 0.0, 0.0, 0.0, "ml", 1),
    ("Еспресо", "Espresso", "Espresso", 9, 0.1, 0.0, 0.0, 0.0, "ml", 1),
    ("Американо", "Americano", "Americano", 2, 0.3, 0.0, 0.0, 0.0, "ml", 1),
    ("Чай чорний", "Black tea", "Czarna herbata", 1, 0.1, 0.0, 0.2, 0.0, "ml", 1),
    ("Чай зелений", "Green tea", "Zielona herbata", 1, 0.1, 0.0, 0.2, 0.0, "ml", 1),
    ("Трав'яний чай", "Herbal tea", "Herbata ziołowa", 1, 0.0, 0.0, 0.2, 0.0, "ml", 1),
    ("Холодний чай солодкий", "Iced tea, sweetened", "Herbata mrożona słodzona", 30, 0.0, 0.0, 7.5, 0.0, "ml", 1),
    ("Молоко 2.5%", "Milk 2.5%", "Mleko 2,5%", 52, 3.2, 2.5, 4.8, 0.0, "ml", 1.03),
    ("Молоко 1.5%", "Milk 1.5%", "Mleko 1,5%", 46, 3.4, 1.5, 4.8, 0.0, "ml", 1.03),
    ("Кефір 2.5%", "Kefir 2.5%", "Kefir 2,5%", 52, 3.3, 2.5, 4.0, 0.0, "ml", 1.03),
    ("Айран", "Ayran", "Ayran", 35, 2.0, 1.5, 3.0, 0.0, "ml", 1.02),
    ("Соєвий напій без цукру", "Soy drink, unsweetened", "Napój sojowy niesłodzony", 33, 3.3, 1.8, 0.5, 0.4, "ml", 1),
    ("Мигдальний напій без цукру", "Almond drink, unsweetened", "Napój migdałowy niesłodzony", 15, 0.5, 1.1, 0.3, 0.2, "ml", 1),
    ("Кокосова вода", "Coconut water", "Woda kokosowa", 19, 0.7, 0.2, 3.7, 1.1, "ml", 1),
    ("Апельсиновий сік", "Orange juice", "Sok pomarańczowy", 45, 0.7, 0.2, 10.4, 0.2, "ml", 1.04),
    ("Яблучний сік", "Apple juice", "Sok jabłkowy", 46, 0.1, 0.1, 11.3, 0.2, "ml", 1.04),
    ("Виноградний сік", "Grape juice", "Sok winogronowy", 60, 0.4, 0.1, 15.0, 0.2, "ml", 1.05),
    ("Томатний сік", "Tomato juice", "Sok pomidorowy", 17, 0.9, 0.1, 3.5, 0.4, "ml", 1.02),
    ("Лимонад", "Lemonade", "Lemoniada", 40, 0.0, 0.0, 10.0, 0.0, "ml", 1),
    ("Кола", "Cola", "Cola", 42, 0.0, 0.0, 10.6, 0.0, "ml", 1),
    ("Спортивний напій", "Sports drink", "Napój izotoniczny", 25, 0.0, 0.0, 6.0, 0.0, "ml", 1),
    ("Енергетичний напій", "Energy drink", "Napój energetyczny", 45, 0.0, 0.0, 11.0, 0.0, "ml", 1),
    ("Газована вода", "Sparkling water", "Woda gazowana", 0, 0.0, 0.0, 0.0, 0.0, "ml", 1),
    ("Вода", "Water", "Woda", 0, 0.0, 0.0, 0.0, 0.0, "ml", 1),
]


CATEGORY_RULES = {
    "meat": ("chicken", "turkey", "beef", "pork"),
    "fish": ("salmon", "tuna", "mackerel", "shrimp"),
    "dairy": ("yogurt", "cottage cheese", "hard cheese", "mozzarella", "milk", "kefir", "ayran", "soy drink", "almond drink"),
    "eggs": ("egg",),
    "grains": ("oatmeal", "rice", "buckwheat", "quinoa", "pasta"),
    "bread": ("bread", "tortilla"),
    "vegetables": ("potato", "sweet potato", "corn", "broccoli", "cauliflower", "spinach", "tomato", "cucumber", "carrot", "bell pepper", "avocado"),
    "fruits": ("apple", "banana", "orange", "strawber", "blueber", "raspber"),
    "legumes": ("kidney beans", "chickpeas", "lentils"),
    "nuts": ("peanuts", "almonds", "walnuts", "peanut butter"),
    "oils": ("olive oil",),
    "sweets": ("honey", "chocolate"),
    "beverages": ("coffee", "espresso", "americano", "tea", "water", "juice", "lemonade", "cola", "sports drink", "energy drink"),
}


def product_category(name):
    normalized = name.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(keyword in normalized for keyword in keywords):
            return category
    return "other"


def seed_products():
    app = create_app()

    with app.app_context():
        created = 0
        skipped = 0

        for (
            uk,
            en,
            pl,
            kcal,
            protein,
            fat,
            carbs,
            fiber,
            default_unit,
            grams_per_unit,
        ) in PRODUCTS:
            existing = ProductName.query.filter_by(
                locale="en",
                name=en,
            ).first()

            if existing:
                existing.product.category = product_category(en)
                if en in LIQUID_PRODUCTS:
                    existing.product.liquid_ml_per_100g = 100
                skipped += 1
                continue

            product = Product(
                source="system",
                kcal_per_100g=kcal,
                protein_per_100g=protein,
                fat_per_100g=fat,
                carbs_per_100g=carbs,
                fiber_per_100g=fiber,
                liquid_ml_per_100g=(
                    100 if en in LIQUID_PRODUCTS else 0
                ),
                category=product_category(en),
                default_unit=default_unit,
                grams_per_unit=grams_per_unit,
            )

            db.session.add(product)
            db.session.flush()

            db.session.add_all(
                [
                    ProductName(
                        product_id=product.id,
                        locale="uk",
                        name=uk,
                    ),
                    ProductName(
                        product_id=product.id,
                        locale="en",
                        name=en,
                    ),
                    ProductName(
                        product_id=product.id,
                        locale="pl",
                        name=pl,
                    ),
                ]
            )

            created += 1

        db.session.commit()

        print(f"Nutrition products created: {created}")
        print(f"Nutrition products skipped: {skipped}")


if __name__ == "__main__":
    seed_products()
