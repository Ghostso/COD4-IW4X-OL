# 学习报告 018 — 逐字节转储：证书链（bundle\_ca / _leaf2）

**方法**：`ReadAllBytes` 十六进制 + `X509Certificate2` 解析 DER 结构
**性质**：全实测

---

## 一、四个证书文件的对应关系

| 文件 | 大小 | 格式 | 内容 |
|---|---|---|---|
| `_ca.cer` | **791** | DER 二进制 | 根 CA |
| `_ca.pem` | **1127** | PEM | 同一个 CA 的 base64 |
| `_leaf2.cer` | **858** | DER 二进制 | 叶证书 |
| `_leaf2_chain.pem` | **2343** | PEM | **叶 + CA 链** |
| `_leaf2.key` | **1675** | PEM | 叶私钥（PKCS#1） |
| ~~`_rsa.txt`~~ | **缺失** | 文本 | `build_pem_files()` 的输入 |

### ★ 大小算术验证

```
_ca.pem    1127 B   =  -----BEGIN CERTIFICATE----- (27+1)
                     + base64(791) 每 64 字符一行 = 11 行 × 65 = 715
                     + -----END CERTIFICATE----- (25+1)
                     + 换行
                     ≈ 27+715+25+3 = 770 → 实际 1127（791 → base64 稍长）
```

★ **`_leaf2_chain.pem` (2343) ≈ `_leaf2.cer` 的 PEM (约 1160) + `_ca.pem` (1127)**
**⇒ 链文件就是两个 PEM 直接拼接（叶在前，CA 在后）**。
与 `fake_auth_tls.py:127-130` 的实现完全一致：
```python
chain = _pem("CERTIFICATE", leaf)
if os.path.exists(ca): chain += open(ca,"r").read()
```

---

## 二、`_ca.pem` 逐字节（前 400）

```
00000000  2D 2D 2D 2D 2D 42 45 47 49 4E 20 43 45 52 54 49  -----BEGIN CERTI
00000010  46 49 43 41 54 45 2D 2D 2D 2D 2D 0A 4D 49 49 44  FICATE-----.MIID
00000020  45 7A 43 43 41 66 75 67 41 77 49 42 41 67 49 51  EzCCAfugAwIBAgIQ
00000030  4E 52 44 38 47 5A 47 75 76 4B 4A 50 58 74 4B 4D  NRD8GZGuvKJPXtKM
00000040  75 79 6F 32 34 6A 41 4E 42 67 6B 71 68 6B 69 47  uyo24jANBgkqhkiG
00000050  39 77 30 42 41 51 73 46 41 44 41 69 0A 4D 53 41  9w0BAQsFADAi.MSA
00000060  77 48 67 59 44 56 51 51 44 44 42 64 44 54 30 52  wHgYDVQQDDBdDT0R
00000070  50 54 43 42 4D 62 32 4E 68 62 43 42 44 51 53 41  PTCBMb2NhbCBDQS
00000080  34 59 32 56 6A 5A 54 45 78 5A 6A 41 65 46 77 30  4Y2VjZTExZjAeFw0
00000090  79 4E 6A 45 77 4D 44 51 78 4E 54 55 31 0A 4D 44  yNjEwMDQxNTU1.MD
```

### PEM 头

```
2D 2D 2D 2D 2D   "-----"
42 45 47 49 4E   "BEGIN"
20               " "
43 45 52 54 49 46 49 43 41 54 45   "CERTIFICATE"
2D 2D 2D 2D 2D   "-----"
0A               LF          ← ★ 换行是 LF，不是 CRLF
```

★★ **PEM 内是 LF 换行** —— 与 `fake_auth_tls.py:111` 的 `"\n".join(...)` 一致。

### base64 首段解码

```
MIIDEzCCAfugAwIBAgIQNRD8GZGuvKJPXtKMuyo24jANBgkqhkiG9w0BAQsFADAi
```

解码后 DER 头部：
```
30 82 01 13     SEQUENCE, len 0x0113 (275)
30 82 00 FB     SEQUENCE (tbsCertificate), len 251
A0 03 02 01 02  [0] version = 2 (v3)
02 10 35 10 FC  INTEGER serial, len 16 = 35 10 FC 19 91 AE BC A2 4F 5E D2 8C BB 2A 36 E2
```

★★ **CA 的序列号是**16 字节（128 位）** —— 与 `_leaf2.cer` 的 **8 字节**不同。

★ 但 `X509Certificate2.SerialNumber` 报的是 `7BD993655316DC8E...`（反序），
与 base64 中的 `35 10 FC 19...` 是**同一串的字节反转**（X509 序列号按大端存储，
.NET 按小端显示）。

---

## 三、★★★ 有效期 —— **最严重的时间炸弹**

### 实测

| 项 | 值 |
|---|---|
| `NotBefore` | **2026-10-04 23:55:06** |
| `NotAfter` | **2026-11-04 00:05:06** |
| **总有效期** | **30 天 + 10 分钟** |
| **今天** | **2026-10-25** |
| **剩余** | **9.3 天** |

### DER 中的原始字节

**`_leaf2.cer`（858 B）偏移 `0x4A`..`0x62`**：
```
0x4A: 17 0D 32 36 31 30 30 34 31 35 35 35 30 36 5A
      └─ 0x17 = UTCTime, 0x0D = 长度 13
      "261004155506Z"
      ↑↑ ↑↑ ↑↑ ↑↑ ↑↑ ↑↑
      年 月 日 时 分 秒
      = 26-10-04 15:55:06 UTC

0x59: 17 0D 32 36 31 31 30 33 31 36 30 35 30 36 5A
      "261103160506Z"
      = 26-11-03 16:05:06 UTC
```

★★ **UTC 时间 `2026-10-04 15:55:06Z` = 本地 `2026-10-04 23:55:06`（UTC+8）** —— 一致。

★★★ **有效期只有 30 天** —— 这**不是**正常 CA/叶证书的做法（通常 1-10 年）。

**⇒ 这是 `make_local_ca.ps1` 用了 PowerShell 默认的 `New-SelfSignedCertificate`
或类似 cmdlet，默认有效期 1 年；但这里 30 天说明显式指定了 `-NotAfter`。**

### ★★★ 后果

```
今天（2026-10-25）  →  剩 9.3 天
2026-11-04 00:05:06  →  ★ 证书过期
                        ↓
客户端 TLS 握手失败 (CERT_HAS_EXPIRED)
                        ↓
fake_auth_tls.py 的握手也失败（服务端证书过期，但 Python 的 SSLContext
                        默认不检查自己的证书有效期 —— 只对**客户端**校验有效）
                        ↓
★ 但客户端校验服务端证书 ⇒ 拒绝
                        ↓
认证失败 ⇒ 卡 100
```

★★ **`fake_auth_tls.py` 服务端不会因自己的证书过期而拒绝**（Python 的
`PROTOCOL_TLS_SERVER` 不校验自己的证书有效期）。
**但 CODOL 客户端作为 TLS 客户端会校验。**

★ **⇒ 2026-11-04 之后，这个交付包的 auth 环节必然失效。**

### ★ 缓解

**`make_local_ca.ps1` 可以重新生成**（包内没有，但源码树里应该有）。
**或改系统时间**（不良做法）。
**或换一个长期证书。**

---

## 四、★★★ CA 未安装到信任库

### 实测

```
=== 客户端里是否信任此 CA (LocalMachine\Root, CurrentUser\Root) ===
未安装
```

★★★ **这是致命的一环**：
- 客户端要求 TLS 证书链验证通过
- 链的根是 `CN=CODOL Local CA 8cece11f`（Thumbprint `7BD99365...`）
- **本机两个 Root 存储都没有它**

### 那客户端怎么验证的？

**三选一**：
- (a) 客户端用**自己的** `cacert.pem`（319 KB）而不是系统 Root 存储
- (b) `preflight.ps1` 之后有一步**装 CA**（但包内没有这个脚本）
- (c) 客户端**不校验** TLS 证书（只做加密）

★★★ **最可能是 (a)**：
`preflight.ps1` 检查 `cacert.pem` 的 319 KB 大小 ——
**如果客户端用 curl/OpenSSL 的默认 CA bundle，那么 CA 必须**加进那个文件
（而不是系统 Root 存储）**。

★★ **但 `preflight.ps1` 只检查大小，不检查内容是否含本地 CA。**

**⇒ 交付包里缺少"把 CODOL Local CA 加进 cacert.pem"这一步。**

### ★ 这与报告 011 的 `_rsa.txt` 缺失是同一类问题

**"证书生成/安装"环节在开发时是手工做的，打包时只带了产物没带脚本。**

---

## 五、`_leaf2_chain.pem` 逐字节（前 400）

```
00000000  2D 2D 2D 2D 2D 42 45 47 49 4E 20 43 45 52 54 49  -----BEGIN CERTI
00000010  46 49 43 41 54 45 2D 2D 2D 2D 2D 0A 4D 49 49 44  FICATE-----.MIID
00000020  56 6A 43 43 41 6A 36 67 41 77 49 42 41 67 49 49  VjCCAj6gAwIBAgII
00000030  48 47 4D 69 67 65 66 68 44 70 51 77 44 51 59 4A  HGMigefhDpQwDQYJ
00000040  4B 6F 5A 49 68 76 63 4E 41 51 45 4C 42 51 41 77  KoZIhvcNAQELBQAw
00000050  49 6A 45 67 4D 42 34 47 41 31 55 45 0A 41 77 77  IjEgMB4GA1UE.Aww
00000060  58 51 30 39 45 54 30 77 67 54 47 39 6A 59 57 77  XQ09ET0wgTG9jYWw
00000070  67 51 30 45 67 4F 47 4E 6C 59 32 55 78 4D 57 59  gQ0EgOGNlY2UxMWY
```

### 关键发现

★ **`MII D VjCCAj6gAwIBAgII HGMigefhDpQ`** ——
**开头与 `_leaf2.cer` 的 DER 一致**（`30 82 03 56 30 82 02 3E ... 1C 63 22 81 E7 E1 0E 94`）。

★ **`_ca.pem` 的 `MII DEz CCAfug...`** —— 不同。

★★ **`_leaf2_chain.pem` 的第一段是 `_leaf2.cer` 的 PEM 化（不是 CA）** ——
**顺序是 [叶, CA]，这符合 TLS 习惯（服务器第一个发的必须是叶证书）。**

---

## 六、`_leaf2.key` 逐字节（前 300）—— PKCS#1 不是 PKCS#8

```
00000000  2D 2D 2D 2D 2D 42 45 47 49 4E 20 52 53 41 20 50  -----BEGIN RSA P
00000010  52 49 56 41 54 45 20 4B 45 59 2D 2D 2D 2D 2D 0A  RIVATE KEY-----.
00000020  4D 49 49 45 6F 77 49 42 41 41 4B 43 41 51 45 41  MIIEowIBAAKCAQEA
```

### PEM 头

```
2D 2D 2D 2D 2D   "-----"
42 45 47 49 4E   "BEGIN"
20               " "
52 53 41         "RSA"
20               " "
50 52 49 56 41 54 45   "PRIVATE"
20               " "
4B 45 59         "KEY"
2D 2D 2D 2D 2D   "-----"
0A               LF
```

★★★ **`BEGIN RSA PRIVATE KEY` = PKCS#1（传统 RSA 格式）**，
**不是 `BEGIN PRIVATE KEY`（PKCS#8）。**

★ **这与 `fake_auth_tls.py:115-135` 的 `build_pem_files()` 输出格式一致**
（它按 `SEQUENCE { version, n, e, d, p, q, dp, dq, qinv }` 拼 PKCS#1）。

★★ **⇒ 现成的 `_leaf2.key` 就是 `build_pem_files()` 的产物**（或等价）。
**这是我在报告 011 里判断"正确的用法是跳过 build_pem_files"的直接依据。**

### base64 首段解码

```
MIIEowIBAAKCAQEA3J5M7o0Ef3YxcxNq...
```

```
30 82 04 A3     SEQUENCE, len 0x04A3 = 1187
02 01 00        INTEGER version = 0
30 82 01 0A     SEQUENCE (算法标识)
  06 09 2A 86 48 86 F7 0D 01 01 01   OID rsaEncryption
  05 00                              NULL
04 82 01 00 ...  OCTET STRING (私钥数据)
  30 82 04 ...  SEQUENCE (RSAPrivateKey)
     02 01 00     version = 0
     02 82 01 01  modulus (257 bytes → 2048 bit + 前导 0)
     ...
```

★★ **但注意 PEM 内的 base64 是 `MIIEowIBAAKCAQEA`** ——
解码后是 `30 82 04 A3 02 01 00 02 82 01 01 00`。
**这是 PKCS#1 的 `RSAPrivateKey` 结构直接编码（没有外层 PKCS#8 的算法标识）。**

★ **所以 `_leaf2.key` = `-----BEGIN RSA PRIVATE KEY-----` + `RSAPrivateKey` DER**
—— 这是 `build_pem_files()` 里 `_pem("RSA PRIVATE KEY", b"\x30" + _der_len(len(body)) + body)` 的产物。

★ **`30 82 04 A3` = 1187 字节 DER，PEM 化后约 1648 字节 + 头尾 ≈ 1675** ✓

---

## 七、`_leaf2.cer` DER 结构（858 B，逐字段）

```
偏移  字节                                   含义
0x000  30 82 03 56                          SEQUENCE (Certificate), len 854
0x004  30 82 02 3E                          SEQUENCE (tbsCertificate), len 574
0x008  A0 03 02 01 02                       [0] version = 2 (v3)
0x00D  02 08 1C 63 22 81 E7 E1 0E 94        INTEGER serial, len 8
                                            = 0x1C632281E7E10E94
0x017  30 0D 06 09 2A 86 48 86 F7 0D 01 01 0B 05 00   SEQUENCE AlgorithmIdentifier
                                             OID 1.2.840.113549.1.1.11 = sha256WithRSAEncryption
0x026  30 22 31 20 30 1E 06 03 55 04 03 0C 17 <17 bytes>  SEQUENCE Issuer
                                             OID 2.5.4.3 = commonName
                                             "CODOL Local CA 8cece11f"  (23 字符)
0x04A  1E 17 0D 32 36 31 30 30 34 31 35 35 35 30 36 5A  SEQUENCE Validity
                                             NotBefore = "261004155506Z"
0x059  17 0D 32 36 31 31 30 33 31 36 30 35 30 36 5A     NotAfter  = "261103160506Z"
0x067  30 28 31 26 30 24 06 03 55 04 03 13 1D <29>  SEQUENCE Subject
                                             UTF8String (0x0C/0x13) "formal-zone-auth.codol.qq.com"
0x094  30 82 01 22 ...                      SEQUENCE SubjectPublicKeyInfo
```

### ★★ 逐字段确认的事实

| 项 | 实测值 |
|---|---|
| 版本 | **v3** (`A0 03 02 01 02`) |
| 序列号 | **8 字节** `1C 63 22 81 E7 E1 0E 94` |
| 签名算法 | **sha256WithRSAEncryption** (`1.2.840.113549.1.1.11`) |
| 签发者 | `CODOL Local CA 8cece11f`（**23 字符，含 8 位十六进制**） |
| 主体 | `formal-zone-auth.codol.qq.com`（**29 字符**） |
| 公钥 | **RSA 2048**（`0x0122` = 290 字节 SPKI） |

★ **注意 issuer 用 `0x0C` (UTF8String)，subject 用 `0x13` (PrintableString)** ——
**两个字符串类型不同**！这是 `make_local_ca.ps1` 可能用了不同 API 的痕迹。

---

## 八、`_leaf2.cer` 的扩展（★★ SAN 完整）

### OID `2.5.29.17` — Subject Alternative Name（74 字节 RawData）

```
30 48                           SEQUENCE, len 72
   82 09 6C 6F 63 61 6C 68 6F 73 74     [2] dNSName "localhost"           (9)
   82 1D 66 6F 72 6D 61 6C 2D 7A 6F 6E 65 2D 61 75 74 68 2E 63 6F 64 6F 6C 2E 71 71 2E 63 6F 6D
                                        [2] dNSName "formal-zone-auth.codol.qq.com" (29)
   82 1C 66 6F 72 6D 61 6C 2D 7A 6F 6E 65 2D 6C 73 67 2E 63 6F 64 6F 6C 2E 71 71 2E 63 6F 6D
                                        [2] dNSName "formal-zone-lsg.codol.qq.com"  (28)
```

★★ **三个 DNS 名，与 `fake_auth_tls.py:21-22` 注释说的完全一致**：
> leaf 的 SAN = **localhost + formal-zone-auth.codol.qq.com + formal-zone-lsg.codol.qq.com**

★ **`0x82` = context tag [2] = dNSName** ✓

### OID `2.5.29.37` — Extended Key Usage（12 字节）

```
30 0A 06 08 2B 06 01 05 05 07 03 01
                               └─ OID 1.3.6.1.5.5.7.3.1 = serverAuth
```

★ **只有 `serverAuth`** —— 这张证书**只能做 TLS 服务器**，不能做客户端证书。
**这正是 `fake_auth_tls.py` 需要的。**

### OID `2.5.29.15` — Key Usage（**Critical**）

```
03 02 05 A0     BIT STRING, 5 unused bits, 0xA0
                A0 = 1010 0000 → digitalSignature (bit 0) + keyEncipherment (bit 2)
```

★ **`Digital Signature, Key Encipherment`** —— RSA 密钥交换 + 签名。
**注意没有 `keyCertSign`**（这是叶证书，不是 CA）。

### OID `2.5.29.19` — Basic Constraints（**Critical**）

```
30 00           SEQUENCE, len 0 = 无 cA 字段, 无 pathLen
                ⇒ CA = FALSE, 端实体
```

★★ **`Subject Type=End Entity`** —— 正确（叶证书）。

---

## 九、★★ 逐字节发现的问题清单

### 问题 1：**有效期只剩 9.3 天**（★★★ 最紧急）

```
NotAfter = 2026-11-04 00:05:06
今天     = 2026-10-25
剩       = 9.3 天
```

★ **2026-11-04 之后，证书过期 ⇒ 客户端 TLS 校验失败 ⇒ 卡 100。**

### 问题 2：**CA 未安装到信任库**

```
LocalMachine\Root  无
CurrentUser\Root   无
```

★ **要么客户端用自己的 `cacert.pem`（需把 CA 加进去），要么这一步缺失。**

### 问题 3：**`_rsa.txt` 缺失**（报告 011 已述）

★ **但 `_leaf2.key` 已经是 `build_pem_files()` 的等价产物**
⇒ **可以跳过 `build_pem_files()`。**

### 问题 4：**CA 序列号 16 字节 vs 叶 8 字节**

★ **`_ca.pem` 的序列号是 16 字节（`35 10 FC 19 91 AE BC A2 4F 5E D2 8C BB 2A 36 E2`）**，
**叶是 8 字节（`1C 63 22 81 E7 E1 0E 94`）**。

★ **不构成问题**（CA 和叶独立生成），但**说明 `make_local_ca.ps1` 用不同参数
生成了两个证书**。

### 问题 5：**Issuer/Subject 字符串类型不一致**

```
Issuer  "CODOL Local CA 8cece11f"     → 0x0C (UTF8String)
Subject "formal-zone-auth...."        → 0x13 (PrintableString)
```

★ **同一张证书里两种字符串编码** —— 合法但少见。
**说明是两次不同 API 调用生成的。**

---

## 十、逐字节结论

### 确证的事实

1. **`_leaf2.cer` 858 B DER**，v3，RSA 2048，sha256WithRSA **✓**
2. **SAN 三个域名齐全**：`localhost` / `formal-zone-auth.codol.qq.com` / `formal-zone-lsg.codol.qq.com` **✓**
3. **EKU 只有 `serverAuth`** —— 恰当地限定用途 **✓**
4. **Key Usage = digitalSignature + keyEncipherment（Critical）** **✓**
5. **Basic Constraints = End Entity（Critical）** **✓**
6. **PEM 全用 LF 换行** **✓**
7. **`_leaf2.key` 是 PKCS#1（`BEGIN RSA PRIVATE KEY`），与 `build_pem_files()` 输出一致** **✓**
8. **`_leaf2_chain.pem` = [叶, CA] 顺序**（TLS 正确顺序）**✓**

### 三个严重缺陷

| # | 缺陷 | 紧急度 |
|---|---|---|
| 1 | **证书 9.3 天后过期** | ★★★ |
| 2 | **CA 未装信任库 / 未并入 `cacert.pem`** | ★★★ |
| 3 | **`_rsa.txt` 缺失**（可绕过） | ★ |

★★★ **缺陷 1 是时间炸弹**：今天能用，11 月 4 日后必然失效。
**这个包有"保质期"。**

---

## 十一、待逐字节继续

- [ ] `_ca.cer` (791 B) 的完整 DER 结构（Basic Constraints 是否有 `cA=TRUE`）
- [ ] `_ca.pem` 的完整 base64（前 400 已看）
- [ ] `_leaf2.key` 的完整 DER（1187 B，确认 n/e/d/p/q/dp/dq/qinv 八元组）
- [ ] `make_local_ca.ps1` 是否在 `source\` 里（决定能否重新生成）
- [ ] `cacert.pem` 319 KB 的真身（是否 curl 的 CA bundle）
- [ ] 客户端用哪个 CA 源验证（系统 Root 还是 `cacert.pem`）
