# find direct E8-call callers of target VAs in a PE
import struct, sys

def main(path, targets):
    d = open(path, 'rb').read()
    pe = struct.unpack('<I', d[0x3c:0x40])[0]
    opt_size = struct.unpack('<H', d[pe+0x14:pe+0x16])[0]
    sec_off = pe + 0x18 + opt_size
    nsec = struct.unpack('<H', d[pe+6:pe+8])[0]
    base = struct.unpack('<I', d[pe+0x34:pe+0x38])[0]
    secs = []
    for i in range(nsec):
        o = sec_off + i*40
        name = d[o:o+8].rstrip(b'\0').decode(errors='replace')
        vs, va, rs, rp = struct.unpack('<IIII', d[o+8:o+24])
        secs.append((name, base+va, vs, rs, rp))
    for tgt in targets:
        hits = []
        for name, va0, vs, rs, rp in secs:
            if name != '.text':
                continue
            seg = d[rp:rp+rs]
            for i in range(len(seg)-5):
                if seg[i] == 0xE8:
                    rel = struct.unpack('<i', seg[i+1:i+5])[0]
                    srcva = va0 + i
                    if (srcva + 5 + rel) & 0xFFFFFFFF == tgt:
                        hits.append(hex(srcva))
        print(hex(tgt), 'callers:', hits)

if __name__ == '__main__':
    main(sys.argv[1], [int(x, 16) for x in sys.argv[2:]])
