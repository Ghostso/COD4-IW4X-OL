# -*- coding: utf-8 -*-
"""047 work package D, pass 3: upstream caller BFS from known game-protocol
string xref sites identified by 046.

Read-only. No claim of a complete chain unless a verified handler edge is found.
"""
import os, json, struct, hashlib
import pefile, capstone

TASK = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047"
WS = r"D:\BaiduNetdiskDownload\使命召唤OL"
IMG = os.path.join(WS, r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
OUT = os.path.join(TASK, "evidence")
IB = 0x400000

img = open(IMG, "rb").read()
pe = pefile.PE(data=img, fast_load=False)
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

def callers_of(target_rva, lo=0x1000, hi=0x8a7000):
    out = []
    tva = IB + target_rva
    for i in range(lo, hi - 5):
        if img[i] == 0xE8:
            rel = struct.unpack_from("<i", img, i + 1)[0]
            if (IB + i + 5 + rel) & 0xFFFFFFFF == tva:
                out.append(i)
    return out

def find_func_start(rva, limit=0x600):
    lo = max(0x1000, rva - limit)
    best = None
    for i in range(lo, rva):
        if img[i] == 0x55 and img[i + 1] == 0x8B and img[i + 2] == 0xEC:
            best = i
    return best

# 046-recorded read/dispatch xref sites. These are sites INSIDE functions that
# reference the protocol strings, so they are starting anchors, not handlers.
ANCHORS = {
    "gamestateupdate": [0x54B7B, 0x73214],
    "EXE_CONFIGSTRINGMISMATCH": [0x731E1, 0xF2833],
    "EXE_LOSTRELIABLECOMMANDS": [0xF2737, 0x376B14],
    "connectResponse": [0x1C17B5],
}

report = {"image_sha256": hashlib.sha256(img).hexdigest(), "anchors": {}, "conclusion": []}
for name, sites in ANCHORS.items():
    report["anchors"][name] = {}
    for site in sites:
        if not in_file(site, 1):
            report["anchors"][name][hex(site)] = {"status": "outside_file"}
            continue
        fstart = find_func_start(site)
        if fstart is None:
            report["anchors"][name][hex(site)] = {"status": "no_function_start"}
            continue
        ups = callers_of(fstart)
        report["anchors"][name][hex(site)] = {
            "function_start": hex(fstart),
            "upstream_call_sites": [hex(c) for c in ups],
            "upstream_functions": [hex(find_func_start(c)) if find_func_start(c) is not None else None for c in ups],
        }

report["conclusion"] = [
    "These are upstream caller sets for the functions containing known game-string xrefs.",
    "A function containing a string xref is not yet a read/opcode/handler point.",
    "The receive->parse->dispatch chain remains UNRESOLVED until a buffer-flow edge is proven.",
]

path = os.path.join(OUT, "047_workpackageD_upstream_bfs.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("wrote", path)
for name, d in report["anchors"].items():
    for site, v in d.items():
        n = len(v.get("upstream_call_sites", [])) if isinstance(v, dict) else 0
        print(name, site, "upstream=", n)
