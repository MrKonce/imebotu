"""
Youthall (www.youthall.com) Staj & Genç Yetenek İlanları Kazıyıcı Modülü
TNKÜ İME ve Staj için Tekirdağ / Çorlu / Çerkezköy lokasyonlu ilanları çeker.
"""

import sys
import os
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import urllib3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import (
    USER_AGENT,
    REQUEST_TIMEOUT,
    MIN_RELEVANCE_SCORE,
    calculate_relevance_score,
    validate_strict_location,
)
from database import add_rejected_url, is_url_rejected

YOUTHALL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def fetch_youthall_jobs() -> List[Dict[str, Any]]:
    """
    Youthall üzerinden Tekirdağ ve Trakya bölgesindeki staj/İME ilanlarını çeker.
    Yalnızca resmi lokasyon etiketinde Tekirdağ/Çorlu/Çerkezköy geçen ilanları alır.
    """
    results: List[Dict[str, Any]] = []
    seen_urls = set()

    target_urls = [
        "https://www.youthall.com/tr/is-ilanlari/tekirdag/",
        "https://www.youthall.com/tr/is-ilanlari/tekirdag/?order=1",
        "https://www.youthall.com/tr/is-ilanlari/tekirdag/stajyer/",
        "https://www.youthall.com/tr/is-ilanlari/?query=%C3%A7orlu",
        "https://www.youthall.com/tr/is-ilanlari/?query=%C3%A7erkezk%C3%B6y",
        "https://www.youthall.com/tr/is-ilanlari/?query=ergene",
    ]

    for list_url in target_urls:
        try:
            resp = requests.get(list_url, headers=YOUTHALL_HEADERS, timeout=REQUEST_TIMEOUT, verify=False)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            job_cards = soup.find_all("div", class_="jobs")

            for card in job_cards:
                a_tag = card.find("a", href=True)
                if not a_tag:
                    continue

                href = a_tag["href"].strip()
                full_url = href if href.startswith("http") else f"https://www.youthall.com{href}"

                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                if is_url_rejected(full_url):
                    continue

                # Ana Lokasyon HTML Etiketi Kontrolü (map-marker içeren tag)
                primary_location = ""
                tags = card.find_all("div", class_="jobs-tag")
                for tag in tags:
                    if tag.find("i", class_=lambda cl: cl and "map-marker" in str(cl)):
                        primary_location = tag.get_text(strip=True)
                        break

                card_title_el = card.find("div", class_="jobs-content-title")
                card_title = card_title_el.get_text(strip=True) if card_title_el else ""

                logo_img = card.find("img", class_="jobs-content-logo")
                card_company = ""
                if logo_img and logo_img.get("alt"):
                    card_company = logo_img["alt"].replace(" logo", "").replace(" Logo", "").strip()

                if not card_company:
                    parts = [p for p in full_url.split("/") if p]
                    if len(parts) >= 3:
                        card_company = parts[-2].replace("-", " ").title()

                # Detay sayfasını açarak tam başlığı ve resmi lokasyonu doğrula
                real_title = card_title
                real_company = card_company
                real_loc = primary_location

                try:
                    det_resp = requests.get(full_url, headers=YOUTHALL_HEADERS, timeout=7, verify=False, allow_redirects=True)
                    if det_resp.status_code == 200 and "/youth/login" not in det_resp.url:
                        dsoup = BeautifulSoup(det_resp.text, "html.parser")
                        h1 = dsoup.find("h1")
                        if h1 and h1.get_text(strip=True):
                            real_title = h1.get_text(strip=True)

                        comp_div = dsoup.find(class_=lambda cl: cl and "c-job_info_company" in str(cl))
                        if comp_div and comp_div.get_text(strip=True):
                            real_company = comp_div.get_text(strip=True)

                        if not real_loc:
                            meta_desc = dsoup.find("meta", property="og:description")
                            desc_content = meta_desc.get("content", "") if meta_desc else ""
                            if "tekirdağ" in real_title.lower() or "çorlu" in real_title.lower() or "çerkezköy" in real_title.lower():
                                real_loc = "Tekirdağ"
                except Exception:
                    pass

                if not real_loc:
                    continue

                # Katı Beyaz Liste ve Blacklist Kontrolü (Sadece Ana Lokasyon)
                is_valid, matched_or_reason = validate_strict_location(
                    raw_location=real_loc,
                    title=real_title,
                    company=real_company
                )

                if not is_valid:
                    add_rejected_url(full_url, f"Youthall Lokasyon Reddi: {matched_or_reason}")
                    continue

                # Uygunluk skoru
                score = calculate_relevance_score(
                    title=real_title,
                    text=f"{real_title} {real_company}",
                    location=real_loc,
                    source="Youthall",
                    company=real_company
                )

                if score < MIN_RELEVANCE_SCORE:
                    add_rejected_url(full_url, f"Youthall Düşük Skor ({score} < {MIN_RELEVANCE_SCORE})")
                    continue

                clean_loc = f"Tekirdağ / {matched_or_reason.capitalize()}" if matched_or_reason != "tekirdag" else "Tekirdağ"

                results.append({
                    "company": real_company,
                    "title": real_title,
                    "location": clean_loc,
                    "url": full_url,
                    "source": "Youthall",
                    "relevance_score": score,
                    "notes": f"Youthall Staj & Kariyer İlanı - {real_company} ({clean_loc})",
                })

        except Exception as e:
            print(f"[UYARI] Youthall tarama hatası ({list_url}): {e}")

    return results


if __name__ == "__main__":
    jobs = fetch_youthall_jobs()
    print(f"Youthall'dan {len(jobs)} adet geçerli ilan çekildi:")
    for j in jobs:
        print(f"  * {j['company']} - {j['title']} ({j['location']}) -> {j['url']}")
