# -*- coding: utf-8 -*-
import os, struct
p = r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\mem_linear_20261007_134406\r_39EEA000_00246000.bin'
b = open(p, 'rb').read()
print("size = %d (0x%X)" % (len(b), len(b)))
print()
print("=== all 'mmbook' occurrences ===")
i = 0; n = 0
while n < 10:
    i = b.find(b'mmbook', i)
    if i < 0: break
    print("   off=0x%X  %r" % (i, b[i:i+44]))
    i += 1; n += 1
print()
print("=== SessionId 0x1122334455667788 (LE u64) ===")
pat = struct.pack('<Q', 0x1122334455667788)
j = b.find(pat)
print("   %s" % (hex(j) if j >= 0 else "NOT FOUND"))
if j >= 0: print("   context: " + b[max(0,j-40):j+56].hex(" "))
print()
print("=== candidate dwords ===")
for v in (0x11223344, 0x55667788, 0x12E38001, 0x0C0DE001, 1432778633):
    q = b.find(struct.pack('<I', v))
    print("   0x%08X (%d) -> %s" % (v, v, hex(q) if q >= 0 else "not found"))
print()
print("=== strings ===")
for s in (b'coop_take_mp_fav_tropical', b'mp_crash_tropical', b'mp_firingrange',
          b'1432778633', b'288240001', b'localConfig'):
    q = b.find(s)
    print("   %-28s -> %s" % (s.decode(), hex(q) if q >= 0 else "not found"))
