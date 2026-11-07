# -*- coding: utf-8 -*-
"""
pe_exports.py -- READ-ONLY dump of IMAGE_EXPORT_DIRECTORY and its three arrays.

Why: pe_probe.py has no `exports` mode (six subcommands only: dirs/secs/imps/
refs/hex/scan) and ff15_map.py prints only dir[0]'s bare header.  Reading the
export table by RVA offset is structurally impossible via Read/Grep, so this
script exists.  Nothing here writes.

Prints the 40-byte header, the DLL name, and one row per EAT entry joining
AddressOfFunctions[i] with the name whose AddressOfNameOrdinals entry == i.
Unnamed entries are printed as <unnamed>, not skipped.
"""
import sys, struct

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def parse_pe(d):
    e = u32(d, 0x3C)
    if d[e:e + 4] != b'PE\0\0':
        raise SystemExit('no PE sig')
    c = e + 4
    nsec = u16(d, c + 2); optsz = u16(d, c + 16); opt = c + 20
    magic = u16(d, opt)
    if magic != 0x10b:
        raise SystemExit('not PE32 (magic 0x%X)' % magic)
    ib = u32(d, opt + 28); sizeofimage = u32(d, opt + 56)
    nddir = u32(d, opt + 92); ddoff = opt + 96
    dirs = [(u32(d, ddoff + i * 8), u32(d, ddoff + i * 8 + 4))
            for i in range(min(nddir, 16))]
    secs = []; so = opt + optsz
    for i in range(nsec):
        p = so + i * 40
        secs.append(dict(idx=i, name=d[p:p + 8].rstrip(b'\0').decode('latin1'),
                         vsize=u32(d, p + 8), va=u32(d, p + 12),
                         rawsize=u32(d, p + 16), raw=u32(d, p + 20),
                         chars=u32(d, p + 36)))
    return ib, sizeofimage, dirs, secs

def off_of_rva(secs, rva):
    """file offset only if the byte is really in the file (rawsize, not vsize)"""
    for s in secs:
        if s['va'] <= rva < s['va'] + s['rawsize']:
            return s['raw'] + (rva - s['va']), s
    return None, None

def sec_at(secs, rva):
    """section by virtual size -- covers the unbacked tail"""
    for s in secs:
        if s['va'] <= rva < s['va'] + max(s['vsize'], s['rawsize']):
            return s
    return None

def cstr(d, off, limit=400):
    e = d.find(b'\0', off, off + limit)
    if e < 0: e = off + limit
    return d[off:e].decode('latin1')

path = sys.argv[1]
d = open(path, 'rb').read()
ib, sizeofimage, dirs, secs = parse_pe(d)
va, sz = dirs[0]
print('=' * 78)
print('FILE: %s  (%d bytes)' % (path, len(d)))
print('ImageBase 0x%08X   SizeOfImage 0x%X' % (ib, sizeofimage))
print('dir[0] EXPORT  RVA=0x%08X  size=0x%X' % (va, sz))
if not va:
    raise SystemExit('  -> no export directory in this file')

off, s = off_of_rva(secs, va)
if off is None:
    print('  !! export directory header is not file-backed')
    raise SystemExit(0)
print('  header raw off 0x%X  in section [%d]%s' % (off, s['idx'], s['name']))

ch = u32(d, off); tds = u32(d, off + 4)
mj = u16(d, off + 8); mn = u16(d, off + 10)
nameRVA = u32(d, off + 12); base = u32(d, off + 16)
nfunc = u32(d, off + 20); nname = u32(d, off + 24)
af = u32(d, off + 28); an = u32(d, off + 32); ao = u32(d, off + 36)
print('  Characteristics 0x%X   TimeDateStamp 0x%08X   Version %d.%d'
      % (ch, tds, mj, mn))
print('  Name RVA 0x%08X   Base %d   NumberOfFunctions %d   NumberOfNames %d'
      % (nameRVA, base, nfunc, nname))
print('  AddressOfFunctions(EAT) 0x%08X' % af)
print('  AddressOfNames         0x%08X' % an)
print('  AddressOfNameOrdinals  0x%08X' % ao)
print('  export dir ends at RVA 0x%08X (start + size)' % (va + sz))

no, _ = off_of_rva(secs, nameRVA)
print('  DLL NAME: "%s"' % (cstr(d, no) if no is not None else '<unbacked>'))
print()

# join AddressOfNames[i] + AddressOfNameOrdinals[i] -> name for EAT index
nameoff, _ = off_of_rva(secs, an)
ordoff, _ = off_of_rva(secs, ao)
names = {}
if nameoff is not None and ordoff is not None:
    for i in range(nname):
        nrva = u32(d, nameoff + i * 4)
        ordv = u16(d, ordoff + i * 2)
        fo, _ = off_of_rva(secs, nrva)
        names[ordv] = cstr(d, fo) if fo is not None else '<name string unbacked>'
else:
    print('  !! name/ordinal arrays are not file-backed')

print('  idx   ord   fnRVA       fn        name')
for i in range(nfunc):
    eo, _ = off_of_rva(secs, af + i * 4)
    frva = u32(d, eo) if eo is not None else 0
    fs = sec_at(secs, frva) if frva else None
    bk = (frva - fs['va'] < fs['rawsize']) if fs else None
    print('  %3d   %3d   0x%08X  %-9s %-56s %s'
          % (i, base + i, frva,
             '[%d]%s' % (fs['idx'], fs['name']) if fs else '<outside>',
             names.get(i, '<unnamed>'),
             'BACKED' if bk else ('VIRTUAL-ONLY' if fs else '')))
print()
print('  named %d of %d EAT entries' % (len(names), nfunc))
