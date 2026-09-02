from models import User


def test_login_page_loads(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "HelpDesk Login" in response.get_data(as_text=True)


def test_login_with_valid_user_credentials_redirects_to_tickets(client, login):
    response = login()
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Zalogowano pomyślnie." in body
    assert "Lista zgłoszeń" in body

    with client.session_transaction() as session:
        assert "user_id" in session


def test_login_with_valid_technician_credentials_redirects_to_dashboard(client, login):
    response = login("tech")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Zalogowano pomyślnie." in body
    assert "Dashboard" in body


def test_login_with_invalid_credentials_is_rejected(client):
    response = client.post(
        "/login",
        data={"username": "bad", "password": "wrong"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Niepoprawna nazwa użytkownika lub hasło." in response.get_data(as_text=True)


def test_inactive_user_cannot_log_in(client):
    response = client.post(
        "/login",
        data={"username": "inactive", "password": "inactive"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Konto użytkownika zostało dezaktywowane." in response.get_data(as_text=True)


def test_protected_route_requires_login(client):
    response = client.get("/tickets")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_regular_user_is_redirected_from_dashboard_to_ticket_list(client, login):
    login()

    response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tickets")


def test_regular_user_cannot_open_admin_panel(client, login):
    login()

    response = client.get("/admin/users")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
