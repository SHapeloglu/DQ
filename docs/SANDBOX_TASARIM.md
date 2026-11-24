# Custom Script Sandbox Tasarımı

Durum: taslak, karar bekliyor
Tarih: 2026-11-11
Kapsam: `custom_script_assertion` ve `/api/scripts/test` için izolasyon. Bu belge yalnız tasarımdır; kod değişikliği yoktur.

Terimler:
- Sandbox A: bugünkü süreç içi yapı (AST denylist/allowlist, kısıtlı builtins, aynı süreçte `exec`).
- Sandbox B: ayrı süreç veya konteyner ile izolasyon.

Doğrulama notu: Satır numaraları 2026-11-11 tarihli çalışma ağacına göredir. Bu belge yazılırken pytest bu ortamda kurulu değildi; mevcut testler çalıştırılmadı. Gecikme ve kaynak değerleri tahmindir, ölçülmedi.

## 1. Amaç ve durum

Editor ve üzeri roller Python fonksiyonu yükleyip veri kalitesi kontrolü olarak kullanabilir. Kod, dq-web sürecinde çalışır.

Sandbox A şu katmanlardan oluşur:
- AST denylist: 8 yasaklı import adı (`dq/engine.py:390`) ve yasaklı fonksiyon adları (`dq/engine.py:394-398`).
- AST allowlist: öznitelik erişimi yalnız `GUVENLI_OZNITELIKLER` (`dq/engine.py:403-411`) ve `math.<ad>` ile sınırlıdır (`dq/engine.py:430-434`).
- Kısıtlı builtins sözlüğü (`dq/engine.py:444-454`).
- Aynı süreçte `exec(code, namespace)` (`dq/engine.py:458`).
- Assertion sarmalayıcısı: kullanıcı fonksiyonundaki her istisna `False` döner (`dq/engine.py:471-478`).

Neden yetersiz:
1. Aynı süreç. Kod, DB havuzu, `secrets_loader.get_secret` ile okunan değerler ve ortam değişkenleriyle aynı bellekte çalışır. Bir kaçış olursa bunlara doğrudan erişir.
2. Zaman ve bellek sınırı yok. Kodun kendi yorumu bunu kabul eder (`dq/engine.py:391-393`).
3. Denylist ad tabanlıdır. Nesneler değer olarak dolaşabildiği için ad kontrolü tek başına sınır değildir. Allowlist el ile bakım ister.
4. Kayıt sırasında da çalışır. `script_create` ve `script_update` kodu `exec` eder (`routers/scripts.py:55`, `routers/scripts.py:111`). Modül gövdesi kayıt anında çalışır.
5. Test endpoint'i event loop'u bloklar. `script_test` `async def` olarak tanımlı (`routers/scripts.py:144-145`) ama içinde senkron `exec` ve kullanıcı fonksiyonu çağrılır. Dockerfile tek işçi ile başlatır (`CMD`, son satır). Sonsuz döngü arayüzün tamamını durdurabilir. Bu bulgu kod okumasına dayanır; çalıştırılarak doğrulanmadı.
6. Çalışma hataları gizlenir. `assertion()` istisnayı `False`'a çevirir. Test endpoint'i "Test geçti: False" döndürür ve hata görünmez (`routers/scripts.py:160-166`).

Ek bulgu: çalışma zamanı yolu bugün bağlı değildir. `_get_custom_script_fn` tanımlıdır (`dq/config.py:61-78`) ama repoda çağıran yoktur. `_ASSERTION_MAP` içinde `custom_script` anahtarı yoktur (`dq/config.py:83-104`). `docs/ARCHITECTURE.md:88-92` ise Airflow'un bu yolu kullandığını yazar. Bu belge, Airflow yolu bağlanırsa aynı runner'ın kullanılmasını şart koşar.

Sandbox A'nın 1–6 maddelerindeki sorunların bir kısmı izolasyon gerektirmeden düzeltilebilir. Bu, Aşama 1'in kapsamıdır.

## 2. Tehdit modeli

Aktörler:

| Aktör | Yetki | Not |
|---|---|---|
| Editor | Kod ekler, düzenler, test eder | `yetki_kapisi` POST için editor ister (`auth.py:243-246`) |
| Admin | Editor yetkileri ve yönetim | `/admin`, `/settings` için admin (`auth.py:210-211`) |
| Servis anahtarı sahibi | Editor yetkisi, yalnız `/api/` ve `/odata/` | `DQ_API_TOKEN` (`auth.py:206`, `auth.py:248-250`) |
| Ele geçirilmiş editor hesabı | Editor ile aynı | Dış saldırgan için en olası giriş |

Varsayım: yazarlar güvenilir olmayabilir (hata veya kötü niyet). Anonim erişim login ve yetki kapısı ile engellenir. Port 8002 tüm arayüzlere açıktır (`docker-compose.yml`, `ports`); bu, giriş kontrolünün önemini artırır.

Varlıklar:
- Ortak MySQL, `dq` veritabanı. `ortak-db` ağındaki diğer servisler de erişilebilir olabilir; ağ içeriği bu depoda doğrulanamadı.
- Docker secret dosyaları (`/run/secrets`) ve ortam değişkenleri (`env_file`: `.env`, `secrets/.env.secrets`). Değerler okunmadı.
- PostgreSQL metrik deposu ve uyarı kanalları (SMTP, webhook) bağlantı bilgileri.
- Host dosya sistemi. `./dags:/app/dags` bağı yazılabilir modda (`:ro` yok). Yazılan dosyanın Airflow tarafından okunup okunmadığı doğrulanmadı.
- Kullanılabilirlik. Tek işçi uvicorn.

Kabul edilemez sonuçlar:
1. Sunucu dosyası okuma, özellikle `/run/secrets`, `/app` ve host bağları.
2. DB parolası veya secret değerine erişim.
3. Ağ çıkışı, veri sızdırma veya `ortak-db` üzerindeki diğer servislere erişim.
4. Kaynak tüketimi: sonsuz döngü, bellek ve CPU tüketimi, arayüzün durması.
5. Konteyner kaçışı ve host erişimi.
6. DAG dizinine yazarak Airflow'da kod çalıştırma (dolaylı yol).
7. Hata metni üzerinden HTML enjeksiyonu. `templates/script_form.html:165-182` hata metnini `innerHTML` ile basar.

Sandbox A'nın bilinen bypass sınıfları (kategori düzeyinde; örnek kod yazılmadı):
- Ad tabanlı yasak listeler. Değerler üzerinden dolaylı erişim yolu kalır.
- Öznitelik allowlist'inin el ile bakımı. Yeni eklenen her metot yeni bir yüzeydir.
- Metin biçimlendirme ile öznitelik zinciri okuma. Test dosyasında bir örnek kapatılmıştır (`tests/test_sandbox_sertlestirme.py:61-67`).
- Çalışma zamanı nesnelerine (jeneratör, çerçeve, kod nesnesi) öznitelik üzerinden ulaşma. Test dosyasında bir örnek vardır (`tests/test_sandbox_sertlestirme.py:52-58`).
- İzin verilen yerleşiklerin (ör. `type`) dolaylı kullanımı.
- Denylist dışı modüller. Import'un çalışmaması, kısıtlı builtins'te `__import__` bulunmamasına dayanır. Bu varsayım testlenmiyor.
- Kaynak tüketimi. Tek bir yerleşik çağrının C tarafında uzun süre çalışması süreç içi kontrolle kesilemez.
- Kayıt anında modül gövdesinin çalışması.
- Hata metinlerinde girdinin yankılanması.

Bu sınıfların her biri kullanılabilir bir saldırı anlamına gelmek zorunda değildir. Ama kontrol tek katmanlıdır ve sınırı aynı süreç paylaşır. Bu nedenle güvenlik sınırı olarak yeterli kabul edilmez.

## 3. Seçenekler

Tablo A: hangi tehdit alanını kapatır.

| Seçenek | Zaman aşımı | Bellek | Secret/env | Dosya okuma | Ağ | Konteyner kaçışı |
|---|---|---|---|---|---|---|
| (a) Alt süreç + rlimit + timeout + boş env | Evet | Evet | Evet | Hayır | Hayır | Hayır |
| (b) Ayrı konteyner (runner) | Evet | Evet | Evet | Evet | Evet | Kısmi; çekirdek paylaşılır |
| (c) gVisor / nsjail ek katman | Evet | Evet | Evet | Evet | Evet | Daha güçlü; (a) veya (b) üstüne eklenir |
| (d) RestrictedPython | Hayır | Hayır | Hayır | Hayır | Hayır | Hayır |

Tablo B: maliyet ve uyum.

| Seçenek | Güvenlik kazancı | Operasyonel maliyet | Gecikme (tahmini) | Mimari uyum | Geri alınabilirlik |
|---|---|---|---|---|---|
| (a) | Orta. Kaynak sınırı ve env sızıntısı kapanır. | Düşük. Yaklaşık 150 satır, aynı imaj. | +30 ile 80 ms istek başına | Yüksek | Kolay. Bayrakla eski yola dönülür. |
| (b) | Yüksek. Dosya, ağ, secret ve sınırlar kapanır. | Orta. Yeni compose servisi, iç ağ, sağlık kontrolü, log. | Soğuk 150 ile 600 ms; sıcak işçiyle 5 ile 20 ms | Orta. dq-web yalnız HTTP istemcisi olur. | Kolay. Servis kaldırılır, bayrak kapanır. |
| (c) | Ek katman. Çekirdek yüzeyi küçülür. | Yüksek. Host kurulumu (root), politika bakımı. WSL2 uyumu belirsiz. | (b) üstüne %10 ile 30 CPU | Düşük-orta | Orta |
| (d) | Düşük-orta. Derleme zamanı kısıtı, aynı süreçte kalır. | Düşük-orta. Bağımlılık ve politika. | Yaklaşık 0 | Orta | Kolay |

Değerlendirme:
- (d) önerilmez. Kod aynı süreçte kalır; DB bağlantısı ve secret aynı bellekte durur. Zaman ve bellek sınırı vermez. Sandbox A'nın yaptığını ikinci bir ad tabanlı katmanla yapar. Kısıtlı Python dönüşümleri tarihsel olarak kaçış açıkları yaşadı; bu belge hangi sürümlerin etkilendiğini incelemedi.
- (a) tek başına yetersiz. Alt süreç aynı uid ile (dq, uid 10001), aynı dosya sistemi ve ağla çalışır. Dosya ve ağ tehditlerini kapatmaz. Ama (b) içinde de kullanılır: runner'ın içindeki iş (a) ile sınırlanır.
- (c) şimdilik kapsam dışıdır. (b) kurulduktan sonra değerlendirilir.

## 4. Önerilen seçenek

Seçenek (b): ayrı bir runner servisi (önerilen ad: `dq-sandbox`). dq-web bu servise yalnız HTTP ile istek atar. Runner içinde her iş ayrı bir alt süreçte (a) mekanizmasıyla çalışır.

Gerekçe:
- Dosya, ağ ve secret erişimini aynı anda kapatan tek seçenek budur. (a) ve (d) bunu yapamaz.
- Docker socket dq-web'e bağlanmaz. Socket'i bir konteynere vermek host üzerinde kök yetkisine eşdeğerdir. Bu tasarım bunu gerektirmez. Runner kalıcı bir servistir; her istek için yeni konteyner açılmaz.
- Mevcut mimariyle uyumludur. dq-web yalnız bir istemci olur; `custom_script_assertion`'ın dış sözleşmesi korunur.
- Geri alınabilir. Runner kapatılır ve dq-web bayrağı eski değere döner.

Kabul edilen sınır: çekirdek paylaşılır. Çekirdek açığı riski kalır. Bu risk (c) ile azaltılabilir; Aşama 4 olarak kapsam dışı bırakıldı.

## 5. Arayüz sözleşmesi

### 5.1 Kullanıcı tarafı (mevcut endpoint, geriye uyumlu)

`POST /api/scripts/test`, form alanları:
- `code`: zorunlu, UTF-8, en çok 20 000 karakter (önerilen sınır).
- `function_name`: varsayılan `check`; `^[A-Za-z_][A-Za-z0-9_]{0,63}$`.
- `test_value`: isteğe bağlı, en çok 1 000 karakter. Önce `float` denenir, olmazsa metin (mevcut davranış korunur).
- `rows` (yeni, isteğe bağlı): JSON dizi, en çok 1 000 eleman. Çoklu örnek veri satırı için.

Başarı (HTTP 200, mevcut alanlar korunur):
`{"ok": true, "result": <bool veya bool listesi>, "value": <girdi>, "message": "..."}`

Hata (HTTP 400 veya üstü):
`{"ok": false, "error": "...", "kod": "<hata kodu>", "sure_ms": <int>}`

`kod` ve `sure_ms` yeni alanlardır. Mevcut istemciler bunları yok sayar.

### 5.2 dq-web ile runner arası (yeni, yalnız iç ağ)

`POST http://dq-sandbox:8080/run`. Dış port yoktur.
- Başlık: `X-DQ-Sandbox-Token`. Değer, Docker secret dosyasından okunur. Önerilen secret adı: `DQ_SANDBOX_TOKEN`. Değer bu belgeye ve git'e yazılmaz.
- İstek: `{"code": str, "function_name": str, "rows": [...]}`.
- Yanıt 200: `{"ok": bool, "result": [...] | null, "kod": str | null, "error": str | null, "sure_ms": int}`.

### 5.3 Hata kodları

| kod | Anlam | HTTP (kullanıcıya) |
|---|---|---|
| `SYNTAX` | Sözdizimi hatası | 400 |
| `YASAKLI_IMPORT` | Yasaklı import | 400 |
| `YASAKLI_OZNITELIK` | Yasaklı öznitelik | 400 |
| `YASAKLI_FONKSIYON` | Yasaklı ad | 400 |
| `FONKSIYON_YOK` | `function_name` tanımlı değil | 400 |
| `CALISMA_HATASI` | Kullanıcı fonksiyonu istisna fırlattı | 400 |
| `ZAMAN_ASIMI` | Süre sınırı aşıldı | 400 |
| `BELLEK_ASIMI` | Bellek sınırı aşıldı | 400 |
| `GIRDI_BUYUK` | Boyut sınırı aşıldı | 413 |
| `SANDBOX_KULLANILAMIYOR` | Runner yok, yanıt yok veya kuyruk dolu | 503 |

Kurallar:
- Kullanıcı kaynaklı hatalar HTTP 400 ve `ok: false` döner. Bu mevcut davranıştır ve korunur.
- Fail closed. Runner kullanılamazsa kod çalıştırılmaz (503). Sandbox A'ya otomatik geri dönüş yoktur.
- Hata metni yalnız kullanıcı fonksiyonunun istisna tipini ve kısa mesajını içerir. Yol, ortam değişkeni veya stack izi dönmez.
- UI hata metnini `textContent` ile basar; `innerHTML` kullanılmaz.
- Kayıt (`/scripts/new`, `/scripts/{id}/edit`) yalnız AST ve sözdizimi denetler; kodu çalıştırmaz (Aşama 1).

## 6. Geçiş planı

Aşama 0: bugünkü durum. Sandbox A; `exec` kayıtta ve testte çalışır.
- Çıkış kriteri: bu belge onaylanır. Mevcut testler kurulu bir ortamda yeşil çalışır.

Aşama 1: süreç içi sertleştirme (Sandbox A, yan önlemler).
- Sınır: zaman aşımı ve bellek sınırı süreç içinde gerçekten uygulanamaz. İş parçacığı durdurulamaz. Zaman aşımı yalnız alt süreçle mümkündür. Bu aşama zaman aşımı vaat etmez.
- İşler:
  1. `/api/scripts/test` `def` olur. İş parçacığı havuzunda çalışır; event loop bloklanmaz.
  2. Kod ve girdi boyut sınırları eklenir (`GIRDI_BUYUK`).
  3. Kayıtta `exec` kaldırılır. Yalnız `ast.parse` ve üst düzeyde `def <function_name>` aranır.
  4. Test endpoint'i kullanıcı fonksiyonunu ham olarak çağırır. İstisna `CALISMA_HATASI` olarak döner.
  5. UI hata metnini `textContent` ile basar.
- Çıkış kriteri: Aşama 1 testleri yeşil (bkz. bölüm 7). Event loop bloklanmadığı yalnız test ortamında, sonsuz döngü içermeyen bir örnekle doğrulanır.

Aşama 2: alt süreç (Sandbox B'nin çekirdeği, dq-web içinde).
- Kod `python -I -S` ile ayrı bir süreçte çalışır. Girdi ve çıktı JSON olarak stdin/stdout üzerinden aktarılır.
- Ortam değişkenleri boştur (`env` yalnız gerekli `PATH` ile). Çalışma dizini geçici bir klasördür.
- `rlimit`: adres alanı yaklaşık 128 MB, CPU yaklaşık 2 s, açık dosya yaklaşık 16. Duvar saati zaman aşımı 2 s; süreç grubu öldürülür.
- `RLIMIT_NPROC` kullanılmaz. Bu sınır uid bazlıdır ve sistem genelinde sayılır.
- Sınır: bu aşama dosya ve ağı kapatmaz (aynı uid). Tek başına kabul edilmez. Aşama 3'e geçiş basamağıdır.
- Bayrak: `DQ_SCRIPT_RUNNER=inprocess|child`. Varsayılan `inprocess`.
- Çıkış kriteri: zaman aşımı, bellek, ortam ve çökme testleri yeşil (bkz. bölüm 7).

Aşama 3: ayrı runner konteyneri (Sandbox B tam hali).
- Compose servisi `dq-sandbox` ayrı ve küçük bir imaj kullanır (`python:3.11-slim`). İmajda yalnız sandbox modülü bulunur. `dq/engine.py` üst düzeyde yalnız stdlib içe aktarır (`dataclasses`, `typing`); yine de sandbox kodunu ayrı bir modüle taşımak önerilir.
- Ağ: yalnız `sandbox-net` (`internal: true`, dış çıkış yok). dq-web hem `ortak-db` hem `sandbox-net` ağına bağlanır. Runner `ortak-db` ağına bağlanmaz.
- Ayarlar: `read_only: true`; `tmpfs /tmp` (16 MB); `cap_drop: [ALL]`; `security_opt: [no-new-privileges:true]`; root olmayan ayrı bir uid (ör. 10002); `mem_limit: 256m`; `cpus: 0.5`; `pids_limit: 64`. Volume, secret, `env_file` ve `ports` tanımlanmaz.
- Eşzamanlılık: en çok 2 iş. Kuyruk dolarsa 503.
- Çıkış kriteri: entegrasyon testleri yeşil (bkz. bölüm 7). Runner'dan dış ağa çıkılamaz; dq-web runner'a erişebilir.
- Yan iş (bu belgenin kapsamı dışı, ilişkili): `docker-compose.yml` içindeki `./dags:/app/dags` bağına `:ro` eklenmesi değerlendirilmelidir. Kod okumasında bu dizine yazan bir web yolu bulunmadı.

Aşama 4 (kapsam dışı): gVisor veya nsjail (seçenek c). Aşama 3 çıkışından sonra karar verilir.

Airflow yolu: `_get_custom_script_fn` bağlanmadan önce Aşama 3 tamamlanmalıdır. Bağlanırsa worker kodu doğrudan çalıştırmaz; aynı runner sözleşmesini çağırır.

## 7. Test planı

Mevcut testler:
- `tests/test_sandbox_sertlestirme.py`: 10 test. Sandbox A'nın taban regresyon setidir. Tüm aşamalarda korunur.
- `tests/test_scripts_cursor.py`: 1 test. `/scripts` GET regresyonu.
- `tests/test_guvenlik_son.py`: 4 test. Sandbox testi değildir; admin parolası ve `dq_token` secure bayrağını test eder. Bu belgenin sandbox kapsamına alınmaz.

Çalıştırma durumu: pytest bu ortamda kurulu değil. Mevcut testler bu belge yazılırken çalıştırılmadı.

Yeni testler (dosya yazılmadı; önerilen isimler):

Aşama 1, `tests/test_sandbox_sertlestirme.py` içine eklenir:
- `test_kod_boyutu_siniri_asilinca_girdi_buyuk`
- `test_kayitta_modul_govdesi_calistirilmaz` (üst düzeyde istisna içeren kod kaydedilebilir olmalı)
- `test_test_endpoint_calisma_hatasini_bildirir` (`CALISMA_HATASI` döner; "Test geçti: False" değil)
- `test_api_scripts_test_async_degil`
- `test_ornek_ozel_tutar_kontrolu_gecer` (README örneği; geçerli ve geçersiz değerler)

Aşama 2, yeni dosya `tests/test_sandbox_runner.py`:
- `test_zaman_asiminda_alt_surec_sonlanir`
- `test_bellek_siniri_asilinca_bellek_asimi`
- `test_alt_surec_ortam_degiskenlerini_gormez` (test içinde geçici ve zararsız bir değişken adı kullanılır; gerçek secret kullanılmaz)
- `test_surec_cokmesi_dq_web_i_etkilemez`
- `test_runner_kapaliyken_503_doner`
- `test_sozlesme_alanlari` (`ok`, `result`, `kod`, `error`, `sure_ms`)
- `test_api_scripts_test_geriye_uyumlu` (başarı ve hata biçimleri)

Aşama 3, Docker gerektirir. `@pytest.mark.docker` ile işaretlenir ve varsayılan olarak atlanır:
- `test_runner_dis_aga_cikamaz`
- `test_runner_kok_dosya_sistemi_salt_okunur`
- `test_runner_secret_dosyalari_yok`
- `test_runner_yalniz_sandbox_agina_bagli`
- `test_runner_bellek_ve_pid_limiti_uygulanir`

Kategori regresyonu (Aşama 1'den itibaren): bölüm 2'deki her bypass sınıfı için bir test. Test içeriği bu belgeye yazılmaz. Beklenen sonuç (reddedilme veya kapsama) kayıt altına alınır.

Manuel kontrol: hata metninin UI'da HTML olarak yorumlanmadığı (test yok, tarayıcıda kontrol edilir).

Ortak kabul kriteri: mevcut 15 sandbox ve scripts testi ile yeni testler yeşil. `python -m py_compile` geçer. Aşama 3'te Docker build başarılıdır.

## 8. Geri alma planı

Aşama 1: değişiklikler ayrı commit olarak tutulur. Geri alma `git revert` ile yapılır. Veri şeması değişmez; `custom_scripts` tablosu etkilenmez. Kayıtta `exec` kalktığında, modül gövdesine bağlı kayıtlı kodların davranışı değişebilir. Bu, geri alma öncesi kontrol edilir.

Aşama 2: `DQ_SCRIPT_RUNNER=inprocess` ile eski yol açılır. Kod silinmez. Geri alma bir ortam değişkeni değişikliği ve dq-web yeniden başlatmasıdır.

Aşama 3: `dq-sandbox` servisi compose'tan kaldırılır, `sandbox-net` silinir, dq-web bayrağı kapatılır. Kural: runner yoksa Sandbox A'ya dönülmez (fail closed). Sandbox A'ya dönüş yalnız admin kararı ve kayıtlı bir istisna ile yapılır. Veri kaybı olmaz.

Genel: her aşama `custom_scripts` verisini değiştirmez; veri göçü gerekmez. Compose değişikliğinden önce mevcut `docker-compose.yml` git'te saklanır.

## 9. Açık sorular

1. Airflow yolu bağlanacak mı? Tavsiye: evet, ama yalnız Aşama 3 tamamlandıktan sonra. Worker kodu doğrudan çalıştırmaz; runner'ı çağırır.
2. Ortak sunucuda iç ağ (`internal: true`) oluşturmaya yetki var mı, ve `ortak-db` ağıyla ilişkisi nedir? Tavsiye: ayrı `sandbox-net` oluşturulur. Ağ yöneticisinin onayı alınmadan dq-web compose değişikliği yapılmaz.
3. Kayıt sırasında modül gövdesinin `exec` edilmesi kaldırılsın mı? Bu davranış değişikliğidir. Tavsiye: evet. Kayıt yalnız AST ve tanım kontrolü yapsın.

## 10. Ekler: okunan dosyalar

- `dq/engine.py`: 1-11 (importlar), 373-480 (`custom_script_assertion`), 484 (`CheckEngine` başlangıcı, referans).
- `routers/scripts.py`: 1-171 (özellikle 45-77, 100-127, 144-171).
- `tests/test_sandbox_sertlestirme.py`: 1-79 (10 test).
- `tests/test_guvenlik_son.py`: 1-102 (4 test; sandbox değil).
- `tests/test_scripts_cursor.py`: 1-28.
- `docker-compose.yml`: 1-55. `Dockerfile`: 1-38 (`CMD` satır 38). `.dockerignore`.
- `dq/config.py`: 61-78 (`_get_custom_script_fn`), 83-104 (`_ASSERTION_MAP`).
- `auth.py`: 206-211 (sabitler), 230-265 (`yetki_kapisi`).
- `main.py`: 1-53.
- `secrets_loader.py`: 1-17.
- `templates/script_form.html`: 116 (not), 150-185 (`fetch` ve `innerHTML`).
- `README.md`: 385-415 (güvenlik örnekleri). `docs/ARCHITECTURE.md`: 22-27, 88-92.
- Fonksiyon ve dosya adları `grep` ile doğrulandı. Önerilen yeni adlar (`dq-sandbox`, `sandbox-net`, `DQ_SCRIPT_RUNNER`, `DQ_SANDBOX_TOKEN`) bu depoda henüz yoktur.
