"""
test_scripts_devre_disi.py — özel script kodu web sürecinde çalıştırılmamalı.

Sandbox tamamlanana kadar (task.md 🔴, seçenek B) kayıt/düzenleme yalnızca sözdizimini
kontrol eder; /api/scripts/test 503 döner. Bu testler exec yolunun yeniden açılmadığını
ve sözdizimi kontrolünün çalıştığını doğrular.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import routers.scripts as scripts_router
from main import app

# Modül seviyesinde çalışsaydı exec hatası verecek kod. Çalıştırılmıyorsa kayıt başarılı olur.
CALISTIRILIRSA_HATA_VEREN_KOD = (
    "raise RuntimeError('kod calisti')\n"
    "def check(value):\n"
    "    return True\n"
)


@pytest.fixture
def db_mock(monkeypatch):
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(scripts_router, "get_conn", lambda: conn)
    monkeypatch.setattr(scripts_router, "release_conn", lambda c: None)
    return conn


def test_kayit_kodu_calistirmaz(db_mock):
    istemci = TestClient(app, raise_server_exceptions=True)
    yanit = istemci.post(
        "/scripts/new",
        data={"name": "t", "code": CALISTIRILIRSA_HATA_VEREN_KOD, "function_name": "check"},
        follow_redirects=False,
    )
    assert yanit.status_code == 303
    assert db_mock.commit.called


def test_kayit_sozdizimi_hatasini_yakalar(db_mock):
    istemci = TestClient(app, raise_server_exceptions=False)
    yanit = istemci.post(
        "/scripts/new",
        data={"name": "t", "code": "def check(:\n", "function_name": "check"},
        follow_redirects=False,
    )
    assert yanit.status_code == 400
    assert not db_mock.commit.called


def test_test_endpoint_devre_disi_ve_kodu_calistirmaz():
    istemci = TestClient(app, raise_server_exceptions=False)
    yanit = istemci.post(
        "/api/scripts/test",
        data={"code": CALISTIRILIRSA_HATA_VEREN_KOD, "function_name": "check", "test_value": "1"},
    )
    assert yanit.status_code == 503
    govde = yanit.json()
    assert govde["ok"] is False
    assert "devre dışı" in govde["error"]
