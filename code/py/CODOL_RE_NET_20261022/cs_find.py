d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
needle = b'\\2482\\2\\2485\\1\\2490\\214'
i = d.find(needle)
print('found at file offset', hex(i), 'VA', hex(B+i) if i>=0 else None)
if i >= 0:
    print(repr(d[i-60:i+420]))
