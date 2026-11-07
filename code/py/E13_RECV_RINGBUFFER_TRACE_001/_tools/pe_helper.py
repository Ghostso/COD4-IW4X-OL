"""Correct PE helpers. Sections store RVAs; capstone prints VAs (RVA = VA - ImageBase)."""
import struct, pefile

class PE:
    def __init__(self, path):
        self.path=path
        self.d=open(path,"rb").read()
        pe=pefile.PE(path,fast_load=True)
        self.IB=pe.OPTIONAL_HEADER.ImageBase
        self.pe=pe
        self.secs=[(s.Name.rstrip(b"\0").decode(), s.VirtualAddress, s.Misc_VirtualSize,
                    s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
    def off(self, rva):
        for nm,va,vs,rp,rs in self.secs:
            if va<=rva<va+vs:
                if rs==0: return None, nm
                return rp+(rva-va), nm
        return None, None
    def off_va(self, va):
        return self.off(va-self.IB)
    def sec_of(self, rva):
        return self.off(rva)[1]
    def bytes_rva(self, rva, n):
        o,nm=self.off(rva)
        return self.d[o:o+n] if o is not None else None
    def in_raw(self, rva):
        for nm,va,vs,rp,rs in self.secs:
            if va<=rva<va+vs: return rs>0 and (rva-va)<rs
        return False