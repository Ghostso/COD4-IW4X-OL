"""Agent 03/04/05/06 - derive the real ResourceManager object layout and vtable
ABI from the constructor at RVA 0x11F20 plus the release path at RVA 0x1C60.

Everything here is read out of the ORIGINAL iips.dll machine code; nothing is
taken from the RESTORE_LOCALRM_001/*.cpp sketches.
"""
import capstone
import pefile

ORIG = r"COD OL\IIPS\iips.dll"
CTOR = 0x11F20
RELEASE = 0x1C60


def main():
    pe = pefile.PE(ORIG, fast_load=True)
    d = open(ORIG, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    r2o = pe.get_offset_from_rva
    imgbase = pe.OPTIONAL_HEADER.ImageBase

    print("=" * 78)
    print("AGENT 03 - ResourceManager object layout (from ctor RVA 0x%X)" % CTOR)
    print("=" * 78)
    print("  the constructor receives `this` in [esp+4]; the frame copies it to ebp.")
    print("  every [ebp+disp] below is an offset inside the ResourceManager object.")
    print()
    o = r2o(CTOR)
    n = 0
    for insn in md.disasm(d[o:o + 0x400], imgbase + CTOR):
        if "[ebp" in insn.op_str:
            print("    0x%08X  %-7s %s" % (insn.address, insn.mnemonic, insn.op_str))
            n += 1
            if n >= 40:
                break
    print()

    print("=" * 78)
    print("AGENT 04 - vtable discovery")
    print("=" * 78)
    print("  In flat 32-bit code `mov dword ptr [ebp+disp8], imm32` is C7 45 dd ii ii ii ii.")
    print("  Scanning the whole image for that form with an in-image immediate:")
    print()
    found = []
    for i in range(len(d) - 10):
        if d[i] == 0xC7 and d[i + 1] == 0x45:
            disp = d[i + 2]
            imm = int.from_bytes(d[i + 3:i + 7], "little")
            if imgbase <= imm < imgbase + pe.OPTIONAL_HEADER.SizeOfImage:
                try:
                    rva = pe.get_rva_from_offset(i)
                except Exception:
                    continue
                found.append((rva, disp, imm))
    for rva, disp, imm in found:
        print("    code RVA 0x%06X : [this+0x%02X] = 0x%08X  (target RVA 0x%X)"
              % (rva, disp, imm, imm - imgbase))
    print("  total: %d" % len(found))
    print()

    print("  --- the vtables the ctor installs ---")
    for va in (0x1003929C, 0x1003926C, 0x100344E4):
        rva = va - imgbase
        off = r2o(rva)
        entries = []
        for k in range(80):
            v = int.from_bytes(d[off + k * 4: off + k * 4 + 4], "little")
            if not (imgbase <= v < imgbase + pe.OPTIONAL_HEADER.SizeOfImage):
                break
            entries.append(v)
        print("    vtable @ 0x%08X (RVA 0x%X): %d consecutive in-image pointers"
              % (va, rva, len(entries)))
        for k, v in enumerate(entries[:14]):
            print("        [%2d] 0x%08X  (RVA 0x%X)" % (k, v, v - imgbase))
        if len(entries) > 14:
            print("        ... plus %d more" % (len(entries) - 14))
    print()

    print("=" * 78)
    print("AGENT 06 - vtable[0] destructor ABI (from ReleaseResourceManagerII)")
    print("=" * 78)
    for insn in md.disasm(d[r2o(RELEASE):r2o(RELEASE) + 0x20], imgbase + RELEASE):
        print("  0x%08X  %-7s %s" % (insn.address, insn.mnemonic, insn.op_str))
    print("""
  Decoded:
    mov  ecx, [esp+4]     ; arg1 = the RM object pointer (cdecl stack frame)
    test ecx, ecx
    je   skip             ; NULL-safe
    mov  eax, [ecx]       ; eax = [this+0]  = vtable for THIS release path
    mov  edx, [eax]       ; edx = vtable[0]
    push 1                ; argument for the callee
    call edx              ; vtable[0](this in ecx, 1)
  ret                     ; plain ret -> ReleaseResourceManagerII itself is cdecl
""")

    print("=" * 78)
    print("disassembly of vtable[0] installed at [this+0] by the ctor")
    print("=" * 78)
    va = 0x1003929C
    off = r2o(va - imgbase)
    vt0 = int.from_bytes(d[off:off + 4], "little")
    print("  vtable[0] = [0x%08X] = 0x%08X (RVA 0x%X)" % (va, vt0, vt0 - imgbase))
    fo = r2o(vt0 - imgbase)
    for insn in md.disasm(d[fo:fo + 0x60], vt0):
        print("    0x%08X  %-7s %s" % (insn.address, insn.mnemonic, insn.op_str))
        if insn.mnemonic.startswith("ret"):
            break

    pe.close()


if __name__ == "__main__":
    main()
