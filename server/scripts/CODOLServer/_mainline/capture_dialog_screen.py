"""Capture the visible '提示' dialog with screen pixels, not PrintWindow.

Usage:
  python -X utf8 CODOLServer/_mainline/capture_dialog_screen.py --out <dir>
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import time
from pathlib import Path

from PIL import ImageGrab


u32 = ctypes.windll.user32
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def text(hwnd) -> str:
    n = u32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 2)
    u32.GetWindowTextW(hwnd, buf, n + 2)
    return buf.value


def cls(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def child_texts(hwnd):
    out = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, _l):
        out.append((cls(h), text(h)))
        return True

    u32.EnumChildWindows(hwnd, CB(cb), 0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=40.0)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    end = time.time() + args.seconds
    saved = 0
    reports = []
    while time.time() < end:
        found = []

        def cb(h, _l):
            if not u32.IsWindowVisible(h):
                return True
            if cls(h) == "#32770" and text(h) == "提示":
                found.append(h)
            return True

        u32.EnumWindows(EnumProc(cb), 0)
        for h in found:
            pid = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            # Bring the dialog to the foreground so the pixels are not
            # occluded by another window before we grab them.
            u32.SetForegroundWindow(h)
            u32.BringWindowToTop(h)
            time.sleep(1.5)
            rect = RECT()
            if not u32.GetWindowRect(h, ctypes.byref(rect)):
                continue
            bbox = (rect.left, rect.top, rect.right, rect.bottom)
            rec = {
                "hwnd": hex(int(h)),
                "pid": int(pid.value),
                "rect": bbox,
                "title": text(h),
                "children": child_texts(h),
            }
            reports.append(rec)
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            img.save(out / ("dialog_%d.png" % saved))
            ImageGrab.grab(all_screens=True).save(out / ("screen_%d.png" % saved))
            saved += 1
            break
        if saved:
            break
        time.sleep(0.2)

    (out / "dialog.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    print("saved", saved)
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
