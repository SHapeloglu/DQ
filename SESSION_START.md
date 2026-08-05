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
- profiler.py       → cache + PII tagging + enum/regex/empty önerileri ✅
- extensions.py     → AlertManager (email/slack/webhook) ✅

## Routers (routers/)
- routers/sources.py → /sources CRUD ✅
- routers/checks.py  → /checks CRUD + /api/suggestions/reject ✅
- routers/api.py     → /api/* + /odata + alerting + /api/health-score + /api/glossary ✅
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
- ÖNEMLİ: Kod değişikliklerinin yürürlüğe girmesi için `docker compose build dq-web && docker compose up -d dq-web` gerekir
  (sadece dags/ klasörü volume mount edilmiş, diğer dosyalar image içinde)

## Postgres (MetricStore — Production)
- DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
- Şema: dwh_health_log.dq_metrics ✅

## Business Glossary
- column_profiles tablosuna eklendi: business_name, description, owner, tags
- GET  /api/glossary/{source_id}
- PUT  /api/glossary/{source_id}/{column_name}

## Airflow DAG'ları (dags/)
- dq_mysql_dag.py, dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- dq_scheduled_profiling_dag.py → scheduled_profiling.toml ile periyodik profil tetikleme ✅

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir
- DB migration: docker exec -i dq-db mysql -u root -proot dq -e "..."

## Tamamlananlar (Bu Session)
- [x] GÖREV 9: Business Glossary — column_profiles + GET/PUT endpoint (commit: 1c5f604)
- [x] GÖREV 11: referential_integrity assert tipi + testler (commit: f6c8c50)
- [x] GÖREV 10: Scheduled Profiling DAG + TOML config (commit: 5757043)
- [x] routers/ unit testleri — 12 test (commit: 30abc14)
- [x] 96 passed, 3 skipped

## Açık Görevler
- [ ] profile_column: 3-4 ayrı SQL → birleştirme (connector API sınırı, riskli, ertelendi)
- [ ] Docker Secrets / Vault entegrasyonu (ertelendi)
- [ ] Airflow connection'ları secure store'dan yükle (ertelendi)
- [ ] GÖREV 9 kalan: Wizard'da glossary bilgisi gösterimi (UI tarafı)

## Git Son Commit
30abc14 feat: routers/ unit testleri — sources, checks, glossary iş mantığı (12 test)

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md yükle
2. Wizard'da glossary UI veya yeni görev
