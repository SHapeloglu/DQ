"""
test_sifre_kasasi.py — sifre_kasasi modülü ve sifrele_mevcut taşıma betiği.

Veritabanı gerekmez: taşıma testleri MagicMock bağlantısı kullanır.
Anahtar her testte monkeypatch ile ayarlanır; gerçek ortam anahtarına bağımlı değildir.
"""
import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet

import sifre_kasasi
from sifre_kasasi import (
    AnahtarHatasi, decrypt_secret, encrypt_secret, is_encrypted, PREFIX,
)


@pytest.fixture
def anahtar(monkeypatch):
    """Geçerli bir Fernet anahtarını DQ_ENC_KEY olarak ayarlar ve döndürür."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DQ_ENC_KEY", key)
    return key


def _tasima_betigi():
    """scripts/sifrele_mevcut.py modülünü dosya yolundan yükler (scripts paketi yok)."""
    yol = Path(__file__).resolve().parent.parent / "scripts" / "sifrele_mevcut.py"
    spec = importlib.util.spec_from_file_location("sifrele_mevcut", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _baglanti(kaynak_satirlari, alert_satirlari):
    """Sahte bağlantı: SELECT sırasına göre bu satırları döndürür; yazma çağrılarını izler."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.side_effect = [kaynak_satirlari, alert_satirlari]
    return conn, cur


# ── Gidiş-dönüş ve öneksiz değer ──────────────────────────────────────────────

def test_gidis_donus_esit(anahtar):
    sifreli = encrypt_secret("cok-gizli-parola")
    assert decrypt_secret(sifreli) == "cok-gizli-parola"


def test_ongeksiz_deger_oldugu_gibi_doner(anahtar):
    # Geriye uyum: eski kayıtlar düz metin olarak okunmaya devam eder.
    assert decrypt_secret("eski-duz-parola") == "eski-duz-parola"


def test_ongeksiz_deger_anahtar_olmadan_da_okunur(monkeypatch):
    monkeypatch.delenv("DQ_ENC_KEY", raising=False)
    assert decrypt_secret("eski-duz-parola") == "eski-duz-parola"


def test_enc_oneki_cozulur(anahtar):
    token = Fernet(anahtar.encode()).encrypt(b"deger").decode()
    assert decrypt_secret(PREFIX + token) == "deger"


def test_sifreli_cikti_orijinali_icermez(anahtar):
    orijinal = "parola-XYZ-12345"
    sifreli = encrypt_secret(orijinal)
    assert sifreli.startswith(PREFIX)
    assert is_encrypted(sifreli)
    assert orijinal not in sifreli


def test_anahtar_yokken_encrypt_hata_verir(monkeypatch):
    monkeypatch.delenv("DQ_ENC_KEY", raising=False)
    with pytest.raises(AnahtarHatasi):
        encrypt_secret("parola")


def test_gecersiz_anahtar_encrypt_hata_verir(monkeypatch):
    monkeypatch.setenv("DQ_ENC_KEY", "bu-fernet-degil")
    with pytest.raises(AnahtarHatasi):
        encrypt_secret("parola")


def test_yanlis_anahtarla_cozme_hata_verir(monkeypatch, anahtar):
    sifreli = encrypt_secret("parola")
    monkeypatch.setenv("DQ_ENC_KEY", Fernet.generate_key().decode())
    with pytest.raises(ValueError):
        decrypt_secret(sifreli)


# ── Taşıma betiği ─────────────────────────────────────────────────────────────

def test_tasima_dry_run_yazma_yapmaz(anahtar):
    betik = _tasima_betigi()
    conn, cur = _baglanti(
        [{"id": 1, "config": json.dumps({"host": "h", "password": "duz"})}],
        [{"id": 1, "smtp_pass": "duz-smtp"}],
    )
    rapor = betik.calistir(conn, uygula=False)

    assert rapor == {"sources.config (password)": 1, "alert_settings.smtp_pass": 1}
    sorgular = [c.args[0] for c in cur.execute.call_args_list]
    assert not any(s.lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE")) for s in sorgular)
    conn.commit.assert_not_called()


def test_tasima_uygula_sifreli_yazar(anahtar):
    betik = _tasima_betigi()
    conn, cur = _baglanti(
        [{"id": 7, "config": json.dumps({"host": "h", "password": "kaynak-parola"})}],
        [{"id": 1, "smtp_pass": "smtp-parola"}],
    )
    betik.calistir(conn, uygula=True)

    yazilanlar = [c.args[1] for c in cur.execute.call_args_list if c.args[0].startswith("UPDATE")]
    assert len(yazilanlar) == 2
    yazilan_config = json.loads(yazilanlar[0][0])
    assert yazilan_config["password"].startswith(PREFIX)
    assert "kaynak-parola" not in json.dumps(yazilan_config)
    assert yazilanlar[1][0].startswith(PREFIX)
    assert "smtp-parola" not in yazilanlar[1][0]
    conn.commit.assert_called_once()


def test_tasima_zaten_sifreli_olani_atlar(anahtar):
    betik = _tasima_betigi()
    zaten = encrypt_secret("var-olan")
    conn, _ = _baglanti(
        [{"id": 1, "config": json.dumps({"password": zaten})}],
        [],
    )
    assert betik.calistir(conn, uygula=False) == {
        "sources.config (password)": 0, "alert_settings.smtp_pass": 0,
    }


# ── Anahtar monkeypatch ile ayarlanır ─────────────────────────────────────────

def test_anahtar_monkeypatch_ile_degisir(monkeypatch):
    a = Fernet.generate_key().decode()
    b = Fernet.generate_key().decode()
    monkeypatch.setenv("DQ_ENC_KEY", a)
    sifreli = encrypt_secret("x")
    monkeypatch.setenv("DQ_ENC_KEY", b)
    assert sifreli != encrypt_secret("x")
    with pytest.raises(ValueError):
        decrypt_secret(sifreli)


# ── Bağlayıcı katmanı: çözülmüş değer gider ───────────────────────────────────

def test_build_connector_sifreli_parolayi_cozer(anahtar, monkeypatch):
    from dq import connectors

    alinan = {}

    class SahteBaglayici:
        def __init__(self, **kwargs):
            alinan.update(kwargs)

    monkeypatch.setitem(connectors.CONNECTOR_REGISTRY, "sahte", SahteBaglayici)
    connectors.build_connector({"type": "sahte", "host": "h",
                                "password": encrypt_secret("gizli")})
    assert alinan["password"] == "gizli"
