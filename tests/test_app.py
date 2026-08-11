import pytest
from werkzeug.security import generate_password_hash

from app import app, db
from models import User


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SECRET_KEY"] = "test-secret"

    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            username="test",
            email="test@example.com",
            password_hash=generate_password_hash("test"),
        )
        db.session.add(user)
        db.session.commit()

        with app.test_client() as client:
            yield client


def login(client, username="test", password="test"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_login_page_loads(client):
    response = client.get("/login")
    assert b"HelpDesk Login" in response.data


def test_login_with_valid_credentials(client):
    response = login(client)
    assert b"Zalogowano pomy\xc5\x9blnie." in response.data
    assert b"Dashboard" in response.data


def test_login_with_invalid_credentials(client):
    response = client.post(
        "/login",
        data={"username": "bad", "password": "wrong"},
        follow_redirects=True,
    )
    assert b"Niepoprawna nazwa użytkownika lub hasło." in response.data


def test_protected_routes_require_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_create_ticket_after_login(client):
    login(client)
    response = client.post(
        "/tickets/create",
        data={"title": "Nowe zgłoszenie", "description": "Opis testowy"},
        follow_redirects=True,
    )
    assert b"Zg\xc5\x82oszenie zosta\xc5\x82o utworzone." in response.data
    assert b"Nowe zg\xc5\x82oszenie" in response.data
