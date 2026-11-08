"""
test_guvenlik_son.py — admin bootstrap parolası ve dq_token çerezinin secure bayrağı.

- DQ_ADMIN_PASSWORD yokken rastgele üretilen parola stderr'e tek satırda yazılır.
- DQ_ADMIN_PASSWORD verilmişse parola hiçbir çıktıda görünmez.
- DQ_COOKIE_SECURE yalnız 1/true/yes ile secure bayrağını açar.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth as auth_modulu
from auth import HAS_AUTH_DEPS

pytestmark = pytest.mark.skipif(not HAS_AUTH_DEPS, reason="JWT bağımlılıkları yok")


def _bos_admin_baglantisi():
    """users tablosunda admin satırı yokmuş gibi davranan sahte bağlantı."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.return_value = None
    return conn, cur


# ── Bootstrap admin parolası ──────────────────────────────────────────────────

def test_parola_uretilirse_stderr_a_gecici_olarak_yazilir(monkeypatch, capsys):
    monkeypatch.delenv("DQ_ADMIN_PASSWORD", raising=False)
    conn, cur = _bos_admin_baglantisi()

    auth_modulu.ensure_users_table(conn)

    err = capsys.readouterr().err
    satirlar = [s for s in err.splitlines() if "geçici admin parolası" in s]
    assert len(satirlar) == 1, err
    satir = satirlar[0]
    assert "geçici" in satir
    assert "ilk girişten sonra değiştirin" in satir

    # Satırdaki parola, kaydedilen hash ile eşleşmeli (gerçekten kullanılabilir).
    parola = satir.split("parolası: ", 1)[1].split(" — ", 1)[0]
    hashed = cur.execute.call_args_list[-1][0][1][2]
    assert auth_modulu.verify_password(parola, hashed)


def test_dq_admin_password_verilince_parola_yazdirilmaz(monkeypatch, capsys):
    gizli = "Gizli-Parola-7531"
    monkeypatch.setenv("DQ_ADMIN_PASSWORD", gizli)
    conn, _cur = _bos_admin_baglantisi()

    auth_modulu.ensure_users_table(conn)

    cikti = capsys.readouterr()
    assert gizli not in cikti.out
    assert gizli not in cikti.err
    assert "geçici" not in cikti.err


# ── dq_token secure bayrağı ───────────────────────────────────────────────────

@pytest.fixture
def giris_istemcisi(monkeypatch):
    """Yalnız login route'larını içeren minimal uygulama; DB ve kullanıcı doğrulaması sahte."""
    # register_auth_routes modül genelindeki _conn_fn'i değiştirir; test sonunda geri alınır.
    monkeypatch.setattr(auth_modulu, "_conn_fn", auth_modulu._conn_fn)
    monkeypatch.setattr(auth_modulu, "ensure_users_table", lambda conn: None)
    monkeypatch.setattr(
        auth_modulu, "authenticate_user",
        lambda conn, u, p: {"id": 1, "username": u, "role": "admin"},
    )
    app = FastAPI()
    auth_modulu.register_auth_routes(app, None, lambda: MagicMock())
    return TestClient(app, follow_redirects=False)


def _token_cerezi(istemci):
    yanit = istemci.post("/login/submit", data={"username": "admin", "password": "x"})
    assert yanit.status_code == 303
    cerezler = [h for h in yanit.headers.get_list("set-cookie") if h.startswith("dq_token=")]
    assert len(cerezler) == 1
    return cerezler[0]


@pytest.mark.parametrize("deger", ["1", "true", "YES"])
def test_cookie_secure_env_acikken_secure_yazilir(monkeypatch, giris_istemcisi, deger):
    monkeypatch.setenv("DQ_COOKIE_SECURE", deger)
    ozellikler = [p.strip().lower() for p in _token_cerezi(giris_istemcisi).split(";")]
    assert "secure" in ozellikler


def test_cookie_secure_ayarsizken_secure_yok(monkeypatch, giris_istemcisi):
    monkeypatch.delenv("DQ_COOKIE_SECURE", raising=False)
    cerez = _token_cerezi(giris_istemcisi)
    ozellikler = [p.strip().lower() for p in cerez.split(";")]
    assert "secure" not in ozellikler
    # Mevcut güvenlik bayrakları korunmalı.
    assert "httponly" in ozellikler
    assert "samesite=lax" in ozellikler
