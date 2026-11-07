# -*- coding: utf-8 -*-
"""047 work package D, pass 4b: locate ws2_32 IAT slots by name string scan and
test whether reliable-command upstream callers reference them.

Read-only evidence only.
"""
import os, json, struct, hashlib
import pefile

TASK = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047"
WS = r"D:\BaiduNetdiskDownload\使命召唤OL"
IMG = os.path.join(WS, r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
OUT = os.path.join(TASK, "evidence")
IB = 0x400000

img = open(IMG, "rb").read()
pe = pefile.PE(data=img, fast_load=True)
SECS = [dict(name=s.Name.rstrip(b"\0").decode("latin1"), va=s.VirtualAddress,
             vsize=s.Misc_VirtualSize, raw=s.PointerToRawData, rsize=s.SizeOfRawData)
        for s in pe.sections]

def sec_of(rva):
    for s in SECS:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            return s
    return None

def in_file(rva, n=1):
    if rva < 0 or rva + n > len(img): return False
    s = sec_of(rva)
    return bool(s) and s["raw"] <= rva and rva + n <= s["raw"] + max(s["rsize"], 0)

# Locate hint/name strings for socket APIs.
api_names = ["socket", "recv", "recvfrom", "select", "WSAGetLastError", "send", "sendto", "connect", "bind", "listen", "accept"]
hint_hits = {}
for name in api_names:
    b = name.encode("ascii") + b"\0"
    hits = []
    i = img.find(b)
    while i >= 0:
        hits.append(i)
        i = img.find(b, i + 1)
    hint_hits[name] = [hex(h) for h in hits[:20]]

# Find dword references to each hint string RVA (import descriptors point at these).
iat_candidates = {}
for name, hits in hint_hits.items():
    for h in hits:
        rva = int(h, 16)
        pat = struct.pack("<I", IB + rva)
        i = img.find(pat)
        refs = []
        while i >= 0:
            refs.append(hex(i))
            i = img.find(pat, i + 1)
        if refs:
            iat_candidates.setdefault(name, []).extend(refs[:10])

CALLERS = [0x7A662, 0x7EBEA, 0x7F702, 0x81338, 0x81F57, 0x1B7D11, 0x1B8882,
           0x1B9516, 0x1BAE87, 0x1BC009, 0x1BC5C2, 0x1BC8F1, 0x376B7E]

def find_func_start(rva, limit=0x800):
    lo = max(0x1000, rva - limit)
    best = None
    for i in range(lo, rva):
        if img[i] == 0x55 and img[i+1] == 0x8B and img[i+2] == 0xEC:
            best = i
    return best

report = {"image_sha256": hashlib.sha256(img).hexdigest(),
          "hint_name_hits": hint_hits,
          "import_name_ref_sites": iat_candidates,
          "callers": {},
          "conclusion": []}

for c in CALLERS:
    fs = find_func_start(c)
    fs_hex = hex(fs) if fs else None
    refs = []
    if fs:
        blob = img[fs:fs+0x1200]
        for name, sites in iat_candidates.items():
            for site in sites:
                s_rva = int(site, 16)
                # direct absolute reference to the import name pointer
                if struct.pack("<I", IB + s_rva) in blob:
                    refs.append({"api": name, "ref": site})
    report["callers"][hex(c)] = {"function_start": fs_hex, "import_refs": refs}

report["conclusion"] = [
    "Hint/name strings and their dword refs were located by raw scan.",
    "A missing intersection still does not prove the caller is unrelated; calls may be indirect.",
]
path = os.path.join(OUT, "047_workpackageD_socket_intersection.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("api hint nsites:", {k: len(v) for k, v in iat_candidates.items()})
for c, e in report["callers"].items():
    print(c, e["function_start"], len(e["import_refs"]))
