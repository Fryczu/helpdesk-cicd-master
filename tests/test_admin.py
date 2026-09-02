from models import User


def test_admin_can_create_user(app, client, login):
    login("admin")

    response = client.post(
        "/admin/users/new",
        data={
            "username": "newtech",
            "email": "newtech@example.com",
            "password": "secret123",
            "role": "Technician",
            "is_active": "on",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Użytkownik został utworzony." in response.get_data(as_text=True)

    with app.app_context():
        user = User.query.filter_by(username="newtech").one()
        assert user.role == "Technician"
        assert user.is_active is True
