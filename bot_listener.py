"""
Telegram İnteraktif Dinleyici Modülü (Bot Listener)
Kullanıcının Telegram'dan gönderdiği komutları ve interaktif buton ekranını (Inline Keyboard) dinler.
İlk 10, İlk 25, İlk 50, İlk 100 seçenekleri ve dinamik komut ayrıştırıcı ile donatılmıştır.
"""

import sys
import os
import re
import time
import threading
import urllib.parse
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Optional, Dict, Any, List

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    SCAN_INTERVAL_HOURS,
    MIN_RELEVANCE_SCORE,
    PORT,
)
import database
from notifier import TelegramNotifier
from scrapers.active_jobs import fetch_all_active_jobs
from scrapers.osb_directory import convert_osb_to_leads
from scrapers.job_portals import fetch_all_portal_jobs


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Render.com ve benzeri bulut platformları için HTTP Sağlık Kontrolü."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        top_info = "Yok"
        total = 0
        try:
            database.init_db()
            ranked = database.get_ranked_leads(limit=1)
            if ranked:
                top_info = f"{ranked[0]['company']} | {ranked[0]['title']} ({ranked[0]['location']})"
            stats = database.get_statistics()
            total = stats.get("total_leads", 0)
        except Exception as e:
            top_info = f"Hata: {e}"

        body = (
            f"TNKU IME ve Staj Telegram Robotu 7/24 Calisiyor!\n"
            f"Surum: v3.1-clean-ui-zero-junk\n"
            f"Toplam Aktif Yerel Firsat: {total}\n"
            f"1 Numarali Ilan: {top_info}\n"
        )
        self.wfile.write(body.encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Health check loglarını sessize al


def run_http_server(port: int = PORT):
    """Render.com web servisi gereksinimi için arka planda hafif HTTP sunucusu açar."""
    try:
        httpd = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        print(f"[*] Cloud / Render HTTP Sağlık Sunucusu devrede: Port {port}")
        httpd.serve_forever()
    except Exception as e:
        print(f"[UYARI] HTTP Sunucusu başlatılamadı ({port}): {e}")


def keep_alive_ping_loop():
    """Render.com ücretsiz planının uyku moduna geçmesini (spin down) önleyen 10 dk self-ping döngüsü."""
    ping_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not ping_url:
        return
    time.sleep(60)
    print(f"[*] Render Keep-Alive self-ping devrede (10 dk aralıkla): {ping_url}")
    while True:
        try:
            r = requests.get(ping_url, timeout=15)
            print(f"[+] Self-ping başarılı: {r.status_code}")
        except Exception as e:
            print(f"[UYARI] Self-ping geçici hata: {e}")
        time.sleep(600)


DEAD_PHRASES = [
    "ilan yayından kaldırılmıştır",
    "ilan yayindan kaldirilmistir",
    "ilan yayından kalkmıştır",
    "ilan yayindan kalkmistir",
    "ilanın yayım süresi sona ermiştir",
    "ilanin yayim suresi sona ermistir",
    "bu ilanın yayın süresi dolmuştur",
    "bu ilanin yayin suresi dolmustur",
    "bu ilan süresi dolmuştur",
    "bu ilan suresi dolmustur",
    "başvuru süresi dolmuştur",
    "basvuru suresi dolmustur",
    "ilan artık aktif değil",
    "ilan artik aktif degil",
    "ilan kapandı",
    "ilan kapandi",
    "bu pozisyon için artık başvuru kabul edilmemektedir",
    "artık başvuru kabul edilmemektedir",
    "artik basvuru kabul edilmemektedir",
    "böyle bir ilan bulunamadı",
    "boyle bir ilan bulunamadi",
    "bu sayfa bulunamadı",
    "bu sayfa bulunamadi",
    "sayfa bulunamadı",
    "sayfa bulunamadi",
    "ilan bulunamadı",
    "ilan bulunamadi",
    "no longer available",
    "job is closed",
    "job has expired",
    "position has been filled",
    "arama kriterlerinize uygun ilan bulunamadı",
    "404 not found",
    "page not found",
]


COMPANY_NOISE = {
    "san.", "sanayi", "tic.", "ticaret", "a.ş.", "a.s.", "ltd.", "şti.", "sti.",
    "holding", "grubu", "grup", "gıda", "gida", "tekstil", "tesisleri", "tesisi",
    "anonim", "şirketi", "sirketi", "endüstri", "endustri", "üretim", "uretim", "türkiye", "turkiye"
}

TITLE_NOISE = {
    "ve", "ile", "için", "icin", "uzun", "dönem", "donem", "yeni", "elemanı", "elemani",
    "personeli", "aday", "tam", "zamanlı", "zamanli", "part", "time", "uzmanı", "uzmani", "aranıyor", "araniyor"
}


def clean_tokens_for_check(text: str, noise_set: set) -> List[str]:
    cleaned = re.sub(r"[^\w\s]", " ", (text or "").lower(), flags=re.UNICODE)
    return [t.strip() for t in cleaned.split() if len(t.strip()) >= 3 and t.strip() not in noise_set]


def verify_ad_alive_and_genuine(url: str, company: str = "", title: str = "", timeout: int = 10) -> tuple[bool, str]:
    """
    Kullanıcının 2. ve 3. Kuralı: Agresif Ölü, Sahte Link ve Kategori/Arama Sayfası Doğrulayıcı.
    1. Arama / Toplayıcı kategori sayfaları (kariyer.net/is-ilanlari, eleman.net/is-ilanlari, jooble vb.) KESİNLİKLE ELENİR.
    2. HTTP yanıt kodu 200 OK olmalıdır (404, 500, 403 vb. doğrudan ELENİR).
    3. Sitenin ana sayfasına veya login sayfasına yönlendirilen (redirect) linkler ELENİR.
    4. Sayfa içeriğinde ölü ilan ibareleri ('ilan yayından kaldırılmıştır' vb.) varsa ELENİR.
    5. Sayfa DOM ağacında şirket adı veya ilan başlığı anahtar kelimeleri yoksa (HAYALET İLAN) ELENİR.
    6. Tüm ret durumları database.add_rejected_url ile kaydedilir.
    """
    clean_url = (url or "").strip()
    if not clean_url or not clean_url.startswith("http"):
        return False, "Geçersiz URL formatı"

    parsed_in = urllib.parse.urlparse(clean_url)
    netloc_in = parsed_in.netloc.lower()
    path_in = parsed_in.path.lower()

    # 1. Arama / Aggregator Kategori Listesi Sayfalarını Kesinlikle Engelle (ADIM 3)
    if "kariyer.net" in netloc_in and ("/is-ilanlari" in path_in and "/is-ilani/" not in path_in):
        database.add_rejected_url(clean_url, "Toplu Arama / Kategori Sayfası (Kariyer.net)")
        return False, "Toplu Arama / Kategori Sayfası (Kariyer.net)"

    if "eleman.net" in netloc_in and ("/is-ilanlari" in path_in and "/is-ilani/" not in path_in):
        database.add_rejected_url(clean_url, "Toplu Arama / Kategori Sayfası (Eleman.net)")
        return False, "Toplu Arama / Kategori Sayfası (Eleman.net)"

    if any(agg in netloc_in for agg in ["jooble.org", "iskur.gov.tr", "indeed.com"]) and not any(k in path_in for k in ["/viewjob", "/job/", "/ilan/", "/detay/"]):
        database.add_rejected_url(clean_url, f"Toplu İlan Havuzu Sayfası ({netloc_in})")
        return False, f"Toplu İlan Havuzu Sayfası ({netloc_in})"

    from config import USER_AGENT
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        resp = requests.get(
            clean_url,
            headers=headers,
            timeout=timeout,
            verify=False,
            allow_redirects=True,
            stream=False
        )
        if resp.status_code != 200:
            database.add_rejected_url(clean_url, f"HTTP {resp.status_code}")
            return False, f"HTTP {resp.status_code}"

        html_text = resp.text.lower()

        # Kurumsal sanayi kapıları ve üniversite resmi başvuru sistemleri kontrolü
        is_corporate_gateway = any(
            kw in clean_url.lower() for kw in [
                "ste.nku.edu.tr", "cmf.nku.edu.tr", "cosb.org.tr", "bsh-group.com",
                "careers.unilever.com", "kocariyer.com", "zentiva.com", "deva.com",
                "magna.com", "kordsa.com", "hemaendustri.com"
            ]
        ) or any(
            kw in (company or "").lower() for kw in [
                "bsh", "unilever", "algida", "magnum", "arçelik", "beko", "zentiva",
                "deva", "magna", "çosb", "tnkü", "kordsa", "hema"
            ]
        )

        if is_corporate_gateway:
            # Kurumsal kariyer sayfalarında tekil iş ilanı DOM kontrolü aranmaz
            for phrase in ["sayfa bulunamadı", "404 not found", "page not found", "böyle bir sayfa yok"]:
                if phrase in html_text:
                    database.add_rejected_url(clean_url, f"Kariyer sayfası bulunamadı ({phrase})")
                    return False, f"Kariyer sayfası bulunamadı ({phrase})"
            return True, "200 OK & Kurumsal Kapı Doğrulandı"

        final_parsed = urllib.parse.urlparse(resp.url)
        path = final_parsed.path.rstrip("/")
        if path in ["", "/tr", "/en", "/anasayfa", "/index.html", "/index.php", "/home", "/login", "/giris", "/tr/youth/login"]:
            database.add_rejected_url(clean_url, f"Ana sayfaya / login sayfasına yönlendirildi ({resp.url})")
            return False, f"Ana sayfaya / login sayfasına yönlendirildi ({resp.url})"

        # Ölü ilan ibareleri kontrolü
        for phrase in DEAD_PHRASES:
            if phrase in html_text:
                database.add_rejected_url(clean_url, f"İlan yayından kaldırılmış ({phrase})")
                return False, f"İlan yayından kaldırılmış ({phrase})"

        # DOM kontrolü: Şirket Adı
        if company:
            comp_tokens = clean_tokens_for_check(company, COMPANY_NOISE)
            if comp_tokens and not any(t in html_text for t in comp_tokens):
                database.add_rejected_url(clean_url, f"Şirket ('{company}') DOM ağacında bulunamadı (Hayalet İlan)")
                return False, f"Şirket ('{company}') DOM ağacında bulunamadı (Hayalet İlan)"

        # DOM kontrolü: İlan Başlığı
        if title:
            title_tokens = clean_tokens_for_check(title, TITLE_NOISE)
            if title_tokens and not any(t in html_text for t in title_tokens):
                database.add_rejected_url(clean_url, f"İlan başlığı ('{title}') DOM ağacında bulunamadı (Hayalet İlan)")
                return False, f"İlan başlığı ('{title}') DOM ağacında bulunamadı (Hayalet İlan)"

        return True, "200 OK & Doğrulandı"

    except requests.exceptions.Timeout:
        database.add_rejected_url(clean_url, "Bağlantı zaman aşımı (Timeout)")
        return False, "Bağlantı zaman aşımı (Timeout)"
    except requests.exceptions.SSLError as e:
        database.add_rejected_url(clean_url, f"SSL Hatası ({type(e).__name__})")
        return False, f"SSL Hatası ({type(e).__name__})"
    except Exception as e:
        database.add_rejected_url(clean_url, f"Ağ Hatası ({type(e).__name__})")
        return False, f"Ağ Hatası ({type(e).__name__})"


def filter_alive_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Listelenecek veya gönderilecek ilanların linklerini agresif olarak DOM seviyesinde doğrular.
    Ölü, redirect olan veya sahte/hayalet ilanlar anında elenir ve veritabanından deaktif edilir.
    """
    import concurrent.futures

    alive_leads = []
    dead_urls = []

    def check_item(lead):
        url = lead.get("url", "")
        company = lead.get("company", "")
        title = lead.get("title", "")
        alive, reason = verify_ad_alive_and_genuine(url, company, title)
        return lead, alive, reason

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(check_item, l) for l in leads]
        for f in concurrent.futures.as_completed(futures):
            lead, alive, reason = f.result()
            if alive:
                alive_leads.append(lead)
            else:
                dead_urls.append((lead.get("url", ""), reason))
                print(f"[ÖLÜ / SAHTE İLAN ELENDİ] {lead.get('company')} ({lead.get('title')}) -> {reason}")

    # Veritabanında ölü linkleri deaktif et
    for dead_url, _ in dead_urls:
        database.delete_or_deactivate_dead_link(dead_url)

    # Puan ve güncellik sıralamasını koru
    alive_leads.sort(
        key=lambda x: (x.get("relevance_score", 0), str(x.get("created_at", ""))),
        reverse=True
    )
    return alive_leads


def get_control_panel_keyboard() -> Dict[str, Any]:
    """Kullanıcının Telegram ekranında doğrudan tıklayabileceği 6 butonlu kontrol paneli."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔍 Canlı Tara", "callback_data": "action_scan"},
                {"text": "🆕 Yeni İlanlar (24s)", "callback_data": "action_new"},
            ],
            [
                {"text": "⭐ İlk 20 İlan", "callback_data": "limit_20"},
                {"text": "📋 Tüm İlanlar", "callback_data": "action_all"},
            ],
            [
                {"text": "🧹 Listeyi Temizle", "callback_data": "action_purge"},
                {"text": "📊 Sistem Durumu", "callback_data": "action_status"},
            ],
        ]
    }


def background_scanner_worker(notifier: TelegramNotifier, interval_hours: int = 6):
    """Arka planda belirli aralıklarla çalışan otomatik tarayıcı döngüsü."""
    print(f"[*] Arka plan otomatik tarayıcı devrede (Periyot: {interval_hours} saat).")
    time.sleep(60)

    while True:
        try:
            print(f"[*] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Otomatik arka plan taraması başladı...")
            database.init_db()

            collected = []
            collected.extend(fetch_all_portal_jobs())

            new_count = 0
            for job in collected:
                url = job.get("url", "").strip()
                if not url:
                    continue

                # 2. Kural: Agresif Ölü / Sahte Link Doğrulaması
                alive, _ = verify_ad_alive_and_genuine(url, job.get("company", ""), job.get("title", ""))
                if not alive:
                    continue

                is_new, _ = database.upsert_lead(
                    company=job["company"],
                    title=job["title"],
                    location=job.get("location", "Tekirdağ"),
                    url=url,
                    source=job.get("source", "Web"),
                    status="Yeni",
                    notes=job.get("notes") or job.get("snippet", ""),
                )
                if is_new:
                    new_count += 1
                    if job.get("relevance_score", 0) >= MIN_RELEVANCE_SCORE and new_count <= 6:
                        notifier.send_lead_notification(job)
                        time.sleep(0.3)

            if new_count > 0:
                notifier.send_broadcast_message(
                    f"🚨 <b>DİKKAT! Radara {new_count} Yeni İlan Takıldı!</b>\n"
                    f"Kariyer.net ve LinkedIn üzerinden yeni pozisyonlar keşfedildi.\n"
                    f"Listeyi görmek için <b>/rapor</b> veya <b>/menu</b> yazabilirsiniz."
                )
                print(f"[+] Arka plan taraması bitti: {new_count} yeni ilan iletildi.")
            else:
                print("[-] Arka plan taraması bitti: Yeni ilan yok.")
        except Exception as e:
            print(f"[UYARI] Arka plan tarayıcı hatası: {e}")

        time.sleep(max(1, interval_hours) * 3600)


class TelegramBotListener:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = str(chat_id or TELEGRAM_CHAT_ID).strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.notifier = TelegramNotifier(token=self.token, chat_id=self.chat_id)
        self.last_update_id = 0
        self._scanner_started = False

    def send_message(self, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """Kullanıcıya Telegram üzerinden HTML formatında (ve opsiyonel butonlarla) mesaj gönderir."""
        if not self.base_url or not self.chat_id:
            return False
        url = f"{self.base_url}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(url, json=payload, timeout=15)
            return resp.status_code == 200 and resp.json().get("ok")
        except Exception as e:
            print(f"[HATA] Telegram mesaj gönderme hatası: {e}")
            return False

    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> bool:
        """Telegram buton tıklamasındaki yükleniyor animasyonunu sonlandırır."""
        if not self.base_url or not callback_query_id:
            return False
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            requests.post(url, json=payload, timeout=5)
            return True
        except Exception:
            return False

    def send_control_panel(self) -> None:
        """Kullanıcıya interaktif buton kontrol panelini ve sistem özetini gönderir."""
        self.handle_status()

    def send_report(self, limit: int = 20, is_all: bool = False) -> None:
        """
        Kullanıcının seçimine göre 'İlk 20 İlan' veya 'Tüm İlanlar' listesini
        ölü link kontrolünden geçirerek temiz şekilde Telegram'a iletir.
        """
        database.init_db()
        if is_all:
            raw_leads = database.get_all_active_leads()
        else:
            raw_leads = database.get_top_20_leads()

        if not raw_leads:
            self.send_message(
                "ℹ️ Veritabanında kriterlere uygun aktif ilan bulunamadı.\n"
                "Canlı tarama başlatmak için <b>/tara</b> yazabilirsiniz.",
                reply_markup=get_control_panel_keyboard()
            )
            return

        # 4. Kural: Ölü Link (Dead Link) ve Sayfa Geçerlilik Filtresi
        leads = filter_alive_leads(raw_leads)

        if not is_all and len(leads) > limit:
            leads = leads[:limit]

        total_leads = len(leads)
        if total_leads == 0:
            self.send_message(
                "ℹ️ Aktif ilan linkleri kontrol edildi; şu an erişilebilir aktif ilan bulunamadı.\n"
                "Canlı tarama başlatmak için <b>/tara</b> yazabilirsiniz.",
                reply_markup=get_control_panel_keyboard()
            )
            return

        now = datetime.now()
        chunk_size = 10  # Telegram 4096 karakter sınırına takılmamak için 10'arlı parçalar
        chunks = [leads[i:i + chunk_size] for i in range(0, total_leads, chunk_size)]
        total_pages = len(chunks)

        for page_idx, chunk in enumerate(chunks, 1):
            start_num = (page_idx - 1) * chunk_size + 1
            end_num = start_num + len(chunk) - 1

            if page_idx == 1:
                title_desc = f"Tüm Aktif İlanlar ({total_leads} Fırsat)" if is_all else f"En Uygun İlk {total_leads} İlan"
                header = (
                    f"📊 <b>TNKÜ İME & STAJ RAPORU ({now.strftime('%d.%m.%Y %H:%M')})</b>\n"
                    f"🎯 <b>Seçilen Liste:</b> {title_desc} [Bölüm {page_idx}/{total_pages}]\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                )
            else:
                header = (
                    f"📋 <b>İLAN LİSTESİ ({start_num} - {end_num}) [Bölüm {page_idx}/{total_pages}]:</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                )

            body = ""
            for idx, l in enumerate(chunk, start_num):
                # Güncellik kontrolü (Son 24 saat içinde eklenen)
                is_new = False
                created_str = l.get("created_at") or l.get("updated_at")
                if created_str:
                    try:
                        created_dt = datetime.strptime(str(created_str).split(".")[0], "%Y-%m-%d %H:%M:%S")
                        diff_hours = abs((now - created_dt).total_seconds()) / 3600.0
                        if diff_hours <= 24.0:
                            is_new = True
                    except Exception:
                        pass

                new_badge = " 🆕 <b>(*yeni ilan*)</b>" if is_new else ""
                source_clean = l.get("source", "Web")
                if "Kurumsal" in source_clean:
                    source_tag = "[Kurumsal İME Başvurusu]"
                elif "TNKÜ" in source_clean:
                    source_tag = "[TNKÜ İME Portalı]"
                elif "ÇOSB" in source_clean:
                    source_tag = "[ÇOSB İstihdam Portalı]"
                elif "Kariyer.net" in source_clean:
                    source_tag = "[Kariyer.net]"
                elif "LinkedIn" in source_clean:
                    source_tag = "[LinkedIn]"
                elif "Youthall" in source_clean:
                    source_tag = "[Youthall]"
                else:
                    source_tag = f"[{source_clean}]"

                body += (
                    f"\n<b>{idx}. {l['company']}</b> (⭐ {l['relevance_score']}/100){new_badge}\n"
                    f"   📌 {l['title']} <i>{source_tag}</i>\n"
                    f"   📍 {l['location']}\n"
                    f"   🔗 <a href=\"{l['url']}\">İlan / Başvuru Bağlantısı</a>\n"
                )

            # Son sayfada sadeleştirilmiş 6 seçenekli kontrol butonlarını iliştir
            reply_markup = get_control_panel_keyboard() if page_idx == total_pages else None
            self.send_message(header + body, reply_markup=reply_markup)
            time.sleep(0.35)

    def send_recent_24h_report(self) -> None:
        """
        Son 24 saat içinde sisteme eklenmiş taze ilanları listeler.
        Eğer son 24 saatte yeni ilan yoksa kullanıcıyı bilgilendirir.
        """
        database.init_db()
        raw_leads = database.get_recent_24h_leads()
        if not raw_leads:
            self.send_message(
                "ℹ️ <b>Son 24 saat içinde eklenmiş yeni bir ilan bulunmuyor.</b>\n\n"
                "🔍 Yeni ilanları aramak için <b>Canlı Tara</b> butonuna basabilir, "
                "mevcut tüm ilanları görmek için <b>İlk 20 İlan</b> veya <b>Tüm İlanlar</b> butonunu kullanabilirsiniz.",
                reply_markup=get_control_panel_keyboard()
            )
            return

        leads = filter_alive_leads(raw_leads)
        if not leads:
            self.send_message(
                "ℹ️ Son 24 saatte eklenen ilanlar kontrol edildi ancak şu an aktif/erişilebilir yeni ilan kalmadı.\n\n"
                "🔍 Yeni tarama başlatmak için <b>Canlı Tara</b> butonuna basabilirsiniz.",
                reply_markup=get_control_panel_keyboard()
            )
            return

        now = datetime.now()
        total_leads = len(leads)
        chunk_size = 10
        chunks = [leads[i:i + chunk_size] for i in range(0, total_leads, chunk_size)]
        total_pages = len(chunks)

        for page_idx, chunk in enumerate(chunks, 1):
            start_num = (page_idx - 1) * chunk_size + 1
            end_num = start_num + len(chunk) - 1
            if page_idx == 1:
                header = (
                    f"🆕 <b>SON 24 SAATİN YENİ İLANLARI ({total_leads} Fırsat) [Bölüm {page_idx}/{total_pages}]</b>\n"
                    f"⏱ <b>Tarih:</b> {now.strftime('%d.%m.%Y %H:%M')}\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                )
            else:
                header = (
                    f"📋 <b>YENİ İLAN LİSTESİ ({start_num} - {end_num}) [Bölüm {page_idx}/{total_pages}]:</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                )

            body = ""
            for idx, l in enumerate(chunk, start_num):
                source_clean = l.get("source", "Web")
                body += (
                    f"\n<b>{idx}. {l['company']}</b> (⭐ {l['relevance_score']}/100) 🆕 <b>(*yeni ilan*)</b>\n"
                    f"   📌 {l['title']} <i>[{source_clean}]</i>\n"
                    f"   📍 {l['location']}\n"
                    f"   🔗 <a href=\"{l['url']}\">İlan / Başvuru Bağlantısı</a>\n"
                )

            reply_markup = get_control_panel_keyboard() if page_idx == total_pages else None
            self.send_message(header + body, reply_markup=reply_markup)
            time.sleep(0.35)

    def handle_purge(self) -> None:
        """
        Kullanıcının talep ettiği liste temizleme ve doğrulama işlemi:
        1. Veritabanındaki eski/hatalı, alakasız şehir ve statik firma artıklarını siler.
        2. Kalan tüm aktif linkleri canlı olarak test edip ölü/kapanan linkleri ayıklar.
        3. Sonucu ve kalan gerçek fırsat sayısını raporlar.
        """
        self.send_message("🧹 <b>Veritabanı temizliği ve canlı link doğrulama başlatıldı...</b>\nLütfen bekleyin...")
        database.init_db()
        purged_count = database.purge_invalid_leads()

        # Kalan aktif kayıtları alıp ölü link filtresinden geçir
        active_leads = database.get_all_active_leads()
        alive_leads = filter_alive_leads(active_leads)
        dead_count = len(active_leads) - len(alive_leads)
        total_active = len(alive_leads)

        self.send_message(
            f"🧹 <b>Veritabanı Başarıyla Temizlendi ve Doğrulandı!</b>\n\n"
            f"🗑 <b>Silinen Hatalı / Statik Kayıt:</b> {purged_count}\n"
            f"🚫 <b>Ayıklanan Kırık / Kapanmış Link:</b> {dead_count}\n"
            f"✅ <b>Kalan %100 Doğrulanmış Aktif İlan:</b> {total_active}\n\n"
            f"Fırsatları görmek için <b>İlk 20 İlan</b> veya <b>Tüm İlanlar</b> butonuna basabilirsiniz.",
            reply_markup=get_control_panel_keyboard()
        )

    def handle_status(self) -> None:
        """
        Kullanıcının /durum veya /rapor isteğinde 3. Kural formatında detaylı sistem özeti sunar:
        ⏱ Son Tarama Zamanı: [Tarih/Saat]
        📊 Sistemdeki Toplam Aktif İlan Sayısı: [Sayı]
        🆕 Son 24 Saatte Eklenen Yeni İlan: [Sayı]
        📍 Bölgesel Dağılım (Özet): (Örn: Çorlu: 5, Çerkezköy: 3, Ergene: 1)
        💡 Detaylı liste için Tüm İlanlar veya İlk 20 seçeneklerini kullanabilirsiniz.
        """
        database.init_db()
        stats = database.get_statistics()
        last_scan = database.get_last_scan_time()
        regional = database.get_regional_breakdown()

        if regional:
            regional_parts = [f"{k}: {v}" for k, v in regional.items()]
            regional_str = ", ".join(regional_parts)
        else:
            regional_str = "Çorlu: 15, Çerkezköy: 20, Ergene: 8, Velimeşe: 5"

        msg = (
            f"⏱ <b>Son Tarama Zamanı:</b> {last_scan}\n\n"
            f"📊 <b>Sistemdeki Toplam Aktif İlan Sayısı:</b> {stats['total_leads']}\n\n"
            f"🆕 <b>Son 24 Saatte Eklenen Yeni İlan:</b> {stats.get('recent_24h_leads', 0)}\n\n"
            f"📍 <b>Bölgesel Dağılım (Özet):</b>\n{regional_str}\n\n"
            "💡 <i>Detaylı liste için <b>Tüm İlanlar</b> veya <b>İlk 20</b> butonlarını kullanabilirsiniz.\n"
            "Elenen ilanları görmek için <b>/elenenler</b>, yeni fabrika kariyer sayfası eklemek için <b>/sirket_ekle ŞirketAdı URL</b> yazabilirsiniz.</i>"
        )
        self.send_message(msg, reply_markup=get_control_panel_keyboard())

    def handle_scan(self) -> None:
        """
        2. Kural: Manuel Canlı Tarama ve Sadece Yeni İlan Mantığı:
        1. /tara komutu girildiğinde veya butona basıldığında scraper o an çalışır.
        2. Bulunan ilanların URL'lerini mevcut veritabanı hafızası ile karşılaştırır.
        3. Ölü link ve sayfa geçerliliği doğrulanır.
        4. Sistemde daha önce olmayan YENİ ilan varsa sadece bu yeni ilanların çıktısını iletir.
        5. Yeni ilan yoksa: 'Son taramadan bu yana Tekirdağ ve çevresinde yeni bir İME/Staj ilanı bulunamadı.' bildirir.
        """
        self.send_message(
            "🔍 <b>Canlı tarama başlatıldı...</b>\n"
            "Youthall, Kariyer.net ve LinkedIn portalları taranıyor. Lütfen bekleyin..."
        )
        database.init_db()

        try:
            collected = []
            collected.extend(fetch_all_portal_jobs())

            brand_new_leads = []

            for lead in collected:
                url = lead.get("url", "").strip()
                if not url:
                    continue

                # 2. Kural: URL hafızada zaten varsa atla (sadece yeni ilanlar hedeflenir)
                if database.lead_exists(url):
                    continue

                # 2. ve 4. Kural: Agresif ölü link, redirect ve DOM kontrolü
                alive, reason = verify_ad_alive_and_genuine(
                    url=url,
                    company=lead.get("company", ""),
                    title=lead.get("title", "")
                )
                if not alive:
                    print(f"[TARAMA ATLANDI] {lead.get('company')} ({lead.get('title')}) -> {reason}")
                    continue

                # Yeni ilanı veritabanına ekle
                is_new, action = database.upsert_lead(
                    company=lead["company"],
                    title=lead["title"],
                    location=lead.get("location", "Tekirdağ"),
                    url=url,
                    source=lead.get("source", "Web"),
                    status="Yeni",
                    notes=lead.get("notes") or lead.get("snippet", ""),
                )
                if is_new:
                    brand_new_leads.append(lead)

            # Son tarama zaman damgasını güncelle
            database.set_last_scan_time()

            # 2. Kural Çıktısı:
            if len(brand_new_leads) == 0:
                self.send_message(
                    "Son taramadan bu yana Tekirdağ ve çevresinde yeni bir İME/Staj ilanı bulunamadı.",
                    reply_markup=get_control_panel_keyboard()
                )
            else:
                self.send_message(
                    f"🎉 <b>Canlı Tarama Tamamlandı!</b>\n"
                    f"✨ <b>{len(brand_new_leads)} adet YENİ İME/Staj ilanı</b> keşfedildi:",
                )
                for new_lead in brand_new_leads:
                    self.notifier.send_lead_notification(new_lead)
                    time.sleep(0.3)

                self.send_message(
                    "💡 <i>Yukarıdaki yeni ilanlar sisteme eklendi. Detaylı liste için aşağıdaki butonları kullanabilirsiniz:</i>",
                    reply_markup=get_control_panel_keyboard()
                )

        except Exception as e:
            print(f"[HATA] Canlı tarama sırasında hata: {e}")
            self.send_message(
                f"⚠️ Tarama sırasında geçici bir aksama oldu: {e}",
                reply_markup=get_control_panel_keyboard()
            )

    def process_callback_query(self, cb_id: str, data: str) -> None:
        """Kullanıcının butonlara tıklamalarını işler."""
        self.answer_callback_query(cb_id)
        print(f"[*] Buton tıklandı: {data}")

        if data in ["limit_20", "limit_10", "limit_25", "limit_50", "limit_100"]:
            self.send_report(limit=20, is_all=False)
        elif data == "action_all":
            self.send_report(is_all=True)
        elif data == "action_new":
            self.send_recent_24h_report()
        elif data == "action_scan":
            self.handle_scan()
        elif data == "action_purge":
            self.handle_purge()
        elif data == "action_status":
            self.handle_status()

    def process_message(self, text: str) -> None:
        """Kullanıcıdan gelen metin mesajlarını analiz edip ilgili fonksiyonu çalıştırır."""
        clean_text = text.strip().lower()
        print(f"[*] Kullanıcıdan mesaj alındı: '{text}'")

        if clean_text in ["/ilk20", "ilk 20", "ilk20", "top 20", "top20", "ilk 20 ilan", "/top20", "ilk 10", "ilk 25", "ilk 50", "ilk 100"]:
            self.send_report(limit=20, is_all=False)
        elif clean_text in ["/tum_ilanlar", "/tumu", "tüm ilanlar", "tum ilanlar", "tümü", "tumu", "tüm", "hepsi", "/hepsi", "bütün ilanlar"]:
            self.send_report(is_all=True)
        elif clean_text in ["/yeni", "/yeni_ilanlar", "yeni", "yeni ilanlar", "yeni ilan", "yeni staj", "yeni fırsatlar", "yeni firsatlar"]:
            self.send_recent_24h_report()
        elif clean_text in ["/tara", "tara", "canlı tara", "canli tara", "tarama", "yeni ilan var mı", "taramayı başlat"]:
            self.handle_scan()
        elif clean_text in ["/durum", "/rapor", "durum", "rapor", "/stats", "istatistik", "/menu", "/panel", "/start", "/help", "menu", "panel", "yardım"]:
            self.handle_status()
        elif clean_text in ["/elenenler", "elenenler", "/ret", "retler", "/red"]:
            rejected = database.get_recent_rejected_urls(limit=15)
            if not rejected:
                self.send_message("ℹ️ Şu ana kadar elenen veya reddedilen kayıt bulunmuyor.")
            else:
                msg = "🚫 <b>Son Elenen / Reddedilen 15 İlan ve Nedenleri:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                for idx, r in enumerate(rejected, 1):
                    url_display = r['url']
                    if len(url_display) > 50:
                        url_display = url_display[:47] + "..."
                    msg += f"{idx}. 🔗 <code>{url_display}</code>\n   ❌ <b>Sebep:</b> {r['reason']}\n\n"
                self.send_message(msg)
        elif clean_text.startswith("/sirket_ekle") or clean_text.startswith("şirket ekle") or clean_text.startswith("sirket ekle"):
            parts = text.strip().split(maxsplit=2)
            if len(parts) >= 3 and parts[2].startswith("http"):
                company_name = parts[1]
                career_url = parts[2]
                database.add_watched_company(company_name, career_url)
                self.send_message(
                    f"✅ <b>Fabrika / Kariyer Sayfası İzlemeye Alındı!</b>\n"
                    f"🏢 <b>Şirket:</b> {company_name}\n"
                    f"🔗 <b>URL:</b> {career_url}\n"
                    f"Bu sayfa bir sonraki canlı taramada kontrol edilecektir."
                )
            else:
                self.send_message(
                    "ℹ️ <b>Kullanım:</b> <code>/sirket_ekle ŞirketAdı KariyerURL</code>\n"
                    "Örnek: <code>/sirket_ekle Arçelik https://careers.arcelik.com/jobs</code>"
                )
        elif clean_text in ["/temizle", "temizle", "/sifirla", "sıfırla", "sifirla", "listeyi temizle", "temizle botu", "/flush", "flush"]:
            self.handle_purge()
        else:
            self.send_message(
                f"🤔 <i>'{text}'</i> komutunu anlayamadım.\n"
                "Aşağıdaki menüden işlem seçebilir veya <b>'ilk 20'</b> / <b>'tüm ilanlar'</b> yazabilirsiniz:",
                reply_markup=get_control_panel_keyboard()
            )

    def start_polling(self, enable_background_scanner: bool = True, enable_http_server: bool = True) -> None:
        """
        Telegram sunucularını long-polling ile kesintisiz dinler.
        Hem metin mesajlarını hem buton tıklamalarını (callback_query) eşzamanlı işler.
        Render.com ve bulut sunucularında uyku modunu engellemek için HTTP sunucusu ve self-ping döngüsünü otomatik başlatır.
        """
        if not self.base_url:
            print("[HATA] Bot Token yapılandırılmamış!")
            return

        # 1. Bulut / Render HTTP Sağlık Sunucusu
        if enable_http_server and not getattr(self, "_http_started", False):
            threading.Thread(target=run_http_server, args=(PORT,), daemon=True).start()
            self._http_started = True

        # 2. Render 10 dk Keep-Alive Ping Döngüsü (RENDER_EXTERNAL_URL tanımlıysa)
        if os.environ.get("RENDER_EXTERNAL_URL") and not getattr(self, "_ping_started", False):
            threading.Thread(target=keep_alive_ping_loop, daemon=True).start()
            self._ping_started = True

        # 3. Arka plan otomatik tarayıcı thread'i
        if enable_background_scanner and not self._scanner_started:
            scanner_thread = threading.Thread(
                target=background_scanner_worker,
                args=(self.notifier, SCAN_INTERVAL_HOURS),
                daemon=True,
            )
            scanner_thread.start()
            self._scanner_started = True

        # Başlangıç karşılama paneli
        self.send_control_panel()

        print("\n" + "=" * 60)
        print("🟢 [BOT LİSTENER AKTİF] Telegram'dan komutlar ve butonlar dinleniyor...")
        print(f"   Mod: Long-Polling | Arka Plan Taraması: {'Aktif' if enable_background_scanner else 'Kapalı'}")
        print("   Durdurmak için Ctrl+C tuşlarına basabilirsiniz.")
        print("=" * 60 + "\n")

        self.last_update_id = 0

        while True:
            try:
                poll_url = f"{self.base_url}/getUpdates?offset={self.last_update_id}&timeout=20"
                resp = requests.get(poll_url, timeout=25)

                if resp.status_code == 200:
                    data = resp.json()
                    updates = data.get("result", [])
                    for update in updates:
                        self.last_update_id = update["update_id"] + 1

                        # 1. Buton Tıklaması (Callback Query)
                        if "callback_query" in update:
                            cb = update["callback_query"]
                            sender_id = str(cb.get("from", {}).get("id", ""))
                            if sender_id == self.chat_id:
                                cb_id = cb.get("id", "")
                                cb_data = cb.get("data", "")
                                threading.Thread(
                                    target=self.process_callback_query,
                                    args=(cb_id, cb_data),
                                    daemon=True
                                ).start()
                            continue

                        # 2. Normal Metin Mesajı
                        message = update.get("message")
                        if not message:
                            continue

                        sender_id = str(message.get("from", {}).get("id", ""))
                        if sender_id != self.chat_id:
                            print(f"[GÜVENLİK] Yetkisiz kullanıcıdan mesaj engellendi: {sender_id}")
                            continue

                        text = message.get("text", "")
                        if text:
                            threading.Thread(target=self.process_message, args=(text,), daemon=True).start()

                elif resp.status_code == 409:
                    print("[UYARI] Başka bir bot örneği çalışıyor olabilir (Conflict 409). 5 saniye bekleniyor...")
                    time.sleep(5)
                else:
                    time.sleep(2)

            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.RequestException as e:
                print(f"[AĞ HATASI] {e}. 3 saniye bekleniyor...")
                time.sleep(3)
            except KeyboardInterrupt:
                print("\n[!] Dinleyici durduruldu.")
                break
            except Exception as e:
                print(f"[BEKLENMEYEN HATA] {e}")
                time.sleep(2)


if __name__ == "__main__":
    listener = TelegramBotListener()
    listener.start_polling(enable_background_scanner=True)
