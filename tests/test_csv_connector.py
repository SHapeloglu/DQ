"""CsvConnector regresyon testleri: yol SQL metnine girmemeli (SQL enjeksiyonu)."""
import pytest

duckdb = pytest.importorskip("duckdb")

from dq.connectors import CsvConnector


@pytest.fixture
def csv_yolu(tmp_path):
    p = tmp_path / "veri.csv"
    p.write_text("id,name\n1,a\n2,b\n", encoding="utf-8")
    return str(p)


def test_normal_csv_okunur(csv_yolu):
    c = CsvConnector(csv_yolu)
    c.connect()
    try:
        sonuc = c.execute("SELECT COUNT(*) AS n FROM source")
        assert sonuc == [{"n": 2}]
    finally:
        c.close()


def test_yol_icine_sql_enjekte_edilemez(tmp_path, csv_yolu):
    hedef = tmp_path / "pwned_marker"
    # Yolu kapatıp ek bir CREATE TABLE ifadesi eklemeye çalışan yol.
    kotu_yol = csv_yolu + "'); CREATE TABLE pwned AS SELECT 42 AS x; --"
    c = CsvConnector(kotu_yol)
    with pytest.raises(Exception):
        c.connect()
    # Bağlantı kurulamadıysa tablo oluşturulmamış olmalı.
    assert c._conn is not None
    varlik = c._conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'pwned'"
    ).fetchone()
    assert varlik == (0,)
    c.close()
    assert not hedef.exists()
