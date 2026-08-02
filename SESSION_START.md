# DQ — Session Başlangıç Dosyası
Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/config.py      → SodaConfig + _resolve_env_vars() (env override) ✅
- dq/reporter_v2.py → full_report() + MetricStore entegrasyonu ✅
- dq/airflow.py     → DQOperator (explicit imports ✅)
- main.py           → FastAPI app init + router include'ları (59 satır) ✅
- database.py       → MySQL init_db()
- cache_layer.py    → TTLCache + profile_cache singleton (5 dk TTL) ✅
- profiler.py       → profile_column cache entegrasyonu ✅

## Routers (routers/)
- routers/sources.py → /sources CRUD (5 route) ✅
- routers/checks.py  → /checks CRUD + /api/suggestions/reject (7 route) ✅
- routers/api.py     → /api/columns, /api/profile, /api/runs, /api/results, /odata/Results ✅
- routers/ui.py      → /wizard, /import, /runs, /runs/{run_id}, / (index) ✅

## Güvenlik Katmanı
- secrets/.env.secrets     → password'lar (chmod 600, git ignore)
- secrets/.env.secrets.gpg → şifreli kopya (git'te ✅)
- scripts/decrypt_secrets.sh → deploy öncesi çalıştır
- GPG key: dq@localhost (RSA 4096, /root/.gnupg)
- Deploy akışı: bash scripts/decrypt_secrets.sh && docker-compose up -d

## Postgres (MetricStore — Production)
- DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
- Şema: dwh_health_log.dq_metrics ✅

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir

## Tamamlananlar (Bu Session)
- [x] L: main.py route ayrımı → routers/ (672→59 satır, %91 küçültme)
- [x] perf: get_library_suggestions N+1 → tek sorgu (commit: 4d46e77)
- [x] perf: profile_source INSERT → executemany (commit: 8cbbc99)
- [x] feat: cache_layer.py TTL cache + profiler.py entegrasyonu (commit: 36d42a9)
- [x] 73 passed, 3 skipped

## Açık Teknik Borçlar
- [ ] profile_column: her kolon için 3-4 ayrı SQL — connector API sınırı nedeniyle refactor riskli, ertelendi
- [ ] optimized_profiler.py — profile_column sorgularını tek SQL'de birleştir (büyük iş)
- [ ] Docker Secrets / Vault entegrasyonu (ertelendi)
- [ ] Airflow connection'ları secure store'dan yükle (ertelendi)

## Git Son Commit
36d42a9 feat: cache_layer.py — TTL cache + profiler.py entegrasyonu

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md yükle
2. Seçenekler:
   - optimized_profiler.py — profile_column sorgularını birleştir
   - Yeni özellik / TASKS.md'den görev
   - Test coverage artır (cache_layer için unit test yaz)
