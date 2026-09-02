# Konteneryzacja aplikacji HelpDesk

Data realizacji: 2026-08-25

Dokument opisuje pierwszy etap części implementacyjnej pracy: przygotowanie powtarzalnego środowiska uruchomieniowego aplikacji HelpDesk z wykorzystaniem Docker i Docker Compose.

## 1. Cel

Celem konteneryzacji jest ograniczenie zależności procesu uruchomienia od konfiguracji komputera operatora. W stanie bazowym aplikacja wymagała ręcznego przygotowania Pythona, zależności oraz lokalnego PostgreSQL. Po konteneryzacji środowisko aplikacji i bazy jest opisane w plikach przechowywanych razem z kodem.

## 2. Elementy dodane do projektu

- `Dockerfile` - definicja obrazu aplikacji,
- `.dockerignore` - ograniczenie kontekstu budowania obrazu,
- `docker-compose.yml` - definicja aplikacji i PostgreSQL,
- `.env.example` - wzorzec konfiguracji środowiskowej,
- `docker-entrypoint.sh` - inicjalizacja bazy przed uruchomieniem serwera,
- `init_db.py` - oczekiwanie na bazę oraz przygotowanie schematu i danych startowych,
- `gunicorn` - serwer WSGI wykorzystywany wewnątrz kontenera.

## 3. Obraz aplikacji

Obraz bazuje na `python:3.13.5-slim`, zgodnie z wersją Pythona przyjętą w projekcie. Zależności instalowane są z `requirements.txt`. Aplikacja działa jako użytkownik nieuprzywilejowany `appuser`, a nie jako `root`.

Kontener nie uruchamia wbudowanego serwera deweloperskiego Flask. Proces docelowy jest uruchamiany przez Gunicorn:

```text
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 30 app:app
```

## 4. PostgreSQL

Baza została wydzielona do osobnego serwisu `db` korzystającego z obrazu `postgres:16-alpine`.

Parametry bazy są przekazywane z `.env`. Aplikacja łączy się z bazą po nazwie usługi `db`, a nie przez `localhost`, ponieważ oba kontenery komunikują się w sieci tworzonej przez Docker Compose.

Serwis PostgreSQL posiada healthcheck oparty o `pg_isready`. Aplikacja jest uruchamiana dopiero po osiągnięciu przez bazę stanu `healthy`.

## 5. Inicjalizacja bazy

W stanie bazowym tworzenie tabel i danych startowych odbywało się wyłącznie w bloku `if __name__ == "__main__"` w `app.py`. Mechanizm ten nie zostałby wykonany przy starcie aplikacji przez Gunicorn.

Z tego powodu przygotowano `init_db.py`. Skrypt:

1. oczekuje na dostępność bazy,
2. sprawdza połączenie zapytaniem `SELECT 1`,
3. wykonuje `db.create_all()`,
4. tworzy brakujące kategorie,
5. tworzy konto administratora, jeżeli jeszcze nie istnieje.

Skrypt wykonywany jest przez `docker-entrypoint.sh` przed uruchomieniem Gunicorn.

## 6. Konfiguracja i sekrety

Plik `docker-compose.yml` nie zawiera docelowych haseł. Operator tworzy lokalny `.env` na podstawie `.env.example`.

Połączenie aplikacji z bazą może być budowane z następujących zmiennych:

- `DB_HOST`,
- `DB_PORT`,
- `DB_NAME`,
- `DB_USER`,
- `DB_PASSWORD`.

Pozostawiono również obsługę `DATABASE_URL`, ponieważ korzystają z niej testy i może być przydatna w przyszłym środowisku CI/CD.

Dane administratora początkowego również mogą być przekazane przez środowisko:

- `DEFAULT_ADMIN_USERNAME`,
- `DEFAULT_ADMIN_EMAIL`,
- `DEFAULT_ADMIN_PASSWORD`.

## 7. Trwałość danych

Zdefiniowano dwa nazwane wolumeny:

- `postgres_data` montowany w `/var/lib/postgresql/data`,
- `attachments_data` montowany w `/app/uploads/attachments`.

Dzięki temu zatrzymanie lub ponowne utworzenie kontenera aplikacji nie powoduje automatycznej utraty bazy ani załączników.

## 8. Kontrola stanu aplikacji

Serwis aplikacji posiada healthcheck wykonujący żądanie HTTP do `/login`. Pozwala to odróżnić samo uruchomienie procesu kontenera od faktycznej gotowości aplikacji do obsługi żądań.

## 9. Procedura uruchomienia

Na Windows/PowerShell:

```powershell
Copy-Item .env.example .env
# edycja haseł w .env
docker compose up --build -d
docker compose ps
```

Po osiągnięciu stanu `healthy` należy wejść na:

```text
http://localhost:5000/
```

Następnie wykonać podstawową kontrolę funkcjonalną: logowanie, otwarcie listy zgłoszeń i utworzenie testowego zgłoszenia.

## 10. Procedura weryfikacyjna po wdrożeniu konteneryzacji

Do zamknięcia etapu należy potwierdzić na komputerze z Docker Desktop:

1. `docker compose config` kończy się bez błędu,
2. `docker compose build` buduje obraz aplikacji,
3. `docker compose up -d` uruchamia oba serwisy,
4. `docker compose ps` pokazuje `healthy` dla `db` i `app`,
5. aplikacja odpowiada na `http://localhost:5000/`,
6. logowanie działa,
7. można utworzyć zgłoszenie,
8. załącznik pozostaje dostępny po `docker compose down` i ponownym `docker compose up -d`,
9. dane PostgreSQL pozostają dostępne po odtworzeniu kontenerów,
10. lokalny zestaw testów nadal przechodzi poleceniem `python -m pytest -q`.

## 11. Znaczenie dla dalszego CI/CD

Po potwierdzeniu powyższych punktów projekt posiada powtarzalną definicję środowiska, którą można wykorzystać w kolejnym etapie. Pipeline CI będzie mógł automatycznie uruchamiać testy i budować obraz na podstawie `Dockerfile`, a część CD będzie mogła uruchamiać przygotowaną wersję za pomocą tej samej konfiguracji kontenerowej.
