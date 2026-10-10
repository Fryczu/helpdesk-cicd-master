from models import SecurityEvent, User


def test_successful_login_is_recorded(app, client, login):
    login("test")

    with app.app_context():
        event = SecurityEvent.query.filter_by(event_type="login_success").one()
        assert event.success is True
        assert event.username == "test"
        assert event.user_id == User.query.filter_by(username="test").one().id
        assert event.ip_address == "127.0.0.1"


def test_failed_login_is_recorded_without_password(app, client):
    response = client.post(
        "/login",
        data={"username": "unknown-user", "password": "super-secret-password"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        event = SecurityEvent.query.filter_by(event_type="login_failed").one()
        assert event.success is False
        assert event.username == "unknown-user"
        assert event.user_id is None
        assert "super-secret-password" not in (event.details or "")


def test_logout_is_recorded(app, client, login):
    login("test")
    client.get("/logout", follow_redirects=True)

    with app.app_context():
        assert SecurityEvent.query.filter_by(event_type="logout", username="test").count() == 1


def test_denied_admin_access_is_recorded(app, client, login):
    login("test")
    response = client.get("/admin/users")

    assert response.status_code == 302
    with app.app_context():
        event = SecurityEvent.query.filter_by(event_type="access_denied", username="test").one()
        assert event.success is False
        assert "/admin/users" in event.details


def test_admin_role_change_and_password_reset_are_recorded(app, client, login, ids):
    login("admin")
    response = client.post(
        f"/admin/users/{ids['other']}/edit",
        data={
            "role": "Technician",
            "is_active": "on",
            "password": "new-password-123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        target = User.query.filter_by(username="other").one()
        assert target.role == "Technician"
        assert SecurityEvent.query.filter_by(
            event_type="user_role_changed", target_user_id=target.id
        ).count() == 1
        assert SecurityEvent.query.filter_by(
            event_type="user_password_reset", target_user_id=target.id
        ).count() == 1


def test_admin_can_view_security_event_log(app, client, login):
    login("admin")
    client.post(
        "/login",
        data={"username": "bad-login", "password": "wrong"},
        follow_redirects=True,
    )
    # The second POST redirects immediately because the admin session is active,
    # so explicitly create a failed event by logging out first.
    client.get("/logout")
    client.post(
        "/login",
        data={"username": "bad-login", "password": "wrong"},
        follow_redirects=True,
    )
    login("admin")

    response = client.get("/admin/security-events")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Dziennik bezpieczeństwa" in body
    assert "login_failed" in body
    assert "bad-login" in body


def test_last_active_admin_cannot_be_demoted(app, client, login, ids):
    login("admin")
    response = client.post(
        f"/admin/users/{ids['admin']}/edit",
        data={"role": "User", "is_active": "on", "password": ""},
        follow_redirects=True,
    )

    assert "Nie można odebrać uprawnień ostatniemu aktywnemu administratorowi." in response.get_data(as_text=True)
    with app.app_context():
        admin = User.query.filter_by(username="admin").one()
        assert admin.role == "Admin"
        assert SecurityEvent.query.filter_by(event_type="permission_change_rejected").count() == 1
