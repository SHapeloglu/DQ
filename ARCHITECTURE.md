# DQ Mimari Haritası

## 1. Çekirdek Motor (dq/)
- engine.py: CheckEngine + assert tipleri:
  Mevcut: not_empty, regex_match, accepted_values, freshness_hours, row_count_between,
          referential_integrity, equals, between, greater_than, less_than,
          completeness_ratio, statistical_anomaly, schema_drift, schema_check,
          duplicate_row, custom_sql, volume_anomaly, zscore_anomaly,
          cross_table_check, distribution_check, trend_check
  NOT: cross_table_check — tek tanım (3 tekrarlı tanım temizlendi, refactor commit f594bf3)
- YENİ ASSERT TİPİ EKLEME ADIMLARI:
  1. dq/engine.py → fonksiyon yaz (en sona, CheckEngine sınıfından önce)
  2. dq/config.py → import satırına ekle (~satır 40)
  3. dq/config.py → _ASSERTION_MAP dict'ine lambda ekle (~satır 50-65)
  4. tests/test_engine.py → TestXxx sınıfı + test_in_assertion_map testi yaz
- _ASSERTION_MAP: dq/config.py — assert_type string → fabrika fonksiyonu
- _get_metric_store(): dq/config.py — METRICS_PG_DSN varsa Postgres, yoksa SQLite
- anomaly.py: AnomalyDetector — MetricStore geçmişine dayalı anomali tespiti
  Yöntem seçimi: n<8 → z-score, n>=8 → Holt-Winters ExponentialSmoothing (statsmodels)
  AnomalyResult: metric_name, current, is_anomaly, score, method, lower_bound, upper_bound, message
  detect(metric_name, current_value) → AnomalyResult
  detect_all(results) → list[AnomalyResult] (önce MetricStore'a kaydeder)
- connectors.py: BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
  NOT: BaseConnector abstract metodu close() — disconnect() değil
  NOT: SqlAlchemyConnector.test_connection() → dict içinde dialect key zorunlu
- config.py: SodaConfig + _resolve_env_vars() + _ASSERTION_MAP + _get_metric_store()
- scoring.py: get_health_score(), get_score_trend(), get_all_scores()
- metrics.py: MetricStore — SQLite (dev) + Postgres (prod)
  DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
  Şema: dwh_health_log.dq_metrics
  get_recent_values(name, n) → list[float]
- reporter_v2.py: full_report() + MetricStore entegrasyonu
- airflow.py: DQOperator — check'leri Airflow üzerinden çalıştırır
  _run_checks() → engine.run() → AnomalyDetector.detect_all() → Airflow log
  NOT: AnomalyResult'lar şu an sadece log'a yazılıyor (GÖREV 34: DB'ye yazma bekliyor)

## 2. Web Backend (kök dizin)
- main.py (~60 satır): Router include'ları
- database.py: MySQL bağlantısı + _DBPool (size=5, thread-safe) + get_conn/release_conn
- profiler.py: PII tagging (24 pattern) + enum/regex/empty önerileri + cache + SQL optimize
  OPTİMİZASYON: temel istatistik + distinct tek sorguda birleştirildi (GÖREV 29)
- cache_layer.py: TTLCache 5 dk — profile_cache singleton
- extensions.py: AlertManager (email/slack/webhook) + load_alert_manager() + checks_to_toml()
- secrets_loader.py: get_secret(key, default) — /run/secrets/ → env → default

## 3. Routers (routers/)
- sources.py: /sources CRUD
- checks.py: /checks CRUD + /api/suggestions/reject
  NOT: check_create → assert_type + query + assert_value DB'ye kaydedilir, çalıştırılmaz
- api.py: /api/runs, /api/results, /api/health-score/{id}, /api/health-score/{id}/trend,
          /api/glossary/{source_id}, /api/pii-report, /api/pii-report/{source_id},
          /api/alert-settings, /api/columns/{source_id}, /api/profile/{source_id},
          /api/anomaly-results, /api/cross-table-results, /api/distribution-results, /odata
- ui.py: /wizard, /import, /runs, /health, /rule-library, /anomaly, /cross-table, /distribution, /

## 4. DB Şeması (MySQL — dq-db:3308)
- sources: id, name, type, config, alert_enabled
- checks: id, source_id, name, query, assert_type, assert_value, active, test_flag, column_name, tags, library_pattern_id
  NOT: assert_type değerleri → engine.py fonksiyon adlarıyla eşleşir (_ASSERTION_MAP anahtarları)
- runs: id, source_id, dag_id, task_id, total, passed, failed, status, run_at
- run_results: id, run_id, check_name, passed, value_actual, expected, message
- column_profiles: source_id, column_name, col_type, row_count, null_pct, distinct_count,
                   min_val, max_val, avg_val, is_pii, pii_type, business_name, description, owner, tags
- alert_settings: id(=1 singleton), slack_webhook, webhook_url, email_to, smtp_host, smtp_port, smtp_user, smtp_pass
- rule_library: id, column_name_pattern, rule_type, times_used, times_accepted, times_rejected

## 5. Airflow DAG'ları (dags/)
- dq_mysql_dag.py, dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- dq_scheduled_profiling_dag.py → scheduled_profiling.toml

## 6. Güvenlik Katmanı
- secrets/.env.secrets (chmod 600, git ignore) → password + SMTP + alert config
- secrets/files/ (chmod 600, git ignore) → Docker secrets dosya mount
  DB_PASSWORD, METRICS_PG_DSN, METRICS_PG_PASSWORD, ALERT_SMTP_PASS, ALERT_SLACK_WEBHOOK
- secrets/.env.secrets.gpg → şifreli kopya (git'te)
- scripts/decrypt_secrets.sh → deploy öncesi çalıştır
- GPG key: dq@localhost (RSA 4096)
- docker-compose.yml → secrets: bloku + dq-web'e mount ✅

## 7. Kritik Nodlar (Grafik Analizi)
- build_connector()  — betweenness 0.437, tüm connector factory buradan geçer
- CheckEngine        — 43 edge, en geniş etki alanı
- get_conn()         — 29 edge, bağlantı dar boğazı
- api_post_run       — run kayıt + alert tetikleme merkezi (routers/api.py ~L98)
- load_alert_manager() — alert_settings tablosundan yükler, None dönebilir
- AnomalyDetector    — airflow.py'de _run_checks() sonrası çağrılır

## 8. Wizard Veri Akışı
1. Kaynak seç → /api/columns/{source_id} → kolon listesi
2. Profil çalıştır → /api/profile/{source_id} POST → istatistik + PII banner + glossary
3. Kural ekle → /checks POST (assert_type + query + assert_value DB'ye kaydedilir)
   Chip kategorileri: TEMEL, SAYISAL, FORMAT/METİN, TARİH/ZAMAN, İLİŞKİ/REFERANS, ANOMALİ/TREND
4. Run tetikle → Airflow DQOperator → _ASSERTION_MAP'ten assertion yükle → CheckEngine.run()
5. AnomalyDetector.detect_all() → z-score veya Holt-Winters
6. Sonuç → /api/runs POST → run_results tablosu → alert

## 9. Check Çalıştırma Akışı (Airflow)
dq/airflow.py DQOperator._run_checks()
  → dq/config.py SodaConfig.build_checks()
    → _parse_check() → _ASSERTION_MAP[assert_type](assert_value) → assertion fonksiyonu
  → dq/engine.py CheckEngine.run()
    → connector.execute(query) → assertion(value) → CheckResult
  → dq/anomaly.py AnomalyDetector.detect_all(results)
    → MetricStore.record_results() → detect() → z-score | Holt-Winters → AnomalyResult
    → Airflow log (GÖREV 34: run_results'a yazma bekliyor)

## 10. Puanlama (Rakip Karşılaştırma)
Mevcut: ~7.5/10 | Backlog tamamlanırsa: ~8.5/10
Güçlü: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), wizard UX (8/10)
Anomali: 2/10 → 6/10 (Holt-Winters + zscore MetricStore entegrasyonu sonrası)
Zayıf: Ölçeklenebilirlik (4/10)
Rakipler: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality

Pazar gözlemi: %90 Google Dataplex kullanımı; kullanıcılar "kolay kullanım + kural çeşitliliği" diyor
Dataplex'e karşı avantaj: vendor lock-in yok, PII native, 4 tıkla kural ekleme, maliyet=0 lisans
AWS Glue DQ'ya karşı avantaj: self-hosted, PII native, Holt-Winters eşdeğer anomali tespiti
