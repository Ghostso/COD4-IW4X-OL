"""Extract the unpacked client image out of a full-memory dump.

Why: the shipped codoMP_client_shipRetail.exe is packed (7.8 MB on disk but
SizeOfImage = 241 MB, sections named .tp3 with tiny raw sizes).  The real,
unpacked image only exists in memory, and the full-memory dumps we already have
capture it.  This tool carves that image into a standalone file so it can be
disassembled (capstone) and searched offline.

Dump layout (dump_earliest.py): a sparse image of VA 0x10000 .. 0x7FFF0000,
so file_offset = VA - 0x10000.  Bytes that could not be read are zero.

Usage:
  python -I extract_image_from_dump.py <dump.bin> <out.bin> [image_va]
"""
import os
import struct
import sys

DUMP_BASE = 0x10000        # dump covers VA 0x10000 .. 0x7FFF0000
DEFAULT_IMAGE_VA = 0x400000


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    dump_path, out_path = sys.argv[1], sys.argv[2]
    image_va = int(sys.argv[3], 0) if len(sys.argv) > 3 else DEFAULT_IMAGE_VA

    size = os.path.getsize(dump_path)
    print("dump: %s (%d bytes)" % (dump_path, size))
    off = image_va - DUMP_BASE
    if off < 0 or off + 0x400 > size:
        print("image VA 0x%X is outside the dump" % image_va)
        return 2

    with open(dump_path, "rb") as f:
        f.seek(off)
        hdr = f.read(0x400)
        if hdr[:2] != b"MZ":
            print("no MZ at VA 0x%X (got %r) -- dump may be from a different base"
                  % (image_va, hdr[:4]))
            return 2
        e_lfanew = struct.unpack_from("<I", hdr, 0x3C)[0]
        f.seek(off + e_lfanew)
        nt = f.read(0x108)
        if nt[:4] != b"PE\0\0":
            print("no PE signature at +0x%X" % e_lfanew)
            return 2
        machine, nsec = struct.unpack_from("<HH", nt, 4)
        opt_magic = struct.unpack_from("<H", nt, 24)[0]
        size_of_image = struct.unpack_from("<I", nt, 24 + 56)[0]
        size_of_headers = struct.unpack_from("<I", nt, 24 + 60)[0]
        entry = struct.unpack_from("<I", nt, 24 + 16)[0]
        print("PE: machine=0x%04X sections=%d magic=0x%04X" % (machine, nsec, opt_magic))
        print("SizeOfImage=0x%X (%.1f MB) SizeOfHeaders=0x%X EntryPoint=0x%08X"
              % (size_of_image, size_of_image / 1048576.0, size_of_headers, entry))

        sec_off = e_lfanew + 24 + struct.unpack_from("<H", nt, 20)[0]
        f.seek(off + sec_off)
        raw_sec = f.read(40 * nsec)
        print("sections:")
        for i in range(nsec):
            s = raw_sec[i * 40:(i + 1) * 40]
            name = s[:8].rstrip(b"\x00").decode("latin1")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", s, 8)
            chars = struct.unpack_from("<I", s, 36)[0]
            print("  %-10s VA=0x%08X vsize=0x%-8X raw=0x%-8X chars=0x%08X"
                  % (name, vaddr, vsize, rawsize, chars))

        if size_of_image == 0 or size_of_image > (size - off):
            print("!! SizeOfImage looks wrong for this dump (0x%X)" % size_of_image)
            return 2
        f.seek(off)
        data = f.read(size_of_image)

    # sparseness: how much of the image was actually readable
    zero = data.count(b"\x00")
    print("image bytes=%d  zero-bytes=%d (%.1f%% sparse)"
          % (len(data), zero, 100.0 * zero / len(data)))
    with open(out_path, "wb") as o:
        o.write(data)
    print("wrote %s (%d bytes)" % (out_path, len(data)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
