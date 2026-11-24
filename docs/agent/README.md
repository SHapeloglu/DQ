# Ajan iş akışı

Bu klasör, DQ deposunda ajanlarla yapılan işlerin ortak kurallarını tutar. Üç şablon içerir: görev kartı, ledger ve doğrulayıcı prompt'u.

## Roller

| Rol | Ne yapar | Ne yapmaz |
|---|---|---|
| Lider | Görevi böler, görev kartı yazar, ledger'ı günceller, bulguları birleştirir | Kod yazmaz |
| Uygulayıcı | Tek bir görev kartıyla, kendi worktree'sinde çalışır | Kart dışındaki dosyaya yazmaz, kapsam dışı işi kendi başına yapmaz |
| Doğrulayıcı | Bulguyu yeniden üretmeye çalışır, dosya:satır kanıtı ister | Uygulayıcının bağlamını ve gerekçesini kabul etmez |
| Sen | Birleştirme kararını verir | Ara adımlar için onay gerekmez |

## Akış

1. Lider işi parçalar ve her parça için `GOREV_KARTI.md` şablonuna göre kart yazar. Her kart ledger'a bir satır olarak girer.
2. Uygulayıcı kendi worktree'sinde çalışır. Yazabildiği yollar kartta yazılı olanlarla sınırlıdır.
3. Kapsam dışı bir ihtiyaç doğarsa uygulayıcı işi durdurmaz; ledger'da "kapsam dışı talep" olarak işaretler ve yapmaz.
4. Uygulayıcı bulgularını kartta tanımlı çıktı şemasına göre yazar.
5. Doğrulayıcı, `DOGRULAYICI.md` içindeki kurallara göre her bulguyu kontrol eder. Kanıtı olmayan ya da yeniden üretilemeyen bulgu reddedilir ve ledger'a nedeniyle birlikte geri yazılır.
6. Otomatik kapılar geçmeden birleştirme adayı olmaz: `py_compile`, `pytest`, diff'in yalnızca kart kapsamında olması, her onaylı bulgunun kanıt satırı.
7. Sen birleştirmeye bakarsın. Birleştirme tek insan kapısıdır.
8. Canlıya etki eden işler (`docker compose up -d --build`, sunucuda `git pull`, veritabanı değişikliği) ayrı bir kapıdır ve ayrıca onay ister.

## Kurallar

- Aynı dosyaya aynı anda iki uygulayıcı yazmaz. Kartlar dosya kümelerine göre ayrılır.
- Ledger tek kaynak doğrudur. Durum ledger'da değişir, sohbette değil.
- Yarım kalan iş worktree'de kalır. Lider ya devralır ya iptal eder.
- Gizli değer hiçbir çıktıya, karta, ledger'a ya da bulguya yazılmaz; yalnızca değişken adı yazılır.
- Kart ve ledger dosyaları commit'lenmez; görev bitince ledger'dan karar satırı özetlenir.
