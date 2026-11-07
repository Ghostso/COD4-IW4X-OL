"""Find code that writes a value to [reg+0xC8] (the lobby state field).

The reset shows up as c8=4, so look for immediates and register stores into
that offset.  Both `mov dword [reg+0xC8], 4` and `mov [reg+0xC8], reg`
patterns are reported so the writer can be identified.
"""
from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

IMAGE = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x401000
TEXT_END = 0xE65000
LO, HI = 0xBA0000, 0xBB0000


def main() -> int:
    data = IMAGE.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.skipdata = True
    hits = 0
    for insn in md.disasm(data[BASE - 0x400000:TEXT_END - 0x400000], BASE):
        if not (LO <= insn.address < HI):
            continue
        ops = insn.op_str
        if "+ 0xc8]" not in ops:
            continue
        if not ops.startswith("dword ptr ["):
            continue
        hits += 1
        print(f"{insn.address:08X}  {insn.bytes.hex():<20} "
              f"{insn.mnemonic:<7} {ops}")
    print("total", hits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
