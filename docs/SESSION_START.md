# DQ — Session Başlangıç Dosyası

Proje: DQ (Data Quality Platform)
Konum: `/opt/dq/dq_docker` (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL 8.0 + Airflow + Docker Compose

---

## Mimari (Özet)

- `dq/engine.py` → CheckEngine + 19 assert tipi ✅
  Tüm assert tipleri: not_empty, regex_match, accepted_values, freshness_hours,
  row_count_between, referential_integrity, equals, between, greater_than, less_than,
  completeness_ratio, statistical_anomaly, schema_drift, schema_check,
  duplicate_row, custom_sql, volume_anomaly, zscore_anomaly, row_condition
- `dq/config.py` → SodaConfig + _resolve_env_vars() + _ASSERTION_MAP (19 entry) + _get_metric_store() ✅
- `dq/anomaly.py` → AnomalyDetector (z-score + EWMA + Holt-Winters otomatik seçim) + **_detect_trend() trend yönü** ✅
- `dq/metrics.py` → MetricStore (SQLite dev + Postgres prod) + **read_replica_dsn read-write split** ✅
- `dq/connectors.py` → BaseConnector + 8 veritabanı tipi
- `dq/scoring.py` → get_health_score(), get_score_trend(), get_all_scores()
- `dq/reporter_v2.py` → full_report() + MetricStore entegrasyonu
- `dq/airflow.py` → DQOperator — check'leri Airflow üzerinden çalıştırır
- `secrets_loader.py` → get_secret(key, default) — /run/secrets/ → env → default
- `main.py` → FastAPI app init + router include'ları
- `database.py` → MySQL bağlantısı + tablo şeması init_db()
- `cache_layer.py` → TTLCache 5 dk — profile_cache singleton
- `profiler.py` → PII tagging (24 pattern) + enum/regex/empty önerileri
- `extensions.py` → AlertManager (email/slack/webhook) + send_summary_report()

---

## Routers

- `routers/sources.py` → /sources CRUD
- `routers/checks.py` → /checks CRUD + /api/suggestions/reject
- `routers/api.py` → /api/runs, /api/results, /api/health-score, /api/glossary, /api/pii-report, /api/columns, /api/profile, /api/profile-export, /api/alert-settings, /api/anomaly-results, /api/rule-library, /api/cross-table-results, /api/distribution-results, /odata
- `routers/ui.py` → /wizard, /import, /runs, /health, /rule-library, /anomaly, /cross-table, /distribution, /

---

## UI Sayfaları

- `/` → Ana sayfa (kaynak özeti + son run'lar)
- `/health` → Sağlık Skoru Dashboard
- `/anomaly` → Anomali Dashboard (Yöntem/Skor/Trend sütunları + **trend badge ↑/→/↓**)
- `/cross-table` → Cross-Table Kontroller
- `/distribution` → Distribution Check görsel grafik
- `/rule-library` → Rule Library
- `/wizard` → Profil + kural ekleme sihirbazı
  Chip kategorileri: TEMEL, SAYISAL, FORMAT/METİN, TARİH/ZAMAN, İLİŞKİ/REFERANS, ANOMALİ/TREND
- `/runs` → Run geçmişi

---

## Anomali Tespiti Zinciri (uçtan uca)
Wizard → kural DB'ye yazılır → Airflow DQOperator → CheckEngine.run()
→ AnomalyDetector.detect_all() (z-score / EWMA / Holt-Winters + **trend yönü**) → Airflow log + uyarı
→ run_results tablosu + MetricStore kaydı → /anomaly dashboard

---

## Kritik Notlar

- `row_condition` assert tipi: Dataplex gap kapandı ✅
- **Anomali trend yönü:** _detect_trend() → up (artan), stable (sabit), down (azalan) ✅
- **Trend badge dashboard'da:** ↑ (yeşil), → (gri), ↓ (kırmızı)
- **Read replica desteği:** MetricStore(read_replica_dsn=...) → read ops replicadan, write ops primary'ye ✅
- Anomali yöntem filtresi: zscore / ewma / holt_winters
- run_detail.html: [ewma] badge desteği
- `from __future__ import annotations` + Pydantic çakışması: api.py/ui.py'de `Request` import zorunlu
- `sed` güvenilmez — Python string replace scripti kullan (`/tmp/` altında)
- heredoc: `python3 - << 'PYEOF'` tercih edilen
- pymysql venv'de yok — testlerde DB import etme, MagicMock kullan
- Docker build: `docker compose build dq-web && docker compose up -d dq-web`
- DB migration: `docker exec -i dq-db mysql -u root -proot dq -e "..."`
- Connection pool: get_conn() havuzdan alır, release_conn(conn) havuza iade eder
- secrets_loader: TOML'da `password = "secret:DB_PASSWORD"` prefix kullan

---

## Güvenlik Katmanı
- `secrets/.env.secrets` → password'lar + SMTP/alert config (chmod 600, git ignore)
- `secrets/files/` → Docker secrets dosya mount (chmod 600, git ignore)
- `secrets/.env.secrets.gpg` → şifreli kopya (git'te)
- `secrets_loader.py` → get_secret(key, default): /run/secrets/ → env → default
- GPG key: dq@localhost (RSA 4096)

---

## Docker
- `dq-web` → 0.0.0.0:8002 (uvicorn)
- `dq-db` → 0.0.0.0:3308 (mysql:8.0)
- requirements.txt: statsmodels==0.14.2 + numpy==1.26.4 + psycopg2==2.9.9

---

## DB Tabloları
- `sources` (+ alert_enabled)
- `checks`, `runs`, `run_results`
- `column_profiles` (+ business_name, description, owner, tags, is_pii, pii_type)
- `alert_settings` (id=1 singleton)
- `rule_library` (column_name_pattern, rule_type, times_used, times_accepted, times_rejected)
- MetricStore: PostgreSQL dwh_health_log.dq_metrics (name, value, run_at)

---

## Test Durumu
**196 passed, 3 skipped ✅**

---

## Git Son Commitler (bu oturum)

99872b4 docs: GOREV 44-45 sonrası güncellendi
2cd83ff feat: GOREV 45 — Read replica desteği (MetricStore)
01a5a97 feat: GOREV 44 — Anomali trend yönü analizi (up/stable/down)

---

## Rekabet Konumu (güncel)
Genel: 6.7/10 → **~8.4/10**
Güçlü: PII/KVKK (9/10), maliyet (10/10), anomali trend (8.5/10), wizard UX (8.5/10), sağlık skoru (8/10)
Ölçeklenebilirlik: 6/10 (ThreadPoolExecutor, max 4 paralel check)
Rakipler: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality

---

## Sonraki Session'da Yap
1. GÖREV 47: Custom assertion script upload (L)
2. docs/ sync'le
