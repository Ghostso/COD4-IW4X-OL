#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump the text of the game's "致命错误" dialog while it is on screen.

The DW observer only records the top-level window title, so the body of the
WIN_ERROR dialog (which carries the real reason) was never captured.  This
polls for that dialog and enumerates every child control's text.

Usage:
  python -X utf8 _fatal_dialog_probe.py --seconds 200 --out dialog.txt
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import sys
import time

u32 = ctypes.windll.user32

TARGET_TITLES = ("致命错误", "Fatal Error", "Error")


def wtext(hwnd) -> str:
    n = u32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 2)
    u32.GetWindowTextW(hwnd, buf, n + 2)
    return buf.value


def wclass(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def children(hwnd):
    out = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, _l):
        out.append((h, wclass(h), wtext(h)))
        return True

    u32.EnumChildWindows(hwnd, CB(cb), 0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=200.0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    seen = set()
    deadline = time.time() + a.seconds
    lines = []
    while time.time() < deadline:
        found = []
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

        def cb(h, _l):
            if not u32.IsWindowVisible(h):
                return True
            cls = wclass(h)
            txt = wtext(h)
            if cls == "#32770" or txt in TARGET_TITLES:
                found.append((h, cls, txt))
            return True

        u32.EnumWindows(CB(cb), 0)
        for h, cls, txt in found:
            if h in seen:
                continue
            seen.add(h)
            pid = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            rec = ["DIALOG hwnd=0x%X class=%s title=%r pid=%d"
                   % (h, cls, txt, pid.value)]
            for ch, ccls, ctxt in children(h):
                rec.append("    child class=%-24s text=%r" % (ccls, ctxt))
            block = "\n".join(rec)
            lines.append(block)
            print(block, flush=True)
        time.sleep(0.25)

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write("\n\n".join(lines) + "\n")
    print("done, dialogs=%d" % len(lines), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
