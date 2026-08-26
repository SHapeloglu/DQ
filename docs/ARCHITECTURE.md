# DQ Mimari Haritası

## 1. Çekirdek Motor (dq/)
- engine.py: CheckEngine + 19 assert tipi + custom_script_assertion()
- anomaly.py: AnomalyDetector (z-score + EWMA + Holt-Winters + trend yönü)
- config.py: SodaConfig + _ASSERTION_MAP (19+1 entry) + _get_custom_script_fn()
- metrics.py: MetricStore (SQLite dev + Postgres prod + read replica)
- connectors.py: BaseConnector + 8 veritabanı tipi
  NOT: BaseConnector abstract metodu close() — disconnect() değil
  NOT: SqlAlchemyConnector.test_connection() → dict içinde dialect key zorunlu
- scoring.py: get_health_score(), get_score_trend()
- reporter_v2.py: full_report()
- airflow.py: DQOperator
  NOT: Web UI'dan check çalıştırma endpoint'i YOK — sadece Airflow/CLI çalıştırır

### Yeni Assert Tipi Ekleme Adımları
1. dq/engine.py → fonksiyon yaz (en sona, CheckEngine sınıfından önce)
2. dq/config.py → import satırına ekle (satır ~40)
3. dq/config.py → _ASSERTION_MAP dict'ine lambda ekle (satır ~46-58)
4. tests/test_engine.py → TestXxx sınıfı + test_in_assertion_map testi yaz

### custom_script_assertion Detayı
- İmza: custom_script_assertion(code: str, function_name: str = "check")
- AST Validation: os, subprocess, sys, shutil, pathlib, socket, urllib, requests yasaklı
- Yasaklı fonksiyonlar: eval, exec, compile, __import__, open, input, print
- Execution: Kısıtlı __builtins__ (len, str, int, float, bool, abs, min, max, math vb.) ile exec()
- DB Entegrasyonu: _get_custom_script_fn(script_id) → custom_scripts tablosundan kod yükle
- Dönen değer: Assertion fonksiyonu (value → bool)

### schema_check Detayı
- İmza: schema_check(expected_columns: dict) — kolon varlığı + tip kontrolü
- SQL: SELECT column_name, data_type FROM information_schema.columns WHERE table_name=... AND table_schema=...
- Dönen değer: liste veya JSON string — [{"column_name":..., "data_type":...}]
- tip None ise sadece varlık kontrol edilir; case-insensitive karşılaştırma yapar

## 2. Web Backend
- main.py: FastAPI init + router include'ları (sources, checks, scripts, api, ui)
- database.py: MySQL bağlantısı + init_db() (custom_scripts dahil tüm tablolar)
- profiler.py: PII tagging (24 pattern)
- cache_layer.py: TTLCache (5 dk)
- extensions.py: AlertManager
- secrets_loader.py: get_secret() — /run/secrets/ → env → default

## 3. Routers
- sources.py: /sources CRUD
- checks.py: /checks CRUD + /api/suggestions/reject
- scripts.py: /scripts CRUD + /api/scripts/test (dry-run)
- api.py: /api/runs, /api/results, /api/health-score, /api/profile-export, /api/pii-report, /odata
- ui.py: Web sayfaları

## 4. DB Şeması (MySQL — dq-db:3308)
- sources, checks, runs, run_results
- column_profiles (PII, business metadata)
- alert_settings (singleton id=1)
- rule_library (pattern → rule → times_used)
- custom_scripts (id, name, code LONGTEXT, function_name, description, is_active)
- MetricStore: dwh_health_log.dq_metrics (Postgres)

## 5. Airflow DAG'ları
- dq_mysql_dag.py, dq_postgres_dag.py, dq_oracle_dag.py, dq_mongo_dag.py
- dq_scheduled_profiling_dag.py

## 6. Güvenlik
- secrets/.env.secrets (chmod 600, git ignore)
- secrets/files/ (Docker secrets, chmod 600, git ignore)
- secrets_loader.py: /run/secrets/ → env → default
- GPG key: dq@localhost (RSA 4096)
- custom_script_assertion: AST tabanlı kod güvenlik doğrulaması

## 7. Kritik Nodlar (Grafik Analizi)
- build_connector(): betweenness 0.437, tüm connector factory buradan geçer
- CheckEngine: 43 edge, en geniş etki alanı
- get_conn(): 29 edge (bağlantı dar boğazı)
- api_post_run: run kayıt + alert tetikleme merkezi (routers/api.py ~L98)
- load_alert_manager(): alert_settings tablosundan yükler, None dönebilir

## 8. Wizard Veri Akışı
1. Kaynak seç → /api/columns/{source_id} → kolon listesi
2. Profil çalıştır → /api/profile/{source_id} POST → istatistik + PII banner + glossary
3. Kural ekle → /checks POST (assert_type + query + assert_value DB'ye kaydedilir, çalıştırılmaz)
4. Run tetikle → Airflow DQOperator → _ASSERTION_MAP'ten assertion yükle → CheckEngine.run()
5. Sonuç → /api/runs POST → run_results tablosu → alert

## 9. Anomali Tespiti Zinciri
Wizard → Airflow DQOperator → CheckEngine.run() → AnomalyDetector.detect_all()
→ _detect_trend() [trend yönü] → run_results → /anomaly dashboard

## 10. Custom Script Akışı
/scripts/new → kod gir + test et (/api/scripts/test dry-run)
→ AST validation → custom_scripts DB'ye kaydet
→ /checks'te assert_type="custom_script", assert_value="{script_id}"
→ Airflow → _get_custom_script_fn(id) → DB'den kod yükle → exec() → assertion

## 11. Puanlama (Rekabet)
Genel: 6.7/10 → ~8.4/10
Güçlü: PII/KVKK (9/10), maliyet (10/10), anomali trend (8.5/10), wizard UX (8.5/10), custom scripts (8.5/10)
Zayıf: ölçeklenebilirlik (6.5/10)
