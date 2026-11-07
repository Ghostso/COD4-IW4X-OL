# -*- coding: utf-8 -*-
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
p=os.path.join(ROOT,"03_OUT_STRUCTURE_FIELDS.tsv")
t=io.open(p,encoding="utf-8").read()
t=t.replace("\tcaller 0x231050 reads result into thread block\t", "\tcaller 0x231050 does NOT read +0x00 directly; out ptr passed to 0x235E00, struct then read via ping map\t")
t=t.replace("\tcaller 0x231050 result block\t", "\tcaller 0x231050 does NOT read +0x04 directly; read via ping map accessors 0x22A670/0x22B010\t")
t=t.replace("\tcaller 0x231050 result block\t", "\tcaller 0x231050 does NOT read +0x08 directly; read via ping map accessors\t")
io.open(p,"w",encoding="utf-8",newline="").write(t)
print(t)
