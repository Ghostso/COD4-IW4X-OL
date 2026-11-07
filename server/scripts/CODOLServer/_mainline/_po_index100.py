# -*- coding: utf-8 -*-
"""
_po_index100.py - resolve what the number 100 in '[100]...' actually is.

Hypothesis under test:
  The BD_* name block starting at file 0x6CD744 / VA 0x00ACD744 is the
  MSVC enum-name table for bdLobbyErrorCode. If it is a CONTIGUOUS
  NUL-separated token block with no padding, then the token at ordinal N
  corresponds to enum value N, and the number shown by the UI can be
  resolved by looking at ordinal 100.

This script parses that block exactly, prints ordinal->name, and prints
the neighbourhood of ordinal 100. It also prints what BD_* names sit at
values 17 and 100 so the '[100]' question is answered with evidence.
"""
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXE = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
MODULE_BASE = 0x00400000

# start of the contiguous BD_ name block (first token = BD_NO_ERROR)
BLOCK_START = 0x6CD744


def load(p):
    with open(p, "rb") as fh:
        return fh.read()


def main():
    exe = load(EXE)
    end = exe.find(b"BD_AUTH_STEAM_PUBLISHER_BAN")
    end = exe.find(b"\x00", end) + 1
    block = exe[BLOCK_START:end]
    toks = [t.decode("ascii") for t in block.split(b"\x00") if t]
    print("block file 0x%06X..0x%06X  VA 0x%08X..0x%08X  tokens %d" % (
        BLOCK_START, end, MODULE_BASE + BLOCK_START, MODULE_BASE + end, len(toks)))

    # padding check: sum(len(tok)+1) must equal block length if contiguous
    reclaimed = sum(len(t) + 1 for t in toks)
    print("block bytes %d, bytes if contiguous %d, padding bytes %d" % (
        len(block), reclaimed, len(block) - reclaimed))

    print("")
    print("ordinal -> name (selected)")
    for i in (0, 1, 2, 3, 4, 17, 18, 19, 20, 21, 22, 23, 24):
        if i < len(toks):
            print("   [%3d] %s" % (i, toks[i]))
    print("")
    print("neighbourhood of ordinal 100")
    for i in range(max(0, 100 - 6), min(len(toks), 100 + 7)):
        mark = "   <<<<<<<<<< index 100" if i == 100 else ""
        print("   [%3d] %s%s" % (i, toks[i], mark))

    print("")
    print("is 'BD_LOBBY_PROTOCOL_VERSION_FAILURE' at 17?  %s" % (
        toks[17] if len(toks) > 17 else "(out of range)"))
    print("is ordinal 100 one of the BD_LOBBY_* family?  %s" % (
        toks[100].startswith("BD_LOBBY_") if len(toks) > 100 else "(out of range)"))
    print("ordinal 100 name = %s" % (toks[100] if len(toks) > 100 else "(out of range)"))


if __name__ == "__main__":
    main()
