#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""s137_callers.py <target_VA> [<target_VA> ...]
Find E8 rel32 direct-call sites that target the given VA(s) in the flat image.
VA = file_off + 0x400000 ; image = E:\\codol_re\\client_image_20261027.bin
Read-only. Also reports 'call [reg+disp]' (FF /2) sites for +8/+0xc offsets when --ind given.
"""
import sys, struct

IMG = r"E:\codol_re\client_image_20261027.bin"
BASE = 0x400000

def main():
    args = sys.argv[1:]
    ind = False
    if "--ind" in args:
        ind = True
        args.remove("--ind")
    targets = set()
    for a in args:
        targets.add(int(a, 0))
    with open(IMG, "rb") as f:
        data = f.read()
    n = len(data)
    # E8 rel32 scan
    hits = {t: [] for t in targets}
    i = 0
    while True:
        j = data.find(b"\xe8", i)
        if j < 0 or j + 5 > n:
            break
        rel = struct.unpack_from("<i", data, j + 1)[0]
        tgt = (j + BASE) + 5 + rel
        if tgt in hits:
            hits[tgt].append(j + BASE)
        i = j + 1
    for t in sorted(targets):
        print("call -> 0x%08X : %d 处" % (t, len(hits[t])))
        for v in hits[t]:
            print("   0x%08X" % v)
    if ind:
        # FF /2 with modrm mod=10 (disp32) reg=010 -> 0x90|0x91.. ; and mod=01 disp8 -> 0x50|0x51..
        print("--- call [reg+disp] (FF /2) with disp 0x8 or 0xc ---")
        for k in range(n - 7):
            if data[k] == 0xff and (data[k+1] & 0xF8) == 0x10 and (data[k+1] & 0xC0) == 0x40:
                # mod=01 disp8
                pass
        # disp32 form: modrm = 10 rrr mmm ; 0x90..0x97
        i = 0
        while True:
            j = data.find(b"\xff", i)
            if j < 0 or j + 6 > n:
                break
            m = data[j+1]
            if (m & 0xF8) == 0x90:  # mod=10 reg=010
                disp = struct.unpack_from("<i", data, j+2)[0]
                if disp in (8, 0xc):
                    print("   0x%08X  call [r%d+0x%x]  modrm=%02x" % (j+BASE, m & 7, disp, m))
            i = j + 1

if __name__ == "__main__":
    main()
