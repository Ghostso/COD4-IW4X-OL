# -*- coding: utf-8 -*-
"""Disassemble the auth_task validator around 0xB9A470/0xB9A59B."""
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
def hx(va, n):
    o = va-BASE
    return " ".join("%02X"%x for x in d[o:o+n])
print("=== 0xB9A580..0xB9A5B0 (around the 0x2DF write) ===")
print(hx(0xB9A580, 48))
print()
print("=== 0xB9A7C0..0xB9A7E0 (around the second 0x2DF write) ===")
print(hx(0xB9A7C0, 32))
print()
# locate the validator: the doc says stage table at 0xB99C0 picks answer;
# 0xB99A40[idx]=5 -> 715.  Look for cmp against task values near B9A5xx
print("=== 0xB9A560..0xB9A5A0 wide ===")
print(hx(0xB9A560, 64))
