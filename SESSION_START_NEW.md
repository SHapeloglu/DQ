# DQ — Session Başlangıç Dosyası

Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/reporter.py    → DEPRECATED — reporter_v2.py kullan
- dq/reporter_v2.py → full_report() + MetricStore entegrasyonu ✅
- dq/airflow.py     → DQOperator
- main.py           → FastAPI app + Jinja2 UI
- database.py       → MySQL init_db()
- scripts/migrate_metrics_postgres.sql → dwh_health_log şeması

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir

## Tamamlananlar
- [x] .gitignore + .env git takibinden çıkarıldı
- [x] MetricStore → SQLite(dev) + Postgres(prod) dual backend
- [x] SqlAlchemyConnector → dialect-based URL + test_connection() + dialect key
- [x] OracleConnector → service_name parametresi eklendi
- [x] pytest.ini → integration mark, Oracle testleri skip
- [x] MongoConnector → pipeline + filter dict query (GÖREV 3)
- [x] DB2 support → ibm_db_sa kütüphanesi (GÖREV 4)
- [x] Airflow DAGs → PostgreSQL, Oracle, MongoDB DAG'ları (GÖREV 5)
- [x] **GÖREV 1 — Güvenlik** → .env.example, docker-compose hardcoded credentials kaldırıldı (commit: 5249127)
- [x] **GÖREV 2 — MetricStore Postgres** → migration script, reporter deprecated, reporter_v2 MetricStore entegrasyonu (commit: e931715)
- [x] tests/test_metrics.py → 4 test (SQLite backend)
- [x] 73 passed, 1 skipped

## Sonraki Görevler
- [ ] __main__.py → reporter_v2'ye geçir (reporter.py deprecated uyarısını kapat)
- [ ] Postgres MetricStore integration testi yaz (skip guard ile)
- [ ] dwh_health_log migration'ı production Postgres'te çalıştır

## Yeni Session'da Yap
1. Bu dosyayı yükle
2. CLAUDE.md + ARCHITECTURE.md de yükle
3. Hangi göreve devam edeceğini söyle

## Darboğaz → Yeni Session
Belirtiler: yanıtlar yavaşladı / önceki kodu unuttu / alakasız öneri geldi

Yapılacak:
1. Yeni chat aç
2. Bu 3 dosyayı yükle
3. Şunu ekle: "Son yapılan: [ne yaptık] / Devam noktası: [fonksiyon adı]"
4. O anki ilgili fonksiyonu yapıştır (tüm dosyayı değil)
