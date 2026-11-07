import json, struct, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

def pe(path):
    p = Path(path)
    if not p.is_file():
        return {"path": str(p), "exists": False}
    d = p.read_bytes()
    if d[:2] != b"MZ":
        return {"path": str(p), "exists": True, "note": "not PE"}
    peoff = struct.unpack_from("<I", d, 0x3C)[0]
    machine, nsec, ts = struct.unpack_from("<HHI", d, peoff + 4)
    opt = peoff + 24
    magic = struct.unpack_from("<H", d, opt)[0]
    is64 = magic == 0x20B
    size_of_image = struct.unpack_from("<I", d, opt + 56)[0]
    image_base = struct.unpack_from("<Q", d, opt + 24)[0] if is64 else struct.unpack_from("<I", d, opt + 28)[0]
    entry = struct.unpack_from("<I", d, opt + 16)[0]
    return {"path": str(p), "exists": True, "fileSize": p.stat().st_size,
            "machine": hex(machine), "sectionCount": nsec,
            "timeDateStamp": "0x%08X" % ts, "sizeOfImage": "0x%08X" % size_of_image,
            "imageBase": hex(image_base), "entryRva": "0x%08X" % entry,
            "matchesExpected": (ts == 0x6096930A and size_of_image == 0x0E5D6000)}

targets = [
    r"E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe",
    r"E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetailBase.dll",
    r"C:\Games\OLfinal\out.exe",
    r"C:\Games\OLfinal\codoMP_client_shipRetailBase.dll",
]
out = {"expected": {"timeDateStamp": "0x6096930A", "sizeOfImage": "0x0E5D6000",
                    "source": "src/game_server/EngineBindings.hpp:438-439"}, "probed": [pe(t) for t in targets]}
print(json.dumps(out, ensure_ascii=False, indent=2))
print("--- searching for out.exe on C:/D:/E: ---")
for drive in ("C:/Games", "D:/", "E:/"):
    base = Path(drive)
    if not base.is_dir():
        continue
    for cand in base.rglob("out.exe"):
        st = cand.stat()
        print(cand, st.st_size)
