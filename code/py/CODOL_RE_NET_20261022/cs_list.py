import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
def u32(va):
    if not (B <= va < B + len(d)):
        return None
    return struct.unpack("<I", d[va-B:va-B+4])[0]
def cstr(va):
    if not (B <= va < B + len(d)):
        return None
    o = va - B
    e = d.find(b"\x00", o)
    return d[o:e].decode("latin1", "replace")
p = u32(0x8424360)
print("head", hex(p) if p else None)
n = 0
while p and n < 40:
    nxt = u32(p)
    txt = u32(p + 4)
    print(hex(p), "next", hex(nxt) if nxt else None, "text", hex(txt) if txt else None, repr(cstr(txt) if txt else None))
    p = nxt
    n += 1
