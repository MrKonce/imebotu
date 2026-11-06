"""
İME (İşletmede Mesleki Eğitim) ve Uzun Dönem Staj Bulma Robotu
TNKÜ Elektrik-Elektronik Mühendisliği - Ana Orkestratör & Sunucu Başlatıcı
"""

import sys
import time
import argparse
from datetime import datetime

# Windows konsolunda Unicode / Emoji karakterlerinin hatasız gösterilmesi için
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SCAN_INTERVAL_HOURS
import database
from notifier import TelegramNotifier
from scrapers.osb_directory import convert_osb_to_leads
from scrapers.active_jobs import fetch_all_active_jobs
from scrapers.job_portals import fetch_all_portal_jobs


def run_pipeline(sync_osb: bool = True, use_playwright: bool = False) -> None:
    """
    Ana tarama ve bildirim akışını yürütür:
    1. Veritabanını hazırla ve tabloları doğrula.
    2. OSB kurumsal firma rehberini ve canlı web ilanlarını çek.
    3. Append / Update (Upsert) mantığıyla verileri kaydet / güncelle.
    4. Sadece YENİ ve yüksek uygunluklu ilanları Telegram üzerinden kullanıcıya bildir.
    """
    print("\n" + "=" * 60)
    print(f"🚀 [TNKÜ İME & STAJ ROBOTU] Tarama Başlatıldı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Veritabanı İlklendirmesi
    database.init_db()
    notifier = TelegramNotifier()

    collected_leads = []

    # 2. OSB Kurumsal Fabrikalar Rehberi
    if sync_osb:
        print("[1/3] ÇOSB, Çorlu 1. OSB, Velimeşe ve Ergene OSB kurumsal firma rehberi kontrol ediliyor...")
        osb_leads = convert_osb_to_leads()
        collected_leads.extend(osb_leads)
        print(f"    -> {len(osb_leads)} kurumsal OSB sanayi hedefi hazırlandı.")

    # 3. Canlı İş Arama ve Kariyer Sayfaları Taranması
    print("[2/3] Canlı iş ilanları ve arama motorları taranıyor...")
    active_leads = fetch_all_active_jobs(max_queries=4, use_playwright=use_playwright)
    collected_leads.extend(active_leads)

    # 4. Kariyer Portalları (Kariyer.net + LinkedIn) Taranması
    print("[3/3] Kariyer portalları (Kariyer.net & LinkedIn) taranıyor...")
    portal_leads = fetch_all_portal_jobs()
    collected_leads.extend(portal_leads)

    # 5. Kayıt & Güncelleme Döngüsü (Upsert / Append-Update)
    new_leads_count = 0
    updated_leads_count = 0
    ignored_count = 0

    print(f"\n[*] Toplam {len(collected_leads)} potansiyel fırsat analiz ediliyor...")

    for lead in collected_leads:
        url = lead.get("url", "").strip()
        score = lead.get("relevance_score", 0)

        if not url or score <= 0:
            ignored_count += 1
            continue

        is_new, action = database.upsert_lead(
            company=lead["company"],
            title=lead["title"],
            location=lead.get("location", "Tekirdağ"),
            url=url,
            source=lead.get("source", "Web"),
            relevance_score=score,
            status="Yeni",
            notes=lead.get("notes") or lead.get("snippet", ""),
        )

        if is_new:
            new_leads_count += 1
            print(f"[YENİ] {lead['company']} - {lead['title']} (Skor: {score}/100)")
            # Yüksek uygunluklu olanları (Skor >= 30) Telegram'a bildir (spam önleme: max 8)
            if score >= 30 and new_leads_count <= 8:
                notifier.send_lead_notification(lead)
                time.sleep(0.3)
        elif action == "updated":
            updated_leads_count += 1

    # Çok sayıda yeni ilan bulunduysa toplu bir özet bildirim ilet
    if new_leads_count > 8:
        notifier.send_broadcast_message(
            f"🔔 <b>{new_leads_count} Yeni İlan Bulundu!</b>\n"
            f"Kariyer.net, LinkedIn ve Trakya OSB portallarından {new_leads_count} yeni staj/iş ilanı veritabanına kaydedildi.\n"
            f"İlk 25 fırsatı görmek için <b>/rapor</b> yazabilirsin."
        )

    # 6. Özet Rapor
    print("\n" + "-" * 60)
    print("📊 [TARAMA ÖZETİ]")
    print(f"✨ Yeni Eklenen İlan: {new_leads_count}")
    print(f"🔄 Güncellenen / Tazelenen İlan: {updated_leads_count}")
    print(f"🚫 Filtrelenen / Alakasız: {ignored_count}")
    print("-" * 60)

    stats = database.get_statistics()
    print(f"📁 Veritabanında Toplam: {stats['total_leads']} Fırsat | Ortalama Skor: {stats['average_score']}")
    print("=" * 60 + "\n")


def display_stats() -> None:
    """Veritabanı durumunu ve başvuru istatistiklerini ekrana basar."""
    database.init_db()
    stats = database.get_statistics()
    print("\n" + "=" * 50)
    print("📈 TNKÜ İME & STAJ TAKİP İSTATİSTİKLERİ")
    print("=" * 50)
    print(f"Toplam Takip Edilen Fırsat: {stats['total_leads']}")
    print(f"Farklı Kurumsal Firma:      {stats['unique_companies']}")
    print(f"Ortalama E-E Uygunluk:      {stats['average_score']} / 100")
    print(f"Son 3 Günün Yeni İlanları:  {stats['recent_new_leads']}")
    print("\nBaşvuru Durum Dağılımı:")
    for status, count in stats["status_breakdown"].items():
        print(f"  • {status:12}: {count}")
    print("=" * 50 + "\n")


def list_leads(status: str = None, min_score: int = 15, limit: int = 25) -> None:
    """Kayıtlı ilanları terminalde listeler."""
    database.init_db()
    leads = database.get_leads(status=status, min_score=min_score, limit=limit)
    print(f"\n📋 Kayıtlı İlanlar ({'Tümü' if not status else status}, Min Skor: {min_score}):")
    print("-" * 80)
    for lead in leads:
        print(f"[{lead['id']:03d}] {lead['company']} | {lead['title']}")
        print(f"      📍 {lead['location']} | ⭐ {lead['relevance_score']}/100 | 📌 {lead['status']}")
        print(f"      🔗 {lead['url']}")
        print("-" * 80)


def start_scheduler(interval_hours: int = 6, use_playwright: bool = False) -> None:
    """Belirli periyotlarla otomatik arka plan taraması çalıştırır."""
    import schedule

    print(f"⏰ Zamanlayıcı aktif: Her {interval_hours} saatte bir otomatik tarama yapılacak.")
    # İlk çalıştırma
    run_pipeline(sync_osb=True, use_playwright=use_playwright)

    schedule.every(interval_hours).hours.do(
        run_pipeline, sync_osb=False, use_playwright=use_playwright
    )

    while True:
        schedule.run_pending()
        time.sleep(1)


def broadcast_all_leads() -> None:
    """Veritabanındaki tüm kayıtlı ilanları Telegram botu üzerinden topluca gönderir."""
    database.init_db()
    notifier = TelegramNotifier()
    if not notifier.is_configured():
        print("\n[HATA] Telegram Bot Token veya Chat ID henüz .env dosyasına girilmemiş!\n")
        return

    if not notifier.test_connection():
        print("[HATA] Telegram bot bağlantısı kurulamadı. Token'ı kontrol edin.")
        return

    leads = database.get_leads(limit=100)
    print(f"\n📤 Toplam {len(leads)} ilan Telegram hesabınıza iletiliyor...")
    for idx, lead in enumerate(leads, 1):
        print(f" [{idx:02d}/{len(leads):02d}] Gönderiliyor: {lead['company']} - {lead['title']}")
        notifier.send_lead_notification(lead)
        time.sleep(0.5)

    print("\n[BAŞARILI] İlanlar Telegram'a iletildi! 🎉\n")


def run_server_mode() -> None:
    """
    Sunucu Modu (Server Mode - 7/24 Kesintisiz Çalışma):
    Erasmus botundaki gibi tek süreçte (single-process) hem arka plan tarama döngüsünü
    hem de Telegram dinleyicisini eşzamanlı ve asenkron olarak ayağa kaldırır.
    """
    database.init_db()
    from bot_listener import TelegramBotListener
    listener = TelegramBotListener()
    # enable_background_scanner=True ile arka plan thread'i de otomatik başlar
    listener.start_polling(enable_background_scanner=True)


def main():
    parser = argparse.ArgumentParser(
        description="TNKÜ Elektrik-Elektronik İME ve Uzun Dönem Staj Robotu"
    )
    parser.add_argument(
        "--server", action="store_true", help="Sunucu Modu: 7/24 arka plan taraması + Telegram dinleyiciyi birlikte çalıştır"
    )
    parser.add_argument(
        "--once", action="store_true", help="Tek seferlik tarama ve bildirim çalıştır"
    )
    parser.add_argument(
        "--schedule", action="store_true", help="Zamanlayıcıyı CLI periyodik modda başlat"
    )
    parser.add_argument(
        "--interval", type=int, default=SCAN_INTERVAL_HOURS, help="Tarama periyodu (saat, varsayılan: 6)"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Mevcut veritabanı istatistiklerini göster"
    )
    parser.add_argument(
        "--list", action="store_true", help="Kayıtlı ilanları terminalde listele"
    )
    parser.add_argument(
        "--status", type=str, default=None, help="Listeleme için statü filtresi (Yeni, Başvuruldu, vb.)"
    )
    parser.add_argument(
        "--set-status", nargs=2, metavar=("ID", "NEW_STATUS"), help="Bir ilanın durumunu güncelle"
    )
    parser.add_argument(
        "--playwright", action="store_true", help="Playwright tarayıcı motorunu aktif et"
    )
    parser.add_argument(
        "--listen", action="store_true", help="Telegram interaktif bot dinleyicisini başlat (/rapor, /tara vb.)"
    )
    parser.add_argument(
        "--resend-all", action="store_true", help="Veritabanındaki ilanları Telegram'a topluca gönder"
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Listeleme için gösterilecek adet (Varsayılan: 50)"
    )
    parser.add_argument(
        "--rescore", action="store_true", help="Tüm kayıtlı fırsatları güncel E-E skorlama algoritmasıyla yeniden puanla"
    )

    args = parser.parse_args()

    if args.server:
        run_server_mode()
    elif args.listen:
        run_server_mode()
    elif args.once:
        run_pipeline(sync_osb=True, use_playwright=args.playwright)
    elif args.resend_all:
        broadcast_all_leads()
    elif args.stats:
        display_stats()
    elif args.rescore:
        updated = database.rescore_all_leads()
        print(f"[BAŞARILI] Toplam {updated} adet fırsat güncel skorlama algoritmasıyla yeniden puanlandı.")
    elif args.list:
        list_leads(status=args.status, limit=args.limit)
    elif args.set_status:
        lead_id = int(args.set_status[0])
        new_status = args.set_status[1]
        success = database.update_lead_status(lead_id, new_status)
        if success:
            print(f"[BAŞARILI] #{lead_id} nolu ilanın durumu '{new_status}' olarak güncellendi.")
        else:
            print(f"[HATA] #{lead_id} nolu ilan bulunamadı.")
    elif args.schedule:
        start_scheduler(interval_hours=args.interval, use_playwright=args.playwright)
    else:
        # Komut satırından parametresiz çağrıldığında varsayılan olarak sunucu modunda çalışır
        run_server_mode()


if __name__ == "__main__":
    main()
