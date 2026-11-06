"""
Aktif İlan Kazıyıcı Modülü (HTTP & Playwright Destekli)
ÇOSB Özel İstihdam Bürosu, bölgesel kariyer portalları, Indeed ve arama motorlarını
Trakya lokasyonları (Çorlu, Çerkezköy, Ergene, Velimeşe) ve İME / Staj anahtar kelimelerine göre tarar.
"""

import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import (
    LOCATIONS,
    SEARCH_TERMS,
    USER_AGENT,
    REQUEST_TIMEOUT,
    calculate_relevance_score,
)


def scrape_cosb_portal() -> List[Dict[str, Any]]:
    """
    Çerkezköy Organize Sanayi Bölgesi (ÇOSB) Özel İstihdam Bürosu
    resmi kariyer portalındaki (kariyer.cosb.org.tr) canlı iş ve staj ilanlarını çeker.
    """
    results: List[Dict[str, Any]] = []
    base_url = "https://kariyer.cosb.org.tr"
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(base_url, headers=headers, verify=False, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        ilan_links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/Baglan/Ilan?_IlaNo=" in href:
                full_link = href if href.startswith("http") else base_url + href
                ilan_links.add(full_link)

        for link in sorted(ilan_links):
            try:
                detail_resp = requests.get(link, headers=headers, verify=False, timeout=REQUEST_TIMEOUT)
                if detail_resp.status_code != 200 or "Açıklama" not in detail_resp.text:
                    continue

                dsoup = BeautifulSoup(detail_resp.text, "html.parser")
                lines = [l.strip() for l in dsoup.get_text().splitlines() if l.strip()]
                desc = ""
                for i, l in enumerate(lines):
                    if "* Açıklama" in l and i + 1 < len(lines):
                        desc = lines[i + 1]
                        break

                company = "ÇOSB Katılımcı Sanayi Firması"
                if "Çerkezköy Organize Sanayi Bölge Müdürlüğü" in desc:
                    company = "ÇOSB Bölge Müdürlüğü"
                elif "Poliza Endüstri" in desc:
                    company = "Poliza Endüstri A.Ş."

                # Pozisyon Başlığı
                title = "Sanayi Teknik Personel / İlan"
                if "elektrik" in desc.lower() or "154 kv" in desc.lower():
                    title = "154 kV / OG Elektrik Dağıtım & İndirici Merkez Teknisyeni"
                elif "örme kumaş" in desc.lower() or "boyahane" in desc.lower():
                    title = "Örme Kumaş Boyahane Üretim & Kalite Temsilcisi"
                elif "kepçe" in desc.lower() or "arıtma" in desc.lower():
                    title = "Endüstriyel Arıtma Tesisi Operatörü"
                elif "satın alma" in desc.lower():
                    title = "Satın Alma Uzmanı"
                elif "mali işler" in desc.lower():
                    title = "Mali İşler & Muhasebe Sorumlusu"

                loc = "Çerkezköy OSB (ÇOSB), Tekirdağ"
                score = calculate_relevance_score(title, desc, loc)

                results.append({
                    "company": company,
                    "title": title,
                    "location": loc,
                    "url": link,
                    "source": "ÇOSB Özel İstihdam Bürosu",
                    "relevance_score": score,
                    "notes": desc[:300],
                    "snippet": desc[:200],
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[UYARI] ÇOSB Kariyer Portalı taranırken hata: {str(e)}")

    return results


def scrape_search_results_http(query: str) -> List[Dict[str, Any]]:
    """
    HTTP istekleri (requests + bs4) ile arama motoru ve kariyer sayfalarından
    açık iş ilanlarını ve duyuruları çeker.
    """
    results: List[Dict[str, Any]] = []
    encoded_query = urllib.parse.quote(query)
    
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "lxml" if "lxml" in response.text else "html.parser")
            result_elements = soup.select(".result")

            for el in result_elements:
                title_tag = el.select_one(".result__title a")
                snippet_tag = el.select_one(".result__snippet")
                url_tag = el.select_one(".result__url")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                raw_link = title_tag.get("href", "")

                parsed_link = raw_link
                if "uddg=" in raw_link:
                    match = re.search(r"uddg=([^&]+)", raw_link)
                    if match:
                        parsed_link = urllib.parse.unquote(match.group(1))

                if not parsed_link.startswith("http"):
                    continue

                combined_text = f"{title} {snippet}".lower()
                
                company = "Belirtilmemiş"
                if " - " in title:
                    parts = title.split(" - ")
                    company = parts[-1].strip()
                elif " | " in title:
                    parts = title.split(" | ")
                    company = parts[-1].strip()
                elif url_tag:
                    domain = url_tag.get_text(strip=True).split("/")[0]
                    company = domain

                detected_location = "Tekirdağ Bölgesi"
                for loc in LOCATIONS:
                    if loc.lower() in combined_text:
                        detected_location = loc
                        break

                score = calculate_relevance_score(title, snippet, detected_location)

                if score >= 20:
                    results.append(
                        {
                            "company": company,
                            "title": title,
                            "location": detected_location,
                            "url": parsed_link,
                            "source": "Web / İş Arama",
                            "relevance_score": score,
                            "snippet": snippet,
                        }
                    )

    except Exception as e:
        print(f"[UYARI] HTTP Arama Hatası ({query}): {str(e)}")

    return results


def scrape_with_playwright(query: str) -> List[Dict[str, Any]]:
    """
    Playwright headless tarayıcısı kullanarak canlı kariyer ilanlarını (Indeed vb.) çeker.
    """
    results: List[Dict[str, Any]] = []
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            
            # Indeed Türkiye üzerinden Tekirdağ / Çorlu arama
            indeed_url = f"https://tr.indeed.com/jobs?q={urllib.parse.quote(query)}&l=Tekirda%C4%9F"
            page.goto(indeed_url, timeout=18000)
            page.wait_for_timeout(2500)

            soup = BeautifulSoup(page.content(), "html.parser")
            cards = soup.select(".job_seen_beacon, div.cardOutline, .result")
            for card in cards:
                title_el = card.select_one("h2.jobTitle span, a.jcs-JobTitle")
                comp_el = card.select_one("[data-testid='company-name'], span.css-63koeb, .companyName")
                loc_el = card.select_one("[data-testid='text-location'], div.css-1p0sjhy, .companyLocation")
                link_el = card.select_one("a.jcs-JobTitle, h2.jobTitle a")
                snip_el = card.select_one(".job-snippet, .underShelfFooter")

                if title_el:
                    title = title_el.get_text(strip=True)
                    company = comp_el.get_text(strip=True) if comp_el else "Bilinmeyen Firma"
                    location = loc_el.get_text(strip=True) if loc_el else "Tekirdağ / Çorlu"
                    href = link_el.get("href", "") if link_el else ""
                    link = f"https://tr.indeed.com{href}" if href.startswith("/") else (href or indeed_url)
                    snippet = snip_el.get_text(strip=True) if snip_el else ""

                    score = calculate_relevance_score(title, snippet, location)
                    if score >= 20 and link:
                        results.append(
                            {
                                "company": company,
                                "title": title,
                                "location": location,
                                "url": link,
                                "source": "Indeed / Canlı İlan",
                                "relevance_score": score,
                                "snippet": snippet,
                            }
                        )
            browser.close()
    except ImportError:
        pass
    except Exception as e:
        print(f"[UYARI] Playwright tarama uyarısı ({query}): {str(e)}")

    return results


def fetch_all_active_jobs(max_queries: int = 5, use_playwright: bool = False) -> List[Dict[str, Any]]:
    """
    ÇOSB İstihdam Portalı ve arama kombinasyonları ile
    tüm aktif ilanları tarar ve mükerrer URL'leri filtreler.
    """
    all_jobs: Dict[str, Dict[str, Any]] = {}
    
    # 1. ÇOSB Canlı İstihdam ve Kariyer Portalı
    print("[*] ÇOSB Resmi İstihdam Portalı taranıyor...")
    cosb_jobs = scrape_cosb_portal()
    for job in cosb_jobs:
        url = job.get("url")
        if url and url not in all_jobs:
            all_jobs[url] = job
    print(f"    -> {len(cosb_jobs)} açık ÇOSB ilanı tespit edildi.")

    # 2. Öncelikli sorgu kombinasyonları oluştur
    search_combinations = [
        f"{kw} {loc}"
        for kw in ["staj", "stajyer", "İME", "elektrik"]
        for loc in ["Çorlu", "Çerkezköy", "Tekirdağ", "Ergene"]
    ]

    selected_queries = search_combinations[:max_queries]
    print(f"[*] Toplam {len(selected_queries)} hedef canlı arama sorgusu çalıştırılıyor...")

    for query in selected_queries:
        print(f"    -> Taranıyor: '{query}'")
        
        found = scrape_search_results_http(query)
        
        # Playwright desteği (kullanıcı seçeneği veya HTTP boş döndüğünde)
        if (use_playwright or len(all_jobs) < 3) and len(found) == 0:
            pw_found = scrape_with_playwright(query)
            found.extend(pw_found)

        for job in found:
            url = job.get("url")
            if url and url not in all_jobs:
                all_jobs[url] = job

    print(f"[+] Toplam {len(all_jobs)} tekil potansiyel ilan/lead bulundu.")
    return list(all_jobs.values())
