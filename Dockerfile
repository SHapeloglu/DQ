# DQ (veri kalitesi) web arayüzünün Docker imajı. Python 3.11 üzerine kurulur.
# Adımlar: derleme araçları, Python bağımlılıkları, proje dosyaları, uvicorn ile başlatma.
# Konteyner root olmayan 'dq' kullanıcısı (uid 10001) ile çalışır. Build bağlamı .dockerignore ile daraltılmıştır.
FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları
# gcc ve MySQL istemci geliştirme dosyaları: mysqlclient paketi C kodu derler, bu araçlar olmadan kurulum hata verir.
# pkg-config derleme ayarlarını bulmaya yarar. Sonundaki 'rm' ile apt önbelleği silinir, imaj küçülür.
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
# Bağımlılık dosyası önce kopyalanır: kaynak kod değişse bile pip katmanı önbellekten gelir.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyaları
# Projenin geri kalan tüm dosyaları imaja kopyalanır.
# .dockerignore sayesinde .env, secrets/, .git, testler ve *.db imaja girmez.
COPY . .

# Root olmayan kullanıcı. Yalnızca /app dizininin sahibi değişir: uygulama burada SQLite dosyası (dq_metrics.db, dq_results.db) oluşturabilir.
# Kod dosyaları root sahipliğinde kalır (dq yazamaz). ./dags bind mount'u ana makinedeki 644/755 izinleriyle okunabilir.
# /run/secrets dosyalarının dq tarafından okunabilirliği canlı deploy'da doğrulanmalı (compose secret izinleri).
RUN groupadd --system --gid 10001 dq \
    && useradd --system --uid 10001 --gid dq --no-create-home --shell /usr/sbin/nologin dq \
    && chown dq:dq /app
USER dq

EXPOSE 8000

# uvicorn: main.py içindeki 'app' nesnesini 0.0.0.0:8000 üzerinde başlatır (konteyner içinde tüm arayüzler). Tek işçi çalışır.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
