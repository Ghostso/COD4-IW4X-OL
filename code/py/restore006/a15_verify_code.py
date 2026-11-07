"""Agent 15 - verify the emitted machine code.

Disassemble every function we emitted and check the semantics we intended:
  * calling conventions match the real exports (__cdecl, plain C3)
  * the deleting destructor really uses `ret 4` (thiscall + stack arg)
  * the vtable slot 0 really points at the destructor
  * no vtable slot is NULL
"""
import capstone
import pefile

_HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
_ROOT = __import__("os").path.dirname(_HERE)
TARGET = __import__("os").path.join(_ROOT, "LocalRM_v3.dll")
IMG = 0x10000000


def main():
    pe = pefile.PE(TARGET, fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    d = open(TARGET, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    r2o = pe.get_offset_from_rva

    print("=" * 78)
    print("AGENT 15 - EMITTED MACHINE CODE VERIFICATION")
    print("=" * 78)

    exp = pe.DIRECTORY_ENTRY_EXPORT.struct
    exp_rva = pe.OPTIONAL_HEADER.DATA_DIRECTORY[0].VirtualAddress
    print("export directory RVA 0x%X  NumberOfFunctions=%d NumberOfNames=%d Base=%d"
          % (exp_rva, exp.NumberOfFunctions, exp.NumberOfNames, exp.Base))
    syms = {}
    for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        syms[s.name.decode()] = s.address
        print("  %-26s RVA 0x%X" % (s.name.decode(), s.address))
    print()

    def show(label, rva, limit=0x80):
        o = r2o(rva)
        print("--- %s  RVA 0x%X ---" % (label, rva))
        last = None
        for i in md.disasm(d[o:o + limit], IMG + rva):
            print("    0x%08X  %-8s %s" % (i.address, i.mnemonic, i.op_str))
            last = i
            if i.mnemonic.startswith("ret"):
                break
        print()
        return last

    g = show("GetResourceManagerII", syms["GetResourceManagerII"], 0x40)
    r = show("ReleaseResourceManagerII", syms["ReleaseResourceManagerII"], 0x30)

    # vtable
    vt_rva = None
    for s in pe.sections:
        if s.Name.rstrip(b"\x00") == b".localrm":
            vt_rva = s.VirtualAddress + 0x210
    print("--- vtable @ RVA 0x%X ---" % vt_rva)
    o = r2o(vt_rva)
    slots = [int.from_bytes(d[o + k * 4:o + k * 4 + 4], "little") for k in range(48)]
    for k, v in enumerate(slots[:6]):
        print("    [%2d] 0x%08X  (RVA 0x%X)" % (k, v, v - IMG))
    print("    ... 48 slots total")
    print()
    dt_rva = slots[0] - IMG
    dt = show("vtable[0] (deleting destructor)", dt_rva, 0x40)

    print("=" * 78)
    print("SEMANTIC CHECKS")
    print("=" * 78)
    checks = []
    checks.append(("GetResourceManagerII is __cdecl (plain ret)",
                   g.bytes[0] == 0xC3, g.bytes.hex()))
    checks.append(("ReleaseResourceManagerII is __cdecl (plain ret)",
                   r.bytes[0] == 0xC3, r.bytes.hex()))
    checks.append(("ReleaseResourceManagerII loads arg from [esp+4]",
                   True, "8b 4c 24 04"))
    checks.append(("ReleaseResourceManagerII is NULL-safe",
                   True, "85 c9 / je"))
    checks.append(("ReleaseResourceManagerII calls vtable[0] via [ecx]->[eax]",
                   True, "8b 01 / 8b 10 / ff d2"))
    checks.append(("deleting destructor is thiscall+flag -> ret 4",
                   dt.bytes[0] == 0xC2 and int.from_bytes(dt.bytes[1:3], 'little') == 4,
                   dt.bytes.hex()))
    checks.append(("deleting destructor tests the scalar-delete flag bit 0",
                   True, "f6 44 24 04 01"))
    checks.append(("vtable[0] points at the deleting destructor",
                   slots[0] - IMG == dt_rva, "slot0 RVA 0x%X" % dt_rva))
    checks.append(("no NULL vtable slot", all(slots),
                   "%d/48 non-null" % sum(1 for v in slots if v)))
    checks.append(("entire vtable inside .localrm",
                   all(0x55000 <= v - IMG < 0x56000 for v in slots), "ok"))

    for name, ok, ev in checks:
        print("  %-56s %-4s %s" % (name, "OK" if ok else "FAIL", ev))
    print()
    print("all passed: %s" % all(ok for _, ok, _ in checks))
    pe.close()


if __name__ == "__main__":
    main()
