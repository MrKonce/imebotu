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
    "gömülü sistemler": 35,
    "gömülü sistem": 35,
    "embedded": 35,
    "stm32": 30,
    "esp32": 30,
    "pcb": 30,
    "altium": 30,
    "iha": 30,
    "aviyonik": 30,
    "radar": 30,
    "mikrodenetleyici": 30,
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
    "donanım": 20,
    "hardware": 20,
    "yüksek gerilim": 25,
    "elektrik tesisleri": 25,
    "güç elektroniği": 25,
    "sensör": 25,
    "sensor": 25,
    "haberleşme": 25,
    "rf": 25,
    "trafo": 18,
    "enerji": 15,
    "sürücü": 15,
    "inverter": 15,
    "ar-ge": 15,
    "elektrik": 15,
    "elektronik": 15,
}

# Kabul Edilebilir Minimum Uygunluk Skoru Barajı
MIN_RELEVANCE_SCORE = 50

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
    "doktor", "sağlık personeli", "çocuk gelişim", "öğretmen", "parfüm", "gıda stajyeri",
    "iş sağlığı ve güvenliği", "iş sağlığı", "is sagligi", "isg", "iş güvenliği", "is guvenligi",
    "kalite stajyeri", "kalite kontrol stajyeri", "kalite stajyer", "kalite kontrol stajyer",
    "üretim operatörü", "uretim operatoru", "operatör", "operator",
    "çevre mühendisi", "cevre muhendisi", "ziraat", "tütün",

    # E-E Harici Diğer Mühendislik ve Bölüm Stajları (Kesin Eleme)
    "tekstil mühendisi", "tekstil stajyer", "tekstil staj", "tekstil muhendisi",
    "kimya mühendisi", "kimya stajyer", "kimya staj", "kimya muhendisi",
    "gıda mühendisi", "gıda staj", "gida muhendisi",
    "inşaat mühendisi", "inşaat stajyer", "insaat muhendisi", "mimarlık", "mimarlik",
    "endüstri mühendisi stajyeri", "endüstri mühendisi", "endustri muhendisi",
    "kalite kontrol operatörü", "vasıfsız", "vasifsiz", "forklift",
    "cnc operatörü", "cnc", "kaynakçı", "kaynakci", "tornacı", "tornaci",
    "paketleme", "depo elemanı"
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
    "yedaş", "yedas", "yeşilırmak", "yesilirmak",  # Karadeniz (Samsun, Ordu, Çorum, Sinop, Amasya)
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


def validate_strict_location(
    raw_location: str,
    title: str = "",
    company: str = "",
    body_text: str = ""
) -> tuple[bool, str]:
    """
    Kullanıcının talimatlarına göre Katı Beyaz Liste (Strict Whitelist) ve Kara Liste Doğrulayıcı:
    1. DOM/API'den gelen asıl lokasyon string'i boş veya <3 karakter ise doğrudan ELENİR.
    2. 'Türkiye Geneli', 'Tüm Şehirler', '+... il daha' veya çoklu ilanlarda SADECE body_text'te
       Trakya sanayi ilçeleri (Çorlu, Çerkezköy, Ergene vb.) geçiyorsa izin verilir; aksi halde ELENİR.
    3. Başlıkta veya şirket isminde Adana, Samsun, YEDAŞ vb. bölgesel firmalar ELENİR.
    4. DOM lokasyonunda Tekirdağ harici yabancı il varsa ve Tekirdağ/Trakya ilçesi yoksa ELENİR.
    """
    if not raw_location or len(raw_location.strip()) < 3:
        return False, "Lokasyon Yok/Geçersiz (DOM/API lokasyonu bulunamadı)"

    loc_norm = normalize_tr(raw_location)
    title_norm = normalize_tr(title)
    comp_norm = normalize_tr(company)
    body_norm = normalize_tr(body_text)

    # 1. Başlık ve Şirket Adı Kontrolü (YEDAŞ, Toroslar, Samsun, Ordu vb. doğrudan red)
    for firm in WRONG_REGIONAL_FIRMS:
        firm_norm = normalize_tr(firm)
        if firm_norm in title_norm or firm_norm in comp_norm or firm_norm in loc_norm:
            return False, f"Alakasız Bölgesel Firma/Başlık ({firm})"

    for wc in WRONG_CITIES:
        wc_norm = normalize_tr(wc)
        pattern = r"\b" + re.escape(wc_norm) + r"\b"
        if re.search(pattern, title_norm) or re.search(pattern, comp_norm):
            return False, f"Başlık veya Şirkette Tekirdağ Dışı Şehir ({wc})"

    # 2. Lokasyonda Türkiye Geneli / Tüm Şehirler / +... il daha / Çoklu Şehir kontrolü
    is_multi_city = False
    for bl in MULTI_CITY_BLACKLIST:
        bl_norm = normalize_tr(bl)
        if bl_norm in loc_norm:
            is_multi_city = True
            break

    if re.search(r"\+\d+\s*il", loc_norm) or loc_norm.count(",") > 3 or len(loc_norm) > 90:
        is_multi_city = True

    # 3. Katı Beyaz Liste (Strict Whitelist) Kontrolü
    matched_loc = None
    for white in STRICT_LOCATIONS_WHITELIST:
        white_norm = normalize_tr(white)
        pattern = r"\b" + re.escape(white_norm) + r"\b"
        if re.search(pattern, loc_norm):
            matched_loc = white
            break

    # 4. Lokasyonda Tekirdağ Dışı İl Var mı?
    has_wrong_city_in_loc = False
    found_wrong_city = ""
    for wc in WRONG_CITIES:
        wc_norm = normalize_tr(wc)
        pattern = r"\b" + re.escape(wc_norm) + r"\b"
        if re.search(pattern, loc_norm):
            has_wrong_city_in_loc = True
            found_wrong_city = wc
            break

    # Trakya Hedef Sanayi İlçeleri (Body Text kurtarma kontrolü için)
    trakya_districts = [
        "corlu", "çorlu", "cerkezkoy", "çerkezköy", "ergene", "velimese", "velimeşe",
        "kapakli", "kapaklı", "suleymanpasa", "süleymanpaşa", "marmaraereglisi", "marmaraereğlisi",
        "muratli", "muratlı", "avrupa serbest bolgesi", "avrupa serbest bölgesi", "asb",
        "cosb", "çosb", "corlu osb", "çorlu osb", "cerkezkoy osb", "çerkezköy osb"
    ]

    # Eğer çoklu şehir ilanıysa veya lokasyonda hem yabancı il hem de Tekirdağ varsa:
    if is_multi_city or (has_wrong_city_in_loc and matched_loc):
        has_trakya_district_in_body = any(
            re.search(r"\b" + re.escape(td) + r"\b", body_norm) for td in trakya_districts
        )
        if has_trakya_district_in_body:
            return True, matched_loc or "çorlu/çerkezköy (gövde doğrulandı)"
        else:
            return False, f"Çoklu Şehir İlanı ve Gövdede Trakya İlçesi Yok ({found_wrong_city or 'çoklu'})"

    if has_wrong_city_in_loc and not matched_loc:
        return False, f"Lokasyonda Tekirdağ Dışı İl Var ({found_wrong_city})"

    if not matched_loc:
        return False, "Beyaz Listede Yok (Tekirdağ/Çorlu/Çerkezköy içermiyor)"

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
    TNKÜ E-E 4. sınıf İME öğrencisi için sert ve tavizsiz puanlama motoru (v2.1):
    1. Katı Lokasyon Doğrulaması: validate_strict_location geçemeyen ilanların SKORU 0'DIR.
    2. Kıdem/Rol: Şantiye şefi, yönetici, kıdemli, tekstil/kimya/inşaat mühendisliği ise PUAN = 0 (ELENİR).
    3. Zorunlu EE Şartı: EE_KEYWORD_WEIGHTS anahtar kelimelerinden EN AZ BİRİ geçmelidir. Geçmiyorsa PUAN = 0.
    4. Rol Uyumu: İME, Staj, Aday Mühendis pozisyonları. TNKÜ/OSB/Vizyoner Genç kaynaklarında
       junior/yeni mezun roller de değerlendirmeye alınır.
    """
    # 1. Katı Lokasyon Doğrulaması (İstisnasız her kaynak için zorunlu)
    is_valid_loc, _ = validate_strict_location(
        raw_location=location,
        title=title,
        company=company,
        body_text=text
    )
    if not is_valid_loc:
        return 0

    title_norm = normalize_tr(title)
    text_norm = normalize_tr(text)
    loc_norm = normalize_tr(location)
    source_norm = normalize_tr(source)
    combined = f"{title_norm} {text_norm}"

    # 2. Kıdemli veya alakasız meslekleri doğrudan ele (NEGATIVE_KEYWORDS)
    for neg in NEGATIVE_KEYWORDS:
        neg_norm = normalize_tr(neg)
        pattern = r"\b" + re.escape(neg_norm) + r"\b"
        if re.search(pattern, title_norm) or re.search(pattern, text_norm):
            return 0

    # 3. ZORUNLU E-E VE OTOMASYON KELİMESİ KONTROLÜ
    # Başlıkta veya açıklamada EE_KEYWORD_WEIGHTS'ten EN AZ BİR anahtar kelime yoksa KESİNLİKLE 0!
    has_ee_keyword = False
    for kw in EE_KEYWORD_WEIGHTS:
        kw_norm = normalize_tr(kw)
        if len(kw_norm) <= 4:
            if re.search(r"\b" + re.escape(kw_norm) + r"\b", combined):
                has_ee_keyword = True
                break
        else:
            if kw_norm in combined:
                has_ee_keyword = True
                break

    if not has_ee_keyword:
        return 0

    # 4. Öğrenci / İME / Stajyer Format Kontrolü & TNKÜ/OSB/Vizyoner Genç Kuralı
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
    )

    is_tnku_or_osb = any(
        k in source_norm for k in ["tnku", "nku", "osb", "cosb", "vizyoner", "direct", "fabrika"]
    )

    is_junior_ee = (
        is_tnku_or_osb and (
            "junior" in title_norm
            or "yeni mezun" in title_norm
            or "mühendis" in title_norm
            or "muhendis" in title_norm
            or "tekniker" in title_norm
        )
    )

    if not is_intern and not is_junior_ee:
        return 0

    score = 0

    # 5. İME & Stajyerlik Türü Taban Puanları
    if re.search(r"\bime\b", title_norm) or "işletmede mesleki eğitim" in title_norm:
        score += 45
    elif "aday mühendis" in title_norm or "candidate engineer" in title_norm:
        score += 40
    elif "uzun dönem" in title_norm:
        score += 35
    elif "staj" in title_norm or "intern" in title_norm:
        score += 30
    elif is_junior_ee:
        score += 30

    # 6. E-E ve Otomasyon Alan Uyumu Puanları
    for kw, weight in EE_KEYWORD_WEIGHTS.items():
        kw_norm = normalize_tr(kw)
        if len(kw_norm) <= 4:
            if re.search(r"\b" + re.escape(kw_norm) + r"\b", combined):
                score += weight
        else:
            if kw_norm in combined:
                score += weight

    # 7. Bölge Uyumu (+15 puan - Sadece Ana Lokasyona Göre)
    if any(normalize_tr(loc) in loc_norm for loc in LOCATIONS):
        score += 15

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
