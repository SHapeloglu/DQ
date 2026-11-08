"""
test_guvenlik_kalan.py — güvenlik ve dayanıklılık için kalan üç kontrol.

1) API dokümantasyon uçları (/docs, /redoc, /openapi.json) üretimde kapalı olmalı;
   aksi halde uygulamanın tüm yolları girişsiz taranabilir.
2) Airflow operatörünün _serialize metodu sonuçları çiftlemeden yazmalı;
   aksi halde XCom ve API'ye giden sonuç sayısı şişer.
3) Holt-Winters anomali fonksiyonu, belirgin sapmayı yakalamalı ve model
   hatası gibi görünen bir mesajla sessizce 'anomali yok' dönmemeli.

Veritabanı veya gerçek Airflow gerekmez.
"""
import logging
import sys
import types
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from main import app
from auth import yetki_kapisi, HAS_AUTH_DEPS


# ── 1) API dokümantasyon uçları ───────────────────────────────────────────────

@pytest.mark.skipif(not HAS_AUTH_DEPS, reason="JWT bağımlılıkları yok")
def test_app_dokumantasyon_ucları_kapali():
    # Neden: FastAPI varsayılan olarak /docs, /redoc ve /openapi.json'ı açar.
    # Bu üçü kapalı olmazsa API'nin tüm uçları giriş yapmadan listelenebilir.
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


@pytest.fixture
def istemci():
    """Yetki kapısı AÇIK (override'sız) istemci; test bitince override geri konur."""
    # Neden: conftest kapıyı testler için kapatır; burada gerçek davranışı görmek istiyoruz.
    eski = app.dependency_overrides.pop(yetki_kapisi, None)
    yield TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    if eski is not None:
        app.dependency_overrides[yetki_kapisi] = eski


@pytest.mark.skipif(not HAS_AUTH_DEPS, reason="JWT bağımlılıkları yok")
@pytest.mark.parametrize("yol", ["/docs", "/openapi.json", "/redoc"])
def test_girissiz_dokumantasyon_acik_degil(istemci, yol):
    # Neden: Giriş yapmamış biri dokümantasyonu göremeyi/ indirmeyi başaramamalı.
    # Uç kapalıysa 404 döner; bazı durumlarda giriş kapısı 401/307 verebilir.
    # Kabul şartı: hiçbir durumda 200 (açık) dönmemeli.
    r = istemci.get(yol)
    assert r.status_code != 200


# ── 2) Airflow operatörü: _serialize çiftleme kontrolü ───────────────────────

@pytest.fixture
def airflow_operatoru(monkeypatch):
    """
    DQOperator sınıfını döndürür.

    Gerçek airflow paketi yoksa (bu ortamda yok) küçük bir sahte paket kurulur.
    Böylece dq/airflow.py yine import edilebilir ve _serialize test edilebilir.
    Test bitince sahte modüller ve dq.airflow önbellekten silinir.
    """
    try:
        import airflow  # noqa: F401  — gerçek paket varsa onu kullan
    except ImportError:
        # Sahte BaseOperator: __init__ yalnızca kwargs'ı alır ve hiçbir şey yapmaz.
        class SahteBaseOperator:
            def __init__(self, **kwargs):
                pass

        def sahte_apply_defaults(fn):
            # Dekoratör işlevsiz: fonksiyonu aynen döndürür.
            return fn

        paket = types.ModuleType("airflow")
        modeller = types.ModuleType("airflow.models")
        modeller.BaseOperator = SahteBaseOperator
        araclar = types.ModuleType("airflow.utils")
        dekor = types.ModuleType("airflow.utils.decorators")
        dekor.apply_defaults = sahte_apply_defaults

        monkeypatch.setitem(sys.modules, "airflow", paket)
        monkeypatch.setitem(sys.modules, "airflow.models", modeller)
        monkeypatch.setitem(sys.modules, "airflow.utils", araclar)
        monkeypatch.setitem(sys.modules, "airflow.utils.decorators", dekor)

    from dq.airflow import DQOperator
    yield DQOperator

    # Önbellekteki operatör modülü bir sonraki testi sahte pakete bağlı bırakmasın.
    sys.modules.pop("dq.airflow", None)


def test_serialize_sonuclari_cifte_eklemez(airflow_operatoru):
    # Neden: _serialize her sonucu bir kez eklemeli. 2 sonuç verildiğinde
    # payload["results"] de 2 elemanlı olmalı; 4 dönerse çiftleme vardır.
    DQOperator = airflow_operatoru

    # __init__ çağrılmadan nesne oluşturuluyor: yalnızca _serialize'ın
    # kullandığı öznitelikler (config ve mode) elle atanıyor.
    op = object.__new__(DQOperator)
    op.config = "checks.toml"
    op.mode = "checks"
    op.log = logging.getLogger("test")

    # Dataclass tipi bir sonuç (check sonucu benzeri) ve basit bir nesne.
    from dataclasses import dataclass

    @dataclass
    class SahteSonuc:
        name: str
        passed: bool
        value: float

    sonuclar = [
        SahteSonuc(name="Satır sayısı > 0", passed=True, value=100.0),
        SahteSonuc(name="Null oran < %10", passed=False, value=12.5),
    ]

    context = {
        "dag": SimpleNamespace(dag_id="orders_quality"),
        "task": SimpleNamespace(task_id="check_orders"),
        "run_id": "x",
    }

    payload = op._serialize(sonuclar, context)

    # 2 sonuç girdi; çıktı da 2 olmalı.
    assert len(payload["results"]) == 2
    # Özet de aynı sayıyı göstermeli (total bozulmamış olmalı).
    assert payload["summary"]["total"] == 2


# ── 3) Holt-Winters anomali tespiti ──────────────────────────────────────────

def test_holt_winters_belirgin_sapmayi_yakalar():
    # Neden: 30 gözlemlik sabit gürültülü bir geçmişe çok uzak bir değer gelince
    # anomali olarak işaretlenmeli. Model hatası mesajı dönerse fonksiyon
    # sessizce hatalı çalışıyor demektir; bunu da yakalamak istiyoruz.
    from dq.anomaly import _holt_winters_detect

    # Deterministik gürültü: 98 ile 102 arasında değerler (her çalıştırmada aynı).
    gecmis = [100.0 + ((i * 7) % 5) - 2 for i in range(30)]
    guncel = 1000.0   # geçmişin çok üstünde

    sonuc = _holt_winters_detect("siparis_tutari", guncel, gecmis, 3.0)

    # statsmodels yoksa z-score'a düşer; o da bu veride anomali verir.
    assert sonuc.is_anomaly is True
    assert sonuc.method in ("zscore", "holt_winters")
    # Hata mesajı içermemeli (NameError veya "Model hatası" görünmemeli).
    assert "NameError" not in sonuc.message
    assert "Model hatası" not in sonuc.message
