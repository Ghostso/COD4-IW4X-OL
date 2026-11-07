"""RESTORE-IIPS-CONTRACT-001 / Task 07 - the readiness/callback handoff site.

Task 06 tied the contract sequence to code sites. The final step is the one that
matters most:

    [ResourceManagerII::InitializeWorkAfterClientConnected()]
        [ResourceManagerII::Initialize() succeed]         <-- site 0x17E52
        [SendMessage][m_hCallbackHWnd %d]                 <-- site 0x17E72

This is where the provider declares itself ready and messages a callback window.
This script decodes both sites and the surrounding function so the handoff is
read from instructions, not inferred from log text.
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
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    ib = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + 224
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return d, pe, ib, secs


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def decode(d, secs, rva, n, ib):
    """Small decoder covering the forms that appear in this function."""
    off = r2o(secs, rva)
    out = []
    p = off
    cur = rva
    end = min(off + n, len(d))
    while p < end:
        b = d[p]
        ln, txt = 1, None
        if b == 0x55:
            txt = "push ebp"
        elif b == 0x8B and d[p + 1] == 0xEC:
            txt, ln = "mov ebp,esp", 2
        elif b == 0x81 and d[p + 1] == 0xEC:
            txt, ln = "sub esp,0x%X" % struct.unpack_from("<I", d, p + 2)[0], 6
        elif b == 0x83 and d[p + 1] == 0xEC:
            txt, ln = "sub esp,0x%X" % d[p + 2], 3
        elif b == 0x56:
            txt = "push esi"
        elif b == 0x57:
            txt = "push edi"
        elif b == 0x53:
            txt = "push ebx"
        elif b == 0x8B and d[p + 1] == 0xF1:
            txt, ln = "mov esi,ecx", 2
        elif b == 0x8B and d[p + 1] == 0x75:
            txt, ln = "mov esi,[ebp+0x%X]" % d[p + 2], 3
        elif b == 0x8B and d[p + 1] == 0x45:
            txt, ln = "mov eax,[ebp+0x%X]" % d[p + 2], 3
        elif b == 0x8B and d[p + 1] == 0x4D:
            txt, ln = "mov ecx,[ebp+0x%X]" % d[p + 2], 3
        elif b == 0x8B and d[p + 1] == 0x75 and d[p + 2] == 0x08:
            txt, ln = "mov esi,[ebp+0x8]", 3
        elif b == 0x68:
            v = struct.unpack_from("<I", d, p + 1)[0]
            txt, ln = "push 0x%08X" % v, 5
        elif b == 0x6A:
            txt, ln = "push %d" % struct.unpack_from("<b", d, p + 1)[0], 2
        elif b == 0xE8:
            txt, ln = "call 0x%X" % (cur + 5 + struct.unpack_from("<i", d, p + 1)[0]), 5
        elif b == 0xFF and d[p + 1] == 0x15:
            txt, ln = "call dword [0x%08X]" % struct.unpack_from("<I", d, p + 2)[0], 6
        elif b == 0xFF and d[p + 1] == 0x75:
            txt, ln = "push dword [ebp+0x%X]" % d[p + 2], 3
        elif b == 0xFF and d[p + 1] == 0x50:
            txt, ln = "call eax", 2
        elif b == 0xFF and d[p + 1] == 0x52:
            txt, ln = "call edx", 2
        elif b == 0x85 and d[p + 1] == 0xC0:
            txt, ln = "test eax,eax", 2
        elif b == 0x74:
            txt, ln = "je 0x%X" % (cur + 2 + struct.unpack_from("<b", d, p + 1)[0]), 2
        elif b == 0x75:
            txt, ln = "jne 0x%X" % (cur + 2 + struct.unpack_from("<b", d, p + 1)[0]), 2
        elif b == 0xEB:
            txt, ln = "jmp 0x%X" % (cur + 2 + struct.unpack_from("<b", d, p + 1)[0]), 2
        elif b == 0xC3:
            txt = "ret"
        elif b == 0xC2:
            txt, ln = "ret 0x%X" % struct.unpack_from("<H", d, p + 1)[0], 3
        elif b == 0x5E:
            txt = "pop esi"
        elif b == 0x5F:
            txt = "pop edi"
        elif b == 0x5D:
            txt = "pop ebp"
        elif b == 0x33 and d[p + 1] == 0xC0:
            txt, ln = "xor eax,eax", 2
        elif b == 0x50:
            txt = "push eax"
        elif b == 0x51:
            txt = "push ecx"
        elif b == 0x52:
            txt = "push edx"
        elif b == 0x89 and d[p + 1] == 0x45:
            txt, ln = "mov [ebp+0x%X],eax" % d[p + 2], 3
        elif b == 0x8D and d[p + 1] == 0x45:
            txt, ln = "lea eax,[ebp+0x%X]" % d[p + 2], 3
        if txt is None:
            txt = "db 0x%02X" % b
        out.append({"rva": "0x%X" % cur,
                    "bytes": d[p:p + ln].hex(" ").upper(), "asm": txt})
        p += ln
        cur += ln
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    d, pe, ib, secs = load(IIPS)
    rep = {"image_base": "0x%X" % ib}
    print("=== Task 07: readiness + callback handoff ===")
    print("  iips.dll image base = 0x%08X" % ib)
    print()

    # Find the enclosing function of 0x17E72 by walking back to a prologue.
    site = 0x17E72
    off = r2o(secs, site)
    start_off = off
    for back in range(0, 0x800):
        p = off - back
        if p < 4:
            break
        if d[p] == 0x55 and d[p + 1] == 0x8B and d[p + 2] == 0xEC:
            start_off = p
            break
    rva_at_start = site - (off - start_off)
    rep["function_start"] = "0x%X" % rva_at_start
    print("  enclosing function starts at RVA 0x%X" % rva_at_start)
    print()
    ins = decode(d, secs, rva_at_start, 0x1C0, ib)
    rep["function_body"] = ins
    for i in ins[:110]:
        print("   %-8s %-24s %s" % (i["rva"], i["bytes"], i["asm"]))

    with open(os.path.join(OUT, "t10_callback_handoff.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t10_callback_handoff.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
