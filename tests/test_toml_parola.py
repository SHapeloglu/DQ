# TOML içe aktarmada [source] parolası DB'ye düz metin yazılmamalı.
import json
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

import sifre_kasasi
from toml_import import toml_to_db


@pytest.fixture(autouse=True)
def _anahtar(monkeypatch):
    monkeypatch.setenv("DQ_ENC_KEY", Fernet.generate_key().decode())


def _yazilan_config(conn) -> dict:
    """sources INSERT'ine giden config JSON'unu döndürür."""
    cur = conn.cursor.return_value.__enter__.return_value
    for call in cur.execute.call_args_list:
        sql, params = call.args[0], call.args[1]
        if "INSERT INTO sources" in sql:
            return json.loads(params[2])
    raise AssertionError("sources INSERT bulunamadı")


def test_duz_parola_sifrelenir():
    conn = MagicMock()
    raw = {"source": {"type": "postgres", "host": "db", "user": "u", "password": "cok-gizli-123"},
           "checks": []}
    toml_to_db(raw, conn)
    cfg = _yazilan_config(conn)
    assert cfg["password"].startswith(sifre_kasasi.PREFIX)
    assert "cok-gizli-123" not in json.dumps(cfg)
    assert sifre_kasasi.decrypt_secret(cfg["password"]) == "cok-gizli-123"


def test_secret_referansi_cozulur_ve_sifrelenir(monkeypatch):
    conn = MagicMock()
    raw = {"source": {"type": "mysql", "host": "db", "password": "secret:DB_PASSWORD"}, "checks": []}
    with patch("toml_import.get_secret", return_value="gercek-parola") as mock_get:
        toml_to_db(raw, conn)
    mock_get.assert_called_once_with("DB_PASSWORD")
    cfg = _yazilan_config(conn)
    assert "secret:" not in json.dumps(cfg)
    assert "gercek-parola" not in json.dumps(cfg)
    assert sifre_kasasi.decrypt_secret(cfg["password"]) == "gercek-parola"


def test_tanimsiz_secret_referansi_hata_verir():
    conn = MagicMock()
    raw = {"source": {"type": "mysql", "host": "db", "password": "secret:YOK_ANAHTAR"}, "checks": []}
    with patch("toml_import.get_secret", return_value=""):
        with pytest.raises(ValueError, match="YOK_ANAHTAR"):
            toml_to_db(raw, conn)
    # Hata durumunda sources'a hiçbir kayıt yazılmamış olmalı.
    cur = conn.cursor.return_value.__enter__.return_value
    assert not any("INSERT INTO sources" in c.args[0] for c in cur.execute.call_args_list)


def test_anahtar_yoksa_duz_parola_yazilmaz(monkeypatch):
    monkeypatch.delenv("DQ_ENC_KEY", raising=False)
    conn = MagicMock()
    raw = {"source": {"type": "postgres", "host": "db", "password": "gizli"}, "checks": []}
    with pytest.raises(Exception):
        toml_to_db(raw, conn)
    cur = conn.cursor.return_value.__enter__.return_value
    assert not any("INSERT INTO sources" in c.args[0] for c in cur.execute.call_args_list)
