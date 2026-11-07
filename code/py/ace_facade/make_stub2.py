"""Build an x86 stub DLL by APPENDING a new section to a real DLL.

Why this approach:
  - hand-rolled PE            -> err=193 (structure rejected)
  - tables overwritten in .data -> err=998 (template's init saw corrupt state)
  - tables in .rsrc            -> err=193 (section not writable)

Appending a section leaves every byte of the template untouched, and we
control the new section's characteristics (read+write, no execute), so the
loader has nothing to object to.
"""
import struct
import sys


def align(v, a):
    return (v + a - 1) // a * a


def parse(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    opt = pe + 24
    sect_align = struct.unpack_from("<I", d, opt + 32)[0]
    file_align = struct.unpack_from("<I", d, opt + 36)[0]
    size_image = struct.unpack_from("<I", d, opt + 56)[0]
    return pe, nsec, optsz, opt, sect_align, file_align, size_image


def build(template, exports, out_path, dll_name):
    data = bytearray(open(template, "rb").read())
    pe, nsec, optsz, opt, sa, fa, size_image = parse(data)
    sh = pe + 24 + optsz                      # section headers start
    hdr_end = sh + (nsec + 1) * 40

    # 1. find the raw end of the file (so we can place our section after it)
    raw_end = 0
    last_va_end = 0
    for i in range(nsec):
        s = sh + i * 40
        vsz, va, rsz, ptr = struct.unpack_from("<IIII", data, s + 8)
        raw_end = max(raw_end, ptr + rsz)
        last_va_end = max(last_va_end, va + max(vsz, rsz))
    raw_end = align(raw_end, fa)
    new_va = align(last_va_end, sa)

    # 2. lay our export tables out inside the new section
    n = len(exports)
    dirlen = 40 + 4 * n + 4 * n + 2 * n
    name_blob = b""
    name_rvas = []
    for e in exports:
        name_rvas.append(dirlen + len(name_blob))
        name_blob += e.encode("ascii") + b"\x00"
    dll_name_rva_in_sec = dirlen + len(name_blob)
    name_blob += dll_name.encode("ascii") + b"\x00"
    stub_off_in_sec = align(dirlen + len(name_blob), 4)
    stub = b"\x31\xc0\xc3"                    # xor eax,eax ; ret
    sec_size = stub_off_in_sec + 16

    sec = bytearray(align(sec_size, fa))
    # export directory
    struct.pack_into("<I", sec, 12, new_va + dll_name_rva_in_sec)  # Name
    struct.pack_into("<I", sec, 16, 1)                             # Base
    struct.pack_into("<I", sec, 20, n)                             # NumFuncs
    struct.pack_into("<I", sec, 24, n)                             # NumNames
    struct.pack_into("<I", sec, 28, new_va + 40)                   # AddrFuncs
    struct.pack_into("<I", sec, 32, new_va + 40 + 4 * n)           # AddrNames
    struct.pack_into("<I", sec, 36, new_va + 40 + 8 * n)           # AddrOrds
    for i in range(n):
        struct.pack_into("<I", sec, 40 + i * 4, new_va + stub_off_in_sec)
    for i in range(n):
        struct.pack_into("<I", sec, 40 + 4 * n + i * 4, new_va + name_rvas[i])
    for i in range(n):
        struct.pack_into("<H", sec, 40 + 8 * n + i * 2, i)
    sec[dirlen:dirlen + len(name_blob)] = name_blob
    sec[stub_off_in_sec:stub_off_in_sec + len(stub)] = stub

    # 3. append the new section header
    name = b".aceexp\x00"
    hdr = bytearray(40)
    hdr[0:8] = name
    struct.pack_into("<IIII", hdr, 8, sec_size, new_va, len(sec), raw_end)
    struct.pack_into("<I", hdr, 36, 0xC0000040)   # init-data | read | write
    data[sh + nsec * 40: sh + nsec * 40 + 40] = hdr

    # 4. update header counts
    struct.pack_into("<H", data, pe + 6, nsec + 1)
    new_img = align(new_va + sec_size, sa)
    struct.pack_into("<I", data, opt + 56, new_img)
    struct.pack_into("<II", data, pe + 24 + 96, new_va, dirlen)   # export dir

    # 5. pad to raw_end and append section bytes
    while len(data) < raw_end:
        data.append(0)
    data += bytes(sec)

    open(out_path, "wb").write(bytes(data))
    print("built %s  exports=%d  newsec_va=0x%X size=%d  img=0x%X"
          % (out_path, n, new_va, sec_size, new_img))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4])
