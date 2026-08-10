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
- `main.py` → FastAPI app init + router include'ları ✅
- `database.py` → MySQL init_db() + column_profiles PII + glossary kolonları ✅
- `cache_layer.py` → TTLCache + profile_cache singleton (5 dk TTL) ✅
- `profiler.py` → cache + PII tagging (24 pattern) + enum/regex/empty önerileri ✅
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

- `/` → Ana sayfa (kaynak özeti + son run'lar + Analiz Sayfaları kartı)
- `/health` → Sağlık Skoru Dashboard
- `/anomaly` → Anomali Dashboard (zscore/volume/trend/distribution sonuçları)
- `/cross-table` → Cross-Table Kontroller
- `/distribution` → Distribution Check görsel grafik
- `/rule-library` → Rule Library (pattern listesi, ekle/sil)
- `/wizard` → Profil + kural ekleme sihirbazı
- `/runs` → Run geçmişi

---

## Yeni Assert Tipi Ekleme Adımları
1. `dq/engine.py` → fonksiyon yaz (CheckEngine sınıfından önce)
2. `dq/config.py` → import satırına ekle (~satır 40)
3. `dq/config.py` → `_ASSERTION_MAP` dict'ine lambda ekle (~satır 46-60)
4. `tests/test_xxx.py` → TestXxx sınıfı + `test_in_assertion_map` testi yaz

---

## Kritik Notlar

- `from __future__ import annotations` + Pydantic çakışması:
  api.py ve ui.py'de fonksiyon parametrelerine tip hint yazarken dikkat.
  api.py'de `Request` import'u zorunlu: `from fastapi import APIRouter, HTTPException, Request`
- `sed` güvenilmez — Python string replace scripti kullan (`/tmp/` altında)
- heredoc: `cat > /tmp/fix.py << 'EOF'` sonra `python3 /tmp/fix.py`
- pymysql venv'de yok — testlerde DB import etme, MagicMock kullan
- Docker build: `docker compose build dq-web && docker compose up -d dq-web`
- DB migration: `docker exec -i dq-db mysql -u root -proot dq -e "..."`

---

## Güvenlik Katmanı
- `secrets/.env.secrets` → password'lar + SMTP/alert config (chmod 600, git ignore)
- `secrets/.env.secrets.gpg` → şifreli kopya (git'te ✅)
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
**176 passed, 3 skipped ✅**

---

## Git Son Commitler

550c57c feat: Ana sayfaya Analiz Sayfaları kartı eklendi
6fad0df feat: GÖREV 24 — Distribution Check UI
17421a6 feat: GÖREV 23 — Cross-Table UI
f407918 feat: GÖREV 22 — Anomali Dashboard UI
c6e213e feat: GÖREV 21 — Rule Library UI
26c6602 feat: GÖREV 19 — trend_check assertion
9919134 feat: GÖREV 20 — AlertManager.send_summary_report()


---

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md + TASKS.md zip'le, yükle
2. Backlog: Docker Secrets/Vault veya Airflow secure store
3. Öneri: pytest ile test sayısını kontrol et
