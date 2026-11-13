# Görev kartı şablonu

Lider her uygulayıcı için bu şablonu doldurur. Kart eksikse uygulayıcı işe başlamaz.

```markdown
## Görev: <kısa ad>

- **Kimlik:** <ledger satır no>, <tarih>
- **Amaç:** <tek cümle; ne düzeltilecek ya da incelenecek>
- **Worktree:** <yol ve dal adı>

### Kapsam

- **Okunabilir yollar:** <dosya ya da klasör listesi>
- **Yazılabilir yollar:** <dosya ya da klasör listesi; boşsa yazma yok>
- **İzinli komutlar:** <tam komutlar; ör. `python -m py_compile routers/scripts.py`, `pytest tests/test_scripts_cursor.py -q`>
- **Yasak:** <açıkça yasaklananlar; ör. commit, push, pull, docker, sunucuya bağlanma>

### Kapsam dışı talep

Kapsam dışı bir şey gerekirse yapmayın. Ledger'a "kapsam dışı talep" satırı yazın: ne gerekiyor, neden, hangi dosya.

### Çıktı şeması

Her bulgu ya da değişiklik için:

- **Dosya:** <yol>
- **Satır:** <başlangıç-bitiş>
- **Alıntı:** <satırın birebir metni>
- **İddia:** <tek cümle>
- **Kanıt komutu:** <bulguyu yeniden üretecek komut>
- **Kanıt çıktısı:** <komutun çıktısından ilgili satır; gizli değer varsa maskele>
- **Önem:** kritik / yüksek / orta / düşük

Değişiklik yapıldıysa ayrıca: değişen dosyalar, `git diff --stat` çıktısı, izinli komutların sonucu.

### Bitiş ölçütü

- <ölçülebilir koşul; ör. "pytest tests/test_x.py geçiyor", "bulgu listesi tamam">
- Bitince ledger'da durum "doğrulamada" olarak işaretlenir.
```
