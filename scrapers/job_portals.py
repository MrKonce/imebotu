"""
Kariyer Portalları Kazıyıcı Modülü (Kariyer.net + LinkedIn)
- Kariyer.net: Mobil arayüz (m.kariyer.net) üzerinden captcha engeline takılmadan doğrudan ilanları çeker.
- LinkedIn: Public guest jobs API üzerinden Çorlu, Çerkezköy ve Tekirdağ ilanlarını çeker.
"""

import sys
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    LOCATIONS,
    USER_AGENT,
    REQUEST_TIMEOUT,
    calculate_relevance_score,
)

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

DESKTOP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# =============================================================================
# 1. Kariyer.net Kazıyıcı (Mobil Web - Hızlı & Engel Yok)
# =============================================================================

def _fetch_kariyernet_search(query: str, location_slug: str = "tekirdag") -> List[Dict[str, Any]]:
    """m.kariyer.net üzerinden ilanları arar ve ayrıştırır."""
    results: List[Dict[str, Any]] = []
    encoded_kw = urllib.parse.quote(query)
    url = f"https://m.kariyer.net/is-ilanlari?kw={encoded_kw}&c={location_slug}"

    try:
        resp = requests.get(url, headers=MOBILE_HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        job_links = soup.select('a[href*="/is-ilani/"]')
        seen_urls = set()

        for a in job_links:
            href = a.get("href", "")
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)

            full_url = f"https://www.kariyer.net{href}" if href.startswith("/") else href
            raw_text = a.get_text(" | ", strip=True)
            parts = [p.strip() for p in raw_text.split("|") if p.strip()]

            # Başlık ve firma tespiti
            # Sponsorlu ilan ibaresini temizle
            clean_parts = [p for p in parts if "Sponsorlu" not in p and "update" not in p.lower()]
            if not clean_parts:
                continue

            title = clean_parts[0]
            company = clean_parts[1] if len(clean_parts) > 1 else "Kariyer.net İlanı"

            # Lokasyon tespiti
            detected_loc = "Tekirdağ / Çorlu"
            full_context = f"{title} {company} {' '.join(clean_parts)}".lower()
            for loc in LOCATIONS:
                if loc.lower() in full_context:
                    detected_loc = loc
                    break

            # Uygunluk skoru
            score = calculate_relevance_score(title, " ".join(clean_parts), detected_loc)

            # Minimum eşik (en az 25 puan veya elektrik/staj/mühendislik içermesi)
            results.append({
                "company": company,
                "title": title,
                "location": detected_loc,
                "url": full_url,
                "source": "Kariyer.net",
                "relevance_score": score,
                "snippet": f"Kariyer.net ilanı - {company} ({detected_loc})",
            })
    except Exception as e:
        print(f"[UYARI] Kariyer.net arama hatası ({query}): {e}")

    return results


def fetch_kariyernet_all() -> List[Dict[str, Any]]:
    """Tüm hedef anahtar kelimeler ile Kariyer.net'i tarar."""
    queries = [
        "stajyer elektrik",
        "stajyer otomasyon",
        "aday mühendis",
        "uzun dönem stajyer",
        "İME",
        "elektrik mühendisi",
    ]
    all_jobs: Dict[str, Dict[str, Any]] = {}
    print("[Kariyer.net] İlanlar taranıyor (m.kariyer.net)...")

    for q in queries:
        found = _fetch_kariyernet_search(q, "tekirdag")
        for job in found:
            if job["url"] not in all_jobs:
                all_jobs[job["url"]] = job

    print(f"[Kariyer.net] Toplam {len(all_jobs)} tekil ilan bulundu.")
    return list(all_jobs.values())


# =============================================================================
# 2. LinkedIn Public Jobs API
# =============================================================================

def _fetch_linkedin_jobs(query: str, location: str = "Tekirdağ") -> List[Dict[str, Any]]:
    """LinkedIn guest API üzerinden iş ilanlarını çeker."""
    results: List[Dict[str, Any]] = []
    encoded_kw = urllib.parse.quote(query)
    encoded_loc = urllib.parse.quote(location)
    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={encoded_kw}&location={encoded_loc}&start=0"
    )

    try:
        resp = requests.get(url, headers=DESKTOP_HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200 or not resp.text.strip():
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("li, div.base-card")
        seen_urls = set()

        for card in cards:
            title_el = card.select_one("h3, .base-search-card__title")
            comp_el = card.select_one("h4, .base-search-card__subtitle")
            loc_el = card.select_one(".job-search-card__location")
            link_el = card.select_one("a.base-card__full-link, a[href*='linkedin.com/jobs']")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            company = comp_el.get_text(strip=True) if comp_el else "Belirtilmemiş"
            job_loc = loc_el.get_text(strip=True) if loc_el else location
            href = link_el.get("href", "").split("?")[0] if link_el else ""

            if not href or href in seen_urls:
                continue
            seen_urls.add(href)

            # Lokasyon filtresi
            loc_check = f"{title} {company} {job_loc}".lower()
            location_match = any(loc.lower() in loc_check for loc in LOCATIONS)
            score = calculate_relevance_score(title, company, job_loc)

            # Lokasyon uymuyorsa ve skor düşükse ele
            if not location_match and score < 30:
                continue

            results.append({
                "company": company,
                "title": title,
                "location": job_loc,
                "url": href,
                "source": "LinkedIn",
                "relevance_score": score,
                "snippet": f"LinkedIn ilanı - {company} ({job_loc})",
            })
    except Exception as e:
        print(f"[UYARI] LinkedIn arama hatası ({query}): {e}")

    return results


def fetch_linkedin_all() -> List[Dict[str, Any]]:
    """Tüm hedef kelimeler ile LinkedIn'den uygun ilanları tarar."""
    queries = [
        ("stajyer elektrik", "Tekirdağ"),
        ("stajyer otomasyon", "Çorlu"),
        ("aday mühendis elektrik", "Tekirdağ"),
        ("stajyer elektronik", "Çorlu"),
        ("intern engineering", "Çerkezköy"),
    ]
    all_jobs: Dict[str, Dict[str, Any]] = {}
    print("[LinkedIn] İlanlar taranıyor...")

    for kw, loc in queries:
        found = _fetch_linkedin_jobs(kw, loc)
        for job in found:
            if job["url"] not in all_jobs:
                all_jobs[job["url"]] = job

    print(f"[LinkedIn] Toplam {len(all_jobs)} tekil ilan bulundu.")
    return list(all_jobs.values())


# =============================================================================
# 3. Ana Fonksiyon: Tüm Portalları Birleştir
# =============================================================================

def fetch_all_portal_jobs() -> List[Dict[str, Any]]:
    """Kariyer.net ve LinkedIn portallarından tüm uygun ilanları birleştirir."""
    all_jobs: Dict[str, Dict[str, Any]] = {}

    # Kariyer.net
    for job in fetch_kariyernet_all():
        if job["url"] not in all_jobs:
            all_jobs[job["url"]] = job

    # LinkedIn
    for job in fetch_linkedin_all():
        if job["url"] not in all_jobs:
            all_jobs[job["url"]] = job

    print(f"[PORTAL TOPLAM] {len(all_jobs)} tekil ilan toplandı.")
    return list(all_jobs.values())
