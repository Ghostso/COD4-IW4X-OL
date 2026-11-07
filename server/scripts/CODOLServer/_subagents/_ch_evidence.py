"""Emit the VA-level evidence table for the CODOL connect/handshake chain.

Read-only. Produces JSON on stdout so the report generator can quote exact
addresses without hand-copying them.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ch_dis import disasm  # noqa: E402


def rows(start, end):
    return [
        {"va": "0x%08X" % a, "bytes": None, "asm": "%s %s" % (m, o)}
        for a, s, m, o in disasm(start, end)
    ]


CONNECT_CALL = rows(0x7F2D1A, 0x7F2D35)
BC_RET0 = rows(0xB88CE7, 0xB88CF1)
BC_B75E00 = rows(0xB88F06, 0xB88F4D)
B75E00 = rows(0xB75E00, 0xB75E65)
HANDSHAKE_START = rows(0xB9AA14, 0xB9AA60)
HANDSHAKE_HTTP = rows(0xB9AD99, 0xB9AE26)
CURL_STATUS = rows(0xC752BC, 0xC75320)
CURL_DONE = rows(0xC767D0, 0xC76860)

EVIDENCE = {
    "image": "CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin",
    "image_base": "0x400000",
    "call_site_7F2D2A": {
        "desc": "only caller of 0xB88CC0 (thiscall, ret 0x28 = 10 stack args)",
        "rows": CONNECT_CALL,
    },
    "B88CC0_early_ret0": {
        "desc": "exit A: [objA+0x20] != 0 -> xor al,al ; ret 0x28",
        "rows": BC_RET0,
    },
    "B88CC0_write_and_dispatch": {
        "desc": "exit B via 0xB75E00 failure; otherwise call 0xB9A9E0 and return its al",
        "rows": BC_B75E00,
    },
    "B75E00": {
        "desc": "write len into stream; if [obj+0xC]==0 it returns 1 unconditionally",
        "rows": B75E00,
    },
    "B9A9E0_head": {
        "desc": "builds https://<host>:<port>/auth/ request, then writes JSON body",
        "rows": HANDSHAKE_START,
    },
    "B9A9E0_tail": {
        "desc": "POST perform + response state; success requires state==3",
        "rows": HANDSHAKE_HTTP,
    },
    "C752BC_http_status": {
        "desc": "HTTP status gating: 200 <= status < 300 -> state 5",
        "rows": CURL_STATUS,
    },
    "C767F0_state": {
        "desc": "state query: arg==3 succeeds only when [ecx+4]==3 (request completed)",
        "rows": CURL_DONE,
    },
}

STRINGS = {
    "0xD5A2CC": "https://%s:%d/auth/",
    "0xD5A228": "auth_task",
    "0xD5A1E4": "application/json",
    "0xD5A1D4": "Content-Type",
    "0xD59AEC": "extra_data",
    "0xD59E6C": "X-TransactionID",
    "0xD59E7C": "%I64u",
    "0xD5A114": "iv_seed",
    "0xDB7AC0": "title_id",
    "0xCC383C": "identity",
    "0xDC9CA4": "cacert.pem",
    "0xDC9CB0": "CODOL/1.0",
    "0xD95674": "Host: %s",
    "0xD95684": "Host: %s:%d",
    "0xCBF8E8": "DELETE",
    "0xCBE460": "COPY",
}


def main():
    out = {"evidence": EVIDENCE, "strings": STRINGS}
    print(json.dumps(out, indent=1, ensure_ascii=True))


if __name__ == "__main__":
    main()
