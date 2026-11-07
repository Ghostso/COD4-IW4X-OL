# 24-byte constant block at [ebp-0x1C] and the permutation table at [ebp-0x7C]
block = [0x90F542AD,0xE621A488,0x0289C93B,0xDC02FF39,0xFF770411,0x0D6288EE]
b = b"".join(x.to_bytes(4,"little") for x in block)
print("const24 =", b.hex())
print("ascii   =", ''.join(chr(c) if 32<=c<127 else '.' for c in b))
print()
tbl = [8,0x12,9,0xe,5,0x14,0xa,7,0xb,0xc,0x15,0x16]
print("table[0:12] =", tbl)
print("indices are used as: bl = byte ptr [ebp + ebx - 0x1c]")
print("=> table entries index INTO the 24-byte block")
