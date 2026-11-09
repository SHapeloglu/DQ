"""
test_scripts_cursor.py — /scripts sayfası pymysql ile çalışmalı.

Önceden `cursor(dictionary=True)` (mysql-connector sözdizimi) kullanılıyordu; pymysql
bunu kabul etmediği için sayfa 500 veriyordu. Bu test o regresyonu yakalar.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import routers.scripts as scripts_router
from main import app


def test_scripts_listesi_dictionary_argumani_kullanmaz(monkeypatch):
    cur = MagicMock()
    cur.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(scripts_router, "get_conn", lambda: conn)
    monkeypatch.setattr(scripts_router, "release_conn", lambda c: None, raising=False)

    istemci = TestClient(app, raise_server_exceptions=True)
    yanit = istemci.get("/scripts")
    assert yanit.status_code == 200
    for cagri in conn.cursor.call_args_list:
        assert "dictionary" not in cagri.kwargs
