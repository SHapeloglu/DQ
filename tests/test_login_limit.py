# Giriş deneme sınırı: 5 hatalı denemeden sonra 5 dk kilit; kilitliyken şifre denenmez.
import pytest
from unittest.mock import MagicMock, patch
from urllib.parse import unquote_plus
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import auth


@pytest.fixture(autouse=True)
def _temiz_sayaç():
    auth._denemeler.clear()
    yield
    auth._denemeler.clear()


def _app():
    app = FastAPI()
    auth.register_auth_routes(app, templates=None, get_conn_fn=lambda: MagicMock())
    return TestClient(app, follow_redirects=False)


def test_bes_hatadan_sonra_kilit():
    anahtar = ("ali", "1.2.3.4")
    for _ in range(auth.LOGIN_MAX_DENEME - 1):
        auth._basarisiz_kaydet(anahtar, now=1000.0)
    assert auth._kilit_kalan_sn(anahtar, now=1000.0) == 0
    auth._basarisiz_kaydet(anahtar, now=1000.0)
    assert auth._kilit_kalan_sn(anahtar, now=1000.0) > 0


def test_kilit_suresi_dolunca_acilir():
    anahtar = ("ali", "1.2.3.4")
    for _ in range(auth.LOGIN_MAX_DENEME):
        auth._basarisiz_kaydet(anahtar, now=1000.0)
    assert auth._kilit_kalan_sn(anahtar, now=1000.0 + auth.LOGIN_KILIT_SN - 1) > 0
    assert auth._kilit_kalan_sn(anahtar, now=1000.0 + auth.LOGIN_KILIT_SN + 1) == 0


def test_pencere_disi_hatalar_sayilmaz():
    anahtar = ("ali", "1.2.3.4")
    for i in range(auth.LOGIN_MAX_DENEME - 1):
        auth._basarisiz_kaydet(anahtar, now=1000.0 + i)
    # Pencere dışında kalan bir hata yeni pencere başlatır; kilit olmaz.
    auth._basarisiz_kaydet(anahtar, now=1000.0 + auth.LOGIN_PENCERE_SN + 10)
    assert auth._kilit_kalan_sn(anahtar, now=1000.0 + auth.LOGIN_PENCERE_SN + 10) == 0


def test_kilitliyken_sifre_denenmez():
    client = _app()
    with patch("auth.ensure_users_table"), patch("auth.authenticate_user", return_value=None) as mock_auth:
        for _ in range(auth.LOGIN_MAX_DENEME):
            client.post("/login/submit", data={"username": "ali", "password": "x"})
        assert mock_auth.call_count == auth.LOGIN_MAX_DENEME
        r = client.post("/login/submit", data={"username": "ali", "password": "x"})
        assert r.status_code == 303
        assert "Çok fazla hatalı deneme" in unquote_plus(r.headers["location"])
        assert mock_auth.call_count == auth.LOGIN_MAX_DENEME  # kilitliyken çağrı yapılmadı


def test_basarili_giris_sayaci_sifirlar():
    client = _app()
    user = {"id": 1, "username": "ali", "role": "admin"}
    with patch("auth.ensure_users_table"):
        with patch("auth.authenticate_user", return_value=None):
            for _ in range(auth.LOGIN_MAX_DENEME - 1):
                client.post("/login/submit", data={"username": "ali", "password": "x"})
        with patch("auth.authenticate_user", return_value=user):
            r = client.post("/login/submit", data={"username": "ali", "password": "doğru"})
        assert r.status_code == 303 and r.headers["location"] == "/"
        assert auth._denemeler == {}


def test_kullanici_adi_buyuk_kucuk_harf_ayni_anahtar():
    client = _app()
    with patch("auth.ensure_users_table"), patch("auth.authenticate_user", return_value=None):
        for ad in ["Ali", "ALI", " ali "] * 2:
            client.post("/login/submit", data={"username": ad, "password": "x"})
    assert len(auth._denemeler) == 1
