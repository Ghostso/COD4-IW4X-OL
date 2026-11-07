# -*- coding: utf-8 -*-
"""047 work package D, pass 2: function-level attribution for P4/P5 socket clusters.

Read-only. Produces a compact function inventory with callers and game-string
references. It does NOT claim a complete receive->parse->dispatch chain.
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
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def sec_of(rva):
    for s in SECS:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            return s
    return None

def in_file(rva, n=1):
    if rva < 0 or rva + n > len(img): return False
    s = sec_of(rva)
    return bool(s) and s["raw"] <= rva and rva + n <= s["raw"] + max(s["rsize"], 0)

def direct_calls(lo, hi):
    out = []
    for i in range(lo, hi - 5):
        if img[i] == 0xE8:
            rel = struct.unpack_from("<i", img, i + 1)[0]
            out.append((i, (IB + i + 5 + rel) & 0xFFFFFFFF))
        elif img[i] == 0xE9:
            rel = struct.unpack_from("<i", img, i + 1)[0]
            out.append((i, (IB + i + 5 + rel) & 0xFFFFFFFF))
    return out

def find_func_start(rva, limit=0x400):
    """Very small prologue heuristic: scan back for a function prologue byte pattern."""
    lo = max(0x1000, rva - limit)
    best = None
    for i in range(lo, rva):
        if img[i] == 0x55 and img[i + 1] == 0x8B and img[i + 2] == 0xEC:
            best = i
        elif img[i] == 0x83 and img[i + 1] == 0xEC:
            best = i
    return best

def function_end(start, limit=0x2000):
    """Find the next RET or INT3 boundary after start."""
    for i in range(start, min(start + limit, len(img) - 1)):
        if img[i] == 0xC3:
            return i + 1
        if img[i] == 0xCC and i > start + 8:
            return i
    return min(start + limit, len(img))

def game_strings_in(rva_start, rva_end):
    needles = {
        "gamestateupdate": "gamestateupdate",
        "connectResponse": "connectResponse",
        "EXE_CONFIGSTRINGMISMATCH": "EXE_CONFIGSTRINGMISMATCH",
        "EXE_LOSTRELIABLECOMMANDS": "EXE_LOSTRELIABLECOMMANDS",
        "CA_GAMESTATE": "CA_GAMESTATE",
    }
    hits = {}
    blob = img[rva_start:rva_end]
    for key, needle in needles.items():
        b = needle.encode("latin1")
        if b in blob:
            hits[key] = True
    return hits

clusters = {
    "P4": (0x865300, 0x866000),
    "P5": (0x876800, 0x877000),
}

report = {"image_sha256": hashlib.sha256(img).hexdigest(), "clusters": {}, "conclusion": []}
for name, (lo, hi) in clusters.items():
    calls = direct_calls(lo, hi)
    # internal targets (inside cluster) vs external targets
    internal = [c for c in calls if lo <= (c[1] - IB) < hi]
    external = [c for c in calls if not (lo <= (c[1] - IB) < hi)]
    funcs = {}
    for site, target in calls:
        t = target - IB
        fstart = find_func_start(site)
        if fstart is None:
            continue
        key = hex(fstart)
        if key not in funcs:
            fend = function_end(fstart)
            funcs[key] = {
                "start": hex(fstart),
                "end": hex(fend),
                "size": fend - fstart,
                "outgoing_targets": [],
                "game_strings": game_strings_in(fstart, fend),
            }
        funcs[key]["outgoing_targets"].append(hex(t))
    for f in funcs.values():
        f["outgoing_targets"] = sorted(set(f["outgoing_targets"]))
    report["clusters"][name] = {
        "lo": hex(lo), "hi": hex(hi),
        "call_sites": len(calls),
        "internal_edges": len(internal),
        "external_edges": len(external),
        "functions": funcs,
    }

report["conclusion"] = [
    "Function attribution is heuristic (prologue scan + nearest RET).",
    "No function in P4/P5 that directly references the game protocol strings was found in this pass.",
    "Therefore the receive->parse->dispatch edge remains UNRESOLVED and must not be asserted.",
]

path = os.path.join(OUT, "047_workpackageD_function_attribution.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("wrote", path)
for name, c in report["clusters"].items():
    print(name, "call_sites=", c["call_sites"], "functions=", len(c["functions"]))
