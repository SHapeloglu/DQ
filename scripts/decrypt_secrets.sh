#!/bin/bash
# secrets/.env.secrets.gpg dosyasini GPG ile acip duz metin secrets/.env.secrets dosyasini olusturur.
# Calistirma: elle, proje klasorunden: bash scripts/decrypt_secrets.sh. Yollar calisma klasorune gore alinir.
# Gerekli: gpg kurulu ve sifreli dosyanin parolasi (gpg ekranda sorar).
# DIKKAT: cikti duz metin gizli bilgi icerir; git'e eklenmemeli. Uretilen dosya 600 izinlidir.
# DIKKAT: mevcut secrets/.env.secrets dosyasi sorulmadan uzerine yazilir.
# Şifreli secrets dosyasını çözer
# Kullanım: bash scripts/decrypt_secrets.sh
set -e
GPG_FILE="secrets/.env.secrets.gpg"
OUT_FILE="secrets/.env.secrets"
if [ ! -f "$GPG_FILE" ]; then
    echo "HATA: $GPG_FILE bulunamadı" >&2
    exit 1
fi
# --decrypt: sifreli dosyayi cozer. --yes: cikti dosyasi varsa sormadan uzerine yazar. Parolayi betik saklamaz; gpg sorar.
gpg --decrypt --yes --output "$OUT_FILE" "$GPG_FILE"
# Duz metin gizli dosyayi sadece sahibi okuyup yazabilsin (600).
chmod 600 "$OUT_FILE"
echo "OK: $OUT_FILE oluşturuldu"
