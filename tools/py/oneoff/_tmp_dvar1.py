import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regs = []
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p = line.split()
    if len(p) >= 5: regs.append((int(p[0],16), int(p[1],16), p[4]))
def blob(fn):
    for base,size,f in regs:
        if f == fn: return base, open(os.path.join(D,fn),'rb').read()
    return None, None
base, data = blob('r_00CA8000.bin')
# 0x00DDE834 附近 0x200 字节的原始 hex
off = 0x00DDE7F0 - base
print('=== 0x00DDE7F0 原始 hex ===')
for i in range(0, 0x1A0, 16):
    chunk = data[off+i:off+i+16]
    if not chunk: break
    hexs = chunk.hex(' ')
    asc = ''.join(chr(c) if 32<=c<=126 else '.' for c in chunk)
    print('  0x%08X  %-47s  %s' % (base+off+i, hexs, asc))
