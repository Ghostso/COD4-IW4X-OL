d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
for k in [b'"ambient"', b'skylight', b'"classname"']:
    n = d.count(k)
    print(k, n)
    i = 0
    c = 0
    while c < 3:
        i = d.find(k, i)
        if i < 0:
            break
        s = d[i-40:i+120]
        print("  VA", hex(B+i), "".join(chr(x) if 32 <= x < 127 else "." for x in s)[:150])
        i += 1
        c += 1
