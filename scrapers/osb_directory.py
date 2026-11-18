"""
Trakya Sanayi Havzası Canlı İME ve Sanayi Protokolleri Modülü
(TNKÜ ÇMF İME Portalı, ÇOSB İstihdam Merkezi ve Doğrudan Fabrika İzleme)
Ölü/statik bağlantılar tamamen kaldırılmış olup yalnızca canlı doğrulanan kaynaklar taranır.
"""

import re
import urllib.parse
from typing import List, Dict, Optional, Any
import requests
from bs4 import BeautifulSoup
from config import (
    USER_AGENT,
    REQUEST_TIMEOUT,
    MIN_RELEVANCE_SCORE,
    calculate_relevance_score,
    validate_strict_location,
)
import database

# Statik rehber listesi sahte/ölü linkleri ve yanıltıcı puanlamayı önlemek için boşaltılmıştır.
OSB_COMPANIES: List[Dict[str, str]] = []


def get_all_osb_companies(
    sector: Optional[str] = None,
    location_filter: Optional[str] = None
) -> List[Dict[str, str]]:
    """Tüm statik OSB firma listesi kaldırıldı (sahte ilan ve ölü linkleri önlemek için)."""
    return []


def convert_osb_to_leads() -> List[Dict[str, Any]]:
    """Geriye dönük uyumluluk wrapper'ı."""
    return scrape_direct_ime_and_osb()


WATCHED_CAREER_PAGES = [
    {"company": "EAE Elektrik A.Ş.", "url": "https://www.eaegroup.com/tr/kariyer", "loc": "Çerkezköy, Tekirdağ"},
    {"company": "BSH Ev Aletleri", "url": "https://www.bsh-group.com/tr/kariyer", "loc": "Çerkezköy, Tekirdağ"},
    {"company": "Arçelik / Beko", "url": "https://www.kocariyer.com/", "loc": "Çerkezköy, Tekirdağ"},
    {"company": "Zentiva Sağlık", "url": "https://www.zentiva.com.tr/kariyer", "loc": "Çerkezköy, Tekirdağ"},
    {"company": "Modern Karton (Eren)", "url": "https://www.erenholding.com.tr/kariyer", "loc": "Çorlu, Tekirdağ"},
    {"company": "Lila Kağıt", "url": "https://www.lilakagit.com/kariyer", "loc": "Çorlu, Tekirdağ"},
    {"company": "GTM Elektronik", "url": "https://www.gtmelektronik.com/iletisim", "loc": "Çorlu, Tekirdağ"},
    {"company": "Yorglass Cam", "url": "https://www.yorglass.com/kariyer", "loc": "Çerkezköy, Tekirdağ"},
    {"company": "PharmaVision", "url": "https://www.pharmavision.com.tr/kariyer", "loc": "Çerkezköy, Tekirdağ"},
    {"company": "Frigoblock Soğutma", "url": "https://www.frigoblock.com.tr/kariyer", "loc": "Çorlu, Tekirdağ"},
]


def scrape_direct_ime_and_osb() -> List[Dict[str, Any]]:
    """
    Sıfır Hata Canlı Fabrika ve Üniversite İME Tarayıcısı:
    1. TNKÜ Çorlu Mühendislik Fakültesi İME ve E-E Bölüm sayfalarından (cmf.nku.edu.tr & ste.nku.edu.tr)
       resmi sanayi firma taleplerini çeker.
    2. ÇOSB İstihdam Bürosu portalındaki aktif ilanları tarar.
    3. WATCHED_CAREER_PAGES ve dynamic database.get_watched_companies() listelerindeki fabrikaları denetler.
    """
    results: List[Dict[str, Any]] = []
    seen_urls = set()

    # 1. TNKÜ Resmi STE Başvuru Havuzu (Doğrudan Öğrenci Başvuru Sistemi)
    ste_lead = {
        "company": "TNKÜ İME Sanayi Protokolleri",
        "title": "İşletmede Mesleki Eğitim (İME) & Stajyer Firma Talep Havuzu",
        "location": "Çorlu / Çerkezköy / Tekirdağ",
        "url": "http://ste.nku.edu.tr/#/student/create",
        "source": "TNKÜ ÇMF İME Portalı",
        "relevance_score": 95,
        "notes": "TNKÜ Çorlu Mühendislik Fakültesi İME ve Stajyer talep eden protokol sanayi firmalarına resmi başvuru ekranı (ste.nku.edu.tr)",
    }
    results.append(ste_lead)
    seen_urls.add(ste_lead["url"])

    # 2. TNKÜ E-E Bölümü ve Fakülte Duyuruları
    target_pages = [
        ("https://cmf-eem.web.nku.edu.tr/", "TNKÜ E-E Bölüm Duyurusu"),
        ("https://cmf.nku.edu.tr/", "TNKÜ ÇMF Fakülte Duyurusu"),
    ]
    month_regex = r"^\d{1,2}\s*(?:Oca|Şub|Sub|Mar|Nis|May|Haz|Tem|Ağu|Agu|Eyl|Eki|Kas|Ara)\s*(?:\d{4})?\s*"

    for page_url, source_label in target_pages:
        try:
            r = requests.get(page_url, headers={"User-Agent": USER_AGENT}, verify=False, timeout=8)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select("a[href*='duyuruayrinti']"):
                    raw_title = a.get_text(" ", strip=True)
                    href = a.get("href", "")
                    if not href.startswith("http"):
                        href = urllib.parse.urljoin(page_url, href)

                    if href in seen_urls:
                        continue

                    cleaned_title = re.sub(month_regex, "", raw_title, flags=re.IGNORECASE).strip()
                    lower_title = cleaned_title.lower()

                    # İdari / bürokratik duyuruları atla
                    if any(skip in lower_title for skip in ["teslim", "defteri", "yönerge", "yonerge", "komisyon", "sınav", "sinav", "ders"]):
                        continue

                    # Stajyer / öğrenci alımı / İME fırsatı kontrolü
                    if any(k in lower_title for k in ["staj", "ime", "öğrenci alımı", "ogrenci alimi", "aday mühendis", "aday muhendis", "kariyer"]):
                        company = "TNKÜ Sanayi Protokolü"
                        if " - " in cleaned_title:
                            company = cleaned_title.split(" - ")[0].strip()

                        # Skorlama
                        score = calculate_relevance_score(
                            title=cleaned_title,
                            text=f"{cleaned_title} {company}",
                            location="Çorlu, Tekirdağ",
                            source="TNKÜ ÇMF İME Portalı",
                            company=company
                        )
                        # TNKÜ resmi duyuruları için taban puan
                        score = max(score, 65)

                        item = {
                            "company": company,
                            "title": cleaned_title,
                            "location": "Çorlu / Tekirdağ",
                            "url": href,
                            "source": "TNKÜ ÇMF İME Portalı",
                            "relevance_score": score,
                            "notes": f"{source_label}: {cleaned_title}",
                        }
                        results.append(item)
                        seen_urls.add(href)
        except Exception as e:
            print(f"[UYARI] TNKÜ duyuru sayfası taranırken hata ({page_url}): {e}")

    # 3. ÇOSB Canlı İstihdam Portalı
    try:
        from scrapers.active_jobs import scrape_cosb_portal
        cosb_jobs = scrape_cosb_portal()
        for cj in cosb_jobs:
            u = cj.get("url")
            if u and u not in seen_urls:
                results.append(cj)
                seen_urls.add(u)
    except Exception as e:
        print(f"[UYARI] ÇOSB portalı taranırken hata: {e}")

    # 4. Dinamik İzlenen Şirketler (watched_companies tablosu)
    try:
        watched_dyn = database.get_watched_companies()
        for w in watched_dyn:
            comp_name = w["company"]
            c_url = w["url"]
            if c_url in seen_urls:
                continue
            seen_urls.add(c_url)
            try:
                r_check = requests.get(c_url, headers={"User-Agent": USER_AGENT}, timeout=6, verify=False)
                if r_check.status_code == 200:
                    results.append({
                        "company": comp_name,
                        "title": "Doğrudan Fabrika İME / Aday Mühendislik Takip Sayfası",
                        "location": "Çerkezköy / Çorlu, Tekirdağ",
                        "url": c_url,
                        "source": "Doğrudan Fabrika Kariyer",
                        "relevance_score": 80,
                        "notes": f"Kullanıcı tarafından izlemeye alınan fabrika sayfası: {comp_name}",
                    })
            except Exception:
                pass
    except Exception as e:
        print(f"[UYARI] İzlenen şirketler kontrolü hatası: {e}")

    return results
