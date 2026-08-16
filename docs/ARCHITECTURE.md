# DQ Mimari Haritası

## 1. Çekirdek Motor (dq/)
- engine.py: CheckEngine + 19 assert tipi
- anomaly.py: AnomalyDetector (z-score + EWMA + Holt-Winters + trend yönü)
- config.py: SodaConfig + _ASSERTION_MAP (19 entry)
- metrics.py: MetricStore (SQLite dev + Postgres prod + read replica)
- connectors.py: BaseConnector + 8 veritabanı tipi
- scoring.py: get_health_score(), get_score_trend()
- reporter_v2.py: full_report()
- airflow.py: DQOperator

## 2. Web Backend
- main.py: FastAPI init
- database.py: MySQL bağlantısı
- profiler.py: PII tagging (24 pattern)
- cache_layer.py: TTLCache (5 dk)
- extensions.py: AlertManager
- secrets_loader.py: get_secret()

## 3. Routers
- sources.py: /sources CRUD
- checks.py: /checks CRUD
- api.py: /api/*, /odata
- ui.py: Web sayfaları

## 4. DB Şeması
- sources, checks, runs, run_results
- column_profiles (PII, business metadata)
- alert_settings (singleton id=1)
- rule_library (pattern → rule → times_used)
- MetricStore: dwh_health_log.dq_metrics (Postgres)

## 5. Airflow DAG'ları
- dq_mysql_dag.py, dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- dq_scheduled_profiling_dag.py

## 6. Güvenlik
- secrets/.env.secrets (chmod 600, git ignore)
- secrets_loader.py: /run/secrets/ → env → default
- GPG key: dq@localhost (RSA 4096)

## 7. Kritik Nodlar (Grafik Analizi)
- build_connector(): betweenness 0.437
- CheckEngine: 43 edge
- get_conn(): 29 edge (bağlantı dar boğazı)
- api_post_run: run kayıt + alert tetikleme

## 8. Anomali Tespiti Zinciri
Wizard → Airflow DQOperator → CheckEngine.run() → AnomalyDetector.detect_all()
→ _detect_trend() [trend yönü] → run_results → /anomaly dashboard

## 9. Puanlama (Rekabet)
Genel: 6.7/10 → ~8.4/10
Güçlü: PII/KVKK (9/10), maliyet (10/10), anomali trend (8.5/10), wizard UX (8.5/10)
Zayıf: ölçeklenebilirlik (6/10)
