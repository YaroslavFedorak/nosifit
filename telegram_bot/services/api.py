from dataclasses import dataclass, field
from urllib.parse import quote

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
    "invalid_water": "Вкажіть від 0,05 до 5 л.",
    "invalid_weight": "Вкажіть вагу від 20 до 400 кг.",
    "meal_not_found": "Цей прийом їжі вже видалено.",
    "entry_not_found": "Цей продукт уже видалено.",
    "nothing_to_copy": "Учора не було записів.",
    "duplicate_product": "У вас уже є продукт з такою назвою.",
    "duplicate_dish": "У вас уже є страва з такою назвою.",
    "dish_not_found": "Цю страву вже видалено.",
    "invalid_dish": "Перевірте назву страви (до 120 символів).",
    "product_not_found": "Цей продукт уже видалено.",
    "session_not_found": "Тренування не знайдено — можливо, почався новий день.",
    "telegram_session_scope": "Це доступно лише на сайті.",
    "invalid_barcode": "Це не схоже на штрихкод: потрібні 8, 12, 13 або 14 цифр з правильною контрольною цифрою.",
    "lookup_unavailable": "Пошук за штрихкодом тимчасово недоступний. Спробуйте за хвилину або знайдіть продукт за назвою.",
    "incomplete_product": "У базі бракує даних про цей продукт. Створіть свій продукт з етикетки.",
    "invalid_product_data": "Дані про цей продукт у базі неправдоподібні. Створіть свій продукт з етикетки.",
    "duplicate_barcode": "У вас уже є продукт з цим штрихкодом.",
    "rate_limited": "Забагато запитів. Спробуйте за хвилину.",
}


def _json_or_empty(response: requests.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


@dataclass
class NosiFitAPI:
    base_url: str
    session: requests.Session = field(default_factory=requests.Session)

    # Set once the web app says the session is gone (expired, revoked by
    # disconnecting Telegram, password changed, account deleted).
    expired: bool = False

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=10,
                allow_redirects=False,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise NosiFitAPIError("Не вдалося підключитися до NosiFit.") from exc
        payload = _json_or_empty(response) if not response.ok else {}
        # Each API reports its stable code in "code" (nutrition, auth) or
        # "error" (training).
        code = payload.get("code") or payload.get("error")
        if response.status_code == 403 and code == "telegram_session_scope":
            # The session is fine, the endpoint is just not open to the bot.
            raise NosiFitAPIError(ERROR_MESSAGES[code], code)
        needs_login = response.status_code in (401, 403) or (
            response.is_redirect
            and "/auth/login" in response.headers.get("Location", "")
        )
        if needs_login:
            self.expired = True
            raise NosiFitAPIError(
                "Сесія закінчилась. Увійдіть ще раз: /login",
                "session_expired",
            )
        if not response.ok:
            detail = ERROR_MESSAGES.get(code) or "Щось пішло не так. Спробуйте ще раз."
            raise NosiFitAPIError(detail, code)
        return response

    def ensure_authenticated(self) -> None:
        if not self.session.cookies:
            raise NosiFitAPIError("Спочатку увійдіть: /login")

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
        return self.search_products_page(query, locale, limit, category, offset)[0]

    def search_products_page(
        self,
        query: str,
        locale: str = "uk",
        limit: int = 8,
        category: str | None = None,
        offset: int = 0,
    ) -> tuple[list[dict], bool]:
        """One page of results and whether the server has more."""
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
        return payload.get("products", []), bool(payload.get("has_more"))

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

    def lookup_barcode(self, code: str, locale: str = "uk") -> dict:
        """Catalog product or Open Food Facts preview for a barcode
        (``status`` "found" / "not_found"); the same endpoint the website uses."""
        self.ensure_authenticated()
        return self._request(
            "GET",
            f"/api/nutrition/products/barcode/{quote(code, safe='')}",
            params={"locale": locale},
        ).json()

    def import_barcode(self, code: str, locale: str = "uk") -> dict:
        """Adds the scanned product to the catalog (or returns the existing one)."""
        self.ensure_authenticated()
        return self._request(
            "POST",
            f"/api/nutrition/products/barcode/{quote(code, safe='')}/import",
            json={"locale": locale},
        ).json()["product"]

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

    def log_food(
        self,
        category: str,
        items: list[dict] | None = None,
        *,
        dish_id: int | None = None,
        time: str | None = None,
        locale: str = "uk",
    ) -> dict:
        """Log products or a dish in one request; returns the updated day.

        The server finds or creates today's meal of ``category``, stores every
        entry with its nutrition snapshot and answers with the same payload
        as ``get_day`` (under ``"day"``), so no follow-up request is needed.
        """
        self.ensure_authenticated()
        body = {"category": category, "locale": locale, "return": "day"}
        if items is not None:
            body["items"] = items
        if dish_id is not None:
            body["dish_id"] = dish_id
        if time:
            body["time"] = time
        return self._request("POST", "/api/nutrition/log", json=body).json()

    def list_dishes(
        self,
        locale: str = "uk",
        limit: int = 8,
        offset: int = 0,
        sort: str = "recent",
        query: str = "",
    ) -> tuple[list[dict], bool]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/dishes",
            params={
                "locale": locale,
                "limit": limit,
                "offset": offset,
                "sort": sort,
                **({"q": query} if query else {}),
            },
        ).json()
        return payload.get("dishes", []), bool(payload.get("has_more"))

    def get_dish(self, dish_id: int, locale: str = "uk") -> dict:
        self.ensure_authenticated()
        return self._request(
            "GET", f"/api/nutrition/dishes/{dish_id}", params={"locale": locale}
        ).json()

    def create_dish(self, name: str, items: list[dict], locale: str = "uk") -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/dishes",
            json={"name": name, "items": items, "locale": locale},
        ).json()

    def update_dish(self, dish_id: int, data: dict, locale: str = "uk") -> dict:
        self.ensure_authenticated()
        return self._request(
            "PATCH",
            f"/api/nutrition/dishes/{dish_id}",
            json={**data, "locale": locale},
        ).json()

    def delete_dish(self, dish_id: int) -> dict:
        self.ensure_authenticated()
        return self._request("DELETE", f"/api/nutrition/dishes/{dish_id}").json()

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

    # --- Training ---------------------------------------------------------

    def search_exercises(
        self, query: str, locale: str = "uk", limit: int = 8, offset: int = 0
    ) -> dict:
        """{"items": [...], "has_more": bool}; items carry "last" values."""
        self.ensure_authenticated()
        return self._request(
            "GET",
            "/api/training/exercises/search",
            params={"q": query, "locale": locale, "limit": limit, "offset": offset},
        ).json()

    def get_recent_exercises(self, locale: str = "uk", limit: int = 6) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/training/exercises/recent",
            params={"locale": locale, "limit": limit},
        ).json()
        return payload.get("items", [])

    def get_today_session(self, locale: str = "uk") -> dict | None:
        """Today's session (server calendar) or None."""
        self.ensure_authenticated()
        return self._request(
            "GET",
            "/api/training/sessions/today",
            params={"locale": locale},
        ).json().get("session")

    def save_session(self, exercises: list[dict], session_id: int | None) -> dict:
        """Replace the whole workout of today's session ``session_id``.

        Without an id a new session is created; an empty list deletes the
        session. ``strict``: a stale id is an error (session_not_found)
        instead of silently starting another session.
        """
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/training/sessions/complete",
            json={"session_id": session_id, "strict": True, "exercises": exercises},
        ).json()
