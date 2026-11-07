# EX-065 shared image loader for tcls_core.exe and TCLS-family modules.
import pefile


class Img:
    def __init__(self, path):
        self.path = path
        self.pe = pefile.PE(path, fast_load=True)
        self.pe.parse_data_directories()
        self.data = open(path, "rb").read()
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.by_rva = bytearray(self.size)
        self.secs = []
        for s in self.pe.sections:
            nm = s.Name.decode(errors="replace").rstrip("\x00")
            self.secs.append((nm, s.VirtualAddress, s.Misc_VirtualSize,
                              s.PointerToRawData, s.SizeOfRawData,
                              s.Characteristics))
            n = min(s.Misc_VirtualSize, s.SizeOfRawData)
            self.by_rva[s.VirtualAddress:s.VirtualAddress + n] = \
                self.data[s.PointerToRawData:s.PointerToRawData + n]
        self.imports = {}
        if hasattr(self.pe, "DIRECTORY_ENTRY_IMPORT"):
            for d in self.pe.DIRECTORY_ENTRY_IMPORT:
                for i in d.imports:
                    nm = i.name.decode(errors="replace") if i.name \
                        else "ord%d" % i.ordinal
                    self.imports[i.address - self.base] = (d.dll.decode(
                        errors="replace"), nm)

    def read(self, rva, n):
        return bytes(self.by_rva[rva:rva + n])

    def is_code(self, rva):
        for (nm, va, vs, raw, rs, ch) in self.secs:
            if ch & 0x20000000 and va <= rva < va + max(vs, rs):
                return True
        return False

    def codesec(self):
        for (nm, va, vs, raw, rs, ch) in self.secs:
            if ch & 0x20000000:
                return va, va + vs
        return 0x1000, 0x1000

    def rva2raw(self, rva):
        for (nm, va, vs, raw, rs, ch) in self.secs:
            if va <= rva < va + max(vs, rs):
                return raw + (rva - va)
        return None

    def raw2rva(self, off):
        for (nm, va, vs, raw, rs, ch) in self.secs:
            if raw <= off < raw + rs:
                return va + (off - raw), nm
        return None, None

    def cstr(self, rva, limit=200):
        o = self.rva2raw(rva)
        if o is None:
            return None
        e = self.data.find(b"\x00", o, o + limit)
        if e < 0:
            return None
        return self.data[o:e]
