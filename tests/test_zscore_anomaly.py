# Bu dosya: zscore_anomaly (dq/engine.py) testleri. Geçmiş değerler sahte store'dan gelir; veritabanı gerekmez.
# Z-skoru = (değer - ortalama) / standart sapma. Eşik (max_zscore) aşılırsa anomali sayılır. Testler pytest ile çalışır.
import math
import pytest
from unittest.mock import MagicMock
from dq.engine import zscore_anomaly


def make_store(values):
    """Son N değeri döndüren sahte store üretir (zscore_anomaly için)."""
    store = MagicMock()
    store.get_recent_values.return_value = values
    return store


class TestZscoreAnomaly:
    """zscore_anomaly (z-skoru ile anomali tespiti) fonksiyonunun testleri. Yeni değerin geçmiş ortalamadan kaç standart sapma uzakta olduğuna bakılır; max_zscore'u aşarsa anomali sayılır."""
    def test_normal_value_passes(self):
        """Geçmiş hep 100 ise ve yeni değer 100 ise anomali yok (True)."""
        values = [100.0] * 20
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=3.0)
        assert fn(100.0) is True

    def test_anomaly_detected(self):
        """Geçmişte 100–101.9 arası değerler varken 9999 gelirse büyük anomali (False). 'std != 0' yorumu: standart sapma sıfır olursa z-skoru hesaplanamaz, bu test o durumu dışlar."""
        values = [100.0 + i * 0.1 for i in range(20)]  # std != 0
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=3.0)
        assert fn(9999.0) is False

    def test_insufficient_samples_passes(self):
        """Örnek sayısı az (min_samples=5, elimizde 2) ise yeterli veri yok diye kontrol geçer (True)."""
        store = make_store([100.0, 200.0])
        fn = zscore_anomaly("m", store, max_zscore=3.0, min_samples=5)
        assert fn(9999.0) is True

    def test_constant_series_passes(self):
        """Sabit seri (std = 0) için z-skoru tanımsız; hata vermeden geçmeli (True). Sıfıra bölme hatasını yakalar."""
        values = [50.0] * 10
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=3.0)
        assert fn(50.0) is True

    def test_exact_threshold_passes(self):
        """Eşik 10.0 iken 10.5 değeri (ortalamaya çok yakın) geçer. DİKKAT: Test adı 'tam eşik' diyor ama 10.5 değerinin z-skoru 0'a yakındır, yani eşiğin tam sınırını test etmez. (TODO(kontrol))"""
        values = list(range(1, 21))
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=10.0)
        assert fn(10.5) is True

    def test_custom_max_zscore(self):
        """max_zscore=0.0 gibi çok sıkı bir eşikle, küçük bir sapma bile olsa 9999 anomali sayılmalı (False)."""
        values = [100.0 + i * 0.1 for i in range(20)]  # std != 0
        store = make_store(values)
        fn = zscore_anomaly("m", store, max_zscore=0.0)
        assert fn(9999.0) is False

    def test_store_called_with_metric_name(self):
        """store.get_recent_values, metrik adı ve n=100 parametresiyle tam bir kez çağrılmalı. Doğru metriğin ve doğru pencere boyutunun okunduğunu doğrular."""
        store = make_store([100.0] * 10)
        fn = zscore_anomaly("siparis_sayisi", store, max_zscore=3.0)
        fn(100.0)
        store.get_recent_values.assert_called_once_with("siparis_sayisi", n=100)

    def test_in_assertion_map(self):
        """'zscore_anomaly' kuralının _ASSERTION_MAP (kural adı → fonksiyon) kaydının olduğunu doğrular."""
        from dq.config import _ASSERTION_MAP
        assert "zscore_anomaly" in _ASSERTION_MAP
