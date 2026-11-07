# -*- coding: utf-8 -*-
"""验证：定时器条目 [entry+0x08] 是否就是传给回调作为"源数组"的指针。
   找 0x7FA9B0 之前的参数装配，看第五个 push 用的是哪个偏移。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== 0x7FA9A0 .. 0x7FA9B5 : 回调调用前的参数装配（逐字节）===")
for l in pe.dis(0x7FA998, 16):
    print(l)
print()
print("=== 该函数的栈局部 -0x50..-0x18 分别是哪些字段？（0x7FA640 填充时的映射）===")
print("  0x7FA8A5  lea eax,[ebp-0x50]   ; 条目结构基址 <- 局部")
print("  0x7FA6x   mov [esi+8],...      ; 入队时刻")
print("  0x7FA6A6  mov [esi+0xC],...    ; 超时时刻")
print("  ==> 所以 [ebp-0x50+8] = [ebp-0x48]，[ebp-0x50+0xC] = [ebp-0x44]")
print()
print("=== 但回调调用点用的是 [ebp-0x20]，不是 [ebp-0x50]！重新看 ===")
for l in pe.dis(0x7FA8B0, 30):
    print(l)
