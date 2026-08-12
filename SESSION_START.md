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
- `dq/config.py` → SodaConfig + _resolve_env_vars() + _ASSERTION_MAP + _get_metric_store() ✅
  NOT: zscore_anomaly artık store=None değil, gerçek MetricStore kullanıyor
  NOT: _get_metric_store() → METRICS_PG_DSN varsa Postgres, yoksa SQLite fallback
- `dq/anomaly.py` → AnomalyDetector (z-score + Holt-Winters otomatik seçim) ✅
  n<8 → z-score, n>=8 → Holt-Winters ExponentialSmoothing (statsmodels)
  AnomalyResult: metric_name, current, is_anomaly, score, method, lower_bound, upper_bound
- `dq/connectors.py` → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- `dq/metrics.py` → MetricStore (SQLite dev + Postgres prod) + get_recent_values(name, n) ✅
- `dq/scoring.py` → get_health_score(), get_score_trend(), get_all_scores() ✅
- `dq/reporter_v2.py` → full_report() + MetricStore entegrasyonu ✅
- `dq/airflow.py` → DQOperator — CheckEngine.run() sonrası AnomalyDetector.detect_all() ✅
- `secrets_loader.py` → get_secret(key, default) — /run/secrets/ → env → default ✅
- `main.py` → FastAPI app init + router include'ları ✅
- `database.py` → MySQL init_db() + _DBPool (size=5, thread-safe) + get_conn/release_conn ✅
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
- `/anomaly` → Anomali Dashboard (Yöntem/Skor sütunları: Holt-Winters/zscore badge)
- `/cross-table` → Cross-Table Kontroller
- `/distribution` → Distribution Check görsel grafik
- `/rule-library` → Rule Library
- `/wizard` → Profil + kural ekleme sihirbazı
  Chip kategorileri: TEMEL, SAYISAL, FORMAT/METİN, TARİH/ZAMAN, İLİŞKİ/REFERANS, ANOMALİ/TREND
  ANOMALİ/TREND: Hacim anomalisi (volume_anomaly) + Geçmişe dayalı anomali (zscore_anomaly)
- `/runs` → Run geçmişi

---

## Anomali Tespiti Zinciri (uçtan uca)
Wizard → kural DB'ye yazılır → Airflow DQOperator → CheckEngine.run()
→ AnomalyDetector.detect_all() → z-score veya Holt-Winters → Airflow log + uyarı
→ run_results tablosu → /anomaly dashboard

---

## Kritik Notlar

- `from __future__ import annotations` + Pydantic çakışması:
  api.py ve ui.py'de fonksiyon parametrelerine tip hint yazarken dikkat.
  api.py'de `Request` import zorunlu: `from fastapi import APIRouter, HTTPException, Request`
- `sed` güvenilmez — Python string replace scripti kullan (`/tmp/` altında)
- heredoc: `cat > /tmp/fix.py << 'EOF'` sonra `python3 /tmp/fix.py`
  VEYA: `python3 - << 'PYEOF'` ... `PYEOF` (tercih edilen)
- pymysql venv'de yok — testlerde DB import etme, MagicMock kullan
- Docker build: `docker compose build dq-web && docker compose up -d dq-web`
- DB migration: `docker exec -i dq-db mysql -u root -proot dq -e "..."`
- Connection pool: get_conn() havuzdan alır, release_conn(conn) havuza iade eder
- secrets_loader: TOML'da `password = "secret:DB_PASSWORD"` prefix kullan
- cross_table_check: engine.py'de TEK tanım var (3'ten 1'e indirildi — refactor)

---

## Güvenlik Katmanı
- `secrets/.env.secrets` → password'lar + SMTP/alert config (chmod 600, git ignore)
- `secrets/files/` → Docker secrets dosya mount (chmod 600, git ignore) ✅
- `secrets/.env.secrets.gpg` → şifreli kopya (git'te ✅)
- `secrets_loader.py` → get_secret(key, default): /run/secrets/ → env → default
- GPG key: dq@localhost (RSA 4096)
- docker-compose.yml → dq-web servisi secrets: bloku ile /run/secrets/ mount ✅

---

## Docker
- `dq-web` → 0.0.0.0:8002 (uvicorn)
- `dq-db` → 0.0.0.0:3308 (mysql:8.0)
- requirements.txt: statsmodels==0.14.2 + numpy==1.26.4 eklendi ✅

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

## Git Son Commitler (bu oturum)

df622bc feat: GOREV 33 — anomaly dashboard Yontem/Skor sutunlari
f594bf3 refactor: cross_table_check tekrarlı tanımları temizlendi (3→1)
e9c343a feat: GOREV 32 — AnomalyDetector Airflow DQOperator entegrasyonu
3576733 feat: GOREV 31 — wizard'a anomali panelleri
67fd92f feat: GOREV 30 — zscore_anomaly MetricStore entegrasyonu + statsmodels
8987d80 feat: GOREV 28 — Docker secrets dosya mount entegrasyonu
27afb10 feat: GOREV 29 — profile_column tek sorgu optimizasyonu

---

## Rekabet Konumu (güncel)
Genel: 6.7/10 → backlog tamamlanırsa ~7.8/10
Güçlü: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), wizard UX (8/10)
Anomali tespiti: 2/10 → 6/10 (Holt-Winters entegrasyonu sonrası)
Zayıf: Ölçeklenebilirlik (4/10)
Rakipler: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality

---

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md + TASKS.md zip'le, yükle
2. Sıradaki görevler:
   - anomaly.html → AnomalyResult verisi run_results'a yazma (Airflow log'dan DB'ye)
   - ML anomali tespiti iyileştirme (GÖREV 34)
   - Dökümanlar: ARCHITECTURE.md rekabet bölümü güncelle
   - Oturum yönetimi protokolünü diğer projelere uygula
