# v4.2 – dane zgłaszającego w obsłudze zgłoszeń

Zmiany względem v4.1:

- technik i administrator widzą nazwę użytkownika zgłaszającego na liście zgłoszeń,
- w szczegółach zgłoszenia technik i administrator widzą nazwę użytkownika i adres e-mail zgłaszającego,
- dodano testy widoczności danych zgłaszającego,
- aktualny zestaw zawiera 29 testów,
- zmiana nie wymaga migracji bazy danych – wykorzystuje istniejącą relację `Ticket.creator`.

Ta wersja nadaje się do scenariusza aktualizacji działającego środowiska v4.1 -> v4.2 z zachowaniem istniejących wolumenów PostgreSQL i załączników.
