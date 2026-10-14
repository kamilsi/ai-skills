# Asystent Lokalny Zambrów (`zambrow`)

Wielomodułowy asystent lokalny dla miasta Zambrów i powiatu zambrowskiego. Monitoruje wiadomości, sprawy samorządowe, ogłoszenia drobne, katalog firm, dyskusje na forum mieszkańców, kalendarz imprez miejskich oraz repertuar i seanse Kina Miejskiego MOK z automatyczną weryfikacją ocen i jakości filmów (Filmweb + IMDb).

Obsługiwane portale i źródła:
- **Zambrow.org** — najstarszy i największy portal miejski (artykuły, ogłoszenia, firmy, forum dyskusyjne, kalendarz imprez).
- **Zambrowiacy.pl** — niezależny portal regionalny (samorząd, oświata, inwestycje, kultura).
- **Kino.mokzambrow.pl** — kino Miejskiego Ośrodka Kultury (repertuar, kalendarium, seanse, zwiastuny, cennik biletów i rezerwacja Eurobilet).
- **Filmweb.pl & IMDb.com** — automatyczna weryfikacja ocen, liczby głosów i werdykt jakościowy dla wyświetlanych filmów.
- **Instytucje miejskie** — Urząd Miasta, Starostwo, Szpital, Policja, MOSiR/basen, Biblioteka Miejska, ZCiW.

---

## Dwa warianty działania skilla

Skill występuje w dwóch wersjach dopasowanych do środowiska wykonawczego:

### 1. Wersja lokalna na PC (CLI / Antigravity IDE)
- **Lokalizacja:** `SKILL.md`, `scripts/zambrow_tool.py`, `references/categories.md`
- **Działanie:** Wywoływany automatycznie przez model Antigravity lub bezpośrednio z wiersza poleceń przez skrypt `zambrow_tool.py` (czysty Python 3 stdlib, bez zależności zewnętrznych). Posiada wsparcie dla Generative UI (`events_calendar.html`).
- **Instalacja:** Dostępny natychmiast dzięki dowiązaniu symbolicznemu `~/.gemini/skills/ -> ~/Code/ai-skills`.
- **Przykłady użycia:**
  ```bash
  # Kino: dzisiejszy repertuar z ocenami Filmweb/IMDb
  python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --today -r

  # Kalendarz imprez i wydarzeń kulturalnych
  python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events

  # Wiadomości z ostatnich 14 dni
  python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --days 14

  # Szukanie usług / fachowców wraz z danymi kontaktowymi
  python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "elektryk" --section adverts --details
  ```

---

### 2. Wersja webowa (dla Gemini Apps / gemini.google.com GUI)
- **Lokalizacja:** `web/` (oraz spakowane archiwum `web/zambrow.zip`).
- **Działanie:** Oparta na instrukcjach dla modelu i wbudowanym Google Search Grounding (`site:zambrow.org`, `site:zambrowiacy.pl`, `site:kino.mokzambrow.pl`, `site:filmweb.pl`, `site:imdb.com`). Zgodna z oficjalną specyfikacją Google Agent Skills.
- **Zawartość paczki:**
  ```text
  zambrow.zip
  └── SKILL.md  (100% self-contained; środowisko webowe nie wspiera folderu references/)
  ```

---

## ⚠️ Ważne: Utrzymanie i ręczna synchronizacja z Gemini GUI Web

> [!IMPORTANT]
> **Gemini Web (`gemini.google.com`) NIE synchronizuje się automatycznie z lokalnym dyskiem ani repozytorium Git.**
>
> Wszelkie zmiany w instrukcjach, adresach URL portali, cennikach biletów czy kategoriach **muszą być każdorazowo ręcznie wgrane do interfejsu webowego Gemini**.

### Instrukcja aktualizacji w Gemini Web GUI:
1. Zbuduj lub zaktualizuj paczkę `zambrow.zip`:
   ```bash
   cd ~/Code/ai-skills/zambrow/web && zip -X -FS zambrow.zip SKILL.md
   ```
2. Otwórz w przeglądarce [gemini.google.com](https://gemini.google.com) lub aplikację Gemini na macOS.
3. W menu bocznym kliknij **Dostosuj (Customize)** -> na górze wybierz zakładkę **Umiejętności (Skills)**.
4. Kliknij przycisk **Prześlij (Upload)**:
   - Wybierz plik `zambrow.zip` (zawiera `SKILL.md` bezpośrednio w korzeniu),
   - Albo bezpośrednio sam plik `web/SKILL.md`.
5. Przejrzyj formularz i kliknij **Utwórz (Create)** (lub Zapisz zmiany).
6. Upewnij się, że skill `zambrow` ma włączony suwak aktywności.
7. W czacie możesz wywołać go wpisując `/zambrow` lub zadając naturalne pytanie (np. *„Co grają dzisiaj w kinie w Zambrowie i jakie filmy polecasz?”* albo *„Jakie imprezy są w Zambrowie w ten weekend?”*).

---

## Wymogi specyfikacji Agent Skills
Zgodnie ze specyfikacją [agentskills.io](https://agentskills.io) oraz wytycznymi Google Agent Skills:
1. **Nazewnictwo:** Nazwa w polu `name` musi być w formacie kebab-case (maks. 64 znaki, np. `zambrow`).
2. **Lokalizacja pliku:** Plik `SKILL.md` **musi znajdować się w folderze głównym** (w korzeniu archiwum ZIP, a nie w podfolderze).
3. **Opis (description):** Twardy limit **maks. 1 024 znaki** (rekomendowane 400–700 znaków), precyzujący co skill robi i kiedy ma zostać wywołany.
4. **Brak `references/` w wersji webowej:** Webowe runtime'y Gemini nie indeksują podkatalogów — cała wiedza musi być zawarta wewnątrz `SKILL.md`.
