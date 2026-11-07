import struct, re
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
# find all IAT-like blocks: sequences of dwords pointing into loaded DLLs
for lo, hi, name in [(0xCA8000,0xCB4000,'exe .data IAT-ish')]:
    print('===', name)
    i = lo
    runs = []
    cur = None
    for va in range(lo, hi, 4):
        v = struct.unpack('<I', d[va-B:va-B+4])[0]
        ok = 0x71000000 <= v < 0x78000000 or 0x10000000 <= v < 0x30000000
        if ok:
            if cur is None: cur = [va, va]
            else: cur[1] = va
        else:
            if cur: runs.append(tuple(cur)); cur = None
    if cur: runs.append(tuple(cur))
    for a,b in runs:
        if b-a >= 12:
            print('  run %#x..%#x (%d dwords)' % (a,b,(b-a)//4+1))
