import struct, collections
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
blocks = [(0xCA8000,0xCA8030),(0xCA8038,0xCA8064),(0xCA8074,0xCA80BC),(0xCA80D4,0xCA8368),(0xCA8370,0xCA8384),(0xCA8394,0xCA84AC),(0xCA84D4,0xCA852C),(0xCA8534,0xCA855C),(0xCA85C8,0xCA8600),(0xCA8608,0xCA8680),(0xCA8688,0xCA8740),(0xCA8748,0xCA8760),(0xCB1C64,0xCB1FFC),(0xCB2664,0xCB2A94)]
for a,b in blocks:
    vals = [struct.unpack('<I', d[v-B:v-B+4])[0] for v in range(a,b+4,4)]
    # group by high 16 bits
    grp = collections.Counter(v & 0xFFFF0000 for v in vals)
    print('%#x..%#x n=%d  ranges=%s' % (a,b,len(vals), {hex(k):v for k,v in grp.most_common(5)}))
