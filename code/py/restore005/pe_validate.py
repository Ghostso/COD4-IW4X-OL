"""Strict PE32 validity checks, modelled on the real NT/ntdll loader
(LdrpValidateImageForProtection / RtlImageNtHeader / MiCreateSection).

Every check prints OK or the specific violation.
"""
import hashlib
import os
import struct
import sys

IMAGE_FILE_MACHINE_I386 = 0x014C
IMAGE_NT_OPTIONAL_HDR32_MAGIC = 0x010B
IMAGE_FILE_DLL = 0x2000
IMAGE_FILE_EXECUTABLE_IMAGE = 0x0002


def u16(d, o):
    return struct.unpack_from("<H", d, o)[0]


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


class V:
    def __init__(self, path, quiet=False):
        self.path = path
        self.fails = []
        self.warns = []
        self.quiet = quiet
        with open(path, "rb") as f:
            self.d = f.read()
        self.n = len(self.d)

    def ck(self, cond, ok_msg, bad_msg, warn=False):
        if cond:
            if not self.quiet:
                print("  OK   %s" % ok_msg)
        else:
            print("  FAIL %s" % bad_msg)
            (self.warns if warn else self.fails).append(bad_msg)
        return cond

    def run(self):
        d, n = self.d, self.n
        print("=" * 78)
        print("PE VALIDATION: %s" % self.path)
        print("  size   = %d" % n)
        print("  sha256 = %s" % hashlib.sha256(d).hexdigest())
        print("=" * 78)

        print("--- DOS header ---")
        if not self.ck(u16(d, 0) == 0x5A4D, "e_magic = MZ", "e_magic != MZ"):
            return False
        e_lfanew = u32(d, 0x3C)
        self.ck(0 < e_lfanew <= n - 4, "e_lfanew = 0x%X in range" % e_lfanew,
                "e_lfanew 0x%X out of range" % e_lfanew)

        print("--- NT header ---")
        pe = e_lfanew
        if not self.ck(u32(d, pe) == 0x00004550, "PE signature", "bad PE signature"):
            return False
        coff = pe + 4
        machine = u16(d, coff)
        nsec = u16(d, coff + 2)
        szopt = u16(d, coff + 16)
        chars = u16(d, coff + 18)
        print("  machine=0x%04X sections=%d SizeOfOptionalHeader=%d Characteristics=0x%04X"
              % (machine, nsec, szopt, chars))
        self.ck(machine == IMAGE_FILE_MACHINE_I386, "Machine = I386",
                "Machine 0x%04X != I386" % machine)
        self.ck(chars & IMAGE_FILE_DLL, "IMAGE_FILE_DLL set", "IMAGE_FILE_DLL not set")
        self.ck(szopt >= 224, "SizeOfOptionalHeader = %d" % szopt,
                "SizeOfOptionalHeader = %d (< 224)" % szopt)
        self.ck(1 <= nsec <= 96, "NumberOfSections = %d" % nsec,
                "NumberOfSections = %d invalid" % nsec)

        # `coff` already points past the 4-byte "PE\0\0" signature, i.e. it is
        # the start of IMAGE_FILE_HEADER (20 bytes).  The optional header
        # follows immediately.
        opt = coff + 20
        # SizeOfOptionalHeader (0xE0 = 224) covers the OPTIONAL header only;
        # the section table starts right after it.
        sechdr = opt + szopt
        self.ck(sechdr + nsec * 40 <= n, "section table fits in file",
                "section table exceeds file")
        if sechdr + nsec * 40 > n:
            return False

        print("--- Optional header ---")
        magic = u16(d, opt)
        self.ck(magic == IMAGE_NT_OPTIONAL_HDR32_MAGIC, "Magic = 0x10B (PE32)",
                "Magic = 0x%X not PE32" % magic)
        ep = u32(d, opt + 16)
        imagebase = u32(d, opt + 28)
        sect_align = u32(d, opt + 32)
        file_align = u32(d, opt + 36)
        size_image = u32(d, opt + 56)
        size_headers = u32(d, opt + 60)
        subsystem = u16(d, opt + 68)
        dllchars = u16(d, opt + 70)
        nrva = u32(d, opt + 92)
        print("  AddressOfEntryPoint = 0x%X" % ep)
        print("  ImageBase           = 0x%X" % imagebase)
        print("  SectionAlignment    = 0x%X" % sect_align)
        print("  FileAlignment       = 0x%X" % file_align)
        print("  SizeOfImage         = 0x%X" % size_image)
        print("  SizeOfHeaders       = 0x%X" % size_headers)
        print("  Subsystem           = %d" % subsystem)
        print("  DllCharacteristics  = 0x%X" % dllchars)
        print("  NumberOfRvaAndSizes = %d" % nrva)

        self.ck(file_align != 0, "FileAlignment != 0", "FileAlignment = 0")
        self.ck(sect_align != 0, "SectionAlignment != 0", "SectionAlignment = 0")
        self.ck(dllchars & 0x0040 == 0,
                "IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE clear",
                "DYNAMIC_BASE set but no fixups guaranteed", warn=True)

        # SizeOfHeaders: loader maps headers up to SizeOfHeaders in the ROM image.
        # Must be a multiple of FileAlignment and >= size of all headers.
        min_headers = sechdr + nsec * 40
        self.ck(size_headers % max(file_align, 1) == 0,
                "SizeOfHeaders 0x%X is FileAlignment aligned" % size_headers,
                "SizeOfHeaders 0x%X not FileAlignment(0x%X) aligned" % (size_headers, file_align))
        self.ck(size_headers >= min_headers,
                "SizeOfHeaders 0x%X >= header bytes 0x%X" % (size_headers, min_headers),
                "SizeOfHeaders 0x%X < header bytes 0x%X" % (size_headers, min_headers))

        print("--- sections ---")
        secs = []
        va_sorted = []
        for i in range(nsec):
            o = sechdr + i * 40
            name = d[o:o + 8].rstrip(b"\x00").decode("latin-1")
            vs = u32(d, o + 8)
            va = u32(d, o + 12)
            rs = u32(d, o + 16)
            rp = u32(d, o + 20)
            ch = u32(d, o + 36)
            secs.append((name, vs, va, rs, rp, ch))
            print("  [%d] %-9s VA=0x%-7X VS=0x%-7X RawPtr=0x%-7X RawSz=0x%-7X Ch=0x%08X"
                  % (i, name, va, vs, rp, rs, ch))

        for i, (name, vs, va, rs, rp, ch) in enumerate(secs):
            self.ck(va % sect_align == 0, "%s VA aligned" % name,
                    "%s VirtualAddress 0x%X not SectionAlignment(0x%X) aligned" % (name, va, sect_align))
            self.ck(rp % file_align == 0 if file_align else False,
                    "%s RawPtr aligned" % name,
                    "%s PointerToRawData 0x%X not FileAlignment(0x%X) aligned" % (name, rp, file_align))
            self.ck(rp + rs <= n, "%s raw data inside file" % name,
                    "%s raw [0x%X,0x%X) exceeds file size 0x%X" % (name, rp, rp + rs, n))
            if rs:
                self.ck(rp >= size_headers,
                        "%s raw data after headers" % name,
                        "%s raw data 0x%X overlaps headers (SizeOfHeaders 0x%X)" % (name, rp, size_headers))
            # VirtualSize vs SizeOfRawData: loader tolerates RS < VS only for the
            # tail; enforce the well-defined case.
            self.ck(vs <= rs or rs == 0 or (vs - rs) <= (sect_align - 1),
                    "%s VirtualSize within SizeOfRawData slack" % name,
                    "%s VirtualSize 0x%X > SizeOfRawData 0x%X (unbacked virtual bytes)" % (name, vs, rs),
                    warn=True)
            va_sorted.append((va, va + max(vs, rs), name))

        # last section must fit in SizeOfImage
        last_end = max((e for _, e, _ in va_sorted), default=0)
        self.ck(last_end <= size_image,
                "highest section end 0x%X <= SizeOfImage 0x%X" % (last_end, size_image),
                "SizeOfImage 0x%X < highest section end 0x%X" % (size_image, last_end))

        print("--- overlay / signed-image certificate (ROM-image check) ---")
        # The loader treats the file as a ROM image: file bytes beyond the last
        # section are still validated against SizeOfImage when a SECURITY
        # directory is present.
        dirs = []
        for i in range(min(nrva, 16)):
            dirs.append((u32(d, opt + 96 + i * 8), u32(d, opt + 100 + i * 8)))
        sec_rva, sec_sz = dirs[4] if len(dirs) > 4 else (0, 0)
        print("  file size            = 0x%X" % n)
        print("  SizeOfImage          = 0x%X" % size_image)
        print("  SECURITY dir RVA     = 0x%X size 0x%X" % (sec_rva, sec_sz))
        if sec_rva:
            self.ck(sec_rva + sec_sz <= n,
                    "certificate within file [0x%X,0x%X)" % (sec_rva, sec_rva + sec_sz),
                    "certificate [0x%X,0x%X) exceeds file 0x%X" % (sec_rva, sec_rva + sec_sz, n))
            self.ck(sec_rva + sec_sz <= size_image,
                    "certificate inside SizeOfImage",
                    "certificate ends 0x%X but SizeOfImage = 0x%X -> loader sees truncated image"
                    % (sec_rva + sec_sz, size_image))
        # ROM-image rule: the file must not extend past SizeOfImage
        self.ck(n <= size_image,
                "file size 0x%X <= SizeOfImage 0x%X" % (n, size_image),
                "file size 0x%X > SizeOfImage 0x%X (overlay beyond image)" % (n, size_image),
                warn=True)

        print("--- entrypoint ---")
        if ep:
            sec = None
            for (name, vs, va, rs, rp, ch) in secs:
                lo, hi = va, va + max(vs, rs)
                if lo <= ep < hi:
                    sec = (name, va, vs, rs, rp, ch)
                    break
            self.ck(sec is not None, "AddressOfEntryPoint 0x%X inside a section" % ep,
                    "AddressOfEntryPoint 0x%X not inside any section" % ep)
            if sec:
                self.ck(sec[5] & 0x20000000 != 0,
                        "entrypoint section %s is executable" % sec[0],
                        "entrypoint section %s not executable" % sec[0])

        print("--- data directories ---")
        for i, (rva, sz) in enumerate(dirs):
            if rva or sz:
                flag = ""
                if rva and rva >= size_image:
                    flag = "  <-- RVA >= SizeOfImage"
                if flag:
                    self.fails.append("dir %d RVA 0x%X >= SizeOfImage" % (i, rva))
                print("  dir[%2d] RVA=0x%08X Size=0x%08X%s" % (i, rva, sz, flag))

        print("--- IMPORT directory ---")
        imp_rva, imp_sz = dirs[1] if len(dirs) > 1 else (0, 0)
        if imp_rva:
            off = self.rva2off(imp_rva, secs)
            if off is None:
                self.fails.append("IMPORT RVA 0x%X unmappable" % imp_rva)
                print("  FAIL IMPORT RVA unmappable")
            else:
                print("  IMPORT RVA 0x%X -> file 0x%X" % (imp_rva, off))
                k = 0
                good = True
                while True:
                    b = off + k * 20
                    oft, ts, fc, name_rva, ft = struct.unpack_from("<IIIII", d, b)
                    if oft == 0 and name_rva == 0 and ft == 0:
                        break
                    nm_off = self.rva2off(name_rva, secs)
                    dll = d[nm_off:d.index(b"\x00", nm_off)].decode("latin-1") if nm_off else "?"
                    print("     %-16s OFT=0x%X Name=0x%X IAT=0x%X" % (dll, oft, name_rva, ft))
                    for r in (oft, ft):
                        if r and self.rva2off(r, secs) is None:
                            good = False
                            self.fails.append("IMPORT thunk RVA 0x%X unmappable" % r)
                    k += 1
                    if k > 64:
                        break
                self.ck(good, "all import thunk RVAs mappable",
                        "some import thunk RVAs unmappable")

        print("--- IAT directory ---")
        iat_rva, iat_sz = dirs[12] if len(dirs) > 12 else (0, 0)
        if iat_rva:
            o = self.rva2off(iat_rva, secs)
            self.ck(o is not None, "IAT RVA 0x%X mappable" % iat_rva,
                    "IAT RVA 0x%X unmappable" % iat_rva)
            self.ck(iat_rva + iat_sz <= size_image,
                    "IAT inside SizeOfImage", "IAT ends 0x%X > SizeOfImage 0x%X" % (iat_rva + iat_sz, size_image))

        print("--- IMPORT vs IAT overlap (LEGITIMATE, do not 'fix') ---")
        if imp_rva and iat_rva:
            imp_lo, imp_hi = imp_rva, imp_rva + max(imp_sz, 20)
            iat_lo, iat_hi = iat_rva, iat_rva + iat_sz
            if iat_lo < imp_hi and imp_lo < iat_hi:
                print("  NOTE: IMPORT dir [0x%X,0x%X) overlaps IAT [0x%X,0x%X) -- this is the"
                      % (imp_lo, imp_hi, iat_lo, iat_hi))
                print("        layout in the ORIGINAL iips.dll and loads fine. Not a defect.")

        print()
        print("RESULT: %s   (%d hard failures, %d warnings)"
              % ("VALID" if not self.fails else "INVALID", len(self.fails), len(self.warns)))
        for f in self.fails:
            print("   HARD: %s" % f)
        for w in self.warns:
            print("   WARN: %s" % w)
        return not self.fails

    def rva2off(self, rva, secs):
        for (name, vs, va, rs, rp, ch) in secs:
            if va <= rva < va + max(vs, rs):
                delta = rva - va
                if delta < rs:
                    return rp + delta
                return None
        return None


if __name__ == "__main__":
    ok_all = True
    for p in sys.argv[1:]:
        v = V(p)
        ok_all &= v.run()
        print()
    sys.exit(0 if ok_all else 1)
