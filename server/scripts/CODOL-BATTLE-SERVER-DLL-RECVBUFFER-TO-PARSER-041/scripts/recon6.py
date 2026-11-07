# -*- coding: utf-8 -*-
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

calls = scan_call_rel32()
jumps = scan_jmp_rel32()

def landing(lo, hi):
    out = []
    for i in calls+jumps:
        t = target_of(i)
        if t is not None and IB+lo <= t < IB+hi:
            out.append((i.address-IB, i.mnemonic, t-IB))
    return out

for lo, hi, label in [(0x22D470,0x22D575,"std-thread-launch 0x22D470"),
                      (0x22FD70,0x22FDC0,"0x22FD70"),
                      (0x235CD0,0x235E00,"recv-obj-ctor"),
                      (0x235E00,0x2360B0,"recv-body"),
                      (0x2360B0,0x236110,"checksum"),
                      (0x236110,0x23614C,"tick-helper")]:
    L = landing(lo,hi)
    print("== %s : %d landings" % (label, len(L)))
    for a,m,t in L:
        print("   0x%06X %s -> 0x%06X" % (a,m,t))
