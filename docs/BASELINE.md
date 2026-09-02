# Stan bazowy aplikacji HelpDesk przed CI/CD

Data inwentaryzacji: 2026-08-25

Dokument opisuje punkt odniesienia przed rozpoczęciem konteneryzacji i budowy potoku CI/CD. Ma służyć zarówno jako dokumentacja techniczna, jak i podstawa do późniejszego porównania procesu manualnego z procesem zautomatyzowanym.

## 1. Stan projektu w dostarczonym archiwum

- aplikacja: monolityczna aplikacja webowa Flask,
- deklarowana wersja środowiska: Python 3.13,
- baza podstawowa: PostgreSQL,
- ORM: Flask-SQLAlchemy,
- interfejs: Jinja + Bootstrap 5,
- obsługa plików: lokalny katalog `uploads/attachments`,
- uruchamianie: bezpośrednio przez `python app.py`,
- serwer: wbudowany serwer deweloperski Flask z `debug=True`,
- inicjalizacja bazy: `db.create_all()` przy uruchomieniu `app.py`,
- dane startowe: domyślne kategorie i konto administratora tworzone przez aplikację,
- konteneryzacja: brak `Dockerfile` i Docker Compose,
- CI/CD: brak workflow GitHub Actions,
- migracje bazy: brak wersjonowanych migracji,
- testy w stanie wejściowym: jeden plik `tests/test_app.py` z kilkoma scenariuszami.

## 2. Konfiguracja bazowa wynikająca z kodu i README

Jeżeli zmienne środowiskowe nie zostaną ustawione, aplikacja korzysta z następujących wartości domyślnych:

- `DATABASE_URL=postgresql://postgres:1234@localhost:5432/helpdesk_db`,
- `SECRET_KEY=change-this-secret`,
- baza: `helpdesk_db`,
- użytkownik PostgreSQL: `postgres`,
- hasło PostgreSQL: `1234`,
- adres aplikacji: `http://127.0.0.1:5000/`,
- konto startowe: `admin`,
- hasło startowe: `admin123`.

Wartości te opisują stan bazowy projektu i nie są docelową konfiguracją wdrożeniową. W dalszych etapach sekrety i parametry połączenia powinny być przekazywane z zewnątrz, np. przez zmienne środowiskowe.

## 3. Ręczne przygotowanie środowiska od zera

Poniższa procedura odwzorowuje obecny sposób uruchomienia aplikacji na komputerze z Windows/PowerShell.

1. Pobrać właściwą wersję kodu z repozytorium i przejść do katalogu projektu.
2. Upewnić się, że Python 3.13 jest zainstalowany i dostępny w `PATH`.
3. Utworzyć środowisko wirtualne:

   ```powershell
   python -m venv venv
   ```

4. Aktywować środowisko:

   ```powershell
   venv\Scripts\Activate.ps1
   ```

5. Zainstalować zależności:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Uruchomić PostgreSQL i przygotować bazę `helpdesk_db` dostępną dla konfiguracji aplikacji.
7. Ustawić `DATABASE_URL` i `SECRET_KEY` albo świadomie skorzystać z wartości domyślnych projektu.
8. Uruchomić aplikację:

   ```powershell
   python app.py
   ```

9. Przy pierwszym uruchomieniu aplikacja wykonuje `db.create_all()`, tworzy brakujące kategorie i - jeżeli konto nie istnieje - domyślnego administratora.
10. Otworzyć `http://127.0.0.1:5000/` i wykonać ręczną kontrolę działania, np. logowanie oraz otwarcie listy zgłoszeń.

Każdy z powyższych etapów wymaga ręcznego wykonania lub ręcznej kontroli operatora. Jest to proces przygotowania środowiska od zera, a nie jeszcze docelowy scenariusz pomiarowy wdrożenia kolejnej wersji.

## 4. Referencyjny proces manualnego wdrożenia kolejnej wersji

Do późniejszego eksperymentu należy odróżnić pierwszą instalację od kolejnego wdrożenia na przygotowanym już środowisku. Dla kolejnej wersji punktem odniesienia będzie następująca procedura:

1. pobranie lub przełączenie kodu na wskazaną wersję,
2. aktywacja właściwego środowiska Pythona,
3. instalacja/aktualizacja zależności z `requirements.txt`,
4. weryfikacja dostępności PostgreSQL i konfiguracji `DATABASE_URL`,
5. zatrzymanie poprzednio uruchomionej instancji aplikacji, jeżeli działa,
6. uruchomienie nowej wersji poleceniem `python app.py`,
7. ręczna weryfikacja, czy aplikacja odpowiada pod adresem `http://127.0.0.1:5000/`,
8. wykonanie prostego testu funkcjonalnego, np. logowania i odczytu listy zgłoszeń.

Dla późniejszych pomiarów należy dokładnie ustalić punkt START i STOP. Proponowany wariant: START w momencie rozpoczęcia pobierania/przełączania wersji kodu, STOP po poprawnym zakończeniu testu funkcjonalnego nowej wersji.

## 5. Wynik testów w stanie bazowym

Polecenie:

```powershell
python -m pytest
```

w dostarczonej wersji projektu nie dochodziło do wykonania testów. Pytest zatrzymywał się na etapie kolekcji z błędem `SyntaxError: bytes can only contain ASCII literal characters`, ponieważ jeden z komunikatów zawierających polskie znaki zapisano bezpośrednio jako literał bajtowy `b"..."`.

Dodatkowo pierwotna fixture próbowała zmienić `SQLALCHEMY_DATABASE_URI` na SQLite dopiero po zaimportowaniu aplikacji. Flask-SQLAlchemy jest jednak inicjalizowane podczas importu `app.py`, dlatego taka zmiana nie gwarantowała faktycznego przełączenia silnika na bazę testową.

## 6. Problemy i ryzyka istotne dla kolejnych etapów

- brak izolowanego, niezawodnego zestawu testów możliwego do uruchomienia w CI,
- brak konteneryzacji,
- brak potoku CI/CD,
- wartości domyślne sekretu i danych połączenia zapisane w kodzie,
- domyślne konto administratora i hasło tworzone automatycznie,
- uruchamianie serwera z `debug=True`,
- brak mechanizmu wersjonowanych migracji bazy danych,
- załączniki przechowywane w lokalnym systemie plików,
- obecność artefaktów lokalnych (`__pycache__`, przykładowy plik w `uploads`) w archiwum projektu.

Powyższe punkty nie muszą być wszystkie rozwiązane przed rozpoczęciem CI/CD, ale powinny być świadomie uwzględnione przy projektowaniu środowiska kontenerowego i procesu wdrożenia.

## 7. Zmiana wykonana w kroku „uporządkowanie testów”

Po zapisaniu stanu bazowego zestaw testów został rozdzielony na czytelne obszary: uwierzytelnianie i autoryzacja, obsługa zgłoszeń oraz funkcje administratora. Testy korzystają z izolowanej bazy SQLite tworzonej przed każdym testem, tymczasowego katalogu na załączniki oraz jawnie przygotowanych użytkowników i kategorii.

Zakres testów obejmuje między innymi:

- stronę logowania,
- poprawne i błędne logowanie,
- zablokowane konto,
- ochronę tras wymagających logowania,
- przekierowanie użytkownika bez uprawnień,
- utworzenie zgłoszenia z kategorią,
- walidację braku kategorii,
- izolację zgłoszeń pomiędzy zwykłymi użytkownikami,
- dodawanie komentarza,
- zmianę statusu przez technika i jej odmowę dla zwykłego użytkownika,
- przypisanie technika,
- zapis załącznika i jego metadanych,
- utworzenie użytkownika przez administratora.

## 8. Weryfikacja po uporządkowaniu testów i usunięcie ostrzeżeń

Po uporządkowaniu zestawu testów wykonano pełne uruchomienie na lokalnym środowisku Python 3.13.5. Wynik wyniósł:

```text
18 passed, 123 warnings in 12.64s
```

Wszystkie 18 przypadków testowych zakończyło się powodzeniem. Ostrzeżenia nie wpływały na wynik testów, ale wskazywały dwa miejsca wymagające modernizacji przed uruchamianiem testów w CI:

- modele używały wycofywanego w Pythonie 3.13 `datetime.utcnow()`,
- kod aplikacji i część testów używały legacy API SQLAlchemy `Query.get()` oraz pośrednio `Query.get_or_404()`.

Kod został zrefaktoryzowany bez wyciszania ostrzeżeń. Generowanie czasu UTC wykorzystuje teraz `datetime.now(UTC)` z zachowaniem dotychczasowego formatu naiwnych wartości czasu w istniejących kolumnach bazy, natomiast pobieranie rekordów po kluczu głównym realizowane jest przez `db.session.get(...)`. Obsługa brakujących rekordów w trasach HTTP wykonuje jawne `abort(404)`. Zmiany nie modyfikują zakresu funkcjonalnego aplikacji i nie wymagają na tym etapie migracji istniejącego schematu PostgreSQL.

Po pobraniu tej wersji projektu należy ponownie uruchomić `python -m pytest -q` i potwierdzić wynik na środowisku lokalnym przed wykorzystaniem testów jako bramki CI.


## 9. Potwierdzenie zakończenia etapu testów

Po refaktoryzacji ostrzeżeń zestaw 18 testów został ponownie uruchomiony w lokalnym środowisku użytkownika i zakończył się powodzeniem. Tym samym etap przygotowania testów można traktować jako zakończony, a działający zestaw testowy stanowi bramkę jakościową gotową do późniejszego włączenia do Continuous Integration.

Następnym krokiem projektu jest konteneryzacja opisana w `docs/CONTAINERIZATION.md`.
