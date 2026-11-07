import sys
p = r'run_codol_001\runs\OMIT_RETEST_20261022\kit\firingrange-gamestate.bin'
d = open(p, 'rb').read()
print('len', len(d))
for i in range(0, len(d), 16):
    b = d[i:i+16]
    print('%04x  %-47s %s' % (i, b.hex(' '), ''.join(chr(c) if 32 <= c < 127 else '.' for c in b)))
