# DQ — Session Başlangıç Dosyası
Proje: DQ (Data Quality Platform)
Konum: /opt/dq/dq_docker (Contabo VPS, SSH erişimi)
Stack: FastAPI + MySQL + Airflow + Docker

## Mimari (özet)
- dq/engine.py      → CheckEngine + assert tipleri ✅
  Tüm assert tipleri: not_empty, regex_match, accepted_values, freshness_hours,
  row_count_between, referential_integrity, equals, between, greater_than, less_than,
  completeness_ratio, statistical_anomaly, schema_drift, schema_check,
  duplicate_row, custom_sql, volume_anomaly
- dq/config.py      → SodaConfig + _resolve_env_vars() + _ASSERTION_MAP (satır ~46) ✅
- dq/connectors.py  → BaseConnector + MySQL/PG/Oracle/BQ/CSV/SQLAlchemy/MongoDB/DB2
- dq/metrics.py     → MetricStore (SQLite dev + Postgres production) ✅
- dq/scoring.py     → get_health_score(), get_score_trend(), get_all_scores() ✅
- dq/reporter_v2.py → full_report() + MetricStore entegrasyonu ✅
- dq/airflow.py     → DQOperator — check'leri Airflow üzerinden çalıştırır ✅
  NOT: Web UI'dan check çalıştırma endpoint'i YOK — sadece Airflow/CLI çalıştırır
- main.py           → FastAPI app init + router include'ları (59 satır) ✅
- database.py       → MySQL init_db() + column_profiles PII + glossary kolonları ✅
- cache_layer.py    → TTLCache + profile_cache singleton (5 dk TTL) ✅
- profiler.py       → cache + PII tagging (24 pattern) + enum/regex/empty önerileri + SQL optimize ✅
- extensions.py     → AlertManager (email/slack/webhook) + load_alert_manager ✅

## Yeni Assert Tipi Ekleme Adımları
1. dq/engine.py → fonksiyon yaz (CheckEngine sınıfından önce)
2. dq/config.py → import satırına ekle (satır ~40)
3. dq/config.py → _ASSERTION_MAP dict'ine lambda ekle (satır ~46-58)
4. tests/test_engine.py → TestXxx sınıfı + test_in_assertion_map testi yaz

## Routers (routers/)
- routers/sources.py → /sources CRUD ✅
- routers/checks.py  → /checks CRUD + /api/suggestions/reject ✅
  NOT: check_create → assert_type + query + assert_value DB'ye kaydedilir, çalıştırılmaz
- routers/api.py     → /api/* + /odata + alerting + /api/health-score + /api/glossary + /api/pii-report + /api/alert-settings ✅
- routers/ui.py      → /wizard, /import, /runs, /health, / ✅

## Check Çalıştırma Akışı
dq/airflow.py DQOperator._run_checks()
  → dq/config.py SodaConfig.build_checks()
    → _parse_check() → _ASSERTION_MAP[assert_type](assert_value) → assertion fonksiyonu
  → dq/engine.py CheckEngine.run()
    → connector.execute(query) → assertion(value) → CheckResult

## Güvenlik Katmanı
- secrets/.env.secrets     → password'lar + SMTP/alert config (chmod 600, git ignore)
- secrets/.env.secrets.gpg → şifreli kopya (git'te ✅)
- scripts/decrypt_secrets.sh → deploy öncesi çalıştır
- GPG key: dq@localhost (RSA 4096, /root/.gnupg)

## Docker
- dq-web  → 0.0.0.0:8002 (uvicorn)
- dq-db   → 0.0.0.0:3308 (mysql:8.0)
- ÖNEMLİ: Kod değişikliklerinin yürürlüğe girmesi için `docker compose build dq-web && docker compose up -d dq-web` gerekir
  (sadece dags/ klasörü volume mount edilmiş, diğer dosyalar image içinde)

## Postgres (MetricStore — Production)
- DSN: postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics
- Şema: dwh_health_log.dq_metrics ✅

## DB Tabloları
- sources (+ alert_enabled kolonu)
- checks, runs, run_results
- column_profiles (+ business_name, description, owner, tags, is_pii, pii_type)
- alert_settings (id=1 singleton)
- rule_library
  NOT: assert_type değerleri → engine.py fonksiyon adlarıyla eşleşir (_ASSERTION_MAP anahtarları)

## Kurallar (UYULACAK)
- Sadece değişen fonksiyon/blok yaz
- Tüm dosyayı yeniden yazma
- HTML/template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir
- DB migration: docker exec -i dq-db mysql -u root -proot dq -e "..."
- sed güvenilmez — Python string replace scripti kullan (/tmp/ altında)

## Test Durumu
136 passed, 3 skipped ✅

## Git Son Commitler
9967e86 feat: GÖREV 15 — volume_anomaly assertion (satır sayısı değişim tespiti, 8 yeni test)
28d5c17 feat: GÖREV 14 — custom_sql assertion (kullanıcı tanımlı SQL, 7 yeni test)
6887602 feat: GÖREV 13 — duplicate_row assertion (tekrar satır tespiti, 5 yeni test)
654e4be feat: GÖREV 12 — schema_check assertion (kolon varlığı + tip kontrolü, 8 yeni test)
6a12754 docs: ARCHITECTURE.md güncellendi

## Backlog (Öncelik Sırasına Göre)

### Ayrı Sayfa / Dashboard (Zor)
- [ ] GÖREV 16: Statistical Anomali — MetricStore + istatistik, health dashboard anomali sekmesi
- [ ] GÖREV 17: Cross-table Check — iki farklı kaynakta çapraz kolon karşılaştırma (ayrı sayfa)
- [ ] GÖREV 18: Distribution Check — dağılım karşılaştırma (görsel grafik gerekiyor)

### Diğer
- [ ] GÖREV 19: Veri kalitesi trendi karşılaştırma — iki kaynak yan yana skor trendi
- [ ] GÖREV 20: Check sonuçları email özet raporu — günlük/haftalık özet
- [ ] GÖREV 21: Rule library UI — kural kütüphanesini wizard'da görsel yönetim
- [ ] Docker Secrets / Vault entegrasyonu (ertelendi)
- [ ] Airflow connection'ları secure store'dan yükle (ertelendi)

## Rakip Karşılaştırma Notları
- DQ-main güçlü: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), business glossary
- DQ-main zayıf: Anomali tespiti (2/10), connector çeşitliliği (6/10), ölçeklenebilirlik (4/10)
- Backlog tamamlanırsa tahmini genel puan: 6.7 → 7.8/10

## Yeni Session'da Yap
1. SESSION_START.md + CLAUDE.md + ARCHITECTURE.md + TASKS.md zip'le yükle
2. Öncelikli: GÖREV 16 (Statistical Anomali) — anomali tespiti kritik eksik
3. Alternatif: GÖREV 17 (Cross-table Check) — rakiplerle rekabet için kritik
