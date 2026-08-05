# DQ (Data Quality Platform) - Proje Anayasası

## Proje Özeti
DQ; veritabanı bağlayıcıları, kalite motoru, Airflow entegrasyonları, FastAPI web arayüzü ve anomali tespiti içeren modüler bir Python Veri Kalitesi platformudur.

## Kodlama Standartları
- Python 3.10+
- Tüm fonksiyonlarda Type Hinting zorunlu
- Özel exception yapıları kullan
- PEP8, modüler ve temiz kod
- Testler pytest ile tests/ altında

## Temel Komutlar
- Test: cd /opt/dq/dq_docker && pytest tests/
- Docker rebuild: docker compose build dq-web && docker compose up -d dq-web
- DB migration: docker exec -i dq-db mysql -u root -proot dq -e "..."

## Token Kuralları (Sıkı)
- Sormadan main.py, templates/, tests/ context'e ekleme
- Değişiklik tek fonksiyon/metot bazında yap
- HTML şablonları HİÇBİR ZAMAN context'e girmesin
- Açıklama istenmediği sürece sadece kod yaz

## Kritik Hatırlatmalar
- Çalışma dizini: /opt/dq/dq_docker — root'tan komut çalıştırma
- Multi-komut paste sorun çıkarır — tek komut at
- sed ile düzenleme bazen sessizce başarısız — Python ile değiştir
- BaseConnector abstract metodu close() — disconnect() değil
- SqlAlchemyConnector.test_connection() → dict içinde dialect key zorunlu
- alert_settings tablosu singleton (id=1)
