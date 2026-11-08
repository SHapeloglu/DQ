"""
test_yetki.py — genel yetki kapısı (auth.yetki_kapisi) testleri.

conftest.py kapıyı tüm testler için açık bırakır; burada override kaldırılır ve gerçek davranış denenir.
"""
import pytest
from fastapi.testclient import TestClient

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


def _cerez(rol):
    """Verilen rolle geçerli bir dq_token çerezi üretir."""
    return {"dq_token": create_token({"sub": "t", "role": rol, "id": 1})}


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
