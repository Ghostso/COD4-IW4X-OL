# ★★★ AES 实现定位：`0x483a50` 与算法表 `0xd5b2e0`

> **这是解开 `.ff` 加密的直接入口**
> 证据：运行时内存镜像 `client_runtime.bin`（230MB），映射 `off = VA - 0x400000`

---

## 1. 定位方法

磁盘 EXE 的 `.tp3` 代码段线性反汇编错位（第 25 卷），
**改用运行时内存镜像 `client_runtime.bin`**。

映射关系实测：

```
dump 文件偏移 = VA − 0x400000
```

验证（两个独立点）：

| 字符串 | VA | dump 偏移 | 读回 |
|---|---|---|---|
| `aes` | `0xDB5ED4` | `0x9B5ED4` | `b'aes'` ✓ |
| `common_gametype_mp` | `0xDB60C8` | `0x9B60C8` | 完整 ✓ |

---

## 2. ★ 算法表 @ `0xd5b2e0`

每条 **0x14 字节**：

```
+0x00  u32  名字指针
+0x04  u32  字段1
+0x08  u32  字段2
+0x0c  u32  字段3
+0x10  u32  字段4
```

### 第 1 条（唯一确定的一条）

```
+0x00  name    = 0xDB5ED4  →  "aes"
+0x04  field1  = 6
+0x08  field2  = 16
+0x0c  field3  = 32
+0x10  field4  = 16
```

**解释**：

| 字段 | 值 | 含义 |
|---|---|---|
| field1 | 6 | 可能是 key schedule 轮数参数 |
| field2 | **16** | **AES-128 密钥长度（字节）** |
| field3 | **32** | **AES-256 密钥长度（字节）** |
| field4 | **16** | **AES 块大小（字节）** |

**这是一个通用的"分组密码描述符"。**

### 后续条目 = AES 常数表

从 `0xd5b2f4` 起的数据：

```
33 28 40 4b 41 6b 7d 5c a3 4b 90 4b 09 40 80 08
...
```

`0x63`（S-box[0]）、`0x7c`（S-box[1]）、`0x77`（S-box[2]）、
`0x7b`（S-box[3]）—— **AES S-box 的标准开头**。

**所以这段是 AES 的 T-table / S-box 数据。**

---

## 3. ★ AES 初始化函数 @ `0x483a50`

```
0x483a50  55              push ebp
0x483a51  8b ec           mov ebp, esp
0x483a53  81 ec 5c 01 00 00  sub esp, 0x15c
0x483a59  a1 40 f2 e3 00  mov eax, [0xe3f240]      ← 栈保护 cookie
0x483a64  68 e0 b2 d5 00  push 0xd5b2e0           ← 算法表
0x483a69  e8 62 46 74 00  call 0xbc80d0
0x483a71  b8 00 01 00 00  mov eax, 0x100          ← 256
0x483a76  8d 8d d0 fe ff ff  lea ecx, [ebp-0x130]
0x483a7c  e8 bf 0e 00 00  call 0x484940           ← 构造对象
0x483a81  68 c0 5e db 00  push 0xdb5ec0           ← "sha256"
0x483a86  e8 55 4d 74 00  call 0xbc87e0           ← 查 hash
0x483a8e  8b f0           mov esi, eax
0x483a90  8d 85 a4 fe ff ff  lea eax, [ebp-0x15c]
0x483a96  50              push eax
0x483a97  68 a7 04 00 00  push 0x4a7              ← 1191
0x483a9c  68 b0 c4 da 00  push 0xdac4b0           ← ★ 一个 1191 字节的 DER 块
0x483aa1  e8 ca 43 74 00  call 0xbc7e70           ← 导入公钥
...
0x483ad5  c7 85 cc fe ff ff 28 00 00 00  mov [ebp-0x134], 0x28   ← 40
0x483adf  e8 6c 4d 74 00  call 0xbc8850           ← 校验
...
0x483af3  68 b8 b2 c2 01  push 0x1c2b2b8           ← 输出缓冲
0x483af8  6a 00           push 0
0x483afa  6a 00           push 0
0x483afc  6a 18           push 0x18                ← 24
0x483afe  8d 4d d4        lea ecx, [ebp-0x2c]
0x483b01  51              push ecx                ← 输入缓冲
0x483b02  8d 55 ec        lea edx, [ebp-0x14]
0x483b05  52              push edx
0x483b06  68 d4 5e db 00  push 0xdb5ed4           ← ★ "aes"
0x483b0b  e8 70 4c 74 00  call 0xbc8780           ← 查 cipher
0x483b14  e8 27 4b 74 00  call 0xbc8640           ← ★ 设置加密
0x483b1c  6a 10           push 0x10                ← 16
0x483b1e  8d 45 ec        lea eax, [ebp-0x14]      ← session key
0x483b21  50              push eax
0x483b22  6a 10           push 0x10                ← 16
0x483b24  68 34 17 c5 01  push 0x1c51734           ← ★ 目标密钥缓冲
0x483b29  e8 d5 8a 7b 00  call 0xc3c603           ← memcpy
```

---

## 4. ★ 这段代码在做什么

```
1. 取算法表 [0xd5b2e0]          ← 得到 "aes" 描述符
2. 构造一个 256 字节对象
3. 查找 "sha256" 哈希
4. 导入一段 1191 字节的 DER 数据 [0xdac4b0]   ← ★ RSA 公钥/私钥
5. 用 RSA 做某种运算，结果 24 字节 [ebp-0x2c]
6. 查找 "aes" cipher
7. 用前面的 24 字节 + "aes" 设置一个 16 字节密钥 [ebp-0x14]
8. memcpy 到全局 0x1c51734
```

**结论：**

> **AES 的 16 字节会话密钥，由一段 RSA 运算派生，存到全局 `0x1c51734`。**

---

## 5. 那段 1191 字节的 DER

起始 `0xdac4b0`：

```
30 82 04 a3 02 01 00 02 82 01 01 00 bd 7e d6 e2 ...
```

ASN.1 解析：

| 字节 | 含义 |
|---|---|
| `30 82 04 a3` | SEQUENCE，长度 0x04A3 = **1187** |
| `02 01 00` | INTEGER，长度 1，值 0 |
| `02 82 01 01` | INTEGER，长度 257 |
| `00 bd 7e d6 e2 ...` | **RSA 模数（2048 位带前导 0）** |

**这是一把 2048 位 RSA 密钥。**

---

## 6. 这是 RSA + AES 混合加密

```
RSA 2048 密钥（内嵌在 EXE 里）
    ↓ 用来包裹
AES-128 的 16 字节会话密钥
    ↓ 存到
全局 0x1c51734
    ↓ 用于
解密 .ff 载荷
```

**典型的"信封加密"（envelope encryption）。**

---

## 7. 但这里有个问题

`0x483a50` 里第 7 步用 `call 0xbc8640` 设置加密，
输入是 `[ebp-0x2c]`（24 字节）。

**如果这个 AES 密钥是"加密"用的，那解密用的是哪把？**

两种可能：

1. **对称**：同一把密钥加解密 → 我们拿到 `0x1c51734` 就能解 `.ff`
2. **非对称**：RSA 公钥加密、私钥解密 → 私钥在服务端，客户端解不了

**看第 4 步导入的是"公钥还是私钥"：**

DER 结构 `30 82 04 A3 02 01 00 02 82 01 01 ...` ——
第二个 INTEGER 是 257 字节（2048 位 + 1 前导 0），这是 **RSA 模数**。

**后面还有没有 privateExponent？**

长度 1187 字节，一个 2048 位 RSA 公钥大概 270 字节。
**1187 字节远大于公钥** ⇒ **很可能是私钥（包含 d、p、q）**。

---

## 8. 如果内嵌的是私钥

**那就意味着：客户端自己就能解密 `.ff`。**

**钥匙就在 `0xdac4b0`（1187 字节 DER）里，或运行时在 `0x1c51734`（16 字节）。**

---

## 9. 下一步

1. 在 dump 里读 `0x1c51734` 的 16 字节（运行时的实际密钥）
2. 验证 `0xdac4b0` 的 DER 是公钥还是私钥
3. 用它解 `ui_mp.ff`

---

## 10. 未解

1. `0x1c51734` 在 dump 里是 0（可能是未初始化或已被清零）
2. `0xdac4b0` 的完整 ASN.1 结构
3. 24 字节中间值（`[ebp-0x2c]`）的构造
