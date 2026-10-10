from datetime import UTC, datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
TICKET_STATUSES = ["New", "In Progress", "Resolved", "Closed"]
USER_ROLES = ["Admin", "Technician", "User"]


def utc_now_naive():
    """Return the current UTC time as a naive datetime for existing DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)

DEFAULT_CATEGORIES = [
    "Hardware",
    "Software",
    "Network",
    "Printer",
    "Access Management",
    "Email",
    "Other",
]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="User")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    comments = db.relationship("Comment", back_populates="author", lazy="dynamic")
    activity_logs = db.relationship("ActivityLog", back_populates="user", lazy="dynamic")
    security_events = db.relationship(
        "SecurityEvent",
        foreign_keys="SecurityEvent.user_id",
        back_populates="user",
        lazy="dynamic",
        passive_deletes=True,
    )
    security_target_events = db.relationship(
        "SecurityEvent",
        foreign_keys="SecurityEvent.target_user_id",
        back_populates="target_user",
        lazy="dynamic",
        passive_deletes=True,
    )
    created_tickets = db.relationship(
        "Ticket",
        foreign_keys="Ticket.user_id",
        back_populates="creator",
        lazy="dynamic",
    )
    assigned_tickets = db.relationship(
        "Ticket",
        foreign_keys="Ticket.assigned_to_id",
        back_populates="assigned_technician",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def is_admin(self):
        return self.role == "Admin"

    @property
    def is_technician(self):
        return self.role == "Technician"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    tickets = db.relationship("Ticket", back_populates="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.name}>"


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="New")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    comments = db.relationship("Comment", back_populates="ticket", lazy="dynamic")
    attachments = db.relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", back_populates="ticket", cascade="all, delete-orphan")
    creator = db.relationship("User", foreign_keys=[user_id], back_populates="created_tickets")
    category = db.relationship("Category", back_populates="tickets")
    assigned_technician = db.relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_tickets",
    )

    def __repr__(self):
        return f"<Ticket {self.title}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    ticket = db.relationship("Ticket", back_populates="activity_logs")
    user = db.relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.action} on Ticket {self.ticket_id}>"


class SecurityEvent(db.Model):
    __tablename__ = "security_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    success = db.Column(db.Boolean, nullable=False, default=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    username = db.Column(db.String(80), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive, index=True)

    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="security_events",
    )
    target_user = db.relationship(
        "User",
        foreign_keys=[target_user_id],
        back_populates="security_target_events",
    )

    def __repr__(self):
        return f"<SecurityEvent {self.event_type} success={self.success}>"


class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=False)
    size = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    path = db.Column(db.String(255), nullable=False)
    ticket = db.relationship("Ticket", back_populates="attachments")

    def __repr__(self):
        return f"<Attachment {self.original_name}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    ticket = db.relationship("Ticket", back_populates="comments")
    author = db.relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<Comment {self.id} on Ticket {self.ticket_id}>"
