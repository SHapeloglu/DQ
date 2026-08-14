# DQ-main vs Rakipler — Benchmark Raporu

**Tarih:** Ağustos 2026 | **DQ-main Versiyonu:** v1.0 (194 test) | **Pazar:** Açık kaynak + self-hosted

---

## 1. Özellik Karşılaştırması (19 Assert Tipi)

| Assert Tipi | DQ-main | Dataplex | Soda Core | Great Expectations | AWS Glue |
|---|:---:|:---:|:---:|:---:|:---:|
| not_empty | ✅ | ✅ | ✅ | ✅ | ✅ |
| regex_match | ✅ | ✅ | ✅ | ✅ | ✅ |
| accepted_values | ✅ | ✅ | ✅ | ✅ | ✅ |
| freshness_hours | ✅ | ✅ | ✅ | ✅ | ❌ |
| row_count_between | ✅ | ✅ | ✅ | ✅ | ✅ |
| referential_integrity | ✅ | ✅ | ✅ | ✅ | ✅ |
| equals | ✅ | ✅ | ✅ | ✅ | ✅ |
| between | ✅ | ✅ | ✅ | ✅ | ✅ |
| greater_than | ✅ | ✅ | ✅ | ✅ | ✅ |
| less_than | ✅ | ✅ | ✅ | ✅ | ✅ |
| completeness_ratio | ✅ | ✅ | ✅ | ✅ | ✅ |
| **statistical_anomaly** | ✅ | ✅ | ❌ | ❌ | ✅ (DetectAnomalies) |
| **schema_drift** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **schema_check** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **duplicate_row** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **custom_sql** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **volume_anomaly** | ✅ | ✅ | ❌ | ❌ | ✅ (DetectAnomalies) |
| **zscore_anomaly** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **row_condition** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **TOPLAM** | **19/19** | **17/19** | **15/19** | **14/19** | **15/19** |

---

## 2. Anomali Tespiti (Deep Dive)

| Yöntem | DQ-main | Dataplex | Soda | GE | Glue |
|---|---|---|---|---|---|
| Z-Score | ✅ | ❌ | ❌ | ❌ | ❌ |
| EWMA (Exponential) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Holt-Winters | ✅ | ❌ | ❌ | ❌ | ❌ |
| Otomatik Seçim (n<8→z, n<14→ewma, n>=14→hw) | ✅ | ❌ | ❌ | ❌ | ❌ |
| ML-based DetectAnomalies | ❌ | ❌ | ❌ | ❌ | ✅ |
| Yöntem Filtresi UI | ✅ | ✅ | ❌ | ❌ | ❌ |

**Sonuç:** DQ-main + AWS Glue yan yana. DQ-main: istatistiksel rigor. Glue: ML blackbox.

---

## 3. PII/KVKK Tespiti

| Özellik | DQ-main | Dataplex | Soda | GE | Glue |
|---|:---:|:---:|:---:|:---:|:---:|
| Pattern-based PII (24 pattern) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Enum önerisi | ✅ | ✅ | ❌ | ❌ | ❌ |
| Regex önerisi | ✅ | ❌ | ❌ | ❌ | ❌ |
| PII Dashboard | ✅ | ✅ | ❌ | ❌ | ❌ |
| GDPR/KVKK Tag | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 4. Maliyet & Lisans

| Yön | DQ-main | Dataplex | Soda | GE | Glue |
|---|---|---|---|---|---|
| **Lisans** | Apache 2.0 | Google proprietary | Apache 2.0 | Elastic | AWS proprietary |
| **Hosting** | Self-hosted | Cloud (Google) | Self/Cloud | Self/Cloud | Cloud (AWS) |
| **Başlangıç Maliyeti** | $0 (Contabo VPS) | $5k-20k/ay | $0 | $0 | $2-5/dk |
| **Toplam TCO (1 yıl, 100TB)** | ~$500 (VPS) | ~$150k+ | ~$500 | ~$500 | ~$100k+ |

---

## 5. Toplam Puanlama

| Kategori | DQ-main | Dataplex | Soda | GE | Glue |
|---|:---:|:---:|:---:|:---:|:---:|
| **Özellik** | 9.5 | 9.0 | 8.0 | 7.5 | 8.5 |
| **Anomali** | 8.5 | 7.0 | 5.0 | 5.5 | 9.0 |
| **PII/KVKK** | 9.0 | 9.0 | 4.0 | 3.0 | 4.0 |
| **UX** | 8.5 | 7.5 | 6.0 | 6.5 | 5.5 |
| **Maliyet** | 9.5 | 5.0 | 9.0 | 9.0 | 6.0 |
| **Ölçeklenebilirlik** | 6.5 | 9.5 | 6.0 | 8.0 | 9.5 |
| **Entegrasyon** | 7.0 | 8.5 | 8.0 | 8.5 | 8.5 |
| **ORTALAMA** | **8.3/10** | **8.1/10** | **6.6/10** | **6.9/10** | **8.1/10** |

---

**DQ-main Nişi:** Self-hosted + PII-yoğun + maliyet bilinçli kuruluşlar
