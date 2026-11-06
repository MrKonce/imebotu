"""
Kariyer Portalları Kazıyıcı Modülü (Kariyer.net + LinkedIn)
TNKÜ E-E İME Öğrencisi için SIKI LOKASYON (Tekirdağ / Çorlu / Çerkezköy / OSB) ve STAJ / İME odaklıdır.
Gaziantep, Samsun, İzmir veya İstanbul gibi uzak şehirler ve şantiye şefi/kıdemli pozisyonlar elenir.
"""

import sys
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    LOCATIONS,
    WRONG_CITIES,
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
# 1. Kariyer.net Kazıyıcı (Mobil Web - Doğrudan Tekirdağ / Çorlu / Çerkezköy Filtreli)
# =============================================================================

def _fetch_kariyernet_search(query: str, location_slug: str = "tekirdag") -> List[Dict[str, Any]]:
    """m.kariyer.net üzerinden doğrudan Tekirdağ il ve ilçe yollarıyla arar."""
    results: List[Dict[str, Any]] = []
    encoded_kw = urllib.parse.quote(query)
    # Doğru Kariyer.net mobil URL yapısı: /is-ilanlari/{sehir}?kw={kelime}
    url = f"https://m.kariyer.net/is-ilanlari/{location_slug}?kw={encoded_kw}"

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

            # Sponsorlu ve gereksiz etiketleri temizle
            clean_parts = [
                p for p in parts
                if "Sponsorlu" not in p and "update" not in p.lower() and p not in ["B", "T", "accessible"]
            ]
            if len(clean_parts) < 2:
                continue

            title = clean_parts[0]
            company = clean_parts[1] if len(clean_parts) > 1 else "Kariyer.net İlanı"

            full_context = f"{title} {company} {' '.join(clean_parts)}".lower()

            # 1. Uzak Şehir Filtresi: Gaziantep, Samsun, İzmir vb. kesinlikle elenir!
            if any(wc in full_context for wc in WRONG_CITIES):
                # Tekirdağ açıkça geçmiyorsa ele
                if not any(loc.lower() in full_context for loc in LOCATIONS):
                    continue

            # 2. Lokasyon Doğrulaması: Tekirdağ / Çorlu / Çerkezköy vb. içermiyorsa ASLA kabul etme
            matched_loc = None
            for loc in LOCATIONS:
                if loc.lower() in full_context:
                    matched_loc = loc
                    break

            if not matched_loc:
                # Kesinlikle Tekirdağ dışı, ATLA! (Eski hatadaki gibi Çorlu varsayımı YAPMA)
                continue

            # 3. Kıdemli / Şantiye Şefi / Yönetici pozisyonlarını ele
            if any(s in title.lower() for s in ["şantiye şefi", "şantiye", "müdür", "yönetici", "kıdemli", "senior", "direktör", "başmühendis"]):
                continue

            # 4. Uygunluk skoru hesapla
            score = calculate_relevance_score(
                title=title,
                text=" ".join(clean_parts),
                location=matched_loc,
                source="Kariyer.net"
            )

            # Skor 0 ise (alakasız sektör, kıdemli veya staj dışı) ekleme
            if score <= 0:
                continue

            results.append({
                "company": company,
                "title": title,
                "location": f"Tekirdağ / {matched_loc}" if matched_loc != "Tekirdağ" else "Tekirdağ",
                "url": full_url,
                "source": "Kariyer.net",
                "relevance_score": score,
                "notes": f"Kariyer.net ilanı - {company} ({matched_loc})",
            })
    except Exception as e:
        print(f"[UYARI] Kariyer.net arama hatası ({query} - {location_slug}): {e}")

    return results


def fetch_kariyernet_all() -> List[Dict[str, Any]]:
    """Tüm hedef staj/İME anahtar kelimeleri ile Tekirdağ, Çorlu ve Çerkezköy'ü tarar."""
    queries = [
        "stajyer",
        "staj",
        "aday mühendis",
        "uzun dönem",
        "İME",
        "işletmede mesleki eğitim",
        "elektrik stajyer",
        "otomasyon stajyer",
        "elektrik bakım",
    ]
    city_slugs = [
        "tekirdag",
        "tekirdag-corlu",
        "tekirdag-cerkezkoy",
    ]

    all_jobs: Dict[str, Dict[str, Any]] = {}
    print("[Kariyer.net] Doğrulanmış Tekirdağ & Çorlu & Çerkezköy staj/İME ilanları taranıyor...")

    for city in city_slugs:
        for q in queries:
            found = _fetch_kariyernet_search(query=q, location_slug=city)
            for job in found:
                if job["url"] not in all_jobs:
                    all_jobs[job["url"]] = job

    print(f"[Kariyer.net] Toplam {len(all_jobs)} doğrulanmış yerel staj/İME ilanı bulundu.")
    return list(all_jobs.values())


# =============================================================================
# 2. LinkedIn Public Jobs API (Tekirdağ / Çorlu / Çerkezköy Kesin Eşleşme)
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

            loc_check = f"{title} {company} {job_loc}".lower()

            # 1. Uzak şehir filtresi
            if any(wc in loc_check for wc in WRONG_CITIES):
                if not any(loc.lower() in loc_check for loc in LOCATIONS):
                    continue

            # 2. Kesin Lokasyon Doğrulaması (Esenyurt, İstanbul vb. elenir)
            matched_loc = None
            for loc in LOCATIONS:
                if loc.lower() in loc_check:
                    matched_loc = loc
                    break

            if not matched_loc:
                continue

            # 3. Kıdemli pozisyonları ele
            if any(s in title.lower() for s in ["şantiye", "müdür", "yönetici", "kıdemli", "senior", "direktör"]):
                continue

            score = calculate_relevance_score(
                title=title,
                text=company,
                location=job_loc,
                source="LinkedIn"
            )

            if score <= 0:
                continue

            results.append({
                "company": company,
                "title": title,
                "location": job_loc,
                "url": href,
                "source": "LinkedIn",
                "relevance_score": score,
                "notes": f"LinkedIn ilanı - {company} ({job_loc})",
            })
    except Exception as e:
        print(f"[UYARI] LinkedIn arama hatası ({query}): {e}")

    return results


def fetch_linkedin_all() -> List[Dict[str, Any]]:
    """LinkedIn üzerinden SADECE yerel Tekirdağ / Çorlu / Çerkezköy stajyer ilanlarını arar."""
    queries = [
        ("stajyer", "Tekirdağ"),
        ("intern", "Tekirdağ"),
        ("uzun dönem stajyer", "Çorlu"),
        ("aday mühendis", "Çerkezköy"),
    ]
    all_jobs: Dict[str, Dict[str, Any]] = {}
    print("[LinkedIn] Yerel stajyer/aday mühendis ilanları taranıyor...")

    for kw, loc in queries:
        found = _fetch_linkedin_jobs(kw, loc)
        for job in found:
            if job["url"] not in all_jobs:
                all_jobs[job["url"]] = job

    print(f"[LinkedIn] Toplam {len(all_jobs)} tekil yerel ilan bulundu.")
    return list(all_jobs.values())


# =============================================================================
# 3. Ana Fonksiyon: Tüm Portalları Birleştir
# =============================================================================

def fetch_all_portal_jobs() -> List[Dict[str, Any]]:
    """Kariyer.net ve LinkedIn portallarından filtrelenmiş yerel staj/İME ilanlarını toplar."""
    all_jobs: Dict[str, Dict[str, Any]] = {}

    for job in fetch_kariyernet_all():
        if job["url"] not in all_jobs:
            all_jobs[job["url"]] = job

    for job in fetch_linkedin_all():
        if job["url"] not in all_jobs:
            all_jobs[job["url"]] = job

    return list(all_jobs.values())
