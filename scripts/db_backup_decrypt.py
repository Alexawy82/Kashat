#!/usr/bin/env python3
from __future__ import annotations

import getpass
from pathlib import Path


def main() -> None:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:
        print("Please install cryptography: pip install cryptography")
        return
    inp = Path("backup.duckdb.aes")
    out = Path("restored.duckdb")
    if not inp.exists():
        print("Encrypted backup not found:", inp)
        return
    data = inp.read_bytes()
    nonce, ct = data[:12], data[12:]
    pwd = getpass.getpass("Password: ").encode()
    key = (pwd + b"\x00" * 32)[:32]
    aes = AESGCM(key)
    pt = aes.decrypt(nonce, ct, None)
    out.write_bytes(pt)
    print("Decrypted DB written:", out)


if __name__ == '__main__':
    main()

