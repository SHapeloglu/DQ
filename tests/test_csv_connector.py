"""CsvConnector regresyon testleri: SQL enjeksiyonu ve taban dizin (DQ_CSV_BASE) kısıtı."""
import pytest

duckdb = pytest.importorskip("duckdb")

from dq.connectors import CsvConnector


@pytest.fixture
def taban(tmp_path, monkeypatch):
    """DQ_CSV_BASE = tmp_path/base. CSV dosyaları bu dizin altında olmalı."""
    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setenv("DQ_CSV_BASE", str(base))
    return base


@pytest.fixture
def csv_yolu(taban):
    p = taban / "veri.csv"
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


def test_taban_tanimsizsa_kaynak_kapali(csv_yolu, monkeypatch):
    monkeypatch.delenv("DQ_CSV_BASE", raising=False)
    c = CsvConnector(csv_yolu)
    with pytest.raises(ValueError, match="DQ_CSV_BASE tanımlı değil"):
        c.connect()


def test_taban_disi_yol_reddedilir(tmp_path, taban):
    disari = tmp_path / "disari.csv"
    disari.write_text("id\n1\n", encoding="utf-8")
    c = CsvConnector(str(disari))
    with pytest.raises(ValueError, match="DQ_CSV_BASE dışında"):
        c.connect()


def test_dizin_gecisi_ile_cikis_reddedilir(tmp_path, taban):
    disari = tmp_path / "disari.csv"
    disari.write_text("id\n1\n", encoding="utf-8")
    gecisli = str(taban / ".." / "disari.csv")
    c = CsvConnector(gecisli)
    with pytest.raises(ValueError, match="DQ_CSV_BASE dışında"):
        c.connect()


def test_sembolik_baglanti_ile_cikis_reddedilir(tmp_path, taban):
    disari = tmp_path / "disari.csv"
    disari.write_text("id\n1\n", encoding="utf-8")
    baglanti = taban / "link.csv"
    baglanti.symlink_to(disari)
    c = CsvConnector(str(baglanti))
    with pytest.raises(ValueError, match="DQ_CSV_BASE dışında"):
        c.connect()
