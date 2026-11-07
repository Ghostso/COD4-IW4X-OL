import sys, struct, os, hashlib
import pefile
import capstone

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
ORIG = os.path.join(ROOT, r'工具\EX035_DIR\IIPS\iips.dll')
GEN  = os.path.join(ROOT, 'LocalRM.dll')

SEC_CHARS = {0x20:'CODE',0x40:'IDATA',0x80:'UDATA',0x02000000:'DISCARD',
             0x20000000:'EXEC',0x40000000:'READ',0x80000000:'WRITE',
             0x01000000:'LNK_OTHER',0x04000000:'NOT_CACHED',0x08000000:'NOT_PAGED',
             0x10000000:'SHARED',0x00000200:'LNK_INFO',0x00000800:'LNK_REMOVE',
             0x00001000:'LNK_COMDAT',0x00008000:'GPREL',0x00020000:'MEM_16BIT',
             0x00040000:'MEM_LOCKED',0x00080000:'MEM_PRELOAD'}
def fl(v): return '|'.join(n for b,n in SEC_CHARS.items() if v & b)

def rva2off(secs, rva):
    for s in secs:
        va, vs = s.VirtualAddress, s.Misc_VirtualSize
        if va <= rva < va + max(vs, s.SizeOfRawData):
            off = rva - va
            if off < s.SizeOfRawData:
                return s.PointerToRawData + off
    return None

def load(path):
    pe = pefile.PE(path, fast_load=True)
    secs = list(pe.sections)
    return pe, secs, open(path,'rb').read()

po, so, do = load(ORIG)
pg, sg, dg = load(GEN)

print('=' * 78)
print('A01 FIELD-BY-FIELD DIFF: ORIGINAL iips.dll  ->  generated LocalRM.dll')
print('=' * 78)
print(f'{"FIELD":42s} {"ORIGINAL":>16s} {"GENERATED":>16s}  CHANGED')
print('-' * 92)
def cmp(name, a, b, fmt=None):
    a = int(a) if not isinstance(a, int) else a
    b = int(b) if not isinstance(b, int) else b
    if fmt is None:
        fmt = '#06x' if a < 0x10000 and b < 0x10000 else '#x'
    a_s, b_s = ('0x' + format(a, 'x')), ('0x' + format(b, 'x'))
    ch = '' if a == b else '  <<< CHANGED'
    print(f'{name:42s} {a_s:>16s} {b_s:>16s}{ch}')

fo, fg = po.FILE_HEADER, pg.FILE_HEADER
oo, og = po.OPTIONAL_HEADER, pg.OPTIONAL_HEADER
cmp('DOS.e_magic', po.DOS_HEADER.e_magic, pg.DOS_HEADER.e_magic)
cmp('DOS.e_lfanew', po.DOS_HEADER.e_lfanew, pg.DOS_HEADER.e_lfanew)
print()
cmp('COFF.Machine', fo.Machine, fg.Machine)
cmp('COFF.NumberOfSections', fo.NumberOfSections, fg.NumberOfSections)
cmp('COFF.TimeDateStamp', fo.TimeDateStamp, fg.TimeDateStamp)
cmp('COFF.PointerToSymbolTable', fo.PointerToSymbolTable, fg.PointerToSymbolTable)
cmp('COFF.NumberOfSymbols', fo.NumberOfSymbols, fg.NumberOfSymbols)
cmp('COFF.SizeOfOptionalHeader', fo.SizeOfOptionalHeader, fg.SizeOfOptionalHeader)
cmp('COFF.Characteristics', fo.Characteristics, fg.Characteristics, '#06x')
print()
for n in ('Magic','AddressOfEntryPoint','ImageBase','SectionAlignment','FileAlignment',
          'SizeOfCode','SizeOfInitializedData','SizeOfUninitializedData','SizeOfImage',
          'SizeOfHeaders','Subsystem','DllCharacteristics','SizeOfStackReserve',
          'SizeOfStackCommit','SizeOfHeapReserve','SizeOfHeapCommit',
          'NumberOfRvaAndSizes','BaseOfCode','BaseOfData','CheckSum',
          'MajorOperatingSystemVersion','MajorSubsystemVersion','MinorSubsystemVersion'):
    cmp('OPT.'+n, getattr(oo,n), getattr(og,n))
print()
names = {v:k for k,v in pefile.DIRECTORY_ENTRY.items()}
print('DATA DIRECTORIES')
for i,(a,b) in enumerate(zip(oo.DATA_DIRECTORY, og.DATA_DIRECTORY)):
    nm = names.get(i, str(i))
    ch = '' if (a.VirtualAddress == b.VirtualAddress and a.Size == b.Size) else '   <<< CHANGED'
    print(f'  [{i:2d}] {nm:36s} orig RVA {a.VirtualAddress:#010x} sz {a.Size:#07x}  ->  '
          f'gen RVA {b.VirtualAddress:#010x} sz {b.Size:#07x}{ch}')
print()
print('SECTIONS')
for i,(a,b) in enumerate(zip(so, sg)):
    an = a.Name.rstrip(b'\x00').decode('latin1'); bn = b.Name.rstrip(b'\x00').decode('latin1')
    print(f'  [{i}] {an}')
    for f in ('Misc_VirtualSize','VirtualAddress','SizeOfRawData','PointerToRawData','Characteristics'):
        va, vb = getattr(a,f), getattr(b,f)
        ch = '' if va == vb else '   <<< CHANGED'
        print(f'        {f:22s} orig {va:#010x}  gen {vb:#010x}{ch}')
    print(f'        {"PointerToRelocations":22s} orig {a.PointerToRelocations:#010x}  gen {b.PointerToRelocations:#010x}')
    print(f'        {"NumberOfRelocations":22s} orig {a.NumberOfRelocations:#010x}  gen {b.NumberOfRelocations:#010x}')

print()
print('=' * 78)
print('A02 ALIGNMENT / OVERLAP / BOUNDS VALIDATION')
print('=' * 78)
for pe_, secs, data, label in ((po,so,do,'ORIGINAL'), (pg,sg,dg,'GENERATED')):
    oh = pe_.OPTIONAL_HEADER
    print(f'--- {label} ---')
    print(f'  FileAlignment      = {oh.FileAlignment:#x}   SectionAlignment = {oh.SectionAlignment:#x}')
    print(f'  SizeOfHeaders      = {oh.SizeOfHeaders:#x}  '
          f'{"OK (FileAlignment-aligned)" if oh.SizeOfHeaders % oh.FileAlignment == 0 else "*** VIOLATION ***"}')
    print(f'  SizeOfImage        = {oh.SizeOfImage:#x}  '
          f'{"OK (SectionAlignment-aligned)" if oh.SizeOfImage % oh.SectionAlignment == 0 else "*** VIOLATION: NOT SectionAlignment-ALIGNED ***"}')
    # section VA / raw alignment + ordering + overlap
    prev = None
    for s in secs:
        n = s.Name.rstrip(b'\x00').decode('latin1')
        va_ok = (s.VirtualAddress % oh.SectionAlignment == 0)
        rp_ok = (s.PointerToRawData == 0) or (s.PointerToRawData % oh.FileAlignment == 0)
        va_end  = s.VirtualAddress + s.Misc_VirtualSize
        raw_end = s.PointerToRawData + s.SizeOfRawData
        msgs = []
        if not va_ok: msgs.append('VA-ALIGN VIOLATION')
        if not rp_ok: msgs.append('RAW-ALIGN VIOLATION')
        if raw_end > len(data): msgs.append(f'RAW-END {raw_end:#x} > FILESIZE {len(data):#x}')
        if prev is not None:
            if s.VirtualAddress < prev_vend: msgs.append(f'VA-OVERLAP with {prev_name} (prev ends {prev_vend:#x})')
            if s.PointerToRawData < prev_rend: msgs.append(f'RAW-OVERLAP with {prev_name} (prev ends {prev_rend:#x})')
        if s.SizeOfRawData < s.Misc_VirtualSize:
            msgs.append(f'RawSize<VirtualSize (OK only if last section / uninit tail)')
        print(f'  {n:8s} VA {s.VirtualAddress:#08x}-{va_end:#08x}  RAW {s.PointerToRawData:#08x}-{raw_end:#08x}  '
              f'{" ".join(msgs) if msgs else "OK"}')
        prev, prev_name, prev_vend, prev_rend = s, n, va_end, raw_end
    # SizeOfImage sufficiency
    maxva = max(s.VirtualAddress + s.Misc_VirtualSize for s in secs)
    print(f'  max(VA+VSize) = {maxva:#x}   SizeOfImage = {oh.SizeOfImage:#x}   '
          f'{"SizeOfImage < section extent *** BAD ***" if oh.SizeOfImage < maxva else "covers all sections"}')
    print()

print('=' * 78)
print('A01 CRITICAL: AddressOfEntryPoint RVA -> file offset')
print('=' * 78)
for pe_, secs, data, label, oh in ((po,so,do,'ORIGINAL',oo), (pg,sg,dg,'GENERATED',og)):
    rva = oh.AddressOfEntryPoint
    off = rva2off(secs, rva)
    insec = next((s.Name.rstrip(b'\x00').decode('latin1') for s in secs
                  if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize), None)
    print(f'  {label:10s} EntryPoint RVA {rva:#x}  section={insec}  file_off={hex(off) if off is not None else "NONE"}')
    if off is not None:
        chunk = data[off:off+32]
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        md.detail = True
        print(f'      bytes: {chunk[:16].hex()}')
        for ins in md.disasm(chunk[:24], rva):
            print(f'      {ins.address:#08x}  {ins.bytes.hex():<14s} {ins.mnemonic} {ins.op_str}')
print()
