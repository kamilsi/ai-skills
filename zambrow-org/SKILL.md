---
name: zambrow-org
description: >-
  Search, extract contacts, and browse local services, companies, classified ads,
  forum discussions, local news articles, and cinema repertory/calendar in Zambrów
  from Zambrow.org, Zambrowiacy.pl, and Kino.mokzambrow.pl (the municipal portals
  and cinema for Zambrów and surrounding areas). Use whenever the user asks to find
  local news, contractors, tradesmen, repair services, companies, classifieds,
  forum opinions, or cinema showtimes and movies in Zambrów (e.g. "zambrow.org",
  "zambrowiacy.pl", "kino Zambrów", "kino.mokzambrow.pl", "repertuar kina",
  "co grają w kinie w Zambrowie", "filmy Zambrów", "wiadomości Zambrów",
  "co się dzieje w Zambrowie", "kominiarz Zambrów", "elektryk Zambrów",
  "forum Zambrów", "katalog firm Zambrów").
---

# Zambrów Local News, Services, Community & Cinema Skill

This skill provides automated tools to search, extract contacts, browse community recommendations, track local news, and inspect the cinema repertoire & calendar from the three primary portals covering the town and county of Zambrów:
1. **Zambrow.org** — the primary municipal portal (Local News, Classified Ads / Ogłoszenia, Company Directory / Katalog Firm, and Community Discussion Forum).
2. **Zambrowiacy.pl** — regional editorial and municipal news portal (Local News, Public Administration / Samorząd, Education / Szkoły, Announcements). *Note: zambrowiacy.pl does not host a user forum or classified ads.*
3. **Kino.mokzambrow.pl** — the municipal cinema (Miejski Ośrodek Kultury / Centrum Kultury w Zambrowie): currently playing movies ("gramy"), upcoming announcements ("zapowiedzi"), full monthly calendar with exact daily showtimes, movie synopsis, trailers, age restrictions, ticket prices (2D/3D), box office opening hours, and direct online ticket booking via Eurobilet.

## Helper CLI Tool: `zambrow_tool.py`

Located at:
`~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py` (and in workspace `ai-skills/zambrow-org/scripts/zambrow_tool.py`)

The script is built with zero external dependencies (pure Python 3 standard library). It automatically:
- Scrapes and aggregates chronological news from both portals with headlines, dates, authors, categories, leads, and full text.
- Parses cinema repertory, daily showtime schedules, movie metadata, and ticket pricing from `kino.mokzambrow.pl`.
- Performs unified keyword search across Zambrow.org, Zambrowiacy.pl, and Kino.mokzambrow.pl with source badges.
- Decodes Cloudflare email protection (`data-cfemail`).
- Unmasks JavaScript-protected contact details (`showNumber()` phone numbers & `showEmail()`).
- Normalizes and formats Polish phone numbers and addresses.

---

### 1. Cinema Repertoire & Calendar (`cinema` / `kino`)

Fetches live movie showtimes, calendar schedules, and ticket info from `kino.mokzambrow.pl`:

```bash
# Today's cinema repertoire (titles, showtimes, links to details, online booking)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --today
# or using alias 'kino'
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py kino --today

# Repertoire with inline Filmweb & IMDb ratings and quality verdict (-r / --ratings)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --today -r
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --schedule --days 7 --ratings

# Repertoire for a specific date (e.g. 2026-10-16, tomorrow)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --date 2026-10-16 -r
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --date jutro

# Upcoming calendar schedule for the next N days (default: 7)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --schedule --days 7

# List all movies with genres, runtimes, screening dates, and trailer links (add -r for ratings)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --movies -r

# Filter by status: currently playing or upcoming announcements
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --gramy -r
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --zapowiedzi -r

# Get complete movie details (synopsis, Filmweb + IMDb ratings, verdict, screening schedule, trailer, booking)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --movie "Marsupilami"
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --movie "Lalka"

# Quick rating lookup for any movie on Filmweb & IMDb (checks score, vote count & verdict)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --rate "Napad"
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py kino --rate "Incepcja"

# Cinema box office opening hours, telephone, address, and 2D/3D ticket prices
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --info

# Machine-readable JSON output
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --today -r --json
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py cinema --schedule --days 7 --json
```

---

### 2. Scraping Local News & Articles (`news`)

Scrapes chronological news across portals, sorted newest first:

```bash
# Unified news from portals for the last 14 days (headlines + leads by default)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --days 14

# Choose specific source: all (default), zambrow-org, or zambrowiacy
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --source all --days 7 --limit 20
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --source zambrowiacy --days 14
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --source zambrow-org --days 14

# Filter by category or topic (e.g. edukacja, komunikat, inwestycje)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --category edukacja
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --category szpital

# Include full article body text in the output
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --days 3 --full

# Fast mode (headlines and dates only, skipping leads) or machine-readable JSON
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --days 14 --no-lead
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py news --days 14 --json
```

---

### 3. Searching the Portals (`search`)

Searches across `zambrow.org`, `zambrowiacy.pl`, and `kino.mokzambrow.pl` simultaneously:

```bash
# Global search across portals (all sections)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "szpital" -S all
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "Lalka" -S all

# Search only specific source (zambrow-org, zambrowiacy, or cinema/kino)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "inwestycje" -S zambrowiacy
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "kominiarz" -S zambrow-org
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "animowany" -S cinema

# Filter by section (forum, adverts, firms, news, cinema)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "elektryk" --section adverts
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "sprzątanie" --section firms
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "hydraulik" --section forum
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "oświata" --section news
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "kino" --section cinema

# Automatically scrape direct phone numbers and emails for each hit
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "elektryk" --section adverts --details

# Machine-readable JSON output
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py search "szpital" --json
```

---

### 4. Fetching Post / Article / Ad / Company / Movie Details (`get`)

Pass any full URL from `zambrow.org`, `zambrowiacy.pl`, or `kino.mokzambrow.pl`:

```bash
# Kino Zambrów movie page (synopsis, showtimes, trailer, booking link)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://kino.mokzambrow.pl/lalka-2/"
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://kino.mokzambrow.pl/marsupilami/"

# Kino Zambrów info page (box office hours, ticket prices 2D/3D, contact)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://kino.mokzambrow.pl/kino/"

# Zambrow.org news article
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://zambrow.org/artykul/uwaga-woda-warunkowo-n1868601"

# Zambrowiacy.pl news article
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://zambrowiacy.pl/info/od-jutra-rozpoczecie-przyjec-do-zakladu-opiekunczo-leczniczego-w-zambrowie/"

# Forum thread on zambrow.org (author, replies, decoded contacts)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://zambrow.org/post/kominiarz-f615014"

# Classified ad on zambrow.org (unmasked phone, email, date, description)
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://zambrow.org/oferta/elektryk-amperzloty-chlopak-m2465554"

# Company card from catalog on zambrow.org
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py get "https://zambrow.org/firma/dom-na-blysk-uslugi-sprzatajace-agnieszka-le-m27443"
```

---

### 5. Browsing Categories (`browse`)

```bash
# Browse classified ads in a specific branch on zambrow.org
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py browse "ogloszenia/uslugi-i-firmy/elektryk"
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py browse "ogloszenia/uslugi-i-firmy/remontowo--budowlane"

# Browse company directory map
python3 ~/.gemini/skills/zambrow-org/scripts/zambrow_tool.py browse "budownictwo-dom-mapa"
```

For a comprehensive list of category slugs and URLs, see [references/categories.md](./references/categories.md).

---

## Interactive Browser Fallback (Chrome DevTools MCP)

For submitting forms, purchasing tickets interactively, adding threads, or viewing image galleries:
1. Use `navigate_page` with URL (e.g. `https://bilety-mokzambrow.eurobilet.pl/MSI/mvc/pl#new_tab` or `https://zambrow.org/forum/ogolne/`).
2. Use `take_snapshot` to inspect page nodes.
3. Use `click` or `fill_form` to interact.
