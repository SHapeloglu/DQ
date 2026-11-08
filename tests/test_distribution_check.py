# Bu dosya: dq.engine.distribution_check() fonksiyonunu test eder. Beklenen ortalama ve standart sapma, verilen metin değerle tolerans yüzdesi içinde karşılaştırılır.
# Testler pytest ile çalışır; sınıf (class) ile gruplanmıştır ama pytest bunu otomatik bulur.
from dq.engine import distribution_check


class TestDistributionCheck:
    """
    distribution_check() fonksiyonunun, beklenen ortalama/standart sapma ile verilen değerleri tolerans içinde karşılaştırdığını test eder.
    Girdi metin olarak verilir: "ortalama" veya "ortalama,standart_sapma". Tolerans yüzdesi (tolerance_pct) sınırı belirler.
    Doğru (True) ya da yanlış (False) döner.
    """
    def test_mean_only_pass(self):
        """Sadece ortalama verildiğinde, beklenen değere yakın (tolerans içinde) değerin kabul edildiğini doğrular."""
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("100.0") is True

    def test_mean_only_fail(self):
        """Sadece ortalama verildiğinde, tolerans dışına çıkan (120, beklenen 100 ±%10) değerin reddedildiğini doğrular."""
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("120.0") is False

    def test_mean_and_std_pass(self):
        """Ortalama ve standart sapma birlikte verilip ikisi de tolerans içindeyse kabul edildiğini doğrular."""
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("100.0,10.0") is True

    def test_mean_and_std_fail_on_std(self):
        """Ortalama doğru olsa bile standart sapma (15 - beklenen 10) toleransın dışındaysa reddedildiğini doğrular. Standart sapmanın da kontrol edildiğini gösterir."""
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=5.0)
        assert fn("100.0,15.0") is False

    def test_mean_and_std_fail_on_mean(self):
        """Standart sapma doğru olsa bile ortalama (90) toleransın dışındaysa reddedildiğini doğrular."""
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=5.0)
        assert fn("90.0,10.0") is False

    def test_tolerance_boundary_pass(self):
        """Tolerans sınırının tam üstündeki değerin (110 = 100 + %10) kabul edildiğini doğrular. Sınır değeri dahildir (<= karşılaştırması)."""
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn("110.0,11.0") is True

    def test_none_value_fails(self):
        """Veri yoksa (None) kontrolün hata vermeden False döndüğünü doğrular. Boş veri gelen gerçek hayatta çökmemesi için önemlidir."""
        fn = distribution_check(expected_mean=100.0, expected_std=10.0, tolerance_pct=10.0)
        assert fn(None) is False

    def test_zero_expected_mean(self):
        """Beklenen ortalama 0 olduğunda (yüzde hesabında 0'a bölme riskini) fonksiyonun doğru çalıştığını doğrular."""
        fn = distribution_check(expected_mean=0.0, expected_std=1.0, tolerance_pct=10.0)
        assert fn("0.0,1.0") is True
