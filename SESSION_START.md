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
- scripts/migrate_metrics_postgres.sql → dwh_health_log şeması ✅

## Postgres (MetricStore — Production)
- Host: 127.0.0.1:5432 (sunucuda native Postgres çalışıyor)
- DB: dqmetrics | User: dquser | Pass: dqpass
- DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
- Şema: dwh_health_log.dq_metrics (migration çalıştırıldı ✅)

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir

## Tamamlananlar (Bu Session)
- [x] DQOperator lazy importları dosya başına taşındı (commit: da49c54)
- [x] TASKS.md güncellendi — GÖREV 1+2 tamamlandı (commit: e69dbd2)
- [x] METRICS_PG_DSN → .env'e eklendi
- [x] Host Postgres: dquser + dqmetrics DB oluşturuldu
- [x] dwh_health_log migration çalıştırıldı (commit: a870da6)
- [x] 73 passed, 3 skipped

## Tüm Tamamlananlar
- [x] GÖREV 1 — Güvenlik: .env.example, docker-compose credentials (commit: 5249127)
- [x] GÖREV 2 — MetricStore Postgres: migration script, reporter_v2 (commit: e931715)
- [x] GÖREV 3 — MongoConnector: pipeline + filter dict query
- [x] GÖREV 4 — DB2 support: ibm_db_sa kütüphanesi
- [x] GÖREV 5 — Airflow DAGs: PostgreSQL, Oracle, MongoDB
- [x] pytest.ini — integration mark tanımlı, warning yok
- [x] SqlAlchemyConnector → dialect-based URL + dialect key
- [x] OracleConnector → service_name parametresi
- [x] __main__.py → reporter_v2'ye geçirildi

## Açık Teknik Borçlar
- [ ] main.py route ayrımı → routes.py (672 satır, ertelendi)
- [ ] Production Vault/Docker Secrets entegrasyonu (ertelendi)
- [ ] Airflow connection'ları secure store'dan yükle (ertelendi)
- [ ] Database credentials encrypted olarak sakla (ertelendi)

## Git Son Commit
a870da6 feat: host Postgres kullan — dqmetrics DB + dquser oluşturuldu, migration çalıştırıldı

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md yükle
2. Hangi göreve devam edeceğini söyle
3. İlgili fonksiyonu yapıştır (tüm dosyayı değil)

## Darboğaz Belirtileri
Yanıtlar yavaşladı / önceki kodu unuttu → yeni chat aç, 3 dosyayı yükle
