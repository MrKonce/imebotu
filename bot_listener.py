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
            f"Surum: v2.1-strict-tekirdag-only\n"
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


def get_control_panel_keyboard() -> Dict[str, Any]:
    """Kullanıcının Telegram ekranında doğrudan tıklayabileceği interaktif buton menüsü."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔟 İlk 10 İlan", "callback_data": "limit_10"},
                {"text": "🎯 İlk 25 İlan", "callback_data": "limit_25"},
            ],
            [
                {"text": "🚀 İlk 50 İlan", "callback_data": "limit_50"},
                {"text": "💯 İlk 100 İlan", "callback_data": "limit_100"},
            ],
            [
                {"text": "🔍 Canlı Tara", "callback_data": "action_scan"},
                {"text": "📊 Durum & Radar", "callback_data": "action_status"},
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
            collected.extend(fetch_all_active_jobs(max_queries=3, use_playwright=False))
            collected.extend(fetch_all_portal_jobs())

            new_count = 0
            for job in collected:
                is_new, _ = database.upsert_lead(
                    company=job["company"],
                    title=job["title"],
                    location=job.get("location", "Tekirdağ"),
                    url=job["url"],
                    source=job.get("source", "Web"),
                    status="Yeni",
                    notes=job.get("notes") or job.get("snippet", ""),
                )
                if is_new:
                    new_count += 1
                    if job.get("relevance_score", 0) >= 30 and new_count <= 6:
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
        """Kullanıcıya interaktif buton kontrol panelini gönderir."""
        stats = database.get_statistics()
        msg = (
            "🎛️ <b>TNKÜ İME & STAJ RADAR KONTROL PANELİ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 <b>Toplam Takip Edilen Fırsat:</b> {stats['total_leads']}\n"
            f"🏢 <b>Farklı Kurumsal Firma:</b> {stats['unique_companies']}\n"
            f"⭐ <b>Ortalama Uygunluk:</b> {stats['average_score']}/100\n"
            f"✨ <b>Son 3 Günün Taze İlanları:</b> {stats['recent_new_leads']} adet\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Görmek istediğiniz fırsat sayısını aşağıdaki butonlardan seçebilir veya doğrudan yazabilirsiniz:\n"
            "<i>(Örn: 'ilk 10', 'ilk 25', 'ilk 50', 'ilk 100')</i>"
        )
        self.send_message(msg, reply_markup=get_control_panel_keyboard())

    def send_report(self, limit: int = 50) -> None:
        """
        Kullanıcının talep ettiği adette (10, 25, 50, 100 vb.) en güncel çalışan
        ve E-E İME profiline en uygun fırsatları sayfalı / parçalı olarak gönderir.
        """
        database.init_db()
        leads = database.get_ranked_leads(limit=limit)
        stats = database.get_statistics()

        if not leads:
            self.send_message(
                "ℹ️ Veritabanında kriterlere uygun fırsat bulunamadı.\n"
                "Canlı tarama başlatmak için <b>/tara</b> yazabilirsiniz.",
                reply_markup=get_control_panel_keyboard()
            )
            return

        now = datetime.now()
        total_leads = len(leads)
        chunk_size = 12  # Telegram 4096 karakter sınırına takılmamak için 12'şerli parçalar
        chunks = [leads[i:i + chunk_size] for i in range(0, total_leads, chunk_size)]
        total_pages = len(chunks)

        for page_idx, chunk in enumerate(chunks, 1):
            start_num = (page_idx - 1) * chunk_size + 1
            end_num = start_num + len(chunk) - 1

            if page_idx == 1:
                header = (
                    f"📊 <b>GÜNCEL İME & STAJ RAPORU ({now.strftime('%d.%m.%Y %H:%M')})</b>\n"
                    f"🎯 <b>Seçilen Liste:</b> İlk {total_leads} Fırsat [Bölüm {page_idx}/{total_pages}]\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"📁 <b>Toplam Fırsat:</b> {stats['total_leads']} | ✨ <b>Son 3 Günün Yeni İlanı:</b> {stats['recent_new_leads']}\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                )
            else:
                header = (
                    f"📋 <b>İME & STAJ FIRSATLARI ({start_num} - {end_num}) [Bölüm {page_idx}/{total_pages}]:</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                )

            body = ""
            for idx, l in enumerate(chunk, start_num):
                # Güncellik kontrolü (Son 3 gün içinde yayımlanan/eklenen)
                is_new = False
                created_str = l.get("created_at") or l.get("updated_at")
                if created_str:
                    try:
                        created_dt = datetime.strptime(str(created_str).split(".")[0], "%Y-%m-%d %H:%M:%S")
                        diff_days = abs((now - created_dt).total_seconds()) / 86400.0
                        if diff_days <= 3.0:
                            is_new = True
                    except Exception:
                        pass

                new_badge = " 🆕 <b>(*yeni ilan*)</b>" if is_new else ""
                source_clean = l.get("source", "Web")
                if "OSB Rehberi" in source_clean:
                    source_tag = "[OSB Hedefi]"
                elif "Kariyer.net" in source_clean:
                    source_tag = "[Kariyer.net]"
                elif "LinkedIn" in source_clean:
                    source_tag = "[LinkedIn]"
                else:
                    source_tag = f"[{source_clean}]"

                body += (
                    f"\n<b>{idx}. {l['company']}</b> (⭐ {l['relevance_score']}/100){new_badge}\n"
                    f"   📌 {l['title']} <i>{source_tag}</i>\n"
                    f"   📍 {l['location']}\n"
                    f"   🔗 <a href=\"{l['url']}\">İlan / Başvuru Bağlantısı</a>\n"
                )

            # Son sayfada menü butonlarını iliştir
            reply_markup = get_control_panel_keyboard() if page_idx == total_pages else None
            self.send_message(header + body, reply_markup=reply_markup)
            time.sleep(0.35)

    def handle_status(self) -> None:
        """Başvuru durum dağılımını ve radar istatistiklerini özetler."""
        database.init_db()
        stats = database.get_statistics()
        msg = (
            "📈 <b>BAŞVURU VE RADAR TAKİP DURUMU</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )
        for st, count in stats["status_breakdown"].items():
            icon = "🆕" if st == "Yeni" else "📤" if st == "Başvuruldu" else "🤝" if st == "Mülakat" else "✅"
            msg += f"{icon} <b>{st}:</b> {count} firma\n"

        msg += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 <b>Aktif Fırsat:</b> {stats['total_leads']}\n"
            f"🏢 <b>Kurumsal Firma:</b> {stats['unique_companies']}\n"
            f"⭐ <b>Ortalama Uygunluk:</b> {stats['average_score']}/100\n"
            f"✨ <b>Son 3 Günün Taze İlanları:</b> {stats['recent_new_leads']} adet"
        )
        self.send_message(msg, reply_markup=get_control_panel_keyboard())

    def handle_scan(self) -> None:
        """Kullanıcının isteğiyle anlık canlı tarama tetikler (Asenkron yürütülür)."""
        self.send_message(
            "🔍 <b>Canlı tarama başlatıldı...</b>\n"
            "Kariyer.net, LinkedIn ve Trakya OSB portalları taranıyor. Lütfen bekleyin..."
        )
        database.init_db()

        try:
            collected = []
            collected.extend(convert_osb_to_leads())
            collected.extend(fetch_all_active_jobs(max_queries=3, use_playwright=False))
            collected.extend(fetch_all_portal_jobs())

            new_count = 0
            updated_count = 0

            for lead in collected:
                is_new, action = database.upsert_lead(
                    company=lead["company"],
                    title=lead["title"],
                    location=lead.get("location", "Tekirdağ"),
                    url=lead["url"],
                    source=lead.get("source", "Web"),
                    status="Yeni",
                    notes=lead.get("notes") or lead.get("snippet", ""),
                )
                if is_new:
                    new_count += 1
                    if lead.get("relevance_score", 0) >= 30 and new_count <= 5:
                        self.notifier.send_lead_notification(lead)
                        time.sleep(0.3)
                elif action == "updated":
                    updated_count += 1

            if new_count == 0:
                self.send_message(
                    f"✅ <b>Tarama Tamamlandı:</b> Şu an için yeni ilan bulunamadı.\n"
                    f"Kayıtlı {updated_count} fırsatın durumu güncellendi.",
                    reply_markup=get_control_panel_keyboard()
                )
            else:
                self.send_message(
                    f"🎉 <b>Tarama Tamamlandı!</b>\n"
                    f"✨ <b>{new_count} adet YENİ fırsat</b> keşfedildi ve veritabanına eklendi!\n"
                    "Görmek istediğiniz ilan sayısını aşağıdaki butonlardan seçebilirsiniz:",
                    reply_markup=get_control_panel_keyboard()
                )
        except Exception as e:
            print(f"[HATA] Canlı tarama sırasında hata: {e}")
            self.send_message(f"⚠️ Tarama sırasında geçici bir ağ aksaması oldu: {e}", reply_markup=get_control_panel_keyboard())

    def process_callback_query(self, cb_id: str, data: str) -> None:
        """Kullanıcının butonlara tıklamalarını işler."""
        self.answer_callback_query(cb_id)
        print(f"[*] Buton tıklandı: {data}")

        if data == "limit_10":
            self.send_report(limit=10)
        elif data == "limit_25":
            self.send_report(limit=25)
        elif data == "limit_50":
            self.send_report(limit=50)
        elif data == "limit_100":
            self.send_report(limit=100)
        elif data == "action_scan":
            self.handle_scan()
        elif data == "action_status":
            self.handle_status()

    def process_message(self, text: str) -> None:
        """Kullanıcıdan gelen metin mesajlarını analiz edip ilgili fonksiyonu çalıştırır."""
        clean_text = text.strip().lower()
        print(f"[*] Kullanıcıdan mesaj alındı: '{text}'")

        # Sayısal talep kontrolleri ('ilk 10', 'ilk 50', '50', '/rapor 100' vb.)
        match_number = re.match(r"^(?:(?:/)?rapor\s+|ilk\s+)?(\d{1,3})$", clean_text)
        if match_number:
            requested_limit = int(match_number.group(1))
            # Makul sınırlar içine al (min 1, max 100)
            target_limit = max(1, min(100, requested_limit))
            self.send_report(limit=target_limit)
            return

        if clean_text in ["/rapor", "rapor", "bugünün raporunu ver", "bugunun raporunu ver", "rapor ver"]:
            # Varsayılan olarak ilk 50 ilan (veya kullanıcı ekranı)
            self.send_report(limit=50)
        elif clean_text in ["/tara", "tara", "tarama yap", "yeni ilan var mı", "yeni ilanlar", "taramayı başlat"]:
            self.handle_scan()
        elif clean_text in ["/durum", "/stats", "durum", "istatistik"]:
            self.handle_status()
        elif clean_text in ["/temizle", "temizle", "/sifirla", "sıfırla", "sifirla", "temizle botu"]:
            purged = database.purge_invalid_leads()
            self.send_message(
                f"🧹 <b>Veritabanı Sıfırlandı ve Temizlendi!</b>\n"
                f"Alakasız şehirler (İzmir, Ankara, Gaziantep vb.) ve öğrenciye uygun olmayan pozisyonlar silindi.\n"
                f"Temizlenen geçersiz kayıt: {purged}\n\n"
                f"Güncel ve doğrulanmış Tekirdağ/Çorlu İME listesini görmek için <b>/rapor</b> veya <b>'ilk 25'</b> yazabilirsiniz.",
                reply_markup=get_control_panel_keyboard()
            )
        elif clean_text in ["/menu", "/panel", "/ekran", "menu", "panel", "ekran", "/start", "/help", "/yardim", "yardım"]:
            self.send_control_panel()
        else:
            self.send_message(
                f"🤔 <i>'{text}'</i> komutunu anlayamadım.\n"
                "Aşağıdaki kontrol ekranından istediğiniz raporu seçebilir veya <b>'ilk 50'</b> yazabilirsiniz:",
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
