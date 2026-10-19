#!/usr/bin/env python3
"""
zambrow_tool.py — CLI helper to search, browse, extract contacts, and track news & cinema in Zambrów.
Supports:
  - Search across portals: Zambrow.org (forum, classifieds, firms, news), Zambrowiacy.pl (news), and Kino.mokzambrow.pl (movies, schedule)
  - Detail extraction: phone numbers (showNumber JS & text), emails (Cloudflare decode & text), addresses
  - Category browsing on Zambrow.org
  - Cinema repertory, daily schedule, movie descriptions, showtimes, box office & pricing from kino.mokzambrow.pl
  - Terminal formatted view or raw JSON
"""

import sys
import os
import re
import html
import json
import time
import argparse
import datetime
import pathlib
import hashlib
import concurrent.futures
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import email.utils
from typing import List, Dict, Any, Optional

BASE_URL = "https://zambrow.org"
ZAMBROWIACY_BASE_URL = "https://zambrowiacy.pl"
KINO_BASE_URL = "https://kino.mokzambrow.pl"
KINO_BOOKING_URL = "https://bilety-mokzambrow.eurobilet.pl/MSI/mvc/pl#new_tab"
EVENTS_URL = f"{BASE_URL}/wydarzenia-imprezy"
CACHE_DIR = pathlib.Path.home() / ".cache" / "zambrow"

def get_cache(namespace: str, key: str, max_age_seconds: int = 3600) -> Optional[Any]:
    """Retrieves cached JSON payload if present and not expired."""
    try:
        fpath = CACHE_DIR / namespace / (hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json")
        if not fpath.exists():
            return None
        if (time.time() - fpath.stat().st_mtime) > max_age_seconds:
            return None
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def set_cache(namespace: str, key: str, value: Any) -> None:
    """Saves payload to disk cache safely."""
    try:
        ndir = CACHE_DIR / namespace
        ndir.mkdir(parents=True, exist_ok=True)
        fpath = ndir / (hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json")
        tmp_fpath = fpath.with_suffix(".tmp")
        with open(tmp_fpath, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False)
        tmp_fpath.replace(fpath)
    except Exception:
        pass
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

MONTH_MAP = {
    "sty": 1, "lut": 2, "mar": 3, "kwi": 4, "maj": 5, "cze": 6,
    "lip": 7, "sie": 8, "wrz": 9, "paź": 10, "paz": 10, "lis": 11, "gru": 12
}

POLISH_WEEKDAYS = {
    0: "poniedziałek",
    1: "wtorek",
    2: "środa",
    3: "czwartek",
    4: "piątek",
    5: "sobota",
    6: "niedziela"
}

def decode_cf_email(cf_hex: str) -> str:
    """Decodes Cloudflare email protection (data-cfemail hex xor)."""
    try:
        k = int(cf_hex[:2], 16)
        return "".join([chr(int(cf_hex[i:i+2], 16) ^ k) for i in range(2, len(cf_hex), 2)])
    except Exception:
        return ""

def clean_html_text(text: str) -> str:
    """Removes HTML tags and unescapes entities."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return " ".join(clean.split())

def fetch_url(url: str, timeout: int = 15, max_retries: int = 3) -> str:
    """Fetches URL, handles 429 rate limits with backoff, and decodes Cloudflare protected emails."""
    if not url.startswith("http"):
        url = urllib.parse.urljoin(BASE_URL, url)
    
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    
    content = ""
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", "ignore")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                time.sleep(1.2 * (attempt + 1))
                continue
            raise
    
    # Replace Cloudflare protected emails inline
    content = re.sub(
        r"<a[^>]*data-cfemail=[\x27\x22]([0-9a-fA-F]+)[\x27\x22][^>]*>.*?</a>",
        lambda m: decode_cf_email(m.group(1)),
        content
    )
    content = re.sub(
        r"data-cfemail=[\x27\x22]([0-9a-fA-F]+)[\x27\x22]",
        lambda m: decode_cf_email(m.group(1)),
        content
    )
    return content

def download_images(image_urls: List[str], dest_dir: str, limit: int = 5) -> List[str]:
    """Downloads up to limit images into dest_dir, returning list of saved file paths."""
    out_dir = pathlib.Path(dest_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for idx, img_url in enumerate(image_urls[:limit], 1):
        ext = ".jpg"
        if ".png" in img_url.lower(): ext = ".png"
        elif ".webp" in img_url.lower(): ext = ".webp"
        fname = f"foto_{idx}{ext}"
        target = out_dir / fname
        try:
            req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(target, "wb") as f:
                f.write(data)
            saved.append(str(target))
        except Exception as e:
            sys.stderr.write(f"Warning: failed to download {img_url}: {e}\n")
    return saved

def fetch_kino_json(endpoint: str, timeout: int = 15, max_age: int = 1800) -> Any:
    """Fetches WordPress REST API JSON from kino.mokzambrow.pl with disk caching."""
    cached = get_cache("kino_api", endpoint, max_age_seconds=max_age)
    if cached is not None:
        return cached
    url = f"{KINO_BASE_URL}/wp-json/wp/v2/{endpoint}"
    content = fetch_url(url, timeout=timeout)
    data = json.loads(content)
    set_cache("kino_api", endpoint, data)
    return data

def get_cinema_info() -> Dict[str, Any]:
    """Returns cinema contacts, box office hours, and ticket prices."""
    return {
        "source": "kino.mokzambrow.pl",
        "type": "cinema_info",
        "title": "Kino Miejskiego Ośrodka Kultury w Zambrowie (Centrum Kultury)",
        "name": "Kino Miejskiego Ośrodka Kultury w Zambrowie (Centrum Kultury)",
        "url": f"{KINO_BASE_URL}/kino/",
        "address": "Centrum Kultury w Zambrowie, ul. Wyszyńskiego 2a, 18-300 Zambrów",
        "phone": "86 475 44 88",
        "box_office_hours": "13:30 – 19:30 (kasa biletowa kina)",
        "prices": {
            "2D": {
                "normalny": "20 zł",
                "ulgowy": "16 zł",
                "grupowy": "13 zł",
                "karta_rodzina_3plus_senior": "13 zł"
            },
            "3D": {
                "normalny": "26 zł",
                "ulgowy": "23 zł",
                "grupowy": "21 zł",
                "karta_rodzina_3plus_senior": "13 zł"
            }
        },
        "booking_url": KINO_BOOKING_URL,
        "website": KINO_BASE_URL
    }

def search_zambrowiacy(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Searches zambrowiacy.pl using RSS search feed."""
    url = f"{ZAMBROWIACY_BASE_URL}/feed/?s={urllib.parse.quote(query)}"
    namespaces = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/"
    }
    try:
        content = fetch_url(url)
        root = ET.fromstring(content)
        channel = root.find("channel")
        if channel is None:
            return []
        items = channel.findall("item")
        results = []
        for it in items[:limit]:
            title = it.find("title").text or ""
            link = it.find("link").text or ""
            pub_date = it.find("pubDate").text or ""
            desc = it.find("description").text or ""
            clean_desc = clean_html_text(desc)
            clean_desc = re.sub(r"\[\s*&#8230;\s*\]", "...", clean_desc)
            clean_desc = re.sub(r"\[\s*\.\.\.\s*\]", "...", clean_desc)
            
            categories = [clean_html_text(c.text) for c in it.findall("category") if c.text]
            cat_str = ", ".join(categories) if categories else "Wiadomości"
            
            creator = it.find("dc:creator", namespaces)
            author = clean_html_text(creator.text) if creator is not None and creator.text else "Redakcja"
            
            dt = parse_date(pub_date)
            date_display = dt.strftime("%Y-%m-%d %H:%M") if dt else pub_date
            
            results.append({
                "source": "zambrowiacy.pl",
                "section": "Zambrowiacy.pl",
                "type": "news",
                "title": title,
                "url": link,
                "date": date_display,
                "info": f"Autor: {author} | Kategoria: {cat_str}",
                "snippet": clean_desc,
                "lead": clean_desc
            })
        return results
    except Exception:
        return []

def search_portal(query: str, section: Optional[str] = None, source: str = "all") -> List[Dict[str, Any]]:
    """
    Searches zambrow.org, zambrowiacy.pl, and/or kino.mokzambrow.pl with optional section filter:
      - None or 'all': all categories & portals
      - 'forum': Forum (zambrow.org)
      - 'adverts': Ogłoszenia (zambrow.org)
      - 'commercial': Firmy (zambrow.org)
      - 'news': Wiadomości (zambrow.org & zambrowiacy.pl)
      - 'cinema' / 'kino': Repertuar kina, filmy, zapowiedzi (kino.mokzambrow.pl)
      - 'events' / 'imprezy': Kalendarz imprez i wydarzeń kulturalnych (zambrow.org)
    """
    results = []
    
    # 1. zambrow.org
    if source in ("all", "zambrow-org"):
        if not section or section not in ("cinema", "kino", "filmy", "events", "imprezy", "wydarzenia"):
            url = f"{BASE_URL}/szukaj?q={urllib.parse.quote(query)}"
            if section and section != "all":
                sec_map = {
                    "forum": "forum",
                    "adverts": "adverts",
                    "ogloszenia": "adverts",
                    "firms": "commercial",
                    "firmy": "commercial",
                    "commercial": "commercial",
                    "news": "news",
                    "wiadomosci": "news"
                }
                wts = sec_map.get(section.lower(), section)
                url += f"&wts={wts}"
            
            try:
                content = fetch_url(url)
                sections = re.findall(r"<div class=[\x27\x22]search__results[\x27\x22]>(.*?)</ul>", content, re.DOTALL)
                for sec_html in sections:
                    header_m = re.search(r"<h2[^>]*>(.*?)</h2>", sec_html)
                    header = html.unescape(header_m.group(1).strip()) if header_m else "Wyniki zambrow.org"
                    
                    items = re.findall(r"<li class=[\x27\x22]search__item[\x27\x22]>(.*?)</li>", sec_html, re.DOTALL)
                    for item in items:
                        link_m = re.search(
                            r"<a href=[\x27\x22]([^\x27\x22]+)[\x27\x22][^>]*class=[\x27\x22]search__link[\x27\x22][^>]*>(.*?)</a>",
                            item, re.DOTALL
                        )
                        if not link_m:
                            continue
                        href = link_m.group(1)
                        inner = link_m.group(2)
                        
                        title_m = re.search(r"<h4[^>]*>(.*?)</h4>", inner, re.DOTALL)
                        title = clean_html_text(title_m.group(1)) if title_m else ""
                        
                        prev_m = re.search(r"<p class=[\x27\x22]search__prev[\x27\x22][^>]*>(.*?)</p>", inner, re.DOTALL)
                        snippet = clean_html_text(prev_m.group(1)) if prev_m else ""
                        
                        info_m = re.search(r"<div class=[\x27\x22]search__info[\x27\x22][^>]*>(.*?)</div>", item, re.DOTALL)
                        info = clean_html_text(info_m.group(1)) if info_m else ""
                        
                        full_url = urllib.parse.urljoin(BASE_URL, href)
                        
                        item_type = "unknown"
                        if "/post/" in href:
                            item_type = "forum"
                        elif "/oferta/" in href or "/ogloszenie/" in href:
                            item_type = "ad"
                        elif "/firma/" in href:
                            item_type = "firm"
                        elif "/artykul/" in href:
                            item_type = "news"
                        
                        results.append({
                            "source": "zambrow.org",
                            "section": header,
                            "type": item_type,
                            "title": title,
                            "url": full_url,
                            "info": info,
                            "snippet": snippet
                        })
            except Exception:
                pass

    # 2. zambrowiacy.pl (news only)
    if source in ("all", "zambrowiacy"):
        if not section or section in ("all", "news", "wiadomosci"):
            z_items = search_zambrowiacy(query)
            results.extend(z_items)

    # 3. kino.mokzambrow.pl (cinema movies, schedule, pricing)
    if source in ("all", "cinema", "kino") or section in ("cinema", "kino", "filmy"):
        try:
            k_query = query.strip()
            
            # Match cinema general info
            if any(k in k_query.lower() for k in ("kino", "cennik", "bilet", "kasa", "sala", "film")):
                info = get_cinema_info()
                results.append({
                    "source": "kino.mokzambrow.pl",
                    "section": "Kino Zambrów",
                    "type": "cinema_info",
                    "title": info["name"] + " — Cennik, Kasa, Informacje",
                    "url": f"{KINO_BASE_URL}/kino/",
                    "info": f"Kasa: {info['box_office_hours']} | Tel: {info['phone']} | Ceny 2D: 20/16 zł, 3D: 26/23 zł",
                    "snippet": f"Adres: {info['address']}. Zakup biletów online: {info['booking_url']}"
                })
            
            # Search movie posts via WP REST API
            q_enc = urllib.parse.quote(k_query)
            search_posts = fetch_kino_json(f"posts?search={q_enc}&_embed&per_page=10")
            for sp in search_posts:
                if sp.get("id") == 395:
                    continue
                m_det = parse_movie_post(sp)
                status_label = "Teraz gramy" if m_det["status"] == "gramy" else "Zapowiedź"
                info_parts = [f"Status: {status_label}"]
                if m_det.get("genre"): info_parts.append(m_det["genre"])
                if m_det.get("runtime"): info_parts.append(m_det["runtime"])
                if m_det.get("date_range"): info_parts.append(f"Termin: {m_det['date_range']}")
                
                results.append({
                    "source": "kino.mokzambrow.pl",
                    "section": "Kino Zambrów",
                    "type": "cinema_movie",
                    "title": f"{m_det['title']} ({status_label})",
                    "url": m_det["url"],
                    "info": " | ".join(info_parts),
                    "snippet": m_det.get("synopsis", "")[:250] + ("..." if len(m_det.get("synopsis", "")) > 250 else ""),
                    "lead": m_det.get("synopsis", "")
                })
        except Exception:
            pass
            
    # 4. Events / Imprezy (zambrow.org/wydarzenia-imprezy)
    if source in ("all", "zambrow-org") and (not section or section in ("all", "events", "imprezy", "wydarzenia")):
        try:
            evs = scrape_events()
            q_lower = query.strip().lower()
            for ev in evs:
                target_str = (ev.get("title", "") + " " + ev.get("location", "") + " " + ev.get("description", "") + " " + ev.get("category", "")).lower()
                if q_lower in target_str or not q_lower or section in ("events", "imprezy", "wydarzenia"):
                    results.append({
                        "source": "zambrow.org",
                        "section": "Wydarzenia i Imprezy",
                        "type": "event",
                        "title": f"📅 {ev['date']} | {ev['title']} ({ev['category']})",
                        "url": ev["url"],
                        "info": f"Czas: {ev.get('time', '')} | Miejsce: {ev.get('location', '')}",
                        "snippet": ev.get("description", "")[:250],
                        "lead": ev.get("description", "")
                    })
        except Exception:
            pass

    return results

def extract_phones(text: str) -> List[str]:
    """Finds mobile and landline Polish phone numbers."""
    matches = re.findall(
        r"(?:(?:\+|00)?48[\s-]?)?(?:[1-9]\d{2}[-\s]?\d{3}[-\s]?\d{3}|[1-9]\d[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})",
        text
    )
    res = []
    for m in matches:
        digits = re.sub(r"\D", "", m)
        if len(digits) == 9 or (len(digits) == 11 and digits.startswith("48")):
            formatted = digits[-9:]
            formatted = f"{formatted[:3]} {formatted[3:6]} {formatted[6:]}"
            if formatted not in res:
                res.append(formatted)
    return res

def extract_emails(text: str) -> List[str]:
    """Finds email addresses in text."""
    matches = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    res = []
    for m in matches:
        m_lower = m.lower()
        if m_lower not in res and not m_lower.endswith(".png") and not m_lower.endswith(".jpg"):
            res.append(m_lower)
    return res

def parse_forum_post(url: str, content: str) -> Dict[str, Any]:
    """Parses a forum thread on zambrow.org."""
    title_m = re.search(r"<h1 class=[\x27\x22]page__title[\x27\x22][^>]*>(.*?)</h1>", content)
    title = clean_html_text(title_m.group(1)) if title_m else ""
    
    comments = []
    blocks = re.findall(r"<div class=[\x27\x22]comment__content[\x27\x22]>(.*?)</div>\s*</div>", content, re.DOTALL)
    for b in blocks:
        author_m = re.search(r"<span class=[\x27\x22]comment__author[\x27\x22][^>]*>(.*?)</span>", b, re.DOTALL)
        author = clean_html_text(author_m.group(1)) if author_m else ""
        date_m = re.search(r"<span class=[\x27\x22]comment__date[\x27\x22][^>]*>(.*?)</span>", b, re.DOTALL)
        date = clean_html_text(date_m.group(1)) if date_m else ""
        text_m = re.search(r"<p class=[\x27\x22]comment__contents[\x27\x22][^>]*>(.*?)</p>", b, re.DOTALL)
        text = clean_html_text(text_m.group(1)) if text_m else ""
        
        comments.append({
            "author": author,
            "date": date,
            "text": text,
            "phones": extract_phones(text),
            "emails": extract_emails(text)
        })
        
    all_phones = []
    all_emails = []
    for c in comments:
        for p in c["phones"]:
            if p not in all_phones: all_phones.append(p)
        for e in c["emails"]:
            if e not in all_emails: all_emails.append(e)
            
    return {
        "type": "forum",
        "title": title,
        "url": url,
        "comments_count": len(comments),
        "phones": all_phones,
        "emails": all_emails,
        "comments": comments
    }

def parse_ad_offer(url: str, content: str) -> Dict[str, Any]:
    """Parses a classified offer (/oferta/... or /ogloszenie/...)."""
    title_m = re.search(r"<h1[^>]*class=[\x27\x22]announ__title[\x27\x22][^>]*>(.*?)</h1>", content, re.DOTALL)
    if not title_m:
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
    title = clean_html_text(title_m.group(1)) if title_m else ""
    
    phone_m = re.search(r"phoneNumber\s*=\s*[\x27\x22]([^\x27\x22]+)[\x27\x22]", content)
    phone = phone_m.group(1).strip() if phone_m else ""
    
    email_m = re.search(r"emailNumber\s*=\s*[\x27\x22]([^\x27\x22]+)[\x27\x22]", content)
    email = email_m.group(1).strip() if email_m else ""
    
    date_m = re.search(r"<span class=[\x27\x22]announ__date[\x27\x22][^>]*>(.*?)</span>", content, re.DOTALL)
    date_val = clean_html_text(date_m.group(1)) if date_m else ""
    
    id_m = re.search(r"<span class=[\x27\x22]announ__id[\x27\x22][^>]*>(.*?)</span>", content, re.DOTALL)
    id_val = clean_html_text(id_m.group(1)) if id_m else ""
    
    addr_m = re.search(r"<p class=[\x27\x22]announ__contact-data[\x27\x22][^>]*>(.*?)</p>", content, re.DOTALL)
    address = clean_html_text(addr_m.group(1)) if addr_m else ""
    
    price = ""
    price_tag_m = re.search(r"<span class=[\x27\x22]announ__price-tag[\x27\x22][^>]*>(.*?)</span>", content, re.DOTALL)
    if price_tag_m:
        price = clean_html_text(price_tag_m.group(1))
    else:
        price_m = re.search(r"<div class=[\x27\x22]announ__price[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
        if price_m:
            price = clean_html_text(price_m.group(1))

    params = []
    param_matches = re.findall(r"<div class=[\x27\x22]announ__parameter[^\x27\x22]*[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
    for pm in param_matches:
        p_clean = clean_html_text(pm)
        if p_clean and p_clean not in params:
            params.append(p_clean)

    desc = ""
    descr_m = re.search(r"<div class=[\x27\x22]announ__descr[^\x27\x22]*[\x27\x22][^>]*>(.*?)(?:<div class=[\x27\x22]button-block|\Z)", content, re.DOTALL)
    if descr_m:
        raw_desc = descr_m.group(1)
        raw_desc = re.sub(r"<div class=[\x27\x22]section__header[\x27\x22][^>]*>.*?</div>", "", raw_desc, flags=re.DOTALL)
        raw_desc = re.sub(r"<br\s*/?>", "\n", raw_desc, flags=re.IGNORECASE)
        raw_desc = re.sub(r"</p>", "\n\n", raw_desc, flags=re.IGNORECASE)
        clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
        clean_desc = html.unescape(clean_desc)
        desc = "\n".join(" ".join(line.split()) for line in clean_desc.split("\n") if line.strip())

    if not desc:
        desc_m = re.search(r"<div class=[\x27\x22]announ__text[^\x27\x22]*[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
        if desc_m:
            desc = clean_html_text(desc_m.group(1))

    if not desc:
        scripts = re.findall(r"<script type=[\x27\x22]application/ld\+json[\x27\x22]>(.*?)</script>", content, re.DOTALL)
        for s in scripts:
            try:
                d = json.loads(s.strip())
                if "description" in d and d["description"]:
                    desc = d["description"]
                    break
            except Exception:
                pass

    photos = []
    seen_photos = set()
    photo_matches = re.findall(r"<img[^>]+src=[\x27\x22]([^\x27\x22]+)[\x27\x22][^>]*class=[\x27\x22][^\x27\x22]*announ__photo[^\x27\x22]*[\x27\x22]", content)
    if not photo_matches:
        photo_matches = re.findall(r"class=[\x27\x22][^\x27\x22]*announ__photo[^\x27\x22]*[\x27\x22][^>]*src=[\x27\x22]([^\x27\x22]+)[\x27\x22]", content)
    if not photo_matches:
        photo_matches = re.findall(r"<img[^>]+src=[\x27\x22](/static/files/ogloszenia/[^\x27\x22]+)[\x27\x22]", content)

    for p in photo_matches:
        p_clean = p.replace("/./", "/")
        if not p_clean.startswith("http"):
            p_full = urllib.parse.urljoin(BASE_URL, p_clean)
        else:
            p_full = p_clean
        if p_full not in seen_photos:
            seen_photos.add(p_full)
            photos.append(p_full)

    return {
        "type": "ad",
        "title": title,
        "phone": phone,
        "email": email,
        "date": date_val,
        "id": id_val,
        "price": price,
        "parameters": params,
        "address": address,
        "description": desc,
        "photos": photos,
        "url": url
    }

def parse_firm_page(url: str, content: str) -> Dict[str, Any]:
    """Parses a company page (/firma/...)."""
    title_m = re.search(r"<h1[^>]*class=[\x27\x22]announ__title[\x27\x22][^>]*>(.*?)</h1>", content, re.DOTALL)
    if not title_m:
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
    title = clean_html_text(title_m.group(1)) if title_m else ""
    
    phone_m = re.search(r"phoneNumber\s*=\s*[\x27\x22]([^\x27\x22]+)[\x27\x22]", content)
    phone = phone_m.group(1).strip() if phone_m else ""
    
    email_m = re.search(r"emailNumber\s*=\s*[\x27\x22]([^\x27\x22]+)[\x27\x22]", content)
    email = email_m.group(1).strip() if email_m else ""
    
    kw_m = re.search(r"<meta name=[\x27\x22]keywords[\x27\x22]\s+content=[\x27\x22](.*?)[\x27\x22]", content)
    keywords = kw_m.group(1) if kw_m else ""
    
    addr_m = re.search(r"<div class=[\x27\x22]announ__contact[^\x27\x22]*[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
    address = clean_html_text(addr_m.group(1)) if addr_m else ""
    if not address and keywords:
        address = keywords
        
    date_m = re.search(r"<span class=[\x27\x22]announ__date[\x27\x22][^>]*>(.*?)</span>", content, re.DOTALL)
    date_val = clean_html_text(date_m.group(1)) if date_m else ""
    
    desc_m = re.search(r"<div class=[\x27\x22]announ__description[^\x27\x22]*[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
    desc = clean_html_text(desc_m.group(1)) if desc_m else ""
    
    return {
        "type": "firm",
        "title": title,
        "phone": phone,
        "email": email,
        "date": date_val,
        "address": address,
        "description": desc,
        "url": url
    }

def parse_news_article(url: str, content: str) -> Dict[str, Any]:
    """Parses a news article page (/artykul/...) on zambrow.org."""
    ld = {}
    scripts = re.findall(r'<script type=[\x27\x22]application/ld\+json[\x27\x22]>(.*?)</script>', content, re.DOTALL)
    for s in scripts:
        try:
            d = json.loads(s.strip())
            if isinstance(d, dict) and d.get("@type") == "NewsArticle":
                ld = d
                break
        except Exception:
            pass

    headline = ld.get("headline") or ""
    if not headline:
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
        headline = clean_html_text(h1_m.group(1)) if h1_m else ""

    date_pub = ld.get("datePublished") or ""
    if not date_pub:
        m = re.search(r"<meta property=[\x27\x22]article:published_time[\x27\x22] content=[\x27\x22](.*?)[\x27\x22]", content)
        if m:
            date_pub = m.group(1)

    author = ""
    if isinstance(ld.get("author"), dict):
        author = ld["author"].get("name", "")
    elif isinstance(ld.get("author"), str):
        author = ld["author"]
    if not author:
        aut_m = re.search(r"<a[^>]*href=[\x27\x22]/autor/[^\x27\x22]+[\x27\x22][^>]*>(.*?)</a>", content, re.DOTALL)
        if aut_m:
            author = clean_html_text(aut_m.group(1))

    body = ld.get("articleBody") or ""
    if not body:
        text_m = re.search(r"<div class=[\x27\x22]announ__text[^\x27\x22]*[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
        if text_m:
            body = clean_html_text(text_m.group(1))
    
    # Clean ads and middle tags
    body = re.sub(r"\[middle\d+\]", "", body)
    body = re.sub(r"\s*Reklama\s*", "\n\n", body)
    body = "\n\n".join([p.strip() for p in body.split("\n\n") if p.strip()])

    og_m = re.search(r"<meta property=[\x27\x22]og:description[\x27\x22] content=[\x27\x22](.*?)[\x27\x22]", content)
    og_desc = og_m.group(1).strip() if og_m else ""

    lead = ld.get("description") or og_desc
    if not lead and body:
        lead = body.split(".")[0].strip() + "."

    sec_m = re.search(r"<meta property=[\x27\x22]article:section[\x27\x22] content=[\x27\x22](.*?)[\x27\x22]", content)
    tag_m = re.search(r"<meta property=[\x27\x22]article:tag[\x27\x22] content=[\x27\x22](.*?)[\x27\x22]", content)
    section = sec_m.group(1).strip() if sec_m else ""
    tag = tag_m.group(1).strip() if tag_m else ""
    cat = tag if tag else section

    image_url = ""
    if isinstance(ld.get("image"), dict):
        image_url = ld["image"].get("url", "")
    elif isinstance(ld.get("image"), str):
        image_url = ld["image"]
    if not image_url:
        img_m = re.search(r"<meta property=[\x27\x22]og:image[\x27\x22] content=[\x27\x22](.*?)[\x27\x22]", content)
        if img_m:
            image_url = img_m.group(1)

    return {
        "source": "zambrow.org",
        "type": "news",
        "title": headline,
        "headline": headline,
        "date": date_pub,
        "author": author,
        "category": cat,
        "section": section,
        "tag": tag,
        "lead": lead,
        "body": body,
        "image": image_url,
        "url": url,
        "phones": extract_phones(body),
        "emails": extract_emails(body)
    }

def parse_zambrowiacy_page(url: str, content: str) -> Dict[str, Any]:
    """Parses an article page from zambrowiacy.pl."""
    title_m = re.search(r"<h1[^>]*class=[\x27\x22][^'\"]*(?:entry-title|jeg_post_title)[^'\"]*[\x27\x22][^>]*>(.*?)</h1>", content, re.DOTALL)
    if not title_m:
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
    title = clean_html_text(title_m.group(1)) if title_m else ""
    
    time_m = re.search(r"<time[^>]*datetime=[\x27\x22]([^\x27\x22]+)[\x27\x22]", content)
    date_pub = time_m.group(1) if time_m else ""
    if not date_pub:
        date_text_m = re.search(r"<div class=[\x27\x22]jeg_meta_date[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
        if date_text_m:
            date_pub = clean_html_text(date_text_m.group(1))

    author_m = re.search(r"<div class=[\x27\x22]jeg_meta_author[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
    author = clean_html_text(author_m.group(1)) if author_m else ""
    author = re.sub(r"^by\s+", "", author, flags=re.I)
    if not author:
        author = "Redakcja"

    cat_m = re.search(r"<div class=[\x27\x22]jeg_meta_category[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
    category = clean_html_text(cat_m.group(1)) if cat_m else "Wiadomości"

    body = ""
    lead = ""
    body_m = re.search(r"<div[^>]*class=[\x27\x22][^'\"]*(?:content-inner|entry-content)[^'\"]*[\x27\x22][^>]*>(.*?)</div>\s*<div class=[\x27\x22]jeg_share_bottom", content, re.DOTALL)
    if not body_m:
        body_m = re.search(r"<div[^>]*class=[\x27\x22][^'\"]*(?:content-inner|entry-content)[^'\"]*[\x27\x22][^>]*>(.*?)</div>", content, re.DOTALL)
    
    if body_m:
        raw_body = body_m.group(1)
        raw_body = re.sub(r"<style[^>]*>.*?</style>", "", raw_body, flags=re.DOTALL)
        raw_body = re.sub(r"<script[^>]*>.*?</script>", "", raw_body, flags=re.DOTALL)
        raw_body = re.sub(r"<div class=[\x27\x22]jnews_inline_related_post.*?</div>", "", raw_body, flags=re.DOTALL)
        
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", raw_body, re.DOTALL)
        clean_paras = [clean_html_text(p) for p in paragraphs if clean_html_text(p)]
        if clean_paras:
            lead = clean_paras[0]
            body = "\n\n".join(clean_paras)
        else:
            body = clean_html_text(raw_body)
            lead = body[:300] + "..." if len(body) > 300 else body

    img_m = re.search(r'<meta property=[\x27\x22]og:image[\x27\x22] content=[\x27\x22]([^\x27\x22]+)[\x27\x22]', content)
    image_url = img_m.group(1) if img_m else ""

    return {
        "source": "zambrowiacy.pl",
        "type": "news",
        "title": title,
        "headline": title,
        "date": date_pub,
        "author": author,
        "category": category,
        "section": "Zambrowiacy.pl",
        "lead": lead,
        "body": body,
        "image": image_url,
        "url": url,
        "phones": extract_phones(body),
        "emails": extract_emails(body)
    }

def get_verdict(rate: float, count: int) -> str:
    """Returns a readable verdict on whether the movie is worth watching."""
    if count == 0 or rate == 0:
        return "Brak wystarczającej liczby ocen (świeża premiera / przedpremierowy)"
    if rate >= 7.5:
        return "Bardzo dobry — wysoko oceniany, zdecydowanie polecany! 🌟"
    elif rate >= 6.5:
        return "Dobry / solidny film — warto obejrzeć na seansie kinowym 👍"
    elif rate >= 5.5:
        return "Średni / poprawny — lekki seans dla fanów gatunku, opinie mieszane 🤔"
    else:
        return "Nisko oceniany — raczej słabe recenzje widzów ⚠️"

def fetch_movie_ratings(title: str, year: Optional[int] = None) -> Dict[str, Any]:
    """Queries Filmweb API and IMDb suggestion API to check movie score, reviews and verdict."""
    result: Dict[str, Any] = {
        "title": title,
        "filmweb": None,
        "imdb": None,
        "verdict": None
    }
    
    clean_title = re.sub(r"\s*[-–—]\s*\d+$", "", title).strip()
    clean_title = re.sub(r"\s*\(\d{4}\)$", "", clean_title).strip()
    
    cache_key = clean_title.lower()
    cached = get_cache("ratings", cache_key, max_age_seconds=86400 * 3) # 3 days
    if cached is not None:
        return cached
    
    # 1. Filmweb API
    try:
        q = urllib.parse.quote(clean_title)
        s_url = f"https://www.filmweb.pl/api/v1/live/search?query={q}"
        req = urllib.request.Request(s_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hits = [h for h in data.get("searchHits", []) if h.get("type") == "film"]
            if hits:
                top = hits[0]
                fid = top["id"]
                m_title = top.get("matchedTitle", clean_title)
                
                r_url = f"https://www.filmweb.pl/api/v1/film/{fid}/rating"
                r_req = urllib.request.Request(r_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(r_req, timeout=6) as r_resp:
                    r_data = json.loads(r_resp.read().decode("utf-8"))
                    rate = r_data.get("rate", 0.0)
                    count = r_data.get("count", 0)
                    want_to_see = r_data.get("countWantToSee", 0)
                    
                    year_val = None
                    try:
                        p_url = f"https://www.filmweb.pl/api/v1/film/{fid}/preview"
                        p_req = urllib.request.Request(p_url, headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(p_req, timeout=6) as p_resp:
                            p_data = json.loads(p_resp.read().decode("utf-8"))
                            year_val = p_data.get("year")
                    except Exception:
                        pass
                        
                    slug_title = re.sub(r"[^\w\s-]", "", m_title).strip().replace(" ", "-")
                    fw_url = f"https://www.filmweb.pl/film/{slug_title}-{year_val or ''}-{fid}".rstrip("-")
                    
                    result["filmweb"] = {
                        "id": fid,
                        "title": m_title,
                        "rating": round(rate, 1) if rate else None,
                        "votes_count": count,
                        "want_to_see": want_to_see,
                        "year": year_val,
                        "url": fw_url
                    }
                    if rate:
                        result["verdict"] = get_verdict(rate, count)
    except Exception:
        pass

    # 2. IMDb suggestion API
    try:
        q_imdb = urllib.parse.quote(clean_title.lower())
        imdb_url = f"https://v3.sg.media-imdb.com/suggestion/x/{q_imdb}.json"
        req_imdb = urllib.request.Request(imdb_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req_imdb, timeout=6) as resp_imdb:
            d_imdb = json.loads(resp_imdb.read().decode("utf-8")).get("d", [])
            movie_hits = [x for x in d_imdb if x.get("qid") in ("movie", "tvMovie", "tvMiniSeries")]
            top_imdb = movie_hits[0] if movie_hits else (d_imdb[0] if d_imdb else None)
            if top_imdb:
                imdb_id = top_imdb.get("id")
                result["imdb"] = {
                    "id": imdb_id,
                    "title": top_imdb.get("l"),
                    "year": top_imdb.get("y"),
                    "cast": top_imdb.get("s"),
                    "url": f"https://www.imdb.com/title/{imdb_id}/"
                }
    except Exception:
        pass

    if result.get("filmweb") or result.get("imdb"):
        set_cache("ratings", cache_key, result)

    return result

def parse_movie_post(post: Dict[str, Any], with_ratings: bool = False) -> Dict[str, Any]:
    """Parses a movie post from WP REST API into structured data."""
    title = html.unescape(post.get("title", {}).get("rendered", ""))
    link = post.get("link", "")
    slug = post.get("slug", "")
    categories = post.get("categories", [])
    
    cat_type = "gramy" if 4 in categories else ("zapowiedzi" if 3 in categories else "info")
    
    raw_excerpt = post.get("excerpt", {}).get("rendered", "")
    clean_lines = [html.unescape(line).strip() for line in re.sub(r'<[^>]+>', '\n', raw_excerpt).split('\n') if line.strip()]
    
    genre = ""
    age_limit = ""
    runtime = ""
    origin = ""
    date_range = ""
    
    for l in clean_lines:
        if "Minimalny wiek" in l:
            age_limit = re.sub(r"^Minimalny wiek\s*[-–—:]\s*", "", l, flags=re.I).strip()
        elif "Czas trwania" in l:
            runtime = re.sub(r"^Czas trwania\s*[-–—:]\s*", "", l, flags=re.I).strip()
        elif "Kraj i rok" in l:
            origin = re.sub(r"^Kraj i rok produkcji\s*[-–—:]\s*", "", l, flags=re.I).strip()
        elif re.match(r"^\d{2}\.\d{2}\s*[-–—]\s*\d{2}\.\d{2}", l):
            date_range = l.strip()
        elif not genre and not any(k in l for k in ("Minimalny", "Czas", "Kraj", "Wiek")):
            cleaned = re.sub(r"^Gatunek\s*[-–—:]\s*", "", l, flags=re.I).strip()
            genre = cleaned
            
    content = post.get("content", {}).get("rendered", "")
    
    synopsis = ""
    syn_m = re.search(r'<div class=[\x27\x22]wpb_text_column[^>]*>.*?<div class=[\x27\x22]wpb_wrapper[\x27\x22]>\s*<p>(.*?)</p>', content, re.DOTALL)
    if not syn_m:
        syn_m = re.search(r'\[vc_column_text\](.*?)\[/vc_column_text\]', content, re.DOTALL)
    if syn_m:
        synopsis = html.unescape(re.sub(r'<[^>]+>', ' ', syn_m.group(1))).strip()
        
    trailer_url = ""
    tr_m = re.search(r'link=[\x27\x22](https?://(?:www\.)?youtube\.com/[^\x27\x22]+)[\x27\x22]', content)
    if not tr_m:
        tr_m = re.search(r'(https?://(?:www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]+)', content)
    if tr_m:
        trailer_url = tr_m.group(1)
        
    poster_url = ""
    if "_embedded" in post and "wp:featuredmedia" in post["_embedded"]:
        f_media = post["_embedded"]["wp:featuredmedia"]
        if f_media and isinstance(f_media, list):
            poster_url = f_media[0].get("source_url", "")
            
    showtimes = []
    days_times = re.findall(
        r'text=[\x27\x22](\d{1,2}\s+[a-ząćęłńóśźż]+)[\x27\x22].*?text=[\x27\x22](\d{1,2}:\d{2})[\x27\x22]',
        content,
        re.DOTALL | re.IGNORECASE
    )
    for d, t in days_times:
        showtimes.append(f"{d}: {t}")
        
    res = {
        "id": post.get("id"),
        "title": title,
        "slug": slug,
        "url": link,
        "source": "kino.mokzambrow.pl",
        "type": "cinema_movie",
        "status": cat_type,
        "genre": genre,
        "age_limit": age_limit,
        "runtime": runtime,
        "origin": origin,
        "date_range": date_range,
        "synopsis": synopsis,
        "trailer": trailer_url,
        "poster": poster_url,
        "showtimes": showtimes,
        "booking_url": KINO_BOOKING_URL
    }
    if with_ratings:
        res["ratings"] = fetch_movie_ratings(title)
    return res

def get_cinema_calendar() -> Dict[str, List[Dict[str, Any]]]:
    """Fetches and parses the monthly calendar from the homepage MEC widget."""
    try:
        pages = fetch_kino_json("pages?include=8,1276")
    except Exception:
        pages = []
        
    html_content = ""
    for p in pages:
        c = p.get("content", {}).get("rendered", "")
        if "mec_daily_view_date_events" in c:
            html_content = c
            break

    if not html_content:
        try:
            html_content = fetch_url(f"{KINO_BASE_URL}/test-repertuaru/")
        except Exception:
            pass

    calendar: Dict[str, List[Dict[str, Any]]] = {}
    day_blocks = re.findall(
        r'<li[^>]*id=[\x27\x22]mec_daily_view_date_events1266_(\d{8})[\x27\x22][^>]*>(.*?)</li>',
        html_content,
        re.DOTALL
    )

    for day_id, day_html in day_blocks:
        date_iso = f"{day_id[:4]}-{day_id[4:6]}-{day_id[6:]}"
        calendar[date_iso] = []

        ld_scripts = re.findall(
            r'<script type=[\x27\x22]application/ld\+json[\x27\x22]>(.*?)</script>',
            day_html,
            re.DOTALL
        )
        for s in ld_scripts:
            try:
                data = json.loads(s.strip())
                raw_name = html.unescape(data.get("name", ""))
                time_part = ""
                title_part = raw_name
                m_time = re.match(r"^(\d{1,2}:\d{2})\s*[-–—]\s*(.*)$", raw_name)
                if m_time:
                    time_part = m_time.group(1)
                    title_part = m_time.group(2).strip()

                calendar[date_iso].append({
                    "time": time_part,
                    "title": title_part,
                    "url": data.get("url", ""),
                    "raw": raw_name,
                    "start_date": data.get("startDate", ""),
                    "end_date": data.get("endDate", ""),
                    "booking_url": KINO_BOOKING_URL
                })
            except Exception:
                pass

        calendar[date_iso].sort(key=lambda x: x["time"])

    return calendar

def get_cinema_movies(category: str = "all", with_ratings: bool = False) -> List[Dict[str, Any]]:
    """Lists currently playing or upcoming movies with metadata."""
    cat_param = ""
    if category == "gramy":
        cat_param = "&categories=4"
    elif category == "zapowiedzi":
        cat_param = "&categories=3"
    else:
        cat_param = "&categories=4,3"
        
    posts = fetch_kino_json(f"posts?per_page=50&_embed{cat_param}")
    movies = [parse_movie_post(p) for p in posts if p.get("id") != 395]

    if with_ratings:
        def attach_ratings(m):
            m["ratings"] = fetch_movie_ratings(m["title"])
            return m
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            movies = list(executor.map(attach_ratings, movies))

    return movies

def get_cinema_movie_details(identifier: str, with_ratings: bool = True) -> Optional[Dict[str, Any]]:
    """Finds movie by title, slug, or ID and returns complete card."""
    ident = identifier.strip().lower()
    
    # 1. Try slug
    try:
        posts = fetch_kino_json(f"posts?slug={urllib.parse.quote(ident)}&_embed")
        if posts and posts[0].get("id") != 395:
            return parse_movie_post(posts[0], with_ratings=with_ratings)
    except Exception:
        pass
        
    # 2. Try ID
    if ident.isdigit():
        try:
            p = fetch_kino_json(f"posts/{ident}?_embed")
            if p and p.get("id") != 395:
                return parse_movie_post(p, with_ratings=with_ratings)
        except Exception:
            pass
            
    # 3. Search by title
    try:
        posts = fetch_kino_json(f"posts?search={urllib.parse.quote(ident)}&_embed&per_page=10")
        for p in posts:
            if p.get("id") == 395:
                continue
            m = parse_movie_post(p, with_ratings=with_ratings)
            if ident in m["title"].lower() or ident in m["slug"].lower():
                return m
        if posts:
            return parse_movie_post(posts[0], with_ratings=with_ratings)
    except Exception:
        pass
        
    return None

def get_cinema_schedule(target_date: Optional[str] = None, days_ahead: int = 7) -> Dict[str, Any]:
    """Returns cinema schedule for a specific date or a date range starting today."""
    cal = get_cinema_calendar()
    today_dt = datetime.date.today()
    today_str = today_dt.strftime("%Y-%m-%d")
    
    if target_date:
        t_clean = target_date.lower().strip()
        if t_clean in ("today", "dzis", "dzisiaj"):
            req_date = today_str
        elif t_clean in ("tomorrow", "jutro"):
            req_date = (today_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            req_date = t_clean
            
        events = cal.get(req_date, [])
        return {
            "mode": "single_day",
            "date": req_date,
            "events": events
        }
    else:
        all_dates = sorted(cal.keys())
        upcoming = {}
        end_dt = today_dt + datetime.timedelta(days=days_ahead)
        
        for d_str in all_dates:
            try:
                parts = [int(p) for p in d_str.split("-")]
                d = datetime.date(parts[0], parts[1], parts[2])
                if today_dt <= d <= end_dt:
                    upcoming[d_str] = cal[d_str]
            except Exception:
                pass
                
        return {
            "mode": "schedule",
            "start_date": today_str,
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "schedule": upcoming
        }

def parse_kino_page(url: str, content: str) -> Dict[str, Any]:
    """Parses any URL from kino.mokzambrow.pl."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.strip("/")
    slug = path.split("/")[-1] if path else ""

    if slug in ("kino", "info", "cennik") or path in ("kino", "info", "cennik"):
        return get_cinema_info()

    if slug in ("calendar", "test-repertuaru", ""):
        return {
            "source": "kino.mokzambrow.pl",
            "type": "cinema_calendar",
            "title": "Kalendarium Kina Zambrów",
            "url": url,
            "calendar": get_cinema_calendar(),
            "booking_url": KINO_BOOKING_URL
        }

    m = get_cinema_movie_details(slug)
    if m:
        return m
        
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
    title = clean_html_text(title_m.group(1)) if title_m else slug
    return {
        "source": "kino.mokzambrow.pl",
        "type": "cinema_generic",
        "title": title,
        "url": url,
        "phones": extract_phones(content),
        "booking_url": KINO_BOOKING_URL
    }

def get_page_details(url: str) -> Dict[str, Any]:
    """Extracts structured details from a forum post, classified ad, company page, news article, cinema page, or events calendar."""
    is_article = "/artykul/" in url or "/firma/" in url
    if is_article:
        cached = get_cache("pages", url, max_age_seconds=86400 * 7)
        if cached is not None:
            return cached

    content = fetch_url(url)
    
    if "kino.mokzambrow.pl" in url:
        res = parse_kino_page(url, content)
    elif "wydarzenia-imprezy" in url or "/imprezy" in url:
        res = {
            "source": "zambrow.org",
            "type": "events_calendar",
            "title": "Kalendarium wydarzeń i imprez w Zambrowie i okolicach",
            "url": url,
            "events": scrape_events()
        }
    elif "zambrowiacy.pl" in url:
        res = parse_zambrowiacy_page(url, content)
    elif "/post/" in url:
        res = parse_forum_post(url, content)
    elif "/oferta/" in url or "/ogloszenie/" in url:
        res = parse_ad_offer(url, content)
    elif "/firma/" in url:
        res = parse_firm_page(url, content)
    elif "/artykul/" in url:
        res = parse_news_article(url, content)
    else:
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
        title = clean_html_text(title_m.group(1)) if title_m else ""
        res = {
            "type": "generic",
            "url": url,
            "title": title,
            "phones": extract_phones(content),
            "emails": extract_emails(content)
        }

    if is_article and res:
        set_cache("pages", url, res)
    return res

def parse_date(date_str: str) -> Optional[datetime.datetime]:
    """Parses ISO date string, YYYY/MM/DD, YYYY-MM-DD, or RFC 2822 (RSS) to UTC datetime."""
    if not date_str:
        return None
    try:
        if any(day in date_str for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")) or "GMT" in date_str or "+" in date_str[-5:] or "-" in date_str[-5:]:
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                return dt.astimezone(datetime.timezone.utc)
            except Exception:
                pass

        clean_d = date_str.replace("Z", "+00:00")
        if "T" in clean_d:
            dt = datetime.datetime.fromisoformat(clean_d)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        elif "/" in clean_d:
            parts = clean_d.split("/")
            return datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=datetime.timezone.utc)
        elif "-" in clean_d:
            parts = clean_d.split(" ")[0].split("-")
            if len(parts) == 3:
                return datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=datetime.timezone.utc)
    except Exception:
        pass
    return None

def scrape_events(
    days: Optional[int] = None,
    month: Optional[int] = None,
    with_details: bool = False
) -> List[Dict[str, Any]]:
    """
    Scrapes upcoming municipal and regional events from zambrow.org/wydarzenia-imprezy.
    Returns list of dicts:
      - title
      - date (YYYY-MM-DD)
      - badge (e.g. 'PAŹ 15')
      - time (e.g. '17:00')
      - location (e.g. 'Centrum Kultury Gminy Zambrów')
      - category (e.g. 'Koncert / Muzyka', 'Warsztaty / Edukacja', 'Wystawa / Wernisaż')
      - description (snippet)
      - url (link to full article / event details)
      - image (thumbnail url)
      - days_away (number of days relative to today)
      - phones / emails / full_body (if with_details is True)
    """
    content = fetch_url(EVENTS_URL)
    items = re.findall(r"<div class=[\x27\x22]calendar[\x27\x22]>(.*?)</div>\s*</div>\s*</li>", content, re.DOTALL)
    
    events = []
    now = datetime.datetime.now()
    today = now.date()
    
    for it in items:
        # 1. Parse date badge
        m_sheet = re.search(r"<div class=[\x27\x22]calendar__sheet[\x27\x22][^>]*>(.*?)</div>", it, re.DOTALL)
        date_iso = ""
        badge_text = ""
        ev_date = None
        if m_sheet:
            raw_sheet = m_sheet.group(1)
            m_parts = re.search(r"([A-Za-zŻŁĆĄĘÓŃŚŹżłćąęóńśź]+).*?>(\d+)<", raw_sheet)
            if m_parts:
                m_code = m_parts.group(1).strip().lower()[:3]
                day_num = int(m_parts.group(2))
                m_idx = MONTH_MAP.get(m_code, now.month)
                year = now.year
                if m_idx < now.month - 1:
                    year += 1
                try:
                    ev_date = datetime.date(year, m_idx, day_num)
                    date_iso = ev_date.strftime("%Y-%m-%d")
                except ValueError:
                    date_iso = f"{year:04d}-{m_idx:02d}-{day_num:02d}"
                badge_text = f"{m_parts.group(1).strip()} {day_num}"
                
        # 2. Parse link
        m_link = re.search(r"<a href=[\x27\x22]([^\x27\x22]+)[\x27\x22][^>]*class=[\x27\x22]card__link[\x27\x22][^>]*>(.*?)</a>", it, re.DOTALL)
        href = urllib.parse.urljoin(BASE_URL, m_link.group(1).strip()) if m_link else ""
        
        # 3. Parse title
        m_name = re.search(r"<h4 class=[\x27\x22]calendar__event-name[\x27\x22][^>]*>(.*?)</h4>", it, re.DOTALL)
        name = clean_html_text(m_name.group(1)) if m_name else ""
        
        # 4. Parse time & location
        m_data = re.search(r"<span class=[\x27\x22]calendar__event-data[\x27\x22][^>]*>(.*?)</span>", it, re.DOTALL)
        event_data = clean_html_text(m_data.group(1)) if m_data else ""
        
        time_str = ""
        place_str = ""
        if "Godzina:" in event_data:
            parts = event_data.split("/")
            for p in parts:
                p = p.strip()
                if p.startswith("Godzina:"):
                    time_str = p.replace("Godzina:", "").strip()
                elif p.startswith("Miejsce:"):
                    place_str = p.replace("Miejsce:", "").strip()
                else:
                    if not place_str and p:
                        place_str = p
        elif event_data:
            place_str = event_data

        # 5. Parse description
        m_descr = re.search(r"<p class=[\x27\x22]calendar__descr[\x27\x22][^>]*>(.*?)</p>", it, re.DOTALL)
        descr = clean_html_text(m_descr.group(1)) if m_descr else ""
        
        # 6. Parse image
        m_img = re.search(r"<img[^>]*src=[\x27\x22]([^\x27\x22]+)[\x27\x22]", it, re.DOTALL)
        img_url = urllib.parse.urljoin(BASE_URL, m_img.group(1).strip()) if m_img else ""
        
        # 7. Category classification
        name_lower = name.lower()
        descr_lower = descr.lower()
        if "wernisaż" in name_lower or "wystaw" in name_lower or "malar" in name_lower:
            cat = "Wystawa / Wernisaż"
        elif "koncert" in name_lower or "recital" in name_lower or "chopin" in name_lower or "muzyk" in name_lower:
            cat = "Koncert / Muzyka"
        elif "spotka" in name_lower or "pisark" in name_lower or "autor" in name_lower or "książk" in name_lower:
            cat = "Spotkanie autorskie"
        elif "warsztat" in name_lower or "szkolenie" in name_lower or "kurs" in name_lower:
            cat = "Warsztaty / Edukacja"
        elif "mecz" in name_lower or "turniej" in name_lower or "sport" in name_lower or "bieg" in name_lower:
            cat = "Sport"
        elif "wernisaż" in descr_lower or "wystaw" in descr_lower:
            cat = "Wystawa / Wernisaż"
        elif "koncert" in descr_lower or "muzyk" in descr_lower:
            cat = "Koncert / Muzyka"
        elif "warsztat" in descr_lower or "szkolenie" in descr_lower:
            cat = "Warsztaty / Edukacja"
        else:
            cat = "Wydarzenie kulturalne"

        days_away = (ev_date - today).days if ev_date else None
        
        # Filters
        if days is not None and days_away is not None:
            if days_away < 0 or days_away > days:
                continue
                
        if month is not None and ev_date is not None:
            if ev_date.month != month:
                continue

        event_obj = {
            "source": "zambrow.org",
            "type": "event",
            "title": name,
            "date": date_iso,
            "badge": badge_text,
            "time": time_str,
            "location": place_str,
            "category": cat,
            "description": descr,
            "url": href,
            "image": img_url,
            "days_away": days_away
        }
        
        if with_details and href:
            try:
                art = parse_news_article(href, fetch_url(href))
                if art.get("body"):
                    event_obj["full_body"] = art["body"]
                if art.get("phones"):
                    event_obj["phones"] = art["phones"]
                if art.get("emails"):
                    event_obj["emails"] = art["emails"]
            except Exception:
                pass
                
        events.append(event_obj)
        
    return events

def scrape_zambrowiacy_news(
    days: int = 14,
    limit: int = 50,
    category: Optional[str] = None,
    with_lead: bool = True,
    with_full: bool = False
) -> List[Dict[str, Any]]:
    """Scrapes news from zambrowiacy.pl via RSS feeds."""
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=days)
    
    namespaces = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/"
    }
    
    articles = []
    seen_urls = set()
    page = 1
    max_pages = 10
    stop_paging = False
    
    cat_query = category.lower().strip() if category else None
    
    while page <= max_pages and not stop_paging and len(articles) < limit:
        feed_url = f"{ZAMBROWIACY_BASE_URL}/feed/" if page == 1 else f"{ZAMBROWIACY_BASE_URL}/feed/?paged={page}"
        try:
            feed_xml = fetch_url(feed_url)
            root = ET.fromstring(feed_xml)
            channel = root.find("channel")
            if channel is None:
                break
            items = channel.findall("item")
            if not items:
                break
            
            for it in items:
                link = (it.find("link").text or "").strip()
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)
                
                pub_date_str = it.find("pubDate").text if it.find("pubDate") is not None else ""
                pub_dt = parse_date(pub_date_str)
                if pub_dt and pub_dt < cutoff:
                    stop_paging = True
                    break
                    
                categories = [clean_html_text(c.text) for c in it.findall("category") if c.text]
                cat_str = ", ".join(categories) if categories else "Wiadomości"
                
                if cat_query:
                    if not any(cat_query in c.lower() for c in categories):
                        continue
                
                title = clean_html_text(it.find("title").text or "") if it.find("title") is not None else ""
                creator = it.find("dc:creator", namespaces)
                author = clean_html_text(creator.text) if creator is not None and creator.text else "Redakcja"
                
                desc_el = it.find("description")
                clean_desc = clean_html_text(desc_el.text or "") if desc_el is not None else ""
                clean_desc = re.sub(r"\[\s*&#8230;\s*\]", "...", clean_desc)
                clean_desc = re.sub(r"\[\s*\.\.\.\s*\]", "...", clean_desc)
                
                full_body = ""
                if with_full:
                    content_el = it.find("content:encoded", namespaces)
                    if content_el is not None and content_el.text:
                        full_body = clean_html_text(content_el.text)
                
                date_iso = pub_dt.strftime("%Y-%m-%d %H:%M") if pub_dt else pub_date_str
                
                art = {
                    "source": "zambrowiacy.pl",
                    "type": "news",
                    "title": title,
                    "headline": title,
                    "date": date_iso,
                    "author": author,
                    "category": cat_str,
                    "section": "Zambrowiacy.pl",
                    "url": link,
                    "phones": extract_phones(full_body or clean_desc),
                    "emails": extract_emails(full_body or clean_desc)
                }
                if with_lead:
                    art["lead"] = clean_desc
                if with_full:
                    art["body"] = full_body
                    
                articles.append(art)
                if len(articles) >= limit:
                    break
        except Exception:
            break
        page += 1
        
    return articles

def scrape_zambrow_org_news(
    days: int = 14,
    limit: int = 50,
    category: Optional[str] = None,
    with_lead: bool = True,
    with_full: bool = False,
    workers: int = 8
) -> List[Dict[str, Any]]:
    """Crawls news from zambrow.org."""
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    
    seen_urls = set()
    matching_cards = []

    def extract_cards_from_html(html_content: str) -> List[Dict[str, str]]:
        cards = []
        blocks = re.findall(r'<div class=[\x27\x22]news-card[\x27\x22]>(.*?)</div>\s*</div>\s*</div>', html_content, re.DOTALL)
        for b in blocks:
            u_m = re.search(r'href=[\x27\x22](/artykul/[^#\x27\x22]+)[\x27\x22]', b)
            t_m = re.search(r'<h[34][^>]*class=[\x27\x22]news-card__title[\x27\x22][^>]*>(.*?)</h[34]>', b, re.DOTALL)
            if not t_m:
                t_m = re.search(r'<h[34][^>]*>(.*?)</h[34]>', b, re.DOTALL)
            d_m = re.search(r'<div class=[\x27\x22]news-card__date[\x27\x22]>\s*(\d{4}/\d{2}/\d{2})\s*</div>', b)
            cat_m = re.search(r'<div class=[\x27\x22]news-card__category[\x27\x22]>(.*?)</div>', b, re.DOTALL)
            
            date_val = ""
            if d_m:
                date_val = d_m.group(1).replace("/", "-")
            elif "label--today" in b:
                date_val = now.strftime("%Y-%m-%d")
            elif "label--yesterday" in b:
                date_val = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                
            if u_m and t_m:
                url = urllib.parse.urljoin(BASE_URL, u_m.group(1))
                title = clean_html_text(t_m.group(1))
                cat = clean_html_text(cat_m.group(1)) if cat_m else ""
                cards.append({
                    "url": url,
                    "title": title,
                    "date": date_val,
                    "category": cat
                })
        return cards

    # Homepage
    try:
        home_html = fetch_url(BASE_URL)
        for c in extract_cards_from_html(home_html):
            if c["url"] not in seen_urls:
                seen_urls.add(c["url"])
                if not c["date"] or c["date"] >= cutoff_str:
                    matching_cards.append(c)
    except Exception:
        pass

    # Paginated /aktualnosci/
    page = 1
    max_pages = 20
    stop_paging = False
    while page <= max_pages and not stop_paging:
        p_url = f"{BASE_URL}/aktualnosci/" if page == 1 else f"{BASE_URL}/aktualnosci/strona{page}"
        try:
            p_html = fetch_url(p_url)
            p_cards = extract_cards_from_html(p_html)
            if not p_cards:
                break
                
            for c in p_cards:
                if c["url"] not in seen_urls:
                    seen_urls.add(c["url"])
                    if c["date"] and c["date"] < cutoff_str:
                        stop_paging = True
                        break
                    matching_cards.append(c)
        except Exception:
            break
        page += 1

    if category:
        cat_query = category.lower().strip()
        matching_cards = [c for c in matching_cards if cat_query in c.get("category", "").lower()]

    target_cards = matching_cards[:limit]

    if not with_lead and not with_full:
        for c in target_cards:
            c["source"] = "zambrow.org"
            c["type"] = "news"
        return target_cards

    def fetch_details(c: Dict[str, str]) -> Dict[str, Any]:
        try:
            det = get_page_details(c["url"])
            if not with_full:
                det.pop("body", None)
            if not with_lead:
                det.pop("lead", None)
            return det
        except Exception:
            return {
                "source": "zambrow.org",
                "type": "news",
                "url": c["url"],
                "title": c["title"],
                "date": c["date"],
                "category": c["category"]
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        raw_results = list(executor.map(fetch_details, target_cards))

    results = []
    for art in raw_results:
        art_dt = parse_date(art.get("date", ""))
        if art_dt and art_dt < cutoff:
            continue
        results.append(art)

    def sort_key(a):
        dt = parse_date(a.get("date", ""))
        return dt.timestamp() if dt else 0

    results.sort(key=sort_key, reverse=True)
    return results[:limit]

def scrape_news(
    days: int = 14,
    limit: int = 50,
    category: Optional[str] = None,
    source: str = "all",
    with_lead: bool = True,
    with_full: bool = False,
    workers: int = 8
) -> List[Dict[str, Any]]:
    """Crawls news from zambrow.org and/or zambrowiacy.pl."""
    results = []
    
    if source in ("all", "zambrow-org"):
        org_arts = scrape_zambrow_org_news(
            days=days,
            limit=limit,
            category=category,
            with_lead=with_lead,
            with_full=with_full,
            workers=workers
        )
        results.extend(org_arts)
        
    if source in ("all", "zambrowiacy"):
        zamb_arts = scrape_zambrowiacy_news(
            days=days,
            limit=limit,
            category=category,
            with_lead=with_lead,
            with_full=with_full
        )
        results.extend(zamb_arts)
        
    def sort_key(a):
        dt = parse_date(a.get("date", ""))
        return dt.timestamp() if dt else 0

    results.sort(key=sort_key, reverse=True)
    return results[:limit]

def browse_category(path: str) -> List[Dict[str, Any]]:
    """Browses a section URL on zambrow.org (classifieds, forum, firms)."""
    if not path.startswith("http"):
        path = path.lstrip("/")
        url = f"{BASE_URL}/{path}"
    else:
        url = path
        
    content = fetch_url(url)
    results = []
    seen = set()
    
    # 1. Structured classified items (li.classified__item)
    classified_blocks = re.findall(r"<li class=[\x27\x22][^\x27\x22]*classified__item[^\x27\x22]*[\x27\x22][^>]*>(.*?)</li>", content, re.DOTALL)
    for block in classified_blocks:
        url_m = re.search(r"href=[\x27\x22](/oferta/[^\x27\x22]+)[\x27\x22]", block)
        if not url_m:
            url_m = re.search(r"itemprop=[\x27\x22]url[\x27\x22]\s+content=[\x27\x22]([^\x27\x22]+)[\x27\x22]", block)
        if not url_m: continue
        item_url = url_m.group(1)
        if not item_url.startswith("http"): item_url = urllib.parse.urljoin(BASE_URL, item_url)
        if item_url in seen: continue
        seen.add(item_url)
        
        title = ""
        title_m = re.search(r"<h3 class=[\x27\x22]classified__title[\x27\x22][^>]*>(.*?)</h3>", block, re.DOTALL)
        if title_m:
            title = clean_html_text(title_m.group(1))
        else:
            title_attr = re.search(r"title=[\x27\x22]([^\x27\x22]+)[\x27\x22]", block)
            if title_attr:
                title = clean_html_text(title_attr.group(1).split(" | Zambrow.org")[0].split(" - ogłoszenia")[0])
        if not title:
            slug = item_url.split("/")[-1]
            title = re.sub(r"-m\d+$", "", slug).replace("-", " ").capitalize()

        price = ""
        price_m = re.search(r"<div class=[\x27\x22]classified__price[\x27\x22][^>]*>(.*?)</div>", block, re.DOTALL)
        if price_m:
            price = clean_html_text(price_m.group(1))
            
        filters = [clean_html_text(f).strip(" |") for f in re.findall(r"<span class=[\x27\x22]classified__filter[\x27\x22][^>]*>(.*?)</span>", block, re.DOTALL)]
        filters = [f for f in filters if f]
        
        thumb_m = re.search(r"<img[^>]+src=[\x27\x22]([^\x27\x22]+)[\x27\x22]", block)
        thumb = thumb_m.group(1) if thumb_m else ""
        if thumb and not thumb.startswith("http"):
            thumb = urllib.parse.urljoin(BASE_URL, thumb.replace("/./", "/"))
            
        results.append({
            "title": title,
            "url": item_url,
            "price": price,
            "tags": filters,
            "thumbnail": thumb,
            "type": "ad"
        })

    # 2. Structured forum entries (li.forum__entry)
    forum_blocks = re.findall(r"<li class=[\x27\x22]forum__entry[\x27\x22][^>]*>(.*?)</li>", content, re.DOTALL)
    for row in forum_blocks:
        link_m = re.search(r"<a href=[\x27\x22](/post/[^\x27\x22]+)[\x27\x22][^>]*>(.*?)</a>", row, re.DOTALL)
        if not link_m: continue
        t_url = urllib.parse.urljoin(BASE_URL, link_m.group(1))
        if t_url in seen: continue
        seen.add(t_url)
        t_title = clean_html_text(link_m.group(2))
        
        meta_m = re.search(r"<span>(\d{2}/\d{2}/\d{4}),\s*autor:\s*([^<]+)</span>", row)
        date_str = meta_m.group(1) if meta_m else ""
        author_str = meta_m.group(2).strip() if meta_m else ""
        
        reply_m = re.search(r"<div class=[\x27\x22]forum__entry-reply[\x27\x22][^>]*>\s*([0-9-:\s]+)<br\s*/?>\s*([^<]+)</div>", row)
        last_reply_date = reply_m.group(1).strip() if reply_m else ""
        last_reply_user = reply_m.group(2).strip() if reply_m else ""
        
        comm_m = re.search(r"<div class=[\x27\x22]forum__entry-comments[\x27\x22][^>]*>.*?(\d+)\s*</div>", row, re.DOTALL)
        comments_count = int(comm_m.group(1)) if comm_m else 0
        
        results.append({
            "title": t_title,
            "url": t_url,
            "date": date_str,
            "author": author_str,
            "last_reply": f"{last_reply_date} ({last_reply_user})" if last_reply_date else "",
            "comments_count": comments_count,
            "type": "forum"
        })

    # 3. Fallback for offers not in classified__item
    offers = re.findall(r"<a href=[\x27\x22](/oferta/[^\x27\x22]+)[\x27\x22]", content)
    for o in offers:
        full_url = urllib.parse.urljoin(BASE_URL, o)
        if full_url in seen: continue
        seen.add(full_url)
        slug = o.split("/")[-1]
        title_slug = re.sub(r"-m\d+$", "", slug).replace("-", " ").capitalize()
        results.append({
            "title": title_slug,
            "url": full_url,
            "type": "ad"
        })
        
    # 4. Companies (/firma/...)
    firms = re.findall(r"<a href=[\x27\x22](/firma/[^\x27\x22]+)[\x27\x22]", content)
    for f in firms:
        full_url = urllib.parse.urljoin(BASE_URL, f)
        if full_url in seen: continue
        seen.add(full_url)
        slug = f.split("/")[-1]
        title_slug = re.sub(r"-m?\d+$", "", slug).replace("-", " ").capitalize()
        results.append({
            "title": title_slug,
            "url": full_url,
            "type": "firm"
        })
        
    # 5. Forum threads fallback
    threads = re.findall(r"<a href=[\x27\x22](/post/[^\x27\x22]+)[\x27\x22]", content)
    for t in threads:
        full_url = urllib.parse.urljoin(BASE_URL, t)
        if full_url in seen: continue
        seen.add(full_url)
        slug = t.split("/")[-1]
        title_slug = re.sub(r"-f\d+$", "", slug).replace("-", " ").capitalize()
        results.append({
            "title": title_slug,
            "url": full_url,
            "type": "forum"
        })
        
    return results

def main():
    parser = argparse.ArgumentParser(description="zambrow_tool.py — Zambrów local news, services, and cinema CLI helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # search
    search_p = subparsers.add_parser("search", help="Search the portals (forum, adverts, firms, news, cinema, events)")
    search_p.add_argument("query", help="Search term (e.g. kominiarz, elektryk, Lalka, kino, koncert)")
    search_p.add_argument("-s", "--section", choices=["all", "forum", "adverts", "firms", "news", "cinema", "kino", "filmy", "events", "imprezy", "wydarzenia"], default="all",
                          help="Filter by section")
    search_p.add_argument("-S", "--source", choices=["all", "zambrow-org", "zambrowiacy", "cinema", "kino"], default="all",
                          help="Source portal: all (default), zambrow-org, zambrowiacy, or cinema/kino")
    search_p.add_argument("--details", action="store_true", help="Fetch direct phone and email details for each hit")
    search_p.add_argument("--json", action="store_true", help="Output raw JSON")
    
    # get
    get_p = subparsers.add_parser("get", help="Fetch and parse details of a post, ad, company, cinema movie, or events calendar")
    get_p.add_argument("url", help="URL or path (e.g. /post/... or /oferta/... or https://kino.mokzambrow.pl/marsupilami/ or https://zambrow.org/wydarzenia-imprezy)")
    get_p.add_argument("--download-images", dest="download_images_dir", default=None,
                       help="Katalog docelowy do pobrania zdjęć oferty (np. --download-images ~/zambrow-vault/nieruchomosci/img/2586674)")
    get_p.add_argument("--max-images", type=int, default=5,
                       help="Maksymalna liczba zdjęć do pobrania (domyślnie 5)")
    get_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # events / imprezy / wydarzenia
    events_p = subparsers.add_parser("events", aliases=["imprezy", "wydarzenia"],
                                     help="Kalendarz imprez i wydarzeń kulturalnych w Zambrowie i powiecie (zambrow.org/wydarzenia-imprezy)")
    events_p.add_argument("-d", "--days", type=int, default=None,
                          help="Pokaż wydarzenia na najbliższe N dni (np. --days 14)")
    events_p.add_argument("-m", "--month", type=int, default=None,
                          help="Filtruj wg numeru miesiąca (1-12)")
    events_p.add_argument("-c", "--category", help="Filtruj wg kategorii (np. 'koncert', 'warsztaty', 'wystawa', 'spotkanie')")
    events_p.add_argument("--details", action="store_true",
                          help="Pobierz pełną treść artykułu i kontakty dla każdego wydarzenia")
    events_p.add_argument("--json", action="store_true",
                          help="Zwróć wynik w formacie JSON (dla Generative UI / widgetów)")
    
    # news
    news_p = subparsers.add_parser("news", help="Scrape latest news with headlines and leads from zambrow.org and/or zambrowiacy.pl")
    news_p.add_argument("-d", "--days", type=int, default=14, help="Number of days back to scrape (default: 14)")
    news_p.add_argument("-m", "--limit", type=int, default=50, help="Maximum number of articles to return (default: 50)")
    news_p.add_argument("-c", "--category", help="Filter by category or tag (e.g. 'edukacja', 'komunikat', 'inwestycje')")
    news_p.add_argument("-S", "--source", choices=["all", "zambrow-org", "zambrowiacy"], default="all",
                        help="Source portal: all (default: both), zambrow-org, or zambrowiacy")
    news_p.add_argument("--full", action="store_true", help="Include full article text in output")
    news_p.add_argument("--no-lead", action="store_true", help="Fast mode without article leads")
    news_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # browse
    browse_p = subparsers.add_parser("browse", help="Browse listings in a category on zambrow.org")
    browse_p.add_argument("category", help="Category path, e.g. 'ogloszenia/uslugi-i-firmy/elektryk' or 'budownictwo-dom-mapa'")
    browse_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # cinema / kino
    cinema_p = subparsers.add_parser("cinema", aliases=["kino"], help="Kino Miejskiego Ośrodka Kultury w Zambrowie (kino.mokzambrow.pl)")
    cinema_p.add_argument("--today", action="store_true", help="Repertuar na dzisiaj (domyślnie, jeśli brak innych opcji)")
    cinema_p.add_argument("--date", help="Repertuar na konkretny dzień (np. 2026-10-15, today, jutro)")
    cinema_p.add_argument("--schedule", action="store_true", help="Wyświetl harmonogram kalendarium na kolejne dni")
    cinema_p.add_argument("--days", type=int, default=7, help="Liczba dni do wyświetlenia w kalendarium (domyślnie 7)")
    cinema_p.add_argument("--movies", action="store_true", help="Lista wszystkich filmów (gramy + zapowiedzi)")
    cinema_p.add_argument("--gramy", action="store_true", help="Tylko aktualnie grane filmy")
    cinema_p.add_argument("--zapowiedzi", action="store_true", help="Tylko nadchodzące zapowiedzi")
    cinema_p.add_argument("--movie", help="Szczegóły konkretnego filmu (wg tytułu lub sluga, np. 'Marsupilami', 'Lalka')")
    cinema_p.add_argument("-r", "--ratings", action="store_true", help="Pobierz i dołącz oceny oraz werdykt z Filmweb.pl i IMDb.com")
    cinema_p.add_argument("--rate", help="Sprawdź ocenę filmu na Filmwebie i IMDb (np. --rate 'Marsupilami')")
    cinema_p.add_argument("--info", action="store_true", help="Cennik biletów 2D/3D, godziny kasy, adres, dane kontaktowe")
    cinema_p.add_argument("--json", action="store_true", help="Wyjście w formacie JSON")
    
    args = parser.parse_args()
    
    if args.command in ("cinema", "kino"):
        if args.info:
            info = get_cinema_info()
            if args.json:
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print(f"\n🎬 {info['name']}\n")
                print(f"📍 Adres: {info['address']}")
                print(f"📞 Telefon: {info['phone']}")
                print(f"🕒 Kasa biletowa: {info['box_office_hours']}")
                print(f"🌐 Strona www: {info['website']}")
                print(f"🎟️ Bilety online: {info['booking_url']}\n")
                print("💰 Cennik biletów:")
                print("  • Filmy 2D:")
                for k, v in info["prices"]["2D"].items():
                    k_clean = k.replace("_", " ").capitalize()
                    print(f"    - {k_clean}: {v}")
                print("  • Filmy 3D:")
                for k, v in info["prices"]["3D"].items():
                    k_clean = k.replace("_", " ").capitalize()
                    print(f"    - {k_clean}: {v}")
                print()
            return

        if args.rate:
            r = fetch_movie_ratings(args.rate)
            if args.json:
                print(json.dumps(r, indent=2, ensure_ascii=False))
            else:
                print(f"\n🎬 Oceny filmu: '{args.rate}'\n")
                if r.get("filmweb"):
                    fw = r["filmweb"]
                    rate_str = f"{fw['rating']}/10" if fw.get("rating") else "brak ocen"
                    votes_str = f" ({fw['votes_count']} ocen)" if fw.get("votes_count") else ""
                    print(f"⭐ Filmweb: {rate_str}{votes_str}")
                    if r.get("verdict"):
                        print(f"   Werdykt: {r['verdict']}")
                    print(f"   Link: {fw['url']}")
                else:
                    print("⭐ Filmweb: Brak wyników")

                if r.get("imdb"):
                    im = r["imdb"]
                    y_str = f" ({im['year']})" if im.get("year") else ""
                    cast_str = f" | Obsada: {im['cast']}" if im.get("cast") else ""
                    print(f"🎬 IMDb: {im['title']}{y_str}{cast_str}")
                    print(f"   Link: {im['url']}")
                else:
                    print("🎬 IMDb: Brak wyników")
                print()
            return

        if args.movie:
            movie = get_cinema_movie_details(args.movie, with_ratings=True)
            if not movie:
                print(f"Nie znaleziono filmu pasującego do zapytania: '{args.movie}'.")
                return
            if args.json:
                print(json.dumps(movie, indent=2, ensure_ascii=False))
            else:
                status_badge = "Aktualnie gramy" if movie["status"] == "gramy" else "Zapowiedź"
                print(f"\n🎬 {movie['title']} [{status_badge}]\n")
                if movie.get("genre"): print(f"🏷️ Gatunek: {movie['genre']}")
                if movie.get("runtime"): print(f"⏱️ Czas trwania: {movie['runtime']}")
                if movie.get("age_limit"): print(f"🔞 Ograniczenie wiekowe: {movie['age_limit']}")
                if movie.get("origin"): print(f"🌍 Kraj i rok: {movie['origin']}")
                if movie.get("date_range"): print(f"📅 Okres grania: {movie['date_range']}")
                print(f"🔗 Strona filmu: {movie['url']}")
                print(f"🎟️ Rezerwacja/Bilety: {movie['booking_url']}")
                if movie.get("trailer"): print(f"▶️ Zwiastun: {movie['trailer']}")
                if movie.get("poster"): print(f"🖼️ Plakat: {movie['poster']}")

                # Ratings & verdict
                r = movie.get("ratings")
                if r:
                    print("\n⭐ Oceny i werdykt (Filmweb / IMDb):")
                    if r.get("filmweb"):
                        fw = r["filmweb"]
                        rate_str = f"{fw['rating']}/10" if fw.get("rating") else "brak ocen"
                        votes_str = f" ({fw['votes_count']} ocen)" if fw.get("votes_count") else ""
                        print(f"  • Filmweb: {rate_str}{votes_str}")
                        if r.get("verdict"):
                            print(f"    Werdykt: {r['verdict']}")
                        print(f"    Link: {fw['url']}")
                    if r.get("imdb"):
                        im = r["imdb"]
                        y_str = f" ({im['year']})" if im.get("year") else ""
                        cast_str = f" | Obsada: {im['cast']}" if im.get("cast") else ""
                        print(f"  • IMDb: {im['title']}{y_str}{cast_str}")
                        print(f"    Link: {im['url']}")

                if movie.get("showtimes"):
                    print("\n🕒 Harmonogram seansów:")
                    for s in movie["showtimes"]:
                        print(f"  • {s}")

                if movie.get("synopsis"):
                    print(f"\n📖 Opis filmu:\n{movie['synopsis']}")
                print()
            return

        if args.movies or args.gramy or args.zapowiedzi:
            cat = "gramy" if args.gramy else ("zapowiedzi" if args.zapowiedzi else "all")
            movies = get_cinema_movies(category=cat, with_ratings=args.ratings)
            if args.json:
                print(json.dumps(movies, indent=2, ensure_ascii=False))
            else:
                print(f"\n🎞️ Filmy w Kinie Zambrów ({len(movies)} pozycji):\n")
                current_st = None
                for m in movies:
                    st = "AKTUALNIE GRAMY" if m["status"] == "gramy" else "NADCHODZĄCE ZAPOWIEDZI"
                    if st != current_st:
                        current_st = st
                        print(f"=== {current_st} ===")
                    details = []
                    if m.get("genre"): details.append(m["genre"])
                    if m.get("runtime"): details.append(m["runtime"])
                    if m.get("date_range"): details.append(f"Termin: {m['date_range']}")
                    det_str = f" | {', '.join(details)}" if details else ""
                    print(f"• {m['title']}{det_str}")
                    print(f"  URL: {m['url']}")
                    if m.get("ratings"):
                        r = m["ratings"]
                        if r.get("filmweb") and r["filmweb"].get("rating"):
                            fw = r["filmweb"]
                            print(f"  ⭐ Filmweb: {fw['rating']}/10 ({fw['votes_count']} ocen) — {r.get('verdict', '')}")
                        if r.get("imdb"):
                            print(f"  🎬 IMDb: {r['imdb']['url']}")
                    if m.get("trailer"):
                        print(f"  Zwiastun: {m['trailer']}")
                    print()
                print(f"🎟️ Zakup i rezerwacja biletów online: {KINO_BOOKING_URL}\n")
            return

        # Single date or schedule
        target_d = args.date if args.date else ("today" if not args.schedule else None)
        sched = get_cinema_schedule(target_date=target_d, days_ahead=args.days)
        
        # If ratings requested, fetch ratings for all unique movie titles in schedule
        ratings_map = {}
        if args.ratings:
            titles_to_fetch = set()
            if sched.get("mode") == "single_day":
                for ev in sched.get("events", []):
                    if ev.get("title"): titles_to_fetch.add(ev["title"])
            else:
                for day_evs in sched.get("schedule", {}).values():
                    for ev in day_evs:
                        if ev.get("title"): titles_to_fetch.add(ev["title"])
            if titles_to_fetch:
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    t_list = list(titles_to_fetch)
                    r_results = list(executor.map(fetch_movie_ratings, t_list))
                    for t, r in zip(t_list, r_results):
                        ratings_map[t] = r

        if args.json:
            if args.ratings:
                sched["ratings"] = ratings_map
            print(json.dumps(sched, indent=2, ensure_ascii=False))
        else:
            if sched.get("mode") == "single_day":
                req_d = sched["date"]
                evs = sched.get("events", [])
                try:
                    p = [int(x) for x in req_d.split("-")]
                    weekday_num = datetime.date(p[0], p[1], p[2]).weekday()
                    weekday_str = f", {POLISH_WEEKDAYS.get(weekday_num, '')}"
                except Exception:
                    weekday_str = ""
                    
                print(f"\n🎬 Repertuar Kina Zambrów na dzień {req_d}{weekday_str}:\n")
                if not evs:
                    print("  Brak zaplanowanych seansów w tym dniu.")
                else:
                    for i, ev in enumerate(evs, 1):
                        time_prefix = f"{ev['time']} — " if ev.get("time") else ""
                        print(f"  [{i}] {time_prefix}{ev['title']}")
                        if ev.get("url"):
                            print(f"      Szczegóły: {ev['url']}")
                        if args.ratings and ev.get("title") in ratings_map:
                            r = ratings_map[ev["title"]]
                            if r.get("filmweb") and r["filmweb"].get("rating"):
                                fw = r["filmweb"]
                                print(f"      ⭐ Filmweb: {fw['rating']}/10 ({fw['votes_count']} ocen) — {r.get('verdict', '')}")
                            if r.get("imdb"):
                                print(f"      🎬 IMDb: {r['imdb']['url']}")
                print(f"\n🎟️ Rezerwacja i zakup biletów online: {KINO_BOOKING_URL}")
                print("📍 Kasa kina: Centrum Kultury, ul. Wyszyńskiego 2a, tel. 86 475 44 88 (czynna 13:30 – 19:30)\n")
            else:
                start = sched.get("start_date", "")
                end = sched.get("end_date", "")
                days_dict = sched.get("schedule", {})
                print(f"\n📅 Kalendarium Kina Zambrów ({start} do {end}):\n")
                if not days_dict:
                    print("  Brak dostępnych terminów w wybranym przedziale.")
                else:
                    for d_str, ev_list in sorted(days_dict.items()):
                        try:
                            p = [int(x) for x in d_str.split("-")]
                            w_name = POLISH_WEEKDAYS.get(datetime.date(p[0], p[1], p[2]).weekday(), "")
                            w_tag = f" ({w_name})" if w_name else ""
                        except Exception:
                            w_tag = ""
                            
                        if not ev_list:
                            continue
                            
                        print(f"=== {d_str}{w_tag} ===")
                        for ev in ev_list:
                            time_prefix = f"{ev['time']} — " if ev.get("time") else ""
                            print(f"  • {time_prefix}{ev['title']}")
                            if ev.get("url"):
                                print(f"    URL: {ev['url']}")
                            if args.ratings and ev.get("title") in ratings_map:
                                r = ratings_map[ev["title"]]
                                if r.get("filmweb") and r["filmweb"].get("rating"):
                                    fw = r["filmweb"]
                                    print(f"    ⭐ Filmweb: {fw['rating']}/10 ({fw['votes_count']} ocen) — {r.get('verdict', '')}")
                                if r.get("imdb"):
                                    print(f"    🎬 IMDb: {r['imdb']['url']}")
                        print()
                print(f"🎟️ Bilety online: {KINO_BOOKING_URL}\n")
        return

    elif args.command == "news":
        articles = scrape_news(
            days=args.days,
            limit=args.limit,
            category=args.category,
            source=args.source,
            with_lead=not args.no_lead,
            with_full=args.full
        )
        if args.json:
            print(json.dumps(articles, indent=2, ensure_ascii=False))
        else:
            source_label = {
                "all": "zambrow.org & zambrowiacy.pl",
                "zambrow-org": "zambrow.org",
                "zambrowiacy": "zambrowiacy.pl"
            }.get(args.source, args.source)

            if not articles:
                cat_suffix = f" w kategorii '{args.category}'" if args.category else ""
                print(f"Brak wiadomości z ostatnich {args.days} dni ({source_label}){cat_suffix}.")
                return
            
            cat_str = f" [kategoria: {args.category}]" if args.category else ""
            print(f"\n📰 Wiadomości {source_label} z ostatnich {args.days} dni{cat_str} ({len(articles)} artykułów):\n")
            for i, a in enumerate(articles, 1):
                date_display = a.get("date", "")[:16].replace("T", " ") if a.get("date") else "Brak daty"
                source_tag = f"[{a.get('source', '')}] " if a.get("source") else ""
                cat_display = f"[{a.get('category')}] " if a.get("category") else ""
                author_display = f" | ✍️ {a['author']}" if a.get("author") else ""
                
                print(f"[{i}] {date_display} | {source_tag}{cat_display}{a.get('title')}{author_display}")
                print(f"    URL: {a.get('url')}")
                if a.get("lead"):
                    print(f"    Lead: {a.get('lead')}")
                if args.full and a.get("body"):
                    print(f"\n    Treść:\n{a.get('body')}\n")
                print()
            
            print("💡 Aby pobrać pełną treść konkretnego artykułu, uruchom:")
            print("   python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py get \"<URL>\"\n")

    elif args.command == "search":
        items = search_portal(args.query, args.section, args.source)
        
        if args.details:
            for item in items:
                try:
                    if item["type"] in ("forum", "ad", "firm", "news", "cinema_movie", "cinema_info"):
                        det = get_page_details(item["url"])
                        if item["type"] == "forum":
                            item["phones"] = det.get("phones", [])
                            item["emails"] = det.get("emails", [])
                        elif item["type"] == "news":
                            item["lead"] = det.get("lead", "")
                            item["date"] = det.get("date", "")
                        elif item["type"] == "cinema_movie":
                            item["showtimes"] = det.get("showtimes", [])
                            item["trailer"] = det.get("trailer", "")
                            item["booking_url"] = det.get("booking_url", "")
                        else:
                            if det.get("phone"): item["phone"] = det["phone"]
                            if det.get("email"): item["email"] = det["email"]
                            if det.get("address"): item["address"] = det["address"]
                except Exception as e:
                    item["error"] = str(e)
                    
        if args.json:
            print(json.dumps(items, indent=2, ensure_ascii=False))
        else:
            if not items:
                print(f"Brak wyników dla zapytania: '{args.query}'")
                return
            print(f"\n🔍 Wyniki dla '{args.query}' ({len(items)} pozycji):\n")
            current_sec = None
            for it in items:
                if it["section"] != current_sec:
                    current_sec = it["section"]
                    print(f"\n=== {current_sec} ===")
                source_tag = f"[{it.get('source', '')}] " if it.get("source") else ""
                print(f"• {source_tag}{it['title']}")
                print(f"  URL: {it['url']}")
                if it.get("info"):
                    print(f"  Info: {it['info']}")
                if it.get("snippet"):
                    print(f"  Fragment: {it['snippet']}")
                if it.get("lead"):
                    print(f"  Lead: {it['lead']}")
                if it.get("phone"):
                    print(f"  📞 Telefon: {it['phone']}")
                if it.get("email"):
                    print(f"  ✉️ Email: {it['email']}")
                if it.get("phones"):
                    print(f"  📞 Telefony: {', '.join(it['phones'])}")
                if it.get("emails"):
                    print(f"  ✉️ Emaile: {', '.join(it['emails'])}")
                if it.get("trailer"):
                    print(f"  ▶️ Zwiastun: {it['trailer']}")
                if it.get("booking_url"):
                    print(f"  🎟️ Bilety: {it['booking_url']}")
                print()
                
    elif args.command == "get":
        data = get_page_details(args.url)
        if getattr(args, "download_images_dir", None) and data.get("photos"):
            saved = download_images(data["photos"], args.download_images_dir, limit=args.max_images)
            data["downloaded_images"] = saved
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\n📄 {data.get('title', 'Szczegóły strony')}")
            print(f"URL: {data.get('url')}")
            print(f"Typ: {data.get('type')}")
            if data.get("price"):
                print(f"💰 Cena: {data['price']}")
            if data.get("parameters"):
                print(f"🏷️ Parametry: {', '.join(data['parameters'])}")
            if data.get("date"):
                print(f"📅 Data: {data['date']}")
            if data.get("author"):
                print(f"✍️ Autor: {data['author']}")
            if data.get("category"):
                print(f"🏷️ Kategoria: {data['category']}")
            if data.get("genre"):
                print(f"🎭 Gatunek: {data['genre']}")
            if data.get("runtime"):
                print(f"⏱️ Czas trwania: {data['runtime']}")
            if data.get("age_limit"):
                print(f"🔞 Wiek: {data['age_limit']}")
            if data.get("date_range"):
                print(f"📅 Okres grania: {data['date_range']}")
            if data.get("trailer"):
                print(f"▶️ Zwiastun: {data['trailer']}")
            if data.get("booking_url"):
                print(f"🎟️ Bilety: {data['booking_url']}")
            if data.get("ratings"):
                r = data["ratings"]
                print("\n⭐ Oceny i werdykt (Filmweb / IMDb):")
                if r.get("filmweb"):
                    fw = r["filmweb"]
                    rate_str = f"{fw['rating']}/10" if fw.get("rating") else "brak ocen"
                    votes_str = f" ({fw['votes_count']} ocen)" if fw.get("votes_count") else ""
                    print(f"  • Filmweb: {rate_str}{votes_str}")
                    if r.get("verdict"):
                        print(f"    Werdykt: {r['verdict']}")
                    print(f"    Link: {fw['url']}")
                if r.get("imdb"):
                    im = r["imdb"]
                    y_str = f" ({im['year']})" if im.get("year") else ""
                    cast_str = f" | Obsada: {im['cast']}" if im.get("cast") else ""
                    print(f"  • IMDb: {im['title']}{y_str}{cast_str}")
                    print(f"    Link: {im['url']}")
            if data.get("showtimes"):
                print("\n🕒 Seanse:")
                for s in data["showtimes"]:
                    print(f"  • {s}")
            if data.get("lead"):
                print(f"\n📌 Lead:\n{data['lead']}")
            if data.get("synopsis"):
                print(f"\n📖 Opis:\n{data['synopsis']}")
            if data.get("body"):
                print(f"\n📝 Treść:\n{data['body']}")
            if data.get("phone"):
                print(f"📞 Telefon: {data['phone']}")
            if data.get("email"):
                print(f"✉️ Email: {data['email']}")
            if data.get("address"):
                print(f"📍 Adres: {data['address']}")
            if data.get("box_office_hours"):
                print(f"🕒 Kasa biletowa: {data['box_office_hours']}")
            if data.get("prices"):
                print("\n💰 Cennik:")
                for fmt, p_dict in data["prices"].items():
                    print(f"  • Format {fmt}:")
                    for k, v in p_dict.items():
                        print(f"    - {k.replace('_', ' ').capitalize()}: {v}")
            if data.get("description"):
                print(f"\n📝 Opis:\n{data['description']}")
            if data.get("photos"):
                print(f"\n🖼️ Zdjęcia ({len(data['photos'])}):")
                for ph in data["photos"][:5]:
                    print(f"  • {ph}")
                if len(data["photos"]) > 5:
                    print(f"  ... (+ {len(data['photos']) - 5} kolejnych)")
            if data.get("downloaded_images"):
                print(f"\n📥 Zapisano zdjęcia lokalnie ({len(data['downloaded_images'])}):")
                for d_img in data["downloaded_images"]:
                    print(f"  • {d_img}")
            if data.get("comments"):
                print(f"\n💬 Komentarze / Odpowiedzi ({len(data['comments'])}):")
                for i, c in enumerate(data["comments"], 1):
                    contacts = []
                    if c.get("phones"): contacts.append(f"tel: {', '.join(c['phones'])}")
                    if c.get("emails"): contacts.append(f"mail: {', '.join(c['emails'])}")
                    contact_str = f" [{'; '.join(contacts)}]" if contacts else ""
                    print(f"  [{i}] {c['author']} ({c['date']}){contact_str}:")
                    print(f"      {c['text']}")
            if data.get("events"):
                print(f"\n🎭 Zaplanowane wydarzenia ({len(data['events'])} pozycji):")
                for ev in data["events"]:
                    t_str = f" ⏰ {ev['time']}" if ev.get("time") else ""
                    loc_str = f" 📍 {ev['location']}" if ev.get("location") else ""
                    print(f"  • 📅 {ev['date']}{t_str} | {ev['title']} ({ev['category']}){loc_str}")
                    print(f"    🔗 {ev['url']}")
            print()
            
    elif args.command in ("events", "imprezy", "wydarzenia"):
        evs = scrape_events(days=args.days, month=args.month, with_details=args.details)
        if args.category:
            cat_q = args.category.strip().lower()
            evs = [e for e in evs if cat_q in e.get("category", "").lower() or cat_q in e.get("title", "").lower()]
            
        if args.json:
            print(json.dumps(evs, indent=2, ensure_ascii=False))
        else:
            if not evs:
                filter_desc = []
                if args.days: filter_desc.append(f"w ciągu najbliższych {args.days} dni")
                if args.month: filter_desc.append(f"w miesiącu {args.month}")
                if args.category: filter_desc.append(f"w kategorii '{args.category}'")
                desc_str = f" ({', '.join(filter_desc)})" if filter_desc else ""
                print(f"Brak zaplanowanych wydarzeń{desc_str}.")
                return
                
            print(f"\n🎭 Kalendarium Imprez i Wydarzeń w Zambrowie i powiecie ({len(evs)} pozycji):\n")
            for i, ev in enumerate(evs, 1):
                badge_str = f"[{ev['badge']}] " if ev.get("badge") else ""
                days_away = ev.get("days_away")
                if days_away is not None:
                    if days_away == 0:
                        rel_str = " (DZISIAJ!)"
                    elif days_away == 1:
                        rel_str = " (JUTRO)"
                    elif days_away > 1:
                        rel_str = f" (za {days_away} dni)"
                    else:
                        rel_str = ""
                else:
                    rel_str = ""
                    
                time_str = f" ⏰ {ev['time']}" if ev.get("time") else ""
                loc_str = f" 📍 {ev['location']}" if ev.get("location") else ""
                cat_str = f" [{ev.get('category')}]" if ev.get("category") else ""
                
                print(f"[{i}] 📅 {ev.get('date', 'Termin nieokreślony')}{rel_str} | {badge_str}{ev['title']}{cat_str}")
                if time_str or loc_str:
                    print(f"    {time_str.strip()}{loc_str}")
                print(f"    🔗 URL: {ev['url']}")
                if ev.get("description"):
                    print(f"    📝 Opis: {ev['description']}")
                if ev.get("full_body"):
                    print(f"\n    📖 Pełny opis:\n{ev['full_body']}\n")
                if ev.get("phones"):
                    print(f"    📞 Tel: {', '.join(ev['phones'])}")
                print()
                
            print("💡 Wygeneruj dane dla GUI / widgetu interaktywnego:")
            print("   python3 ~/.gemini/skills/zambrow/scripts/zambrow_tool.py events --json\n")

    elif args.command == "browse":
        items = browse_category(args.category)
        if args.json:
            print(json.dumps(items, indent=2, ensure_ascii=False))
        else:
            print(f"\n📂 Pozycje w kategorii '{args.category}' ({len(items)} pozycji):\n")
            for it in items:
                price_str = f" [Cena: {it['price']}]" if it.get("price") else ""
                tags_str = f" | {', '.join(it['tags'])}" if it.get("tags") else ""
                author_str = f" | autor: {it['author']}" if it.get("author") else ""
                date_str = f" ({it['date']})" if it.get("date") else ""
                reply_str = f" | ost. odp: {it['last_reply']}" if it.get("last_reply") else ""
                comm_str = f" [{it['comments_count']} odp.]" if it.get("comments_count") is not None and it["comments_count"] > 0 else ""
                
                print(f"•{price_str} {it['title']}{comm_str} ({it['type']}){tags_str}{author_str}{date_str}{reply_str}")
                print(f"  {it['url']}")
            print()

if __name__ == "__main__":
    main()
