import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Proje dizinini mutlak yol (absolute path) olarak sabitle
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env dosyasını mutlak yoldan yükle
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ==========================================
# TNKÜ E-E MÜHENDİSLİĞİ İME & STAJ KONFİGÜRASYONU
# ==========================================

# Hedef Sanayi & İlçe Lokasyonları (Trakya / Tekirdağ Havzası)
LOCATIONS = [
    "Çorlu",
    "Çerkezköy",
    "Ergene",
    "Velimeşe",
    "Tekirdağ",
    "Muratlı",
    "Kapaklı",
    "Süleymanpaşa",
    "Marmaraereğlisi",
]

# Pozisyon ve Arama Terimleri
SEARCH_TERMS = [
    "İşletmede Mesleki Eğitim",
    "İME",
    "Uzun Dönem Staj",
    "Uzun Dönem Stajyer",
    "Aday Mühendis",
    "Elektrik Mühendisi Stajyer",
    "Otomasyon Staj",
    "Elektrik Elektronik Stajyer",
    "Bakım Onarım Stajyer",
    "Ar-Ge Stajyer",
]

# Elektrik-Elektronik Mühendisliği Uygunluk / Skorlama Anahtar Kelimeleri ve Ağırlıkları
EE_KEYWORD_WEIGHTS = {
    # Doğrudan E-E ve Otomasyon Ana Dalları
    "elektrik-elektronik": 35,
    "elektrik elektronik": 35,
    "elektrik mühendisi": 30,
    "elektronik mühendisi": 30,
    "otomasyon": 25,
    "plc": 25,
    "scada": 20,
    "mekatronik": 20,
    "elektrik bakım": 25,
    "bakım onarım": 18,
    "pano": 20,
    "eplan": 18,
    "autocad": 10,
    "gömülü": 25,
    "embedded": 25,
    "donanım": 20,
    "hardware": 20,
    "yüksek gerilim": 20,
    "trafo": 18,
    "şalt": 15,
    "enerji": 15,
    "sürücü": 15,
    "inverter": 15,
    "ar-ge": 15,
    "r&d": 15,
    "test mühendisi": 15,
    "kalite mühendisi": 12,
    "üretim mühendisi": 12,
    "elektrik teknik": 20,
    "elektrik": 12,
    "elektronik": 12,
}

# Telegram Bildirim Ayarları
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Sunucu & Tarama Zamanlayıcı Ayarları (Server Mode)
SCAN_INTERVAL_HOURS = int(os.getenv("SCAN_INTERVAL_HOURS", "6"))
SERVER_MODE = os.getenv("SERVER_MODE", "polling")  # "polling" veya "webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", "8080"))

# Veritabanı Dosya Yolu (Mutlak Yol Sabitlemesi - CWD Bağımsız)
raw_db_path = os.getenv("DB_PATH", "ime_leads.db")
if os.path.isabs(raw_db_path):
    DB_PATH = raw_db_path
else:
    DB_PATH = os.path.join(BASE_DIR, raw_db_path)

# Tarama & Ağ İstek Ayarları
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Alakasız / Mühendislik Dışı Meslekler (Kesin Eleme Listesi)
NEGATIVE_KEYWORDS = [
    "insan kaynakları", "human resources", "ik staj", "ik uzman",
    "finans", "muhasebe", "accounting", "finance", "mali işler",
    "lojistik", "logistics", "depo", "sevkiyat", "ithalat", "ihracat", "dış ticaret",
    "hukuk", "avukat", "legal",
    "pazarlama", "marketing", "sosyal medya", "grafik", "tasarımcı", "reklam",
    "kurumsal iletişim", "halkla ilişkiler",
    "satış temsilcisi", "satış danışmanı", "satış elemanı", "kasiyer", "mağaza",
    "çağrı merkezi", "call center", "müşteri temsilcisi",
    "gayrimenkul", "emlak", "garson", "şoför", "aşçı", "mutfak",
    "güvenlik", "temizlik", "kurye", "vale",
    "diş hekimi", "dental", "veteriner", "eczacı", "eczane", "hemşire", "hasta kabul",
    "doktor", "sağlık personeli", "çocuk gelişim", "öğretmen"
]

WRONG_CITIES = [
    "izmir", "ankara", "bursa", "antalya", "adana", "eskişehir",
    "kayseri", "konya", "gaziantep", "trabzon", "samsun", "diyarbakır"
]


def calculate_relevance_score(
    title: str,
    text: str = "",
    location: str = "",
    source: str = "",
    created_at: str = None
) -> int:
    """
    TNKÜ E-E Mühendisliği 4. sınıf İME öğrencisi için hassas puanlama algoritması:
    - Mühendislik dışı bölümleri (İK, Finans, Lojistik vb.) doğrudan 0 puanla eler.
    - E-E, Otomasyon, PLC, Bakım ve İME terimlerine yüksek öncelik verir.
    - Canlı kariyer portallarındaki aktif ilanlara ve güncelliğe (tazeliğe) ek puan katar.
    - 0 - 100 arasında normalize bir uygunluk skoru döndürür.
    """
    title_lower = title.lower()
    combined_content = f"{title} {text}".lower()

    # 1. Alakasız meslekleri doğrudan ele
    for neg in NEGATIVE_KEYWORDS:
        if neg in title_lower:
            return 0

    # 2. Hedef dışı uzak şehirler (Tekirdağ / Trakya geçmiyorsa ele)
    loc_clean = (location or "").lower()
    if any(wc in loc_clean for wc in WRONG_CITIES) and not any(loc.lower() in loc_clean for loc in LOCATIONS):
        return 0

    score = 0

    # 3. Anahtar kelime eşleşmeleri
    for kw, weight in EE_KEYWORD_WEIGHTS.items():
        if len(kw) <= 4:
            if re.search(r"\b" + re.escape(kw) + r"\b", combined_content):
                score += weight
        else:
            if kw in combined_content:
                score += weight

    # 4. Program ve İlan Tipi Ağırlıkları
    if re.search(r"\bime\b", title_lower) or "işletmede mesleki eğitim" in title_lower:
        score += 35
    elif "aday mühendis" in title_lower or "candidate engineer" in title_lower:
        score += 25
    elif "uzun dönem" in title_lower:
        score += 20
    elif "staj" in title_lower or "intern" in title_lower:
        score += 15

    # 5. Hedef Lokasyon Eşleşmesi (+15 bonus)
    loc_lower = f"{location} {combined_content}".lower()
    if any(loc.lower() in loc_lower for loc in LOCATIONS):
        score += 15

    # 6. Canlı ve Aktif İlan Bonusu (+15 bonus - Şu an işe alım yapan platformlar)
    if source and "OSB Rehberi" not in source:
        score += 15

    # 7. Güncellik / Tazelik Bonusu
    if created_at:
        try:
            created_dt = datetime.strptime(str(created_at).split(".")[0], "%Y-%m-%d %H:%M:%S")
            diff_days = abs((datetime.now() - created_dt).total_seconds()) / 86400.0
            if diff_days <= 3.0:
                score += 15
            elif diff_days <= 7.0:
                score += 10
            elif diff_days <= 14.0:
                score += 5
        except Exception:
            pass

    # Maksimum 100 puan ile sınırla
    return min(100, max(0, score))
