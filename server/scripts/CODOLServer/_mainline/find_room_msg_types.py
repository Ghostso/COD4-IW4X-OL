"""Locate room message constructors by scanning the image for the
'mov dword [reg], vtable_va' pattern directly (C7 0x mov [r], imm32),
then disassembling forward to catch the [reg+4] type store.
Handles both absolute imm32 stores and lea/mov forms.
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

want = ("StartGame", "RoomInfo", "RoomStateUpdated", "MemberDetails", "MemberDetailsNoUpdated",
        "MemberDetailsQuery", "JoinMemberInfos", "ChangeTeam", "ChangeTeamRequest",
        "StartCountingDown", "Ready", "MessageJoin@@", "Leave@@", "JoinRequest", "Vote",
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
    hits = []
    for b, s, f in regions:
        blob = cache.get(b) or cache.setdefault(b, open(os.path.join(D, f), "rb").read())
        # C7 07 xx xx xx xx  = mov dword [edi], imm32   (constructor style)
        # C7 00/01/02/03... follow ModRM with disp=0
        needle = bytes([0xC7])
        off = 0
        while True:
            i = blob.find(needle, off)
            if i < 0 or i + 6 > len(blob):
                break
            off = i + 1
            modrm = blob[i + 1]
            if modrm >> 6 != 0 or (modrm >> 3) & 7 != 0:
                continue
            if blob[i + 2:i + 6] != vt.to_bytes(4, "little"):
                continue
            hits.append(b + i)
    for hit in hits[:4]:
        code = read(hit, 48)
        if not code:
            continue
        insns = list(md.disasm(code, hit))
        for ins in insns[1:10]:
            if ins.mnemonic == "mov" and "+ 4]" in ins.op_str:
                rhs = ins.op_str.split(",")[-1].strip()
                if rhs.startswith("0x") or rhs.lstrip("-").isdigit():
                    print("%-40s vt=0x%08X ctor@0x%08X  type=%s" % (name, vt, hit, rhs))
                    break
