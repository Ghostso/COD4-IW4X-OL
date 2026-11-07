import json, os, struct, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

WANT_TS, WANT_SIZE = 0x6096930A, 0x0E5D6000

def pe(path):
    try:
        with open(path, "rb") as f:
            d = f.read(0x400)
            if len(d) < 0x40 or d[:2] != b"MZ":
                return None
            peoff = struct.unpack_from("<I", d, 0x3C)[0]
            if peoff + 0x60 > len(d):
                f.seek(0); d = f.read(peoff + 0x200)
            machine, nsec, ts = struct.unpack_from("<HHI", d, peoff + 4)
            opt = peoff + 24
            size_of_image = struct.unpack_from("<I", d, opt + 56)[0]
            return {"machine": hex(machine), "ts": "0x%08X" % ts, "sizeOfImage": "0x%08X" % size_of_image,
                    "match": (ts == WANT_TS and size_of_image == WANT_SIZE)}
    except Exception:
        return None

roots = [r"E:\CODOL_SANDBOX", r"C:\Games", r"F:\桌面\ol", r"D:\BaiduNetdiskDownload\使命召唤OL"]
names = ("out.exe", "codomp_client_shipretail.exe")
found = []
seen = 0
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        if seen > 40000:
            break
        for fn in filenames:
            if fn.lower() in names:
                p = os.path.join(dirpath, fn)
                info = pe(p)
                seen += 1
                if info:
                    try:
                        size = os.path.getsize(p)
                    except OSError:
                        size = None
                    found.append({"path": p, "fileSize": size, **info})
print(json.dumps({"expected": {"ts": "0x6096930A", "sizeOfImage": "0x0E5D6000"}, "candidates": found},
                 ensure_ascii=False, indent=2))
