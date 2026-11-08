# Bu dosya: dq.engine.cross_table_check() fonksiyonunu test eder. İki tablo arasında sayı karşılaştırması (eşit, küçük, büyük, yüzde tolerans) yapılır.
# Veritabanı gerekmez: make_connector ile sahte bağlantı üretilir. Testler pytest ile çalışır; 'assert' başarısızsa test kırmızı olur.
from unittest.mock import MagicMock, patch
from dq.engine import cross_table_check


def make_connector(return_value):
    """
    Sahte (MagicMock) bir veritabanı bağlantısı üretir. execute() çağrılınca [{"val": return_value}] döner.
    Böylece 'diğer tablodan gelen sayı' sabit bir değer olur ve testler gerçek DB'ye ihtiyaç duymaz.
    """
    conn = MagicMock()
    conn.execute.return_value = [{"val": return_value}]
    conn.__enter__ = lambda s: conn
    conn.__exit__ = MagicMock(return_value=False)
    return conn


class TestCrossTableCheck:
    """
    cross_table_check() fonksiyonunun iki tablo arasındaki karşılaştırmayı doğru yaptığını test eder.
    fn(kaynak_değer) şeklinde çağrılır; kaynak_değer ilk tablodan gelen sayıdır, diğer tablonun sayısı make_connector ile verilir.
    Karşılaştırıcılar: equals (eşit), less_than (küçük), greater_than (büyük), within_pct (yüzde tolerans içinde).
    """
    def test_equals_pass(self):
        """Kaynak 100, hedef 100: eşitlik kontrolü geçmeli (True)."""
        conn_b = make_connector(100)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="equals")
        assert fn(100) is True

    def test_equals_fail(self):
        """Kaynak 100, hedef 200: eşitlik kontrolü başarısız olmalı (False)."""
        conn_b = make_connector(200)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="equals")
        assert fn(100) is False

    def test_less_than_pass(self):
        """Kaynak 100, hedef 200: 'kaynak hedeften küçük' koşulu sağlanır (True)."""
        conn_b = make_connector(200)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="less_than")
        assert fn(100) is True

    def test_less_than_fail(self):
        """Kaynak 100, hedef 50: 'kaynak hedeften küçük' koşulu sağlanmaz (False)."""
        conn_b = make_connector(50)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="less_than")
        assert fn(100) is False

    def test_greater_than_pass(self):
        """Kaynak 100, hedef 50: 'kaynak hedeften büyük' koşulu sağlanır (True)."""
        conn_b = make_connector(50)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="greater_than")
        assert fn(100) is True

    def test_within_pct_pass(self):
        """Tolerans %5. Kaynak 104, hedef 100: fark %4 olduğu için kabul edilir (True)."""
        conn_b = make_connector(100)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="within_pct", tolerance=5.0)
        assert fn(104) is True

    def test_within_pct_fail(self):
        """Tolerans %5. Kaynak 110, hedef 100: fark %10 olduğu için reddedilir (False)."""
        conn_b = make_connector(100)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="within_pct", tolerance=5.0)
        assert fn(110) is False

    def test_empty_result_fails(self):
        """Hedef tablo sorgusu boş sonuç dönerse kontrol hata vermeden False döner. Tablo bulunamadığında yanlışlıkla 'geçti' sayılmasın diye."""
        conn_b = MagicMock()
        conn_b.execute.return_value = []
        conn_b.__enter__ = lambda s: conn_b
        conn_b.__exit__ = MagicMock(return_value=False)
        fn = cross_table_check(conn_b, "SELECT COUNT(*) FROM b", comparator="equals")
        assert fn(100) is False
