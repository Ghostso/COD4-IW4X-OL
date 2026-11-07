"""Find all code sites referencing object offsets +0x604 / +0x608."""
from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

IMAGE = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x401000
TEXT_END = 0xBA2000


def main() -> int:
    data = IMAGE.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.skipdata = True
    # Only real memory operands count: [reg+0x604] / [reg+0x608]
    for insn in md.disasm(data[BASE - 0x400000:TEXT_END - 0x400000], BASE):
        ops = insn.op_str
        if ("+ 0x604]" not in ops) and ("+ 0x608]" not in ops):
            continue
        print(f"{insn.address:08X}  {insn.bytes.hex():<20} "
              f"{insn.mnemonic:<7} {ops}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
