"""cache_layer.py — TTL'li in-memory profil cache'i."""
from __future__ import annotations
import time
import hashlib
import json
from typing import Any


class TTLCache:
    """Basit TTL'li in-memory key-value cache."""

    def __init__(self, ttl_seconds: int = 300):
        """Önbelleği oluşturur. `ttl_seconds` bir kaydın kaç saniye geçerli kalacağıdır (varsayılan 300 sn = 5 dk)."""
        self._store: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl_seconds

    def _key(self, *parts: str) -> str:
        """Parçaları '|' ile birleştirip MD5 özeti üretir; önbellek anahtarı olarak kullanılır. MD5 burada güvenlik için değil, anahtar üretmek için kullanılır."""
        raw = "|".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, *parts: str) -> Any | None:
        """Anahtara ait değeri döndürür. Kayıt yoksa ya da süresi dolmuşsa None döner; süresi dolan kayıt silinir."""
        key = self._key(*parts)
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, *parts: str, value: Any) -> None:
        """Değeri verilen parçalar anahtarıyla saklar. Süre, şu anki zamana `ttl` eklenerek hesaplanır."""
        key = self._key(*parts)
        self._store[key] = (value, time.time() + self.ttl)

    def invalidate(self, *parts: str) -> None:
        """Verilen anahtarı önbellekten hemen siler (ör. veri değiştiğinde). Yoksa sessizce geçer."""
        key = self._key(*parts)
        self._store.pop(key, None)

    def clear(self) -> None:
        """Önbellekteki tüm kayıtları siler."""
        self._store.clear()

    def __len__(self) -> int:
        """Yalnız süresi dolmamış kayıtların sayısını döndürür. Süresi dolanlar bellekte kalabilir; yalnız `get` ile silinirler."""
        now = time.time()
        return sum(1 for _, (_, exp) in self._store.items() if exp > now)


# Modül düzeyinde singleton — profil sonuçları için (5 dk TTL)
profile_cache = TTLCache(ttl_seconds=300)
