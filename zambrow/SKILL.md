---
name: zambrow
description: >-
  Search, extract contacts, and browse local services, companies, classifieds,
  forum discussions, local news, municipal events calendar, cinema showtimes,
  labor market (PUP), and GUS BDL macroeconomic statistics in Zambrów.
  Use whenever the user asks about Zambrów: local news, events, concerts, cinema repertory,
  contractors, repair services, classifieds, municipal affairs, unemployment, wages,
  or demographics (e.g. "co słychać w Zambrowie", "imprezy Zambrów", "kino Zambrów",
  "repertuar kina", "ogłoszenia Zambrów", "forum Zambrów", "bezrobocie Zambrów", "GUS Zambrów").
---

# Zambrów Local News, Services, Community, Events & Cinema Skill

This skill provides automated tools to search, extract contacts, browse community recommendations, track local news, inspect the events calendar, and check cinema repertoire from the primary portals covering the town and county of Zambrów:
1. **Zambrow.org** — the primary municipal portal (Local News, Classified Ads / Ogłoszenia, Company Directory / Katalog Firm, Community Discussion Forum, and Municipal Events Calendar / Wydarzenia & Imprezy).
2. **Zambrowiacy.pl** — regional editorial and municipal news portal (Local News, Public Administration / Samorząd, Education / Szkoły, Announcements). *Note: zambrowiacy.pl does not host a user forum or classified ads.*
3. **Kino.mokzambrow.pl** — the municipal cinema (Miejski Ośrodek Kultury / Centrum Kultury w Zambrowie): currently playing movies ("gramy"), upcoming announcements ("zapowiedzi"), full monthly calendar with exact daily showtimes, movie synopsis, trailers, age restrictions, ticket prices (2D/3D), box office opening hours, and direct online ticket booking via Eurobilet.

## Helper CLI Tool: `zambrow_tool.py`

Located at:
`~/.gemini/skills/zambrow/scripts/zambrow_tool.py` (and in workspace `ai-skills/zambrow/scripts/zambrow_tool.py`)

The script is built with zero external dependencies (pure Python 3 standard library). It automatically:
- Scrapes and aggregates chronological news from both portals with headlines, dates, authors, categories, leads, and full text.
- Scrapes the municipal events and cultural calendar from Zambrow.org with dates, times, locations, categories, and direct links.
- Parses cinema repertory, daily showtime schedules, movie metadata, and ticket pricing from `kino.mokzambrow.pl`.
- Performs unified keyword search across Zambrow.org (articles, forum, ads, companies, events), Zambrowiacy.pl, and Kino.mokzambrow.pl with source badges.
- Decodes Cloudflare email protection (`data-cfemail`).
- Unmasks JavaScript-protected contact details (`showNumber()` phone numbers & `showEmail()`).
- Normalizes and formats Polish phone numbers and addresses.

---

### 1. Cinema Repertoire & Calendar (`cinema` / `kino`)

Fetches live movie showtimes, calendar schedules, and ticket info from `kino.mokzambrow.pl`:

```bash
# Today's cinema repertoire (titles, showtimes, links to details, online booking)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --today
# or using alias 'kino'
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py kino --today

# Repertoire with inline Filmweb & IMDb ratings and quality verdict (-r / --ratings)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --today -r
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --schedule --days 7 --ratings

# Repertoire for a specific date (e.g. 2026-10-16, tomorrow)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --date 2026-10-16 -r
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --date jutro

# Upcoming calendar schedule for the next N days (default: 7)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --schedule --days 7

# List all movies with genres, runtimes, screening dates, and trailer links (add -r for ratings)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --movies -r

# Filter by status: currently playing or upcoming announcements
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --gramy -r
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --zapowiedzi -r

# Get complete movie details (synopsis, Filmweb + IMDb ratings, verdict, screening schedule, trailer, booking)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --movie "Marsupilami"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --movie "Lalka"

# Quick rating lookup for any movie on Filmweb & IMDb (checks score, vote count & verdict)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --rate "Napad"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py kino --rate "Incepcja"

# Cinema box office opening hours, telephone, address, and 2D/3D ticket prices
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --info

# Machine-readable JSON output
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --today -r --json
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --schedule --days 7 --json
```

---

### 2. Scraping Local News & Articles (`news`)

Scrapes chronological news across portals, sorted newest first:

```bash
# Unified news from portals for the last 14 days (headlines + leads by default)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --days 14

# Choose specific source: all (default), zambrow-org, or zambrowiacy
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --source all --days 7 --limit 20
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --source zambrowiacy --days 14
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --source zambrow-org --days 14

# Filter by category or topic (e.g. edukacja, komunikat, inwestycje)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --category edukacja
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --category szpital

# Include full article body text in the output
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --days 3 --full

# Fast mode (headlines and dates only, skipping leads) or machine-readable JSON
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --days 14 --no-lead
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py news --days 14 --json
```

> [!TIP]
> **Kros-walidacja gorących i kontrowersyjnych tematów na Forum (`forum`):**
> W przypadku newsów politycznych, kontrowersyjnych interpelacji radnych (np. symbole w szkołach, spory w radzie miasta, inwestycje, szpital, lokalne podatki) **zawsze warto skros-walidować temat na forum mieszkańców `zambrow.org`** (`search "<temat/nazwisko>" --section forum` lub `browse "forum"`). Artykuły prasowe często prezentują jedynie oficjalne stanowiska lub autopromocję polityków, podczas gdy dyskusje na forum pozwalają poznać autentyczne nastroje mieszkańców, lokalny kontekst i zweryfikować, czy sprawa ma realne podłoże, czy to jedynie medialny teatr.



---

### 3. Municipal Events & Cultural Calendar (`events` / `imprezy` / `wydarzenia`)

Scrapes live upcoming concerts, exhibitions, workshops, author meetings, and community events from `zambrow.org/wydarzenia-imprezy`:

```bash
# List all upcoming events in Zambrów and county (dates, venues, categories, times)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events
# or using aliases 'imprezy' / 'wydarzenia'
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py imprezy

# Filter by timeframe (next N days, e.g. 7 or 14 days)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --days 7
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --days 14

# Filter by month (1-12)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --month 10

# Filter by category or topic (e.g. koncert, warsztaty, wernisaż, spotkanie)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --category koncert
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --category warsztaty

# Scrape full article body and contacts for each event
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --details

# Machine-readable JSON output (feed for Generative UI calendar widgets)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --json
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --days 14 --json
```

---

### 4. Searching the Portals (`search`)

Searches across `zambrow.org` (forum, adverts, firms, news, events), `zambrowiacy.pl`, and `kino.mokzambrow.pl` simultaneously:

```bash
# Global search across portals (all sections)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "szpital" -S all
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "Lalka" -S all
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "koncert" -S all

# Search only specific source (zambrow-org, zambrowiacy, or cinema/kino)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "inwestycje" -S zambrowiacy
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "kominiarz" -S zambrow-org
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "animowany" -S cinema

# Filter by section (forum, adverts, firms, news, cinema, events)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "elektryk" --section adverts
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "sprzątanie" --section firms
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "hydraulik" --section forum
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "oświata" --section news
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "kino" --section cinema
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "koncert" --section events

# Automatically scrape direct phone numbers and emails for each hit
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "elektryk" --section adverts --details

# Machine-readable JSON output
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py search "szpital" --json
```

---

### 5. Fetching Post / Article / Ad / Company / Movie / Events Details (`get`)

Pass any full URL from `zambrow.org`, `zambrowiacy.pl`, or `kino.mokzambrow.pl`:

```bash
# Events Calendar on zambrow.org
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrow.org/wydarzenia-imprezy"

# Specific event article on zambrow.org
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrow.org/artykul/przed-nami-cztery-recitale-n1859368"

# Kino Zambrów movie page (synopsis, showtimes, trailer, booking link)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://kino.mokzambrow.pl/lalka-2/"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://kino.mokzambrow.pl/marsupilami/"

# Kino Zambrów info page (box office hours, ticket prices 2D/3D, contact)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://kino.mokzambrow.pl/kino/"

# Zambrow.org news article
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrow.org/artykul/uwaga-woda-warunkowo-n1868601"

# Zambrowiacy.pl news article
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrowiacy.pl/info/od-jutra-rozpoczecie-przyjec-do-zakladu-opiekunczo-leczniczego-w-zambrowie/"

# Forum thread on zambrow.org (author, replies, decoded contacts)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrow.org/post/kominiarz-f615014"

# Classified ad on zambrow.org (unmasked phone, email, date, price, parameters, description)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrow.org/oferta/elektryk-amperzloty-chlopak-m2465554"

# Real estate offer with automatic image downloading for visual classification
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrow.org/oferta/dom-20856m2budynek-gospodarczy-13060m-m2586674" --download-images "~/zambrow-vault/nieruchomosci/img/2586674" --max-images 5

# Company card from catalog on zambrow.org
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get "https://zambrow.org/firma/dom-na-blysk-uslugi-sprzatajace-agnieszka-le-m27443"
```

---

### 6. Browsing Categories & Classifieds (`browse`)

```bash
# Browse real estate classifieds (shows extracted prices, dates, categories, and thumbnails)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "ogloszenia/nieruchomosci/"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "ogloszenia/nieruchomosci/domy/"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "ogloszenia/nieruchomosci/mieszkania/"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "ogloszenia/nieruchomosci/dzialki-grunty/"

# Pagination and limiting results (-p, --page, -m, --limit)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "ogloszenia/nieruchomosci/" --page 2 --limit 15

# Browse community discussion forums (shows thread title, author, date, last reply, comment count)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "forum/ogolne/"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "forum/regionalne/"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "forum/polityczne/"

# Browse classified ads in specific service branches
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "ogloszenia/uslugi-i-firmy/elektryk"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "ogloszenia/uslugi-i-firmy/remontowo--budowlane"

# Browse company directory map
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py browse "budownictwo-dom-mapa"
```

For a comprehensive list of category slugs and URLs, see [references/categories.md](./references/categories.md).

---

### 7. Official KRS Company Registry Lookup (`krs`)

Fetches official, up-to-date company registration data directly from the Ministry of Justice Open REST API (`api-krs.ms.gov.pl`):

```bash
# Lookup company details (board members, supervisory council, share capital, representation)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py krs 0000130730

# Output structured JSON for automated OSINT verification & agent pipelines
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py krs 0000130730 --json
```

---

### 8. Public Information Bulletin (BIP) Search (`bip`)

Unified search and scraping across municipal and county Public Information Bulletins (City of Zambrów contracts register at `bip.zambrow.pl` and County of Zambrów council sessions, job postings, and announcements at `samorzad.gov.pl/web/powiat-zambrowski/`):

```bash
# Search contracts and municipal records for keywords
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bip "audyt"
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bip "szpital"

# Filter by section: umowy, sesje, praca, wszystkie
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bip --section praca
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bip --section sesje

# Filter by target: miasto (bip.zambrow.pl) or powiat (samorzad.gov.pl)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bip "remont" --target miasto
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bip --target powiat --section praca

# Structured JSON output
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bip "doradztwo" --json
```

---

### 9. GUS Bank Danych Lokalnych (`bdl`)

Official macroeconomic, demographic, housing, wage, and enterprise statistics from the Central Statistical Office (GUS BDL REST API `https://bdl.stat.gov.pl/api/v1/`). Preconfigured for Powiat Zambrowski (`062013814000`) and Miasto Zambrów (`062013814011`):

```bash
# Full 10-year macroeconomic & demographic dashboard for Zambrów (salaries, unemployment, population, new flats, REGON)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bdl

# Query specific preset metric or variable ID (e.g. wynagrodzenia, bezrobocie, ludnosc, mieszkania, firmy)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bdl wynagrodzenia
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bdl bezrobocie --unit powiat
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bdl 748601 --unit miasto --years 5

# Search GUS BDL variable catalog
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bdl search "mieszkania oddane"

# Export historical indicators to CSV for R statistical modeling (Agent Statystyk)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bdl --export-csv ~/zambrow-vault/data/bdl_wskazniki_zambrow.csv --years 10
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py bdl --json
```

---

### 10. Powiatowy Urząd Pracy i WUP (`pup`)

Monitors the local labor market, training grants, internship funding freezes, and statistical bulletins from Powiatowy Urząd Pracy w Zambrowie (`zambrow.praca.gov.pl`) and Wojewódzki Urząd Pracy w Białymstoku (`wupbialystok.praca.gov.pl`):

```bash
# Latest news, recruitment announcements, and internship grant updates from PUP Zambrów
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py pup news

# Monthly labor market statistical reports and PDF bulletins (WUP Białystok & PUP Zambrów)
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py pup reports

# Full details and attachments for a specific PUP announcement
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py pup get "<URL>"

# Export PUP announcements and monthly bulletins to CSV for Agent Statystyk
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py pup export --export-csv ~/zambrow-vault/data/pup_komunikaty.csv
python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py pup news --json
```

---

## Generative UI / Interactive Visual Event Calendar (Generative UI Widget)

When the user asks for a visual, interactive calendar or wants to explore upcoming events/movies interactively:
1. Fetch live events or movie data as structured JSON:
   ```bash
   python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --json
   # or for cinema:
   python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py cinema --schedule --days 7 --json
   ```
2. Following the **Generative UI** skill, generate a responsive interactive HTML widget (`.html`) in the artifact directory (`<appDataDir>/brain/<conversation-id>/events_calendar.html`):
   - Include allowlisted Tailwind CSS: `<script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>`
   - Adhere to the design system using host theme variables: `bg-[var(--card)]`, `text-[var(--foreground)]`, `text-[var(--muted-foreground)]`, `border-[var(--border)]`, `bg-[var(--primary)]`.
   - Provide interactive filter pills: *Wszystkie*, *Koncerty*, *Warsztaty / Edukacja*, *Wystawy / Wernisaże*, *Spotkania*.
   - Render date badges (e.g. `PAŹ 15`), relative countdown tags (*Jutro*, *za 3 dni*), time, venue location tags, and direct clickable links to articles and tickets.
3. Embed inline using `<agent-embed src="file:///.../events_calendar.html"></agent-embed>` (when under 500px tall) or present as a side artifact.

---

## Interactive Browser Fallback (Chrome DevTools MCP)

For submitting forms, purchasing tickets interactively, adding threads, or viewing image galleries:
1. Use `navigate_page` with URL (e.g. `https://bilety-mokzambrow.eurobilet.pl/MSI/mvc/pl#new_tab` or `https://zambrow.org/forum/ogolne/`).
2. Use `take_snapshot` to inspect page nodes.
3. Use `click` or `fill_form` to interact.
