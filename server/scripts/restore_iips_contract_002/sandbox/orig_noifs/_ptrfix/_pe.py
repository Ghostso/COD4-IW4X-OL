import struct, sys, os

PATH = r"d:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
print("file size = 0x%X (%d)" % (len(data), len(data)))

e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
print("e_lfanew = 0x%X" % e_lfanew)
pe = data[e_lfanew:e_lfanew+4]
print("sig =", pe)

coff = e_lfanew + 4
machine, nsec, tds, psym, nsym, osz, chars = struct.unpack_from("<HHIIIHH", data, coff)
print("machine=0x%04X nsections=%d TimeDateStamp=0x%08X Characteristics=0x%04X" % (machine, nsec, tds, chars))
print("TimeDateStamp = %s" % __import__("datetime").datetime.utcfromtimestamp(tds))

opt = coff + 20
magic = struct.unpack_from("<H", data, opt)[0]
print("optional magic = 0x%04X (%s)" % (magic, "PE32" if magic == 0x10b else "PE32+" if magic == 0x20b else "?"))
if magic != 0x10b:
    print("NOT PE32, aborting"); sys.exit(1)

(_, _, _, _, _, ImageBase, SectionAlignment, FileAlignment, _, _, _, _, _,
 _, MajorOS, MinorOS, MajorImg, MinorImg, MajorSub, MinorSub, Win32Ver,
 SizeOfImage, SizeOfHeaders, CheckSum, Subsystem, DllChars,
 SizeOfStackReserve, SizeOfStackCommit, SizeOfHeapReserve, SizeOfHeapCommit,
 LoaderFlags, NumberOfRvaAndSizes) = struct.unpack_from("<27sIIIIIHHHHHHIIIIHHIIIIII"[:0] or "<HBBIIIIIIIIIHHHHHHIIIIHHIIIIII", data, opt+2) if False else (None,)*32

# do it explicitly to avoid mistakes
off = opt + 2
vals = struct.unpack_from("<BBIIIIIIIIIHHHHHHIIIIHHIIIIII", data, off)
(c_linker_v, c_linker_r, SizeOfCode, SizeOfInitData, SizeOfUninitData, EntryPoint,
 BaseOfCode, BaseOfData, ImageBase, SecAlign, FileAlign, MajOS, MinOS, MajImg, MinImg,
 MajSub, MinSub, Win32Ver, SizeOfImage, SizeOfHeaders, CheckSum, Subsystem, DllChars,
 StackReserve, StackCommit, HeapReserve, HeapCommit, LoaderFlags, NumDirs) = vals
print("ImageBase = 0x%08X" % ImageBase)
print("SizeOfImage = 0x%X   SizeOfHeaders = 0x%X" % (SizeOfImage, SizeOfHeaders))
print("SectionAlignment = 0x%X  FileAlignment = 0x%X" % (SecAlign, FileAlign))
print("EntryPoint RVA = 0x%X -> VA 0x%X" % (EntryPoint, ImageBase + EntryPoint))
print("BaseOfCode = 0x%X  BaseOfData = 0x%X" % (BaseOfCode, BaseOfData))
print("SizeOfCode=0x%X SizeOfInitData=0x%X SizeOfUninitData=0x%X" % (SizeOfCode, SizeOfInitData, SizeOfUninitData))
print("Subsystem=%d DllChars=0x%04X NumDirs=%d" % (Subsystem, DllChars, NumDirs))

dirs_off = off + 28 + 68
DIRNAMES = ["Export","Import","Resource","Exception","Security","BaseReloc","Debug","Arch",
            "GlobalPtr","TLS","LoadConfig","BoundImport","IAT","DelayImport","CLR","Reserved"]
print("\n=== DATA DIRECTORIES ===")
dirs = {}
for i in range(min(NumDirs, 16)):
    rva, sz = struct.unpack_from("<II", data, dirs_off + i*8)
    dirs[i] = (rva, sz)
    print("[%2d] %-14s RVA=0x%08X size=0x%X (%d)" % (i, DIRNAMES[i], rva, sz, sz))

sec_off = dirs_off + 16*8
print("\n=== SECTIONS (%d) ===" % nsec)
secs = []
for i in range(nsec):
    o = sec_off + i*40
    name = data[o:o+8]
    vsize, vaddr, rawsize, rawptr, relocptr, lineptr, nreloc, nline, schars = struct.unpack_from("<IIIIIIHHI", data, o+8)
    secs.append(dict(i=i, name=name, vsize=vsize, vaddr=vaddr, rawsize=rawsize, rawptr=rawptr,
                     nreloc=nreloc, chars=schars))
    print("[%d] name=%-10r VAddr=0x%08X VSize=0x%08X RawPtr=0x%08X RawSize=0x%08X Chars=0x%08X nReloc=%d"
          % (i, name, vaddr, vsize, rawptr, rawsize, schars, nreloc))

def rva2off(rva):
    for s in secs:
        if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            if rva - s["vaddr"] < s["rawsize"]:
                return s["rawptr"] + (rva - s["vaddr"])
            return None
    if rva < SizeOfHeaders:
        return rva
    return None

print("\n=== SECTION MAPPING TABLE ===")
for s in secs:
    print("sec[%d] VA 0x%08X..0x%08X (file-backed to 0x%08X, virtual tail 0x%08X)"
          % (s["i"], ImageBase+s["vaddr"], ImageBase+s["vaddr"]+s["vsize"],
             ImageBase+s["vaddr"]+s["rawsize"], ImageBase+s["vaddr"]+s["vsize"]))
    print("       file bytes 0x%08X..0x%08X" % (s["rawptr"], s["rawptr"]+s["rawsize"]))

# per-section characteristics bit decode
CH = [(0x00000020,"CNT_CODE"),(0x00000040,"CNT_INITIALIZED_DATA"),(0x00000080,"CNT_UNINITIALIZED_DATA"),
      (0x00000200,"LNK_INFO"),(0x00000800,"LNK_REMOVE"),(0x00001000,"LNK_COMDAT"),
      (0x00008000,"GPREL"),(0x00020000,"MEM_PURGEABLE"),(0x00080000,"LNK_NRELOC_OVFL"),
      (0x01000000,"MEM_DISCARDABLE"),(0x02000000,"MEM_NOT_CACHED"),(0x04000000,"MEM_NOT_PAGED"),
      (0x08000000,"MEM_SHARED"),(0x10000000,"MEM_EXECUTE"),(0x20000000,"MEM_READ"),
      (0x40000000,"MEM_WRITE")]
print("\n=== SECTION CHARACTERISTICS DECODE ===")
for s in secs:
    flags = [n for b,n in CH if s["chars"] & b]
    print("sec[%d] 0x%08X : %s" % (s["i"], s["chars"], " | ".join(flags) if flags else "(none)"))
