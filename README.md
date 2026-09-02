# HelpDesk-Master

Aplikacja HelpDesk napisana w Python Flask z wykorzystaniem PostgreSQL. Repozytorium zawiera działający zestaw testów oraz przygotowane środowisko kontenerowe Docker Compose.

## Technologie

- Python 3.13
- Flask
- Flask-SQLAlchemy
- PostgreSQL
- Bootstrap 5
- pytest
- Docker / Docker Compose
- Gunicorn

## Uruchomienie testów lokalnie

1. Utwórz środowisko wirtualne:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Zainstaluj zależności:

```powershell
python -m pip install -r requirements.txt
```

3. Uruchom testy:

```powershell
python -m pytest -q
```

Testy korzystają z odizolowanej bazy SQLite oraz tymczasowego katalogu na załączniki, dlatego nie wymagają lokalnego PostgreSQL.

Testy podzielono na:

- `tests/test_auth.py` - logowanie, sesja i kontrola dostępu,
- `tests/test_tickets.py` - zgłoszenia, komentarze, statusy, przypisania i załączniki,
- `tests/test_admin.py` - funkcje administratora,
- `tests/conftest.py` - wspólna konfiguracja środowiska testowego.

## Uruchomienie lokalne bez Dockera

Stan bazowy aplikacji nadal można uruchomić bezpośrednio.

1. Skonfiguruj PostgreSQL. Domyślna konfiguracja lokalna wynikająca ze stanu bazowego to:

- baza: `helpdesk_db`,
- użytkownik: `postgres`,
- hasło: `1234`.

2. Opcjonalnie ustaw `DATABASE_URL` oraz `SECRET_KEY`.

3. Uruchom aplikację:

```powershell
python app.py
```

Aplikacja będzie dostępna pod `http://127.0.0.1:5000/`.

## Uruchomienie przez Docker Compose

### 1. Przygotowanie konfiguracji

Skopiuj plik przykładowy:

```powershell
Copy-Item .env.example .env
```

Następnie zmień w `.env` co najmniej:

- `POSTGRES_PASSWORD`,
- `SECRET_KEY`,
- `DEFAULT_ADMIN_PASSWORD`.

Plik `.env` jest ignorowany przez Git i nie powinien być commitowany.

### 2. Budowa i uruchomienie

```powershell
docker compose up --build -d
```

Po poprawnym uruchomieniu aplikacja będzie dostępna pod:

```text
http://localhost:5000/
```

Port można zmienić przez `APP_PORT` w `.env`.

### 3. Sprawdzenie stanu usług

```powershell
docker compose ps
```

Oba serwisy powinny osiągnąć stan `healthy`.

Logi aplikacji:

```powershell
docker compose logs -f app
```

Logi PostgreSQL:

```powershell
docker compose logs -f db
```

### 4. Zatrzymanie

```powershell
docker compose down
```

To polecenie usuwa kontenery i sieć, ale pozostawia dane w nazwanych wolumenach.

Aby świadomie usunąć także bazę i załączniki:

```powershell
docker compose down -v
```

## Architektura kontenerowa

Docker Compose uruchamia dwa serwisy:

- `app` - aplikacja Flask uruchomiona przez Gunicorn na porcie 5000,
- `db` - PostgreSQL 16.

Dane są przechowywane w dwóch nazwanych wolumenach:

- `postgres_data` - dane PostgreSQL,
- `attachments_data` - załączniki z HelpDesku.

Aplikacja czeka na dostępność bazy, wykonuje inicjalizację schematu i danych startowych, a następnie uruchamia serwer Gunicorn. Healthcheck sprawdza dostępność endpointu `/login`.

## Zmienne środowiskowe kontenera

Najważniejsze parametry:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - połączenie z PostgreSQL,
- `SECRET_KEY` - klucz sesji Flask,
- `DEFAULT_ADMIN_USERNAME`, `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD` - dane administratora tworzonego przy pierwszej inicjalizacji,
- `UPLOAD_FOLDER` - katalog załączników,
- `APP_PORT` - port wystawiany na komputerze hosta.

Aplikacja nadal obsługuje zmienną `DATABASE_URL`, co jest wykorzystywane między innymi przez środowisko testowe.

## Dokumentacja pracy magisterskiej

- `docs/BASELINE.md` - stan przed konteneryzacją i referencyjny proces manualny,
- `docs/CONTAINERIZATION.md` - decyzje projektowe i procedura konteneryzacji.
