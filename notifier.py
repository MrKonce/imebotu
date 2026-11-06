"""
Telegram Bildirim Modülü
Yeni bulunan ilan ve kurumsal İME hedeflerini Telegram Bot üzerinden iletir.
"""

import sys
import html
import time
from typing import Dict, Any, Optional
import requests

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramNotifier:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    def is_configured(self) -> bool:
        """Telegram ayarlarının girilip girilmediğini kontrol eder."""
        return bool(self.token and self.chat_id and "BURAYA" not in self.token)

    def test_connection(self) -> bool:
        """Bot Token ve Chat ID'nin geçerli olup olmadığını doğrular."""
        if not self.is_configured():
            print("[BİLGİ] Telegram konfigürasyonu eksik veya henüz girilmemiş (.env dosyasını kontrol edin).")
            return False

        try:
            url = f"{self.base_url}/getMe"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.json().get("ok"):
                bot_user = resp.json().get("result", {}).get("username", "Bot")
                print(f"[BAŞARILI] Telegram Bot Bağlantısı Aktif (@{bot_user})")
                return True
            else:
                print(f"[HATA] Telegram getMe başarısız: {resp.text}")
                return False
        except Exception as e:
            print(f"[HATA] Telegram bağlantı testi başarısız: {e}")
            return False

    def send_lead_notification(self, lead: Dict[str, Any]) -> bool:
        """
        Yeni bir ilanı tam olarak istenen formatta Telegram'a iletir:
        🏢 **Firma:** [Firma Adı]
        📌 **Pozisyon:** [Başlık]
        📍 **Konum:** [Konum]
        ⭐ **Uygunluk Skoru:** [Skor/Puan]
        🔗 **Link:** [İlan/İletişim URL]
        """
        company = lead.get("company", "Belirtilmemiş")
        title = lead.get("title", "İME / Staj Pozisyonu")
        location = lead.get("location", "Tekirdağ / Çorlu")
        score = lead.get("relevance_score", 0)
        url = lead.get("url", "#")
        notes = lead.get("notes", "")

        # Eğer Telegram yapılandırılmamışsa terminalde şık formatta yazdır (Dry-run)
        if not self.is_configured():
            print("\n" + "=" * 55)
            print("🔔 [YENİ İLAN BİLDİRİMİ (Konsol Çıktısı)]")
            print(f"🏢 Firma: {company}")
            print(f"📌 Pozisyon: {title}")
            print(f"📍 Konum: {location}")
            print(f"⭐ Uygunluk Skoru: {score}/100")
            print(f"🔗 Link: {url}")
            if notes:
                print(f"📝 Notlar: {notes}")
            print("=" * 55 + "\n")
            return True

        # Telegram Mesaj Gövdesi (HTML Biçimlendirmesi)
        safe_company = html.escape(str(company))
        safe_title = html.escape(str(title))
        safe_location = html.escape(str(location))
        safe_url = html.escape(str(url))

        message = (
            f"🏢 <b>Firma:</b> {safe_company}\n"
            f"📌 <b>Pozisyon:</b> {safe_title}\n"
            f"📍 <b>Konum:</b> {safe_location}\n"
            f"⭐ <b>Uygunluk Skoru:</b> {score}/100\n"
            f"🔗 <b>Link:</b> <a href=\"{safe_url}\">{safe_url}</a>"
        )

        if notes:
            safe_notes = html.escape(str(notes))
            message += f"\n\n💡 <i>Ek Bilgi:</i>\n{safe_notes}"

        send_url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            resp = requests.post(send_url, json=payload, timeout=12)
            if resp.status_code == 200 and resp.json().get("ok"):
                # Telegram flood limitini aşmamak için kısa bekleme
                time.sleep(0.4)
                return True
            else:
                print(f"[UYARI] Telegram mesaj gönderilemedi ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            print(f"[HATA] Telegram bildirim hatası: {str(e)}")
            return False

    def send_broadcast_message(self, text: str) -> bool:
        """Genel durum ve özet mesajı gönderir."""
        if not self.is_configured():
            print(f"[BİLDİRİM] {text}")
            return True

        send_url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(send_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
