# DQ — Session Başlangıç Dosyası

Proje: DQ (Data Quality Platform)
Konum: `/opt/dq/dq_docker` (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL 8.0 + Airflow + Docker Compose

---

## Mimari (Özet)

- `dq/engine.py` → CheckEngine + 19 assert tipi ✅
- `dq/config.py` → SodaConfig + _ASSERTION_MAP (19 entry) ✅
- `dq/anomaly.py` → AnomalyDetector (z-score + EWMA + Holt-Winters) + **trend yönü** ✅
- `dq/metrics.py` → MetricStore (SQLite dev + Postgres prod) + **read replica** ✅
- `dq/connectors.py` → BaseConnector + 8 veritabanı tipi
- `dq/scoring.py` → get_health_score(), get_score_trend(), get_all_scores()
- `dq/reporter_v2.py` → full_report() + MetricStore entegrasyonu
- `dq/airflow.py` → DQOperator — CheckEngine.run()
- Diğer: secrets_loader, main.py, database.py, cache_layer.py, profiler.py, extensions.py

---

## Routers

- `routers/sources.py` → /sources CRUD
- `routers/checks.py` → /checks CRUD
- `routers/api.py` → /api/* + /odata + alerting + health-score + anomaly-results + profile-export
- `routers/ui.py` → /wizard, /import, /runs, /health, /rule-library, /anomaly, /cross-table, /distribution, /

---

## Test Durumu
**196 passed, 3 skipped ✅**

---

## Git Son Commitler (bu oturum)

2cd83ff feat: GOREV 45 — Read replica desteği (MetricStore)
01a5a97 feat: GOREV 44 — Anomali trend yönü analizi (up/stable/down)

---

## Rekabet Konumu (güncel)
Genel: 6.7/10 → **~8.4/10** (GÖREV 44-48 + 45 tamamlandı)
Güçlü: PII/KVKK (9/10), maliyet (10/10), anomali trend (8.5/10), wizard UX (8.5/10)
Ölçeklenebilirlik: 6/10 (ThreadPoolExecutor, max 4 paralel check)

---

## Sonraki Session'da Yap
1. GÖREV 47: Custom assertion script upload (kullanıcı Python fonksiyonu yükleme)
