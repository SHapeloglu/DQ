# DQ — Session Başlangıç Dosyası
Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/reporter.py    → DEPRECATED — reporter_v2.py kullan
- dq/reporter_v2.py → full_report() + MetricStore entegrasyonu + report() alias ✅
- dq/airflow.py     → DQOperator (explicit imports ✅)
- main.py           → FastAPI app + Jinja2 UI (672 satır)
- database.py       → MySQL init_db()

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir

## Tamamlananlar
- [x] .gitignore + .env git takibinden çıkarıldı
- [x] GÖREV 1 — Güvenlik: .env.example, docker-compose credentials (commit: 5249127)
- [x] GÖREV 2 — MetricStore Postgres: migration script, reporter_v2 (commit: e931715)
- [x] GÖREV 3 — MongoConnector: pipeline + filter dict query
- [x] GÖREV 4 — DB2 support: ibm_db_sa kütüphanesi
- [x] GÖREV 5 — Airflow DAGs: PostgreSQL, Oracle, MongoDB
- [x] DQOperator lazy importları dosya başına taşındı (commit: da49c54)
- [x] 73 passed, 3 skipped

## Açık Teknik Borçlar
- [ ] main.py route ayrımı → routes.py (ertelendi)
- [ ] Production Vault/Docker Secrets entegrasyonu (ertelendi)
- [ ] dwh_health_log migration → production Postgres'te çalıştır
- [ ] METRICS_PG_DSN → .env'e ekle (production hazır olduğunda)

## Git Son Commit
e69dbd2 docs: TASKS.md güncelle — GÖREV 1+2 tamamlandı olarak işaretlendi

## Yeni Session'da Yap
1. Bu dosyayı yükle
2. CLAUDE.md + ARCHITECTURE.md de yükle
3. Hangi göreve devam edeceğini söyle
