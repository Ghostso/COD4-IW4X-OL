"""Disassemble the wire format of the room-UI message classes.

vf0 = serialize (write side, what our lobby must construct)
All offsets from local memory dump, build 1649370.
Read-only.
"""
import os
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

API = {0xB77B10: 'writeBits', 0xB777C0: 'writeData', 0xB774E0: 'readBits', 0xB77A70: 'writeBitsCore'}

TARGETS = [
    ("RoomInfo.serialize", 0x00627EA0, 0x200),
    ("RoomStateUpdated.serialize", 0x006285B0, 0x100),
    ("MemberDetails.serialize", 0x006261C0, 0x490),
    ("JoinMemberInfos.serialize", 0x00626960, 0x90),
    ("MemberDetailsNoUpdated.serialize", 0x00626650, 0x310),
    ("ChangeTeam.serialize", 0x006281D0, 0x90),
    ("StartCountingDown.serialize", 0x00628320, 0x120),
]


def load_regions(path):
    regions = []
    with open(os.path.join(path, "regions.txt"), encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("#"):
                continue
            f = line.split()
            if len(f) >= 5:
                regions.append((int(f[0], 16), int(f[1], 16), f[4]))
    return regions


def main():
    path = sys.argv[1]
    cache = {}
    regions = load_regions(path)

    def read(address, size):
        for base, sz, fn in regions:
            if base <= address and address + size <= base + sz:
                if base not in cache:
                    with open(os.path.join(path, fn), "rb") as s:
                        cache[base] = s.read()
                return cache[base][address - base: address - base + size]
        return None

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for label, address, size in TARGETS:
        print("\n===== %s @ 0x%08X =====" % (label, address))
        code = read(address, size)
        if code is None:
            print("UNREADABLE")
            continue
        recent_push = []
        for ins in md.disasm(code, address):
            line = "%08X  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            if ins.mnemonic == "push":
                recent_push.append(ins.op_str)
            if ins.mnemonic == "call":
                try:
                    tgt = int(ins.op_str, 16)
                except ValueError:
                    tgt = None
                if tgt in API:
                    line += "   <<< %s args=%s" % (API[tgt], recent_push[-4:])
                    recent_push = []
                elif tgt is not None:
                    recent_push = []
            print(line)
            if ins.mnemonic == "ret":
                break


if __name__ == "__main__":
    main()
