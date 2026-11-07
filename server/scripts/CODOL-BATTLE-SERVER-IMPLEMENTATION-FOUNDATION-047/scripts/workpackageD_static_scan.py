# -*- coding: utf-8 -*-
"""047 work package D: read-only static closure attempt for the game socket receive path.

Evidence inputs (read-only):
  - image_best.bin  (recovered image used by 046)
  - 046 evidence/ and scripts/ (method reference)

This script never writes to the image, the client, or 040-046 directories.
Outputs only under 047/evidence/.
"""
import os, sys, struct, json, hashlib

TASK = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047"
WS = r"D:\BaiduNetdiskDownload\使命召唤OL"
IMG = os.path.join(WS, r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
OUT = os.path.join(TASK, "evidence")
os.makedirs(OUT, exist_ok=True)
IB = 0x400000
TOOLCHAIN_NOTE = "read-only analysis of the recovered image; no runtime access"

try:
    import pefile, capstone
except Exception as exc:
    raise SystemExit("missing analysis dependency: %s" % exc)

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
    if rva < 0 or rva + n > len(img):
        return False
    s = sec_of(rva)
    return bool(s) and s["raw"] <= rva and rva + n <= s["raw"] + max(s["rsize"], 0)

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def dis_range(rva, end, max_ins=4000):
    if not in_file(rva, 1):
        return []
    s = sec_of(rva)
    end = min(end, s["raw"] + s["rsize"])
    out = []
    for ins in md.disasm(img[rva:end], IB + rva):
        out.append(ins)
        if len(out) >= max_ins:
            break
    return out

def direct_calls_to(target_rva, lo=0x1000, hi=0x8a7000):
    hits = []
    tva = IB + target_rva
    for i in range(lo, hi - 5):
        if img[i] in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", img, i + 1)[0]
            if (IB + i + 5 + rel) & 0xFFFFFFFF == tva:
                hits.append((i, "call" if img[i] == 0xE8 else "jmp"))
    return hits

def dword_refs(value):
    pat = struct.pack("<I", value & 0xFFFFFFFF)
    hits = []
    i = img.find(pat)
    while i >= 0:
        if sec_of(i) is not None:
            hits.append(i)
        i = img.find(pat, i + 1)
    return hits

def find_string(needle):
    if isinstance(needle, str):
        needle = needle.encode("latin1")
    hits = []
    i = img.find(needle)
    while i >= 0:
        hits.append(i)
        i = img.find(needle, i + 1)
    return hits

# Candidate socket clusters identified by 046.
CLUSTERS = {
    "P4_server_socket_cluster": (0x865300, 0x866000),
    "P5_client_socket_cluster": (0x876800, 0x877000),
}

def scan_cluster(name, lo, hi):
    calls = []
    indirect = []
    for i in range(lo, hi - 6):
        b = img[i]
        if b in (0xE8, 0xE9):
            rel = struct.unpack_from("<i", img, i + 1)[0]
            tgt = (IB + i + 5 + rel) & 0xFFFFFFFF
            calls.append((i, tgt - IB))
        elif b == 0xFF and img[i + 1] in (0x15, 0x25):
            calls.append((i, struct.unpack_from("<I", img, i + 2)[0]))
    return calls

report = {
    "toolchain": TOOLCHAIN_NOTE,
    "image": IMG,
    "image_sha256": hashlib.sha256(img).hexdigest(),
    "image_size": len(img),
    "clusters": {},
    "game_string_xrefs": {},
    "conclusion": [],
}

for name, (lo, hi) in CLUSTERS.items():
    calls = scan_cluster(name, lo, hi)
    callers = {}
    for site, target in calls:
        callers.setdefault(target, []).append(site)
    report["clusters"][name] = {
        "lo": hex(lo), "hi": hex(hi),
        "call_sites": len(calls),
        "distinct_direct_targets": len(callers),
        "top_targets": sorted(((k, len(v)) for k, v in callers.items()), key=lambda kv: -kv[1])[:25],
    }

for needle in ["gamestateupdate", "connectResponse", "EXE_CONFIGSTRINGMISMATCH",
               "EXE_LOSTRELIABLECOMMANDS", "CA_GAMESTATE", "netchan", "clc_", "svc_"]:
    hits = find_string(needle)
    report["game_string_xrefs"][needle] = {
        "string_hits": [hex(h) for h in hits[:12]],
        "dword_ref_count": len(dword_refs(IB + hits[0])) if hits else 0,
    }

report["conclusion"] = [
    "P4/P5 remain candidate socket clusters; this pass counts call sites and targets only.",
    "A direct receive->parse->dispatch chain is still NOT asserted; no opcode or snapshot format is claimed.",
    "Next step: resolve the top targets to functions and test whether their buffers reach the game-string xrefs.",
]

out_path = os.path.join(OUT, "047_workpackageD_static_scan.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps({k: report[k] for k in ("image_size", "conclusion")}, ensure_ascii=False, indent=2))
print("wrote", out_path)
