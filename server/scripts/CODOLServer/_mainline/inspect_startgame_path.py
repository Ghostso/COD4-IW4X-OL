"""Read-only offline view of the target build's room/message receive path."""
import os
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def load_regions(path):
    regions = []
    with open(os.path.join(path, "regions.txt"), encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) >= 5:
                regions.append((int(fields[0], 16), int(fields[1], 16), fields[4]))
    return regions


def reader(path):
    cache = {}
    regions = load_regions(path)

    def read(address, size):
        for base, region_size, filename in regions:
            if base <= address and address + size <= base + region_size:
                if base not in cache:
                    with open(os.path.join(path, filename), "rb") as stream:
                        cache[base] = stream.read()
                offset = address - base
                return cache[base][offset:offset + size]
        return None
    return read


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -I inspect_startgame_path.py <memory-region-directory>")
    read = reader(sys.argv[1])
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    targets = [
        (0x007F1060, 0x120, "room push receiver entry"),
        (0x007E7C90, 0x1C0, "room push envelope parser"),
        (0x006371F0, 0x160, "room message channel dispatch"),
        (0x00637000, 0x1F0, "room channel inner handler"),
    ]
    for address, size, label in targets:
        print("\n=== %s 0x%08X ===" % (label, address))
        code = read(address, size)
        if code is None:
            print("UNREADABLE")
            continue
        for instruction in md.disasm(code, address):
            print("%08X %-22s %s %s" % (
                instruction.address, instruction.bytes.hex(),
                instruction.mnemonic, instruction.op_str))
    for index in range(64):
        raw = read(0x082E1458 + index * 4, 4)
        handler = struct.unpack("<I", raw)[0] if raw else None
        if handler:
            print("handler[%d] = 0x%08X" % (index, handler))
    for index in range(47):
        raw = read(0x00636F3C + index * 4, 4)
        branch = struct.unpack("<I", raw)[0] if raw else None
        print("switch[%d] = %s" % (index, hex(branch) if branch else None))
    for name, address in (("match state", 0x0063C5E0),
                          ("state 1 predicate A", 0x0063C550),
                          ("state 1 predicate B", 0x0063C350)):
        code = read(address, 0x200)
        print("\n=== %s 0x%08X ===" % (name, address))
        if code:
            for instruction in md.disasm(code, address):
                print("%08X %-22s %s %s" % (
                    instruction.address, instruction.bytes.hex(),
                    instruction.mnemonic, instruction.op_str))


if __name__ == "__main__":
    main()
