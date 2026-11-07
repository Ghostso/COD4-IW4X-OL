# -*- coding: utf-8 -*-
"""047 work package D, pass 5: strict overlap test.

Question: do any upstream callers of the reliable-command anchor fall inside
the P4/P5 socket clusters or inside any function that directly references the
known game protocol strings?

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

CLUSTERS = {"P4": (0x865300, 0x866000), "P5": (0x876800, 0x877000)}
CALLERS = [0x7A662, 0x7EBEA, 0x7F702, 0x81338, 0x81F57, 0x1B7D11, 0x1B8882,
           0x1B9516, 0x1BAE87, 0x1BC009, 0x1BC5C2, 0x1BC8F1, 0x376B7E]

GAME_STRINGS = {
    "gamestateupdate": 0x9B4700,
    "connectResponse": 0x9BFF0C,
    "EXE_CONFIGSTRINGMISMATCH": 0x9B46E4,
    "EXE_LOSTRELIABLECOMMANDS": 0x9BB5E8,
    "CA_GAMESTATE": 0x9C0974,
}

# Find dword references to each game string.
string_refs = {}
for name, rva in GAME_STRINGS.items():
    pat = struct.pack("<I", IB + rva)
    hits = []
    i = img.find(pat)
    while i >= 0:
        hits.append(i)
        i = img.find(pat, i + 1)
    string_refs[name] = hits

report = {"image_sha256": hashlib.sha256(img).hexdigest(),
          "string_ref_sites": {k: [hex(x) for x in v] for k, v in string_refs.items()},
          "overlaps": {}, "conclusion": []}

for c in CALLERS:
    cluster_hit = [n for n, (lo, hi) in CLUSTERS.items() if lo <= c < hi]
    ref_near = []
    for name, sites in string_refs.items():
        for s in sites:
            if abs(s - c) < 0x800:
                ref_near.append({"string": name, "site": hex(s), "distance": abs(s - c)})
    report["overlaps"][hex(c)] = {"cluster": cluster_hit, "near_string_refs": ref_near}

report["conclusion"] = [
    "Empty overlap means the reliable-command anchor callers are not in P4/P5 and are not near the game-string refs.",
    "This narrows candidates but does NOT identify the receive->parse->dispatch chain.",
]
path = os.path.join(OUT, "047_workpackageD_strict_overlap.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
for c, e in report["overlaps"].items():
    print(c, "cluster=", e["cluster"], "near_refs=", len(e["near_string_refs"]))
