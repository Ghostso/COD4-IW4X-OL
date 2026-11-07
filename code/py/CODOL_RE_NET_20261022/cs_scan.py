import struct
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000

def find_all(needle):
    out = []
    i = 0
    while True:
        i = d.find(needle, i)
        if i < 0:
            break
        out.append(B + i)
        i += 1
    return out

for needle in [b'1159\x00', b'** 585 0 0 6690', b'coop_train_mp_firingrange\x00', b'g_gametype']:
    hits = find_all(needle)
    print('==', needle[:24], 'count', len(hits))
    for va in hits[:20]:
        print('   ', hex(va))
