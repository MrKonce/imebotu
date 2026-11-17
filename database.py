import sqlite3
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from config import DB_PATH, NEGATIVE_KEYWORDS, calculate_relevance_score


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    SQLite veritabanı bağlantısı oluşturur.
    - WAL modunu aktif ederek eşzamanlı okuma/yazma kilitlenmelerini engeller.
    - busy_timeout=5000 ile arka plan işlemlerinde kilitlenmeleri tolere eder.
    - Dict benzeri satır erişimi için Row factory kullanır.
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
    except Exception:
        pass
    return conn


def rescore_all_leads(db_path: str = DB_PATH) -> int:
    """
    Veritabanındaki tüm kayıtlı fırsatları yeni ve hassas E-E skorlama algoritmasıyla
    yeniden puanlar. Alakasız meslekleri (İK, Lojistik, Finans vb.) 0 skor ile deaktif eder.
    """
    updated_count = 0
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, location, source, notes, created_at FROM leads")
        rows = cursor.fetchall()

        for r in rows:
            new_score = calculate_relevance_score(
                title=r["title"],
                text=r["notes"] or "",
                location=r["location"] or "",
                source=r["source"] or "",
                created_at=r["created_at"]
            )
            is_active = 1 if new_score > 0 else 0
            cursor.execute(
                "UPDATE leads SET relevance_score = ?, is_active = ? WHERE id = ?",
                (new_score, is_active, r["id"])
            )
            updated_count += 1

        conn.commit()
    return updated_count


def purge_invalid_leads(db_path: str = DB_PATH) -> int:
    """
    Veritabanındaki alakasız şehirleri (İzmir, Ankara, Gaziantep, Adana, Samsun vb.),
    kıdemli / şantiye pozisyonlarını, YEDAŞ gibi bölgesel firmaları ve
    Türkiye Geneli gibi çoklu şehir ilanlarını tamamen temizler.
    Sadece Tekirdağ / Çorlu / Çerkezköy / Ergene / Velimeşe / Muratlı sanayi havzasına ait
    öğrenci ve İME stajyer fırsatlarını bırakır.
    """
    rescore_all_leads(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM leads
            WHERE source NOT LIKE 'OSB Rehberi%'
              AND (
                  is_active = 0
                  OR relevance_score < 30
                  OR LOWER(title) LIKE '%şantiye%'
                  OR LOWER(title) LIKE '%müdür%'
                  OR LOWER(title) LIKE '%kıdemli%'
                  OR LOWER(title) LIKE '%senior%'
                  OR LOWER(title) LIKE '%gayrimenkul%'
                  OR LOWER(title) LIKE '%adana%'
                  OR LOWER(title) LIKE '%samsun%'
                  OR LOWER(company) LIKE '%dh teknik%'
                  OR LOWER(company) LIKE '%şara%'
                  OR LOWER(company) LIKE '%sara%'
                  OR LOWER(company) LIKE '%akbaş%'
                  OR LOWER(company) LIKE '%green diamond%'
                  OR LOWER(company) LIKE '%remax%'
                  OR LOWER(company) LIKE '%aselsan gaziantep%'
                  OR LOWER(company) LIKE '%yeda%'
                  OR LOWER(company) LIKE '%toroslar%'
                  OR LOWER(company) LIKE '%başkent eda%'
                  OR LOWER(company) LIKE '%baskent eda%'
                  OR LOWER(company) LIKE '%gdz%'
                  OR LOWER(company) LIKE '%aydem%'
                  OR LOWER(company) LIKE '%dicle eda%'
                  OR LOWER(company) LIKE '%çoruh eda%'
                  OR LOWER(company) LIKE '%coruh eda%'
                  OR LOWER(location) LIKE '%türkiye geneli%'
                  OR LOWER(location) LIKE '%turkiye geneli%'
                  OR LOWER(location) LIKE '%tüm şehirler%'
                  OR LOWER(location) LIKE '%tum sehirler%'
                  OR LOWER(location) LIKE '%tümü%'
                  OR LOWER(location) LIKE '%tumu%'
                  OR (
                      LOWER(location) NOT LIKE '%tekirdağ%'
                      AND LOWER(location) NOT LIKE '%tekirdag%'
                      AND LOWER(location) NOT LIKE '%çorlu%'
                      AND LOWER(location) NOT LIKE '%corlu%'
                      AND LOWER(location) NOT LIKE '%çerkezköy%'
                      AND LOWER(location) NOT LIKE '%cerkezkoy%'
                      AND LOWER(location) NOT LIKE '%ergene%'
                      AND LOWER(location) NOT LIKE '%velimeşe%'
                      AND LOWER(location) NOT LIKE '%velimese%'
                      AND LOWER(location) NOT LIKE '%muratlı%'
                      AND LOWER(location) NOT LIKE '%muratli%'
                      AND LOWER(location) NOT LIKE '%kapaklı%'
                      AND LOWER(location) NOT LIKE '%kapakli%'
                      AND LOWER(location) NOT LIKE '%süleymanpaşa%'
                      AND LOWER(location) NOT LIKE '%suleymanpasa%'
                  )
                  OR LOWER(location) LIKE '%adana%'
                  OR LOWER(location) LIKE '%samsun%'
                  OR LOWER(location) LIKE '%izmir%'
                  OR LOWER(location) LIKE '%ankara%'
                  OR LOWER(location) LIKE '%gaziantep%'
                  OR LOWER(location) LIKE '%esenyurt%'
                  OR LOWER(location) LIKE '%bursa%'
                  OR LOWER(location) LIKE '%antalya%'
                  OR LOWER(location) LIKE '%trabzon%'
              )
            """
        )
        purged = cursor.rowcount
        conn.commit()
    return purged


def init_db(db_path: str = DB_PATH) -> None:
    """
    Veritabanı tablolarını, gerekli indeksleri, migrasyonları ve temizlikleri hazırlar.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                url TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                relevance_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Yeni',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
            """
        )

        # Tablo migrasyonu: Eski veritabanlarında eksik sütun varsa ekle
        cursor.execute("PRAGMA table_info(leads)")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        if "updated_at" not in existing_cols:
            cursor.execute("ALTER TABLE leads ADD COLUMN updated_at TIMESTAMP")
            cursor.execute("UPDATE leads SET updated_at = created_at WHERE updated_at IS NULL")
        if "last_seen_at" not in existing_cols:
            cursor.execute("ALTER TABLE leads ADD COLUMN last_seen_at TIMESTAMP")
            cursor.execute("UPDATE leads SET last_seen_at = created_at WHERE last_seen_at IS NULL")
        if "is_active" not in existing_cols:
            cursor.execute("ALTER TABLE leads ADD COLUMN is_active INTEGER DEFAULT 1")
            cursor.execute("UPDATE leads SET is_active = 1 WHERE is_active IS NULL")

        # Hızlı sorgulama ve mükerrer kayıt kontrolü için indeksler
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_url ON leads(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(relevance_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_active ON leads(is_active)")

        # Bot meta verileri (Son tarama zamanı vb.)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_meta (
                key TEXT PRIMARY KEY,
                val TEXT
            )
            """
        )
        conn.commit()

    # Başlangıçta eski veya alakasız şehir kayıtlarını otomatik ayıkla
    try:
        purge_invalid_leads(db_path)
    except Exception as e:
        print(f"[UYARI] Otomatik lead temizliği geçici hata: {e}")


def get_last_scan_time(db_path: str = DB_PATH) -> str:
    """Sistemdeki en son yapılan taramanın zaman damgasını döndürür."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT val FROM bot_meta WHERE key = 'last_scan_time'")
        row = cursor.fetchone()
        if row and row["val"]:
            return row["val"]
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def set_last_scan_time(scan_time_str: Optional[str] = None, db_path: str = DB_PATH) -> None:
    """Son yapılan taramanın zaman damgasını kaydeder."""
    now_str = scan_time_str or datetime.now().strftime("%d.%m.%Y %H:%M")
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bot_meta (key, val) VALUES ('last_scan_time', ?) "
            "ON CONFLICT(key) DO UPDATE SET val = excluded.val",
            (now_str,),
        )
        conn.commit()


def delete_or_deactivate_dead_link(url: str, db_path: str = DB_PATH) -> bool:
    """Ölü link (404, 500 veya kapanmış ilan) tespit edildiğinde veritabanından deaktif eder / siler."""
    clean_url = url.strip()
    if not clean_url:
        return False
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE leads SET is_active = 0 WHERE url = ?", (clean_url,))
        conn.commit()
        return cursor.rowcount > 0


def get_regional_breakdown(db_path: str = DB_PATH) -> Dict[str, int]:
    """
    Tekirdağ ilçelerine göre aktif ilan dağılımını hesaplar.
    Örn: {'Çorlu': 5, 'Çerkezköy': 3, 'Ergene': 1, ...}
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT location FROM leads WHERE is_active = 1 AND relevance_score >= 30")
        rows = cursor.fetchall()

    counts = {
        "Çorlu": 0,
        "Çerkezköy": 0,
        "Ergene": 0,
        "Velimeşe": 0,
        "Muratlı": 0,
        "Kapaklı": 0,
        "Süleymanpaşa": 0,
    }
    for r in rows:
        loc = (r["location"] or "").lower()
        if "çorlu" in loc or "corlu" in loc:
            counts["Çorlu"] += 1
        elif "çerkezköy" in loc or "cerkezkoy" in loc:
            counts["Çerkezköy"] += 1
        elif "velimeşe" in loc or "velimese" in loc:
            counts["Velimeşe"] += 1
        elif "ergene" in loc:
            counts["Ergene"] += 1
        elif "muratlı" in loc or "muratli" in loc:
            counts["Muratlı"] += 1
        elif "kapaklı" in loc or "kapakli" in loc:
            counts["Kapaklı"] += 1
        elif "süleymanpaşa" in loc or "suleymanpasa" in loc:
            counts["Süleymanpaşa"] += 1

    return {k: v for k, v in counts.items() if v > 0}


def lead_exists(url: str, db_path: str = DB_PATH) -> bool:
    """Verilen URL'in veritabanında daha önce kayıtlı olup olmadığını kontrol eder."""
    clean_url = url.strip()
    if not clean_url:
        return False
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM leads WHERE url = ?", (clean_url,))
        return cursor.fetchone() is not None


def upsert_lead(
    company: str,
    title: str,
    location: str,
    url: str,
    source: str,
    relevance_score: Optional[int] = None,
    status: str = "Yeni",
    notes: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Tuple[bool, str]:
    """
    İlanı veritabanına ekler veya günceller (Append/Update mantığı).
    
    Skor belirtilmemişse dinamik ve güncel E-E algoritmasıyla otomatik hesaplar.
    Alakasız ilanları (relevance_score <= 0) veritabanına almaz.
    """
    clean_url = url.strip()
    if not clean_url:
        return False, "ignored"

    clean_company = company.strip()
    clean_title = title.strip()
    clean_location = location.strip() if location else "Tekirdağ"
    clean_source = source.strip()
    clean_notes = notes.strip() if notes else ""

    # Katı Beyaz Liste (Strict Whitelist) Doğrulaması (OSB Rehberi hedefleri hariç)
    if "OSB Rehberi" not in clean_source:
        from config import validate_strict_location
        is_valid_loc, loc_reason = validate_strict_location(
            raw_location=clean_location,
            title=clean_title,
            company=clean_company
        )
        if not is_valid_loc:
            return False, f"ignored: {loc_reason}"

    # Skoru güncel ve hassas hesapla
    if relevance_score is None or relevance_score <= 0:
        score = calculate_relevance_score(
            title=clean_title,
            text=clean_notes,
            location=clean_location,
            source=clean_source,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            company=clean_company
        )
    else:
        score = relevance_score

    # Kesinlikle alakasız meslekleri (İK, emlak, muhasebe vb.) veritabanına kaydetme
    if score <= 0:
        return False, "ignored"

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status, relevance_score, notes FROM leads WHERE url = ?",
            (clean_url,)
        )
        existing = cursor.fetchone()

        if existing:
            # GÜNCELLEME (Update) MANTIĞI
            lead_id = existing["id"]
            existing_status = existing["status"]
            # Kullanıcının verdiği özel durumu ('Başvuruldu', 'Mülakat' vb.) koru
            final_status = existing_status if existing_status != "Yeni" else status
            final_score = max(existing["relevance_score"] or 0, score)
            final_notes = clean_notes if clean_notes else (existing["notes"] or "")

            cursor.execute(
                """
                UPDATE leads
                SET company = ?,
                    title = ?,
                    location = ?,
                    source = ?,
                    relevance_score = ?,
                    status = ?,
                    notes = ?,
                    last_seen_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    is_active = 1
                WHERE id = ?
                """,
                (clean_company, clean_title, clean_location, clean_source, final_score, final_status, final_notes, lead_id),
            )
            conn.commit()
            return False, "updated"
        else:
            # EKLEME (Insert) MANTIĞI
            cursor.execute(
                """
                INSERT INTO leads (
                    company, title, location, url, source, relevance_score, status, notes,
                    created_at, updated_at, last_seen_at, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                """,
                (
                    clean_company,
                    clean_title,
                    clean_location,
                    clean_url,
                    clean_source,
                    score,
                    status,
                    clean_notes if clean_notes else None,
                ),
            )
            conn.commit()
            return True, "inserted"


def insert_lead(
    company: str,
    title: str,
    location: str,
    url: str,
    source: str,
    relevance_score: int = 0,
    status: str = "Yeni",
    notes: Optional[str] = None,
    db_path: str = DB_PATH,
) -> bool:
    """Geriye dönük uyumluluk sarmalayıcısı."""
    is_new, _ = upsert_lead(
        company=company,
        title=title,
        location=location,
        url=url,
        source=source,
        relevance_score=relevance_score,
        status=status,
        notes=notes,
        db_path=db_path,
    )
    return is_new


def get_leads(
    status: Optional[str] = None,
    min_score: int = 15,
    order_by: str = "score",
    limit: int = 100,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    """Kayıtlı aktif ilanları filtrelere göre listeler."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM leads WHERE is_active = 1 AND relevance_score >= ?"
        params: List[Any] = [min_score]

        if status:
            query += " AND status = ?"
            params.append(status)

        if order_by == "recent":
            query += " ORDER BY created_at DESC, relevance_score DESC LIMIT ?"
        else:
            query += " ORDER BY relevance_score DESC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_ranked_leads(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Kullanıcının talep ettiği adette (10, 25, 50, 100 vb.) en güncel çalışan ve
    TNKÜ E-E İME profiline en uygun ilanları kusursuz sıralamayla çeker.
    
    Sıralama ve Filtreleme Kriterleri:
    - Kesinlikle sadece Tekirdağ / Çorlu / Çerkezköy / Ergene / Velimeşe / Muratlı sanayi havzası
    - İzmir, Ankara, Gaziantep, Samsun, Esenyurt vb. uzak şehirler SQL seviyesinde KESİNLİKLE ENGELLENİR.
    - Kıdemli, şantiye şefi, müdür ve stajyer/öğrenci dışı ilanlar elenir.
    - Bel Karper, Zorluteks, Dinarsu, GF Hakan, EAE Elektrik gibi 1. sınıf OSB İME fırsatları önceliklidir.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM leads
            WHERE is_active = 1
              AND relevance_score >= 30
              AND LOWER(company) NOT LIKE '%dh teknik%'
              AND LOWER(company) NOT LIKE '%şara%'
              AND LOWER(company) NOT LIKE '%sara%'
              AND LOWER(company) NOT LIKE '%akbaş%'
              AND LOWER(company) NOT LIKE '%green diamond%'
              AND LOWER(company) NOT LIKE '%remax%'
              AND LOWER(company) NOT LIKE '%yeda%'
              AND LOWER(company) NOT LIKE '%toroslar%'
              AND LOWER(company) NOT LIKE '%başkent eda%'
              AND LOWER(company) NOT LIKE '%baskent eda%'
              AND LOWER(title) NOT LIKE '%şantiye%'
              AND LOWER(title) NOT LIKE '%müdür%'
              AND LOWER(title) NOT LIKE '%kıdemli%'
              AND LOWER(title) NOT LIKE '%senior%'
              AND LOWER(title) NOT LIKE '%gayrimenkul%'
              AND LOWER(title) NOT LIKE '%adana%'
              AND LOWER(title) NOT LIKE '%samsun%'
              AND (
                  LOWER(location) LIKE '%tekirdağ%'
                  OR LOWER(location) LIKE '%tekirdag%'
                  OR LOWER(location) LIKE '%çorlu%'
                  OR LOWER(location) LIKE '%corlu%'
                  OR LOWER(location) LIKE '%çerkezköy%'
                  OR LOWER(location) LIKE '%cerkezkoy%'
                  OR LOWER(location) LIKE '%ergene%'
                  OR LOWER(location) LIKE '%velimeşe%'
                  OR LOWER(location) LIKE '%velimese%'
                  OR LOWER(location) LIKE '%muratlı%'
                  OR LOWER(location) LIKE '%muratli%'
                  OR LOWER(location) LIKE '%kapaklı%'
                  OR LOWER(location) LIKE '%kapakli%'
                  OR LOWER(location) LIKE '%süleymanpaşa%'
                  OR LOWER(location) LIKE '%suleymanpasa%'
                  OR source LIKE 'OSB Rehberi%'
              )
              AND LOWER(location) NOT LIKE '%izmir%'
              AND LOWER(location) NOT LIKE '%ankara%'
              AND LOWER(location) NOT LIKE '%gaziantep%'
              AND LOWER(location) NOT LIKE '%samsun%'
              AND LOWER(location) NOT LIKE '%adana%'
              AND LOWER(location) NOT LIKE '%esenyurt%'
              AND LOWER(location) NOT LIKE '%türkiye geneli%'
              AND LOWER(location) NOT LIKE '%turkiye geneli%'
              AND LOWER(location) NOT LIKE '%tüm şehirler%'
              AND LOWER(location) NOT LIKE '%tum sehirler%'
            ORDER BY relevance_score DESC, created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_top_20_leads(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """En yeni ve E-E/İME/Staj açısından en uygun ilk 20 ilanı getirir."""
    return get_ranked_leads(limit=20, db_path=db_path)


def get_all_active_leads(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Katı lokasyon filtremizden geçen tüm aktif ilanları listeler."""
    return get_ranked_leads(limit=500, db_path=db_path)


def get_report_leads(limit: int = 20, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Geriye dönük uyumluluk için get_ranked_leads wrapper'ı."""
    leads = get_ranked_leads(limit=limit, db_path=db_path)
    return {
        "leads": leads,
        "total_count": len(leads)
    }


def update_lead_status(
    lead_id: int,
    new_status: str,
    notes: Optional[str] = None,
    db_path: str = DB_PATH,
) -> bool:
    """Bir ilanın başvuru durumunu ve notunu günceller."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if notes is not None:
            cursor.execute(
                "UPDATE leads SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, notes, lead_id),
            )
        else:
            cursor.execute(
                "UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, lead_id),
            )
        conn.commit()
        return cursor.rowcount > 0


def get_statistics(db_path: str = DB_PATH) -> Dict[str, Any]:
    """Sistemdeki toplam doğrulanmış yerel ilan ve başvuru istatistiklerini hesaplar."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads WHERE is_active = 1 AND relevance_score >= 30")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM leads WHERE is_active = 1 AND relevance_score >= 30 GROUP BY status")
        by_status = dict(cursor.fetchall())

        cursor.execute("SELECT AVG(relevance_score) FROM leads WHERE is_active = 1 AND relevance_score >= 30")
        avg_score = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT COUNT(DISTINCT company) FROM leads WHERE is_active = 1 AND relevance_score >= 30")
        unique_companies = cursor.fetchone()[0]

        # Son 24 saat içinde eklenen taze ilan sayısı
        cursor.execute(
            """
            SELECT COUNT(*) FROM leads
            WHERE is_active = 1
              AND relevance_score >= 30
              AND (julianday('now') - julianday(created_at)) <= 1.0
            """
        )
        recent_24h_count = cursor.fetchone()[0] or 0

        # Son 3 gün içinde eklenen taze ilan sayısı
        cursor.execute(
            """
            SELECT COUNT(*) FROM leads
            WHERE is_active = 1
              AND relevance_score >= 30
              AND source NOT LIKE 'OSB Rehberi%'
              AND (julianday('now') - julianday(created_at)) <= 3.0
            """
        )
        new_recent_count = cursor.fetchone()[0] or 0

        return {
            "total_leads": total,
            "status_breakdown": by_status,
            "average_score": round(avg_score, 1),
            "unique_companies": unique_companies,
            "recent_new_leads": new_recent_count,
            "recent_24h_leads": recent_24h_count,
        }
