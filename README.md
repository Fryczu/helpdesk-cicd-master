# HelpDesk-Master

Prosta aplikacja HelpDesk napisana w Python Flask z wykorzystaniem PostgreSQL.

## Technologie

- Python 3.13
- Flask
- Flask-SQLAlchemy
- PostgreSQL
- Bootstrap 5

## Instalacja

1. Stwórz środowisko wirtualne:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Zainstaluj zależności:

```powershell
python -m pip install -r requirements.txt
```

3. Skonfiguruj bazę danych PostgreSQL i uruchom:

- Nazwa bazy: `helpdesk_db`
- Użytkownik: `postgres`
- Hasło: `1234`

4. Uruchom aplikację:

```powershell
python app.py
```

Aplikacja jest dostępna pod adresem `http://127.0.0.1:5000/`.

## Dane logowania

- Nazwa użytkownika: `admin`
- Hasło: `admin123`

## Testy

Uruchom testy:

```powershell
python -m pytest
```
