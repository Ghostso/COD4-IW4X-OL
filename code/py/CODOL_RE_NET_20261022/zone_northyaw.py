d = open(r"_map_extract\coop_train_zone.bin", "rb").read()
for k in [b"northyaw", b"compass", b"radar", b"minimap"]:
    n = d.count(k)
    print(k, n)
    i = 0
    c = 0
    while c < 5:
        i = d.find(k, i)
        if i < 0:
            break
        s = d[i-60:i+80]
        print("  ", hex(i), "".join(chr(x) if 32 <= x < 127 else "." for x in s))
        i += 1
        c += 1
