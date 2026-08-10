# DQ — Claude Çalışma Rehberi

## Proje
DQ (Data Quality Platform) — FastAPI + MySQL + Airflow + Docker Compose
Konum: `/opt/dq/dq_docker` (Contabo VPS)
GitHub: https://github.com/SHapeloglu/DQ.git (main branch)
Commit dili: Türkçe, format: `feat: GOREV N — açıklama`

---

## Çalışma Kuralları

- Sadece değişen fonksiyon/blok yaz — tüm dosyayı yeniden yazma
- HTML template istenmeden eklenmez
- Açıklama max 3 satır, kod önce gelir
- Bir komut ver, çıktıyı bekle, sonra devam et
- Her görev sonrası commit at

---

## Dosya Düzenleme Hiyerarşisi

1. `cat > /tmp/fix.py << 'EOF'` ile script yaz, sonra `python3 /tmp/fix.py`
2. `cat >>` ile append (sessiz çalışır, tail ile kontrol et)
3. `sed` kullanma — güvenilmez

---

## Yeni Endpoint Ekleme Paterni

1. `routers/api.py` → GET endpoint ekle (source_id=None, limit: int = 200)
2. `routers/ui.py` → HTML route ekle (request: Request — tip hint zorunlu)
3. `templates/xxx.html` → Bootstrap 5 + Chart.js template
4. `docker compose build dq-web && docker compose up -d dq-web`
5. `curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/xxx`
6. `git add ... && git commit -m "feat: ..."`

---

## Yeni Assert Tipi Ekleme Paterni

1. `dq/engine.py` → fonksiyon yaz (CheckEngine sınıfından önce)
2. `dq/config.py` → import satırına ekle (~satır 40)
3. `dq/config.py` → `_ASSERTION_MAP` dict'ine lambda ekle (~satır 46-60)
4. `tests/test_xxx.py` → TestXxx sınıfı + test_in_assertion_map testi yaz

---

## Kritik Teknik Notlar

### from __future__ import annotations sorunu
- api.py ve ui.py'de bu satır var → Pydantic ForwardRef hatası verir
- api.py'de `Request` import zorunlu: `from fastapi import APIRouter, HTTPException, Request`
- Yeni endpoint parametrelerinde `Optional[int]` kullanma → `source_id=None` yaz
- ui.py'de `request: Request` tip hint'i kalmalı (422 verir kaldırınca)

### Docker
- Sadece `dags/` volume mount — diğer her değişiklik rebuild gerektirir
- Build: `docker compose build dq-web && docker compose up -d dq-web`
- curl 000 dönerse: `sleep 5` bekle
- Log: `docker logs dq-web --tail 20`

### Test
- pymysql sadece Docker içinde — venv'de yok
- DB import etme testlerde: database.py, main.py, routers/*.py import etme
- MagicMock kullan
- zscore testlerinde sabit dizi (std=0) kullanma: `[100.0 + i*0.1 for i in range(20)]`

### DB
- `docker exec -i dq-db mysql -u root -proot dq -e "..."`
- alert_settings singleton: id=1

### Postgres MetricStore
- DSN: `postgresql://dquser:dqpass@host.docker.internal:5432/dqmetrics`
- Şema: `dwh_health_log.dq_metrics`

---

## Session Sonu Kontrol Listesi

1. `python3 -m pytest tests/ -q` → test sayısını teyit et
2. 4 MD dosyasını güncelle
3. `git add -A && git commit -m "docs: session sonu MD güncellemesi"`
4. `git push origin main`
5. MD dosyalarını zip'le, indir
