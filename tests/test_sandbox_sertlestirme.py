"""
Custom script sandbox'ının AST sertleştirme testleri.

dq/engine.py içindeki custom_script_assertion fonksiyonunu test eder.
Amaç: bilinen sandbox kaçış yollarının (__class__, getattr vb.) kapalı olduğunu,
meşru kodun ise hâlâ çalıştığını doğrulamak.
"""

import pytest

from dq.engine import custom_script_assertion


def test_dunder_ozniteligi_reddedilir():
    # __class__ erişimi sandbox kaçışının ilk adımıdır; ValueError bekleniyor.
    kod = "def check(v):\n    return v.__class__"
    with pytest.raises(ValueError, match="Yasaklı öznitelik: __class__"):
        custom_script_assertion(kod)


def test_bases_zinciri_reddedilir():
    # ().__class__.__bases__ zinciri, tüm alt sınıflara (__subclasses__) ulaşmak için kullanılır.
    kod = "def check(v):\n    return ().__class__.__bases__"
    with pytest.raises(ValueError, match="Yasaklı öznitelik"):
        custom_script_assertion(kod)


def test_getattr_reddedilir():
    # getattr, alt çizgili isimlere dolaylı erişim verir; çağrısı da yasaklı isim olarak yakalanır.
    kod = "def check(v):\n    return getattr(v, 'x')"
    with pytest.raises(ValueError, match="Yasaklı fonksiyon: getattr"):
        custom_script_assertion(kod)


def test_getattr_degere_atanirsa_da_reddedilir():
    # Sadece çağrıyı değil, ismin kendisini de kontrol ettiğimizi doğrular.
    kod = "def check(v):\n    f = getattr\n    return f(v, 'x')"
    with pytest.raises(ValueError, match="Yasaklı fonksiyon: getattr"):
        custom_script_assertion(kod)


def test_mesru_kod_calisir():
    # Sertleştirme meşru kullanımı bozmamalı: builtin (len, str) ve math birlikte çalışır.
    kod = "def check(v):\n    return len(str(v)) > 2 and math.sqrt(4) == 2"
    assertion = custom_script_assertion(kod)
    assert assertion(1234) is True


def test_yasakli_import_hala_reddedilir():
    kod = "import os\ndef check(v):\n    return True"
    with pytest.raises(ValueError, match="Yasaklı import: os"):
        custom_script_assertion(kod)
