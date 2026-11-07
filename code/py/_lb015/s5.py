# -*- coding: utf-8 -*-
import img, mem, struct
d=img._IMG; BASE=0x400000
# 1) pattern mov esi,[0x82e13fc]; add esi,4
pat = bytes.fromhex("8b35fc132e08")
i=0
print("=== mov esi,[0x82e13fc] occurrences ===")
while True:
    i=d.find(pat,i)
    if i<0: break
    va=BASE+i
    nxt=d[i+6:i+10]
    print("%08X next=%s" % (va, nxt.hex()))
    i+=1
