# DQ Mimari Haritası

## 1. Çekirdek Motor (dq/)
- engine.py: CheckEngine + assert tipleri (not_empty, regex_match, accepted_values, freshness_hours, row_count_between, referential_integrity)
- connectors.py: MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- config.py: SodaConfig + _resolve_env_vars()
- scoring.py: get_health_score(), get_score_trend(), get_all_scores()
- metrics.py: MetricStore — SQLite (dev) + Postgres (prod)
- reporter_v2.py: full_report() + MetricStore

## 2. Web Backend (kök dizin)
- main.py (~60 satır): Router include'ları
- database.py: MySQL bağlantısı + tablo şeması
- profiler.py: PII tagging (24 pattern) + öneriler + cache
- cache_layer.py: TTLCache 5 dk
- extensions.py: AlertManager + load_alert_manager() + checks_to_toml()

## 3. Routers (routers/)
- sources.py: /sources CRUD
- checks.py: /checks CRUD + suggestions
- api.py: /api/runs, /api/results, /api/health-score, /api/glossary, /api/pii-report, /api/alert-settings, /odata
- ui.py: /wizard, /import, /runs, /health, /

## 4. DB Şeması (MySQL)
- sources: id, name, type, config, alert_enabled
- checks: id, source_id, name, query, assert_type, assert_value, active, test_flag
- runs: id, source_id, dag_id, task_id, total, passed, failed, status, run_at
- run_results: id, run_id, check_name, passed, value_actual, expected, message
- column_profiles: ..., is_pii, pii_type, business_name, description, owner, tags
- alert_settings: id(=1), slack_webhook, webhook_url, email_to, smtp_*
- rule_library: kural şablonları

## 5. Kritik Nodlar
- build_connector() — betweenness 0.437, tüm connector factory
- CheckEngine — 43 edge, en geniş etki alanı
- get_conn() — 29 edge, bağlantı dar boğaz
- api_post_run — run kayıt + alert tetikleme merkezi (routers/api.py ~L98)
- load_alert_manager() — alert_settings tablosundan yükler, None dönebilir
