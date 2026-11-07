import zlib

with open(r"COD OL\main\ui_mp.ff", "rb") as f:
    raw = f.read()

print("File size:", len(raw))
# IWff0100 is 8 bytes, followed by version (4 bytes), then zlib stream
# Let's search for 0x78 0x9c or 0x78 0xda (standard zlib headers)
for off in range(8, 32):
    try:
        dec = zlib.decompress(raw[off:], -zlib.MAX_WBITS)
        print(f"Decompressed raw deflate from offset {off}: {len(dec)} bytes")
        break
    except Exception:
        try:
            dec = zlib.decompress(raw[off:])
            print(f"Decompressed zlib from offset {off}: {len(dec)} bytes")
            break
        except Exception:
            pass
