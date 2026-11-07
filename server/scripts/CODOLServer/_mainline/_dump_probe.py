import re, struct, os
d = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_111537\engine'
p = os.path.join(d,'engine_best.bin')
b = open(p,'rb').read()
print('size', len(b), hex(len(b)))
base = 0x00994000
nz = sum(1 for x in b if x)
print('nonzero', nz, 'ratio %.3f' % (nz/len(b)))
ff15 = [i for i in range(len(b)-6) if b[i:i+2]==b'\xff\x15']
print('FF15 count', len(ff15))
slots = {}
for i in ff15:
    v = struct.unpack_from('<I', b, i+2)[0]
    slots[v] = slots.get(v,0)+1
print('distinct ff15 slot targets', len(slots))
ca = [v for v in slots if 0x00ca8000 <= v < 0x00caa000]
print('slots into 0xCA8xxx (in-image)', len(ca))
# print first 40 slot targets sorted
for v in sorted(slots)[:30]:
    print('  %08x x%d' % (v, slots[v]))
