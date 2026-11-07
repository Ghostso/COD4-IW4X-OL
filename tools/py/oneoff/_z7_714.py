# -*- coding: utf-8 -*-
"""Parse the 71/4 identity request into its TLV objects."""
# from the log
hx = ("13 08 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
      "13 08 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
      "08 9E CB E6 01 "
      "13 08 00 00 00 00 "
      "13 08 80 00 00 00 " + "00 "*128 +
      "10 44 34 2D 39 33 2D 39 30 2D 31 38 2D 35 35 2D 31 30 00 00")
b = bytes.fromhex(hx)
print("total:", len(b))
off = 0
n = 0
while off < len(b):
    tag = b[off]
    if tag == 0x13 and off+1 < len(b) and b[off+1] == 0x08:
        ln = int.from_bytes(b[off+2:off+6], "little")
        data = b[off+6:off+6+ln]
        n += 1
        print("  obj%d  tag=13/08 len=%-4d data=%s" % (n, ln, data[:32].hex() if len(data)>0 else "(empty)"))
        if all(x == 0 for x in data):
            print("         (all zeros)")
        off += 6 + ln
    elif tag == 0x08:
        # maybe a raw u32?
        print("  @%3d  tag=0x08 raw=%s" % (off, b[off:off+8].hex()))
        off += 1
    elif tag == 0x10:
        s = b[off+1:off+1+24].split(b"\x00")[0]
        print("  @%3d  tag=0x10 str=%r" % (off, s))
        off += 1 + len(s) + 1
    else:
        print("  @%3d  unknown tag=0x%02X" % (off, tag))
        off += 1
