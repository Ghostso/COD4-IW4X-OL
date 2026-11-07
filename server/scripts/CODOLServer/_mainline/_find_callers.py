"""Print all direct call sites targeting a given VA."""
from __future__ import annotations

import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

IMAGE = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x401000
TEXT_END = 0xE65000


def main() -> int:
    target = int(sys.argv[1], 16)
    data = IMAGE.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.skipdata = True
    for insn in md.disasm(data[BASE - 0x400000:TEXT_END - 0x400000], BASE):
        if insn.mnemonic not in ("call", "jmp"):
            continue
        try:
            dest = int(insn.op_str, 16)
        except ValueError:
            continue
        if dest == target:
            print(f"{insn.address:08X}  {insn.bytes.hex():<20} {insn.op_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
