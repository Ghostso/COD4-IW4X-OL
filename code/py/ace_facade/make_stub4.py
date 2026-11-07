"""Simplest correct approach: rebuild the export section WITHOUT relocations
by making the whole module load at its preferred base is not reliable, so
instead we avoid storing any pointer that needs fixing.

Key realisation: a vtable MUST contain absolute code pointers, so it always
needs a relocation.  Rather than fight that, we register our pointers in the
module's .reloc directory -- that is exactly what .reloc is for, and the
loader will fix them for us at whatever base it picks.

Steps:
  1. append our section as before (export dir + vtable + object + code)
  2. build a NEW relocation block covering every absolute pointer we stored
  3. append it as another section, and point the .reloc data directory at it

The relocation format (IMAGE_BASE_RELOCATION) is:
    DWORD VirtualAddress
    DWORD SizeOfBlock
    WORD  TypeOffset[n]      ; high 4 bits = type (3 = HIGHLOW), low 12 = offset
"""
import struct
import sys


def align(v, a):
    return (v + a - 1) // a * a


VSLOTS = 64


def build(template, exports, out_path, dll_name, factory_index=0):
    data = bytearray(open(template, "rb").read())
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    sa = struct.unpack_from("<I", data, opt + 32)[0]
    fa = struct.unpack_from("<I", data, opt + 36)[0]
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    sh = pe + 24 + optsz

    raw_end = 0
    last_va_end = 0
    reloc_rva = struct.unpack_from("<I", data, opt + 96 + 5 * 8)[0]
    for i in range(nsec):
        s = sh + i * 40
        vsz, va, rsz, ptr = struct.unpack_from("<IIII", data, s + 8)
        raw_end = max(raw_end, ptr + rsz)
        last_va_end = max(last_va_end, va + max(vsz, rsz))
    raw_end = align(raw_end, fa)

    # ---------------- section 1: our export data + code ----------------
    va1 = align(last_va_end, sa)
    n = len(exports)
    dirlen = 40 + 4 * n + 4 * n + 2 * n
    name_blob = b""
    name_rvas = []
    for e in exports:
        name_rvas.append(dirlen + len(name_blob))
        name_blob += e.encode("ascii") + b"\x00"
    dll_name_off = dirlen + len(name_blob)
    name_blob += dll_name.encode("ascii") + b"\x00"
    code_off = align(dirlen + len(name_blob), 4)

    code = bytearray()
    noop_off = code_off
    code += b"\x31\xc0\xc3"
    while len(code) % 4:
        code += b"\x90"
    vt_off = code_off + len(code)
    vt_rva = va1 + vt_off
    for _ in range(VSLOTS):
        code += struct.pack("<I", image_base + va1 + noop_off)   # fixed by reloc
    obj_off = code_off + len(code)
    code += struct.pack("<I", image_base + vt_rva)               # fixed by reloc
    code += b"\x00" * 12
    fac_off = code_off + len(code)
    code += b"\xb8" + struct.pack("<I", image_base + va1 + obj_off) + b"\xc3"
    zero_off = code_off + len(code)
    code += b"\x31\xc0\xc3"

    sec_size = code_off + len(code)
    sec = bytearray(align(sec_size, fa))
    struct.pack_into("<I", sec, 12, va1 + dll_name_off)
    struct.pack_into("<I", sec, 16, 1)
    struct.pack_into("<I", sec, 20, n)
    struct.pack_into("<I", sec, 24, n)
    struct.pack_into("<I", sec, 28, va1 + 40)
    struct.pack_into("<I", sec, 32, va1 + 40 + 4 * n)
    struct.pack_into("<I", sec, 36, va1 + 40 + 8 * n)
    for i in range(n):
        tgt = fac_off if i == factory_index else zero_off
        struct.pack_into("<I", sec, 40 + i * 4, va1 + tgt)
    for i in range(n):
        struct.pack_into("<I", sec, 40 + 4 * n + i * 4, va1 + name_rvas[i])
    for i in range(n):
        struct.pack_into("<H", sec, 40 + 8 * n + i * 2, i)
    sec[dirlen:dirlen + len(name_blob)] = name_blob
    sec[code_off:code_off + len(code)] = code

    # ---------------- section 2: relocations for our pointers ----------------
    # offsets (within section 1) of every dword that holds image_base+RVA
    fixups = [vt_off + 4 * k for k in range(VSLOTS)]
    fixups.append(obj_off)
    fixups.append(fac_off + 1)          # the imm32 inside `mov eax,imm32`
    fixups.sort()

    blocks = bytearray()
    PAGE = 0x1000
    by_page = {}
    for off in fixups:
        by_page.setdefault((va1 + off) // PAGE * PAGE, []).append(
            (va1 + off) % PAGE)
    for page in sorted(by_page):
        ents = by_page[page]
        blk = struct.pack("<II", page, 8 + 2 * len(ents))
        for o in ents:
            blk += struct.pack("<H", 0x3000 | o)     # type 3 = HIGHLOW
        blocks += blk

    # Append our fixup blocks to the TEMPLATE'S EXISTING .reloc section.
    # Creating a second relocation section made the loader reject the file
    # (err=193); the original .reloc has spare raw space, so we simply extend
    # the data directory to cover our extra blocks.
    reloc_sec = None
    for s in range(nsec):
        hdr = sh + s * 40
        nm = data[hdr:hdr + 8].rstrip(b"\x00").decode("latin1")
        if nm == ".reloc":
            reloc_sec = hdr
            break
    if reloc_sec is None:
        raise SystemExit("template has no .reloc section")
    # size currently declared in the data directory (what the loader walks)
    reloc_size = struct.unpack_from("<I", data, opt + 96 + 5 * 8 + 4)[0]
    rvsz, rva_va, rrsz, rptr = struct.unpack_from("<IIII", data, reloc_sec + 8)
    if len(blocks) + reloc_size > rrsz:
        raise SystemExit("template .reloc too small: need %d have %d"
                         % (reloc_size + len(blocks), rrsz))
    data[rptr + reloc_size: rptr + reloc_size + len(blocks)] = blocks
    new_reloc_size = reloc_size + len(blocks)
    # grow the declared size so the loader walks our extra blocks too
    struct.pack_into("<I", data, reloc_sec + 8, max(rvsz, new_reloc_size))

    # ---------------- write both section headers ----------------
    hdr1 = bytearray(40)
    hdr1[0:8] = b".aceobj\x00"
    struct.pack_into("<IIII", hdr1, 8, sec_size, va1, len(sec), raw_end)
    struct.pack_into("<I", hdr1, 36, 0xE0000060)
    data[sh + nsec * 40: sh + nsec * 40 + 40] = hdr1

    struct.pack_into("<H", data, pe + 6, nsec + 1)
    struct.pack_into("<I", data, opt + 56, align(va1 + sec_size, sa))
    struct.pack_into("<II", data, pe + 24 + 96, va1, dirlen)          # export
    struct.pack_into("<II", data, pe + 24 + 96 + 5 * 8,
                     rva_va, new_reloc_size)                          # reloc

    while len(data) < raw_end:
        data.append(0)
    data += bytes(sec)

    open(out_path, "wb").write(bytes(data))
    print("built %s exports=%d vt=0x%X obj=0x%X fac=0x%X relocs=%d"
          % (out_path, n, va1 + vt_off, va1 + obj_off, va1 + fac_off,
             len(fixups)))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4],
          int(sys.argv[5]) if len(sys.argv) > 5 else 0)
