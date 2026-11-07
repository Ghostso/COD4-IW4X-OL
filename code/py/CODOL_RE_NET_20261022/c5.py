import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
# look at the actual bytes: is 0x3306994 a static array or a base offset into a struct?
# Check nearby globals for a pointer at fixed offset
for va in (0x3306910, 0x3306994, 0x33069D4, 0x3306A14):
    o = va - B
    print(hex(va), d[o:o+32].hex(" "))
print()
# search for mov where base is [0x3306910] style and array index applied to a loaded base
# Instead: find what addresses point near 0x3306994
for target in (0x3306990, 0x3306980, 0x3306900):
    pat = struct.pack("<I", target)
    hits = []
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        v = B + i
        if 0x401000 <= v < 0xE5C8000:
            hits.append(v)
        i += 1
    print(hex(target), len(hits), [hex(x) for x in hits[:8]])
