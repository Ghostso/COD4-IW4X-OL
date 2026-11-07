# -*- coding: utf-8 -*-
"""
pe_head.py -- READ-ONLY raw dump of PE header fields that pe_probe.py does not
expose (AddressOfEntryPoint / SizeOfHeaders / subsystem / DllCharacteristics),
plus the section raw-file-offset column re-derived from the header itself.

Why: pe_probe.py has no mode that reads opt+16, and hex/slots modes cannot reach
RVA 0 (headers are not inside any section's VA range).  Nothing here writes.
"""
import sys, struct

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

path = sys.argv[1]
d = open(path, 'rb').read()
e = u32(d, 0x3C)
c = e + 4
machine = u16(d, c); nsec = u16(d, c + 2); tstamp = u32(d, c + 4)
optsz = u16(d, c + 16); chars = u16(d, c + 18)
opt = c + 20
magic = u16(d, opt)
assert magic == 0x10b, 'not PE32'

ib = u32(d, opt + 28)
entry = u32(d, opt + 16)
basecode = u32(d, opt + 20) if False else None
soh = u32(d, opt + 60)
subsys = u16(d, opt + 68)
dllchar = u16(d, opt + 70)
stackres = u32(d, opt + 72); stackcom = u32(d, opt + 76)
heapres = u32(d, opt + 80)
loaderflags = u32(d, opt + 88)

print('=' * 78)
print('FILE: %s  (%d bytes)' % (path, len(d)))
print('e_lfanew        = 0x%X   (opt header at 0x%X)' % (e, opt))
print('Machine         = 0x%04X' % machine)
print('NumberOfSections= %d' % nsec)
print('TimeDateStamp   = 0x%08X (%u)' % (tstamp, tstamp))
print('SizeOfOptHeader = 0x%X' % optsz)
print('Characteristics = 0x%04X  %s' % (chars, 'EXECUTABLE_IMAGE' if chars & 0x2 else ''))
print('Subsystem       = %d  (2=GUI 3=CUI)' % subsys)
print('DllCharacteristics = 0x%04X  %s' % (dllchar, 'DYNAMIC_BASE' if dllchar & 0x40 else ''))
print('SizeOfHeaders   = 0x%X' % soh)
print('ImageBase       = 0x%08X' % ib)
print('AddressOfEntryPoint = RVA 0x%08X  -> VA 0x%08X' % (entry, ib + entry))
print('StackReserve    = 0x%X   StackCommit = 0x%X   HeapReserve = 0x%X'
      % (stackres, stackcom, heapres))
print('LoaderFlags     = 0x%X' % loaderflags)
print()
print('--- section table, RAW offsets accumulated from SizeOfHeaders ---')
so = opt + optsz
cur = soh
for i in range(nsec):
    p = so + i * 40
    nm = d[p:p + 8].rstrip(b'\0').decode('latin1')
    vsz = u32(d, p + 8); va = u32(d, p + 12)
    rsz = u32(d, p + 16); raw = u32(d, p + 20)
    ch = u32(d, p + 36)
    flag = '  <-- MISMATCH vs accumulated 0x%X' % cur if raw != cur and rsz else ''
    print('  [%d] %-6s va=0x%08X vsz=0x%-8X rawsize=0x%-8X raw=0x%08X%s'
          % (i, nm, va, vsz, rsz, raw, flag))
    cur = raw + rsz
print('  end of last section raw = 0x%X   file len = 0x%X   trailing = 0x%X'
      % (cur, len(d), len(d) - cur))
print()
print('--- does the declared entry RVA land on the FF15 stub? ---')
print('  entry RVA 0x%08X  vs stub RVA 0x0E5DC690  -> %s'
      % (entry, 'MATCH' if entry == 0x0E5DC690 else 'NO MATCH'))
if 0 <= entry < len(d):
    # header RVA == file offset for anything inside SizeOfHeaders
    if entry < soh:
        off = entry
        print('  entry bytes (header-mapped) = %s'
              % ' '.join('%02X' % x for x in d[off:off + 16]))
    else:
        for i in range(nsec):
            p = so + i * 40
            va = u32(d, p + 12); rsz = u32(d, p + 16); raw = u32(d, p + 20)
            nm = d[p:p + 8].rstrip(b'\0').decode('latin1')
            if va <= entry < va + rsz:
                off = raw + (entry - va)
                print('  entry in section [%d]%s  fileoff=0x%X' % (i, nm, off))
                print('  entry bytes = %s'
                      % ' '.join('%02X' % x for x in d[off:off + 32]))
                break
