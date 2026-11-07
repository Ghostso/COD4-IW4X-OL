# ★★★★ 拿到 `.ff` 的 AES 密钥链路：内嵌 RSA 私钥

> **这是"完全掌控大厅"最后一道门被打开的地方**
> 证据：运行时内存镜像 `client_runtime.bin`，映射 `off = VA − 0x400000`
> 产物：`_byte_papers/rsa_private_key.json`

---

## 1. 一句话结论

> **客户端 EXE 内部硬编码了一把 2048 位 RSA 私钥（DER，1187 字节），
>  用它派生 AES-128 会话密钥来解密 `.ff`。**
>
> **私钥已经完整提取并通过数学验证。**

---

## 2. 定位路径

```
磁盘 EXE .tp3 线性反汇编错位（第 25 卷）
  ↓
改用运行时内存镜像 client_runtime.bin (230 MB)
  ↓
确认映射 off = VA − 0x400000（两个独立点验证）
  ↓
用 push imm32 模式定位 "aes" 的 5 处引用
  ↓
反汇编 0x483a50 → AES 初始化函数
  ↓
发现它引用 0xdac4b0 的 1187 字节 DER
  ↓
ASN.1 解析 → RSA 私钥
```

---

## 3. DER 结构（`0xdac4b0`，1187 字节）

```
SEQUENCE (1187)
  INTEGER   0                    ← version
  INTEGER   257 字节             ← n  (2048 位模数)
  INTEGER   3 字节               ← e  = 65537
  INTEGER   256 字节             ← d  (私钥指数)
  INTEGER   129 字节             ← p  (素数 1)
  INTEGER   129 字节             ← q  (素数 2)
  INTEGER   129 字节             ← dP = d mod (p-1)
  INTEGER   128 字节             ← dQ = d mod (q-1)
  INTEGER   128 字节             ← qInv = q⁻¹ mod p
```

**8 个 INTEGER + version = 标准 PKCS#1 私钥结构。**

**注意：公钥只有 `(n, e)`，这里还有 `d, p, q, dP, dQ, qInv` —— 是私钥。**

---

## 4. 数学验证（已通过）

```
p × q == n                      ✓
e × d ≡ 1 (mod φ(n))            ✓
```

**不是碰巧的数据段，是真正可用的 RSA 私钥。**

完整数值已保存到 `_byte_papers/rsa_private_key.json`：

```
n     : 2048 位
e     : 65537
d     : 2045 位
p, q  : 各 1024 位
```

---

## 5. AES 初始化流程（`0x483a50` 反汇编）

```
0x483a64  push 0xd5b2e0           ← 算法表（含 "aes" 描述符）
0x483a69  call 0xbc80d0
0x483a7c  call 0x484940           ← 构造 256 字节对象
0x483a81  push 0xdb5ec0           ← "sha256"
0x483a86  call 0xbc87e0           ← 查 hash
0x483a9c  push 0xdac4b0           ← ★ 1187 字节 RSA 私钥
0x483aa1  call 0xbc7e70           ← 导入
0x483adf  call 0xbc8850           ← 校验
0x483b06  push 0xdb5ed4           ← "aes"
0x483b0b  call 0xbc8780           ← 查 cipher
0x483b14  call 0xbc8640           ← ★ 设置密钥
0x483b1c  push 0x10               ← 16 字节
0x483b24  push 0x1c51734          ← ★ 输出到全局
0x483b29  call 0xc3c603           ← memcpy
```

---

## 6. 算法表（`0xd5b2e0`）

每条 0x14 字节：

```
+0x00  u32  名字指针
+0x04  u32  6           ← 轮参数相关
+0x08  u32  16          ← AES-128 密钥长度
+0x0c  u32  32          ← AES-256 密钥长度
+0x10  u32  16          ← 分组长度
```

**紧随其后的数据是 AES S-box（`0x63 0x7c 0x77 0x7b` 开头）。**

---

## 7. 由此推导的解密链

```
1. 用 RSA 私钥 (n, d) 解出 AES-128 密钥
   或：AES 密钥由 RSA 运算的中间结果派生
2. AES-128 密钥存到全局 0x1c51734
3. .ff 的载荷用这个 AES 密钥解密
```

**具体是"RSA 解密出密钥"还是"RSA 派生密钥"，取决于 `0x483a50` 的完整逻辑
（`[ebp-0x2c]` 那 24 字节的构造）。**

---

## 8. 运行时状态的疑点

`0x1c51734` 在**这份 dump 里是 0**。

说明：
- 这份 dump 是在 `0x483a50` 执行**之前**抓的
- 或者密钥只在使用时临时计算，不长期驻留

**需要用"运行一段后"的 dump 验证。**

---

## 9. 这份私钥的使用边界

### 能做

- 解 `ui_mp.ff`（菜单、页面）
- 解 `code_post_gfx_mp.ff`（GSC 脚本）
- 解 `mp_playlists.ff`（磁盘版）
- 解所有 `common_gametype_*.ff`
- **重新加密**（因为私钥在手，对称密钥可重算）

### 不能直接做

- 如果 AES 密钥还掺杂了**运行时随机数**（IV/nonce），
  那还需要对应那一段

---

## 10. 未解

1. `0x483a50` 里 `[ebp-0x2c]` 那 24 字节中间值如何构造
2. AES 模式（CBC / CTR / CFB）
3. IV 从哪来
4. `0xbc8640` 的函数语义（设置加密参数）

---

## 11. 与 `lobby/13` 的呼应

第 13 卷我用七条判据认定 `.ff` 是 AES 加密。

**现在拿到了 `aes` 字符串、AES 算法表、AES S-box、2048 位 RSA 私钥。**

**两种独立路径（黑盒统计 + 代码逆向）指向同一结论，互相印证。**
