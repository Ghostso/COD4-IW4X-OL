#!/usr/bin/env python3
"""模拟 0xb75d40 的"求最高有效位索引"算法，验证各种入参的返回值。

反汇编逻辑（lobby/84-85 已读）：
  ecx = 0
  if n & 0xffff0000: ecx |= 16; n >>= 16
  if n & 0xff00:     ecx |= 8;  n >>= 8
  if n & 0xf0:       ecx |= 4;  n >>= 4
  if n & 0xc:        ecx |= 2;  n >>= 2
  if n & 0x2:        ecx |= 1;  n >>= 1
  return ecx
"""
import sys


def msb_index(n):
    ecx = 0
    if n & 0xFFFF0000:
        ecx |= 16
        n >>= 16
    if n & 0xFF00:
        ecx |= 8
        n >>= 8
    if n & 0xF0:
        ecx |= 4
        n >>= 4
    if n & 0xC:
        ecx |= 2
        n >>= 2
    if n & 0x2:
        ecx |= 1
        n >>= 1
    return ecx


def main():
    print("%-8s %-10s %-10s %-10s" % ("n", "msb_idx", "+1(位宽)", "2^位宽"))
    for n in (1, 2, 3, 15, 16, 21, 31, 32, 63, 127, 255, 256):
        i = msb_index(n)
        print("%-8d %-10d %-10d %-10d" % (n, i, i + 1, 1 << (i + 1)))

    print()
    print("writeBits(n) 走 msb_index(31)+1 =", msb_index(31) + 1, "位")
    print("报文标签 0x10/0x13/0x15 是否 <= 0x1F:",
          all(x <= 0x1F for x in (0x10, 0x13, 0x15)))


if __name__ == "__main__":
    main()
