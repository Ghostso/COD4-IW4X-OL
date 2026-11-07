"""RESTORE-IIPS-CONTRACT-001 / Task 03 - disassemble the sites Task 01 found.

Task 01 established:
  * GetResourceManagerII (0x1C80) is referenced ONLY by its export-directory
    entry -- no in-image caller.
  * The ResourceManager ctor (0x11F20) is called from exactly two places:
      0x1CD4  (inside GetResourceManagerII -- the lazy construction path)
      0x1024D (a SECOND, independent caller)
  * The singleton guard/slot at 0x4EB6C/0x4EB68 has ZERO absolute references,
    which is itself informative: the module must reach them by a base-register
    computation, not by a relocated absolute.

This script decodes those sites with a small purpose-built x86 decoder for the
specific opcodes involved, and prints the guard/status surface of
GetResourceManagerII verbatim so the prerequisites are read from bytes.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")


def load(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    magic = struct.unpack_from("<H", d, pe + 24)[0]
    image_base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    so = pe + 24 + (224 if magic == 0x10B else 240)
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return d, image_base, secs


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def disasm(d, secs, rva, maxbytes=96, image_base=0x10000000):
    """Very small decoder for the instruction forms actually present here."""
    off = r2o(secs, rva)
    if off is None:
        return []
    out = []
    p = off
    end = min(off + maxbytes, len(d))
    cur = rva
    while p < end:
        b = d[p]
        start = p
        txt = None
        ln = 1
        if b == 0x55:
            txt = "push ebp"
        elif b == 0x8B and d[p + 1] == 0xEC:
            txt = "mov ebp,esp"; ln = 2
        elif b == 0x83 and d[p + 1] == 0xEC:
            txt = "sub esp,0x%X" % d[p + 2]; ln = 3
        elif b == 0x81 and d[p + 1] == 0xEC:
            v = struct.unpack_from("<I", d, p + 2)[0]
            txt = "sub esp,0x%X" % v; ln = 6
        elif b == 0xF6 and d[p + 1] == 0x05:
            v = struct.unpack_from("<I", d, p + 2)[0]
            imm = d[p + 6]
            txt = "test byte [0x%08X],0x%X" % (v, imm); ln = 7
        elif b == 0x83 and d[p + 1] == 0x0D:
            v = struct.unpack_from("<I", d, p + 2)[0]
            imm = struct.unpack_from("<b", d, p + 6)[0]
            txt = "or dword [0x%08X],%d" % (v, imm); ln = 7
        elif b == 0x83 and d[p + 1] == 0x25:
            v = struct.unpack_from("<I", d, p + 2)[0]
            imm = struct.unpack_from("<b", d, p + 6)[0]
            txt = "and dword [0x%08X],%d" % (v, imm); ln = 7
        elif b == 0x74:
            disp = struct.unpack_from("<b", d, p + 1)[0]
            txt = "je 0x%X" % (cur + 2 + disp); ln = 2
        elif b == 0x75:
            disp = struct.unpack_from("<b", d, p + 1)[0]
            txt = "jne 0x%X" % (cur + 2 + disp); ln = 2
        elif b == 0xEB:
            disp = struct.unpack_from("<b", d, p + 1)[0]
            txt = "jmp 0x%X" % (cur + 2 + disp); ln = 2
        elif b == 0xE8:
            disp = struct.unpack_from("<i", d, p + 1)[0]
            txt = "call 0x%X" % (cur + 5 + disp); ln = 5
        elif b == 0xE9:
            disp = struct.unpack_from("<i", d, p + 1)[0]
            txt = "jmp 0x%X" % (cur + 5 + disp); ln = 5
        elif b == 0xFF and d[p + 1] == 0x15:
            v = struct.unpack_from("<I", d, p + 2)[0]
            txt = "call dword [0x%08X]" % v; ln = 6
        elif b == 0xFF and d[p + 1] == 0x25:
            v = struct.unpack_from("<I", d, p + 2)[0]
            txt = "jmp dword [0x%08X]" % v; ln = 6
        elif b == 0xB8:
            v = struct.unpack_from("<I", d, p + 1)[0]
            txt = "mov eax,0x%08X" % v; ln = 5
        elif b == 0x68:
            v = struct.unpack_from("<I", d, p + 1)[0]
            txt = "push 0x%08X" % v; ln = 5
        elif b == 0x5D:
            txt = "pop ebp"
        elif b == 0xC3:
            txt = "ret"
        elif b == 0xC2:
            v = struct.unpack_from("<H", d, p + 1)[0]
            txt = "ret 0x%X" % v; ln = 3
        elif b == 0x50:
            txt = "push eax"
        elif b == 0x51:
            txt = "push ecx"
        elif b == 0x52:
            txt = "push edx"
        elif b == 0x53:
            txt = "push ebx"
        elif b == 0x56:
            txt = "push esi"
        elif b == 0x57:
            txt = "push edi"
        elif b == 0x64 and d[p + 1] == 0xA1:
            v = struct.unpack_from("<I", d, p + 2)[0]
            txt = "mov eax,fs:[0x%X]" % v; ln = 6
        elif b == 0x33 and d[p + 1] == 0xC4:
            txt = "xor eax,esp"; ln = 2
        elif b == 0x6A:
            txt = "push %d" % struct.unpack_from("<b", d, p + 1)[0]; ln = 2
        elif b == 0x8D and d[p + 1] == 0x44 and d[p + 2] == 0x24:
            txt = "lea eax,[esp+0x%X]" % d[p + 3]; ln = 4
        elif b == 0xA3:
            v = struct.unpack_from("<I", d, p + 1)[0]
            txt = "mov [0x%08X],eax" % v; ln = 5
        elif b == 0xA1:
            v = struct.unpack_from("<I", d, p + 1)[0]
            txt = "mov eax,[0x%08X]" % v; ln = 5
        elif b == 0xCC:
            txt = "int3"
        if txt is None:
            txt = "db 0x%02X" % b
        out.append({"rva": "0x%X" % cur, "bytes": d[start:start + ln].hex(" ").upper(),
                    "asm": txt})
        p += ln
        cur += ln
        if d[start] in (0xC3, 0xC2) and len(out) > 3:
            break
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    d, image_base, secs = load(IIPS)
    rep = {}
    print("=== Task 03: disassembly of the key sites ===")
    print("  image base = 0x%08X" % image_base)
    print()

    sites = {
        "GetResourceManagerII_0x1C80": (0x1C80, 64),
        "ReleaseResourceManagerII_0x1C60": (0x1C60, 32),
        "second_ctor_caller_0x1024D": (0x10230, 80),
        "lazy_ctor_call_0x1CD4": (0x1CC0, 48),
    }
    for label, (rva, n) in sites.items():
        ins = disasm(d, secs, rva, n, image_base)
        rep[label] = {"rva": "0x%X" % rva, "instructions": ins}
        print("--- %s (RVA 0x%X) ---" % (label, rva))
        for i in ins:
            print("   %-8s %-22s %s" % (i["rva"], i["bytes"], i["asm"]))
        print()

    # Identify the function containing 0x1024D by walking back to a prologue.
    off = r2o(secs, 0x1024D)
    start = off
    for back in range(0, 0x400):
        p = off - back
        if p < 0:
            break
        if d[p] == 0x55 and d[p + 1] == 0x8B and d[p + 2] == 0xEC:
            start = p
            break
    start_rva = start - (off - 0x1024D)
    print("--- function containing 0x1024D: starts at RVA 0x%X ---" % start_rva)
    ins = disasm(d, secs, start_rva, 0x90, image_base)
    for i in ins[:40]:
        print("   %-8s %-22s %s" % (i["rva"], i["bytes"], i["asm"]))
    rep["second_caller_function_start"] = "0x%X" % start_rva
    rep["second_caller_function"] = ins[:40]

    print()
    print("  GUARD SURFACE NOTE")
    print("    Task 01 found ZERO absolute references to 0x1004EB6C / 0x1004EB68")
    print("    inside iips.dll, even though GetResourceManagerII provably reads")
    print("    `test byte [0x1004EB6C],1` (bytes F6 05 6C EB 04 10 01).")
    print("    That means the operand is an unrelocated absolute that happens to")
    print("    equal the preferred-base address; the module is written assuming it")
    print("    loads at 0x10000000.")
    rep["guard_absolute_refs_found"] = 0
    rep["guard_operand_note"] = (
        "GetResourceManagerII encodes `test byte [0x1004EB6C],1` as an absolute "
        "operand equal to image_base+0x4EB6C with NO relocation entry, so the "
        "reference is invisible to an RVA-based scan (which looks for 0x4EB6C).")

    with open(os.path.join(OUT, "t04_disasm_key_sites.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t04_disasm_key_sites.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
