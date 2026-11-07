import sys
from pathlib import Path
import pefile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL")
files = [
    "codoMP_client_shipRetail.exe",
    "codoMP_client_shipRetailBase.dll",
    "TenProxy.dll",
    "TenSLX.dll",
    "TerSafe.dll",
    "libcef.dll",
    "TCJ.dll",
    "TenRpcs.dll",
    "GameRpcs.dll",
    "PolicyProbe.dll",
    "VSDDrvDll.dll",
]

for name in files:
    p = base / name
    if not p.exists():
        continue
    print("\n=====", name, "=====")
    pe = pefile.PE(str(p), fast_load=True)
    print("base", hex(pe.OPTIONAL_HEADER.ImageBase))
    print("entry", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint), "entryva", hex(pe.OPTIONAL_HEADER.ImageBase + pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    tls = getattr(pe, "DIRECTORY_ENTRY_TLS", None)
    if tls:
        s = tls.struct
        cb = []
        try:
            cb = [hex(c) for c in (tls.callbacks or [])]
        except Exception as e:
            cb = ["err:" + str(e)]
        print("TLS", "start", hex(s.StartAddressOfRawData), "callbacks_addr", hex(s.AddressOfCallBacks), "callbacks", cb)
    else:
        print("TLS none")
    exp = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if exp:
        syms = []
        for s in exp.symbols[:30]:
            nm = s.name.decode("latin1", "replace") if s.name else None
            syms.append((s.ordinal, nm, hex(pe.OPTIONAL_HEADER.ImageBase + s.address) if s.address else None))
        print("exports", syms)
    else:
        print("exports none")
