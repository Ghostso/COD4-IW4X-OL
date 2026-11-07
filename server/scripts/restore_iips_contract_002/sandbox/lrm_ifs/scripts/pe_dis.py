#!/usr/bin/env python3
# pe_dis.py - static disasm helper for CODOL TCLS analysis
# Usage:
#   python pe_dis.py <image> <out> <start>:<end|f> [...]  (end 'f' = func mode)
#   python pe_dis.py <image> dump <va> <len>
#   python pe_dis.py <image> find <hexpattern>
import sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

def load_pe(path):
    data = open(path, 'rb').read()
    pe_off = struct.unpack_from('<I', data, 0x3C)[0]
    num_sec = struct.unpack_from('<H', data, pe_off + 6)[0]
    opt_size = struct.unpack_from('<H', data, pe_off + 20)[0]
    opt = pe_off + 24
    image_base = struct.unpack_from('<I', data, opt + 28)[0]
    imp_rva = struct.unpack_from('<I', data, opt + 104)[0]
    secs = []
    soff = opt + opt_size
    for _ in range(num_sec):
        name = data[soff:soff + 8].split(b'\0')[0].decode('latin1')
        vsz, va, rsz, rptr = struct.unpack_from('<IIII', data, soff + 8)
        secs.append((name, va, vsz, rptr, rsz))
        soff += 40
    return data, image_base, secs, imp_rva

def va2off(secs, base, va):
    rva = va - base
    for name, sva, vsz, rptr, rsz in secs:
        if sva <= rva < sva + max(vsz, rsz):
            return rptr + (rva - sva)
    return None

def read_at(data, secs, base, va, n):
    off = va2off(secs, base, va)
    if off is None or off + n > len(data):
        return None
    return data[off:off + n]

def parse_imports(data, base, secs, imp_rva):
    out = {}
    off = va2off(secs, base, base + imp_rva)
    if off is None:
        return out
    while True:
        ilt, ts, fc, name_rva, iat = struct.unpack_from('<IIIII', data, off)
        if ilt == 0 and name_rva == 0 and iat == 0:
            break
        noff = va2off(secs, base, base + name_rva)
        dll = data[noff:data.index(b'\0', noff)].decode('latin1')
        thunk_rva = ilt if ilt else iat
        toff = va2off(secs, base, base + thunk_rva)
        iat_va = base + iat
        while True:
            val = struct.unpack_from('<I', data, toff)[0]
            if val == 0:
                break
            if val & 0x80000000:
                fname = 'ord%d' % (val & 0xFFFF)
            else:
                foff = va2off(secs, base, base + val)
                fname = data[foff + 2:data.index(b'\0', foff + 2)].decode('latin1')
            out[iat_va] = '%s!%s' % (dll, fname)
            iat_va += 4
            toff += 4
        off += 20
    return out

def try_string(data, secs, base, va):
    raw = read_at(data, secs, base, va, 260)
    if raw is None:
        return None
    n = raw.find(b'\0')
    if 4 <= n <= 200 and all(32 <= c < 127 or c in (9, 13, 10) for c in raw[:n]):
        return "'%s'" % raw[:n].decode('latin1')
    if len(raw) >= 10 and raw[1] == 0 and raw[3] == 0:
        end = raw.find(b'\0\0')
        if end > 0 and end % 2 == 0 and end <= 240:
            try:
                s = raw[:end].decode('utf-16le')
                if len(s) >= 3 and all(ord(c) >= 32 or c in '\t\r\n' for c in s):
                    return "L'%s'" % s
            except Exception:
                pass
    return None


def resolve_thunk(data, secs, base, va):
    b = read_at(data, secs, base, va, 12)
    if b is None:
        return None
    if b[0] == 0xB8 and b[5] == 0xFF and b[6] == 0xE0:
        return struct.unpack_from('<I', b, 1)[0]
    if b[0] == 0xE9:
        rel = struct.unpack_from('<i', b, 1)[0]
        return (va + 5 + rel) & 0xFFFFFFFF
    return None

def disasm_range(md, data, base, secs, imports, start, end, func_mode):
    lines = []
    va = start
    ret_seen = False
    pad = 0
    while va < end:
        b = read_at(data, secs, base, va, 16)
        if b is None:
            break
        if func_mode and ret_seen:
            if b[0] in (0xCC, 0x90):
                pad += 1
                lines.append('%08X: %s' % (va, 'int3' if b[0] == 0xCC else 'nop'))
                va += 1
                if pad >= 4:
                    break
                continue
            break
        insns = list(md.disasm(b, va, count=1))
        if not insns:
            lines.append('%08X: db 0x%02X' % (va, b[0]))
            va += 1
            continue
        ins = insns[0]
        text = '%08X: %-10s %s' % (va, ins.mnemonic, ins.op_str)
        cmt = []
        if ins.mnemonic == 'call' and ins.op_str.startswith('dword ptr [0x'):
            iat = int(ins.op_str[ins.op_str.index('[0x') + 1:ins.op_str.index(']')], 16)
            if iat in imports:
                cmt.append(imports[iat])
        if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
            tgt = int(ins.op_str, 16)
            r = resolve_thunk(data, secs, base, tgt)
            if r is not None:
                cmt.append('->0x%X' % r)
        for tok in ins.op_str.replace(',', ' ').split():
            if tok.startswith('0x') and len(tok) >= 8:
                try:
                    v = int(tok, 16)
                except ValueError:
                    continue
                if base <= v < base + 0x2000000:
                    s = try_string(data, secs, base, v)
                    if s:
                        cmt.append(s)
        if cmt:
            text += '    ; ' + ' | '.join(cmt)
        lines.append(text)
        va += ins.size
        if func_mode and ins.mnemonic.startswith('ret'):
            ret_seen = True
    return lines

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    img = sys.argv[1]
    data, base, secs, imp_rva = load_pe(img)
    imports = parse_imports(data, base, secs, imp_rva)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    mode = sys.argv[2]
    if mode == 'dump':
        va = int(sys.argv[3], 16)
        n = int(sys.argv[4], 0)
        raw = read_at(data, secs, base, va, n)
        if raw is None:
            print('VA not mapped')
            return 1
        for i in range(0, len(raw), 16):
            chunk = raw[i:i + 16]
            hexs = ' '.join('%02X' % c for c in chunk)
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
            print('%08X  %-47s  %s' % (va + i, hexs, asc))
        return 0
    if mode == 'find':
        pat = bytes.fromhex(sys.argv[3])
        at = 0
        while True:
            i = data.find(pat, at)
            if i < 0:
                break
            vava = None
            for name, sva, vsz, rptr, rsz in secs:
                if rptr <= i < rptr + rsz:
                    vava = base + sva + (i - rptr)
            print('raw 0x%X  VA 0x%s' % (i, ('%08X' % vava) if vava else '????????'))
            at = i + 1
        return 0
    out_path = mode
    all_lines = []
    for spec in sys.argv[3:]:
        s, e = spec.split(':')
        start = int(s, 16)
        if e == 'f':
            all_lines.append('### FUNC %08X' % start)
            all_lines += disasm_range(md, data, base, secs, imports, start, start + 0x1000, True)
        else:
            end = int(e, 16)
            all_lines.append('### RANGE %08X-%08X' % (start, end))
            all_lines += disasm_range(md, data, base, secs, imports, start, end, False)
    with open(out_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write('\n'.join(all_lines))
    print('wrote %d lines -> %s' % (len(all_lines), out_path))
    return 0

if __name__ == '__main__':
    sys.exit(main())
