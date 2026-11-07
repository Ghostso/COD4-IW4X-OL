"""Instrumented stub: same as make_stub4, but every vtable slot points at a
distinct numbered stub, and each stub RECORDS its slot number into a
well-known dword inside our section before returning 0.

That gives us, with no debugger:
  * how many distinct interface methods the game actually calls
  * which slot indices they are
  * in what order

The recorder is itself harmless: it only touches memory inside our own
section, and returns 0 in eax.

Layout of one recorder (slot N):
    mov  ecx, <counter_base + N*4>   ; or use a shared bump pointer
    inc  dword [ecx]
    xor  eax, eax
    ret

We keep it even simpler: a shared call-log array.  Each slot writes its own
index into the next free log entry, then increments the log count.

    mov  ecx, [<logptr>]        ; 8B 0D <abs32>   -> pointer to log array
    mov  edx, <N>               ; BA <imm32>
    mov  [ecx], edx             ; 89 11
    add  dword [<logptr>], 4    ; 83 05 <abs32> 04
    inc  dword [<count>]        ; FF 05 <abs32>
    xor  eax, eax               ; 31 C0
    ret                         ; C3

All <abs32> need relocations, which make_stub4 already handles.
"""
import struct
import sys


def align(v, a):
    return (v + a - 1) // a * a


VSLOTS = 64
LOGSIZE = 4096


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
    for i in range(nsec):
        s = sh + i * 40
        vsz, va, rsz, ptr = struct.unpack_from("<IIII", data, s + 8)
        raw_end = max(raw_end, ptr + rsz)
        last_va_end = max(last_va_end, va + max(vsz, rsz))
    raw_end = align(raw_end, fa)
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

    fixups = []
    code = bytearray()

    def cur_off():
        return code_off + len(code)

    # NOTE: the export directory must live at the FIRST byte of the section
    # (we point the data directory at section start).  An earlier version put
    # the 4 KB call-log at offset 0, which overwrote the export directory --
    # the loader then read the log (all zeros) as the directory, every
    # absolute address in the recorders stayed 0, and calling any vtable slot
    # faulted with 0xC0000005.
    #
    # Layout is therefore: [export dir][names][log][count][recorders][vtable][object][code]
    log_off = cur_off()
    code += b"\x00" * LOGSIZE
    cnt_off = cur_off()
    code += b"\x00" * 4

    def abs32(rva_of_place):
        """value to store: image_base + va1 + rva ; and register a fixup"""
        fixups.append(rva_of_place - code_off)
        return image_base + va1 + rva_of_place

    # --- recorders: one per slot ---
    #
    # Each recorder needs to reach the log without an absolute address,
    # because every abs32 costs a relocation and the template only has ~216
    # bytes of .reloc slack (194 fixups need ~404).  We therefore obtain the
    # log pointer at RUNTIME with `call $+5 / pop`:
    #
    #     E8 00000000        call  $+5     ; pushes address of next insn
    #     59                 pop   ecx     ; ecx = runtime address after pop
    #     81 E9 <imm32>      sub   ecx, imm ; ecx -= (here - log_off)
    #
    # `sub ecx, imm32` uses an absolute CONSTANT (not a pointer), so it needs
    # no relocation: after the subtraction ecx is correct at any load base.
    # `call rel32` is position independent already.
    rec_offs = []
    for slot in range(VSLOTS):
        rec_offs.append(cur_off())
        # call $+5 ; pop ecx
        #   `call $+5` pushes the address of the instruction FOLLOWING it,
        #   i.e. the address of the `pop`.  After `pop ecx`, ecx therefore
        #   equals the address of the `pop` itself (5 bytes into the
        #   recorder), NOT the address of the `sub`.
        #   The constant must be  pop_addr - log_rva  where pop_addr is
        #   rec_start + 5.  Using rec_start + 6 previously left ecx 7 bytes
        #   adrift (the 6, plus the 1-byte `pop`), so the recorder incremented
        #   the wrong dword and the log stayed empty.
        rec_start = cur_off()
        code += b"\xE8\x00\x00\x00\x00\x59"
        code += b"\x81\xE9" + struct.pack("<I", (va1 + rec_start + 5) - (va1 + log_off))
        # edx = ecx + (cnt_off - log_off)   ; lea edx,[ecx+imm32]
        code += b"\x8D\x91" + struct.pack("<I", cnt_off - log_off)
        # eax = [edx]  (current count)
        code += b"\x8B\x02"
        # clamp
        code += b"\x3D" + struct.pack("<I", LOGSIZE // 4 - 1)
        code += b"\x73\x09"
        # [ecx + eax*4] = slot
        code += b"\xC7\x04\x81" + struct.pack("<I", slot)
        # inc dword [edx]
        code += b"\xFF\x02"
        code += b"\x31\xC0\xC3"

    # --- vtable: slot k -> rec_offs[k] ---
    vt_off = cur_off()
    for k in range(VSLOTS):
        fixups.append(len(code))
        code += struct.pack("<I", image_base + va1 + rec_offs[k])

    # --- object ---
    obj_off = cur_off()
    fixups.append(len(code))
    code += struct.pack("<I", image_base + va1 + vt_off)
    code += b"\x00" * 12

    # --- factory ---
    fac_off = cur_off()
    code += b"\xB8"
    fixups.append(len(code))
    code += struct.pack("<I", image_base + va1 + obj_off)
    code += b"\xC3"

    zero_off = cur_off()
    code += b"\x31\xC0\xC3"

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

    # --- relocations into existing .reloc ---
    reloc_hdr = None
    for s in range(nsec):
        hdr = sh + s * 40
        if data[hdr:hdr + 8].rstrip(b"\x00").decode("latin1") == ".reloc":
            reloc_hdr = hdr
            break
    rvsz, rva_va, rrsz, rptr = struct.unpack_from("<IIII", data, reloc_hdr + 8)
    cur = struct.unpack_from("<I", data, opt + 96 + 5 * 8 + 4)[0]
    fixes = sorted(set(fixups))
    blocks = bytearray()
    by_page = {}
    for f in fixes:
        a = va1 + code_off + f
        by_page.setdefault(a // 0x1000 * 0x1000, []).append(a % 0x1000)
    for page in sorted(by_page):
        ents = by_page[page]
        blocks += struct.pack("<II", page, 8 + 2 * len(ents))
        for o in ents:
            blocks += struct.pack("<H", 0x3000 | o)
    if cur + len(blocks) > rrsz:
        raise SystemExit("reloc space too small: need %d have %d"
                         % (cur + len(blocks), rrsz))
    data[rptr + cur: rptr + cur + len(blocks)] = blocks
    struct.pack_into("<I", data, reloc_hdr + 8, max(rvsz, cur + len(blocks)))
    struct.pack_into("<II", data, opt + 96 + 5 * 8, rva_va, cur + len(blocks))

    hdr1 = bytearray(40)
    hdr1[0:8] = b".aceins\x00"
    struct.pack_into("<IIII", hdr1, 8, sec_size, va1, len(sec), raw_end)
    struct.pack_into("<I", hdr1, 36, 0xE0000060)
    data[sh + nsec * 40: sh + nsec * 40 + 40] = hdr1
    struct.pack_into("<H", data, pe + 6, nsec + 1)
    struct.pack_into("<I", data, opt + 56, align(va1 + sec_size, sa))
    struct.pack_into("<II", data, pe + 24 + 96, va1, dirlen)

    while len(data) < raw_end:
        data.append(0)
    data += bytes(sec)
    open(out_path, "wb").write(bytes(data))
    print("built %s exports=%d log=0x%X cnt=0x%X vt=0x%X obj=0x%X"
          % (out_path, n, va1 + log_off, va1 + cnt_off,
             va1 + vt_off, va1 + obj_off))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4],
          int(sys.argv[5]) if len(sys.argv) > 5 else 0)
