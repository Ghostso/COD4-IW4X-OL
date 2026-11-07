# -*- coding: utf-8 -*-
"""
ff15_pe_map.py  -- READ ONLY analysis.

Goal: upgrade FF15/FF25 findings from "byte statistics" to
      "operand -> VA/RVA -> section" relations.

Explicitly does NOT claim any operand is an IAT slot.
It only reports: address-like pointer target.

Usage: python ff15_pe_map.py <pefile>
"""
import sys, struct, collections, os

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def parse_pe(path):
    d = open(path, 'rb').read()
    pe = {}
    pe['file'] = path
    pe['size'] = len(d)
    if d[:2] != b'MZ': raise SystemExit('not MZ')
    e_lfanew = u32(d, 0x3C)
    pe['e_lfanew'] = e_lfanew
    if d[e_lfanew:e_lfanew+4] != b'PE\0\0': raise SystemExit('not PE')
    coff = e_lfanew + 4
    machine = u16(d, coff)
    nsec = u16(d, coff + 2)
    optsz = u16(d, coff + 16)
    chars = u16(d, coff + 18)
    pe['machine'] = machine
    pe['nsec'] = nsec
    pe['optsz'] = optsz
    pe['characteristics'] = chars
    opt = coff + 20
    magic = u16(d, opt)
    pe['magic'] = magic
    if magic == 0x10B:
        pe['pe32'] = True
        pe['imagebase'] = u32(d, opt + 28)
        pe['sizeofimage'] = u32(d, opt + 56)
        pe['sectionalign'] = u32(d, opt + 32)
        pe['filealign'] = u32(d, opt + 36)
        pe['entry'] = u32(d, opt + 16)
        ddoff = opt + 96
    elif magic == 0x20B:
        pe['pe32'] = False
        pe['imagebase'] = struct.unpack_from('<Q', d, opt + 24)[0]
        pe['sizeofimage'] = u32(d, opt + 56)
        pe['sectionalign'] = u32(d, opt + 32)
        pe['filealign'] = u32(d, opt + 36)
        pe['entry'] = u32(d, opt + 16)
        ddoff = opt + 112
    else:
        raise SystemExit('bad magic %x' % magic)
    ndd = u32(d, opt + (92 if magic == 0x10B else 108))
    pe['ndd'] = ndd
    dirs = []
    for i in range(min(ndd, 16)):
        rva = u32(d, ddoff + i*8)
        sz = u32(d, ddoff + i*8 + 4)
        dirs.append((i, rva, sz))
    pe['dirs'] = dirs
    secoff = opt + optsz
    secs = []
    for i in range(nsec):
        o = secoff + i*40
        name = d[o:o+8].rstrip(b'\0')
        vsize = u32(d, o+8)
        va = u32(d, o+12)
        rawsz = u32(d, o+16)
        praw = u32(d, o+20)
        sc = u32(d, o+36)
        secs.append({'i': i, 'name': name, 'vsize': vsize, 'va': va,
                     'rawsz': rawsz, 'praw': praw, 'chars': sc})
    pe['secs'] = secs
    pe['data'] = d
    return pe

def secname(pe, rva):
    for s in pe['secs']:
        sz = max(s['vsize'], s['rawsz'])
        if s['va'] <= rva < s['va'] + sz:
            return s['name'].decode('latin1')
    return None

def sec_of_rva(pe, rva):
    for s in pe['secs']:
        sz = max(s['vsize'], s['rawsz'])
        if s['va'] <= rva < s['va'] + sz:
            return s
    return None

def rva2off(pe, rva):
    s = sec_of_rva(pe, rva)
    if not s: return None
    delta = rva - s['va']
    if delta >= s['rawsz']: return None
    return s['praw'] + delta

def fmt(i): return '0x%08X' % i

def main():
    path = sys.argv[1]
    pe = parse_pe(path)
    d = pe['data']
    print('=' * 78)
    print('FILE      : %s' % pe['file'])
    print('SIZE      : %d bytes (0x%X)' % (pe['size'], pe['size']))
    print('MACHINE   : 0x%04X   magic=0x%X (%s)' % (
        pe['machine'], pe['magic'], 'PE32' if pe['pe32'] else 'PE32+'))
    print('IMAGEBASE : %s   SizeOfImage=%s' % (fmt(pe['imagebase']), fmt(pe['sizeofimage'])))
    print('ENTRY     : %s' % fmt(pe['entry']))
    print('SECT ALIGN: 0x%X  FILE ALIGN: 0x%X  #SECTIONS=%d  #DIRS=%d' % (
        pe['sectionalign'], pe['filealign'], pe['nsec'], pe['ndd']))
    print('-' * 78)
    print('DATA DIRECTORIES (MEASURED, not pattern-inferred)')
    names = {0:'EXPORT',1:'IMPORT',2:'RESOURCE',3:'EXCEPTION',4:'SECURITY',
             5:'BASERELOC',6:'DEBUG',7:'ARCH',8:'GLOBALPTR',9:'TLS',
             10:'LOADCFG',11:'BOUNDIMP',12:'IAT',13:'DELAYIMP',14:'CLR'}
    for i, rva, sz in pe['dirs']:
        st = 'PRESENT' if (rva or sz) else 'ABSENT'
        print('  dir[%2d] %-10s rva=%s size=0x%-8X %s  sec=%s' % (
            i, names.get(i, '?'), fmt(rva), sz, st,
            secname(pe, rva) if rva else '-'))
    print('-' * 78)
    print('SECTIONS')
    print('  %-3s %-9s %-10s %-10s %-10s %-10s %s' % (
        '#','name','VAddr','VSize','RawPtr','RawSize','chars'))
    for s in pe['secs']:
        print('  %-3d %-9s %-10s %-10s %-10s %-10s %08X' % (
            s['i'], s['name'].decode('latin1'), fmt(s['va']), fmt(s['vsize']),
            fmt(s['praw']), fmt(s['rawsz']), s['chars']))
    print('  (end of image VA = %s)' % fmt(pe['imagebase'] + pe['sizeofimage']))

    # ---------- census ----------
    allpos = []
    for i in range(len(d) - 6):
        if d[i] == 0xFF and d[i+1] in (0x15, 0x25):
            allpos.append(i)
    greedy = []
    last = -10
    for p in allpos:
        if p >= last + 6:
            greedy.append(p)
            last = p

    print('=' * 78)
    print('CENSUS')
    print('  FF15/FF25 raw scan positions (overlap allowed) : %d' % len(allpos))
    print('  FF15/FF25 greedy non-overlapping               : %d' % len(greedy))
    byop = collections.Counter(d[p+1] for p in allpos)
    print('  by opcode byte: %s' % dict((hex(k), v) for k, v in sorted(byop.items())))

    # section of each instruction
    inj = collections.Counter()
    for p in greedy:
        s = None
        for sec in pe['secs']:
            if sec['praw'] <= p < sec['praw'] + sec['rawsz']:
                s = sec['name'].decode('latin1'); break
        inj[s or 'NOT-IN-SECTION'] += 1
    print('  instruction located in section: %s' % dict(inj))

    # ---------- operand interpretation ----------
    print('=' * 78)
    print('OPERAND INTERPRETATION  (greedy set, n=%d)' % len(greedy))
    ib = pe['imagebase']
    secs = pe['secs']

    modes = {
        'as_VA_minus_imagebase': lambda op: op - ib,
        'as_raw_RVA'           : lambda op: op,
        'as_VA_minus_0x400000' : lambda op: op - 0x400000,
    }
    for label, fn in modes.items():
        hit = collections.Counter()
        inrange = 0
        for p in greedy:
            op = u32(d, p + 2)
            rva = fn(op)
            if rva < 0 or rva > 0xFFFFFFFF:
                hit['OVERFLOW/NEGATIVE'] += 1; continue
            s = sec_of_rva(pe, rva)
            if s:
                hit[s['name'].decode('latin1')] += 1
                inrange += 1
            else:
                if rva < pe['sizeofimage']:
                    hit['IN-IMAGE-NO-SECTION (header/gap)'] += 1
                else:
                    hit['OUTSIDE-IMAGE'] += 1
        print('  %-24s in-section=%d  %s' % (label, inrange, dict(hit)))

    # ---------- top targets ----------
    print('=' * 78)
    print('TOP OPERAND VALUES (greedy set) -- "address-like pointer target" only')
    cnt = collections.Counter(u32(d, p+2) for p in greedy)
    print('  distinct operand values: %d' % len(cnt))
    print('  operands occurring >1 time: %d' % sum(1 for v in cnt.values() if v > 1))
    for op, c in cnt.most_common(25):
        rva = op - ib
        s = sec_of_rva(pe, rva)
        print('   op=%s  callsites=%-4d  VA-ImageBase=%s -> %s' % (
            fmt(op), c, fmt(rva) if 0 <= rva <= 0xFFFFFFFF else 'NEG',
            (s['name'].decode('latin1') + (' +0x%X' % (rva - s['va']))) if s else 'OUT-OF-IMAGE'))

    # ---------- band histogram ----------
    print('=' * 78)
    print('OPERAND HIGH-BYTE BAND HISTOGRAM (greedy set)')
    band = collections.Counter()
    for p in greedy:
        op = u32(d, p+2)
        band['0x%02X000000-0x%02XFFFFFF' % (op >> 24, op >> 24)] += 1
    for k in sorted(band):
        print('  %s : %d' % (k, band[k]))

    # ---------- stride / contiguity ----------
    print('=' * 78)
    print('STRIDE / CONTIGUITY OF TARGET ADDRESSES (as raw VA)')
    for label, fn in (('VA(ImageBase-relative)', lambda op: op - ib),
                      ('raw-RVA', lambda op: op)):
        vals = sorted(set(fn(u32(d, p+2)) for p in greedy))
        vals = [v for v in vals if sec_of_rva(pe, v)]
        if len(vals) < 2: continue
        gaps = collections.Counter(b - a for a, b in zip(vals, vals[1:]))
        print('  [%s] usable targets=%d  top gaps: %s' % (
            label, len(vals), gaps.most_common(8)))
        # longest run of stride-4
        best = cur = 1; bs = None; cs = None
        for a, b in zip(vals, vals[1:]):
            if b - a == 4:
                if cur == 1: cs = a
                cur += 1
                if cur > best: best = cur; bs = cs
            else:
                cur = 1
        print('      longest stride-4 run: %d slots%s' % (
            best, (' starting %s' % fmt(bs)) if bs else ''))

    # ---------- is a target inside dir[12] IAT range? ----------
    print('=' * 78)
    print('CROSS-CHECK vs MEASURED dir[12] (IAT) AND dir[1] (IMPORT) RANGES')
    dd = dict((i, (r, z)) for i, r, z in pe['dirs'])
    for di, nm in ((12, 'IAT'), (1, 'IMPORT'), (5, 'BASERELOC')):
        r, z = dd.get(di, (0, 0))
        if not r:
            print('  dir[%d] %-9s ABSENT -> zero operands can land in it' % (di, nm))
            continue
        n = sum(1 for p in greedy if r <= (u32(d, p+2) - ib) < r + z)
        print('  dir[%d] %-9s range=[%s,%s)  greedy operands(as VA-ImageBase) inside=%d' % (
            di, nm, fmt(r), fmt(r+z), n))

    # ---------- second level test ----------
    print('=' * 78)
    print('SECOND-LEVEL TEST: does the 4 bytes AT the target look like a code pointer?')
    tops = [op for op, c in cnt.most_common(20)]
    for op in tops:
        rva = op - ib
        off = rva2off(pe, rva) if 0 <= rva <= 0xFFFFFFFF else None
        if off is None or off + 4 > len(d):
            print('   %s -> no file backing' % fmt(op)); continue
        val = u32(d, off)
        trva = val - ib
        ts = sec_of_rva(pe, trva) if 0 <= trva <= 0xFFFFFFFF else None
        print('   slot %s holds %s -> %s' % (
            fmt(op), fmt(val),
            (ts['name'].decode('latin1') + ' +0x%X' % (trva - ts['va'])) if ts else 'OUT-OF-IMAGE'))

    # ---------- the 0x0E9DC665 sequence ----------
    print('=' * 78)
    print('KNOWN ISOLATED SEQUENCE  FF 15 65 C6 9D 0E  (operand 0x0E9DC665)')
    pat = bytes.fromhex('FF1565C69D0E')
    idx = -1; hits = []
    while True:
        idx = d.find(pat, idx + 1)
        if idx < 0: break
        hits.append(idx)
    print('  exact 6-byte occurrences: %d  at file offsets %s' % (
        len(hits), [hex(x) for x in hits]))
    for h in hits:
        s = None
        for sec in pe['secs']:
            if sec['praw'] <= h < sec['praw'] + sec['rawsz']:
                s = sec; break
        if s:
            print('   offset 0x%X -> section %s RVA %s' % (
                h, s['name'].decode('latin1'), fmt(s['va'] + (h - s['praw']))))

if __name__ == '__main__':
    main()
