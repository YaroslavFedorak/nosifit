from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class NosiFitAPI:
    base_url: str

    def health(self) -> bool:
        """Return whether the NosiFit backend is reachable."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.ok
        except requests.RequestException:
            return False
