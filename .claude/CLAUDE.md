# DQ (Data Quality Platform) - Proje Anayasası

## Proje Özeti
DQ; veritabanı bağlayıcıları (`connectors`), kalite motoru (`engine`), Airflow entegrasyonları, FastAPI web arayüzü ve anomali tespiti içeren modüler bir Python Veri Kalitesi platformudur.

## Kodlama Standartları
- **Python Sürümü:** Python 3.10+
- **Tip İpuçları:** Tüm fonksiyon ve metotlarda Type Hinting zorunludur.
- **Hata Yönetimi:** Özel exception (Custom Exception) yapıları kullanılmalıdır.
- **Kod Stili:** PEP8 standartlarına uygun, modüler ve temiz kod.
- **Testler:** Testler `pytest` ile `tests/` klasörü altında yürütülür.

## Temel Çalıştırma Komutları
- Testleri Çalıştır: `pytest tests/`
- Uygulamayı Başlat: `python main.py`
- Docker ile Çalıştır: `docker-compose up -d`

## Token Kuralları (Sıkı)
- Sormadan `main.py`, `templates/` veya `tests/` dosyalarını context'e ekleme
- Değişiklik tek fonksiyon/metot bazında yap, tüm dosyayı yazma
- HTML şablonları HİÇBİR ZAMAN context'e girmesin
- graphify-out/ klasörünü context'e ekleme
- Açıklama istenmediği sürece sadece kod yaz
