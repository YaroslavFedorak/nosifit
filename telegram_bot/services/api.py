from dataclasses import dataclass, field

import requests


class NosiFitAPIError(RuntimeError):
    pass


@dataclass
class NosiFitAPI:
    base_url: str
    session: requests.Session = field(default_factory=requests.Session)

    def login(self, email: str, password: str) -> None:
        response = self.session.post(
            f"{self.base_url}/auth/login",
            data={"email": email, "password": password},
            timeout=10,
            allow_redirects=True,
        )
        if not response.ok:
            raise NosiFitAPIError("Не вдалося підключитися до NosiFit.")

        if response.url.rstrip("/").endswith("/auth/login"):
            raise NosiFitAPIError("Невірна електронна пошта або пароль.")

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        response = self.session.request(
            method, f"{self.base_url}{path}", timeout=10, **kwargs
        )
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
                detail = response.json().get("error", "NosiFit API request failed")
            except ValueError:
                detail = "NosiFit API request failed"
            raise NosiFitAPIError(detail)
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
        self, query: str, locale: str = "uk", limit: int = 8
    ) -> list[dict]:
        self.ensure_authenticated()
        payload = self._request(
            "GET",
            "/api/nutrition/products",
            params={"q": query, "locale": locale, "limit": limit},
        ).json()
        return payload.get("products", [])

    def get_product(self, product_id: int, locale: str = "uk") -> dict:
        self.ensure_authenticated()
        return self._request(
            "GET",
            f"/api/nutrition/products/{product_id}",
            params={"locale": locale},
        ).json()

    def create_meal(self, name: str, category: str, locale: str = "uk") -> dict:
        self.ensure_authenticated()
        return self._request(
            "POST",
            "/api/nutrition/meals",
            json={"name": name, "category": category, "locale": locale},
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
