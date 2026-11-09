"""
sifre_kasasi.py — Kaynak ve SMTP parolaları için uygulama katmanı şifreleme.

Şifreli değer `enc:` öneki + Fernet belirteci biçimindedir. Öneksiz değer düz metin
kabul edilir (geriye uyum: mevcut kayıtlar taşınana kadar çalışmaya devam eder).

Anahtar: DQ_ENC_KEY ortam değişkeni (Fernet anahtarı, `Fernet.generate_key()`).
  - Anahtar yoksa şifreleme (encrypt) açık hata verir; düz metin ASLA yazılmaz (fail closed).
  - Okuma (decrypt) öneksiz değerlerde anahtar gerektirmez.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

PREFIX = "enc:"
ENV_ANAHTAR = "DQ_ENC_KEY"


class AnahtarHatasi(RuntimeError):
    """DQ_ENC_KEY eksik ya da geçersiz. Mesaj hiçbir zaman parola ya da anahtar içermez."""


def _fernet() -> Fernet:
    """DQ_ENC_KEY'den Fernet nesnesi üretir. Anahtar yoksa ya da bozuksa AnahtarHatasi fırlatır."""
    anahtar = os.getenv(ENV_ANAHTAR, "").strip()
    if not anahtar:
        raise AnahtarHatasi(
            f"{ENV_ANAHTAR} tanımlı değil; parola şifrelenemez. "
            "Düz metin yazılmadı. .env dosyasına Fernet anahtarı ekleyin."
        )
    try:
        return Fernet(anahtar.encode("ascii"))
    except (ValueError, TypeError):
        raise AnahtarHatasi(f"{ENV_ANAHTAR} geçerli bir Fernet anahtarı değil.") from None


def is_encrypted(value) -> bool:
    """Değer `enc:` önekiyle başlıyorsa True döner."""
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt_secret(plain: str) -> str:
    """Düz metin parolayı `enc:` önekli Fernet belirtecine çevirir. Anahtar yoksa AnahtarHatasi fırlatır."""
    if not isinstance(plain, str):
        raise TypeError("Şifrelenecek değer metin olmalı.")
    belirtec = _fernet().encrypt(plain.encode("utf-8")).decode("ascii")
    return PREFIX + belirtec


def decrypt_secret(value):
    """
    `enc:` önekli değeri çözer. Öneksiz değer (ya da metin olmayan değer) olduğu gibi döner.
    Anahtar yanlış ya da veri bozuksa ValueError fırlatır (değer mesaja yazılmaz).
    """
    if not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Şifreli değer çözülemedi: anahtar yanlış ya da veri bozuk.") from None


def encrypt_config_password(config: dict) -> dict:
    """
    Bağlantı sözlüğündeki `password` alanını şifreler (yerinde değiştirir ve döner).
    Boş ya da zaten şifreli değerlere dokunmaz.
    """
    parola = config.get("password")
    if isinstance(parola, str) and parola and not is_encrypted(parola):
        config["password"] = encrypt_secret(parola)
    return config


def decrypt_config_password(config: dict) -> dict:
    """Bağlantı sözlüğündeki `password` alanını çözer (yerinde değiştirir ve döner)."""
    if "password" in config:
        config["password"] = decrypt_secret(config["password"])
    return config
