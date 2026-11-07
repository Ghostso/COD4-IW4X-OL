"""Capture the primary desktop to a real PNG.

PrintWindow returns black for DirectX game windows, so this uses a
desktop BitBlt instead. The target game window (class CODO) is brought
to the foreground before the grab.

Usage: python -X utf8 _pop_desktop_shot.py OUT.png [PID]
"""
import ctypes
import ctypes.wintypes as wt
import sys

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32


class RECT(ctypes.Structure):
    _fields_ = [("L", ctypes.c_long), ("T", ctypes.c_long),
                ("R", ctypes.c_long), ("B", ctypes.c_long)]


def find_game_hwnd(pid):
    hits = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        if not u32.IsWindowVisible(h):
            return True
        cn = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(h, cn, 256)
        if cn.value == "CODO":
            hits.append(h)
        return True

    u32.EnumWindows(EnumProc(cb), 0)
    return hits[0] if hits else None


def main():
    out = sys.argv[1]
    pid = int(sys.argv[2]) if len(sys.argv) > 2 else None
    hwnd = find_game_hwnd(pid) if pid else None
    if hwnd:
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, 9)
        u32.SetForegroundWindow(hwnd)
        ctypes.windll.kernel32.Sleep(600)
    w = u32.GetSystemMetrics(0)
    h = u32.GetSystemMetrics(1)
    hdc = u32.GetDC(0)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    SRCCOPY = 0x00CC0020
    ok = g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, SRCCOPY)
    if not ok:
        print("BitBlt failed")
        return 2

    class BMI(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                    ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                    ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                    ("biClrImportant", wt.DWORD)]

    bi = BMI()
    bi.biSize = ctypes.sizeof(BMI)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bufsz = w * h * 4
    buf = ctypes.create_string_buffer(bufsz)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    hdr = (b"BM" + (bufsz + 54).to_bytes(4, "little") + b"\x00\x00\x00\x00" +
           (54).to_bytes(4, "little") + (40).to_bytes(4, "little") +
           w.to_bytes(4, "little") + h.to_bytes(4, "little") +
           (1).to_bytes(2, "little") + (32).to_bytes(2, "little") +
           (0).to_bytes(4, "little") + bufsz.to_bytes(4, "little") + b"\x00" * 16)
    with open(out, "wb") as f:
        f.write(hdr)
        f.write(buf.raw)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(0, hdc)
    print("saved %s (%dx%d) hwnd=%s" % (out, w, h, hex(hwnd) if hwnd else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
