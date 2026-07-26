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
import os
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

SECRET_KEY  = os.getenv("DQ_SECRET_KEY", "dq-secret-key-change-in-production")
ALGORITHM   = "HS256"
TOKEN_EXPIRE_HOURS = 8

ROLE_WEIGHTS = {"admin": 3, "editor": 2, "viewer": 1}

if HAS_AUTH_DEPS:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None


# ── Şifre yönetimi ────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    if not HAS_AUTH_DEPS:
        raise ImportError("pip install passlib[bcrypt]")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if not HAS_AUTH_DEPS:
        return False
    return pwd_context.verify(plain, hashed)


# ── JWT token ─────────────────────────────────────────────────────────────────

def create_token(data: dict, expires_hours: int = TOKEN_EXPIRE_HOURS) -> str:
    if not HAS_AUTH_DEPS:
        raise ImportError("pip install python-jose[cryptography]")
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    if not HAS_AUTH_DEPS:
        return None
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Kullanıcı DB işlemleri ────────────────────────────────────────────────────

def get_user(conn, username: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM users WHERE username = %s AND is_active = 1",
            (username,)
        )
        return cur.fetchone()


def authenticate_user(conn, username: str, password: str) -> dict | None:
    user = get_user(conn, username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


def create_user(conn, username: str, email: str,
                password: str, role: str = "viewer") -> bool:
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

        # Varsayılan admin — ilk kurulumda yoksa oluştur
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            if HAS_AUTH_DEPS:
                hashed = hash_password("admin123")
                cur.execute(
                    "INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
                    ("admin", "admin@dq.local", hashed, "admin")
                )
                conn.commit()
                print("✓ Varsayılan admin oluşturuldu — şifre: admin123")


# ── Request'ten kullanıcı al ──────────────────────────────────────────────────

def get_current_user(request: Request) -> dict | None:
    """Cookie'deki JWT token'ı okur, kullanıcı bilgilerini döndürür."""
    token = request.cookies.get("dq_token")
    if not token:
        return None
    return decode_token(token)


def require_role(min_role: str = "viewer"):
    """
    Minimum rol gerektirir. Decorator olarak kullanılır.

    Kullanım:
        @app.get("/checks")
        def checks(user = Depends(require_role("viewer"))):
            ...
    """
    def checker(request: Request):
        user = get_current_user(request)
        if not user:
            raise HTTPException(
                status_code=307,
                headers={"Location": "/login"}
            )
        user_weight = ROLE_WEIGHTS.get(user.get("role", "viewer"), 0)
        min_weight  = ROLE_WEIGHTS.get(min_role, 1)
        if user_weight < min_weight:
            raise HTTPException(
                status_code=403,
                detail=f"Bu işlem için en az '{min_role}' rolü gerekli"
            )
        return user
    return checker


# ── Auth route'larını kaydet ──────────────────────────────────────────────────

def register_auth_routes(app, templates, get_conn_fn):
    """Auth route'larını FastAPI app'e ekler."""

    from fastapi.responses import HTMLResponse

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, error: str = ""):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": error
        })

    @app.post("/login/submit")
    async def login_submit(request: Request):
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
            httponly=True,
            max_age=TOKEN_EXPIRE_HOURS * 3600,
            samesite="lax",
        )
        return response

    @app.get("/logout")
    def logout():
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie("dq_token")
        return response

    @app.get("/admin/users", response_class=HTMLResponse)
    def users_page(request: Request, msg: str = "",
                   user=Depends(require_role("admin"))):
        conn = get_conn_fn()
        try:
            ensure_users_table(conn)
            with conn.cursor() as cur:
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
        conn = get_conn_fn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
        finally:
            conn.close()
        return RedirectResponse("/admin/users?msg=Kullanıcı+silindi", status_code=303)
