from dataclasses import dataclass, field

import requests


class NosiFitAPIError(RuntimeError):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


# Backend errors come with a stable ``code``; show users Ukrainian text
# instead of the English ``error`` message.
ERROR_MESSAGES = {
    "invalid_category": "Оберіть тип прийому їжі.",
    "invalid_entry": "Перевірте кількість продукту: до 5000 г / мл або до 100 шт.",
    "invalid_product": "Перевірте значення продукту: калорії до 950, білки, жири й вуглеводи до 100 г на 100 г.",
    "invalid_water": "Вкажіть об'єм від 0.05 до 5 л.",
    "invalid_weight": "Вкажіть вагу від 20 до 400 кг.",
    "meal_not_found": "Цей прийом їжі вже видалено.",
    "entry_not_found": "Цей продукт уже видалено.",
    "nothing_to_copy": "Учора не було записів.",
    "product_not_found": "Цей продукт уже видалено.",
}


@dataclass
class NosiFitAPI:
    base_url: str
    session: requests.Session = field(default_factory=requests.Session)

    def login(self, email: str, password: str) -> None:
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                data={"email": email, "password": password},
                timeout=10,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise NosiFitAPIError(
                "Не вдалося підключитися до NosiFit."
            ) from exc

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            if "/dashboard" in location and self.session.cookies:
                return
            raise NosiFitAPIError("Невірна електронна пошта або пароль.")

        if response.status_code in (200, 401, 403):
            raise NosiFitAPIError("Невірна електронна пошта або пароль.")

        raise NosiFitAPIError(
            f"NosiFit повернув помилку авторизації (HTTP {response.status_code})."
        )

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(
                method, f"{self.base_url}{path}", timeout=10, **kwargs
            )
        except requests.RequestException as exc:
            raise NosiFitAPIError("Не вдалося підключитися до NosiFit.") from exc
        needs_login = (
            response.status_code in (401, 403)
            or response.url.rstrip("/").endswith("/auth/login")
        )
        if needs_login:
            raise NosiFitAPIError(
                "Сесія NosiFit завершилася. Виконайте вхід ще раз."
            )
        if not response.ok:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            code = payload.get("code")
            detail = ERROR_MESSAGES.get(code) or "NosiFit не зміг виконати запит. Спробуйте ще раз."
            raise NosiFitAPIError(detail, code)
        return response

    def health(self) -> bool:
        try:
            return self.session.get(f"{self.base_url}/", timeout=5).ok
        except requests.RequestException:
            return False

    def ensure_authenticated(self) -> None:
        if not self.session.cookies:
            raise NosiFitAPIError("Ви не авторизовані. Виконайте вхід у NosiFit.")

    def get_day(self, locale: str = "uk") -> dict:
        self.ensure_authenticated()
        return self._request(
            "GET", "/api/nutrition/day", params={"locale": locale}
        ).json()

    def search_products(
        self,
        query: str,
        locale: str = "uk",
        limit: int = 8,
        category: str | None = None,
        offset: int = 0,
    ) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products",
            params={
                "q": query,
                "locale": locale,
                "limit": limit,
                "offset": offset,
                **({"category": category} if category else {}),
            },
        ).json()
        return payload.get("products", [])

    def get_products(
        self, locale: str = "uk", limit: int = 50, category: str | None = None
    ) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products",
            params={
                "q": "",
                "locale": locale,
                "limit": limit,
                **({"category": category} if category else {}),
            },
        ).json()
        return payload.get("products", [])

    def get_favorite_products(self, locale: str = "uk", limit: int = 50) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products/favorites",
            params={"locale": locale},
        ).json()
        return payload.get("products", [])[:limit]

    def get_recent_products(self, locale: str = "uk", limit: int = 12) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products/recent",
            params={"locale": locale},
        ).json()
        return payload.get("products", [])[:limit]

    def get_my_products(self, locale: str = "uk", limit: int = 50) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products/mine",
            params={"locale": locale},
        ).json()
        return payload.get("products", [])[:limit]

    def set_product_favorite(
        self, product_id: int, favorite: bool, locale: str = "uk"
    ) -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            f"/api/nutrition/products/{product_id}/favorite",
            json={"favorite": favorite, "locale": locale},
        ).json()

    def create_product(self, data: dict, locale: str = "uk") -> dict:
        self.ensure_authenticated()
        payload = {**data, "locale": locale}
        return self._request(
            "POST",
            "/api/nutrition/products",
            json=payload,
        ).json()

    def get_product(self, product_id: int, locale: str = "uk") -> dict:
        self.ensure_authenticated()
        return self._request(
            "GET",
            f"/api/nutrition/products/{product_id}",
            params={"locale": locale},
        ).json()

    def create_meal(
        self,
        name: str,
        category: str,
        time: str | None = None,
        locale: str = "uk",
    ) -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/meals",
            json={
                "name": name,
                "category": category,
                "time": time,
                "locale": locale,
            },
        ).json()

    def update_meal(
        self,
        meal_id: int,
        *,
        name: str,
        category: str,
        time: str | None = None,
        locale: str = "uk",
    ) -> dict:
        self.ensure_authenticated()
        return self._request(
            "PUT",
            f"/api/nutrition/meals/{meal_id}",
            json={
                "name": name,
                "category": category,
                "time": time,
                "locale": locale,
            },
        ).json()

    def delete_meal(self, meal_id: int) -> dict:
        self.ensure_authenticated()
        return self._request(
            "DELETE",
            f"/api/nutrition/meals/{meal_id}",
        ).json()

    def update_entry(
        self,
        entry_id: int,
        *,
        amount: float,
        unit: str,
        meal_id: int | None = None,
        locale: str = "uk",
    ) -> dict:
        self.ensure_authenticated()
        payload = {
            "amount": amount,
            "unit": unit,
            "locale": locale,
        }
        if meal_id:
            payload["meal_id"] = meal_id
        return self._request(
            "PATCH",
            f"/api/nutrition/entries/{entry_id}",
            json=payload,
        ).json()

    def delete_entry(self, entry_id: int) -> dict:
        self.ensure_authenticated()
        return self._request(
            "DELETE",
            f"/api/nutrition/entries/{entry_id}",
        ).json()

    def add_entries(
        self,
        meal_id: int,
        items: list[dict],
        locale: str = "uk",
    ) -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/entries/bulk",
            json={
                "meal_id": meal_id,
                "locale": locale,
                "items": items,
            },
        ).json()

    def add_entry(
        self,
        meal_id: int,
        product_id: int,
        amount: float,
        unit: str,
        locale: str = "uk",
    ) -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/entries",
            json={
                "meal_id": meal_id,
                "product_id": product_id,
                "amount": amount,
                "unit": unit,
                "locale": locale,
            },
        ).json()

    def get_water(self) -> dict:
        self.ensure_authenticated()
        return self._request("GET", "/api/nutrition/water").json()

    def add_water(self, liters: float) -> dict:
        """Positive adds, negative subtracts."""
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/water",
            json={"amount": liters},
        ).json()

    def get_weight(self) -> dict:
        self.ensure_authenticated()
        return self._request("GET", "/api/nutrition/weight").json()

    def update_weight(self, weight: float) -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/weight",
            json={"weight": weight},
        ).json()

    def update_product(self, product_id: int, data: dict, locale: str = "uk") -> dict:
        """Edit one of the user's own products. Logged entries are recalculated."""
        self.ensure_authenticated()
        return self._request(
            "PATCH",
            f"/api/nutrition/products/{product_id}",
            json={**data, "locale": locale},
        ).json()

    def delete_product(self, product_id: int) -> dict:
        self.ensure_authenticated()
        return self._request(
            "DELETE",
            f"/api/nutrition/products/{product_id}",
        ).json()
