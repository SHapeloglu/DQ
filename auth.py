"""
auth.py — DQ kullanıcı kimlik doğrulama ve rol yönetimi.

Roller:
    admin   → her şey: kullanıcı yönetimi dahil
    editor  → kural ekle/düzenle/sil, kaynak yönet
    viewer  → sadece okuma: dashboard, run geçmişi

Kurulum:
    pip install python-jose[cryptography] passlib[bcrypt]

DB tablosu:
    CREATE TABLE users (
        id       INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        email    VARCHAR(200),
        password VARCHAR(200) NOT NULL,  -- bcrypt hash
        role     VARCHAR(20) DEFAULT 'viewer',
        is_active TINYINT(1) DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
"""

from __future__ import annotations
import hmac
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    HAS_AUTH_DEPS = True
except ImportError:
    HAS_AUTH_DEPS = False

# DQ_SECRET_KEY verilmezse süreç başına rastgele anahtar üretilir (tahmin edilemez; yeniden başlatmada oturumlar düşer). Kalıcı oturum için ortam değişkeni verilmelidir.
SECRET_KEY  = os.getenv("DQ_SECRET_KEY") or secrets.token_urlsafe(48)
ALGORITHM   = "HS256"
TOKEN_EXPIRE_HOURS = 8

ROLE_WEIGHTS = {"admin": 3, "editor": 2, "viewer": 1}

if HAS_AUTH_DEPS:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None


# ── Şifre yönetimi ────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    Düz metin şifreyi bcrypt ile özetler (hash). Veritabanına hiçbir zaman düz şifre yazılmaz; yalnız bu özet yazılır.
    passlib kurulu değilse ImportError fırlatır.
    """
    if not HAS_AUTH_DEPS:
        raise ImportError("pip install passlib[bcrypt]")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Girilen düz şifrenin, saklanan hash ile uyuşup uyuşmadığını kontrol eder. Kütüphaneler yoksa her zaman False döner (giriş yapılamaz)."""
    if not HAS_AUTH_DEPS:
        return False
    return pwd_context.verify(plain, hashed)


# ── JWT token ─────────────────────────────────────────────────────────────────

def create_token(data: dict, expires_hours: int = TOKEN_EXPIRE_HOURS) -> str:
    """
    Verilen bilgilerle (ör. kullanıcı adı, rol) imzalı bir JWT token üretir. Token `expires_hours` saat sonra geçersiz olur.
    jose kurulu değilse ImportError fırlatır.
    """
    if not HAS_AUTH_DEPS:
        raise ImportError("pip install python-jose[cryptography]")
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """JWT token'ı çözer ve içindeki bilgileri (dict) döndürür. Token geçersiz, süresi dolmuş ya da kütüphane yoksa None döner; hata fırlatmaz."""
    if not HAS_AUTH_DEPS:
        return None
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Kullanıcı DB işlemleri ────────────────────────────────────────────────────

def get_user(conn, username: str) -> dict | None:
    """
    Kullanıcı adına göre aktif (is_active=1) kullanıcıyı veritabanından getirir. Bulunamazsa None döner.
    `conn` açık bir veritabanı bağlantısıdır; parola sorgusu parametreli (%s) yapılır.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM users WHERE username = %s AND is_active = 1",
            (username,)
        )
        return cur.fetchone()


def authenticate_user(conn, username: str, password: str) -> dict | None:
    """Kullanıcı adı ve şifreyi kontrol eder. Doğruysa kullanıcı kaydını (dict) döndürür; kullanıcı yoksa ya da şifre yanlışsa None döner."""
    user = get_user(conn, username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


def create_user(conn, username: str, email: str,
                password: str, role: str = "viewer") -> bool:
    """
    Yeni kullanıcı ekler. Şifre hash'lenerek kaydedilir ve işlem commit edilir.
    Başarılıysa True. Kullanıcı adı zaten varsa ya da herhangi bir hata olursa False döner; hata mesajı gösterilmez.
    """
    try:
        hashed = hash_password(password)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
                (username, email, hashed, role)
            )
        conn.commit()
        return True
    except Exception:
        return False


def ensure_users_table(conn):
    """users tablosunu oluşturur ve varsayılan admin ekler."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                username   VARCHAR(100) UNIQUE NOT NULL,
                email      VARCHAR(200),
                password   VARCHAR(200) NOT NULL,
                role       VARCHAR(20) DEFAULT 'viewer',
                is_active  TINYINT(1) DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Admin satırı yoksa oluşturulur (admin silinirse bir sonraki girişte yeniden doğar). İlk parola DQ_ADMIN_PASSWORD ortam değişkeninden gelir; verilmezse rastgele üretilir ve stderr'e BİR KEZ yazılır (dosyaya yazılmaz).
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            if HAS_AUTH_DEPS:
                parola_env = os.environ.get("DQ_ADMIN_PASSWORD")
                ilk_parola = parola_env or secrets.token_urlsafe(12)
                hashed = hash_password(ilk_parola)
                cur.execute(
                    "INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
                    ("admin", "admin@dq.local", hashed, "admin")
                )
                conn.commit()
                if parola_env:
                    print("✓ Varsayılan admin oluşturuldu — parola DQ_ADMIN_PASSWORD değişkeninden")
                else:
                    print(f"✓ Varsayılan admin oluşturuldu — geçici admin parolası: {ilk_parola} — ilk girişten sonra değiştirin", file=sys.stderr)


# ── Request'ten kullanıcı al ──────────────────────────────────────────────────

def get_current_user(request: Request) -> dict | None:
    """Cookie'deki JWT token'ı okur, kullanıcı bilgilerini döndürür."""
    token = request.cookies.get("dq_token")
    if not token:
        return None
    return decode_token(token)


def _guncel_kullanici(username: str) -> dict | None:
    """Kullanıcının veritabanındaki güncel ve aktif kaydını döner. Kayıt yoksa, pasifse ya da
    veritabanına ulaşılamıyorsa None döner (kapalı başarısızlık: erişim verilmez)."""
    if not username or _conn_fn is None:
        return None
    conn = None
    try:
        conn = _conn_fn()
        return get_user(conn, username)
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()


# ── Genel yetki kapısı ───────────────────────────────────────────────────────
# Uygulamanın TÜM rotalarına main.py'de FastAPI(dependencies=[Depends(yetki_kapisi)]) ile uygulanır; böylece yeni eklenen bir rota rol kontrolünü unutsa bile korumasız kalmaz.
# Kurallar: giriş sayfaları açık; /admin/* ve /settings/* için admin; GET/HEAD için viewer; diğer yöntemler (POST/PUT/DELETE) için editor.
# Makine istemcileri (Airflow DAG'ı, Power BI OData) çerez taşıyamaz: DQ_API_TOKEN ortam değişkeni tanımlıysa "X-DQ-Token" başlığıyla (veya "Authorization: Bearer ...") yalnız /api/* ve /odata/* yollarında editor yetkisiyle girebilirler.
ACIK_YOLLAR = ("/login", "/login/submit", "/logout")
MAKINE_YOL_ONEKLERI = ("/api/", "/odata/")
# Yalnız admin erişebilen yollar: yönetim sayfaları ve uyarı ayarları (SMTP ve webhook bilgileri).
ADMIN_YOL_ONEKLERI = ("/admin/", "/settings/", "/api/alert-settings")
ADMIN_YOLLAR = ("/admin", "/settings")

# Veritabanı bağlantı fabrikası; register_auth_routes içinde atanır.
_conn_fn = None


def _servis_anahtari_gecerli(request: Request) -> bool:
    """İstekteki servis anahtarını DQ_API_TOKEN ile sabit sürede karşılaştırır. Ortam değişkeni tanımsızsa her zaman False (makine erişimi kapalı)."""
    beklenen = os.environ.get("DQ_API_TOKEN", "")
    if not beklenen:
        return False
    gelen = request.headers.get("x-dq-token", "")
    if not gelen:
        yetki = request.headers.get("authorization", "")
        if yetki.lower().startswith("bearer "):
            gelen = yetki[7:].strip()
    return bool(gelen) and hmac.compare_digest(gelen.encode(), beklenen.encode())


def yetki_kapisi(request: Request):
    """
    Her istekte çalışan genel bağımlılık. Giriş yoksa /api ve /odata yollarında 401, diğerlerinde /login'e 307 yönlendirme verir; rol yetersizse 403.
    Başarılıysa kullanıcı bilgisini döner (servis anahtarıyla gelenlerde {"sub": "servis", "role": "editor"}).
    """
    yol = request.url.path
    if yol in ACIK_YOLLAR:
        return None

    makine_yolu = yol.startswith(MAKINE_YOL_ONEKLERI)

    if yol.startswith(ADMIN_YOL_ONEKLERI) or yol in ADMIN_YOLLAR:
        gerekli = "admin"
    elif request.method in ("GET", "HEAD", "OPTIONS"):
        gerekli = "viewer"
    else:
        gerekli = "editor"

    if makine_yolu and _servis_anahtari_gecerli(request):
        # Servis anahtarı editor yetkisindedir; admin yollarında bu yetki yetmez.
        user = {"sub": "servis", "role": "editor"}
    else:
        token_user = get_current_user(request)
        # Rol token'daki değil veritabanındaki güncel kayıttan alınır: silinen, pasifleştirilen
        # ya da yetkisi düşürülen kullanıcı, token süresi dolmadan da erişimini kaybeder.
        guncel = _guncel_kullanici(token_user.get("sub", "")) if token_user else None
        if not guncel:
            if makine_yolu:
                raise HTTPException(status_code=401, detail="Kimlik doğrulaması gerekli")
            raise HTTPException(status_code=307, headers={"Location": "/login"})
        user = {**token_user, "role": guncel.get("role", "viewer")}

    if ROLE_WEIGHTS.get(user.get("role", "viewer"), 0) < ROLE_WEIGHTS[gerekli]:
        raise HTTPException(status_code=403, detail=f"Bu işlem için en az '{gerekli}' rolü gerekli")
    request.state.user = user
    return user



def require_role(min_role: str = "viewer"):
    """
    Minimum rol gerektirir. Decorator olarak kullanılır.

    Kullanım:
        @app.get("/checks")
        def checks(user = Depends(require_role("viewer"))):
            ...
    """
    def checker(request: Request):
        """
        FastAPI bağımlılığı (dependency). İsteğin çerezindeki token'a bakar:
        - Token yoksa/geçersizse login sayfasına yönlendirir.
        - Rolü yetersizse HTTP 403 döner.
        Başarılıysa kullanıcı bilgisini route'a verir.
        """
        # Kapıdan geçen (veritabanıyla doğrulanmış) kullanıcı varsa onu kullan.
        user = getattr(request.state, "user", None) or get_current_user(request)
        if not user:
            raise HTTPException(
                # Giriş yapılmamışsa login sayfasına yönlendirme yapılır. (Yönlendirme durum kodu 307 olarak ayarlanmış.)
                status_code=307,
                headers={"Location": "/login"}
            )
        user_weight = ROLE_WEIGHTS.get(user.get("role", "viewer"), 0)
        # Tanınmayan bir rol adı verilirse en düşük seviye (viewer, 1) kabul edilir.
        min_weight  = ROLE_WEIGHTS.get(min_role, 1)
        if user_weight < min_weight:
            raise HTTPException(
                status_code=403,
                detail=f"Bu işlem için en az '{min_role}' rolü gerekli"
            )
        return user
    return checker


def _cookie_secure() -> bool:
    """DQ_COOKIE_SECURE 1/true/yes ise True. Varsayılan False; HTTPS arkasında bu ayar etkinleştirilmelidir."""
    return os.environ.get("DQ_COOKIE_SECURE", "").strip().lower() in ("1", "true", "yes")


# ── Auth route'larını kaydet ──────────────────────────────────────────────────

def register_auth_routes(app, templates, get_conn_fn):
    """Auth route'larını FastAPI app'e ekler."""
    global _conn_fn
    _conn_fn = get_conn_fn

    from fastapi.responses import HTMLResponse

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, error: str = ""):
        """Giriş (login) sayfasını gösterir. `error` parametresi varsa sayfada hata mesajı olarak gösterilir."""
        return templates.TemplateResponse("login.html", {
            "request": request, "error": error
        })

    @app.post("/login/submit")
    async def login_submit(request: Request):
        """
        Giriş formunu işler. Kullanıcı adı/şifre doğruysa JWT'yi `dq_token` çerezine yazar ve ana sayfaya yönlendirir.
        Hatalıysa login sayfasına hata mesajıyla geri döner. Her girişte users tablosunun varlığı kontrol edilir.
        """
        form     = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")

        conn = get_conn_fn()
        try:
            ensure_users_table(conn)
            user = authenticate_user(conn, username, password)
        finally:
            conn.close()

        if not user:
            return RedirectResponse(
                "/login?error=Kullanıcı+adı+veya+şifre+hatalı",
                status_code=303
            )

        token = create_token({
            "sub":  user["username"],
            "role": user["role"],
            "id":   user["id"],
        })

        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            "dq_token", token,
            # httponly: JavaScript token'a erişemez (XSS saldırılarına karşı koruma). samesite=lax: çapraz site isteklerinde çerez gönderilmez (CSRF'e karşı kısmi koruma).
            # secure: DQ_COOKIE_SECURE=1/true/yes ise çerez yalnız HTTPS üzerinden gönderilir. Varsayılan kapalıdır (HTTP kurulumları kırılmasın); HTTPS arkasında DQ_COOKIE_SECURE=1 ayarlanmalı.
            httponly=True,
            max_age=TOKEN_EXPIRE_HOURS * 3600,
            samesite="lax",
            secure=_cookie_secure(),
        )
        return response

    @app.get("/logout")
    def logout():
        """Çıkış yapar: `dq_token` çerezini siler ve login sayfasına yönlendirir."""
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie("dq_token")
        return response

    @app.get("/admin/users", response_class=HTMLResponse)
    def users_page(request: Request, msg: str = "",
                   user=Depends(require_role("admin"))):
        """Yalnız admin'in görebildiği kullanıcı listesi sayfasıdır. Parola hash'i gösterilmez; yalnız id, kullanıcı adı, e-posta, rol, durum ve oluşturma tarihi listelenir."""
        conn = get_conn_fn()
        try:
            ensure_users_table(conn)
            with conn.cursor() as cur:
                # Parola hash'i bu sorguda bilerek seçilmez; sayfaya gitmez.
                cur.execute("SELECT id,username,email,role,is_active,created_at FROM users ORDER BY id")
                users = cur.fetchall()
        finally:
            conn.close()
        return templates.TemplateResponse("users.html", {
            "request": request, "users": users,
            "msg": msg, "current_user": user,
        })

    @app.post("/admin/users/new")
    async def user_create(request: Request,
                          user=Depends(require_role("admin"))):
        """Admin formundan yeni kullanıcı ekler (yalnız admin). Başarılı veya başarısız olduğu bilgisiyle kullanıcı listesine yönlendirir."""
        form     = await request.form()
        username = form.get("username", "")
        email    = form.get("email", "")
        password = form.get("password", "")
        role     = form.get("role", "viewer")

        conn = get_conn_fn()
        try:
            ok = create_user(conn, username, email, password, role)
        finally:
            conn.close()

        if ok:
            return RedirectResponse("/admin/users?msg=Kullanıcı+eklendi", status_code=303)
        return RedirectResponse("/admin/users?msg=Hata:+kullanıcı+eklenemedi", status_code=303)

    @app.post("/admin/users/{user_id}/delete")
    def user_delete(user_id: int,
                    user=Depends(require_role("admin"))):
        """Verilen id'li kullanıcıyı siler (yalnız admin). İşlem sonucu listeye yönlendirme ile bildirilir. Bu işlemin geri alınması yoktur."""
        conn = get_conn_fn()
        try:
            with conn.cursor() as cur:
                # DİKKAT: Admin kendi hesabını da silebilir; bunu engelleyen bir kontrol yok.
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
        finally:
            conn.close()
        return RedirectResponse("/admin/users?msg=Kullanıcı+silindi", status_code=303)
