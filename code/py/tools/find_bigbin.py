import os
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
targets = {241537024: "EXE_241MB", 60327992: "Base.dll_60MB", 7841344: "client_shipRetail"}
found = []
for dp, dns, fns in os.walk(ROOT):
    # skip heavy trees
    if any(x in dp.lower() for x in ("toolchain", "wegame", "\\iw4x\\")):
        dns[:] = []
        continue
    for fn in fns:
        try:
            p = os.path.join(dp, fn)
            sz = os.path.getsize(p)
        except Exception:
            continue
        for t, lab in targets.items():
            if abs(sz - t) <= 4096:
                found.append((lab, sz, p))
for lab, sz, p in found:
    print("%-20s %12d  %s" % (lab, sz, p))
