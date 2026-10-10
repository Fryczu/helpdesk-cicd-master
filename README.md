# HelpDesk-Master

Aplikacja HelpDesk napisana w Python Flask z wykorzystaniem PostgreSQL. Repozytorium zawiera działający zestaw testów oraz przygotowane środowisko kontenerowe Docker Compose.

## Technologie

- Python 3.13
- Flask
- Flask-SQLAlchemy
- Flask-Migrate / Alembic
- PostgreSQL
- Bootstrap 5
- pytest
- Docker / Docker Compose
- Gunicorn

## Rozszerzenia bezpieczeństwa i bazy danych

Projekt rejestruje zdarzenia istotne z punktu widzenia bezpieczeństwa. Zapisywane są m.in.:

- udane i nieudane logowania,
- wylogowania,
- próby wejścia do zasobów bez wymaganej roli,
- tworzenie i usuwanie kont,
- zmiany ról oraz aktywności kont,
- reset hasła wykonywany przez administratora.

Administrator może przeglądać i filtrować wpisy w widoku `Administracja -> Bezpieczeństwo`. Rejestr nie zapisuje haseł ani wartości sekretów.

Schemat bazy danych jest wersjonowany przez Flask-Migrate/Alembic. Przy starcie aplikacji wykonywane jest `upgrade` do najnowszej rewizji. Istniejąca baza utworzona wcześniej przez `db.create_all()` jest automatycznie oznaczana jako rewizja bazowa i następnie otrzymuje tylko brakujące migracje. Dzięki temu aktualizacja nie wymaga kasowania wolumenu PostgreSQL.

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

Aktualny zestaw obejmuje 25 testów. Testy podzielono na:

- `tests/test_auth.py` - logowanie, sesja i kontrola dostępu,
- `tests/test_tickets.py` - zgłoszenia, komentarze, statusy, przypisania i załączniki,
- `tests/test_admin.py` - funkcje administratora,
- `tests/test_security.py` - rejestrowanie zdarzeń bezpieczeństwa i ochrona ostatniego administratora,
- `tests/conftest.py` - wspólna konfiguracja środowiska testowego.

## Uruchomienie lokalne bez Dockera

Stan bazowy aplikacji nadal można uruchomić bezpośrednio.

1. Skonfiguruj PostgreSQL. Domyślna konfiguracja lokalna wynikająca ze stanu bazowego to:

- baza: `helpdesk_db`,
- użytkownik: `postgres`,
- hasło: `1234`.

2. Opcjonalnie ustaw `DATABASE_URL` oraz `SECRET_KEY`.

3. Zainstaluj zależności zaktualizowanego projektu. Flask-Migrate jest wymagany do obsługi migracji.

4. Uruchom aplikację:

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

Aplikacja czeka na dostępność bazy, automatycznie stosuje brakujące migracje Alembic, przygotowuje dane startowe, a następnie uruchamia serwer Gunicorn. Healthcheck sprawdza dostępność endpointu `/login`.

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

## Migracje bazy danych

Migracje znajdują się w katalogu `migrations/`. Aktualnie projekt zawiera:

- `0001_initial_schema` - bazowy schemat istniejącej aplikacji,
- `0002_security_events` - tabela dziennika zdarzeń bezpieczeństwa.

Stan migracji można sprawdzić poleceniem:

```powershell
flask --app app db current
```

Ręczne zastosowanie brakujących migracji:

```powershell
flask --app app db upgrade
```

Po kolejnej zmianie modeli nową rewizję można przygotować poleceniem:

```powershell
flask --app app db migrate -m "opis zmiany"
```

Wygenerowaną migrację należy przejrzeć przed zatwierdzeniem w repozytorium. Przy zwykłym starcie kontenera `init_db.py` wykonuje upgrade automatycznie, dlatego ten sam mechanizm może zostać później użyty podczas wdrożenia przez CI/CD.

## Dziennik bezpieczeństwa

Dziennik jest dostępny wyłącznie dla roli `Admin` pod adresem:

```text
/admin/security-events
```

Widok umożliwia filtrowanie po typie zdarzenia, wyniku oraz nazwie użytkownika. Każdy wpis może przechowywać typ zdarzenia, wynik, konto wykonujące operację, konto będące celem operacji, adres IP, user-agent, opis i czas UTC.


## Endpointy wdrożeniowe

Aplikacja udostępnia dwa publiczne endpointy techniczne używane do automatycznej weryfikacji wdrożenia:

- `GET /health` - zwraca HTTP 200 i `{"status":"ok","database":"ok"}`, jeśli aplikacja działa i ma połączenie z bazą danych. Docker Compose używa tego endpointu jako healthchecku kontenera aplikacji.
- `GET /version` - zwraca nazwę aplikacji oraz metadane `APP_VERSION` i `GIT_COMMIT` zapisane w obrazie podczas budowania. Pozwala potwierdzić, że wdrożona została oczekiwana wersja.

Lokalnie można ustawić `APP_VERSION` i `GIT_COMMIT` w `.env`. W docelowym CI/CD wartości będą przekazywane jako argumenty budowania obrazu.
