"""
secure_store.py - Security layer for the standalone server (report Section 3.6, "Data Security").

* Field encryption at rest: Fernet (AES-128-CBC + HMAC-SHA256, authenticated) using
  backend/fernet_key.bin. Stored values are prefixed "FER_". Legacy "ENC_" values
  (Base64 only - NOT encryption) are still readable and are re-encrypted by migrate_db().
* Passwords: PBKDF2-HMAC-SHA256, 200,000 iterations, random 16-byte salt per user.
  Legacy salted-SHA256 hashes are accepted once and upgraded on successful login.
* Access tokens: HMAC-SHA256-signed (header-less JWT-like) with expiry; the role in the
  token drives role-based access control (patient / physician / admin).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from typing import Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KEY_FILE = os.path.join(BACKEND_DIR, "fernet_key.bin")
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
TOKEN_TTL = 8 * 3600
PBKDF2_ITER = 200_000
_LEGACY_SALT = "healthcare_salt_2024"


def _load_key() -> bytes:
    if os.path.exists(KEY_FILE):
        key = open(KEY_FILE, "rb").read().strip()
        try:
            Fernet(key)
            return key
        except Exception:
            pass
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


_FERNET = Fernet(_load_key())


def _secret() -> bytes:
    val = os.environ.get("SECRET_KEY")
    if not val and os.path.exists(ENV_FILE):
        for line in open(ENV_FILE):
            if line.startswith("SECRET_KEY="):
                val = line.split("=", 1)[1].strip()
    if not val:
        val = base64.urlsafe_b64encode(hashlib.sha256(_load_key()).digest()).decode()
    return val.encode()


# ------------------------------------------------------------ field encryption
def encrypt_field(text: Optional[str]) -> str:
    if text is None or text == "":
        return ""
    return "FER_" + _FERNET.encrypt(str(text).encode()).decode()


def decrypt_field(val: Optional[str]) -> str:
    if not val:
        return ""
    if val.startswith("FER_"):
        try:
            return _FERNET.decrypt(val[4:].encode()).decode()
        except InvalidToken:
            return "[undecryptable]"
    if val.startswith("ENC_"):  # legacy Base64 (not encryption)
        try:
            return base64.b64decode(val[4:]).decode()
        except Exception:
            return val
    return val


def migrate_db(db_path: str) -> int:
    """Re-encrypt legacy Base64/plaintext patient fields with Fernet. Returns rows changed."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, encrypted_name, encrypted_phone FROM patients").fetchall()
    n = 0
    for pid, name, phone in rows:
        new_n = name if (name or "").startswith("FER_") else encrypt_field(decrypt_field(name))
        new_p = phone if (phone or "").startswith("FER_") or not phone else encrypt_field(decrypt_field(phone))
        if new_n != name or new_p != phone:
            conn.execute("UPDATE patients SET encrypted_name=?, encrypted_phone=? WHERE id=?", (new_n, new_p, pid))
            n += 1
    conn.commit()
    conn.close()
    return n


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITER)
    return f"pbkdf2_sha256${PBKDF2_ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> Tuple[bool, bool]:
    """Returns (valid, needs_upgrade)."""
    if not stored:
        return False, False
    if stored.startswith("pbkdf2_sha256$"):
        _, it, salt, dk = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(it)).hex()
        return hmac.compare_digest(calc, dk), False
    legacy = hashlib.sha256((password + _LEGACY_SALT).encode()).hexdigest()
    ok = hmac.compare_digest(legacy, stored)
    return ok, ok


# --------------------------------------------------------------------- tokens
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue_token(user_id: int, username: str, role: str) -> str:
    payload = _b64(json.dumps({"sub": username, "id": user_id, "role": role,
                               "exp": int(time.time()) + TOKEN_TTL}).encode())
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify_token(token: str) -> Optional[dict]:
    try:
        payload, sig = token.split(".")
        good = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(_unb64(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None
