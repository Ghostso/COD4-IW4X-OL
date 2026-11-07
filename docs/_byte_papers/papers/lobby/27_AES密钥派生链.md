# `0x483a50` 全链逆向：AES 密钥从哪来

> 承接 `lobby/26`（拿到 RSA 私钥）
> 本篇把 `0x483a50` 及其被调函数全部读通
> 证据：`client_runtime.bin`，`off = VA − 0x400000`

---

## 1. 调用链全貌

```
0x483b40  (初始化入口)
   ├─ 0xc42de0(0x1c4b700, 0, 0x6044)          memset/zlib 结构清零
   ├─ rep movsd [0x1c4f6fc] ← [ebx], 13 dword  ← ★ 传入 52 字节
   ├─ 0xc3c740(0x1c4b704, ecx, 0x1f)          memset/zlib 结构
   ├─ 0xbc85c0(0xd5b200)                      ← 算法表②
   ├─ 0x483a50()                              ← ★ 派生 AES 密钥
   └─ 0x791eb0(esi)                           ← zlib inflateInit2  ← 不是 .ff 加载！
```

**关键修正**：`0x791eb0` 经反汇编确认是 **zlib `inflateInit2`**
（`z_stream` 的 `alloc`/`free`/`opaque` 三件套，`windowBits=0x8000`）。

**所以 `0x483b40` 是"zlib + AES"组合的初始化，不是 `.ff` 加载。**

---

## 2. `0x483a50` 逐段

### 段 1：取算法表

```
0x483a64  push 0xd5b2e0         ← 表①（前面已解：6/16/32/16）
0x483a69  call 0xbc80d0         ← 设置静态 AES 参数
```

### 段 2：SHA-256 上下文

```
0x483a71  mov eax, 0x100        ← 256
0x483a76  lea ecx, [ebp-0x130]
0x483a7c  call 0x484940         ← 实为 I/O 缓冲操作（非构造器）
0x483a81  push 0xdb5ec0         ← "sha256"
0x483a86  call 0xbc87e0         ← find_hash
0x483a8e  mov esi, eax
```

### 段 3：导入密钥材料

```
0x483a97  push 0x4a7            ← 1191
0x483a9c  push 0xdac4b0         ← RSA 私钥 DER
0x483aa1  call 0xbc7e70         ← rsa_import（已确认结构）
```

### 段 4：RSA 运算

```
0x483ad5  mov [ebp-0x134], 0x28     ← 40
0x483adf  call 0xbc8850             ← rsa_verify / rsa_exptmod
```

### 段 5：查找 AES

```
0x483b06  push 0xdb5ed4         ← "aes"
0x483b0b  call 0xbc8780         ← find_cipher（已确认）
0x483b14  call 0xbc8640         ← cipher_setup（已确认）
```

`cipher_setup` 内部（`0xbc8640`）：

```
0xbc867b  mov [esi+0x10], ecx       ← 密钥长度
0xbc86bd  call [edi+0xe87868]       ← 密钥调度
0xbc86f0  mov bl, [eax+ecx]         ← ★ 逐字节拷贝密钥
0xbc86f3  mov [esi+eax+0x14], bl    ← 到 [ctx+0x14]
```

**入参 `[ebp+0xc]` 就是密钥字节流。**

### 段 6：拷贝到全局

```
0x483b1c  push 0x10             ← 16 字节
0x483b1e  lea eax, [ebp-0x14]   ← ★ 源（密钥）
0x483b22  push 0x10             ← 16
0x483b24  push 0x1c51734        ← ★ 目标全局
0x483b29  call 0xc3c603         ← memcpy
```

---

## 3. ★ 关键结论：16 字节密钥来自 `[ebp-0x14]`

`[ebp-0x14]` 在 `0x483b02` 作为 `lea edx, [ebp-0x14]` 压栈，
作为 `cipher_setup` 的**输出缓冲**参数。

`cipher_setup(..., 0xdb5ed4 /*aes*/, buf_out=[ebp-0x14], ..., key=[ebp-0x2c], 24, 0, 0, target)`。

**所以：**

```
[ebp-0x2c] (24 字节)  = 密钥材料
[ebp-0x14] (16 字节)  = 派生出的 AES-128 密钥
```

---

## 4. `[ebp-0x2c]` 的 24 字节从哪来

回看 `0x483a90` 到 `0x483ad5` 之间的栈参数：

```
0x483a90  lea eax, [ebp-0x15c]      ← 输出结构（rsa_import 的结果）
0x483a96  push eax
0x483a97  push 0x4a7
0x483a9c  push 0xdac4b0
0x483aa1  call 0xbc7e70             ← rsa_import
0x483aa9  lea ecx, [ebp-0x15c]
0x483aaf  push ecx                  ← 参数 1：rsa 上下文
0x483ab0  lea edx, [ebp-0x138]
0x483ab6  push edx                  ← 参数 2：[ebp-0x138]
0x483ab7  push 1                    ← 参数 3：1
0x483ab9  push esi                  ← 参数 4：sha256 索引
0x483aba  push 0                    ← 参数 5：0
0x483abc  push 0                    ← 参数 6：0
0x483abe  lea eax, [ebp-0x134]
0x483ac4  push eax                  ← 参数 7：[ebp-0x134]（长度 = 40）
0x483ac5  lea ecx, [ebp-0x2c]
0x483ac8  push ecx                  ← ★ 参数 8：[ebp-0x2c]（输出）
0x483ac9  lea edx, [ebp-0x130]
0x483acf  push 0x100                ← 参数 9：256
0x483ad4  push edx                  ← 参数 10：[ebp-0x130]
0x483adf  call 0xbc8850
```

**这是 libtomcrypt 的 `rsa_decrypt_key()`**（或 `rsa_encrypt_key`）：

| 参数 | 值 |
|---|---|
| 1 | RSA 私钥上下文 |
| 2 | `[ebp-0x138]`（哈希输出） |
| 3 | 1（某种标志） |
| 4 | sha256 索引 |
| 5, 6 | 0, 0 |
| 7 | `[ebp-0x134]`（长度 40） |
| **8** | **`[ebp-0x2c]`（★ 输出密钥，24 字节）** |
| 9 | 256 |
| 10 | `[ebp-0x130]`（输入） |

**`[ebp-0x130]` 就是 `0x483a76` 那里被准备到的缓冲区（256 字节）**，
它的内容来自…… **`0x484940`**。

---

## 5. `0x484940` 的角色

这正是"段 2"里那个调用，我之前误判为"构造器"。

反汇编显示它是 **I/O/流写入**：
它操作 `[0x1cd17b8]`（可用空间）、`[0x1cd17b4]`（指针），
调用 `0xc427f0`（memcpy）并推进。

**它是一个 `Buffer` 的 `write()`。**

**所以 `[ebp-0x130]` 是一个 256 字节缓冲，内容来自运行时。**

---

## 6. 这条链的完整图景

```
运行时数据 (256B)  ──→  [ebp-0x130]
                          ↓ rsa_decrypt_key(privkey, ..., input=0x130)
                       [ebp-0x2c]  24B  ← 密钥材料
                          ↓ cipher_setup("aes", key=0x2c)
                       [ebp-0x14]  16B  ← AES-128 密钥
                          ↓ memcpy
                       0x1c51734   16B  ← 全局生效
```

---

## 7. 这意味着什么

**AES 密钥 = RSA 私钥解出的数据。**

- RSA 私钥在二进制里（已提取）
- **但密文是"运行时数据"**（256 字节）

**如果那 256 字节来自磁盘（`.ff` 头部的一部分），我们就可以离线算。**

**如果来自服务端下发，就必须抓会话。**

---

## 8. 下一步

1. 确认 `[ebp-0x130]` 的 256 字节来源
2. 找 `0xbc8850` 的正式签名（确认是 `rsa_decrypt_key`）
3. 找出 `0x483b40` 的调用者，看它处理哪个文件

---

## 9. 未解

- 256 字节输入的确切来源
- RSA 解密后的 24 字节如何变成 16 字节 AES 密钥
- `.ff` 的实际加密模式（CBC/CTR）
