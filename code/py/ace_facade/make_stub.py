"""Build a working x86 DLL stub by REUSING a real system DLL as a template.

Hand-rolling a PE failed earlier (err=193).  Instead we take a small, real,
validly-structured x86 DLL and rewrite it into a stub that:
  * exports the exact names the game resolves
  * every export returns 0 / a null-but-noncrashing pointer
  * has no imports, no threads, no side effects

Approach: parse the template's section table, then REPLACE the export
directory contents in place with our own, padding inside the existing
section.  All other headers stay untouched, so the loader sees a file it
already accepts.
"""
import struct
import sys


def rva2off(secs, rva):
    for s in secs:
        va, vsz, ptr, rsz = s[1], s[2], s[3], s[4]
        if va <= rva < va + max(vsz, rsz):
            return ptr + (rva - va)
    return None


def parse(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    off = pe + 24 + optsz
    secs = []
    for i in range(nsec):
        s = data[off + i * 40: off + i * 40 + 40]
        nm = s[:8].rstrip(b"\x00").decode("latin1")
        vsz, va, rsz, ptr = struct.unpack_from("<IIII", s, 8)
        chars = struct.unpack_from("<I", s, 36)[0]
        secs.append([nm, va, vsz, ptr, rsz, chars, off + i * 40])
    return pe, nsec, optsz, secs


def build(template, exports, out_path, dll_name):
    data = bytearray(open(template, "rb").read())
    pe, nsec, optsz, secs = parse(data)

    ddir = pe + 24 + 96
    exp_rva, exp_size = struct.unpack_from("<II", data, ddir)
    if exp_rva == 0:
        raise SystemExit("template has no export directory")
    exp_off = rva2off(secs, exp_rva)
    if exp_off is None:
        raise SystemExit("cannot map export dir")

    # Choose a host section.
    #
    # IMPORTANT: do NOT clobber .data.  Writing our tables at the start of
    # .data overwrote the template's initialised globals, and although every
    # export table entry was provably correct the loader then failed with
    # err=998 (invalid access) because the module's own init touched
    # corrupted state.  .rsrc is safe: the template's resources are
    # irrelevant to us and nothing reads them for a stub.
    host = None
    for s in secs:
        if s[0].lower() == ".rsrc" and s[4] >= 0x400:
            host = s
            break
    if host is None:                     # fall back: largest non-.data section
        cands = [s for s in secs if s[0].lower() not in (".data", ".text")]
        if cands:
            host = max(cands, key=lambda s: s[4])
    if host is None:
        raise SystemExit("no suitable host section")

    nm, hva, hvsz, hptr, hrsz, hchars, hhdr = host
    base = hva                       # we place our tables at the section start
    off = hptr

    n = len(exports)
    dirlen = 40 + 4 * n + 4 * n + 2 * n
    str_start = base + dirlen

    # Name strings.
    # CRITICAL: the internal DLL name must be written OVER the template's
    # existing name string rather than appended.  Appending grew the region
    # past the original allocation and made the loader fail with err=998
    # (invalid access) even though the export tables themselves were correct.
    # We reuse the template's own name slot and require it to be long enough.
    names_blob = b""
    name_rvas = []
    for e in exports:
        name_rvas.append(str_start + len(names_blob))
        names_blob += e.encode("ascii") + b"\x00"

    dll_name_rva = str_start + len(names_blob)
    names_blob += dll_name.encode("ascii") + b"\x00"

    # The internal DLL name goes in its OWN slot at the END of our blob.
    # (Reusing the template's original name slot does not work: those slots
    # are only as long as the original name -- 18 bytes for MshtmlDac -- and
    # our exports plus DLL name need ~50.)
    #
    # Growing the blob is what previously caused err=998, because it ran past
    # the host section's raw size.  We therefore verify the fit up front and
    # fail loudly instead of emitting a DLL the loader rejects.

    # every function points at the SAME shared "return 0" stub.
    # We place the stub right after the strings.
    stub_rva = str_start + len(names_blob)
    stub_rva = (stub_rva + 3) & ~3
    stub = b"\x31\xc0\xc3"           # xor eax,eax ; ret   (3 bytes)

    total = dirlen + len(names_blob) + 16
    if total > hrsz:
        raise SystemExit(
            "template section too small: need %d have %d (pick a bigger "
            "template)" % (total, hrsz))

    # --- write export directory ---
    fun_arr = base + 40
    nam_arr = fun_arr + 4 * n
    ord_arr = nam_arr + 4 * n

    struct.pack_into("<I", data, off + 12, dll_name_rva)   # Name
    struct.pack_into("<I", data, off + 16, 1)              # Base
    struct.pack_into("<I", data, off + 20, n)              # NumberOfFunctions
    struct.pack_into("<I", data, off + 24, n)              # NumberOfNames
    struct.pack_into("<I", data, off + 28, fun_arr)
    struct.pack_into("<I", data, off + 32, nam_arr)
    struct.pack_into("<I", data, off + 36, ord_arr)

    fo = rva2off(secs, fun_arr)
    for i in range(n):
        struct.pack_into("<I", data, fo + i * 4, stub_rva)
    no = rva2off(secs, nam_arr)
    for i in range(n):
        struct.pack_into("<I", data, no + i * 4, name_rvas[i])
    oo = rva2off(secs, ord_arr)
    for i in range(n):
        struct.pack_into("<H", data, oo + i * 2, i)
    so = rva2off(secs, str_start)
    data[so:so + len(names_blob)] = names_blob
    tob = rva2off(secs, stub_rva)
    data[tob:tob + len(stub)] = stub

    # point the data directory at our new tables
    struct.pack_into("<II", data, ddir, base, dirlen)

    open(out_path, "wb").write(bytes(data))
    print("built %s  exports=%d  (template=%s)"
          % (out_path, n, template.split("\\")[-1]))


if __name__ == "__main__":
    template = sys.argv[1]
    names = sys.argv[2].split(",")
    out = sys.argv[3]
    dllname = sys.argv[4]
    build(template, names, out, dllname)
