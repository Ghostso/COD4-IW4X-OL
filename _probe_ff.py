import zlib, re
p = r"COD OL\main\ui_mp.ff"
raw = open(p, "rb").read()
print("size", len(raw), "magic", raw[:8])
found = False
for off in range(8, 64):
    for wbits in (-zlib.MAX_WBITS, zlib.MAX_WBITS, 31):
        try:
            dec = zlib.decompress(raw[off:], wbits)
            print("OK off=%d wbits=%d len=%d" % (off, wbits, len(dec)))
            for pat in (b"a20210427unite", b"20210427", b"codol.qq.com"):
                i = dec.find(pat)
                print("  ", pat, "->", i)
                if i >= 0:
                    print("   ctx:", dec[max(0,i-120):i+160])
            found = True
            break
        except Exception:
            pass
    if found:
        break
if not found:
    print("no decompress")