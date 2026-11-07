# `rsa_decrypt_key` 调用点：AES 密钥是 RSA 解出来的

> 承接 `lobby/27`
> 本篇确认 `0xbc8850` 的函数身份和参数
> 证据：`client_runtime.bin` 反汇编

---

## 1. 参数映射

调用点（`0x483aa9`–`0x483adf`）：

```
push [ebp-0x15c]        ← 参数 10（最后压）
push [ebp-0x138]        ← 参数 9
push 1                  ← 参数 8
push esi (sha256 idx)   ← 参数 7
push 0                  ← 参数 6
push 0                  ← 参数 5
push [ebp-0x134]        ← 参数 4
push [ebp-0x2c]         ← 参数 3   ★ 输出密钥
push 0x100              ← 参数 2   outlen
push [ebp-0x130]        ← 参数 1   in
call 0xbc8850
```

按 x86 cdecl，从右往左压。所以：

| 参数号 | 内容 | 对应 `[ebp+N]` |
|---|---|---|
| 1 | `[ebp-0x130]` | `+8` |
| 2 | `0x100` | `+0xc` |
| 3 | **`[ebp-0x2c]`** | **`+0x10`** |
| 4 | `[ebp-0x134]` | `+0x14` |
| 5 | 0 | `+0x18` |
| 6 | 0 | `+0x1c` |
| 7 | `esi`（sha256 索引） | `+0x20` |
| 8 | 1 | `+0x24` |
| 9 | `[ebp-0x138]` | `+0x28` |
| 10 | `[ebp-0x15c]` | `+0x2c` |

---

## 2. 与 `0xbc8850` 的代码对照

```
0xbc8853  mov eax, [ebp+0x28]     ← 参数 9
0xbc8856  mov [eax], 0            ← 清零（这是"明文长度"输出）
0xbc885c  mov eax, [ebp+0x24]     ← 参数 8
0xbc8862  cmp eax, 1              ← 必须是 1 或 2
0xbc8867  cmp eax, 2
0xbc886c  mov eax, 0x18           ← 否则返回 0x18（错误码）
0xbc888a  mov ebx, [ebp+0x2c]     ← 参数 10（RSA 上下文）
0xbc88a5  mov edi, [ebp+0xc]      ← 参数 2（outlen = 256）
0xbc88ab  cmp eax, edi            ← 比较长度
0xbc88bc  call [0xe3cc48]         ← 内存分配
0xbc88e5  call [0xe88610]         ← ★ 核心：RSA 运算
```

**这是 libtomcrypt `rsa_decrypt_key_ex` 的典型结构：**

```
int rsa_decrypt_key_ex(
    const u8 *in,      // +8   密文
    u32 inlen,         // +0xc  输入长度 = 256
    u8 *out,           // +0x10 ★ 明文（AES 密钥材料）
    u32 *outlen,       // +0x14 输出长度（=40，在 0x483ad5 设为 0x28）
    u8 *reserved1,     // +0x18 = 0
    u8 *reserved2,     // +0x1c = 0
    int hash_idx,      // +0x20 sha256
    int padding,       // +0x24 = 1 (PKCS#1 v1.5)
    int *stat,         // +0x28 状态输出
    rsa_key *key       // +0x2c RSA 私钥
);
```

**`padding = 1` = `LTC_PKCS_1_V1_5`。**

---

## 3. ★ 关键数据

| 项 | 值 |
|---|---|
| 密文 | `[ebp-0x130]`，**256 字节** |
| RSA 密钥 | `0xdac4b0` 的 1187 字节 DER（已提取） |
| 输出 | `[ebp-0x2c]`，**40 字节上限**（`[ebp-0x134] = 0x28`） |
| 哈希 | SHA-256 |
| 填充 | PKCS#1 v1.5 |

**RSA-2048 解密 256 字节密文，得到最多 40 字节明文。**

---

## 4. 这 40 字节明文是什么

它是"密钥材料"。

接下来的 `cipher_setup("aes", key=..., keylen=24)` 用其中 24 字节
（`0x483afc` 压 `0x18` = 24）。

**所以：RSA 解出的明文里，前 24 字节就是 AES-192 密钥？**

**但 `0x483b1c` 用的是 `0x10` = 16 字节**（AES-128）。

**长度对不上。**

两种可能：

1. `[ebp-0x134]` 存的是"输入 40 字节"，实际返回的长度在 `[ebp-0x138]`
2. 24 和 16 是两个不同的用途

**需要确认参数映射（参数 3 和 4 的位置）。**

---

## 5. 我可能把参数顺序搞反了

`push` 顺序（从最后压的往上读）：

```
push [ebp-0x15c]   ; 先压 = 最后一个参数
push [ebp-0x138]
push 1
push esi
push 0
push 0
push [ebp-0x134]
push [ebp-0x2c]
push 0x100
push [ebp-0x130]   ; 最后压 = 第一个参数
call
```

**第一个参数是最后压的 —— 是 `[ebp-0x130]`。**

所以：

```
arg1 = [ebp-0x130]   ← 密文输入
arg2 = 0x100         ← 输入长度 256
arg3 = [ebp-0x2c]    ← 输出缓冲
arg4 = [ebp-0x134]   ← ?
arg5 = 0
arg6 = 0
arg7 = esi
arg8 = 1
arg9 = [ebp-0x138]
arg10 = [ebp-0x15c]
```

**按 `rsa_decrypt_key_ex(in, inlen, out, outlen, ..., key)`：**

- `arg1` = in = `[ebp-0x130]` ✓
- `arg2` = inlen = 256 ✓
- `arg3` = out = `[ebp-0x2c]` ✓
- `arg4` = outlen = `[ebp-0x134]`
- `arg10` = key = `[ebp-0x15c]`

**`[ebp-0x134]` 在 `0x483ad5` 被设为 `0x28` = 40。**

**所以 outlen 缓冲区初始值是 40，RSA 解出后写回实际长度。**

---

## 6. `[ebp-0x15c]` 是 RSA 上下文

它是 `rsa_import` 的输出（`0x483a90` 的 `lea eax, [ebp-0x15c]`）。

**这确认了：**
- 私钥导入到 `[ebp-0x15c]`
- RSA 解密用同一个结构

**形成完整闭环。**

---

## 7. 剩下的问题

```
AES 密钥 = f(RSA_decrypt(密文, 私钥))
```

**但 `cipher_setup` 传的 keylen 是 24，而 `memcpy` 的是 16。**

**需要看 `0x483af3`–`0x483b14` 那几行到底传了什么。**

（可能 `cipher_setup` 的签名是 `(idx, key, keylen, ...)`，
而 `[ebp-0x2c]` 传的是"密钥指针"，24 是"可用长度"，
AES-128 只用前 16 字节。）

---

## 8. 未解

1. 密文 `[ebp-0x130]` 的 256 字节从哪来
2. `cipher_setup` 的 24 与 `memcpy` 的 16 的解释
3. RSA 解出的 40 字节内容（需要运行时 dump）
