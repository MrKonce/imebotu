"""
Kariyer Portalları Kazıyıcı Modülü (Kariyer.net + LinkedIn)
TNKÜ E-E İME Öğrencisi için SIKI LOKASYON (Tekirdağ / Çorlu / Çerkezköy / OSB) ve STAJ / İME odaklıdır.
Gaziantep, Samsun, İzmir veya İstanbul gibi uzak şehirler ve şantiye şefi/kıdemli pozisyonlar elenir.
"""

import json
import re
import sys
import urllib.parse
from datetime import datetime
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
    MIN_RELEVANCE_SCORE,
    calculate_relevance_score,
    validate_strict_location,
)
from database import add_rejected_url, is_url_rejected
from scrapers.youthall import fetch_youthall_jobs

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

DESKTOP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}


# =============================================================================
# 1. Kariyer.net Kazıyıcı (Masaüstü & Detay DOM Lokasyon Ayrıştırma)
# =============================================================================

def _fetch_kariyernet_search(query: str, location_slug: str = "tekirdag") -> List[Dict[str, Any]]:
    """
    Kariyer.net üzerinden doğrudan Tekirdağ/Çorlu/Çerkezköy araması yapar.
    Sıfır Hata (v2.1) Kuralları:
    1. 'Benzer İlanlar' (Ordu, Yozgat vb.) tuzağını keser: Sınır başlığından sonraki ilanları listeye ALMAZ.
    2. Detay sayfasında <script type="application/ld+json"> içindeki JobPosting şemasını okur.
    3. Süresi geçmiş (validThrough < today veya datePosted > 45 gün) ilanları eler.
    4. Lokasyon DOM veya JSON-LD'den okunamazsa ASLA sorgudaki şehri fallback olarak ATAMAZ (location = "").
    5. Elenen ilanları database.rejected_urls tablosuna kaydeder.
    """
    results: List[Dict[str, Any]] = []
    encoded_kw = urllib.parse.quote(query)
    url = f"https://www.kariyer.net/is-ilanlari/{location_slug}?kw={encoded_kw}"

    try:
        resp = requests.get(url, headers=DESKTOP_HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. 'Benzer İlanlar' Sınır Tespiti (Ordu, Yozgat vb. diğer şehir sızıntısını kes)
        cutoff_hrefs = set()
        for b_tag in soup.find_all(lambda tag: tag.name in ["h2", "h3", "h4", "div", "p", "span"] and any(
            phrase in tag.get_text().lower() for phrase in [
                "benzer ilan", "aramana göre bulduğumuz", "önerilen ilan", "diğer ilan", "benzer iş"
            ]
        )):
            for next_a in b_tag.find_all_next("a", href=True):
                h = next_a.get("href", "")
                if "/is-ilani/" in h:
                    cutoff_hrefs.add(h)

        job_links = soup.select('a[href*="/is-ilani/"]')
        seen_urls = set()

        for a in job_links:
            href = a.get("href", "")
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)

            # 'Benzer İlanlar' bölümündeyse DİREKT ATLA
            if href in cutoff_hrefs:
                continue

            full_url = f"https://www.kariyer.net{href}" if href.startswith("/") else href

            # Daha önce elenmiş URL ise boşuna HTTP isteği atma
            if is_url_rejected(full_url):
                continue

            raw_text = a.get_text(" | ", strip=True)
            parts = [p.strip() for p in raw_text.split("|") if p.strip()]
            clean_parts = [
                p for p in parts
                if "Sponsorlu" not in p and "update" not in p.lower() and p not in ["B", "T", "accessible"]
            ]
            fallback_title = clean_parts[0] if clean_parts else "Stajyer / İME"
            fallback_company = clean_parts[1] if len(clean_parts) > 1 else "Kariyer.net İlanı"

            real_loc = ""
            real_title = fallback_title
            real_company = fallback_company
            real_desc = " ".join(clean_parts)

            # 2. Detay Sayfasını Çek & JSON-LD (JobPosting) Ayrıştır
            try:
                det_resp = requests.get(full_url, headers=DESKTOP_HEADERS, timeout=6)
                if det_resp.status_code == 200:
                    dsoup = BeautifulSoup(det_resp.text, "html.parser")

                    # JSON-LD JobPosting Şemasını Ara
                    json_ld_scripts = dsoup.find_all("script", type="application/ld+json")
                    job_posting = None
                    for s in json_ld_scripts:
                        try:
                            data = json.loads(s.string or s.text or "{}")
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                                        job_posting = item
                                        break
                            elif isinstance(data, dict):
                                if data.get("@type") == "JobPosting":
                                    job_posting = data
                                elif "@graph" in data and isinstance(data["@graph"], list):
                                    for item in data["@graph"]:
                                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                                            job_posting = item
                                            break
                            if job_posting:
                                break
                        except Exception:
                            continue

                    now = datetime.now()

                    if job_posting:
                        # Başlık ve Şirket
                        if job_posting.get("title"):
                            real_title = str(job_posting["title"]).strip()
                        hiring_org = job_posting.get("hiringOrganization")
                        if isinstance(hiring_org, dict) and hiring_org.get("name"):
                            real_company = str(hiring_org["name"]).strip()
                        elif isinstance(hiring_org, str):
                            real_company = hiring_org.strip()

                        # Açıklama
                        if job_posting.get("description"):
                            clean_json_desc = BeautifulSoup(str(job_posting["description"]), "html.parser").get_text(" ", strip=True)
                            real_desc = f"{real_desc} {clean_json_desc}"

                        # Süre Geçerlilik Kontrolü
                        valid_through = job_posting.get("validThrough")
                        if valid_through:
                            try:
                                vt_str = str(valid_through).split("T")[0]
                                vt_dt = datetime.strptime(vt_str, "%Y-%m-%d")
                                if vt_dt.date() < now.date():
                                    add_rejected_url(full_url, f"İlan Süresi Dolmuş (validThrough: {valid_through})")
                                    continue
                            except Exception:
                                pass

                        date_posted = job_posting.get("datePosted")
                        if date_posted:
                            try:
                                dp_str = str(date_posted).split("T")[0]
                                dp_dt = datetime.strptime(dp_str, "%Y-%m-%d")
                                if (now.date() - dp_dt.date()).days > 45:
                                    add_rejected_url(full_url, f"Eski İlan (45 günden fazla: {date_posted})")
                                    continue
                            except Exception:
                                pass

                        # JSON-LD'den Lokasyon
                        job_loc_obj = job_posting.get("jobLocation")
                        if isinstance(job_loc_obj, dict):
                            addr = job_loc_obj.get("address", {})
                            if isinstance(addr, dict):
                                reg = addr.get("addressRegion", "") or ""
                                loc = addr.get("addressLocality", "") or ""
                                loc_parts = [p.strip() for p in [reg, loc] if p and p.strip()]
                                if loc_parts:
                                    real_loc = ", ".join(loc_parts)
                        elif isinstance(job_loc_obj, list) and job_loc_obj:
                            loc_parts = []
                            for jlo in job_loc_obj:
                                if isinstance(jlo, dict):
                                    addr = jlo.get("address", {})
                                    if isinstance(addr, dict):
                                        reg = addr.get("addressRegion", "") or ""
                                        loc = addr.get("addressLocality", "") or ""
                                        combined_l = f"{reg} {loc}".strip()
                                        if combined_l:
                                            loc_parts.append(combined_l)
                            if loc_parts:
                                real_loc = ", ".join(loc_parts)

                    # JSON-LD'de lokasyon yoksa DOM yedeklerine bak
                    if not real_loc:
                        loc_el = dsoup.select_one(".company-location, [data-test*='location']")
                        if loc_el:
                            real_loc = loc_el.get_text(" ", strip=True)

                    if not real_title:
                        title_el = dsoup.select_one("h1, [data-test*='job-title']")
                        if title_el and title_el.get_text(strip=True):
                            real_title = title_el.get_text(strip=True)

                    if not real_company:
                        comp_el = dsoup.select_one(".company-name, [data-test*='company-name']")
                        if comp_el and comp_el.get_text(strip=True):
                            real_company = comp_el.get_text(strip=True)
            except Exception:
                pass

            # Kart DOM lokasyonu kontrolü (eğer detay sayfasında bulunamadıysa)
            if not real_loc:
                card_loc_el = a.select_one(".location, [class*='location'], [data-test*='location']")
                if card_loc_el:
                    real_loc = card_loc_el.get_text(" ", strip=True)

            # ASLA ARAMA SORGUSUNDAKİ ŞEHRİ FALLBACK OLARAK ATAMA!
            # Lokasyon bulunamadıysa real_loc boş kalır ve validate_strict_location reddeder.
            is_valid, matched_or_reason = validate_strict_location(
                raw_location=real_loc,
                title=real_title,
                company=real_company,
                body_text=real_desc
            )

            if not is_valid:
                add_rejected_url(full_url, f"Kariyer.net Lokasyon Reddi: {matched_or_reason}")
                continue

            score = calculate_relevance_score(
                title=real_title,
                text=real_desc,
                location=real_loc,
                source="Kariyer.net",
                company=real_company
            )

            if score < MIN_RELEVANCE_SCORE:
                add_rejected_url(full_url, f"Kariyer.net Düşük Skor ({score} < {MIN_RELEVANCE_SCORE})")
                continue

            clean_loc_name = f"Tekirdağ / {matched_or_reason.capitalize()}" if matched_or_reason != "tekirdag" else "Tekirdağ"

            results.append({
                "company": real_company,
                "title": real_title,
                "location": clean_loc_name,
                "url": full_url,
                "source": "Kariyer.net",
                "relevance_score": score,
                "notes": f"Kariyer.net ilanı - {real_company} ({clean_loc_name})",
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
    """LinkedIn guest API üzerinden iş ilanlarını çeker. Fallback lokasyon asla uygulanmaz."""
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
            # KESİNLİKLE FALLBACK YOK: loc_el yoksa boş string bırakılır
            job_loc = loc_el.get_text(strip=True) if loc_el else ""
            href = link_el.get("href", "").split("?")[0] if link_el else ""

            if not href or href in seen_urls:
                continue
            seen_urls.add(href)

            if is_url_rejected(href):
                continue

            # Gerçek DOM verisini Katı Beyaz Liste (Strict Whitelist) ve Blacklist ile doğrula
            is_valid, matched_or_reason = validate_strict_location(
                raw_location=job_loc,
                title=title,
                company=company
            )

            if not is_valid:
                add_rejected_url(href, f"LinkedIn Lokasyon Reddi: {matched_or_reason}")
                continue

            score = calculate_relevance_score(
                title=title,
                text=company,
                location=job_loc,
                source="LinkedIn",
                company=company
            )

            if score < MIN_RELEVANCE_SCORE:
                add_rejected_url(href, f"LinkedIn Düşük Skor ({score} < {MIN_RELEVANCE_SCORE})")
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
        ("elektrik elektronik stajyer", "Tekirdağ"),
        ("otomasyon stajyer", "Tekirdağ"),
        ("aday mühendis elektrik", "Çerkezköy"),
        ("işletmede mesleki eğitim", "Çorlu"),
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
    """Youthall, Kariyer.net, LinkedIn, TNKÜ İME ve Canlı ATS portallarından doğrulanmış yerel staj/İME ilanlarını toplar."""
    all_jobs: Dict[str, Dict[str, Any]] = {}

    # 1. Youthall Portalı
    print("[Youthall] Yerel staj ve genç yetenek ilanları taranıyor...")
    for job in fetch_youthall_jobs():
        if job["url"] not in all_jobs:
            all_jobs[job["url"]] = job

    # 2. Kariyer.net Portalı
    print("[Kariyer.net] Yerel staj/İME ilanları taranıyor...")
    for job in fetch_kariyernet_all():
        if job["url"] not in all_jobs:
            all_jobs[job["url"]] = job

    # 3. LinkedIn Portalı
    print("[LinkedIn] Yerel staj/aday mühendis ilanları taranıyor...")
    for job in fetch_linkedin_all():
        if job["url"] not in all_jobs:
            all_jobs[job["url"]] = job

    # 4. TNKÜ ÇMF İME Portalı & ÇOSB & İzlenen Fabrika Kariyer Sayfaları (ADIM 4)
    print("[TNKÜ & Fabrikalar] TNKÜ ÇMF İME havuzu ve fabrika kariyer sayfaları taranıyor...")
    try:
        from scrapers.osb_directory import scrape_direct_ime_and_osb
        for job in scrape_direct_ime_and_osb():
            if job["url"] not in all_jobs:
                all_jobs[job["url"]] = job
    except Exception as e:
        print(f"[UYARI] TNKÜ ve doğrudan fabrika tarama hatası: {e}")

    # 5. Kurumsal ATS ve Canlı Web Arama
    print("[Canlı Web] Kurumsal ATS ve hedef web aramaları taranıyor...")
    try:
        from scrapers.active_jobs import fetch_all_active_jobs
        for job in fetch_all_active_jobs(max_queries=4):
            if job["url"] not in all_jobs:
                all_jobs[job["url"]] = job
    except Exception as e:
        print(f"[UYARI] Canlı web arama hatası: {e}")

    print(f"[Portallar] Toplam {len(all_jobs)} tekil doğrulanmış ilan toplandı.")
    return list(all_jobs.values())
