# `rsa_decrypt_key` 确认 · 探讨：参数顺序差一位就全错

> 对应：`lobby/28_rsa_decrypt_key确认.md`

---

## 一、一度以为找到了矛盾

AES 密钥只需要 16 字节（`memcpy` 传 `0x10`）。

但 `cipher_setup` 传的密钥长度是 24（`push 0x18`）。

**16 ≠ 24。**

我第一反应是"这条链有问题"。

---

## 二、回头看压栈顺序

x86 cdecl 从右往左压，所以**最后压的是第一个参数**。

代码：

```
push [ebp-0x15c]      ; 第 1 个压 → 第 10 个参数
push [ebp-0x138]      ; 第 2 个压 → 第 9 个参数
push 1                ;           → 第 8
push esi              ;           → 第 7
push 0                ;           → 第 6
push 0                ;           → 第 5
push [ebp-0x134]      ;           → 第 4
push [ebp-0x2c]       ;           → 第 3
push 0x100            ;           → 第 2
push [ebp-0x130]      ; 最后压    → 第 1
call 0xbc8850
```

`[ebp+8]` 是第一个参数 = `[ebp-0x130]`（密文）。
`[ebp+0x10]` 是第三个参数 = `[ebp-0x2c]`（输出）。
`[ebp+0x24]` 是第八个参数 = `1`（padding）。
`[ebp+0x2c]` 是第十个 = `[ebp-0x15c]`（RSA 私钥）。

**代码里 `0xbc88a5` 的 `mov edi, [ebp+0xc]` = 第二个参数 = 256。**

**和 `0xbc88ab` 的 `cmp eax, edi` 对照 —— 是在比较"输出长度"和"输入长度"。**

**这就对了：`rsa_decrypt_key_ex` 会检查 `*outlen >= inlen`。**

---

## 三、16 vs 24 的解释

`cipher_setup` 的签名（从 `0xbc8640` 反汇编）：

```
0xbc8640  push ebp / mov ebp,esp
0xbc8645  mov ebx, [ebp+8]     ← cipher index
0xbc8648  call 0xbca340        ← 校验 index
0xbc8659  mov edx, [ebp+0x1c]  ← flags
0xbc8672  mov esi, [ebp+0x20]  ← ctx（输出）
0xbc867b  mov [esi+0x10], ecx  ← keylen
0xbc86bd  call [edi+0xe87868]  ← set_key
```

**从调用点看：**

```
0x483af3  push 0x1c2b2b8       ← 参数 8 = 输出结构
0x483af8  push 0               ← 参数 7
0x483afc  push 0               ← 参数 6
0x483afc  push 0x18            ← 参数 5 = 24?
0x483afe  lea ecx,[ebp-0x2c]
0x483b01  push ecx             ← 参数 4 = key
0x483b02  lea edx,[ebp-0x14]
0x483b05  push edx             ← 参数 3 = 输出 ctx
0x483b06  push 0xdb5ed4        ← 参数 2 = "aes"
0x483b10  add esp,4
0x483b13  push eax             ← 参数 1 = cipher index
0x483b14  call 0xbc8640
```

**所以第 5 个参数是 24。**

`cipher_setup(idx, name, ctx_out, key, keylen=24, flags=0, params=0, out=...)`？

**但 `0xbc8640` 的 `[ebp+0x10]` 是第 3 个参数，`[ebp+0x14]` 是第 4 个……**

**参数映射不吻合。**

---

## 四、这就是问题所在

`0x483af3` 到 `0x483b14` 这段代码**压了 7 个值，中间还夹了一次 `add esp,4`。**

```
push 0x1c2b2b8
push 0
push 0
push 0x18
lea ecx,[ebp-0x2c]
push ecx
lea edx,[ebp-0x14]
push edx
push 0xdb5ed4
call 0xbc8780      ← 这是 find_cipher，返回 eax
add esp,4          ← 清掉 "aes" 的 push
push eax           ← 把返回的 index 压栈
call 0xbc8640      ← cipher_setup
```

**重新对齐：**

`0xbc8780` = `find_cipher(name)`，只有一个参数（`"aes"`）。

**所以 `0x483b06` 的 `push 0xdb5ed4` 是给 `find_cipher` 的。**

**它前面那三个 push（`0x18`、`0`、`0`）和 `lea ecx,[ebp-0x2c]` 是给后面的 `cipher_setup` 的。**

**`cipher_setup` 的参数：**

```
arg1 = eax (cipher index)
arg2 = [ebp-0x2c]  (key)
arg3 = 0x18        (24 ?)
arg4 = 0
arg5 = 0
arg6 = 0x1c2b2b8
```

**仍然对不上 `0xbc8640` 的 `[ebp+8]/[ebp+0xc]/...`。**

**可能 `0xbc8640` 不是 `cipher_setup`，我的判断有误。**

---

## 五、方法论收获

> **参数映射错误，会让整条链路"看起来矛盾"。**

我第一次推导出"16 vs 24 矛盾"，是因为我把 `find_cipher` 的返回值
漏算了。

**一旦把 `call 0xbc8780` 和 `add esp,4` 纳入考虑，压栈结构就变了。**

**教训：看到一串 `push` 时，必须确认每一个 `push` 属于哪个 `call`。**

**夹在中间的 `call` + `add esp,N` 会打断参数序列。**

---

## 六、诚实的状态

`0xbc8640` 的身份（`cipher_setup`）**尚未完全确认**。

**它更像一个"初始化 ctx + 拷贝密钥"的函数，但参数含义待定。**

**下一步应该反汇编 `0xbca340`（它调用的第一个函数），
并从那里反推参数。**
