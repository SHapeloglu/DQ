"""
test_yetki.py — genel yetki kapısı (auth.yetki_kapisi) testleri.

conftest.py kapıyı tüm testler için açık bırakır; burada override kaldırılır ve gerçek davranış denenir.
"""
import pytest
from fastapi.testclient import TestClient

from unittest.mock import MagicMock

import auth as auth_modulu
from main import app
from auth import yetki_kapisi, create_token, HAS_AUTH_DEPS

pytestmark = pytest.mark.skipif(not HAS_AUTH_DEPS, reason="JWT bağımlılıkları yok")


@pytest.fixture
def istemci():
    """Yetki kapısı AÇIK (override'sız) istemci; test bitince override geri konur."""
    eski = app.dependency_overrides.pop(yetki_kapisi, None)
    yield TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    if eski is not None:
        app.dependency_overrides[yetki_kapisi] = eski


@pytest.fixture(autouse=True)
def _veritabani_taklidi(monkeypatch):
    """Kapı rolü veritabanından okur. Testlerde sahte kullanıcı kaydı kullanılır:
    "t-<rol>" adlı kullanıcı o rolle aktiftir; diğer adlar (ör. "silindi") bulunamaz."""
    def sahte(username):
        if username.startswith("t-"):
            return {"username": username, "role": username.split("-", 1)[1]}
        return None
    monkeypatch.setattr(auth_modulu, "_guncel_kullanici", sahte)


def _cerez(rol):
    """Verilen rolle geçerli bir dq_token çerezi üretir (sahte DB'de aynı rolle aktif kullanıcı)."""
    return {"dq_token": create_token({"sub": f"t-{rol}", "role": rol, "id": 1})}


def test_girissiz_sayfa_login_e_yonlenir(istemci):
    r = istemci.get("/dashboard")
    assert r.status_code == 307 and r.headers["location"] == "/login"


def test_girissiz_api_401(istemci):
    assert istemci.get("/api/results").status_code == 401
    assert istemci.get("/odata/Results").status_code == 401


def test_login_sayfasi_acik(istemci):
    r = istemci.get("/login")
    assert r.status_code == 200 and "/login/submit" in r.text


def test_viewer_yazamaz(istemci):
    r = istemci.post("/api/runs", json={}, cookies=_cerez("viewer"))
    assert r.status_code == 403


def test_viewer_okuyabilir_gecer_kapidan(istemci):
    # Kapıyı geçer (kapı 401/403/307 vermez); sonrası uygulama mantığıdır, sunucu hatası olabilir.
    r = istemci.get("/api/rule-library", cookies=_cerez("viewer"))
    assert r.status_code not in (401, 403, 307)


def test_editor_admin_uclarina_giremez(istemci):
    assert istemci.post("/admin/migrate", cookies=_cerez("editor")).status_code == 403
    assert istemci.get("/settings/alerts", cookies=_cerez("editor")).status_code == 403


def test_servis_anahtari_yalniz_api_yollarinda(istemci, monkeypatch):
    monkeypatch.setenv("DQ_API_TOKEN", "gizli-test-anahtari")
    b = {"X-DQ-Token": "gizli-test-anahtari"}
    assert istemci.get("/api/results", headers=b).status_code not in (401, 403, 307)
    assert istemci.get("/dashboard", headers=b).status_code == 307   # sayfa yollarında geçmez
    assert istemci.get("/api/results", headers={"X-DQ-Token": "yanlis"}).status_code == 401


def test_anahtar_tanimsizsa_makine_erisimi_kapali(istemci, monkeypatch):
    monkeypatch.delenv("DQ_API_TOKEN", raising=False)
    assert istemci.get("/api/results", headers={"X-DQ-Token": ""}).status_code == 401


def test_silinmis_kullanici_eski_tokenla_giremez(istemci):
    # Token süresi dolmamış olsa bile veritabanında kaydı yoksa erişim kapalı.
    cerez = {"dq_token": create_token({"sub": "silindi", "role": "admin", "id": 9})}
    assert istemci.get("/dashboard", cookies=cerez).status_code == 307
    assert istemci.get("/api/results", cookies=cerez).status_code == 401


def test_yetki_dusurulen_kullanici_veritabanina_gore_kisitlanir(istemci):
    # Token "admin" diyor ama veritabanındaki rol viewer: admin yolu reddedilir.
    cerez = {"dq_token": create_token({"sub": "t-viewer", "role": "admin", "id": 1})}
    assert istemci.get("/admin/users", cookies=cerez).status_code == 403


def test_alert_ayarlari_yalniz_admin(istemci):
    assert istemci.get("/api/alert-settings", cookies=_cerez("editor")).status_code == 403
    assert istemci.put("/api/alert-settings", json={"smtp_host": "x"}, cookies=_cerez("editor")).status_code == 403
    assert istemci.get("/api/alert-settings", cookies=_cerez("viewer")).status_code == 403
    assert istemci.get("/api/alert-settings", cookies=_cerez("admin")).status_code not in (401, 403, 307)


def test_servis_anahtari_alert_ayarlarina_giremez(istemci, monkeypatch):
    monkeypatch.setenv("DQ_API_TOKEN", "gizli-test-anahtari")
    b = {"X-DQ-Token": "gizli-test-anahtari"}
    assert istemci.put("/api/alert-settings", json={"smtp_host": "x"}, headers=b).status_code == 403


def test_alert_ayarlarinda_smtp_parolasi_maskelenir(istemci, monkeypatch):
    import routers.api as api_router
    cur = MagicMock()
    cur.fetchone.return_value = {"smtp_host": "smtp.ornek", "smtp_pass": "gizli-parola"}
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(api_router, "get_conn", lambda: conn)
    monkeypatch.setattr(api_router, "release_conn", lambda c: None)
    r = istemci.get("/api/alert-settings", cookies=_cerez("admin"))
    assert r.status_code == 200
    assert r.json()["smtp_pass"] == "********"
    assert "gizli-parola" not in r.text
