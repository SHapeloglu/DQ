"""
test_parola_disari.py — parolanın dışa aktarımda sızmadığını ve düzenlemede korunduğunu doğrular.
"""
import json
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import routers.sources as sources_router
from extensions import checks_to_toml
from main import app


def test_toml_disa_aktarim_parola_icermez():
    kaynak = {
        "name": "ornek",
        "type": "postgres",
        "config": json.dumps({"host": "db.ornek", "port": 5432,
                              "user": "u", "password": "enc:GIZLI-SIFRELI-DEGER"}),
    }
    cikti = checks_to_toml(kaynak, [])
    assert "GIZLI" not in cikti
    assert "enc:" not in cikti
    assert "password =" not in cikti
    assert "password dışa aktarılmadı" in cikti
    assert 'host = "db.ornek"' in cikti


def test_toml_parolasiz_kaynakta_uyari_yok():
    kaynak = {"name": "csv", "type": "csv",
              "config": json.dumps({"path": "/veri/a.csv"})}
    cikti = checks_to_toml(kaynak, [])
    assert "password dışa aktarılmadı" not in cikti


@pytest.fixture
def istemci(monkeypatch):
    monkeypatch.setattr(sources_router, "release_conn", lambda c: None)
    return TestClient(app, follow_redirects=False)


def _sahte_baglanti(mevcut_config):
    """Kaynak satırını döndüren sahte bağlantı; execute çağrılarını yakalar."""
    cur = MagicMock()
    cur.fetchone.return_value = {"config": json.dumps(mevcut_config)}
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


def _guncelleme_configi(cur):
    for cagri in cur.execute.call_args_list:
        sorgu = cagri.args[0]
        if sorgu.strip().upper().startswith("UPDATE SOURCES"):
            return json.loads(cagri.args[1][2])
    raise AssertionError("UPDATE sorgusu bulunamadı")


def test_duzenlemede_parola_bos_ise_mevcut_korunur(istemci, monkeypatch):
    conn, cur = _sahte_baglanti({"host": "eski", "password": "enc:MEVCUT"})
    monkeypatch.setattr(sources_router, "get_conn", lambda: conn)
    yanit = istemci.post("/sources/1/edit", data={
        "name": "ornek", "type": "postgres", "host": "yeni",
        "port": "5432", "database": "d", "user": "u", "password": "",
    })
    assert yanit.status_code == 303
    config = _guncelleme_configi(cur)
    assert config["host"] == "yeni"
    assert config["password"] == "enc:MEVCUT"


def test_duzenlemede_yeni_parola_girilirse_degisir(monkeypatch, istemci):
    monkeypatch.setenv("DQ_ENC_KEY", Fernet.generate_key().decode())
    conn, cur = _sahte_baglanti({"host": "eski", "password": "enc:ESKI"})
    monkeypatch.setattr(sources_router, "get_conn", lambda: conn)
    istemci.post("/sources/1/edit", data={
        "name": "ornek", "type": "postgres", "host": "eski",
        "port": "5432", "database": "d", "user": "u", "password": "YENI-PAROLA",
    })
    config = _guncelleme_configi(cur)
    assert config["password"].startswith("enc:")
    assert "YENI-PAROLA" not in json.dumps(config)
