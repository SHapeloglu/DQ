# Bu dosya: trend_check (dq/engine.py) testleri. Geçmiş değerler MagicMock ile sahte store'dan gelir; veritabanı gerekmez.
# Testler pytest ile çalışır; sınıf (class) yalnızca gruplama için kullanılır.
from unittest.mock import MagicMock
from dq.engine import trend_check


def make_store(values):
    """Son N değeri (geçmiş) döndüren sahte store üretir. trend_check bu değerleri store.get_recent_values üzerinden okur."""
    store = MagicMock()
    store.get_recent_values.return_value = values
    return store


class TestTrendCheck:
    """trend_check (zaman içinde ani değişim kontrolü) fonksiyonunun testleri. Son 'window' gün ile önceki pencereyi karşılaştırır; değişim max_pct_change yüzdesini aşarsa başarısız olur."""
    def test_stable_trend_passes(self):
        """Sabit seri (hep 100) ve yüzde değişim yok: geçer."""
        values = [100.0] * 14
        store = make_store(values)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(100.0) is True

    def test_large_increase_fails(self):
        """Önceki 100, şimdi 150 (%50 artış) eşik %20'yi aşar: başarısız."""
        prev = [100.0] * 7
        curr = [150.0] * 7  # %50 artış
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(150.0) is False

    def test_large_decrease_fails(self):
        """Önceki 100, şimdi 50 (%50 düşüş): yön belirtilmemişse (her iki yön) başarısız."""
        prev = [100.0] * 7
        curr = [50.0] * 7  # %50 düşüş
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(50.0) is False

    def test_insufficient_history_passes(self):
        """Yeterli geçmiş yoksa (5 < pencere 7) kontrol geçer. Yetersiz veriyle yanlış alarm üretmemek için."""
        store = make_store([100.0] * 5)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(100.0) is True

    def test_direction_up_increase_fails(self):
        """direction='up' (sadece artış kontrolü): %30 artış başarısız."""
        prev = [100.0] * 7
        curr = [130.0] * 7  # %30 artış — up modunda kötü
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0, direction="up")
        assert fn(130.0) is False

    def test_direction_up_decrease_passes(self):
        """direction='up' iken %30 düşüş normal kabul edilir (True), çünkü sadece artış kontrol edilir."""
        prev = [100.0] * 7
        curr = [70.0] * 7  # düşüş — up modunda normal
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0, direction="up")
        assert fn(70.0) is True

    def test_direction_down_decrease_fails(self):
        """direction='down' (sadece düşüş kontrolü): %40 düşüş başarısız."""
        prev = [100.0] * 7
        curr = [60.0] * 7  # %40 düşüş — down modunda kötü
        store = make_store(prev + curr)
        fn = trend_check("m", store, window=7, max_pct_change=20.0, direction="down")
        assert fn(60.0) is False

    def test_zero_prev_avg_zero_curr_passes(self):
        """Önceki ve şimdiki ortalama 0 ise yüzde hesabında 0'a bölme olmamalı; sonuç geçer (True)."""
        store = make_store([0.0] * 14)
        fn = trend_check("m", store, window=7, max_pct_change=20.0)
        assert fn(0.0) is True
