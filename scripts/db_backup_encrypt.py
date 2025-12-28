#!/usr/bin/env python3
from __future__ import annotations

import getpass
import os
from pathlib import Path


def has_crypto() -> bool:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
        return True
    except Exception:
        return False


def main() -> None:
    from apps.backend.src.kashat.config import db_path
    src = db_path()
    if not src.exists():
        print("DB file not found:", src)
        return
    out = Path("backup.duckdb.aes")
    if not has_crypto():
        print("Please install cryptography: pip install cryptography")
        return
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import secrets
    pwd = getpass.getpass("Password: ").encode()
    key = (pwd + b"\x00" * 32)[:32]
    nonce = secrets.token_bytes(12)
    data = src.read_bytes()
    aes = AESGCM(key)
    ct = aes.encrypt(nonce, data, None)
    out.write_bytes(nonce + ct)
    print("Encrypted backup written:", out)


if __name__ == '__main__':
    main()

