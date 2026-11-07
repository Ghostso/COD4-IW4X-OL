#!/usr/bin/env python3
"""Decode the /auth/ response template tickets and report their tag prefix.

The client's ticket/tag validator (0xB9A7C7 in 0xB9A470) rejects the reply
unless the decoded server_ticket begins with the NULL_REF tag
DE AD BD EF (LE u32 0xEFBDADDE).  This prints exactly what the template
currently ships so a mismatch is visible without guessing.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

TAG = bytes.fromhex("deadbdef")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\lobby_server"
        r"\lobby_response.json")
    raw = path.read_text(encoding="utf-8")
    filled = raw.replace("$AUTH_TASK", "57").replace("$IV_SEED", "0")
    try:
        data = json.loads(filled)
    except Exception as exc:
        print("template is not valid JSON after substitution:", exc)
        return 2
    print("template:", path)
    print("bytes   :", len(raw))
    for key in ("client_ticket", "server_ticket", "lsg_server_ticket"):
        value = data.get(key)
        if value is None:
            print(f"{key:20s} MISSING")
            continue
        blob = base64.b64decode(value)
        ok = blob[:4] == TAG
        print(f"{key:20s} len={len(blob):4d} prefix={blob[:4].hex()} "
              f"tag_ok={ok}")
    print("lsg_server_ticket_size:", data.get("lsg_server_ticket_size"))
    print("code:", data.get("code"), "auth_task:", data.get("auth_task"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
