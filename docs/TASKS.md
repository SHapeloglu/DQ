# DQ — Aktif Görevler

## Tamamlananlar (Bu Oturum)
- [x] GÖREV 44: Anomali trend yönü analizi (up/stable/down)
- [x] GÖREV 45: Read replica desteği (MetricStore)
- [x] GÖREV 47: Custom assertion script upload (AST validation + API)

## Tamamlananlar (Önceki Oturumlar)
- [x] GÖREV 1-43: Temel motor, connectors, UI, alerting, PII, wizard, anomali
- [x] GÖREV 46: Dataplex vs DQ benchmark raporu
- [x] GÖREV 48: Data profiling export (CSV/JSON)

**Test: 196 passed, 3 skipped ✅**

---

## Backlog
Boş

---

## Rakip Karşılaştırma (Güncel)
- Güçlü: PII/KVKK (9/10), maliyet (10/10), sağlık skoru (8/10), wizard UX (8/10), anomali trend (8.5/10)
- Ölçeklenebilirlik: 6/10 (ThreadPoolExecutor, max 4 paralel check)
- Rakipler: Soda Core, Great Expectations, Google Dataplex, AWS Glue Data Quality
- Tahmini puan: ~8.4/10

---

## Pazar Geri Bildirimi
- Dataplex'ten önde: duplicate_row, custom_sql, referential_integrity, cross_table, schema_check, schema_drift, row_condition, wizard UX
- AWS Glue'den biraz önde: DetectAnomalies native ML yerine 3 yöntemli sistem
- Kullanıcılar: kolay kullanım + kural çeşitliliği istiyor
