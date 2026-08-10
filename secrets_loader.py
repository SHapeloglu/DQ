"""
Secrets yükleyici — önce /run/secrets/<key> dosyasına bakar,
bulamazsa environment variable'dan okur, o da yoksa default döner.
Docker Swarm secrets ve Compose env_file ile uyumlu çalışır.
"""
import os

def get_secret(key: str, default: str = "") -> str:
    secret_path = f"/run/secrets/{key}"
    if os.path.exists(secret_path):
        with open(secret_path) as f:
            return f.read().strip()
    return os.getenv(key, default)
