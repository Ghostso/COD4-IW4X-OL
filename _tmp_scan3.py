import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
print('loaded %.0f MB' % (len(img)/1048576))
print()
print('=== 1) 搜 disp32 == 0x00010614 (用 find 加速) ===')
pat = struct.pack('<I', 0x10614)
n = 0
i = img.find(pat)
while i >= 0 and n < 30:
    if cov[i] == 1:
        va = LO + i
        ctx = img[max(0,i-10):i+14]
        print('   0x%08X  %s' % (va, ctx.hex(' ')))
        n += 1
    i = img.find(pat, i+1)
print('  共', n)
print()
print('=== 2) 搜 call/jmp rel32 到闸门B 0x0062FE80 ===')
tgt = 0x0062FE80
lo = 0x400000 - LO
hi = min(0x0EA59000 - LO, len(img) - 5)
res = []; k = img.find(b'\xE8', lo, hi)
while k >= 0 and len(res) < 20:
    if cov[k] == 1:
        rel = struct.unpack_from('<i', img, k+1)[0]
        if LO + k + 5 + rel == tgt:
            res.append(LO+k)
    k = img.find(b'\xE8', k+1, hi)
for a in res: print('   call @0x%08X' % a)
print('  共', len(res))
