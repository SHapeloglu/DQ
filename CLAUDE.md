# CLAUDE.md — DQ (Veri Kalitesi Platformu)

Self-hosted veri kalitesi platformu: FastAPI web arayüzü (`dq-web`), 19 assert tipi, anomali tespiti (z-score, EWMA, Holt-Winters), PII/KVKK tespiti ve Airflow DAG'ları ile çalışır. Kontroller Airflow'dan çalışır; web arayüzünden kontrol çalıştırma yoktur. Ayrıntılı mimari: `architect.md`.

## Konum

- **Dev ve canlı (aynı klasör):** `/opt/dq/dq_docker/` — Docker Compose ile çalışır. Üst klasör `/opt/dq/` yalnızca `dq_v4_final.zip` (eski arşiv) tutar.
- **Git:** `/opt/dq/dq_docker` bir git deposu; `main` son commit `f2bc7c6` (2026-11-09, PR #6). Uzak: `origin` = `https://github.com/SHapeloglu/DQ.git`. Yerel dal docs/agent-workflow (b6000da, push yok).
- **Servis / port:** `dq-web` konteyneri, host `8002` → konteyner `8000`. Alan adı `dq.powerbi.com.tr` (nginx üzerinden; port 8002 tüm arayüzlere açık, güvenlik duvarı izinli IP'lere bağlı (doğrulanmadı)).
- **Veritabanı:** ortak `mysql-ortak` (veritabanı `dq`, kullanıcı `uygulama`, ağ `ortak-db`). Metrik deposu PostgreSQL (`dwh_health_log`).

## Komutlar

```bash
cd /opt/dq/dq_docker && docker compose up -d --build     # yeniden build + başlat (canlı etkiler)
docker compose ps
docker logs --tail 100 dq-web
docker exec -i mysql-ortak mysql -u uygulama -p"$ORTAK_SIFRE" dq   # şifre /opt/mysql-ortak/.env'de; md'ye yazma
python -m py_compile main.py                              # hızlı sözdizimi kontrolü
pytest                                                    # son kayıt: 251 passed, 3 skipped (2026-11-09); 2026-11-11'de yeniden çalıştırılmadı
```

## Kurallar ve tuzaklar

- Yeni assert tipi: `dq/engine.py` (CheckEngine'den önce) → `dq/config.py` import + `_ASSERTION_MAP` → `tests/test_engine.py`.
- Test mock: `routers.api.get_conn` mock'lanır, `database.get_conn` değil. `pymysql` venv'de yok; testlerde MagicMock kullan.
- Pydantic + `from __future__ import annotations` ile `Optional[int]` kullanma; `Request` import et.
- Türkçe içerikte UTF-8 kontrolü için dosyaları Python ile düzenle (`sed` güvenilmez).
- Sırlar: `.env`, `secrets/files/` ve `secrets/.env.secrets` git'e girmez. `secrets/.env.secrets.gpg` (şifreli kopya) bilinçli olarak git'te tutulur. Değer okunmaz, yalnız değişken adı yazılır. Bu kural `DQ_SECRET_KEY`, `DQ_ADMIN_PASSWORD`, `DQ_API_TOKEN`, `DQ_ENC_KEY` için de geçerlidir.
- Özel script güvenliği: AST doğrulaması ve öznitelik allowlist'i var ama sandbox tam değil (bkz. `task.md`). Kayıt anında da exec çalışır (routers/scripts.py:55,111 → dq/engine.py:458). Özel script kontrol olarak bağlı değil (`custom_script` assertion map'te yok; `task.md` 🔴).
- `get_conn()` havuzdan bağlantı alır; iş bitince `release_conn(conn)` ile iade et.
- TOML'da şifre: `password = "secret:DB_PASSWORD"` öneki (`secrets_loader`); değer değil, değişken adı yazılır.
- Büyük değişiklik sırası: `py_compile` → `pytest` → Docker build.
- Oturum sonunda `session.md`'ye kayıt düş, `task.md`'yi güncelle.

## Oturum geçmişi

Tamamlanan görev geçmişi (GÖREV 41–48, commit'ler, tarihler): `session.md`, eski kayıt bölümleri.

## Diğer dokümanlar

Tek md seti (küçük harfli, tek kaynak): `architect.md` (mimari), `backlog.md` (fikirler), `task.md` (görevler), `session.md` (oturum günlüğü), bu dosya (kurallar). Bu dört dosya sunucudadır (`/opt/dq/dq_docker`) ve git'te değildir; yedeği `task.md` 🟠 maddesinde. `docs/` altında `BENCHMARK.md`, `SESSION_START.md` ve `SANDBOX_TASARIM.md` kalır; eski `ARCHITECTURE`/`BACKLOG`/`CLAUDE`/`TASKS` kopyaları yerel dalda silindi (2026-11-14). Sunucudaki kopyalar sync onayı bekliyor. Kök `README.md` ve `SESSION_SUMMARY.md` ek belgedir.
