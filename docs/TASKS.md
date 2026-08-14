# DQ — Aktif Görevler

## Tamamlananlar (Bu Oturum)
- [x] GÖREV 41: run_detail.html ewma badge desteği
- [x] GÖREV 42: Anomali dashboard yöntem filtresi (zscore/ewma/holt_winters)
- [x] GÖREV 43: row_condition assert tipi (Dataplex gap kapandı)

## Tamamlananlar (Önceki Oturumlar)
- [x] GÖREV 1-40: Temel motor, connectors, UI, alerting, PII, wizard, ThreadPoolExecutor

**Test: 194 passed, 3 skipped ✅**

---

## Backlog (Yeni Fikirler)
- [ ] GÖREV 44: Anomali tespitinde trend analizi — son N değer eğilimi (artan/sabit/azalan)
- [ ] GÖREV 45: Read replica desteği — MetricStore Postgres read-only bağlantısı
- [ ] GÖREV 46: Dataplex vs DQ benchmark raporu — competitive analysis
- [ ] GÖREV 47: Custom assertion script upload — user-defined Python fonksiyonları
- [ ] GÖREV 48: Data profiling export (CSV/JSON) — istatistikler indirilebilir

---

## Rakip Karşılaştırma (Güncel)
- **Güçlü**: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), wizard UX (8/10)
- **Anomali tespiti**: 7/10 (zscore + EWMA + Holt-Winters, otomatik yöntem seçimi)
- **Ölçeklenebilirlik**: 6/10 (ThreadPoolExecutor, max 4 paralel check)
- **Rakipler**: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality
- **Tahmini genel puan**: ~8.3/10

---

## Pazar Geri Bildirimi
- Piyasada %90 Google Dataplex kullanımı gözlemlendi
- Kullanıcılar: 1) kolay kullanım 2) kural çeşitliliği diyor
- Dataplex'te olup bizde olan: duplicate_row ✅, custom_sql ✅, referential_integrity ✅, cross_table ✅, schema_check ✅, schema_drift ✅, row_condition ✅
- AWS Glue Data Quality: DetectAnomalies native ML — bizim 3 yöntemli sistem ile eşdeğer/üstün
- Wizard UX: 4 tıkla kural ekleme, SQL bilgisi gerektirmez — Dataplex'ten üstün
