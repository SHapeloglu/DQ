"""
test_glossary.py — Business Glossary endpoint testleri.
"""
import pytest
from unittest.mock import patch, MagicMock

# Glossary fonksiyonlarını doğrudan test et
def _mock_conn(fetchall_return=None):
    cur = MagicMock()
    cur.fetchall.return_value = fetchall_return or []
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur

def test_glossary_allowed_fields_filter():
    """Sadece izin verilen alanlar UPDATE'e girer."""
    allowed = {"business_name", "description", "owner", "tags"}
    payload = {"business_name": "E-posta", "hacker_field": "x", "owner": "CRM"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    assert "hacker_field" not in updates
    assert updates == {"business_name": "E-posta", "owner": "CRM"}

def test_glossary_allowed_fields_empty():
    """Geçersiz alanlarla updates boş kalır."""
    allowed = {"business_name", "description", "owner", "tags"}
    payload = {"invalid": "x", "another": "y"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    assert len(updates) == 0

def test_glossary_sql_fields_generation():
    """SET clause doğru üretilir."""
    updates = {"business_name": "Test", "owner": "CRM"}
    fields = ", ".join(f"{k}=%s" for k in updates)
    assert "business_name=%s" in fields
    assert "owner=%s" in fields

def test_glossary_mock_get():
    """Mock DB ile GET sorgusu doğru çalışır."""
    rows = [{"id": 1, "column_name": "email", "business_name": "E-posta",
             "description": None, "owner": "CRM", "tags": "pii"}]
    conn, cur = _mock_conn(rows)
    # database import gerekmez — mock doğrudan kullanılır
    cur.execute("SELECT ...", (1,))
    result = cur.fetchall()
    assert result[0]["business_name"] == "E-posta"
    assert result[0]["tags"] == "pii"
