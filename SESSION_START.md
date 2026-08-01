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
- main.py           → FastAPI app + Jinja2 UI (672 satır) — route ayrımı BEKLIYOR
- database.py       → MySQL init_db()

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
- [x] XS: TOML credentials env override — _resolve_env_vars() (commit: b8ce864)
- [x] S: secrets/ klasörü + docker-compose env_file (commit: 19e0254)
- [x] M: GPG şifreleme + decrypt_secrets.sh (commit: d3dfdd2)
- [x] 73 passed, 3 skipped

## Açık Teknik Borçlar
- [ ] L: main.py route ayrımı → routers/ (routers/__init__.py oluşturuldu, route grupları belirlendi)
  - ui.py     → /, /wizard, /import
  - sources.py → /sources CRUD
  - checks.py  → /checks CRUD + suggestions
  - api.py    → /api + /runs + /odata

## Git Son Commit
d3dfdd2 fix: decrypt_secrets.sh — gpg --yes ile overwrite sorma

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md yükle
2. L görevi: main.py route ayrımı — routers/ klasörü hazır
3. İlk adım: sources.py router'ını oluştur
