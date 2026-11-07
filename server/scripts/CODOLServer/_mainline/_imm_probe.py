import csv, re, struct, sys
csvp = r'D:\BaiduNetdiskDownload\使命召唤OL\RESTORE001_FUNCTION_DUMPS.csv'
rows = list(csv.DictReader(open(csvp, encoding='utf-8-sig')))
print('rows', len(rows))
print('cols', rows[0].keys())
# collect all immediate operands from push/lea/mov in the hex dumps
imm = {}
for r in rows:
    hx = (r.get('hex_dump') or '').replace('"','').strip()
    try:
        b = bytes.fromhex(hx)
    except Exception:
        continue
    for i in range(len(b)-4):
        if b[i] in (0x68,):  # push imm32
            v = struct.unpack_from('<I', b, i+1)[0]
            if 0x00400000 <= v < 0x14000000:
                imm.setdefault(v, []).append((r['function_name'], 'push'))
        if b[i] in (0xb8,0xb9,0xba,0xbb,0xbe,0xbf):
            v = struct.unpack_from('<I', b, i+1)[0]
            if 0x00400000 <= v < 0x14000000:
                imm.setdefault(v, []).append((r['function_name'], 'mov'))
print('distinct imm targets', len(imm))
for v in sorted(imm):
    if 0x00c00000 <= v < 0x00d50000 or 0x00e00000 <= v < 0x00f00000:
        print('%08x' % v, imm[v][:3])
