"""
scripts/sifrele_mevcut.py — Mevcut düz metin parolaları şifreler (tek seferlik taşıma).

Hedefler:
  - sources.config (JSON) içindeki "password" alanı
  - alert_settings.smtp_pass

Kullanım (proje kökünden):
  python scripts/sifrele_mevcut.py             # dry-run (varsayılan): yalnız sayım yapar, yazmaz
  python scripts/sifrele_mevcut.py --uygula    # gerçekten yazar

Güvenlik:
  - Değerler hiçbir çıktıya yazılmaz; yalnız tablo/kolon ve kayıt sayısı basılır.
  - DQ_ENC_KEY tanımlı değilse betik durur (düz metin bırakılmaz).
  - --uygula çalışmadan önce yedek uyarısı basılır ve 5 saniye beklenir.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sifre_kasasi import ENV_ANAHTAR, encrypt_secret, is_encrypted  # noqa: E402

# alert_settings.smtp_pass kolonu database.py / main_extensions.py'de VARCHAR(200).
SMTP_PASS_KOLON_UZUNLUGU = 200
MYSQL_TABLO_YOK = 1146


def _kaynak_adaylari(conn) -> list[tuple[int, dict]]:
    """Şifrelenmemiş, boş olmayan `password` içeren sources.config satırlarını döner."""
    adaylar = []
    with conn.cursor() as cur:
        cur.execute("SELECT id, config FROM sources")
        for satir in cur.fetchall():
            config = satir["config"]
            if isinstance(config, str):
                config = json.loads(config)
            parola = config.get("password")
            if isinstance(parola, str) and parola and not is_encrypted(parola):
                adaylar.append((satir["id"], config))
    return adaylar


def _alert_adaylari(conn) -> list[tuple[int, str]]:
    """Şifrelenmemiş, boş olmayan alert_settings.smtp_pass değerlerini döner. Tablo yoksa boş liste."""
    adaylar = []
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT id, smtp_pass FROM alert_settings")
        except Exception as e:
            if e.args and e.args[0] == MYSQL_TABLO_YOK:
                return []
            raise
        for satir in cur.fetchall():
            parola = satir["smtp_pass"]
            if isinstance(parola, str) and parola and not is_encrypted(parola):
                adaylar.append((satir["id"], parola))
    return adaylar


def calistir(conn, uygula: bool = False) -> dict[str, int]:
    """
    Taşımayı çalıştırır. `uygula=False` ise yalnız SELECT yapar ve kayıt sayılarını döner.
    `uygula=True` ise adayları şifreleyip UPDATE eder ve commit eder.
    Dönüş: {"tablo.kolon": kayıt_sayısı}. Değer içermez.
    """
    kaynaklar = _kaynak_adaylari(conn)
    alertler = _alert_adaylari(conn)

    # Sığma kontrolü: yazmadan önce, şifreli değer kolona sığmıyorsa dur (değer yazdırılmaz).
    for _, parola in alertler:
        if len(encrypt_secret(parola)) > SMTP_PASS_KOLON_UZUNLUGU:
            raise RuntimeError(
                f"alert_settings.smtp_pass VARCHAR({SMTP_PASS_KOLON_UZUNLUGU}); "
                "şifreli değer bu sınıra sığmıyor. Önce kolonu genişletin, sonra tekrar deneyin."
            )

    rapor = {
        "sources.config (password)": len(kaynaklar),
        "alert_settings.smtp_pass": len(alertler),
    }
    if not uygula:
        return rapor

    with conn.cursor() as cur:
        for kaynak_id, config in kaynaklar:
            config["password"] = encrypt_secret(config["password"])
            cur.execute("UPDATE sources SET config = %s WHERE id = %s",
                        (json.dumps(config), kaynak_id))
        for alert_id, parola in alertler:
            cur.execute("UPDATE alert_settings SET smtp_pass = %s WHERE id = %s",
                        (encrypt_secret(parola), alert_id))
    conn.commit()
    return rapor


def main(argv: list[str] | None = None) -> int:
    """Komut satırı girişi. Başarıda 0, hatada 1 döner."""
    p = argparse.ArgumentParser(description="Düz metin kaynak/SMTP parolalarını şifreler.")
    p.add_argument("--uygula", action="store_true",
                   help="Gerçekten yazar. Verilmezse dry-run yapılır (yazmaz).")
    args = p.parse_args(argv)

    if not os.getenv(ENV_ANAHTAR, "").strip():
        print(f"HATA: {ENV_ANAHTAR} tanımlı değil. Betik durdu; hiçbir şey yazılmadı.", file=sys.stderr)
        return 1

    from database import get_conn, release_conn

    if args.uygula:
        print("UYARI: Yazmadan önce veritabanının YEDEĞİNİ alın (mysqldump).")
        print("Yedek yoksa şimdi Ctrl+C ile durdurun. 5 saniye bekleniyor...")
        time.sleep(5)
    else:
        print("DRY-RUN: hiçbir şey yazılmayacak. Gerçek taşıma için --uygula verin.")

    conn = get_conn()
    try:
        rapor = calistir(conn, uygula=args.uygula)
    except (RuntimeError, ValueError) as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    finally:
        release_conn(conn)

    for hedef, sayi in rapor.items():
        print(f"{hedef}: {sayi} kayıt {'şifrelendi' if args.uygula else 'şifrelenecek'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
