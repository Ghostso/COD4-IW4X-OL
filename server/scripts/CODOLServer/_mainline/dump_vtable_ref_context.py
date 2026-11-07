"""Disassemble around each vtable reference site to find the constructor
that assigns the wire type byte at [obj+4].
Read-only.
"""
import json
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

D = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\MEMDUMP_20261027_v4\mem"
FIXTURE = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\fixtures\dwroommsg_vtables_20261027.json"

regions = []
for line in open(os.path.join(D, "regions.txt"), encoding="utf-8"):
    if line.startswith("#"):
        continue
    p = line.split()
    if len(p) >= 5:
        regions.append((int(p[0], 16), int(p[1], 16), p[4]))
cache = {}
md = Cs(CS_ARCH_X86, CS_MODE_32)

data = json.load(open(FIXTURE, encoding="utf-8"))
items = data if isinstance(data, list) else data.get("classes", data)

want = ("StartGame", "RoomInfo", "RoomStateUpdated", "MemberDetails@@", "MemberDetailsNoUpdated",
        "MemberDetailsQuery", "JoinMemberInfos", "ChangeTeam@@", "ChangeTeamRequest",
        "StartCountingDown", "Ready@@", "MessageJoin@@", "Leave@@", "JoinRequest", "Vote",
        "InRoomStateChange", "Manifold")


def read(va, n):
    for b, s, f in regions:
        if b <= va and va + n <= b + s:
            if b not in cache:
                cache[b] = open(os.path.join(D, f), "rb").read()
            return cache[b][va - b:va - b + n]
    return None


for it in items:
    name = it.get("name", "")
    if not any(w in name for w in want):
        continue
    vt = it.get("vtable_va")
    if not vt:
        continue
    needle = vt.to_bytes(4, "little")
    sites = []
    for b, s, f in regions:
        blob = cache.get(b) or cache.setdefault(b, open(os.path.join(D, f), "rb").read())
        off = 0
        while True:
            i = blob.find(needle, off)
            if i < 0:
                break
            sites.append(b + i)
            off = i + 1
    for site in sites:
        # disassemble 96 bytes starting 32 before the ref
        start = site - 32
        code = read(start, 128)
        if not code:
            continue
        lines = list(md.disasm(code, start))
        # find the instruction containing our dword
        anchor = None
        for ins in lines:
            if ins.address <= site < ins.address + ins.size:
                anchor = ins
                break
        if anchor is None:
            continue
        # print context: anchor plus next 10 instructions
        idx = lines.index(anchor)
        ctx = lines[max(0, idx - 2): idx + 10]
        block = "\n".join("  %08X  %-20s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str) for i in ctx)
        print("===== %s vt=0x%08X site=0x%08X" % (name, vt, site))
        print(block)
        print()
