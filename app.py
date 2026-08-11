from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from models import db, User, Ticket, Comment, TICKET_STATUSES

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1234@localhost:5432/helpdesk_db",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret")

db.init_app(app)


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


def login_required(view):
    def wrapped_view(*args, **kwargs):
        if current_user() is None:
            flash("Zaloguj się, aby kontynuować.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    wrapped_view.__name__ = view.__name__
    return wrapped_view


@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash("Zalogowano pomyślnie.", "success")
            return redirect(url_for("dashboard"))

        flash("Niepoprawna nazwa użytkownika lub hasło.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Wylogowano.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    statuses = {status: Ticket.query.filter_by(status=status).count() for status in TICKET_STATUSES}
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(5).all()
    return render_template("dashboard.html", statuses=statuses, recent_tickets=recent_tickets)


@app.route("/tickets")
@login_required
def tickets():
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template("tickets.html", tickets=tickets)


@app.route("/tickets/create", methods=["GET", "POST"])
@login_required
def create_ticket():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not description:
            flash("Tytuł i opis są wymagane.", "danger")
            return render_template("create_ticket.html", title=title, description=description)

        ticket = Ticket(title=title, description=description, status="New")
        db.session.add(ticket)
        db.session.commit()

        flash("Zgłoszenie zostało utworzone.", "success")
        return redirect(url_for("tickets"))

    return render_template("create_ticket.html")


@app.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
@login_required
def ticket_details(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "status":
            status = request.form.get("status")
            if status in TICKET_STATUSES:
                ticket.status = status
                db.session.commit()
                flash("Status zgłoszenia został zmieniony.", "success")
            else:
                flash("Nieprawidłowy status.", "danger")
        else:
            comment_text = request.form.get("comment", "").strip()
            if not comment_text:
                flash("Komentarz nie może być pusty.", "danger")
            else:
                comment = Comment(
                    ticket_id=ticket.id,
                    user_id=current_user().id,
                    comment=comment_text,
                )
                db.session.add(comment)
                db.session.commit()
                flash("Komentarz został dodany.", "success")

        return redirect(url_for("ticket_details", ticket_id=ticket.id))

    comments = Comment.query.filter_by(ticket_id=ticket.id).order_by(Comment.created_at.asc()).all()
    return render_template(
        "ticket_details.html",
        ticket=ticket,
        comments=comments,
        statuses=TICKET_STATUSES,
    )


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def create_default_admin():
    with app.app_context():
        if User.query.count() == 0:
            default_user = User(
                username="admin",
                email="admin@example.com",
                password_hash=generate_password_hash("admin123"),
            )
            db.session.add(default_user)
            db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_default_admin()
    app.run(debug=True)
