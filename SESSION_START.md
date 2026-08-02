# DQ — Session Başlangıç Dosyası
Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine + assert tipleri (not_empty, regex_match, accepted_values, freshness_hours) ✅
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/config.py      → SodaConfig + _resolve_env_vars() ✅
- dq/reporter_v2.py → full_report() + MetricStore entegrasyonu ✅
- dq/airflow.py     → DQOperator ✅
- main.py           → FastAPI app init + router include'ları (59 satır) ✅
- database.py       → MySQL init_db() + column_profiles PII kolonları ✅
- cache_layer.py    → TTLCache + profile_cache singleton (5 dk TTL) ✅
- profiler.py       → cache + PII tagging + enum/regex/empty önerileri ✅
- extensions.py     → AlertManager (email/slack/webhook) ✅

## Routers (routers/)
- routers/sources.py → /sources CRUD ✅
- routers/checks.py  → /checks CRUD + /api/suggestions/reject ✅
- routers/api.py     → /api/* + /odata + alerting entegrasyonu ✅
- routers/ui.py      → /wizard, /import, /runs, / ✅

## Güvenlik Katmanı
- secrets/.env.secrets     → password'lar + SMTP/alert config (chmod 600, git ignore)
- secrets/.env.secrets.gpg → şifreli kopya (git'te ✅)
- scripts/decrypt_secrets.sh → deploy öncesi çalıştır
- GPG key: dq@localhost (RSA 4096, /root/.gnupg)
- Deploy akışı: bash scripts/decrypt_secrets.sh && docker-compose up -d

## Docker
- dq-web  → 0.0.0.0:8002 (uvicorn)
- dq-db   → 0.0.0.0:3308 (mysql:8.0)

## Postgres (MetricStore — Production)
- DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
- Şema: dwh_health_log.dq_metrics ✅

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir
- DB migration: docker exec -i dq-db mysql -u root -proot dq -e "..."

## Tamamlananlar (Bu Session)
- [x] L: main.py route ayrımı → routers/ (672→59 satır) (commit: 5813915)
- [x] perf: N+1 fix + executemany (commit: 4d46e77, 8cbbc99)
- [x] feat: cache_layer.py TTL cache (commit: 36d42a9)
- [x] feat: yeni assert tipleri (commit: 9736b9d)
- [x] feat: GÖREV 7 alerting (commit: 263fe8c)
- [x] feat: GÖREV 8 PII tagging (commit: 92d5fcc)
- [x] 73 passed, 3 skipped

## Açık Görevler (Öncelik Sırasına Göre)
- [ ] GÖREV 6: Sağlık Skoru Dashboard (0-100 skor, trafik ışığı, trend)
- [ ] GÖREV 9: Business Glossary (kolon açıklaması, sahip, etiket)
- [ ] GÖREV 10: Scheduled Profiling (Airflow DAG ile otomatik)
- [ ] GÖREV 11 kalan: referential_integrity, row_count_between
- [ ] profile_column: 3-4 ayrı SQL → birleştirme (connector API sınırı, riskli)
- [ ] routers/ için unit testler

## Git Son Commit
92d5fcc feat: GÖREV 8 — PII tagging (is_pii, pii_type) column_profiles'a eklendi

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md yükle
2. GÖREV 6: Sağlık Skoru Dashboard'dan başla
