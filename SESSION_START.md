# DQ — Session Başlangıç Dosyası
Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine + assert tipleri (not_empty, regex_match, accepted_values, freshness_hours, row_count_between, referential_integrity) ✅
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/config.py      → SodaConfig + _resolve_env_vars() + referential_integrity ✅
- dq/scoring.py     → get_health_score(), get_score_trend(), get_all_scores() ✅
- dq/reporter_v2.py → full_report() + MetricStore entegrasyonu ✅
- dq/airflow.py     → DQOperator ✅
- main.py           → FastAPI app init + router include'ları (59 satır) ✅
- database.py       → MySQL init_db() + column_profiles PII + glossary kolonları ✅
- cache_layer.py    → TTLCache + profile_cache singleton (5 dk TTL) ✅
- profiler.py       → cache + PII tagging (24 pattern) + enum/regex/empty önerileri ✅
- extensions.py     → AlertManager (email/slack/webhook) + load_alert_manager ✅

## Routers (routers/)
- routers/sources.py → /sources CRUD ✅
- routers/checks.py  → /checks CRUD + /api/suggestions/reject ✅
- routers/api.py     → /api/* + /odata + alerting + /api/health-score + /api/glossary + /api/pii-report + /api/alert-settings ✅
- routers/ui.py      → /wizard, /import, /runs, /health, / ✅

## Güvenlik Katmanı
- secrets/.env.secrets     → password'lar + SMTP/alert config (chmod 600, git ignore)
- secrets/.env.secrets.gpg → şifreli kopya (git'te ✅)
- scripts/decrypt_secrets.sh → deploy öncesi çalıştır
- GPG key: dq@localhost (RSA 4096, /root/.gnupg)
- Deploy akışı: bash scripts/decrypt_secrets.sh && docker-compose up -d

## Docker
- dq-web  → 0.0.0.0:8002 (uvicorn)
- dq-db   → 0.0.0.0:3308 (mysql:8.0)
- ÖNEMLİ: Kod değişikliklerinin yürürlüğe girmesi için docker compose build dq-web && docker compose up -d dq-web gerekir

## Postgres (MetricStore — Production)
- DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
- Şema: dwh_health_log.dq_metrics ✅

## Alerting (GÖREV 7 ✅)
- alert_settings tablosu: slack_webhook, webhook_url, email_to, smtp_*
- sources.alert_enabled kolonu: kaynak bazlı aç/kapa
- GET/PUT /api/alert-settings
- PUT /api/sources/{id}/alert-enabled
- api_post_run → DB'den load_alert_manager + alert_enabled kontrolü

## PII / KVKK (GÖREV 8 ✅)
- profiler.py: 24 PII keyword (tckn, adres, pasaport, kredi, sifre, ip_, konum vb.)
- GET /api/pii-report            → tüm kaynaklar KVKK özet
- GET /api/pii-report/{source_id} → kaynak bazlı PII kolon detayı

## DB Tabloları
- sources (+ alert_enabled)
- checks, runs, run_results
- column_profiles (+ business_name, description, owner, tags, is_pii, pii_type)
- alert_settings (id=1 singleton)
- rule_library

## Airflow DAG'ları (dags/)
- dq_mysql_dag.py, dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- dq_scheduled_profiling_dag.py ✅

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir
- DB migration: docker exec -i dq-db mysql -u root -proot dq -e "..."
- Çalışma dizini: /opt/dq/dq_docker — root'tan komut çalıştırma

## Tamamlananlar (Bu Session)
- [x] GÖREV 7: Alerting (commit: 7e505ea)
- [x] GÖREV 8: PII Otomatik Tespiti (commit: 5b6c6d0)

## Test Durumu
108 passed, 3 skipped ✅

## Açık Görevler
- [ ] GÖREV 6: Dashboard UI (scoring.py var, endpoint'ler var, UI eksik)
- [ ] GÖREV 9 kalan: Wizard'da glossary UI

## Git Son Commitler
5b6c6d0 feat: GÖREV 8 PII
7e505ea feat: GÖREV 7 alerting
30abc14 feat: routers unit testleri

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md + TASKS.md yükle
2. GÖREV 6 Dashboard UI veya GÖREV 9 Wizard glossary
