# 学习报告 051（重开）— `bundle\` 五个证书文件逐字节

**学习范围**：`_ca.cer` / `_ca.pem` / `_leaf2.cer` / `_leaf2_chain.pem` / `_leaf2.key`
**方法**：`X509Certificate2` 解析 DER + PEM 结构检查
**性质**：全实测
**★★★ 本报告收录**两张证书的完整 X.509 字段**与**30 天有效期的临界问题**

---

## 一、★★★★ 五个证书文件的完整清单

| 文件 | 字节 | 格式 | 内容 |
|---|---|---|---|
| **`_ca.cer`** | **791** | **DER 二进制** | 根 CA |
| **`_ca.pem`** | **1,127** | PEM | 同一 CA 的 base64 |
| **`_leaf2.cer`** | **858** | **DER 二进制** | 叶证书 |
| **`_leaf2_chain.pem`** | **2,343** | PEM | **叶 + CA 链** |
| **`_leaf2.key`** | **1,675** | PEM | 叶私钥（**PKCS#1**） |
| ~~`_rsa.txt`~~ | **缺失** | 文本 | `build_pem_files()` 的输入 |

★★★ **⇒ 实为**5 个文件**（3 PEM + 2 DER），描述**2 张证书**。**

---

## 二、★★★★★ 根 CA 的完整字段（`_ca.cer`，791 B DER）

```
Subject    : CN=CODOL Local CA 8cece11f
Issuer     : CN=CODOL Local CA 8cece11f        ← ★ 自签
NotBefore  : 2026-10-04 23:55:06
NotAfter   : 2026-11-04 00:05:06
总有效期   : 30.01 天
Serial     : 3510FC1991AEBCA24F5ED28CBB2A36E2  ← ★ 16 字节（128 位）
Thumbprint : 7BD993655316DC8E1C4F2A997556EC4CBAC94D40
公钥       : RSA 2048 bit
签名算法   : sha256RSA
```

### ★★★ 三个扩展

| 扩展 | Critical | 长度 |
|---|---|---|
| **密钥用法** | **True** | 4 |
| **基本约束** | **True** | 8 |
| 使用者密钥标识符 | False | 22 |

★★★ **⇒ CA 的 `基本约束` 长度是 **8 字节**（叶只有 2 字节）——**
**⇒ 因为 CA 有 `cA=TRUE` + `pathLenConstraint`。**

★ **⇒ 而 `Subject == Issuer` ⇒ **自签根证书**。**

---

## 三、★★★★★ 叶证书的完整字段（`_leaf2.cer`，858 B DER）

```
Subject    : CN=formal-zone-auth.codol.qq.com
Issuer     : CN=CODOL Local CA 8cece11f          ← ★ 由 CA 签发
NotBefore  : 2026-10-04 23:55:06
NotAfter   : 2026-11-04 00:05:06
总有效期   : 30.01 天
Serial     : 1C632281E7E10E94                    ← ★ 8 字节（64 位）
Thumbprint : 448AA269C7D05756D3C03E06928DB49B269F28F8
公钥       : RSA 2048 bit
签名算法   : sha256RSA
```

### ★★★★★ 四个扩展

| 扩展 | Critical | 长度 |
|---|---|---|
| **使用者可选名称（SAN）** | False | **74** |
| **增强型密钥用法（EKU）** | False | **12** |
| **密钥用法** | **True** | 4 |
| **基本约束** | **True** | **2** |

### ★★★★★ SAN 的三个 DNS 名（逐字）

```
DNS Name=localhost
DNS Name=formal-zone-auth.codol.qq.com
DNS Name=formal-zone-lsg.codol.qq.com
```

★★★ **⇒ 与 `fake_auth_tls.py:21-22` 的注释**完全一致**：**
> leaf 的 SAN = **localhost** + **formal-zone-auth.codol.qq.com** +
> **formal-zone-lsg.codol.qq.com**

★ **⇒ 且与 `preflight.ps1` 的 hosts 五条**完全对应**（auth/lsg 两个域名）。**

★★ **⇒ `localhost` 也在 SAN 里 —— 用于 `127.0.0.1` 的连接。**

---

## 四、★★★★★ **有效期只有 30 天** —— 最关键的问题

### 4.1 两张证书的有效期完全相同

| 证书 | NotBefore | NotAfter | 总天数 |
|---|---|---|---|
| **CA** | **2026-10-04 23:55:06** | **2026-11-04 00:05:06** | **30.01** |
| **Leaf** | **2026-10-04 23:55:06** | **2026-11-04 00:05:06** | **30.01** |

★★★ **⇒ 两张证书的起止时间**完全相同**（同一时刻生成）。**

### 4.2 ★★★★★ 距离过期的剩余时间

```
今天（2026-10-25）
NotAfter = 2026-11-04 00:05:06
        ↓
剩余 ≈ **9.3 天**
```

★★★ **⇒ 这是一个**时间炸弹**：**
```
2026-11-04 00:05:06 之后
        ↓
证书过期
        ↓
客户端 TLS 校验失败（CERT_HAS_EXPIRED）
        ↓
★★★ 认证无法完成 ⇒ 卡 100
```

★★ **⇒ 而 `fake_auth_tls.py` **服务端不会因自己的证书过期而拒绝**（Python 的
`PROTOCOL_TLS_SERVER` 不校验自己的证书有效期）。**
**⇒ 但 CODOL 客户端作为 TLS **客户端**会校验。**

### 4.3 ★★★ 30 天有效期的异常性

★★ **⇒ 正常的本地 CA/叶证书通常是 1-10 年。**

★★★ **⇒ 30 天说明 `make_local_ca.ps1` **显式指定了 `-NotAfter`**（或用了一个 30 天的模板）。**

★ **⇒ 而 `make_local_ca.ps1` **不在交付包里**（报告 001 已确认）。**

---

## 五、★★★★★ `_leaf2.key` 是 **PKCS#1**（不是 PKCS#8）

### 5.1 PEM 头（逐字）

```
-----BEGIN RSA PRIVATE KEY-----
```

★★★ **⇒ `BEGIN RSA PRIVATE KEY` = **PKCS#1**（传统 RSA 格式）。**
**⇒ 不是 `BEGIN PRIVATE KEY`（PKCS#8）。**

★ **⇒ 这与 `fake_auth_tls.py:125` 的 `_pem("RSA PRIVATE KEY", ...)` **完全一致**。**

### 5.2 ★★★ 结构（前 40 字符）

```
MIIEowIBAAKCAQEA3J5M7o0Ef3YxcxNq4SGeV3xa
        ↓ 解 base64 前几字节
30 82 04 A3 02 01 00 02 82 01 01 00
        ↓
SEQUENCE (len 0x04A3 = 1187)
  INTEGER version = 0
  INTEGER modulus (257 字节 → 2048 bit + 前导 0)
```

★★ **⇒ `MIIEow` 开头是 PKCS#1 `RSAPrivateKey` 的典型特征。**

### 5.3 ★★★ 三个 PEM 文件都是 **LF 换行**

| 文件 | 换行 |
|---|---|
| `_ca.pem` | **LF** |
| `_leaf2_chain.pem` | **LF** |
| `_leaf2.key` | **LF** |

★★ **⇒ 与 `fake_auth_tls.py:133-134` 的 `"wb"` + `.encode()` **完全一致**（报告 045）。**

---

## 六、★★★ PEM 结构细节

### 6.1 `_ca.pem`（1,127 B / 20 行）

```
第一行: -----BEGIN CERTIFICATE-----
第二行: MIIDEzCCAfugAwIBAgIQNRD8GZGuvKJPXtKMuyo2
最后行: -----END CERTIFICATE-----
```

★★ **⇒ 20 行 = 1（BEGIN）+ 18（base64，每 64 字符）+ 1（END）。**

★ **⇒ 791 字节 DER ⇒ base64 约 1,055 字符 ⇒ 17 行 ⇒ 实际 18 行（含余数）。**

### 6.2 `_leaf2_chain.pem`（2,343 B / 40 行）

```
第一行: -----BEGIN CERTIFICATE-----
第二行: MIIDVjCCAj6gAwIBAgIIHGMigefhDpQwDQYJKoZI
最后行: -----END CERTIFICATE-----
```

★★★ **⇒ 40 行 = **两张证书**（叶 18 行 + CA 18 行 + 4 个 BEGIN/END 行）。**

★★ **⇒ 且**第一段是叶**（`MIIDVjCCAj6g...` = `_leaf2.cer` 的 base64），**
**⇒ 与 `fake_auth_tls.py:127` 的 `chain = _pem("CERTIFICATE", leaf)` 一致（叶在前）。**

★ **⇒ 大小验证：`_leaf2.cer` 的 PEM ≈ 1,180 + `_ca.pem` 1,127 ≈ **2,307**，**
**⇒ 实际 2,343（差异是 BEGIN/END 行）。**

### 6.3 `_leaf2.key`（1,675 B / 28 行）

```
第一行: -----BEGIN RSA PRIVATE KEY-----
第二行: MIIEowIBAAKCAQEA3J5M7o0Ef3YxcxNq4SGeV3xa
最后行: -----END RSA PRIVATE KEY-----
```

★★ **⇒ 28 行 ≈ 1,187 字节 DER ⇒ base64 约 1,583 字符 ⇒ 25 行 + 3 行头尾 = 28 ✓**

---

## 七、★★★ 序列号与公钥的对比

| 项 | CA | Leaf |
|---|---|---|
| **序列号长度** | **16 字节（128 位）** | **8 字节（64 位）** |
| **序列号值** | `3510FC1991AEBCA24F5ED28CBB2A36E2` | `1C632281E7E10E94` |
| **公钥** | **RSA 2048** | **RSA 2048** |
| **签名算法** | **sha256RSA** | **sha256RSA** |
| **基本约束长度** | **8 字节** | **2 字节** |

★★★ **⇒ 序列号长度不同 ⇒ 两张证书是**分别生成**的（不同参数）。**

★★ **⇒ 而有效期完全相同 ⇒ 同一时刻用同一个脚本生成。**

★ **⇒ 可能：`make_local_ca.ps1` 用 `New-SelfSignedCertificate` 生成 CA（默认 16 字节序列号），**
**再用 `New-SignedCertificate` 生成叶（8 字节序列号）。**

---

## 八、★★★★ 证书信任链的问题

### 8.1 ★★★ CA 是否在系统信任库？

**上一轮（报告 018）实测：**
```
LocalMachine\Root  无
CurrentUser\Root   无
```

★★★ **⇒ 本机的两个 Root 存储**都没有**这张 CA。**

### 8.2 ★★★ 那客户端怎么验证？

★★ **⇒ 三种可能（上一轮已列）：**
```
① 客户端用自己的 cacert.pem（319 KB）
② preflight 之后有一步装 CA（包里没有）
③ 客户端不校验 TLS 证书
```

★★★ **⇒ 最可能是 ①：**
**`preflight.ps1` 检查 `cacert.pem` 的 319 KB 大小 ——**
**如果客户端用 curl/OpenSSL 的默认 CA bundle，那 CA 必须**加进那个文件**。**

★★ **⇒ 但 `preflight.ps1` **只检查大小，不检查内容是否含本地 CA**。**

★★★ **⇒ 交付包**缺少"把 CODOL Local CA 加进 cacert.pem"这一步**。**

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ CA Subject | **`CN=CODOL Local CA 8cece11f`**（自签） |
| 2 | CA Serial | **`3510FC1991AEBCA24F5ED28CBB2A36E2`**（**16 字节**） |
| 3 | CA Thumbprint | **`7BD993655316DC8E1C4F2A997556EC4CBAC94D40`** |
| 4 | CA 扩展 | 密钥用法(4) / **基本约束(8)** / SKI(22) |
| 5 | ★★★ Leaf Subject | **`CN=formal-zone-auth.codol.qq.com`** |
| 6 | Leaf Issuer | `CN=CODOL Local CA 8cece11f` |
| 7 | Leaf Serial | **`1C632281E7E10E94`**（**8 字节**） |
| 8 | Leaf Thumbprint | **`448AA269C7D05756D3C03E06928DB49B269F28F8`** |
| 9 | Leaf 扩展 | **SAN(74)** / **EKU(12)** / 密钥用法(4) / **基本约束(2)** |
| 10 | ★★★ **SAN 三名** | **`localhost`** / `formal-zone-auth.codol.qq.com` / `formal-zone-lsg.codol.qq.com` |
| 11 | ★★★★★ **有效期** | **2026-10-04 23:55:06 → 2026-11-04 00:05:06（30.01 天）** |
| 12 | ★★★★★ **剩余** | **≈ 9.3 天**（今天 2026-10-25） |
| 13 | ★★ 过期后果 | 客户端 TLS 校验失败 ⇒ **卡 100** |
| 14 | ★★★ 30 天异常 | 正常 CA 是 1-10 年 ⇒ 显式指定了 `-NotAfter` |
| 15 | ★★ `_leaf2.key` | **PKCS#1**（`BEGIN RSA PRIVATE KEY`） |
| 16 | ★ 三个 PEM 换行 | **全部 LF** |
| 17 | ★★ `_leaf2_chain.pem` 顺序 | **叶在前，CA 在后**（40 行 = 2 张证书） |
| 18 | ★★★ **CA 未装信任库** | `LocalMachine\Root` 和 `CurrentUser\Root` **都没有** |
| 19 | ★★ 最可能的验证路径 | 客户端用**自己的 `cacert.pem`（319 KB）** |
| 20 | ★★★ 缺失步骤 | **"把 CA 加进 cacert.pem"** |

---

## 十、结论

### 1. ★★★★★ **证书 9.3 天后过期**是交付包最紧急的问题

```
NotAfter = 2026-11-04 00:05:06
今天     = 2026-10-25
        ↓
★ 剩余 ≈ 9.3 天
        ↓
过期后客户端 TLS 校验失败 ⇒ **卡 100**
```

★★ **⇒ 这个包有**保质期**。**

### 2. ★★★★★ **两张证书有效期完全相同**（同一时刻生成）

★ **⇒ 但序列号长度不同（16 vs 8 字节）⇒ 分别生成。**

### 3. ★★★ **SAN 三个域名与 `fake_auth_tls.py` 注释、`preflight.ps1` hosts 完全对应**

### 4. ★★★ **`_leaf2.key` 是 PKCS#1**（与 `build_pem_files()` 输出一致）

### 5. ★★★ **CA 未装系统信任库** ⇒ 必须靠客户端的 `cacert.pem`

★ **⇒ 而"把 CA 加进 cacert.pem"这一步**包里没有**。**

### 6. ★★ 三个 PEM 全是 LF（与 `"wb"` 写入一致）

---

## 十一、下一步

- `payload\` **四个插件 PE**（前一轮已做，需重做以保持本轮独立）
- `payload\` **四个 loader 二进制**（`Injector32.exe` / `Bootstrapper32.dll` / `Bootstrapper64.dll` / `ol_room_owner.exe`）
- `payload\` **18 个小 map lua** + `cha.lua`/`zm.lua` 剩余
- `source\` 结构与关键文档
