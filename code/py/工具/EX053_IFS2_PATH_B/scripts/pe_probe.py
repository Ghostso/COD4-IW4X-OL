# -*- coding: utf-8 -*-
"""
pe_probe.py  -- READ-ONLY PE field/thunk reader.

  pe_probe.py <file> imports           -> dir[1] IMPORT descriptors (DLL names,
                                          thunk names/ordinals) + dir[12] IAT dump
  pe_probe.py <file> slots <rva> <n>   -> dump n DWORDs at rva, classifying each
                                          stored value by where it points

Why this exists: Read/Grep cannot read 32-bit PE header fields that contain 0x00,
so dir[1]/dir[12]/dir[5] were UNKNOWN. This reads them verbatim and prints them.
Wording discipline: a stored value that points into a section is an
"address-like pointer target" unless a header directory says otherwise.
"""
import sys, struct
from collections import Counter


def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]


def parse_pe(path):
    d = open(path, 'rb').read()
    if d[:2] != b'MZ': raise SystemExit('not MZ')
    e = u32(d, 0x3C)
    if d[e:e + 4] != b'PE\0\0': raise SystemExit('no PE sig')
    c = e + 4
    machine = u16(d, c); nsec = u16(d, c + 2); optsz = u16(d, c + 16); opt = c + 20
    magic = u16(d, opt)
    if magic == 0x10b:
        ib = u32(d, opt + 28); sizeofimage = u32(d, opt + 56)
        nddir = u32(d, opt + 92); ddoff = opt + 96; pe32 = True
    elif magic == 0x20b:
        ib = struct.unpack_from('<Q', d, opt + 24)[0]; sizeofimage = u32(d, opt + 56)
        nddir = u32(d, opt + 108); ddoff = opt + 112; pe32 = False
    else:
        raise SystemExit('bad magic 0x%X' % magic)
    dirs = [(u32(d, ddoff + i * 8), u32(d, ddoff + i * 8 + 4)) for i in range(min(nddir, 16))]
    secs = []; so = opt + optsz
    for i in range(nsec):
        p = so + i * 40
        secs.append(dict(name=d[p:p + 8].rstrip(b'\0').decode('latin1'), idx=i,
                         vsize=u32(d, p + 8), va=u32(d, p + 12),
                         rawsize=u32(d, p + 16), raw=u32(d, p + 20),
                         chars=u32(d, p + 36)))
    return dict(data=d, path=path, imagebase=ib, sizeofimage=sizeofimage,
                dirs=dirs, secs=secs, pe32=pe32, machine=machine, nsec=nsec)


def off_of_rva(pe, rva):
    """file offset for rva, or None if not file-backed"""
    for s in pe['secs']:
        if s['va'] <= rva < s['va'] + s['rawsize']:
            return s['raw'] + (rva - s['va'])
    return None


def sec_at(pe, rva):
    for s in pe['secs']:
        if s['va'] <= rva < s['va'] + max(s['vsize'], s['rawsize']):
            return s
    return None


def cstr(b, o, end=200):
    if o is None or o >= len(b): return '<?>'
    e = b.find(b'\0', o)
    if e == -1: e = min(o + end, len(b))
    return b[o:min(e, o + end)].decode('latin1', 'replace')


def where(pe, v):
    """short label for a stored dword"""
    ib = pe['imagebase']
    if v == 0: return 'ZERO'
    if ib <= v < ib + pe['sizeofimage']:
        s = sec_at(pe, v - ib)
        return '[%d]%s rva=0x%X' % (s['idx'], s['name'], v - ib) if s else 'in-image ??'
    return 'non-image 0x%08X' % v


def mode_imports(pe):
    d = pe['data']; ib = pe['imagebase']
    imp = pe['dirs'][1]; iat = pe['dirs'][12]
    print('=' * 78)
    print('IMPORT dir[1]  RVA=0x%08X size=0x%X' % (imp[0], imp[1]))
    o = off_of_rva(pe, imp[0]) if imp[0] else None
    if o is None:
        print('  !! import dir RVA absent or not file-backed -> nothing to read')
    else:
        ndesc = (imp[1] // 20) if imp[1] else 16
        print('  size/20 = %d descriptor slots (last one should be the NULL terminator)' % ndesc)
        for i in range(max(ndesc, 1) + 1):
            p = o + i * 20
            if p + 20 > len(d): break
            oft = u32(d, p); ts = u32(d, p + 4); fwd = u32(d, p + 8)
            nm = u32(d, p + 12); ft = u32(d, p + 16)
            if oft == 0 and nm == 0 and ft == 0:
                print('  [%d] NULL terminator' % i); break
            no = off_of_rva(pe, nm)
            dll = cstr(d, no) if no is not None else '<rva 0x%X NOT FILE-BACKED>' % nm
            print('  [%d] NameRVA=0x%08X  "%-26s"  OFT=0x%08X  FT=0x%08X  ts=0x%X'
                  % (i, nm, dll, oft, ft, ts))
            src = oft if oft else ft
            so = off_of_rva(pe, src)
            if so is None:
                print('        thunk array 0x%X not file-backed' % src); continue
            k = 0; ords = 0; names = []
            while True:
                if so + k * 4 + 4 > len(d): break
                t = u32(d, so + k * 4)
                if t == 0: break
                if t & 0x80000000:
                    ords += 1; names.append('ORDINAL #%d' % (t & 0xFFFF))
                else:
                    no2 = off_of_rva(pe, t)
                    names.append(cstr(d, no2 + 2) if no2 is not None else '<?rva 0x%X>' % t)
                k += 1
                if k > 4000: break
            print('        thunks=%d  of which ordinal=%d' % (k, ords))
            for j, n_ in enumerate(names[:14]):
                print('          [%3d] %s' % (j, n_))
            if len(names) > 14: print('          ... %d more' % (len(names) - 14))

    print()
    print('IAT dir[12]  RVA=0x%08X size=0x%X  -> %d four-byte slots'
          % (iat[0], iat[1], iat[1] // 4))
    io = off_of_rva(pe, iat[0]) if iat[0] else None
    if io is None:
        print('  !! IAT dir absent or not file-backed')
    else:
        n = iat[1] // 4
        cnt = Counter(); ex = {}; firstnz = None
        for k in range(n):
            if io + k * 4 + 4 > len(d): break
            v = u32(d, io + k * 4)
            key = where(pe, v)
            if key.startswith('non-image'): key = 'non-image'
            elif key.startswith('in-image'): key = 'in-image (unmapped rva)'
            cnt[key] += 1
            ex.setdefault(key, []).append((iat[0] + k * 4, v))
            if v and firstnz is None: firstnz = (iat[0] + k * 4, v)
        for k_, c in cnt.most_common():
            e0 = ex[k_][0]
            print('   %-24s %5d   eg slot rva=0x%08X val=0x%08X' % (k_, c, e0[0], e0[1]))
        print('   --- first 40 slots verbatim ---')
        for k in range(min(40, n)):
            if io + k * 4 + 4 > len(d): break
            v = u32(d, io + k * 4)
            print('     %4d  rva=0x%08X  val=0x%08X  %s' % (k, iat[0] + k * 4, v, where(pe, v)))


def mode_slots(pe, rva, n):
    d = pe['data']
    print('=' * 78)
    print('DUMP %d dwords from RVA 0x%08X' % (n, rva))
    o = off_of_rva(pe, rva)
    if o is None:
        print('  !! not file-backed (virtual-only region)')
        return
    for k in range(n):
        if o + k * 4 + 4 > len(d): break
        v = u32(d, o + k * 4)
        print('   +0x%04X  rva=0x%08X  val=0x%08X   %s' % (k * 4, rva + k * 4, v, where(pe, v)))


def mode_hex(pe, rva, n):
    d = pe['data']
    print('=' * 78)
    print('HEXDUMP %d bytes from RVA 0x%08X' % (n, rva))
    o = off_of_rva(pe, rva)
    if o is None:
        print('  !! not file-backed (virtual-only region)')
        return
    for k in range(0, n, 16):
        if o + k >= len(d): break
        chunk = d[o + k:o + k + 16]
        if not chunk: break
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
        print('   rva=0x%08X  %-47s  %s'
              % (rva + k, ' '.join('%02X' % c for c in chunk), asc))


def mode_ascii(pe, rva, n):
    """strings-ish: shows printable runs in a region, useful for name tables"""
    d = pe['data']
    print('=' * 78)
    print('PRINTABLE RUNS in %d bytes from RVA 0x%08X' % (n, rva))
    o = off_of_rva(pe, rva)
    if o is None:
        print('  !! not file-backed'); return
    end = min(o + n, len(d))
    cur = bytearray(); start = None
    for i in range(o, end):
        c = d[i]
        if 32 <= c < 127:
            if start is None: start = i
            cur.append(c)
        else:
            if start is not None and len(cur) >= 4:
                print('   rva=0x%08X off=0x%X  len=%-4d "%s"'
                      % (rva_of(pe, start), start, len(cur), cur.decode('latin1')))
            cur = bytearray(); start = None
    if start is not None and len(cur) >= 4:
        print('   rva=0x%08X off=0x%X  len=%-4d "%s"'
              % (rva_of(pe, start), start, len(cur), cur.decode('latin1')))


def rva_of(pe, off):
    for s in pe['secs']:
        if s['raw'] and s['raw'] <= off < s['raw'] + s['rawsize']:
            return s['va'] + (off - s['raw'])
    return 0


def main():
    pe = parse_pe(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else 'imports'
    if mode == 'imports':
        mode_imports(pe)
    elif mode == 'slots':
        mode_slots(pe, int(sys.argv[3], 0), int(sys.argv[4], 0))
    elif mode == 'hex':
        mode_hex(pe, int(sys.argv[3], 0), int(sys.argv[4], 0))
    elif mode == 'ascii':
        mode_ascii(pe, int(sys.argv[3], 0), int(sys.argv[4], 0))
    else:
        raise SystemExit('unknown mode %s' % mode)


if __name__ == '__main__':
    main()
