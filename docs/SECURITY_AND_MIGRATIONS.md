# Rozszerzenie HelpDesk: zdarzenia bezpieczeństwa i migracje schematu

Data realizacji: 2026-09-27

## 1. Cel zmian

Rozszerzenie łączy część praktyczną aplikacji z zagadnieniami bezpieczeństwa i uwarunkowań technologicznych automatyzacji. Dodano dwa mechanizmy: audyt zdarzeń bezpieczeństwa oraz wersjonowane migracje schematu PostgreSQL.

## 2. Dziennik zdarzeń bezpieczeństwa

Nowy model `SecurityEvent` przechowuje zdarzenia niezależnie od historii aktywności ticketów. Dzięki temu możliwe jest zapisanie także zdarzeń, które nie są związane ze zgłoszeniem, np. nieudanego logowania.

Rejestrowane są obecnie:

- `login_success`,
- `login_failed`,
- `logout`,
- `access_denied`,
- `user_created`,
- `user_role_changed`,
- `user_status_changed`,
- `user_password_reset`,
- `user_deleted`,
- `permission_change_rejected`.

Wpis może zawierać identyfikator użytkownika, nazwę loginu, użytkownika będącego celem zmiany, adres IP, user-agent, opis i czas UTC. Hasła ani wartości sekretów nie są logowane.

Dla administratora dodano widok `/admin/security-events`. Dane można filtrować po typie zdarzenia, wyniku i nazwie użytkownika.

Dodatkowo aplikacja blokuje odebranie roli lub dezaktywację ostatniego aktywnego administratora. Zablokowana próba także trafia do dziennika bezpieczeństwa.

## 3. Migracje PostgreSQL

Do projektu dodano Flask-Migrate, które korzysta z Alembic. Katalog `migrations/` zawiera historię schematu:

1. `0001_initial_schema` - stan bazowy aplikacji przed wprowadzeniem migracji,
2. `0002_security_events` - utworzenie tabeli i indeksów dziennika bezpieczeństwa.

Dla nowej pustej bazy wykonywane są obie rewizje. Dla istniejącej bazy, która została wcześniej utworzona przez `db.create_all()`, kod wykrywa obecność istniejących tabel bez tabeli `alembic_version`, wykonuje `stamp` do rewizji `0001_initial_schema`, a następnie uruchamia `upgrade`. Pozwala to zachować dotychczasowe dane i zastosować wyłącznie nowe zmiany.

## 4. Automatyzacja podczas uruchamiania

`docker-entrypoint.sh` nadal uruchamia `init_db.py` przed Gunicornem. Skrypt po uzyskaniu połączenia z PostgreSQL uruchamia brakujące migracje, a dopiero później tworzy brakujące dane startowe. Oznacza to, że późniejszy etap CD może aktualizować kod i schemat bazy w ramach jednego kontrolowanego procesu.

## 5. Testy

Dodano `tests/test_security.py`. Testy sprawdzają m.in. zapis poprawnego i błędnego logowania, wylogowanie, odmowę dostępu, rejestrowanie zmian roli i resetu hasła, dostęp administratora do dziennika oraz ochronę ostatniego aktywnego administratora.

Łącznie projekt zawiera 25 testów automatycznych.
