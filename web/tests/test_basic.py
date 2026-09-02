import pytest
from web.app.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_home_page(client):
    respone = client.get("/")
    assert respone.status_code == 200
