import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
b=open(os.path.join(D,'r_3D5BB000.bin'),'rb').read()
base=0x3D5BB000
obj=0x3D5BB008
print('=== 0x10600..0x10640 原始 (闸门B 所在) ===')
o=obj+0x10600-base
for k in range(0,0x40,16):
    c=b[o+k:o+k+16]
    print('  +0x%X  %-47s  %s' % (0x10600+k, c.hex(' '), ''.join(chr(x) if 32<=x<=126 else '.' for x in c)))
print()
print('=== 附近有没有可读字符串 (整块 0x10500..0x10800) ===')
lo=obj+0x10500-base; hi=obj+0x10800-base
cur=bytearray(); pos=lo
for ch in b[lo:hi]:
    if 32<=ch<=126: cur.append(ch)
    else:
        if len(cur)>=6: print('  0x%08X  %s' % (obj+pos-len(cur), cur.decode('latin1')))
        cur=bytearray()
    pos+=1
