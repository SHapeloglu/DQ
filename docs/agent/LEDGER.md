# Ledger

Tek kaynak doğru. Her görev bir satır. Durum yalnızca bu dosyada değişir.

## Durum değerleri

- `bekliyor`: kart yazıldı, uygulayıcı başlamadı
- `uygulamada`: uygulayıcı çalışıyor
- `kapsam-disi-talep`: uygulayıcı kapsam dışı bir şey istedi; lider karar verene kadar bekler
- `dogrulamada`: uygulayıcı bitirdi, doğrulayıcı bakıyor
- `reddedildi`: doğrulayıcı en az bir bulguyu kanıtsız ya da yeniden üretilemez buldu; nedeni satırda
- `birlestirmeye-hazir`: otomatik kapılar geçti, sen bakacaksın
- `birlestirildi`: sen onayladın
- `iptal`: vazgeçildi; nedeni yazılır

## Görevler

| No | Tarih | Görev | Rol | Worktree / dal | Yazılabilir yollar | Durum | Not |
|---|---|---|---|---|---|---|---|
| 1 | | | uygulayıcı | | | bekliyor | |

## Kapsam dışı talepler

| Görev no | Talep | Gerekçe | Karar | Karar tarihi |
|---|---|---|---|---|
| | | | | |

## Bulgular

| Bulgu no | Görev no | Dosya | Satır | Önem | Kanıt | Doğrulayıcı kararı | Not |
|---|---|---|---|---|---|---|---|
| | | | | | | onaylandı / reddedildi / belirsiz | |

## Otomatik kapılar (birleştirme öncesi)

| Görev no | py_compile | pytest | Diff kapsam içi | Her bulgu kanıtlı | Sonuç |
|---|---|---|---|---|---|
| | | | | | |
