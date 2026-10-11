import os

import pytest
from werkzeug.security import generate_password_hash

# Flask-SQLAlchemy reads the database URL when db.init_app(app) is called in app.py.
# The test database therefore has to be selected before importing the application.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

from app import app as flask_app
from app import db
from models import Category, User


@pytest.fixture()
def app(tmp_path):
    upload_dir = tmp_path / "uploads" / "attachments"
    upload_dir.mkdir(parents=True, exist_ok=True)

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        UPLOAD_FOLDER=str(upload_dir),
    )

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        users = [
            User(
                username="test",
                email="test@example.com",
                password_hash=generate_password_hash("test"),
                role="User",
                is_active=True,
            ),
            User(
                username="other",
                email="other@example.com",
                password_hash=generate_password_hash("other"),
                role="User",
                is_active=True,
            ),
            User(
                username="tech",
                email="tech@example.com",
                password_hash=generate_password_hash("tech"),
                role="Technician",
                is_active=True,
            ),
            User(
                username="admin",
                email="admin@example.com",
                password_hash=generate_password_hash("admin"),
                role="Admin",
                is_active=True,
            ),
            User(
                username="inactive",
                email="inactive@example.com",
                password_hash=generate_password_hash("inactive"),
                role="User",
                is_active=False,
            ),
        ]
        db.session.add_all(users)
        db.session.add_all([Category(name="Hardware"), Category(name="Software")])
        db.session.commit()

        yield flask_app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login(client):
    def _login(username="test", password=None, follow_redirects=True):
        if password is None:
            password = username
        return client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=follow_redirects,
        )

    return _login


@pytest.fixture()
def ids(app):
    with app.app_context():
        return {
            "test": User.query.filter_by(username="test").one().id,
            "other": User.query.filter_by(username="other").one().id,
            "tech": User.query.filter_by(username="tech").one().id,
            "admin": User.query.filter_by(username="admin").one().id,
            "hardware": Category.query.filter_by(name="Hardware").one().id,
            "software": Category.query.filter_by(name="Software").one().id,
        }
