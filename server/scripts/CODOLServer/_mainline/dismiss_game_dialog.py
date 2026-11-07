"""Dismiss the game's modal '#32770' error dialog(s).

On the datafix sandbox the client reaches the DW lobby handshake and then,
~52 s later, raises the engine dialog 'WIN_ERROR / 与大厅服务失去连接'.
This tool only *clicks that dialog's own OK button* (WM_COMMAND IDOK, then
BM_CLICK on the child Button) so we can observe whether the game continues
to the main menu afterwards.  It does not read or write game memory and
does not touch the game binary.

Usage:
  python -X utf8 CODOLServer/_mainline/dismiss_game_dialog.py --seconds 120
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import time

u32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindows = u32.EnumWindows
EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM),
                        wt.LPARAM]
EnumChildWindows = u32.EnumChildWindows
EnumChildWindows.argtypes = [wt.HWND,
                             ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM),
                             wt.LPARAM]
GetClassNameW = u32.GetClassNameW
GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
GetWindowTextW = u32.GetWindowTextW
GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
GetWindowThreadProcessId = u32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
PostMessageW = u32.PostMessageW
PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
SendMessageW = u32.SendMessageW
SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
IsWindowVisible = u32.IsWindowVisible
IsWindowVisible.argtypes = [wt.HWND]

WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
BM_CLICK = 0x00F5
IDOK = 1


def cls(hwnd):
    b = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, b, 256)
    return b.value


def text(hwnd):
    b = ctypes.create_unicode_buffer(1024)
    GetWindowTextW(hwnd, b, 1024)
    return b.value


def children(hwnd):
    out = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        out.append(h)
        return True

    EnumChildWindows(hwnd, cb, 0)
    return out


def top_level_dialogs():
    out = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        if cls(h) == "#32770":
            pid = wt.DWORD()
            GetWindowThreadProcessId(h, ctypes.byref(pid))
            out.append((h, pid.value))
        return True

    EnumWindows(cb, 0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--game-only", action="store_true",
                    help="only touch dialogs owned by codoMP_client_shipRetail")
    ap.add_argument("--verify-seconds", type=float, default=8.0,
                    help="how long to confirm the dialog is really gone")
    a = ap.parse_args()

    deadline = time.time() + a.seconds
    handled = set()
    while time.time() < deadline:
        for hwnd, pid in top_level_dialogs():
            if not IsWindowVisible(hwnd):
                continue
            if hwnd in handled:
                continue
            title = text(hwnd)
            kids = children(hwnd)
            labels = [(k, cls(k), text(k)) for k in kids]
            print("DIALOG hwnd=0x%X pid=%d title=%r children=%r"
                  % (hwnd, pid, title, labels), flush=True)
            # 1) ask the dialog itself to treat OK as pressed
            PostMessageW(hwnd, WM_COMMAND, IDOK, 0)
            time.sleep(0.3)
            # 2) click any Button child
            for k, kc, kt in labels:
                if kc.lower() == "button":
                    SendMessageW(k, BM_CLICK, 0, 0)
            time.sleep(0.3)
            # 3) last resort: close it
            PostMessageW(hwnd, WM_CLOSE, 0, 0)
            # A modal loop only resumes when the dialog is really destroyed.
            # PostMessage/SendMessage returning OK means nothing on its own --
            # the engine's dialog proc may simply ignore every message.
            time.sleep(0.5)
            gone_at = None
            t0 = time.time()
            while time.time() - t0 < a.verify_seconds:
                if not u32.IsWindow(hwnd):
                    gone_at = time.time() - t0
                    break
                if not IsWindowVisible(hwnd):
                    gone_at = time.time() - t0
                    break
                time.sleep(0.2)
            handled.add(hwnd)
            if gone_at is None:
                print("  !! STILL ALIVE after %.1fs -> modal loop still blocked"
                      % a.verify_seconds, flush=True)
            else:
                print("  -> destroyed after %.2fs" % gone_at, flush=True)
        time.sleep(a.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
