# DQ — Aktif Görevler

## Tamamlananlar
- [x] GÖREV 3: MongoConnector
- [x] GÖREV 4: DB2 Doğrulama
- [x] GÖREV 5: Airflow DAG Genişletme
- [x] GÖREV 6: Sağlık Skoru Dashboard — trafik ışığı + trend grafiği
- [x] GÖREV 7: Alerting
- [x] GÖREV 8: PII Otomatik Tespiti
- [x] GÖREV 9: Business Glossary + Wizard UI
- [x] GÖREV 10: Scheduled Profiling DAG
- [x] GÖREV 11: referential_integrity
- [x] Wizard PII uyarı banner
- [x] KVKK raporu CSV export
- [x] profile_column SQL optimizasyonu
- [x] GÖREV 12: Schema Check — kolon varlığı + tip kontrolü
- [x] GÖREV 13: Duplicate Row — tekrar satır tespiti
- [x] GÖREV 14: Custom SQL assert
- [x] GÖREV 15: Volume Anomali
- [x] GÖREV 16: zscore_anomaly — MetricStore geçmişinden Z-score anomali tespiti
- [x] GÖREV 17: cross_table_check — iki kaynak çapraz skaler karşılaştırma
- [x] GÖREV 18: distribution_check — ortalama + std sapma dağılım kontrolü
- [x] GÖREV 19: trend_check — pencere ortalaması trend karşılaştırma
- [x] GÖREV 20: AlertManager.send_summary_report() — günlük/haftalık HTML email özet
- [x] GÖREV 21: Rule Library UI — /rule-library sayfası
- [x] GÖREV 22: Anomali Dashboard UI — /anomaly sayfası + /api/anomaly-results
- [x] GÖREV 23: Cross-Table UI — /cross-table sayfası + /api/cross-table-results
- [x] GÖREV 24: Distribution Check UI — /distribution sayfası + /api/distribution-results
- [x] Ana sayfaya Analiz Sayfaları kartı eklendi

**Test: 176 passed, 3 skipped**

---

- [x] GÖREV 25: secrets_loader.py — Docker Secrets uyumlu secret okuma katmanı
- [x] GÖREV 26: TOML'da secret: prefix desteği, _resolve_env_vars secrets_loader entegrasyonu
- [x] GÖREV 27: Thread-safe MySQL connection pool (size=5), release_conn() ile havuz iadesi

**Test: 176 passed, 3 skipped**

## Backlog

- [ ] profile_column: sample + tip bazlı sorguları birleştirme (zor)
- [ ] GÖREV 28: Airflow connection'larını Vault/secure store'dan yükle (Swarm geçişinde)
- [ ] GÖREV 29: profile_column tek sorguda birleştirme (conditional aggregation)

---

## Rakip Karşılaştırma (Güncel)
- **Güçlü**: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10),
  business glossary, rule library, anomali/distribution/cross-table UI
- **Zayıf**: ölçeklenebilirlik (4/10)
- **Tahmini genel puan**: ~8.2/10
