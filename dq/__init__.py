"""
dq paketi — veri kalitesi (DQ) kütüphanesinin giriş noktası.
Dışarıdan sık kullanılan isimler burada toplanır:
  - run, run_from_toml, run_from_dict : kontrolleri çalıştırır
  - Check, CheckResult               : kural ve sonuç nesneleri
  - BaseConnector, build_connector   : veri kaynağı bağlantıları
Örnek: from dq import run_from_toml
"""
from dq.__main__ import run, run_from_toml, run_from_dict
from dq.engine import Check, CheckResult
from dq.connectors import BaseConnector, build_connector

__all__ = [
    "run", "run_from_toml", "run_from_dict",
    "Check", "CheckResult",
    "BaseConnector", "build_connector",
]
