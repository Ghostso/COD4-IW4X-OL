"""Agent 01/02 - disassemble the REAL GetResourceManagerII / ReleaseResourceManagerII
from the original iips.dll and derive the calling convention from the machine code
instead of from a hand-written C++ sketch.

Read-only.
"""
import capstone
import pefile
import struct

ORIG = r"COD OL\IIPS\iips.dll"

EXPORTS = {
    "GetResourceManager": 0x1BC0,
    "ReleaseResourceManagerII": 0x1C60,
    "ReleaseResourceManager": 0x1C60,
    "GetResourceManagerII": 0x1C80,
}


def main():
    pe = pefile.PE(ORIG, fast_load=True)
    data = open(ORIG, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True

    for name, rva in sorted(EXPORTS.items(), key=lambda kv: kv[1]):
        off = pe.get_offset_from_rva(rva)
        print("=" * 78)
        print("%s  RVA 0x%X  file 0x%X" % (name, rva, off))
        print("=" * 78)
        code = data[off:off + 0x120]
        for insn in md.disasm(code, 0x10000000 + rva):
            mark = ""
            m = insn.mnemonic
            op = insn.op_str
            # highlight stack / call structure
            if m.startswith("ret"):
                mark = "   <-- return / stack cleanup"
            if m == "call":
                mark = "   <-- call"
            print("  0x%08X  %-8s %s%s" % (insn.address, m, op, mark))
            if m.startswith("ret"):
                break
        print()

    print("=" * 78)
    print("CALLING-CONVENTION EVIDENCE (x86)")
    print("=" * 78)
    print("""
  __stdcall : callee cleans the stack -> epilogue is  `ret 0xN`
              argument at [esp+4] because the CALL pushed the return address
  __cdecl   : caller cleans the stack -> epilogue is  `ret`

  So the decisive byte is the `ret imm16` form (opcode 0xC2) versus
  the plain `ret` (opcode 0xC3).
""")

    for name, rva in sorted(EXPORTS.items(), key=lambda kv: kv[1]):
        off = pe.get_offset_from_rva(rva)
        last = None
        for insn in md.disasm(data[off:off + 0x120], 0):
            if insn.mnemonic.startswith("ret"):
                last = insn
                break
        if last is None:
            print("  %-26s no ret found" % name)
            continue
        kind = "ret imm16" if last.bytes[0] == 0xC2 else "ret"
        extra = struct.unpack_from("<H", last.bytes, 1)[0] if last.bytes[0] == 0xC2 else 0
        conv = ("__stdcall (callee cleans %d bytes = %d args)"
                % (extra, extra // 4)) if extra else "cdecl-like (caller cleans)"
        print("  %-26s epilogue %-9s bytes=%-10s -> %s"
              % (name, kind, last.bytes.hex(), conv))

    pe.close()


if __name__ == "__main__":
    main()
