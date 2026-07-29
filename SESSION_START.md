# DQ — Session Başlangıç Dosyası

Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/airflow.py     → DQOperator
- main.py           → FastAPI app + Jinja2 UI
- database.py       → MySQL init_db()

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir

## Tamamlananlar
- [x] .gitignore + .env git takibinden çıkarıldı
- [x] MetricStore → SQLite(dev) + Postgres(prod) dual backend
- [x] SqlAlchemyConnector → dialect-based URL
- [x] OracleConnector → service_name parametresi
- [x] MongoConnector → pipeline + filter dict query (GÖREV 3) ✅
- [x] DB2 support → ibm_db_sa kütüphanesi (GÖREV 4) ✅
- [x] Airflow DAGs → PostgreSQL, Oracle, MongoDB DAG'ları (GÖREV 5) ✅
- [x] 69 passed, 1 skipped

## Aktif Görevler
- GÖREV 1 — Güvenlik (Production .env → Vault/Docker Secrets)
- GÖREV 2 — MetricStore → Postgres dwh_health_log şemasına taşı

## Git Son Commit
a7203b4 GÖREV 3+4+5: MongoConnector, DB2, Airflow DAGs
