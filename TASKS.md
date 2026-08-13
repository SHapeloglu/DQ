# DQ — Aktif Görevler
## Tamamlananlar
- [x] GÖREV 1-24: Temel motor, connectors, UI dashboard'lar, alerting, PII, wizard
- [x] GÖREV 25: secrets_loader.py — Docker Secrets uyumlu secret okuma katmanı
- [x] GÖREV 26: TOML'da secret: prefix desteği, _resolve_env_vars entegrasyonu
- [x] GÖREV 27: Thread-safe MySQL connection pool (size=5), release_conn()
- [x] GÖREV 28: Docker secrets dosya mount (secrets/files/, docker-compose secrets bloku)
- [x] GÖREV 29: profile_column tek sorgu optimizasyonu (3 sorgu → 1)
- [x] GÖREV 30: zscore_anomaly MetricStore entegrasyonu + statsmodels/numpy eklendi
- [x] GÖREV 31: Wizard'a ANOMALİ/TREND bölümü — Hacim anomalisi + Geçmişe dayalı anomali
- [x] GÖREV 32: AnomalyDetector → Airflow DQOperator entegrasyonu (Holt-Winters/zscore)
- [x] GÖREV 33: Anomali dashboard Yöntem/Skor sütunları (Holt-Winters/zscore badge)
- [x] refactor: cross_table_check ölü kod temizliği (3 tanım → 1)
- [x] GÖREV 34: AnomalyResult'ları run_results DB'ye yaz (to_check_dict + airflow._serialize)
- [x] GÖREV 35: run_detail.html anomali badge'i ([zscore]/[holt_winters]/[ewma] → sarı uyarı ikonu)
- [x] GÖREV 36: Wizard'a schema_drift + schema_check chip/panel/query/TOML eklendi
- [x] GÖREV 37: Alert'lerde anomali/kural ayrımı (ANOMALİ ⚠ + KURAL HATASI ✗ bölümleri)
- [x] GÖREV 38: Airflow DSN kontrolü — get_secret() zaten kullanılıyor, hardcoded DSN yok
- [x] GÖREV 39: EWMA anomali yöntemi — <5 zscore, 5-13 ewma, >=14 holt_winters
**Test: 191 passed, 3 skipped**

---
## Backlog (öncelik sırasıyla)
- [ ] GÖREV 40: Ölçeklenebilirlik — CheckEngine.run() ThreadPoolExecutor (4/10 → hedef 6/10)
- [ ] GÖREV 41: run_detail.html badge'ine [ewma] desteği ekle (şu an sadece zscore/holt_winters)
- [ ] GÖREV 42: Anomali dashboard'una yöntem filtresi (zscore / ewma / holt_winters)

---
## Rakip Karşılaştırma (Güncel)
- **Güçlü**: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), wizard UX (8/10)
- **Anomali tespiti**: 7/10 (zscore + EWMA + Holt-Winters, otomatik yöntem seçimi)
- **Zayıf**: ölçeklenebilirlik (4/10)
- **Rakipler**: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality
- **Tahmini genel puan**: ~8.0/10 (backlog tamamlanırsa ~8.5/10)

---
## Pazar Geri Bildirimi
- Piyasada %90 Google Dataplex kullanımı gözlemlendi
- Kullanıcılar: 1) kolay kullanım 2) kural çeşitliliği diyor
- Dataplex'te olup bizde olan: duplicate_row, custom_sql, referential_integrity, cross_table, schema_check, schema_drift ✅
- Dataplex'te olan bizde EKSİK: row_condition (kısmen custom_sql ile karşılanıyor)
- AWS Glue Data Quality: DetectAnomalies native ML — bizim 3 yöntemli sistem ile eşdeğer/üstün
- Wizard UX: 4 tıkla kural ekleme, SQL bilgisi gerektirmez — Dataplex'ten üstün
