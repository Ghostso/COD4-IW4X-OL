#!/usr/bin/env python3
"""Capture the rendered CODOL client window without exposing the desktop."""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import sys
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab


TARGET_NAME = "codoMP_client_shipRetail.exe"
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
window_enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = (window_enum_proc, wintypes.LPARAM)
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
user32.GetClientRect.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
)
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL


def process_name(pid: int) -> str | None:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return Path(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)


def find_window(requested_pid: int | None) -> tuple[int, int] | None:
    matches: list[tuple[int, int, int]] = []

    @window_enum_proc
    def visit(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if requested_pid is not None:
            selected = pid.value == requested_pid
        else:
            selected = (process_name(pid.value) or "").lower() == TARGET_NAME.lower()
        if selected:
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
            matches.append((pid.value, hwnd, area))
        return True

    if not user32.EnumWindows(visit, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    if not matches:
        return None
    pid, hwnd, _area = max(matches, key=lambda entry: (entry[0], entry[2]))
    return pid, hwnd


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help=f"Defaults to the newest visible {TARGET_NAME} window")
    parser.add_argument("--output", type=Path)
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    match = find_window(args.pid)
    if match is None:
        print(f"No visible {TARGET_NAME} window was found.", file=sys.stderr)
        return 2

    pid, hwnd = match
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = (args.output or args.repository / "diagnostics" / f"codol_window_{stamp}.png").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(window=hwnd).save(output)
    print(f"Captured PID {pid}, HWND 0x{hwnd:X}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
