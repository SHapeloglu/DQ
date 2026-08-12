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

**Test: 191 passed, 3 skipped**

---

## Backlog (öncelik sırasıyla)

- [ ] GÖREV 34: AnomalyResult'ları run_results tablosuna yaz (Airflow log'dan DB'ye)
  Şu an sadece Airflow log'una yazılıyor, dashboard'da görünmüyor
- [ ] GÖREV 35: ML anomali tespiti iyileştirme — isolation forest veya EWMA
- [ ] GÖREV 36: Airflow connection'larını secrets_loader ile yükle (DAG'larda hardcoded DSN temizliği)
- [ ] GÖREV 37: schema_check + schema_drift wizard paneli (benzer pattern: volume_anomaly gibi)
- [ ] GÖREV 38: Ölçeklenebilirlik iyileştirmesi (4/10 → hedef 6/10)

---

## Rakip Karşılaştırma (Güncel)
- **Güçlü**: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), wizard UX (8/10)
- **Anomali tespiti**: 2/10 → 6/10 (Holt-Winters + zscore, MetricStore entegrasyonu)
- **Zayıf**: ölçeklenebilirlik (4/10)
- **Rakipler**: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality
- **Tahmini genel puan**: ~7.5/10 (backlog tamamlanırsa ~8.5/10)

---

## Pazar Geri Bildirimi (bu oturumda)
- Piyasada %90 Google Dataplex kullanımı gözlemlendi
- Kullanıcılar: 1) kolay kullanım 2) kural çeşitliliği diyor
- Dataplex'te olup bizde olan: duplicate_row, custom_sql, referential_integrity, cross_table ✅
- Dataplex'te olan bizde EKSİK: row_condition (kısmen custom_sql ile karşılanıyor)
- AWS Glue Data Quality: DetectAnomalies native ML — bizim Holt-Winters ile eşdeğer
- Wizard UX: 4 tıkla kural ekleme, SQL bilgisi gerektirmez — Dataplex'ten üstün
