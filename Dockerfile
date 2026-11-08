# DQ (veri kalitesi) web arayüzünün Docker imajı. Python 3.11 üzerine kurulur.
# Adımlar: derleme araçları, Python bağımlılıkları, proje dosyaları, uvicorn ile başlatma.
# DİKKAT: bu dosyada USER tanımlı değil; konteyner root olarak çalışır (düzeltilmedi, bilgi amaçlı).
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
# DİKKAT: bu klasörde .dockerignore dosyası yok; .env ve secrets klasörü de imaja girer. .dockerignore eklenmesi önerilir (düzeltilmedi).
COPY . .

EXPOSE 8000

# uvicorn: main.py içindeki 'app' nesnesini 0.0.0.0:8000 üzerinde başlatır (konteyner içinde tüm arayüzler). Tek işçi çalışır.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
