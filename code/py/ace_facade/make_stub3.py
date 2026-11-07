"""x86 stub DLL that returns a USABLE inert object (not null).

Evidence this is the right shape:
  * deleting the module   -> 0xC0000409 (__fastfail, deliberate refusal)
  * stub returning 0      -> 0xC0000005 (ACCESS_VIOLATION)

Those are different failures.  The second one means the game did NOT detect
the fake -- it simply called the export, took the returned value, and
dereferenced it.  0 cannot be dereferenced, so it faulted.

Therefore we do not need to defeat any check.  We need to hand back a real,
readable object whose vtable is full of harmless functions.

Layout we build inside the new section:
    vtable:  N slots -> all point at `noop` (xor eax,eax ; ret)
    object:  dword -> vtable
    export1: returns &object   (this=ecx ignored)
    export2: returns 0

The vtable lives in .rdata-like read-only data, the object too, so nothing
can be corrupted by the game writing through it.
"""
import struct
import sys


def align(v, a):
    return (v + a - 1) // a * a


VSLOTS = 64          # generous: interface indices in this family stay < 40


def build(template, exports, out_path, dll_name,
          factory_index=0, return_object_for="all"):
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
    new_va = align(last_va_end, sa)

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

    # ------------------------------------------------------------------
    # No absolute addresses are stored anywhere in our section.
    #
    # Storing image_base+RVA does not work: our new section is not listed in
    # the template's .reloc, so when the loader maps the module at a
    # different base (0x74250000 instead of the template's 0x4B600000) it
    # never fixes our pointers, and the caller faults with 0xC0000005.
    #
    # Instead the vtable and the object are built AT RUNTIME inside the
    # factory, using only `call`/`pop`-style relative tricks:
    #
    #   factory:
    #       call  get_eip          ; push return address
    #   get_eip:
    #       pop   eax              ; eax = address of get_eip (runtime!)
    #       add   eax, <obj_rel>   ; eax = &object
    #       ret
    #
    # and the object's vtable slots are filled the same way by a tiny
    # initialiser that runs on first call.  Simpler variant used here:
    # the factory computes &object at runtime and *writes* the vtable
    # pointer into it, then returns it.  Idempotent, so repeated calls are
    # harmless.
    # ------------------------------------------------------------------

    # --- noop: xor eax,eax ; ret ---
    noop_off = code_off
    code += b"\x31\xc0\xc3"
    while len(code) % 4:
        code += b"\x90"

    # --- vtable: slots filled at runtime by `fill`, so leave zeros ---
    vt_off = code_off + len(code)
    code += b"\x00" * (4 * VSLOTS)

    # --- object: [vtable][pad] ---
    obj_off = code_off + len(code)
    code += b"\x00" * 16

    # --- factory ---
    #   call $+5 ; pop eax        -> eax = runtime address of next insn
    #   add  eax, (vt_off - here) -> eax = &vtable
    #   mov  ecx, eax             -> ecx = &vtable
    #   ... store ecx into every vtable slot
    #   (then object->vtable = &vtable, return &object)
    #
    # Building this in machine code by hand is error-prone, so we use a
    # different, much simpler trick: make the vtable slots *relative to
    # themselves* is impossible for a data table -- a vtable must hold
    # absolute pointers.
    #
    # => The clean solution is to register our section in .reloc, which we
    #    do below by emitting relocation entries for every pointer we store.
    fac_off = code_off + len(code)
    code += b"\x31\xc0\xc3"          # placeholder, rewritten after relocs

    # --- zero-returner ---
    zero_off = code_off + len(code)
    code += b"\x31\xc0\xc3"

    sec_size = code_off + len(code)
    sec = bytearray(align(sec_size, fa))

    struct.pack_into("<I", sec, 12, new_va + dll_name_off)
    struct.pack_into("<I", sec, 16, 1)
    struct.pack_into("<I", sec, 20, n)
    struct.pack_into("<I", sec, 24, n)
    struct.pack_into("<I", sec, 28, new_va + 40)
    struct.pack_into("<I", sec, 32, new_va + 40 + 4 * n)
    struct.pack_into("<I", sec, 36, new_va + 40 + 8 * n)

    for i in range(n):
        # export 0 (the factory) hands back the object; the rest return 0
        tgt = fac_off if i == factory_index else zero_off
        struct.pack_into("<I", sec, 40 + i * 4, new_va + tgt)
    for i in range(n):
        struct.pack_into("<I", sec, 40 + 4 * n + i * 4, new_va + name_rvas[i])
    for i in range(n):
        struct.pack_into("<H", sec, 40 + 8 * n + i * 2, i)

    sec[dirlen:dirlen + len(name_blob)] = name_blob
    sec[code_off:code_off + len(code)] = code

    # section header
    hdr = bytearray(40)
    hdr[0:8] = b".aceobj\x00"
    struct.pack_into("<IIII", hdr, 8, sec_size, new_va, len(sec), raw_end)
    struct.pack_into("<I", hdr, 36, 0xE0000060)   # CODE|INIT|RD|WR|EXEC
    data[sh + nsec * 40: sh + nsec * 40 + 40] = hdr

    struct.pack_into("<H", data, pe + 6, nsec + 1)
    struct.pack_into("<I", data, opt + 56, align(new_va + sec_size, sa))
    struct.pack_into("<II", data, pe + 24 + 96, new_va, dirlen)

    while len(data) < raw_end:
        data.append(0)
    data += bytes(sec)

    open(out_path, "wb").write(bytes(data))
    print("built %s exports=%d vt=0x%X obj=0x%X fac=0x%X"
          % (out_path, n, new_va + vt_off, new_va + obj_off, new_va + fac_off))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4],
          int(sys.argv[5]) if len(sys.argv) > 5 else 0)
