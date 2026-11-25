# Veritabanı ayarlarında sabit varsayılan kimlik bilgisi (root/root) bulunmamalı.
# DB_USER veya DB_PASSWORD yoksa bağlantı açılmadan önce açık bir hata verilmeli.
import pytest
from unittest.mock import patch


def test_varsayilan_kimlik_bilgisi_yok(monkeypatch):
    """DB_USER/DB_PASSWORD tanımsızken ayar sözlüğünde 'root' kalmamalı."""
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    import importlib, database
    importlib.reload(database)
    assert database.DB_CONFIG["user"] != "root"
    assert database.DB_CONFIG["password"] != "root"


def test_parola_yoksa_acik_hata(monkeypatch):
    """Parola boşsa pymysql'e gitmeden RuntimeError fırlamalı."""
    import database
    cfg = dict(database.DB_CONFIG, user="uygulama", password="")
    pool = database._DBPool.__new__(database._DBPool)
    pool._config = cfg
    with patch("database.pymysql.connect") as mock_connect:
        with pytest.raises(RuntimeError, match="DB_PASSWORD"):
            pool._new_conn()
        mock_connect.assert_not_called()
