#!/usr/bin/env python3
"""Test whether the decoded tickets XOR-decrypt into plausible host data.

SESSION_RECORD_20260926_LOBBY_STAGE2.md documents two hardcoded XOR ciphers
(0xBA9600 and 0xBA97C0) that 0xBA97B0 uses right after reading the ticket
tag, writing 24 bytes into [obj+0x28] and iv_seed into [obj+0x2C].

The observed host pointer candidate is 0x25201B16 (622861078) and its
neighbour is 2307161978 = 0x898B0A3A.  This checks whether those dwords can
be produced by either keystream applied to the template tickets.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

KEYS = {
    "0xBA9600": bytes.fromhex(
        "34c361ea76fd3fed210389d388dc3b43093499185830ca34"),
    "0xBA97C0": bytes.fromhex(
        "8ecd56428021ead23643c94801f4095daafe3875f087b13f"),
}

TARGETS = [0x25201B16, 0x898B0A3A]
TEMPLATE = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer"
                r"\lobby_server\lobby_response.json")


def main() -> int:
    raw = TEMPLATE.read_text(encoding="utf-8")
    # $EXTRA_DATA is a JSON-string token; substitute a minimal valid string so
    # the template parses.  Ticket fields are unaffected.
    filled = (raw.replace("$AUTH_TASK", "57")
                 .replace("$IV_SEED", "0")
                 .replace("$EXTRA_DATA", json.dumps("{}")))
    data = json.loads(filled)
    tickets = {
        "client_ticket": base64.b64decode(data["client_ticket"]),
        "server_ticket": base64.b64decode(data["server_ticket"]),
        "lsg_server_ticket": base64.b64decode(data["lsg_server_ticket"]),
    }

    for name, blob in tickets.items():
        print(f"== {name}: {blob[:8].hex()} ...")
        for kname, key in KEYS.items():
            for off in (0, 4):
                src = blob[off:off + len(key)]
                if len(src) < len(key):
                    continue
                out = bytes(s ^ k for s, k in zip(src, key))
                d0 = int.from_bytes(out[0:4], "little")
                d1 = int.from_bytes(out[4:8], "little")
                mark = ""
                if d0 in TARGETS:
                    mark += f"  <== dword0 matches 0x{d0:08X}"
                if d1 in TARGETS:
                    mark += f"  <== dword1 matches 0x{d1:08X}"
                print(f"   {kname} off={off} -> "
                      f"{out[:8].hex()} d0=0x{d0:08X} d1=0x{d1:08X}{mark}")
                printable = "".join(
                    chr(b) if 0x20 <= b < 0x7F else "." for b in out)
                print(f"      ascii: {printable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
