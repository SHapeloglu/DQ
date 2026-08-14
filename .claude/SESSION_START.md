# DQ — Session Başlangıç Dosyası

Proje: DQ (Data Quality Platform)
Konum: `/opt/dq/dq_docker` (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL 8.0 + Airflow + Docker Compose

---

## Mimari (Özet)

- `dq/engine.py` → CheckEngine + assert tipleri ✅
  Tüm assert tipleri: not_empty, regex_match, accepted_values, freshness_hours,
  row_count_between, referential_integrity, equals, between, greater_than, less_than,
  completeness_ratio, statistical_anomaly, schema_drift, schema_check,
  duplicate_row, custom_sql, volume_anomaly,
  zscore_anomaly, cross_table_check, distribution_check, trend_check
- `dq/config.py` → SodaConfig + _resolve_env_vars() + _ASSERTION_MAP (~satır 46) ✅
- `dq/connectors.py` → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- `dq/metrics.py` → MetricStore (SQLite dev + Postgres prod) + get_recent_values(name, n) ✅
- `dq/scoring.py` → get_health_score(), get_score_trend(), get_all_scores() ✅
- `dq/reporter_v2.py` → full_report() + MetricStore entegrasyonu ✅
- `dq/airflow.py` → DQOperator — check'leri Airflow üzerinden çalıştırır ✅
- `secrets_loader.py` → get_secret(key, default) — /run/secrets/ → env → default ✅
- `main.py` → FastAPI app init + router include'ları ✅
- `database.py` → MySQL init_db() + _DBPool (size=5, thread-safe) + get_conn/release_conn ✅
- `cache_layer.py` → TTLCache + profile_cache singleton (5 dk TTL) ✅
- `profiler.py` → cache + PII tagging (24 pattern) + enum/regex/empty önerileri ✅
  NOT: profile_column → tek sorguda tüm istatistikler (GOREV 29)
  Tip tespiti: num_avg IS NOT NULL → numeric; str_min_len IS NOT NULL → string/date
- `extensions.py` → AlertManager (email/slack/webhook) + send_summary_report() ✅

---

## Routers

- `routers/sources.py` → /sources CRUD ✅
- `routers/checks.py` → /checks CRUD + /api/suggestions/reject ✅
- `routers/api.py` → /api/* + /odata + alerting + /api/health-score +
  /api/glossary + /api/pii-report + /api/alert-settings + /api/rule-library +
  /api/anomaly-results + /api/cross-table-results + /api/distribution-results ✅
- `routers/ui.py` → /wizard, /import, /runs, /health, /rule-library,
  /anomaly, /cross-table, /distribution, / ✅

---

## UI Sayfaları

- `/` → Ana sayfa
- `/health` → Sağlık Skoru Dashboard
- `/anomaly` → Anomali Dashboard
- `/cross-table` → Cross-Table Kontroller
- `/distribution` → Distribution Check görsel grafik
- `/rule-library` → Rule Library
- `/wizard` → Profil + kural ekleme sihirbazı
- `/runs` → Run geçmişi

---

## Kritik Notlar

- `from __future__ import annotations` + Pydantic çakışması: api.py/ui.py'de dikkat
- `sed` güvenilmez — Python string replace scripti kullan (`/tmp/` altında)
- heredoc: `cat > /tmp/fix.py << 'EOF'` sonra `python3 /tmp/fix.py`
- pymysql venv'de yok — testlerde DB import etme, MagicMock kullan
- Docker build: `docker compose build dq-web && docker compose up -d dq-web`
- DB migration: `docker exec -i dq-db mysql -u root -proot dq -e "..."`
- Connection pool: get_conn() havuzdan alır, release_conn(conn) havuza iade eder
- secrets_loader: TOML'da `password = "secret:DB_PASSWORD"` prefix kullan

---

## Güvenlik Katmanı
- `secrets/.env.secrets` → password'lar + SMTP/alert config (chmod 600, git ignore)
- `secrets/.env.secrets.gpg` → şifreli kopya (git'te ✅)
- `secrets_loader.py` → get_secret(key, default): /run/secrets/ → env → default
- GPG key: dq@localhost (RSA 4096)

---

## Docker
- `dq-web` → 0.0.0.0:8002 (uvicorn)
- `dq-db` → 0.0.0.0:3308 (mysql:8.0)

---

## DB Tabloları
- `sources` (+ alert_enabled)
- `checks`, `runs`, `run_results`
- `column_profiles` (+ business_name, description, owner, tags, is_pii, pii_type)
- `alert_settings` (id=1 singleton)
- `rule_library` (column_name_pattern, rule_type, times_used, times_accepted, times_rejected)

---

## Test Durumu
**191 passed, 3 skipped ✅**

---

## Git Son Commitler

27afb10 feat: GOREV 29 — profile_column tek sorgu optimizasyonu (3 sorgu -> 1)
d3ecabd feat: GOREV 27 — thread-safe MySQL connection pool
ee487ff feat: GOREV 26 — TOML'da secret: prefix destegi
41ea8b4 feat: GOREV 25 — secrets_loader.py eklendi

---

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md + TASKS.md zip'le, yukle
2. Backlog: GOREV 28 (Vault/Docker Swarm Secrets) — production hardening
