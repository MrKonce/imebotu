"""
Trakya Sanayi Havzası OSB Kurumsal Üretim Tesisleri Rehberi
(Çerkezköy OSB, Çorlu 1. OSB, Velimeşe OSB, Ergene ve Muratlı OSB)
Özellikle Elektrik-Elektronik, Otomasyon, PLC/SCADA, Bakım-Onarım ve Üretim alanları için kurumsal firmaları barındırır.
"""

from typing import List, Dict, Optional
from config import calculate_relevance_score

OSB_COMPANIES: List[Dict[str, str]] = [
    # ---------------- TNKÜ PROTOKOLLÜ & ÇOSB FİRMALARI ----------------
    {
        "company": "EAE Elektrik A.Ş.",
        "osb": "Çerkezköy / Makine İhtisas OSB",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Elektrik Dağıtım & Busbar & Pano Sistemleri",
        "careers_url": "https://www.eaegroup.com/tr/kariyer",
        "hr_email": "ik@eaegroup.com",
        "description": "Türkiye'nin lider elektrik ekipman üreticisi. Busbar sistemleri, kablo kanalları, endüstriyel pano ve otomasyon. TNKÜ ile resmi mesleki eğitim iş birliği bulunur.",
        "recommended_title": "İşletmede Mesleki Eğitim (İME) / E-E Aday Mühendis",
    },
    {
        "company": "GTM Endüstriyel Elektronik A.Ş.",
        "osb": "Çorlu Sanayi Bölgesi",
        "location": "Çorlu, Tekirdağ",
        "sector": "Endüstriyel Elektronik & Kart Tasarımı & Otomasyon",
        "careers_url": "https://www.gtmelektronik.com/iletisim",
        "hr_email": "info@gtmelektronik.com",
        "description": "Endüstriyel kart tamiri, gömülü donanım, otomasyon sistemleri ve PLC revizyonları. TNKÜ ile protokolü mevcuttur.",
        "recommended_title": "İME Elektronik Donanım & Otomasyon Stajyeri",
    },
    {
        "company": "Sarten Ambalaj Sanayi",
        "osb": "Çorlu / Silivri Sanayi Havzası",
        "location": "Çorlu, Tekirdağ",
        "sector": "Metal & Plastik Ambalaj & Kalıp Otomasyonu",
        "careers_url": "https://www.sarten.com.tr/kariyer",
        "hr_email": "ik@sarten.com.tr",
        "description": "Bölgenin en büyük ambalaj üreticisi. Yüksek hızlı pres hatları, PLC tabanlı hat otomasyonu ve elektrik bakım departmanı.",
        "recommended_title": "İME Bakım & Otomasyon Stajyeri",
    },
    {
        "company": "Yorglass Cam Sanayi",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Endüstriyel Cam & Beyaz Eşya",
        "careers_url": "https://www.yorglass.com/kariyer",
        "hr_email": "ik@yorglass.com",
        "description": "Beyaz eşya camları, fırınlama ve serigrafi hatları otomasyonu, robotik transfer sistemleri ve PLC kontrolü.",
        "recommended_title": "Uzun Dönem Aday Mühendis / İME Elektrik",
    },
    {
        "company": "Frigoblock Soğutma Sistemleri",
        "osb": "Çorlu / Velimeşe Yolu",
        "location": "Çorlu, Tekirdağ",
        "sector": "Endüstriyel Soğutma & Pano İmalatı",
        "careers_url": "https://www.frigoblock.com.tr/kariyer",
        "hr_email": "ik@frigoblock.com.tr",
        "description": "Endüstriyel soğutma cihazları, elektrik güç ve kumanda panosu montajı, kablolama ve PLC otomasyon yazılımları.",
        "recommended_title": "Elektrik Pano Tasarım & İME Stajyeri",
    },
    {
        "company": "BSH Ev Aletleri (Bosch & Siemens)",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Beyaz Eşya & Elektronik & Otomasyon",
        "careers_url": "https://www.bsh-group.com/tr/kariyer",
        "hr_email": "ik.cerkezkoy@bshg.com",
        "description": "Avrupa'nın en büyük üretim tesisi. Yüksek otomasyon, endüstri 4.0, PLC, robotik montaj hatları ve E-E Ar-Ge merkezi.",
        "recommended_title": "İşletmede Mesleki Eğitim (İME) / Uzun Dönem E-E Stajyeri",
    },
    {
        "company": "Arçelik / Beko Çerkezköy Fabrikası",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Elektronik & Beyaz Eşya",
        "careers_url": "https://www.kocariyer.com/",
        "hr_email": "ik@arcelik.com",
        "description": "Akıllı fabrika sistemleri, SMD dizgi hatları, gömülü sistemler, elektrik test altyapısı ve otomatik hat kontrolü.",
        "recommended_title": "Uzun Dönem Aday Mühendis / İME Elektrik-Elektronik",
    },
    {
        "company": "Hema Endüstri A.Ş. (Hattat Holding)",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Otomotiv & Hidrolik & Ağır Makine",
        "careers_url": "https://www.hemaendustri.com.tr/kariyer",
        "hr_email": "ik@hattat.com.tr",
        "description": "Hidrolik direksiyon, transmisyon ve döküm tesisleri. Güç elektroniği, pano, CNC elektrik bakım ve otomasyon sistemleri.",
        "recommended_title": "İME Bakım-Onarım & Otomasyon Stajyeri",
    },
    {
        "company": "Deva Holding Çerkezköy Tesisleri",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "İlaç & Biyoteknoloji",
        "careers_url": "https://www.deva.com.tr/tr/kariyer",
        "hr_email": "insankaynaklari@deva.com.tr",
        "description": "GMP standartlarında yüksek otomasyonlu üretim, SCADA izleme, HVAC otomasyonu ve validasyon süreçleri.",
        "recommended_title": "Otomasyon & Tesis Elektrik İME Stajyeri",
    },
    {
        "company": "Zentiva Sağlık Ürünleri",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "İlaç & Kimya",
        "careers_url": "https://www.zentiva.com.tr/kariyer",
        "hr_email": "ik@zentiva.com.tr",
        "description": "Avrupa standartlarında üretim tesisi, PLC paketleme makineleri, enerji dağıtım panoları ve bina otomasyonu.",
        "recommended_title": "Uzun Dönem Elektrik-Bakım Stajyeri",
    },
    {
        "company": "Jotun Boya Çerkezköy Fabrikası",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Kimya & Endüstriyel Boya",
        "careers_url": "https://www.jotun.com/tr-tr/about-jotun/careers",
        "hr_email": "ik.turkey@jotun.com",
        "description": "Ex-proof elektrik tesisatı, SCADA proses otomasyonu ve endüstriyel proses kontrol sistemleri.",
        "recommended_title": "İME Enstrümantasyon & Elektrik Stajyeri",
    },
    {
        "company": "Sarbak Metal",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Metalurji & Pirinç Üretimi",
        "careers_url": "https://www.sarbak.com.tr/kariyer",
        "hr_email": "ik@sarbak.com.tr",
        "description": "Sürekli döküm ve pres hatları, yüksek gerilim trafo merkezleri, kompanzasyon ve fırın kontrol otomasyonu.",
        "recommended_title": "Yüksek Gerilim & Tesis Elektrik Aday Mühendis",
    },
    {
        "company": "PharmaVision Sanayi",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "İlaç & Sağlık",
        "careers_url": "https://www.pharmavision.com.tr/kariyer",
        "hr_email": "ik@pharmavision.com.tr",
        "description": "Modern steril üretim alanları, otomasyon yazılımları, kalibrasyon ve PLC bakım operasyonları.",
        "recommended_title": "İşletmede Mesleki Eğitim (İME) Elektrik Stajyeri",
    },

    # ---------------- ÇORLU 1. OSB & VELİMEŞE OSB ----------------
    {
        "company": "Modern Karton / Modern Ambalaj (Eren Holding)",
        "osb": "Çorlu 1. OSB",
        "location": "Çorlu, Tekirdağ",
        "sector": "Kağıt & Ambalaj & Enerji Santrali",
        "careers_url": "https://www.erenholding.com.tr/kariyer",
        "hr_email": "ik@modernkarton.com.tr",
        "description": "Büyük ölçekli kağıt üretim makineleri, kojenerasyon/enerji üretim santrali, dev inverter/sürücü panoları ve DCS sistemleri.",
        "recommended_title": "İME Enerji & Otomasyon Stajyeri",
    },
    {
        "company": "Lila Kağıt (Sofia & Maylo Üretimi)",
        "osb": "Çorlu 1. OSB",
        "location": "Çorlu, Tekirdağ",
        "sector": "Hızlı Tüketim & Kağıt Üretimi",
        "careers_url": "https://www.lilakagit.com/kariyer",
        "hr_email": "ik@lilakagit.com",
        "description": "Yüksek hızlı kağıt konverting ve bobin üretim hatları, Siemens/ABB sürücüler, PLC ağları ve kestirimci bakım.",
        "recommended_title": "Uzun Dönem Otomasyon & Pano Stajyeri",
    },
    {
        "company": "Termo Teknik (Stelrad Grubu)",
        "osb": "Çorlu 1. OSB",
        "location": "Çorlu, Tekirdağ",
        "sector": "Isıtma Sistemleri & Panel Radyatör",
        "careers_url": "https://www.termoteknik.com/kariyer",
        "hr_email": "ik@termoteknik.com",
        "description": "Robotik kaynak hatları, elektrostatik toz boya tesisleri, PLC kumanda panoları ve test laboratuvarı.",
        "recommended_title": "Aday Mühendis / İME Elektrik-Elektronik",
    },
    {
        "company": "Flokser Tekstil & Kimya",
        "osb": "Velimeşe OSB",
        "location": "Ergene / Velimeşe, Tekirdağ",
        "sector": "Tekstil & Poliüretan Kimya",
        "careers_url": "https://www.flokser.com.tr/kariyer",
        "hr_email": "ik@flokser.com.tr",
        "description": "Kaplama hatları, reaktör otomasyonu, pano tasarımı ve endüstriyel elektrik altyapısı.",
        "recommended_title": "İME Elektrik Bakım Stajyeri",
    },
    {
        "company": "Trakya Döküm A.Ş. (Soyak Grubu)",
        "osb": "Çorlu - Lüleburgaz Havzası",
        "location": "Çorlu / Büyükkarıştıran, Tekirdağ",
        "sector": "Otomotiv Yan Sanayi & Döküm",
        "careers_url": "https://www.trakyadokum.com.tr/kariyer",
        "hr_email": "ik@trakyadokum.com.tr",
        "description": "Otomatik kalıplama, indüksiyon ergitme ocakları, robotik taşlama hücreleri ve yüksek akım elektrik dağıtımı.",
        "recommended_title": "Uzun Dönem E-E Bakım & Otomasyon Stajyeri",
    },
    {
        "company": "Öztiryakiler Mutfak Donanımları",
        "osb": "Çorlu Sanayi Bölgesi",
        "location": "Çorlu, Tekirdağ",
        "sector": "Endüstriyel Ekipman & Makine",
        "careers_url": "https://www.oztiryakiler.com.tr/kariyer",
        "hr_email": "ik@oztiryakiler.com.tr",
        "description": "Endüstriyel mutfak cihazları, dijital kontrol kartları, rezistans ve güç devreleri, gömülü yazılım.",
        "recommended_title": "Ar-Ge Elektronik & İME Stajyeri",
    },

    # ---------------- ERGENE & MURATLI OSB ----------------
    {
        "company": "Korozo Ambalaj Çorlu Tesisleri",
        "osb": "Ergene 1. OSB",
        "location": "Ergene, Tekirdağ",
        "sector": "Esnek Ambalaj & Ekstrüzyon",
        "careers_url": "https://www.korozo.com.tr/kariyer",
        "hr_email": "ik@korozo.com.tr",
        "description": "Baskı makineleri, film ekstrüzyon hatları, servo motor kontrol sistemleri ve PLC revizyonları.",
        "recommended_title": "İME Otomasyon & Elektrik Stajyeri",
    },
    {
        "company": "Şişecam Otomotiv Camları Fabrikası",
        "osb": "Çorlu / Velimeşe Yolu",
        "location": "Çorlu, Tekirdağ",
        "sector": "Cam & Otomotiv Yan Sanayi",
        "careers_url": "https://www.sisecam.com.tr/tr/kariyer",
        "hr_email": "ik@sisecam.com",
        "description": "Dünya devi cam teknolojisi, fırın sıcaklık kontrol sistemleri, optik kalite kontrol kameraları, PLC & SCADA.",
        "recommended_title": "Aday Mühendis / İME Elektrik-Elektronik",
    },
    {
        "company": "Muratlı Karton Sanayi",
        "osb": "Muratlı OSB",
        "location": "Muratlı, Tekirdağ",
        "sector": "Karton & Kağıt Üretimi",
        "careers_url": "https://www.muratlikarton.com/kariyer",
        "hr_email": "ik@muratlikarton.com",
        "description": "Kuşeli karton üretim hatları, yüksek güç motorları, kompanzasyon ve kontinü otomasyon döngüleri.",
        "recommended_title": "İME Tesis Elektrik & Bakım Stajyeri",
    },
    # ---------------- ÇOSB & ÇORLU 1. OSB & VELİMEŞE & ERGENE EK HEDEFLER ----------------
    {
        "company": "Hyosung İstanbul Spandex A.Ş.",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Kimya & Elastan İplik & Endüstriyel Otomasyon",
        "careers_url": "https://www.hyosungtrakya.com/kariyer",
        "hr_email": "ik@hyosung.com",
        "description": "Bölgenin en büyük yabancı sermayeli sanayi tesisi. Sürekli hat otomasyonu, DCS, yüksek gerilim güç dağıtımı, AC sürücüler ve PLC kontrolü.",
        "recommended_title": "İşletmede Mesleki Eğitim (İME) / Otomasyon & Elektrik Stajyeri",
    },
    {
        "company": "Vatan Kablo Metal Endüstri A.Ş.",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Alçak/Orta/Yüksek Gerilim Kablo İmalatı",
        "careers_url": "https://www.vatankablo.com.tr/kariyer",
        "hr_email": "ik@vatankablo.com.tr",
        "description": "Türkiye'nin öncü kablo üreticilerinden. Bakır çekme, izole ekstrüzyon hatları, yüksek gerilim test laboratuvarları ve hat otomasyonu. Doğrudan Elektrik-Elektronik ana alanı.",
        "recommended_title": "Uzun Dönem Aday Mühendis / Yüksek Gerilim & Kablo Test Stajyeri",
    },
    {
        "company": "GF Hakan Plastik (Georg Fischer Grubu)",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Plastik Boru & Endüstriyel Akış Sistemleri",
        "careers_url": "https://www.hakan.com.tr/kariyer",
        "hr_email": "insankaynaklari@hakan.com.tr",
        "description": "ÇOSB yerleşkesinde boru ekstrüzyon makineleri, kalıp otomasyonu, robotik istifleme ve enerji yönetimi sistemleri.",
        "recommended_title": "İME Elektrik Bakım & Hat Otomasyonu Stajyeri",
    },
    {
        "company": "Koçak Farma İlaç ve Kimya Sanayi",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "İlaç Üretimi & Biyoteknoloji",
        "careers_url": "https://www.kocakfarma.com/kariyer",
        "hr_email": "ik@kocakfarma.com",
        "description": "Türkiye'nin en modern steril enjektör ve aşı üretim kampüsü. Siemens SCADA, bina yönetim sistemleri (BMS), temiz oda HVAC otomasyonu.",
        "recommended_title": "İşletmede Mesleki Eğitim (İME) SCADA & Tesis Elektrik Stajyeri",
    },
    {
        "company": "Dinarsu Halı İmalat ve Ticaret T.A.Ş.",
        "osb": "Çerkezköy OSB (ÇOSB)",
        "location": "Çerkezköy, Tekirdağ",
        "sector": "Zemin Kaplamaları & Tekstil Teknolojileri",
        "careers_url": "https://www.dinarsu.com.tr/iletisim",
        "hr_email": "ik@dinarsu.com.tr",
        "description": "Yüksek hızlı tufting ve baskı makineleri, servo sürücü sistemleri, dijital baskı kafaları elektroniği ve pano revizyonları.",
        "recommended_title": "Uzun Dönem Elektrik-Elektronik Bakım Stajyeri",
    },
    {
        "company": "Kasar & Dual Tekstil Sanayi A.Ş.",
        "osb": "Velimeşe OSB",
        "location": "Ergene / Velimeşe, Tekirdağ",
        "sector": "İleri Tekstil Apre & Boya Otomasyonu",
        "careers_url": "https://www.kasardual.com.tr/kariyer",
        "hr_email": "ik@kasardual.com.tr",
        "description": "Velimeşe OSB'nin en büyük entegre tekstil boyahane tesisi. Otomatik kimyasal dozajlama, PLC ramöz makineleri, atık ısı geri kazanım otomasyonu ve enerji izleme.",
        "recommended_title": "İME Otomasyon & Enstrümantasyon Stajyeri",
    },
    {
        "company": "Ünsped Paketleme ve Lojistik Tesisleri",
        "osb": "Velimeşe OSB",
        "location": "Ergene / Velimeşe, Tekirdağ",
        "sector": "Endüstriyel Paketleme & Akıllı Lojistik Sistemleri",
        "careers_url": "https://www.unsped.com.tr/kariyer",
        "hr_email": "ik@unsped.com.tr",
        "description": "Velimeşe OSB'de otomatik konveyör sistemleri, barkod/RFID okuma kameraları, PLC kumanda panoları ve intralojistik robotları.",
        "recommended_title": "İşletmede Mesleki Eğitim (İME) / Otomasyon Sistemleri Stajyeri",
    },
    {
        "company": "Can Tekstil Entegre Tesisleri",
        "osb": "Ergene 1. OSB",
        "location": "Ergene, Tekirdağ",
        "sector": "İplik, Dokuma & Kumaş Üretimi",
        "careers_url": "https://www.cantekstil.com/kariyer",
        "hr_email": "ik@cantekstil.com",
        "description": "Ergene OSB'de yüksek kapasiteli dokuma tezgahları, invertörlü tahrik sistemleri, kompanzasyon ve güç elektroniği bakım bölümü.",
        "recommended_title": "Uzun Dönem Bakım & Enerji Yönetimi Aday Mühendis",
    },
    {
        "company": "Şenpiliç Trakya Entegre Üretim Tesisleri",
        "osb": "Ergene / Çorlu Sanayi Bölgesi",
        "location": "Ergene / Çorlu, Tekirdağ",
        "sector": "Gıda Endüstrisi & Otomatik Kesim & Soğuk Zincir",
        "careers_url": "https://www.senpilic.com.tr/kariyer",
        "hr_email": "ik@senpilic.com.tr",
        "description": "Yüksek hızlı otomatik paketleme, endüstriyel amonyaklı soğutma otomasyonu, PLC kontrol üniteleri ve yedekli jeneratör/trafo dağıtımı.",
        "recommended_title": "İME Tesis Elektrik & Otomasyon Stajyeri",
    },
    {
        "company": "Zorluteks Tekstil (Zorlu Holding)",
        "osb": "Çorlu / Muratlı Sanayi Havzası",
        "location": "Çorlu / Muratlı, Tekirdağ",
        "sector": "Ev Tekstili, Akıllı Tekstiller & Enerji Santrali",
        "careers_url": "https://www.zorluteks.com.tr/kariyer",
        "hr_email": "zorlukariyer@zorlu.com",
        "description": "Trakya bölgesinin en büyük sanayi komplekslerinden biri. Kendi doğalgaz çevrim enerji santrali, Endüstri 4.0 dijital fabrika altyapısı, SCADA ve geniş elektrik bakım ekibi.",
        "recommended_title": "İşletmede Mesleki Eğitim (İME) / E-E Aday Mühendis",
    },
    {
        "company": "Bel Karper Gıda (Lactalis Grubu)",
        "osb": "Çorlu 1. OSB",
        "location": "Çorlu, Tekirdağ",
        "sector": "Süt & Gıda Endüstrisi Otomasyonu",
        "careers_url": "https://www.bel-group.com/en/careers/",
        "hr_email": "ik@bel-karper.com.tr",
        "description": "Çorlu 1. OSB tesislerinde yüksek hijyen standartlarında PLC kontrollü otomatik eritme ve vakum paketleme hatları, pnömatik-elektrik otomasyonu.",
        "recommended_title": "Uzun Dönem Elektrik Bakım & Otomasyon Stajyeri",
    },
    {
        "company": "Altek Döküm Haddehane A.Ş.",
        "osb": "Veliköy / Çerkezköy OSB Havzası",
        "location": "Çerkezköy / Veliköy, Tekirdağ",
        "sector": "Bakır & Pirinç Haddehane, Döküm",
        "careers_url": "https://www.altekdokum.com/kariyer",
        "hr_email": "ik@altekdokum.com",
        "description": "Sürekli döküm hatları, yüksek frekanslı indüksiyon ocakları, DC/AC yüksek güç motor sürücüleri, kompanzasyon ve harmonik filtreleme sistemleri.",
        "recommended_title": "İME Güç Elektroniği & Yüksek Akım Stajyeri",
    },
]


def get_all_osb_companies(
    sector: Optional[str] = None,
    location_filter: Optional[str] = None
) -> List[Dict[str, str]]:
    """Tüm OSB kurumsal firma listesini filtreleyerek getirir."""
    results = []
    for comp in OSB_COMPANIES:
        if sector and sector.lower() not in comp["sector"].lower():
            continue
        if location_filter and location_filter.lower() not in comp["location"].lower():
            continue
        results.append(comp)
    return results


def convert_osb_to_leads() -> List[Dict[str, any]]:
    """
    OSB rehberindeki firmaları veritabanına aktarılabilecek lead formatına dönüştürür
    ve her biri için E-E uygunluk skoru hesaplar.
    """
    leads = []
    for comp in OSB_COMPANIES:
        title = comp["recommended_title"]
        desc = comp["description"]
        score = calculate_relevance_score(
            title=title,
            text=f"{comp['sector']} {desc} {comp['osb']}",
            location=comp["location"]
        )

        lead = {
            "company": comp["company"],
            "title": title,
            "location": f"{comp['location']} ({comp['osb']})",
            "url": comp["careers_url"],
            "source": f"OSB Rehberi [{comp['osb']}]",
            "relevance_score": score,
            "status": "Yeni",
            "notes": (
                f"Sektör: {comp['sector']}\n"
                f"İK İletişim: {comp['hr_email']}\n"
                f"Detay: {comp['description']}"
            )
        }
        leads.append(lead)
    return leads
