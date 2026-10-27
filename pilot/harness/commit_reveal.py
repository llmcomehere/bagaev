#!/usr/bin/env python3
"""Commit-reveal закрытого payload: точные bytes + минимум 32 случайных bytes nonce.

stdout содержит только SHA-256 или VERIFIED/MISMATCH. Payload и nonce не копируются.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
from pathlib import Path

DOMAIN = b"bagaev-pilot-hidden-task/1\0"


def commitment(payload: bytes, nonce: bytes) -> str:
    if len(nonce) < 32:
        raise ValueError("NONCE_TOO_SHORT: нужны минимум 32 случайных байта")
    return hashlib.sha256(DOMAIN + len(nonce).to_bytes(8, "big") + nonce
                          + len(payload).to_bytes(8, "big") + payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("commit", "verify"))
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--nonce-file", type=Path, required=True)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    value = commitment(args.payload.read_bytes(), args.nonce_file.read_bytes())
    if args.action == "commit":
        print(value)
        return 0
    ok = isinstance(args.sha256, str) and hmac.compare_digest(value, args.sha256)
    print("VERIFIED" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
