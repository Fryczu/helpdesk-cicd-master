import os
import uuid
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from models import (
    DEFAULT_CATEGORIES,
    TICKET_STATUSES,
    USER_ROLES,
    ActivityLog,
    Attachment,
    Category,
    Comment,
    Ticket,
    User,
    db,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1234@localhost:5432/helpdesk_db",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "attachments")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Zaloguj się, aby kontynuować.", "warning")
            return redirect(url_for("login"))
        if not user.is_active:
            session.pop("user_id", None)
            flash("Konto użytkownika zostało dezaktywowane.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user = current_user()
            if user is None:
                flash("Zaloguj się, aby kontynuować.", "warning")
                return redirect(url_for("login"))
            if not user.is_active:
                session.pop("user_id", None)
                flash("Konto użytkownika zostało dezaktywowane.", "warning")
                return redirect(url_for("login"))
            if allowed_roles and user.role not in allowed_roles:
                flash("Nie masz uprawnień do tej części systemu.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def can_access_ticket(user, ticket):
    if user is None:
        return False
    if user.role in {"Admin", "Technician"}:
        return True
    return user.role == "User" and ticket.user_id == user.id


def save_ticket_attachments(ticket_id, uploaded_files):
    saved_files = []
    for uploaded_file in uploaded_files:
        if not uploaded_file or not uploaded_file.filename:
            continue

        filename = secure_filename(uploaded_file.filename)
        unique_name = f"{ticket_id}_{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        uploaded_file.save(file_path)

        attachment = Attachment(
            ticket_id=ticket_id,
            filename=unique_name,
            original_name=filename,
            content_type=uploaded_file.mimetype or "application/octet-stream",
            size=os.path.getsize(file_path),
            path=file_path,
        )
        db.session.add(attachment)
        saved_files.append(attachment)

    if saved_files:
        db.session.commit()

    return saved_files


def log_activity(ticket_id, user_id, action, message):
    activity = ActivityLog(ticket_id=ticket_id, user_id=user_id, action=action, message=message)
    db.session.add(activity)
    db.session.commit()


@app.route("/")
def index():
    user = current_user()
    if user:
        return redirect(url_for("tickets" if user.role == "User" else "dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    user = current_user()
    if user:
        return redirect(url_for("tickets" if user.role == "User" else "dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()
        if user and user.is_active and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash("Zalogowano pomyślnie.", "success")
            return redirect(url_for("tickets" if user.role == "User" else "dashboard"))

        if user and not user.is_active:
            flash("Konto użytkownika zostało dezaktywowane.", "warning")
        else:
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
    user = current_user()
    if user.role == "User":
        return redirect(url_for("tickets"))

    ticket_query = Ticket.query
    statuses = {
        status: ticket_query.filter_by(status=status).count() for status in TICKET_STATUSES
    }
    recent_tickets = ticket_query.order_by(Ticket.created_at.desc()).limit(5).all()
    recent_activity = (
        ActivityLog.query
        .join(User)
        .filter(User.role != "Admin")
        .order_by(ActivityLog.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "dashboard.html",
        statuses=statuses,
        recent_tickets=recent_tickets,
        recent_activity=recent_activity,
    )


@app.route("/tickets")
@login_required
def tickets():
    user = current_user()
    filter_name = request.args.get("filter", "all")

    query = Ticket.query
    if user.role == "User":
        query = query.filter_by(user_id=user.id)

    if filter_name == "unassigned":
        query = query.filter(Ticket.assigned_to_id.is_(None))
    elif filter_name == "assigned":
        query = query.filter(Ticket.assigned_to_id.isnot(None))
    elif filter_name == "rejected":
        query = query.filter(Ticket.status == "Closed")
    elif filter_name == "completed":
        query = query.filter(Ticket.status == "Resolved")

    ticket_list = query.order_by(Ticket.created_at.desc()).all()
    return render_template("tickets.html", tickets=ticket_list, active_filter=filter_name)


@app.route("/tickets/create", methods=["GET", "POST"])
@login_required
def create_ticket():
    categories = Category.query.order_by(Category.name.asc()).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id", type=int)
        uploaded_files = request.files.getlist("attachments")

        if not title or not description:
            flash("Tytuł i opis są wymagane.", "danger")
            return render_template(
                "create_ticket.html",
                title=title,
                description=description,
                categories=categories,
            )

        if category_id is None or not Category.query.get(category_id):
            flash("Wybierz poprawną kategorię zgłoszenia.", "danger")
            return render_template(
                "create_ticket.html",
                title=title,
                description=description,
                categories=categories,
            )

        ticket = Ticket(
            title=title,
            description=description,
            status="New",
            user_id=current_user().id,
            category_id=category_id,
        )
        db.session.add(ticket)
        db.session.flush()
        save_ticket_attachments(ticket.id, uploaded_files)
        log_activity(
            ticket.id,
            current_user().id,
            "ticket_created",
            f"Utworzono zgłoszenie {ticket.title}.",
        )

        flash("Zgłoszenie zostało utworzone.", "success")
        return redirect(url_for("tickets"))

    return render_template("create_ticket.html", categories=categories)


@app.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
@login_required
def ticket_details(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    user = current_user()

    if not can_access_ticket(user, ticket):
        flash("Nie masz uprawnień do przeglądania tego zgłoszenia.", "danger")
        return redirect(url_for("tickets"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "status":
            if user.role not in {"Technician", "Admin"}:
                flash("Tylko technik lub administrator może zmieniać status zgłoszenia.", "danger")
            else:
                status = request.form.get("status")
                if status in TICKET_STATUSES:
                    old_status = ticket.status
                    ticket.status = status
                    db.session.commit()
                    log_activity(
                        ticket.id,
                        user.id,
                        "status_changed",
                        f"Zmienił status z {old_status} na {status}.",
                    )
                    flash("Status zgłoszenia został zmieniony.", "success")
                else:
                    flash("Nieprawidłowy status.", "danger")

        elif action == "assign":
            if user.role not in {"Technician", "Admin"}:
                flash("Nie masz uprawnień do przypisywania zgłoszeń.", "danger")
            else:
                assigned_id = request.form.get("assigned_to_id")
                if assigned_id:
                    technician = User.query.filter_by(id=assigned_id, role="Technician").first()
                    if technician is None:
                        flash("Wybrany użytkownik nie jest technikiem.", "danger")
                    else:
                        ticket.assigned_to_id = technician.id
                        db.session.commit()
                        log_activity(
                            ticket.id,
                            user.id,
                            "ticket_assigned",
                            f"Przypisał zgłoszenie do technika {technician.username}.",
                        )
                        flash("Zgłoszenie zostało przypisane do technika.", "success")
                else:
                    ticket.assigned_to_id = None
                    db.session.commit()
                    log_activity(
                        ticket.id,
                        user.id,
                        "ticket_unassigned",
                        "Usunął przypisanie technika do zgłoszenia.",
                    )
                    flash("Przypisanie technika zostało usunięte.", "success")

        elif action == "attachment":
            if user.role not in {"Technician", "Admin"} and not (user.role == "User" and ticket.user_id == user.id):
                flash("Nie masz uprawnień do dodawania załączników do tego zgłoszenia.", "danger")
            else:
                uploaded_files = request.files.getlist("attachments")
                if not uploaded_files or all(not file or not file.filename for file in uploaded_files):
                    flash("Wybierz plik do załączenia.", "danger")
                else:
                    save_ticket_attachments(ticket.id, uploaded_files)
                    log_activity(
                        ticket.id,
                        user.id,
                        "attachment_added",
                        f"Dodał załącznik do zgłoszenia.",
                    )
                    flash("Załączniki zostały dodane.", "success")

        else:
            can_comment = user.role in {"Technician", "Admin"} or (
                user.role == "User" and ticket.user_id == user.id
            )
            if not can_comment:
                flash("Nie masz uprawnień do dodawania komentarza do tego zgłoszenia.", "danger")
            else:
                comment_text = request.form.get("comment", "").strip()
                if not comment_text:
                    flash("Komentarz nie może być pusty.", "danger")
                else:
                    comment = Comment(
                        ticket_id=ticket.id,
                        user_id=user.id,
                        comment=comment_text,
                    )
                    db.session.add(comment)
                    db.session.commit()
                    log_activity(
                        ticket.id,
                        user.id,
                        "comment_added",
                        "Dodał komentarz do zgłoszenia.",
                    )
                    flash("Komentarz został dodany.", "success")

        return redirect(url_for("ticket_details", ticket_id=ticket.id))

    comments = Comment.query.filter_by(ticket_id=ticket.id).order_by(Comment.created_at.asc()).all()
    attachments = Attachment.query.filter_by(ticket_id=ticket.id).order_by(Attachment.created_at.asc()).all()
    technicians = User.query.filter_by(role="Technician").order_by(User.username.asc()).all()
    can_add_attachment = user.role in {"Technician", "Admin"} or (user.role == "User" and ticket.user_id == user.id)
    return render_template(
        "ticket_details.html",
        ticket=ticket,
        comments=comments,
        attachments=attachments,
        statuses=TICKET_STATUSES,
        technicians=technicians,
        can_change_status=user.role in {"Technician", "Admin"},
        can_assign=user.role in {"Technician", "Admin"},
        can_add_attachment=can_add_attachment,
    )


@app.route("/attachments/<int:attachment_id>")
@login_required
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    ticket = attachment.ticket
    user = current_user()

    if not can_access_ticket(user, ticket):
        flash("Nie masz uprawnień do pobrania tego załącznika.", "danger")
        return redirect(url_for("tickets"))

    return send_from_directory(app.config["UPLOAD_FOLDER"], attachment.filename, as_attachment=True, download_name=attachment.original_name)


@app.route("/admin")
@login_required
@role_required("Admin")
def admin_dashboard():
    return redirect(url_for("admin_users"))


@app.route("/admin/users")
@login_required
@role_required("Admin")
def admin_users():
    users = User.query.order_by(User.username.asc()).all()
    return render_template("admin_users.html", users=users, roles=USER_ROLES)


@app.route("/admin/users/new", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def admin_create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "User")
        is_active = request.form.get("is_active") == "on"

        if not username or not email or not password:
            flash("Nazwa użytkownika, email i hasło są wymagane.", "danger")
            return render_template("admin_user_form.html", user=None, roles=USER_ROLES)

        if role not in USER_ROLES:
            flash("Nieprawidłowa rola użytkownika.", "danger")
            return render_template("admin_user_form.html", user=None, roles=USER_ROLES)

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Użytkownik o tej nazwie lub adresie email już istnieje.", "danger")
            return render_template("admin_user_form.html", user=None, roles=USER_ROLES)

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_active=is_active,
        )
        db.session.add(user)
        db.session.commit()
        flash("Użytkownik został utworzony.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_form.html", user=None, roles=USER_ROLES)


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        role = request.form.get("role", user.role)
        is_active = request.form.get("is_active") == "on"
        password = request.form.get("password", "").strip()

        if role not in USER_ROLES:
            flash("Nieprawidłowa rola użytkownika.", "danger")
            return render_template("admin_user_form.html", user=user, roles=USER_ROLES)

        user.role = role
        user.is_active = is_active
        if password:
            user.password_hash = generate_password_hash(password)
        db.session.commit()
        flash("Dane użytkownika zostały zaktualizowane.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_form.html", user=user, roles=USER_ROLES)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("Admin")
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user().id:
        flash("Nie można usunąć własnego konta z poziomu panelu administratora.", "danger")
        return redirect(url_for("admin_users"))

    admin_count = User.query.filter_by(role="Admin").count()
    if user.role == "Admin" and admin_count <= 1:
        flash("Nie można usunąć ostatniego administratora.", "danger")
        return redirect(url_for("admin_users"))

    replacement_admin = User.query.filter(User.id != user.id, User.role == "Admin").first()
    replacement_user = replacement_admin or current_user()

    for ticket in list(user.created_tickets):
        ticket.user_id = replacement_user.id

    for comment in list(user.comments):
        comment.user_id = replacement_user.id

    for ticket in list(user.assigned_tickets):
        ticket.assigned_to_id = None

    db.session.delete(user)
    db.session.commit()
    flash("Użytkownik został usunięty.", "success")
    return redirect(url_for("admin_users"))


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def create_default_categories():
    with app.app_context():
        for category_name in DEFAULT_CATEGORIES:
            if not Category.query.filter_by(name=category_name).first():
                db.session.add(Category(name=category_name))
        db.session.commit()


def create_default_admin():
    with app.app_context():
        if not User.query.filter_by(username="admin").first():
            default_user = User(
                username="admin",
                email="admin@example.com",
                password_hash=generate_password_hash("admin123"),
                role="Admin",
                is_active=True,
            )
            db.session.add(default_user)
            db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_default_categories()
        create_default_admin()
    app.run(debug=True)
