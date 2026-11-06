# 🎓 TNKÜ İME (İşletmede Mesleki Eğitim) & Uzun Dönem Staj Bulma Robotu

Tekirdağ Namık Kemal Üniversitesi (TNKÜ) Elektrik-Elektronik Mühendisliği 4. sınıf öğrencileri için 8. yarıyıl (15 AKTS) İşletmede Mesleki Eğitim (İME), aday mühendislik ve uzun dönem staj pozisyonlarını otomatik olarak keşfeden, puanlayan ve Telegram üzerinden anlık bildiren modüler Python otomasyon sistemidir.

---

## 🏗️ Proje Mimarisi & Klasör Hiyerarşisi

```text
ime_staj_bot/
├── config.py             # Lokasyon, arama filtreleri, E-E yetkinlik skorlama algoritması, ortam ayarları
├── database.py           # SQLite veritabanı (WAL modu, upsert/append-update, 25'li dengeli raporlama)
├── notifier.py           # Telegram bot bildirim modülü (HTML formatı, flood koruması)
├── bot_listener.py       # Telegram interaktif dinleyici (/rapor, /tara, /durum) ve arka plan tarayıcı thread'i
├── main.py               # CLI orkestratörü ve Sunucu Başlatıcı (--server, --once, --stats vb.)
├── requirements.txt      # Gerekli Python kütüphaneleri
├── .env.example          # Telegram ve sunucu ortam değişkenleri şablonu
├── Dockerfile            # Container deployment için Docker dosyası
├── docker-compose.yml    # Docker Compose servis tanımı
├── systemd/
│   └── ime_bot.service   # Ubuntu/Debian Linux VPS için 7/24 kesintisiz systemd servis dosyası
└── scrapers/             # Kazıyıcı ve Portallar
    ├── __init__.py
    ├── osb_directory.py  # ÇOSB, Çorlu 1. OSB, Velimeşe, Ergene ve Muratlı kurumsal üretim rehberi
    ├── active_jobs.py    # HTTP & Playwright tabanlı canlı iş arama ve duyuru kazıyıcı
    └── job_portals.py    # Kariyer.net (mobil) & LinkedIn API canlı iş kazıyıcıları
```

---

## 🎯 Hedef Lokasyonlar ve Sektör Kapsamı

Robot özellikle aşağıdaki Trakya sanayi havzalarını ve ilgili mühendislik disiplinlerini hedefler:
- **Lokasyonlar:** Çerkezköy (ÇOSB), Çorlu (1. OSB & Sanayi Bölgesi), Ergene, Velimeşe OSB, Tekirdağ (Süleymanpaşa), Muratlı OSB, Kapaklı.
- **Odak Sektörler:** Beyaz Eşya, Otomasyon & Makine, İlaç & Biyoteknoloji, Ambalaj & Kağıt, Metalurji, Kimya ve Enerji Santralleri.
- **E-E Skorlama Ağırlıkları:** PLC, SCADA, Pano, Bakım-Onarım, Gömülü Sistemler, Ar-Ge, Sürücüler/Inverter, Yüksek Gerilim ve EPLAN.

---

## 🖥️ Sunucuya (Linux VPS / Ubuntu / Debian) Dağıtım (7/24 Çalıştırma)

Erasmus+ radar botunuz gibi bu botu da uzak bir sunucuya (VPS) taşımak için aşağıdaki adımları izleyebilirsiniz:

### 1. Dosyaları Sunucuya Kopyalama
Yerel bilgisayarınızdan sunucuya `scp` veya `rsync` ile aktarın:
```bash
scp -r ime_staj_bot root@SUNUCU_IP_ADRESI:/root/
```

### 2. Sunucu Ortamını Hazırlama
```bash
# Sunucuya SSH ile bağlanın
ssh root@SUNUCU_IP_ADRESI

# Proje dizinine girin
cd /root/ime_staj_bot

# Python sanal ortamı oluşturun ve aktif edin
python3 -m venv venv
source venv/bin/activate

# Bağımlılıkları kurun
pip install --upgrade pip
pip install -r requirements.txt

# .env dosyanızı oluşturun
cp .env.example .env
nano .env  # TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID bilgilerinizi girin
```

### 3. Systemd Servisini Kurma & Başlatma
```bash
# Servis dosyasını systemd dizinine kopyalayın
cp systemd/ime_bot.service /etc/systemd/system/

# Systemd daemon'ı yenileyin ve servisi aktifleştirin
systemctl daemon-reload
systemctl enable --now ime_bot.service

# Bot durumunu kontrol edin
systemctl status ime_bot.service

# Canlı logları takip edin
journalctl -u ime_bot.service -f
```

---

## 🚀 Yerel Kullanım Komutları

### 1. Sunucu / 7/24 Kesintisiz Mod (Varsayılan)
```powershell
python main.py --server
# veya sadece:
python main.py
```
*Arka planda periyodik tarama thread'i ve kesintisiz Telegram komut dinleyicisini tek süreçte ayağa kaldırır.*

### 2. Tek Seferlik Tarama
```powershell
python main.py --once
```

### 3. Başvuru Durumlarını ve İstatistikleri İnceleme
```powershell
# İstatistik özeti
python main.py --stats

# Kayıtlı ilanları listeleme
python main.py --list
```

---

## 🤖 Telegram Bot Komutları ve İnteraktif Kullanıcı Ekranı

Bot Telegram üzerinden hem **tıklanabilir interaktif buton ekranı (Inline Keyboard)** hem de doğrudan metin komutları ile kontrol edilir:

### 🎛️ İnteraktif Kontrol Paneli Butonları:
- **`[ 🔟 İlk 10 İlan ]`**: En yüksek puanlı ve en taze ilk 10 fırsatı getirir.
- **`[ 🎯 İlk 25 İlan ]`**: En uygun ilk 25 fırsatı özetler.
- **`[ 🚀 İlk 50 İlan ]`**: Kapsamlı ilk 50 fırsatı sayfalı/parçalı olarak iletir.
- **`[ 💯 İlk 100 İlan ]`**: Bölgedeki en geniş 100 fırsatlık listeyi iletir.
- **`[ 🔍 Canlı Tara ]`**: Kariyer.net, LinkedIn ve ÇOSB portallarında anlık canlı tarama tetikler.
- **`[ 📊 Durum & Radar ]`**: Başvuru durumlarını ve takip istatistiklerini gösterir.

### 💬 Doğrudan Metin Komutları:
- **`ilk 10`** veya **`/10`**: İlk 10 ilanı listeler.
- **`ilk 25`** veya **`/25`**: İlk 25 ilanı listeler.
- **`ilk 50`** veya **`/50`**: İlk 50 ilanı listeler.
- **`ilk 100`** veya **`/100`**: İlk 100 ilanı listeler.
- **`/rapor`** veya *"Bugünün raporunu ver"*: Varsayılan ilk 50 güncel ilanı getirir.
- **`/menu`**, **`/panel`** veya **`/start`**: İnteraktif kontrol paneli butonlarını ekrana getirir.
