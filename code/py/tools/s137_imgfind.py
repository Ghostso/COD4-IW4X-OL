#!/usr/bin/env python3
"""s137: search the client image for byte patterns. VA = fileoff + 0x400000."""
import sys, struct
IMG = r"E:\codol_re\client_image_20261027.bin"

def find_all(data, pat, limit=40):
    out = []; i = 0
    while True:
        j = data.find(pat, i)
        if j < 0: break
        out.append(j)
        i = j + 1
        if len(out) >= limit: break
    return out

def main():
    pats = sys.argv[1:]
    if not pats:
        pats = ["181c5a98d6145391cf01"]
    with open(IMG, "rb") as f:
        data = f.read()
    print("image size", len(data))
    for p in pats:
        pat = bytes.fromhex(p)
        hits = find_all(data, pat)
        print("pat %s : %d hits" % (p, len(hits)))
        for h in hits[:20]:
            print("   fileoff=0x%08X VA=0x%08X" % (h, h + 0x400000))

if __name__ == "__main__":
    main()
