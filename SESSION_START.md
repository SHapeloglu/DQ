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
- `dq/anomaly.py` → AnomalyDetector (z-score + EWMA + Holt-Winters otomatik seçim) ✅
- `dq/connectors.py` → BaseConnector + 8 veritabanı tipi
- `dq/metrics.py` → MetricStore (SQLite dev + Postgres prod)
- `dq/scoring.py` → get_health_score(), get_score_trend(), get_all_scores()
- `dq/reporter_v2.py` → full_report() + MetricStore entegrasyonu
- `dq/airflow.py` → DQOperator — CheckEngine.run() → AnomalyDetector.detect_all()
- `secrets_loader.py` → get_secret(key, default) — /run/secrets/ → env → default
- `main.py` → FastAPI app init + router include'ları
- `database.py` → MySQL init_db() + _DBPool (size=5, thread-safe)
- `cache_layer.py` → TTLCache + profile_cache singleton (5 dk TTL)
- `profiler.py` → cache + PII tagging (24 pattern) + enum/regex/empty önerileri
- `extensions.py` → AlertManager (email/slack/webhook) + send_summary_report()

---

## Routers

- `routers/sources.py` → /sources CRUD
- `routers/checks.py` → /checks CRUD + /api/suggestions/reject
- `routers/api.py` → /api/* + /odata + alerting + health-score + glossary + pii-report + alert-settings + rule-library + anomaly-results + cross-table-results + distribution-results
- `routers/ui.py` → /wizard, /import, /runs, /health, /rule-library, /anomaly, /cross-table, /distribution, /

---

## UI Sayfaları

- `/` → Ana sayfa (kaynak özeti + son run'lar)
- `/health` → Sağlık Skoru Dashboard
- `/anomaly` → Anomali Dashboard (Yöntem/Skor sütunları + **yöntem filtresi**)
- `/cross-table` → Cross-Table Kontroller
- `/distribution` → Distribution Check görsel grafik
- `/rule-library` → Rule Library
- `/wizard` → Profil + kural ekleme sihirbazı
  Chip kategorileri: TEMEL, SAYISAL, FORMAT/METİN, TARİH/ZAMAN, İLİŞKİ/REFERANS, ANOMALİ/TREND
- `/runs` → Run geçmişi

---

## Anomali Tespiti Zinciri (uçtan uca)
Wizard → kural DB'ye yazılır → Airflow DQOperator → CheckEngine.run()
→ AnomalyDetector.detect_all() (z-score / EWMA / Holt-Winters) → Airflow log + uyarı
→ run_results tablosu → /anomaly dashboard

---

## Kritik Notlar

- `row_condition` assert tipi: Dataplex gap kapandı
- Anomali yöntem filtresi: zscore / ewma / holt_winters
- run_detail.html: [ewma] badge desteği eklendi
- `from __future__ import annotations` + Pydantic çakışması:
  api.py ve ui.py'de fonksiyon parametrelerine tip hint yazarken dikkat.
  api.py'de `Request` import zorunlu.
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
- requirements.txt: statsmodels==0.14.2 + numpy==1.26.4

---

## DB Tabloları
- `sources` (+ alert_enabled)
- `checks`, `runs`, `run_results`
- `column_profiles` (+ business_name, description, owner, tags, is_pii, pii_type)
- `alert_settings` (id=1 singleton)
- `rule_library` (column_name_pattern, rule_type, times_used, times_accepted, times_rejected)

---

## Test Durumu
**196 passed, 3 skipped ✅**

---

## Git Son Commitler (bu oturum)

1734b0a feat: GOREV 43 — row_condition assert tipi (Dataplex gap)
02693f9 feat: GOREV 42 — anomali dashboard yontem filtresi (zscore/ewma/holt_winters)
76829c6 feat: GOREV 41 — run_detail ewma badge destegi eklendi

---

## Rekabet Konumu (güncel)
Genel: 6.7/10 → backlog tamamlanırsa ~8.3/10
Güçlü: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), wizard UX (8/10)
Anomali tespiti: 7/10 (zscore + EWMA + Holt-Winters)
Ölçeklenebilirlik: 6/10 (ThreadPoolExecutor, max 4 paralel check)
Rakipler: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality

---

## Sonraki Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md + TASKS.md zip'le, yükle
2. GÖREV 44/45/47 backlog'dan seçin
