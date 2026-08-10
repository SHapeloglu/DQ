# DQ Mimari Haritası

## 1. Çekirdek Motor (dq/)
- engine.py: CheckEngine + assert tipleri:
  Mevcut: not_empty, regex_match, accepted_values, freshness_hours, row_count_between,
          referential_integrity, equals, between, greater_than, less_than,
          completeness_ratio, statistical_anomaly, schema_drift, schema_check,
          duplicate_row, custom_sql, volume_anomaly,
          zscore_anomaly, cross_table_check, distribution_check, trend_check
- YENİ ASSERT TİPİ EKLEME ADIMLARI:
  1. dq/engine.py → fonksiyon yaz (en sona, CheckEngine sınıfından önce)
  2. dq/config.py → import satırına ekle (~satır 40)
  3. dq/config.py → _ASSERTION_MAP dict'ine lambda ekle (~satır 46-58)
  4. tests/test_engine.py → TestXxx sınıfı + test_in_assertion_map testi yaz
- _ASSERTION_MAP: dq/config.py satır 46 — assert_type string → fabrika fonksiyonu
- distribution_check(expected_mean, expected_std, tolerance_pct=10.0):
  SQL: SELECT AVG(kolon), STDDEV(kolon) → 'avg,std' formatında string döner
  tolerance_pct: izin verilen sapma yüzdesi
- zscore_anomaly: MetricStore geçmişinden Z-score hesaplar
- cross_table_check: iki kaynak arası skaler değer karşılaştırma
- trend_check: pencere ortalaması karşılaştırma, yön kontrolü
- connectors.py: BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
  NOT: BaseConnector abstract metodu close() — disconnect() değil
  NOT: SqlAlchemyConnector.test_connection() → dict içinde dialect key zorunlu
- config.py: SodaConfig + _resolve_env_vars() + _ASSERTION_MAP
- scoring.py: get_health_score(), get_score_trend(), get_all_scores()
- metrics.py: MetricStore — SQLite (dev) + Postgres (prod)
  DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
  Şema: dwh_health_log.dq_metrics
- reporter_v2.py: full_report() + MetricStore entegrasyonu
- airflow.py: DQOperator — check'leri Airflow üzerinden çalıştırır
  NOT: Web UI'dan check çalıştırma endpoint'i YOK — sadece Airflow/CLI

## 2. Web Backend (kök dizin)
- main.py (~60 satır): Router include'ları
- database.py: MySQL bağlantısı + tablo şeması init_db()
- profiler.py: PII tagging (24 pattern) + enum/regex/empty önerileri + cache + SQL optimize
- cache_layer.py: TTLCache 5 dk — profile_cache singleton
- extensions.py: AlertManager (email/slack/webhook) + load_alert_manager() +
  checks_to_toml() + send_summary_report()

## 3. Routers (routers/)
- sources.py: /sources CRUD
- checks.py: /checks CRUD + /api/suggestions/reject
- api.py: /api/runs, /api/results, /api/health-score/{id}, /api/health-score/{id}/trend,
          /api/glossary/{source_id}, /api/pii-report, /api/pii-report/{source_id},
          /api/alert-settings, /api/columns/{source_id}, /api/profile/{source_id},
          /api/rule-library, /api/anomaly-results, /api/cross-table-results,
          /api/distribution-results, /odata
  NOT: from fastapi import APIRouter, HTTPException, Request — Request import zorunlu
- ui.py: /wizard, /import, /runs, /health, /rule-library,
         /anomaly, /cross-table, /distribution, /

## 4. UI Sayfaları (templates/)
- index.html → Ana sayfa + Analiz Sayfaları kartı
- anomaly.html → Anomali Dashboard (zscore/volume/trend/distribution)
- cross_table.html → Cross-Table Kontroller
- distribution.html → Distribution Check (beklenen vs gerçek avg bar chart)
- rule_library.html → Rule Library
- health.html → Sağlık Skoru Dashboard
- wizard.html → Profil + kural ekleme sihirbazı

## 5. DB Şeması (MySQL — dq-db:3308)
- sources: id, name, type, config, alert_enabled
- checks: id, source_id, name, query, assert_type, assert_value, active, test_flag,
          column_name, tags, library_pattern_id
- runs: id, source_id, dag_id, task_id, total, passed, failed, status, run_at
- run_results: id, run_id, check_name, passed, value_actual, expected, message
- column_profiles: source_id, column_name, col_type, row_count, null_pct, distinct_count,
                   min_val, max_val, avg_val, is_pii, pii_type, business_name,
                   description, owner, tags
- alert_settings: id(=1 singleton), slack_webhook, webhook_url, email_to,
                  smtp_host, smtp_port, smtp_user, smtp_pass
- rule_library: id, column_name_pattern, rule_type, times_used, times_accepted, times_rejected

## 6. Airflow DAG'ları (dags/)
- dq_mysql_dag.py, dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- dq_scheduled_profiling_dag.py → scheduled_profiling.toml

## 7. Güvenlik Katmanı
- secrets/.env.secrets (chmod 600, git ignore)
- secrets/.env.secrets.gpg → şifreli kopya (git'te)
- scripts/decrypt_secrets.sh → deploy öncesi çalıştır
- GPG key: dq@localhost (RSA 4096)

## 8. Kritik Nodlar
- build_connector() — betweenness 0.437, tüm connector factory buradan geçer
- CheckEngine — 43 edge, en geniş etki alanı
- get_conn() — 29 edge, bağlantı dar boğazı
- api_post_run — run kayıt + alert tetikleme merkezi (routers/api.py ~L98)
- load_alert_manager() — alert_settings tablosundan yükler, None dönebilir

## 9. Wizard Veri Akışı
1. Kaynak seç → /api/columns/{source_id} → kolon listesi
2. Profil çalıştır → /api/profile/{source_id} POST → istatistik + PII banner + glossary
3. Kural ekle → /checks POST (assert_type + query + assert_value DB'ye kaydedilir)
4. Run tetikle → Airflow DQOperator → _ASSERTION_MAP'ten assertion yükle → CheckEngine.run()
5. Sonuç → /api/runs POST → run_results tablosu → alert

## 10. Check Çalıştırma Akışı (Airflow)
dq/airflow.py DQOperator._run_checks()
  → dq/config.py SodaConfig.build_checks()
    → _parse_check() → _ASSERTION_MAP[assert_type](assert_value) → assertion fonksiyonu
  → dq/engine.py CheckEngine.run()
    → connector.execute(query) → assertion(value) → CheckResult

## 11. Puanlama (Rakip Karşılaştırma)
Mevcut: ~8.2/10
Güçlü: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10)
Zayıf: ölçeklenebilirlik (4/10)

## 12. Teknik Tuzaklar
- from __future__ import annotations: api.py + ui.py'de var — Pydantic ForwardRef hatası
  Çözüm: api.py'de Request'i explicit import et, Optional[int] yerine source_id=None yaz
- sed güvenilmez: /tmp/fix.py script paterni kullan
- heredoc içinde triple-quote kullanma
- curl 000: uygulama henüz ayağa kalkmamış, sleep 5 bekle
