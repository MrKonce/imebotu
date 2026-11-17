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

# SADECE Okula / Kampüse Yakın Hedef Sanayi & İlçe Lokasyonları (Trakya / Tekirdağ Havzası)
LOCATIONS = [
    "çorlu",
    "çerkezköy",
    "ergene",
    "velimeşe",
    "tekirdağ",
    "muratlı",
    "kapaklı",
    "süleymanpaşa",
    "marmaraereğlisi",
]

# Pozisyon ve Arama Terimleri (Öğrenci & İME Odaklı)
SEARCH_TERMS = [
    "İşletmede Mesleki Eğitim",
    "İME",
    "Uzun Dönem Staj",
    "Uzun Dönem Stajyer",
    "Aday Mühendis",
    "Elektrik Mühendisi Stajyer",
    "Otomasyon Stajyer",
    "Elektrik Elektronik Stajyer",
    "Bakım Onarım Stajyer",
    "Ar-Ge Stajyer",
]

# Elektrik-Elektronik Mühendisliği Uygunluk / Skorlama Anahtar Kelimeleri ve Ağırlıkları
EE_KEYWORD_WEIGHTS = {
    "elektrik-elektronik": 35,
    "elektrik elektronik": 35,
    "elektrik mühendisi": 25,
    "elektronik mühendisi": 25,
    "otomasyon": 30,
    "plc": 30,
    "scada": 25,
    "mekatronik": 25,
    "elektrik bakım": 25,
    "bakım onarım": 20,
    "pano": 20,
    "eplan": 20,
    "autocad": 10,
    "gömülü": 25,
    "embedded": 25,
    "donanım": 20,
    "hardware": 20,
    "yüksek gerilim": 20,
    "trafo": 18,
    "enerji": 15,
    "sürücü": 15,
    "inverter": 15,
    "ar-ge": 15,
    "test": 12,
    "üretim": 10,
    "elektrik": 15,
    "elektronik": 15,
}

# Telegram Bildirim Ayarları
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Sunucu & Tarama Zamanlayıcı Ayarları (Server Mode)
SCAN_INTERVAL_HOURS = int(os.getenv("SCAN_INTERVAL_HOURS", "6"))
SERVER_MODE = os.getenv("SERVER_MODE", "polling")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", "8080"))

# Veritabanı Dosya Yolu
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

# 1. Alakasız Meslekler ve Öğrenciye Uygun Olmayan Kıdemli Pozisyonlar (KESİN ELEME)
NEGATIVE_KEYWORDS = [
    # Kıdemli / Yönetici / Şantiye (Öğrenci İME yapamaz!)
    "şantiye şefi", "şantiye", "müdür", "yönetici", "kıdemli", "senior",
    "direktör", "şef", "başmühendis", "bölge müdürü", "proje müdürü",

    # Mühendislik Dışı Sektörler
    "insan kaynakları", "human resources", "ik staj", "ik uzman", "insan ve kültür",
    "finans", "muhasebe", "accounting", "finance", "mali işler", "ön muhasebe",
    "lojistik", "logistics", "depo", "sevkiyat", "ithalat", "ihracat", "dış ticaret",
    "hukuk", "avukat", "legal",
    "pazarlama", "marketing", "sosyal medya", "grafik", "tasarımcı", "reklam",
    "kurumsal iletişim", "halkla ilişkiler",
    "satış temsilcisi", "satış danışmanı", "satış elemanı", "kasiyer", "mağaza",
    "çağrı merkezi", "call center", "müşteri temsilcisi", "satış",
    "gayrimenkul", "emlak", "garson", "şoför", "aşçı", "mutfak",
    "güvenlik", "temizlik", "kurye", "vale",
    "diş hekimi", "dental", "veteriner", "eczacı", "eczane", "hemşire", "hasta kabul",
    "doktor", "sağlık personeli", "çocuk gelişim", "öğretmen", "parfüm", "gıda stajyeri"
]

# 2. Katı Beyaz Liste (Strict Whitelist) - Sadece Tekirdağ ve İlçeleri
STRICT_LOCATIONS_WHITELIST = [
    "tekirdağ", "tekirdag",
    "çorlu", "corlu",
    "çerkezköy", "cerkezkoy",
    "ergene",
    "kapaklı", "kapakli",
    "süleymanpaşa", "suleymanpasa",
    "marmaraereğlisi", "marmaraereglisi",
    "muratlı", "muratli",
    "velimeşe", "velimese",
    "hayrabolu",
    "saray",
    "şarköy", "sarkoy",
]

# Çoklu / Sahte Şehir ve Türkiye Geneli Kara Listesi
MULTI_CITY_BLACKLIST = [
    "türkiye geneli", "turkiye geneli",
    "tüm şehirler", "tum sehirler",
    "tüm iller", "tum iller",
    "81 il", "tum turkiye", "tüm türkiye",
    "tümü", "tumu",
    "il daha",
]

# Tekirdağ / Trakya Bölgesi Dışındaki Elektrik Dağıtım / Alakasız Bölgesel Şirketler (Kesin Reddet)
WRONG_REGIONAL_FIRMS = [
    "yedaş", "yedas",  # Karadeniz (Samsun, Ordu, Çorum, Sinop, Amasya)
    "toroslar",        # Güney (Adana, Mersin, Hatay, Gaziantep, Osmaniye, Kilis)
    "ayedaş", "ayedas", "bedaş", "bedas",
    "başkent edaş", "baskent edas", "başkent elektrik", "baskent elektrik",
    "gdz", "gediz", "aydem", "adm elektrik",
    "dicle edaş", "dicle edas", "dicle elektrik",
    "çoruh edaş", "coruh edas", "çoruh elektrik", "coruh elektrik",
    "aras edaş", "aras edas", "aras elektrik",
    "fırat edaş", "firat edas", "fırat elektrik", "firat elektrik",
    "osmangazi edaş", "oedaş", "oedas",
    "uludağ edaş", "uedaş", "uedas",
    "çamlıbel edaş", "cedaş", "cedas",
    "akdeniz edaş", "akdeniz elektrik",
    "meram edaş", "meram edas", "meram elektrik",
    "dh teknik", "şara enerji", "sara enerji", "akbaş enerji", "green diamond", "remax"
]

# 80 Tekirdağ Dışı İl (Tekirdağ harici kesin eleme listesi)
WRONG_CITIES = [
    "adana", "adıyaman", "afyon", "afyonkarahisar", "ağrı", "aksaray", "amasya",
    "ankara", "antalya", "ardahan", "artvin", "aydın", "balıkesir", "bartın",
    "batman", "bayburt", "bilecik", "bingöl", "bitlis", "bolu", "burdur",
    "bursa", "çanakkale", "çankırı", "çorum", "denizli", "diyarbakır", "düzce",
    "elazığ", "erzincan", "erzurum", "eskişehir", "gaziantep", "giresun",
    "gümüşhane", "hakkari", "hatay", "iğdır", "isparta", "izmir",
    "kahramanmaraş", "karabük", "karaman", "kars", "kastamonu", "kayseri",
    "kırıkkale", "kırklareli", "kırşehir", "kilis", "kocaeli", "konya",
    "kütahya", "malatya", "manisa", "mardin", "mersin", "muğla", "muş",
    "nevşehir", "niğde", "ordu", "osmaniye", "rize", "sakarya", "samsun",
    "siirt", "sinop", "sivas", "şanlıurfa", "şırnak", "tokat", "trabzon",
    "tunceli", "uşak", "van", "yalova", "yozgat", "zonguldak"
]


def normalize_tr(text: str) -> str:
    """Türkçe İ, I, Ş, Ğ, Ü, Ö, Ç karakterlerini standart küçük harfe dönüştürür."""
    if not text:
        return ""
    mapping = {
        "İ": "i", "I": "ı", "ı": "i",
        "Ş": "ş", "ş": "s",
        "Ğ": "ğ", "ğ": "g",
        "Ü": "ü", "ü": "u",
        "Ö": "ö", "ö": "o",
        "Ç": "ç", "ç": "c",
    }
    res = text
    for upper, lower in mapping.items():
        res = res.replace(upper, lower)
    return res.lower()


def validate_strict_location(raw_location: str, title: str = "", company: str = "") -> tuple[bool, str]:
    """
    Kullanıcının talimatlarına göre Katı Beyaz Liste (Strict Whitelist) ve Kara Liste Doğrulayıcı:
    1. DOM/API'den gelen asıl lokasyon string'inde whitelist kelimesi zorunludur:
       ['tekirdağ', 'çorlu', 'çerkezköy', 'ergene', 'kapaklı', 'süleymanpaşa', 'marmaraereğlisi', ...]
    2. 'Türkiye Geneli', 'Tüm Şehirler', '+... il daha' veya 3'ten fazla il içeren çoklu ilanlar ELENİR.
    3. Başlıkta veya şirket isminde Adana, Samsun, YEDAŞ vb. bölgesel firmalar ELENİR.
    """
    loc_norm = normalize_tr(raw_location)
    title_norm = normalize_tr(title)
    comp_norm = normalize_tr(company)

    # 1. Başlık ve Şirket Adı Kontrolü (YEDAŞ, Toroslar, Adana, Samsun vb. doğrudan red)
    for firm in WRONG_REGIONAL_FIRMS:
        firm_norm = normalize_tr(firm)
        if firm_norm in title_norm or firm_norm in comp_norm or firm_norm in loc_norm:
            return False, f"Alakasız Bölgesel Firma/Başlık ({firm})"

    for wc in WRONG_CITIES:
        wc_norm = normalize_tr(wc)
        pattern = r"\b" + re.escape(wc_norm) + r"\b"
        if re.search(pattern, title_norm) or re.search(pattern, comp_norm):
            return False, f"Başlık veya Şirkette Tekirdağ Dışı Şehir ({wc})"

    # 2. Lokasyonda Türkiye Geneli / Tüm Şehirler / +... il daha kontrolü
    for bl in MULTI_CITY_BLACKLIST:
        bl_norm = normalize_tr(bl)
        if bl_norm in loc_norm:
            return False, f"Genel / Çoklu Şehir İlanı ({bl})"

    if re.search(r"\+\d+\s*il", loc_norm):
        return False, "Çoklu Şehir İlanı (+il)"

    # Çoklu şehir listesi kontrolü (Örn: Adana, Adıyaman, ... Tekirdağ)
    if loc_norm.count(",") > 3 or len(loc_norm) > 90:
        return False, "81 Şehir Yayını (Aşırı uzun lokasyon)"

    # 3. Katı Beyaz Liste (Strict Whitelist) Kontrolü
    matched_loc = None
    for white in STRICT_LOCATIONS_WHITELIST:
        white_norm = normalize_tr(white)
        pattern = r"\b" + re.escape(white_norm) + r"\b"
        if re.search(pattern, loc_norm):
            matched_loc = white
            break

    if not matched_loc:
        return False, "Beyaz Listede Yok (Tekirdağ/Çorlu/Çerkezköy içermiyor)"

    # 4. Lokasyonda Tekirdağ harici başka bir il adı geçiyor mu? (Örn: 'Adana, Tekirdağ')
    for wc in WRONG_CITIES:
        wc_norm = normalize_tr(wc)
        pattern = r"\b" + re.escape(wc_norm) + r"\b"
        if re.search(pattern, loc_norm):
            return False, f"Lokasyonda Tekirdağ Dışı İl Var ({wc})"

    return True, matched_loc


def calculate_relevance_score(
    title: str,
    text: str = "",
    location: str = "",
    source: str = "",
    created_at: str = None,
    company: str = ""
) -> int:
    """
    TNKÜ E-E 4. sınıf İME öğrencisi için sert ve tavizsiz puanlama motoru:
    1. Katı Lokasyon Doğrulaması: validate_strict_location geçemeyen ilanların SKORU 0'DIR.
    2. Kıdem/Rol: Şantiye şefi, yönetici, kıdemli ise PUAN = 0 (ELENİR).
    3. Rol Uyumu: İME, Staj, Aday Mühendis, Öğrenci pozisyonları zirveye taşınır.
    """
    # OSB Rehberi fabrikaları zaten yerel üretim tesisleridir
    if "OSB Rehberi" not in source:
        is_valid_loc, _ = validate_strict_location(raw_location=location, title=title, company=company)
        if not is_valid_loc:
            return 0

    title_norm = normalize_tr(title)
    text_norm = normalize_tr(text)
    loc_norm = normalize_tr(location)
    combined = f"{title_norm} {text_norm} {loc_norm}"

    # 1. Kıdemli veya alakasız meslekleri doğrudan ele
    for neg in NEGATIVE_KEYWORDS:
        neg_norm = normalize_tr(neg)
        if neg_norm in title_norm or neg_norm in text_norm:
            return 0

    # 2. Lokasyon Kontrolü: Kesinlikle Tekirdağ / Çorlu / Çerkezköy havzasında olmalı
    if any(normalize_tr(wc) in combined for wc in WRONG_CITIES):
        # Tekirdağ açıkça geçmiyorsa ele
        if not any(normalize_tr(loc) in combined for loc in LOCATIONS):
            return 0

    # Hedef lokasyonlardan en az biri açıkça doğrulanmalı (OSB hedefleri zaten lokasyonludur)
    is_valid_location = any(normalize_tr(loc) in combined for loc in LOCATIONS)
    if not is_valid_location and "OSB Rehberi" not in source:
        return 0

    # 3. Öğrenci / İME / Stajyer Format Kontrolü (HAYATİ ÖNEMDE)
    is_intern = (
        re.search(r"\bime\b", title_norm)
        or "işletmede mesleki eğitim" in title_norm
        or "staj" in title_norm
        or "intern" in title_norm
        or "aday mühendis" in title_norm
        or "candidate engineer" in title_norm
        or "öğrenci" in title_norm
        or "genç yetenek" in title_norm
        or "uzun dönem" in title_norm
        or "OSB Rehberi" in source  # OSB hedefleri zaten öğrenci İME başvuru fabrikalarıdır
    )

    # İME/Staj içermeyen tam zamanlı tecrübeli mühendis ilanları elenir
    if not is_intern:
        return 0

    score = 0

    # 4. İME & Stajyerlik Türü Puanları
    if re.search(r"\bime\b", title_norm) or "işletmede mesleki eğitim" in title_norm:
        score += 45
    elif "aday mühendis" in title_norm or "candidate engineer" in title_norm:
        score += 40
    elif "uzun dönem" in title_norm:
        score += 35
    elif "staj" in title_norm or "intern" in title_norm:
        score += 30

    # 5. E-E ve Otomasyon Alan Uyumu
    for kw, weight in EE_KEYWORD_WEIGHTS.items():
        kw_norm = normalize_tr(kw)
        if len(kw_norm) <= 4:
            if re.search(r"\b" + re.escape(kw_norm) + r"\b", combined):
                score += weight
        else:
            if kw_norm in combined:
                score += weight

    # 6. Bölge Uyumu (+15 puan)
    if any(normalize_tr(loc) in combined for loc in LOCATIONS):
        score += 15

    # 7. OSB Kurumsal Fabrikaları (BSH, Arçelik, Lila vb.) Taban İME Puanı
    if "OSB Rehberi" in source:
        score = max(score, 90)

    # 8. Güncellik Bonusu (Son 3 gün: +10)
    if created_at:
        try:
            created_dt = datetime.strptime(str(created_at).split(".")[0], "%Y-%m-%d %H:%M:%S")
            diff_days = abs((datetime.now() - created_dt).total_seconds()) / 86400.0
            if diff_days <= 3.0:
                score += 10
        except Exception:
            pass

    return min(100, max(0, score))
