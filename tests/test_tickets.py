from io import BytesIO
from pathlib import Path

from models import ActivityLog, Attachment, Comment, Ticket, db


def test_user_can_create_ticket_with_valid_category(app, client, login, ids):
    login()

    response = client.post(
        "/tickets/create",
        data={
            "title": "Nowe zgłoszenie",
            "description": "Opis testowy",
            "category_id": str(ids["software"]),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Zgłoszenie zostało utworzone." in body
    assert "Nowe zgłoszenie" in body

    with app.app_context():
        ticket = Ticket.query.filter_by(title="Nowe zgłoszenie").one()
        assert ticket.user_id == ids["test"]
        assert ticket.category_id == ids["software"]
        assert ticket.status == "New"
        assert ActivityLog.query.filter_by(
            ticket_id=ticket.id,
            action="ticket_created",
        ).count() == 1


def test_ticket_creation_requires_category(app, client, login):
    login()

    response = client.post(
        "/tickets/create",
        data={"title": "Brak kategorii", "description": "Opis"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Wybierz poprawną kategorię zgłoszenia." in response.get_data(as_text=True)

    with app.app_context():
        assert Ticket.query.filter_by(title="Brak kategorii").count() == 0


def test_user_sees_only_own_tickets(app, client, login, ids):
    with app.app_context():
        own = Ticket(
            title="Moje zgłoszenie",
            description="Opis",
            user_id=ids["test"],
            category_id=ids["hardware"],
        )
        other = Ticket(
            title="Cudze zgłoszenie",
            description="Opis",
            user_id=ids["other"],
            category_id=ids["hardware"],
        )
        db.session.add_all([own, other])
        db.session.commit()

    login()
    response = client.get("/tickets")
    body = response.get_data(as_text=True)

    assert "Moje zgłoszenie" in body
    assert "Cudze zgłoszenie" not in body


def test_user_cannot_open_another_users_ticket(app, client, login, ids):
    with app.app_context():
        ticket = Ticket(
            title="Prywatne zgłoszenie",
            description="Opis",
            user_id=ids["other"],
            category_id=ids["hardware"],
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    login()
    response = client.get(f"/tickets/{ticket_id}", follow_redirects=True)

    assert response.status_code == 200
    assert "Nie masz uprawnień do przeglądania tego zgłoszenia." in response.get_data(as_text=True)


def test_ticket_owner_can_add_comment(app, client, login, ids):
    with app.app_context():
        ticket = Ticket(
            title="Komentowane zgłoszenie",
            description="Opis",
            user_id=ids["test"],
            category_id=ids["hardware"],
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    login()
    response = client.post(
        f"/tickets/{ticket_id}",
        data={"comment": "Komentarz testowy"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Komentarz został dodany." in response.get_data(as_text=True)

    with app.app_context():
        assert Comment.query.filter_by(ticket_id=ticket_id, comment="Komentarz testowy").count() == 1
        assert ActivityLog.query.filter_by(ticket_id=ticket_id, action="comment_added").count() == 1


def test_regular_user_cannot_change_ticket_status(app, client, login, ids):
    with app.app_context():
        ticket = Ticket(
            title="Status użytkownika",
            description="Opis",
            user_id=ids["test"],
            category_id=ids["hardware"],
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    login()
    response = client.post(
        f"/tickets/{ticket_id}",
        data={"action": "status", "status": "Resolved"},
        follow_redirects=True,
    )

    assert "Tylko technik lub administrator może zmieniać status zgłoszenia." in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Ticket, ticket_id).status == "New"


def test_technician_can_change_ticket_status(app, client, login, ids):
    with app.app_context():
        ticket = Ticket(
            title="Status technika",
            description="Opis",
            user_id=ids["test"],
            category_id=ids["hardware"],
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    login("tech")
    response = client.post(
        f"/tickets/{ticket_id}",
        data={"action": "status", "status": "Resolved"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Status zgłoszenia został zmieniony." in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Ticket, ticket_id).status == "Resolved"
        assert ActivityLog.query.filter_by(ticket_id=ticket_id, action="status_changed").count() == 1


def test_technician_can_assign_ticket_to_technician(app, client, login, ids):
    with app.app_context():
        ticket = Ticket(
            title="Przypisanie",
            description="Opis",
            user_id=ids["test"],
            category_id=ids["hardware"],
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    login("tech")
    response = client.post(
        f"/tickets/{ticket_id}",
        data={"action": "assign", "assigned_to_id": str(ids["tech"])},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Zgłoszenie zostało przypisane do technika." in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Ticket, ticket_id).assigned_to_id == ids["tech"]
        assert ActivityLog.query.filter_by(ticket_id=ticket_id, action="ticket_assigned").count() == 1


def test_attachment_is_saved_outside_database_and_metadata_is_recorded(app, client, login, ids):
    login()

    response = client.post(
        "/tickets/create",
        data={
            "title": "Z załącznikiem",
            "description": "Opis",
            "category_id": str(ids["software"]),
            "attachments": (BytesIO(b"test file content"), "zalacznik.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Zgłoszenie zostało utworzone." in response.get_data(as_text=True)

    with app.app_context():
        ticket = Ticket.query.filter_by(title="Z załącznikiem").one()
        attachment = Attachment.query.filter_by(ticket_id=ticket.id).one()
        assert attachment.original_name == "zalacznik.txt"
        assert attachment.size == len(b"test file content")
        assert Path(attachment.path).is_file()
        assert Path(attachment.path).read_bytes() == b"test file content"

def test_technician_sees_requester_identity_in_ticket_details(app, client, login, ids):
    with app.app_context():
        ticket = Ticket(
            title="Zgłoszenie z danymi zgłaszającego",
            description="Opis",
            user_id=ids["test"],
            category_id=ids["hardware"],
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    login("tech")
    response = client.get(f"/tickets/{ticket_id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Zgłaszający:" in body
    assert "test" in body
    assert "test@example.com" in body


def test_staff_ticket_list_shows_requester_username(app, client, login, ids):
    with app.app_context():
        ticket = Ticket(
            title="Zgłoszenie widoczne na liście",
            description="Opis",
            user_id=ids["test"],
            category_id=ids["software"],
        )
        db.session.add(ticket)
        db.session.commit()

    login("admin")
    response = client.get("/tickets")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Zgłaszający" in body
    assert "Zgłoszenie widoczne na liście" in body
    assert "test" in body

