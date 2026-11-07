# -*- coding: utf-8 -*-
"""High-rate desktop BitBlt capture plus game-process timeline."""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import time

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


class BMI(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


def shots(path):
    def cb(h, l):
        if not u32.IsWindowVisible(h):
            return True
        cn = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(h, cn, 256)
        if cn.value == "CODO":
            try:
                if u32.IsIconic(h):
                    u32.ShowWindow(h, 9)
                u32.SetForegroundWindow(h)
            except Exception:
                pass
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    w = u32.GetSystemMetrics(0)
    h = u32.GetSystemMetrics(1)
    hdc = u32.GetDC(0)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    ok = g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)
    if not ok:
        g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0, hdc)
        return False
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
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(buf.raw)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0, hdc)
    return True


def pid_names():
    out = []
    try:
        r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            p = [x.strip('"') for x in line.split('","')]
            if len(p) >= 1 and p[0].lower() == "codomp_client_shipretail.exe":
                if len(p) >= 2:
                    out.append(p[1])
    except Exception:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=150.0)
    ap.add_argument("--every", type=float, default=1.0)
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "shots"), exist_ok=True)
    tl = open(os.path.join(args.out, "timeline.jsonl"), "w", encoding="utf-8")
    t0 = time.time()
    n = 0
    last = 0.0
    seen = None
    while time.time() - t0 < args.seconds:
        el = time.time() - t0
        ps = pid_names()
        key = tuple(ps)
        if key != seen:
            seen = key
            rec = {"t": round(el, 2), "pids": ps}
            json.dump(rec, tl, ensure_ascii=False); tl.write("\n"); tl.flush()
            print(json.dumps(rec), flush=True)
        if el - last >= args.every:
            last = el
            p = os.path.join(args.out, "shots", "shot_%07.2f.bmp" % el)
            if shots(p):
                n += 1
                if n % 10 == 0:
                    print("shots=%d t=%.1f" % (n, el), flush=True)
        time.sleep(0.2)
    tl.close()
    print("done shots=%d" % n, flush=True)


if __name__ == "__main__":
    main()
