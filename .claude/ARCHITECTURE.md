# DQ Mimari Haritası

## 1. Çekirdek Motor (`dq/`)
- `engine.py`: Veri kalitesi kontrollerini çalıştıran ana motor.
- `connectors.py`: Veritabanı bağlantı ve sorgu katmanı.
- `config.py`: SodaConfig — connector + check listesi üretir.
- `contracts.py`: Veri kontrat doğrulama mantığı.
- `anomaly.py`: Anomali tespit algoritmaları (z-score, Holt-Winters).
- `api.py`: REST API servisleri.
- `airflow.py`: Airflow Custom Operator.
- `reporter.py` / `reporter_v2.py`: Raporlama modülleri.

## 2. Web UI & Backend (`/` kök dizin)
- `main.py` (672 satır): Tüm route'lar burada.
- `database.py`: MySQL bağlantısı ve tablo şeması.
- `auth.py`: Kullanıcı yetkilendirme.
- `templates/`: Jinja2 şablonları.

## 3. Test & Orkestrasyon
- `tests/`: unit/integration testler.
- `dags/`: Airflow TOML yapılandırmaları.

## Kritik Nodlar (Graphify - 2026-07-26)
- `build_connector()` — betweenness 0.437, tüm connector factory buradan geçer; değiştirince testleri çalıştır
- `CheckEngine` — 43 edge, en geniş etki alanı; dokunmadan önce bağımlıları say
- `SodaConfig` — api_post_run → CheckEngine zincirinin köprüsü (config.py L76)
- `get_conn()` — 29 edge, bağlantı yönetimi dar boğaz adayı
- `main.py` — 672 satır; düzenlerken sadece ilgili fonksiyonu ver
