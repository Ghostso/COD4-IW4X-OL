# -*- coding: utf-8 -*-
"""Parse the task 71/4 request payload."""
hexs = ("13 08 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
"13 08 10 00 00 00 43 4F 44 4F 4C 2D 4C 4F 43 41 4C 2D 30 30 30 31 "
"08 9E CB E6 01 "
"13 08 80 00 00 00 20 21 22 23 24 25 26 27 28 29 2A 2B 2C 2D 2E 2F 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F 40 41 42 43 44 45 46 47 48 49 4A 4B 4C 4D 4E 4F 50 51 52 53 54 55 56 57 58 59 5A 5B 5C 5D 5E 5F "
"20 21 22 23 24 25 26 27 28 29 2A 2B 2C 2D 2E 2F 30 31 32 33 34 35 36 37 38 39 3A 3B 3C 3D 3E 3F 40 41 42 43 44 45 46 47 48 49 4A 4B 4C 4D 4E 4F 50 51 52 53 54 55 56 57 58 59 5A 5B 5C 5D 5E 5F "
"13 08 80 00 00 00 " + "00 "*128 +
"10 44 34 2D 39 33 2D 39 30 2D 31 38 2D 35 35 2D 31 30 00 00")
b = bytes.fromhex(hexs)
print("total:", len(b))
off = 0
n = 0
while off < len(b):
    if b[off] == 0x13 and off+1 < len(b) and b[off+1] == 0x08:
        ln = int.from_bytes(b[off+2:off+6], "little")
        data = b[off+6:off+6+ln]
        n += 1
        show = data if len(data) <= 24 else data[:16]
        print("  obj%d @%3d  tag13/08 len=%-4d %r%s" % (n, off, ln, show, " ..." if len(data)>24 else ""))
        off += 6 + ln
    else:
        print("  @%3d  other tag=0x%02X  %r" % (off, b[off], b[off:off+24]))
        break
print()
print("tail from", off, ":", b[off:].hex(" "))
