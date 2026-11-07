from pathlib import Path
import struct
import pefile

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
mods = [
    ROOT / r"COD OL\codoMP_client_shipRetail.exe",
    ROOT / r"COD OL\codoMP_client_shipRetailBase.dll",
    ROOT / r"COD OL\TenProxy.dll",
    ROOT / r"COD OL\TCLS\Client.exe",
    ROOT / r"COD OL\TCLS\ClientBase.dll",
    ROOT / r"COD OL\TCLS\TCLSClient.dll",
    ROOT / r"COD OL\TCLS\SSOPlatform.dll",
    ROOT / r"COD OL\TCLS\tacc_2_1.dll",
    ROOT / r"WeGame\tcls\tcls_core.exe",
]
needles = [b"TCLS_SHAREDMEMEMORY", "TCLS_SHAREDMEMEMORY".encode("utf-16le")]
apis = {"CreateFileMappingW", "CreateFileMappingA", "OpenFileMappingW", "OpenFileMappingA", "MapViewOfFile", "UnmapViewOfFile"}

for path in mods:
    print("\n===== " + str(path.relative_to(ROOT)) + " =====")
    if not path.exists():
        print("MISSING")
        continue
    data = path.read_bytes()
    print("size", len(data), "sha256", __import__('hashlib').sha256(data).hexdigest())
    for needle in needles:
        hits = []
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0: break
            hits.append(i)
            start = i + 1
        print("string", "utf16" if needle[1] == 0 else "ascii", "count", len(hits), "offsets", [hex(x) for x in hits[:20]])
    try:
        pe = pefile.PE(data=data, fast_load=False)
    except Exception as e:
        print("pe parse failed", repr(e))
        continue
    print("imagebase", hex(pe.OPTIONAL_HEADER.ImageBase), "entry", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    found = []
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for ent in pe.DIRECTORY_ENTRY_IMPORT:
            dll = ent.dll.decode(errors="replace") if isinstance(ent.dll, bytes) else str(ent.dll)
            for imp in ent.imports or []:
                if imp.name:
                    n = imp.name.decode(errors="replace")
                    if n in apis:
                        found.append((dll, n, imp.address, hex(imp.address)))
    print("mapping imports", found)
