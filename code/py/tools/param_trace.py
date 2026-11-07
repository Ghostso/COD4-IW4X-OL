#!/usr/bin/env python3
"""精确重算 0x483af3..0x483b14 的压栈归属。

关键：0xbc8780 = find_cipher(name) 只吃 1 个参数。
0x483b06 push "aes" -> 给 find_cipher
0x483b10 add esp,4  -> 清掉 "aes"
0x483b13 push eax   -> 给 cipher_setup 的第 1 参数
"""
PUSHES = [
    (0x483af3, "push 0x1c2b2b8", "cipher_setup"),
    (0x483af8, "push 0", "cipher_setup"),
    (0x483afa, "push 0", "cipher_setup"),
    (0x483afc, "push 0x18 (=24)", "cipher_setup"),
    (0x483b01, "push [ebp-0x2c]", "cipher_setup"),
    (0x483b05, "push [ebp-0x14]", "cipher_setup"),
    (0x483b06, "push 0xdb5ed4 (\"aes\")", "find_cipher"),
    (0x483b13, "push eax (cipher idx)", "cipher_setup"),
]

print("=== 栈顺序（先压的在最下面）===")
for a, s, who in PUSHES:
    print("  %#x  %-24s -> %s" % (a, s, who))

print("""
=== cipher_setup 看到的参数 ===
arg1 [ebp+8]  = eax            (cipher idx)
arg2 [ebp+c]  = [ebp-0x14]
arg3 [ebp+10] = [ebp-0x2c]
arg4 [ebp+14] = 0x18  (24)
arg5 [ebp+18] = 0
arg6 [ebp+1c] = 0
arg7 [ebp+20] = 0x1c2b2b8
""")

print("""=== cipher_setup 里各参数的实际用途 ===
[ebp+8]  -> ebx, 传给 cipher_is_valid       = cipher index        ✔ arg1
[ebp+c]  -> 0xbc86e8 mov ecx,[ebp+c] ; 0xbc86f0 mov bl,[eax+ecx]
            逐字节拷贝 -> 这是 **key 源**                          = key   ✔ arg2
[ebp+10] -> 0xbc86bc push eax                              ; 传给 setup 的 args
[ebp+14] -> 0xbc86a7 push edx
[ebp+18] -> 0xbc86a4 push ecx
[ebp+1c] -> 0xbc8659 mov edx,[ebp+1c] ; and 0x1000 ; test 0x2000
[ebp+20] -> 0xbc8672 mov esi,[ebp+20]  = ctx 输出结构
""")

print("""=== 0xbc86b0..0xbc86bd 的 setup 调用 ===
lea eax,[esi+0x114]
push eax                 ; arg4 = &ctx->key_sched
mov eax,[ebp+0x10]
push ecx                 ; arg3 = [ebp+0x18]
push edx                 ; arg2 = [ebp+0x14]
push eax                 ; arg1 = [ebp+0x10]
call setup
""")
print("""=> setup(ctx_key_ptr=&ctx+0x114, a=[ebp+0x10], b=[ebp+0x14], c=[ebp+0x18])
   而 0xbc8d70 的签名: setup(key=arg1, keylen=arg2, ?=arg3, sched=arg4)
   0xbc8d77 cmp esi,0x10  where esi=[ebp+0xc]  => keylen 是第 2 个参数

   所以: key = [ebp+0x10] = [ebp-0x2c]  (RSA 材料)
         keylen = [ebp+0x14] = 0x18     (24)          ✔✔ 一致!
""")
