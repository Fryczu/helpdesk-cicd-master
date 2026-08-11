from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
TICKET_STATUSES = ["New", "In Progress", "Resolved", "Closed"]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    comments = db.relationship("Comment", back_populates="author", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.username}>"


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="New")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    comments = db.relationship("Comment", back_populates="ticket", lazy="dynamic")

    def __repr__(self):
        return f"<Ticket {self.title}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ticket = db.relationship("Ticket", back_populates="comments")
    author = db.relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<Comment {self.id} on Ticket {self.ticket_id}>"
