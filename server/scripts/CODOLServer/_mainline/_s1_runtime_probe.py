# -*- coding: utf-8 -*-
"""Probe runtime dumps for the Blaze/dw anchors and their xrefs."""
import glob
import os
import struct

import capstone

BASE = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs"
CANDIDATES = [
    os.path.join(BASE, r"ENGINE_DUMP_20260925_114204\engine\engine_best.bin"),
    os.path.join(BASE, r"ENGINE_DUMP_20260925_112143\engine\engine_best.bin"),
]

ANCHORS = [
    "@SF_UI_DW_LIVE_CONNECTING_FAILED",
    "@SF_UI_DW_LIVE_DISCONNECTED",
    "DW_LOBBY_CONNECTED",
    "DW_LOBBY_ERROR",
    "dwLogonStart",
    "BD_LOBBY_PROTOCOL_VERSION_FAILURE",
    "BD_MAX_ERROR_CODE",
    "Unknown bdLobbyErrorCode",
    "title_id",
    "tencent_ticket",
]

MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
MD.detail = True


def main():
    for path in CANDIDATES:
        if not os.path.exists(path):
            print("MISSING", path)
            continue
        with open(path, "rb") as fh:
            blob = fh.read()
        print("=" * 78)
        print("DUMP", os.path.basename(path), "size", hex(len(blob)))
        for a in ANCHORS:
            positions = []
            s = 0
            while True:
                i = blob.find(a.encode("ascii"), s)
                if i < 0:
                    break
                positions.append(i)
                s = i + 1
            if positions:
                print("  string %-36s at dump offsets %s" % (a, [hex(p) for p in positions]))


if __name__ == "__main__":
    main()
