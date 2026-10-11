import os
import time

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import (
    app,
    apply_database_migrations,
    create_default_admin,
    create_default_categories,
    db,
)


def wait_for_database(max_attempts=30, delay_seconds=2):
    """Wait until the configured database accepts connections."""
    for attempt in range(1, max_attempts + 1):
        try:
            with app.app_context():
                db.session.execute(text("SELECT 1"))
                db.session.remove()
            print("Database connection established.")
            return
        except OperationalError as exc:
            with app.app_context():
                db.session.rollback()
                db.session.remove()
            if attempt == max_attempts:
                raise RuntimeError("Database did not become available in time.") from exc
            print(f"Database unavailable (attempt {attempt}/{max_attempts}); retrying...")
            time.sleep(delay_seconds)


def initialize_database():
    apply_database_migrations()
    create_default_categories()
    create_default_admin()
    print("Database migrations and initial data are ready.")


if __name__ == "__main__":
    attempts = int(os.getenv("DB_WAIT_ATTEMPTS", "30"))
    delay = float(os.getenv("DB_WAIT_DELAY_SECONDS", "2"))
    wait_for_database(max_attempts=attempts, delay_seconds=delay)
    initialize_database()
