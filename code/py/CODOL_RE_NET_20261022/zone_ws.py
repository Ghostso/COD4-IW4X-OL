d = open(r"_map_extract\coop_train_zone.bin", "rb").read()
i = d.find(b"worldspawn")
print("file offset", hex(i))
s = d[i:i+900]
print("".join(chr(c) if 32 <= c < 127 else "." for c in s))
