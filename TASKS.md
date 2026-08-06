# DQ — Aktif Görevler

## Tamamlananlar
- [x] GÖREV 3: MongoConnector
- [x] GÖREV 4: DB2 Doğrulama
- [x] GÖREV 5: Airflow DAG Genişletme
- [x] GÖREV 6: Sağlık Skoru Dashboard — trafik ışığı + trend grafiği ✅
- [x] GÖREV 7: Alerting (commit: 7e505ea)
- [x] GÖREV 8: PII Otomatik Tespiti (commit: 5b6c6d0)
- [x] GÖREV 9: Business Glossary + Wizard UI (commit: e558cf7)
- [x] GÖREV 10: Scheduled Profiling DAG (commit: 5757043)
- [x] GÖREV 11: referential_integrity (commit: f6c8c50)
- [x] Wizard PII uyarı banner (commit: 9c9738b)
- [x] KVKK raporu CSV export (commit: 9512c61)
- [x] profile_column SQL optimizasyonu — distinct + temel istatistik tek sorguda (commit: 9a2eb57)

Test: 108 passed, 3 skipped ✅

---

## Backlog — Öncelik Sırasına Göre

### Wizard'a Eklenecekler (Kolay)
- [ ] GÖREV 12: Schema Check — kolon varlığı + tip kontrolü, yeni assert tipi
- [ ] GÖREV 13: Duplicate Row — tüm satır tekrarı, yeni assert tipi

### Wizard'a Eklenecekler (Orta)
- [ ] GÖREV 14: Custom SQL assert — textarea ile SQL yaz, sonuç karşılaştır
- [ ] GÖREV 15: Volume Anomali — MetricStore geçmişinden satır sayısı değişim tespiti

### Dashboard / Ayrı Sayfa (Zor)
- [ ] GÖREV 16: Statistical Anomali — MetricStore + istatistik, health dashboard anomali sekmesi
- [ ] GÖREV 17: Cross-table Check — iki kaynak çapraz kolon karşılaştırma, ayrı sayfa
- [ ] GÖREV 18: Distribution Check — dağılım karşılaştırma, görsel grafik

### Diğer Özellikler
- [ ] GÖREV 19: Veri kalitesi trendi karşılaştırma — iki kaynak yan yana skor trendi
- [ ] GÖREV 20: Check sonuçları email özet raporu — günlük/haftalık
- [ ] GÖREV 21: Rule library UI — kural kütüphanesini wizard'da görsel yönetim

---

## Ertelenen
- Docker Secrets / Vault entegrasyonu
- Airflow connection'ları secure store'dan yükle
- profile_column: sample + tip bazlı sorguları birleştirme (zor)

---

## Sıradaki
GÖREV 12 (Schema Check) — en kısa, wizard'a kolay eklenir
GÖREV 15 (Volume Anomali) — anomali tespiti eksiğini kapatır, MetricStore hazır
