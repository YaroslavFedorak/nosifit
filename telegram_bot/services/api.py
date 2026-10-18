from dataclasses import dataclass, field
from urllib.parse import quote

import requests

from telegram_bot.i18n import Texts, current_language, t


class NosiFitAPIError(RuntimeError):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


# Backend errors come with a stable ``code``; users see the text of that code
# in their language (``err.<code>`` in the bot's locales), not the English
# ``error`` message.
ERROR_MESSAGES = Texts(
    "err",
    (
        "invalid_category",
        "invalid_entry",
        "invalid_product",
        "invalid_water",
        "invalid_weight",
        "meal_not_found",
        "entry_not_found",
        "nothing_to_copy",
        "duplicate_product",
        "duplicate_dish",
        "dish_not_found",
        "invalid_dish",
        "product_not_found",
        "session_not_found",
        "telegram_session_scope",
        "invalid_barcode",
        "lookup_unavailable",
        "incomplete_product",
        "invalid_product_data",
        "duplicate_barcode",
        "rate_limited",
        "under_minimum_age",
        "consent_required",
    ),
)

SHOWN_CODES = (
    "telegram_session_scope",
    "consent_required",
    "under_minimum_age",
)


def error_message(code: str | None) -> str:
    return ERROR_MESSAGES.get(code) or t("err.generic")


# Default of every ``locale`` argument: the language of the update being handled.
CURRENT_LANGUAGE = "current"


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
        for field_name in ("params", "json"):
            body = kwargs.get(field_name)
            if isinstance(body, dict) and body.get("locale") == CURRENT_LANGUAGE:
                kwargs[field_name] = {**body, "locale": current_language()}
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=10,
                allow_redirects=False,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise NosiFitAPIError(t("err.connect")) from exc
        payload = _json_or_empty(response) if not response.ok else {}
        # Each API reports its stable code in "code" (nutrition, auth) or
        # "error" (training).
        code = payload.get("code") or payload.get("error")
        if response.status_code == 403 and code in SHOWN_CODES:
            # The session is fine: the endpoint is not open to the bot, or the
            # account still has to accept the privacy policy (/consent).
            raise NosiFitAPIError(error_message(code), code)
        needs_login = response.status_code in (401, 403) or (
            response.is_redirect
            and "/auth/login" in response.headers.get("Location", "")
        )
        if needs_login:
            self.expired = True
            raise NosiFitAPIError(
                t("err.session_expired"),
                "session_expired",
            )
        if not response.ok:
            detail = error_message(code)
            raise NosiFitAPIError(detail, code)
        return response

    def ensure_authenticated(self) -> None:
        if not self.session.cookies:
            raise NosiFitAPIError(t("err.login_first"))

    def give_consent(self) -> dict:
        """Accept the privacy policy and health-data processing (both, explicitly)."""
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/consent",
            json={"privacy_consent": True, "health_consent": True, "age_confirmed": True},
        ).json()

    def withdraw_consent(self) -> dict:
        """Withdraw the health-data consent: the web app erases those records."""
        self.ensure_authenticated()
        return self._request("DELETE", "/api/consent", json={"confirm_erase": True}).json()

    def get_day(self, locale: str = CURRENT_LANGUAGE) -> dict:
        self.ensure_authenticated()
        return self._request(
            "GET", "/api/nutrition/day", params={"locale": locale}
        ).json()

    def search_products(
        self,
        query: str,
        locale: str = CURRENT_LANGUAGE,
        limit: int = 8,
        category: str | None = None,
        offset: int = 0,
    ) -> list[dict]:
        return self.search_products_page(query, locale, limit, category, offset)[0]

    def search_products_page(
        self,
        query: str,
        locale: str = CURRENT_LANGUAGE,
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
        self, locale: str = CURRENT_LANGUAGE, limit: int = 50, category: str | None = None
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

    def get_favorite_products(self, locale: str = CURRENT_LANGUAGE, limit: int = 50) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products/favorites",
            params={"locale": locale},
        ).json()
        return payload.get("products", [])[:limit]

    def get_recent_products(self, locale: str = CURRENT_LANGUAGE, limit: int = 12) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products/recent",
            params={"locale": locale},
        ).json()
        return payload.get("products", [])[:limit]

    def get_my_products(self, locale: str = CURRENT_LANGUAGE, limit: int = 50) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products/mine",
            params={"locale": locale},
        ).json()
        return payload.get("products", [])[:limit]

    def set_product_favorite(
        self, product_id: int, favorite: bool, locale: str = CURRENT_LANGUAGE
    ) -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            f"/api/nutrition/products/{product_id}/favorite",
            json={"favorite": favorite, "locale": locale},
        ).json()

    def create_product(self, data: dict, locale: str = CURRENT_LANGUAGE) -> dict:
        self.ensure_authenticated()
        payload = {**data, "locale": locale}
        return self._request(
            "POST",
            "/api/nutrition/products",
            json=payload,
        ).json()

    def get_product(self, product_id: int, locale: str = CURRENT_LANGUAGE) -> dict:
        self.ensure_authenticated()
        return self._request(
            "GET",
            f"/api/nutrition/products/{product_id}",
            params={"locale": locale},
        ).json()

    def lookup_barcode(self, code: str, locale: str = CURRENT_LANGUAGE) -> dict:
        """Catalog product or Open Food Facts preview for a barcode
        (``status`` "found" / "not_found"); the same endpoint the website uses."""
        self.ensure_authenticated()
        return self._request(
            "GET",
            f"/api/nutrition/products/barcode/{quote(code, safe='')}",
            params={"locale": locale},
        ).json()

    def import_barcode(self, code: str, locale: str = CURRENT_LANGUAGE) -> dict:
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
        locale: str = CURRENT_LANGUAGE,
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
        locale: str = CURRENT_LANGUAGE,
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
        locale: str = CURRENT_LANGUAGE,
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
        locale: str = CURRENT_LANGUAGE,
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
        locale: str = CURRENT_LANGUAGE,
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
        locale: str = CURRENT_LANGUAGE,
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
        locale: str = CURRENT_LANGUAGE,
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

    def get_dish(self, dish_id: int, locale: str = CURRENT_LANGUAGE) -> dict:
        self.ensure_authenticated()
        return self._request(
            "GET", f"/api/nutrition/dishes/{dish_id}", params={"locale": locale}
        ).json()

    def create_dish(self, name: str, items: list[dict], locale: str = CURRENT_LANGUAGE) -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/dishes",
            json={"name": name, "items": items, "locale": locale},
        ).json()

    def update_dish(self, dish_id: int, data: dict, locale: str = CURRENT_LANGUAGE) -> dict:
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

    def update_product(self, product_id: int, data: dict, locale: str = CURRENT_LANGUAGE) -> dict:
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
        self, query: str, locale: str = CURRENT_LANGUAGE, limit: int = 8, offset: int = 0
    ) -> dict:
        """{"items": [...], "has_more": bool}; items carry "last" values."""
        self.ensure_authenticated()
        return self._request(
            "GET",
            "/api/training/exercises/search",
            params={"q": query, "locale": locale, "limit": limit, "offset": offset},
        ).json()

    def get_recent_exercises(self, locale: str = CURRENT_LANGUAGE, limit: int = 6) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/training/exercises/recent",
            params={"locale": locale, "limit": limit},
        ).json()
        return payload.get("items", [])

    def get_today_session(self, locale: str = CURRENT_LANGUAGE) -> dict | None:
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
