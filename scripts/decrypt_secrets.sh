#!/bin/bash
# Şifreli secrets dosyasını çözer
# Kullanım: bash scripts/decrypt_secrets.sh
set -e
GPG_FILE="secrets/.env.secrets.gpg"
OUT_FILE="secrets/.env.secrets"
if [ ! -f "$GPG_FILE" ]; then
    echo "HATA: $GPG_FILE bulunamadı" >&2
    exit 1
fi
gpg --decrypt --yes --output "$OUT_FILE" "$GPG_FILE"
chmod 600 "$OUT_FILE"
echo "OK: $OUT_FILE oluşturuldu"
