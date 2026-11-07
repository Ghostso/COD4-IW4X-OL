# 学习报告 044（重开）— `fake_auth_tls.py` 头部与票据构造

**学习范围**：`bundle\fake_auth_tls.py`（17,600 B）第 1–110 行
**性质**：全实测
**★★★ 本报告收录**票据的完整 128 字节布局**与**TASK_MAP 的六项映射**

---

## 一、★★★★ 文件头 docstring（第 1–23 行，逐字）

### 1.1 ★★★ 端口/地址来源（第 4–13 行）

```
端口/地址来源(三方已验证可用):
  Run-Session.ps1 把 hosts 写成
      127.0.0.1 formal-zone-auth.codol.qq.com
      127.0.0.2 formal-zone-lsg.codol.qq.com
  并把 dwauth.ini 写成
      formal-zone-lsg.codol.qq.com 3074
      formal-zone-auth.codol.qq.com 3074
      0x03EA
  即: 【auth(auth服务, TLS) 在 127.0.0.1:3074】, 【lsg(大厅明文) 在 127.0.0.2:3074】。
  以前我们用 8443/8446 —— 那两个端口客户端根本不会去连。
```

★★★★ **⇒ 完整的拓扑：**
```
127.0.0.1:3074  →  formal-zone-auth.codol.qq.com   （★ TLS 认证）
127.0.0.2:3074  →  formal-zone-lsg.codol.qq.com    （★ 明文大厅）
        ↓
★★★ 同一个端口 **3074**，不同**回环 IP**
```

★★ **⇒ 且明确记录了一次**历史错误**：**
> **"以前我们用 8443/8446 —— 那两个端口客户端根本不会去连。"**

★ **⇒ 与报告 040 的 `[who]` 旁证（关注 8443/8446/8081）**完全对应**。**

### 1.2 ★★★★★ 为什么不用 http.sys（第 15–18 行，逐字）

```
为什么不用 fake_auth_https.ps1(http.sys):
  实测 http.sys 关闭连接时【不发 TLS close-notify】(客户端会看到
  SSLEOFError: EOF occurred in violation of protocol)。这里用 Python 的 ssl
  自己收尾, close_notify 一定会发出去。
```

★★★★★ **⇒ 一个**极其具体的协议细节**：**
```
http.sys 关闭连接时 **不发 TLS close-notify**
        ↓
客户端看到 **`SSLEOFError: EOF occurred in violation of protocol`**
        ↓
★ 用 Python `ssl` 自己收尾 ⇒ **close_notify 一定会发出去**
```

★★★ **⇒ 这是**TLS 协议层的硬要求**（RFC 5246 §7.2.1）：**
**没有 `close_notify` 的 EOF 会被视为"违反协议"。**

### 1.3 ★★ 证书来源（第 20–22 行）

```
证书: _leaf2.cer(由受信任的本地 root CA 签发) + _rsa.txt(导出的 RSA 私钥参数)
     —— 两者由 make_local_ca.ps1 生成, leaf 的 SAN = localhost +
     formal-zone-auth.codol.qq.com + formal-zone-lsg.codol.qq.com
```

★★★ **⇒ SAN 三个域名（与上一轮报告 018 实测**完全一致**）：**
```
localhost
formal-zone-auth.codol.qq.com
formal-zone-lsg.codol.qq.com
```

★★ **⇒ 且 `_rsa.txt` 被明确列为依赖 —— 而它**不在包里**（报告 001 已确认）。**

---

## 二、★★★★★ 票据的完整 128 字节布局（第 45–79 行）

### 2.1 ★★★ 老外的 `makeTicket` 逐字引用（第 51–62 行）

```cpp
ByteVector ticket(128);
writeU32(ticket, 0, 0xEFBDADDE);
ticket[4] = 0;
writeU32(ticket, 5, identity.titleId);
writeU32(ticket, 9, now);
writeU32(ticket, 13, 0x7FFFFFFF);
writeU64(ticket, 17, 0);
writeU64(ticket, 25, identity.userId);
const auto usernameSize = std::min<std::size_t>(17, identity.username.size());
std::copy_n(identity.username.begin(), usernameSize, ticket.begin() + 33);   // ★ 名字
std::copy(identity.sessionKey.begin(), identity.sessionKey.end(), ticket.begin() + 97);
ticket[121] = '3'; ticket[122] = 'U'; ticket[123] = '"';
```

### ★★★★★ 完整的 128 字节布局表

| 偏移 | 大小 | 内容 |
|---|---|---|
| **`0x00`** | 4 | **魔数 `0xEFBDADDE`**（= `DE AD BD EF` 小端） |
| **`0x04`** | 1 | `0` |
| **`0x05`** | 4 | `titleId` |
| **`0x09`** | 4 | `now`（时间戳） |
| **`0x0D`** | 4 | **`0x7FFFFFFF`** |
| **`0x11`** | 8 | `0` |
| **`0x19`** | 8 | `userId` |
| **`0x21`** | **17** | ★★★ **`username`**（显示名） |
| **`0x61`** | 24 | ★ **`sessionKey`**（到 `0x79`） |
| **`0x79`** | 3 | **`'3'` `'U'` `'"'`** |
| `0x7C` | 4 | （剩余，128−124） |

★★★ **⇒ 三个关键位置：**
```
+0x21（33）  ←  username（17 字节）
+0x61（97）  ←  sessionKey（24 字节）
+0x79（121） ←  '3' 'U' '"'
```

### 2.2 ★★★ 客户端请求里也有名字（第 64–65 行）

```
同一文件的 `:207-211` 又说明**客户端自己也会在请求 ticket 的 +14 起带 16 字节名字**，
老外是**用档案里的名字覆盖它**再回给客户端 —— 所以应答 ticket 的 +33 才是权威位置。
```

★★★ **⇒ 两个名字位置：**
```
客户端请求 ticket 的 **+14**（16 字节）  ← 客户端自己填的
应答 ticket 的     **+33**（17 字节）  ← ★★★ **权威位置**
```

★★ **⇒ 老外"用档案里的名字**覆盖**它" ⇒ 应答的 +33 才是客户端最终读的。**

### 2.3 ★★★ 本 shim 的最小改动策略（第 67–68 行，逐字）

```
本 shim 的 ticket 壳还是三方那套模式字节（`DE AD BD EF` + `(k*31+7)`），
这里**只覆盖 +33..+50 这 17 字节**，其余一个字节不动（最小改动，避免把已经跑通的认证弄坏）。
```

★★★ **⇒ **只改 17 字节，其余 111 字节保持模式字节。**

★ **⇒ 理由："避免把已经跑通的认证弄坏"。**

### 2.4 ★★★★★ UTF-8 字符边界回退（第 71–78 行）

```python
# ★ 2026-10-05 21:5x -- 甲方要求把名字改成中文（「笑死了」）。ticket 的 +33 只有 17 字节，
#   直接 [:17] 会把多字节字符从中间切断，客户端拿到半个 UTF-8 序列就是乱码。
#   改成按**字符边界**回退，直到 UTF-8 字节数 <= 17。
encoded = name.encode("utf-8")
while len(encoded) > 17:
    name = name[:-1]
    encoded = name.encode("utf-8")
raw[33:33 + len(encoded)] = encoded
```

★★★★★ **⇒ 一个**经典的 UTF-8 截断问题**：**
```
中文名「笑死了」= E7 AC 91 E6 AD BB E4 BA 86 = 9 字节 ✓ 装得下
        ↓
但长名字会超过 17 字节
        ↓
★ 直接 [:17] 会把多字节字符**从中间切断**
        ↓
客户端拿到**半个 UTF-8 序列** ⇒ 乱码
        ↓
★★★ 解法：按**字符边界**回退（逐字符删，直到 ≤ 17 字节）
```

★ **⇒ 这与上一轮报告 014 的 `force_display_name.py` 的 `truncate_encoded` 是同一类问题。**

---

## 三、★★★★ `TICKET` 常量与公式（第 37–42 行）

```python
# ---- 契约常量 ----
# 票据公式来自三方 CodolLocalLobbyServer.cs:
#   ticket[0..3] = DE AD BD EF ; ticket[k] = (k*31 + 7) & 0xFF  (k = 4..127)
# (旧版我们写成 DE AD BD EF + 04 05 06..., 与三方不同)
TICKET = bytes([0xDE, 0xAD, 0xBD, 0xEF]) + bytes((k * 31 + 7) & 0xFF for k in range(4, 128))
TICKET_B64 = base64.b64encode(TICKET).decode()
```

### ★★★★★ 票据壳的完整公式

```
ticket[0..3]  = DE AD BD EF            （魔数）
ticket[k]     = (k*31 + 7) & 0xFF      （k = 4..127）
```

★★★ **⇒ 一个**线性同余**的模式字节序列。**

★ **⇒ 且记录了**旧版的错误**：**
> **"旧版我们写成 `DE AD BD EF + 04 05 06...`，与三方不同"**

★★ **⇒ 即：旧版是**递增字节**，三方是**线性公式**。**

### ★★ 前几个字节的实算

```
k=4:  (4*31 + 7) & 0xFF = 131 & 0xFF = 0x83
k=5:  (5*31 + 7) = 162 = 0xA2
k=6:  (6*31 + 7) = 193 = 0xC1
k=7:  (7*31 + 7) = 224 = 0xE0
k=8:  (8*31 + 7) = 255 = 0xFF
k=9:  (9*31 + 7) = 286 & 0xFF = 0x1E
...
```

★★ **⇒ 完整票据开头：`DE AD BD EF 83 A2 C1 E0 FF 1E ...`**

---

## 四、★★★★★ `TASK_MAP`（第 80 行）

```python
TASK_MAP = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 57}
```

### ★★★★★ 六项映射

| 请求 `auth_task` | 应答 `auth_task` | 差值 |
|---|---|---|
| **0** | **1** | +1 |
| **10** | **11** | +1 |
| **12** | **13** | +1 |
| **24** | **25** | +1 |
| **26** | **27** | +1 |
| **32** | **57** | ★★★ **+25** |

★★★ **⇒ 五项是 +1，只有 `32 → 57` 是 +25。**

★★ **⇒ 这与报告 025 的"补丁后 `auth_task` 从 32 变成 10"**呼应**：**
```
未打补丁：客户端发 32  →  应答 57
打了补丁：客户端发 10  →  应答 11
```

★★★ **⇒ 所以 `32 → 57` 是**"未签名路径"的任务号**，`10 → 11` 是**"已签名路径"**。**

---

## 五、★★★ DER/PEM 手工构造（第 93–110 行）

```python
# ---- 把 RSA 参数拼成 PKCS#1 PEM ----
def _der_len(n):
    if n < 0x80:
        return bytes([n])
    e = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(e)]) + e

def _der_int(b):
    b = b.lstrip(b"\x00") or b"\x00"
    if b[0] & 0x80:
        b = b"\x00" + b
    return b"\x02" + _der_len(len(b)) + b

def _pem(tag, der):
    b = base64.b64encode(der).decode()
    return ("-----BEGIN %s-----\n" % tag
```

### ★★★★★ 三个 DER 编码函数

**① `_der_len(n)` —— DER 长度编码**
```python
n < 0x80      →  单字节 n
否则          →  0x80|字节数 + 大端字节
```

**② `_der_int(b)` —— DER INTEGER 编码**
```python
① 去掉前导 0x00
② 若最高位是 1（负数）⇒ 补一个 0x00（★ 保证非负）
③ 格式：0x02 + 长度 + 内容
```

★★★ **⇒ 第 ② 步是**关键的 DER 规则**：**
```
INTEGER 是有符号的
        ↓
若最高位是 1 ⇒ 会被解释为**负数**
        ↓
★ 必须补 0x00
```

**③ `_pem(tag, der)` —— PEM 封装**
```python
base64(der) 每 64 字符一行
+ -----BEGIN <tag>----- / -----END <tag>-----
```

★★★ **⇒ 这三个函数**手工实现了完整的 DER/PEM 编码**（不依赖 cryptography 库）。**

★ **⇒ 这解释了为什么 `_rsa.txt`（RSA 参数）是必需的输入。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 拓扑 | **`127.0.0.1:3074`=auth(TLS) / `127.0.0.2:3074`=lsg(明文)** |
| 2 | ★ 历史错误 | 以前用 **8443/8446**，客户端不连 |
| 3 | ★★★★★ **必须发 close_notify** | http.sys 不发 ⇒ `SSLEOFError` |
| 4 | ★★ SAN 三域名 | `localhost` / `formal-zone-auth` / `formal-zone-lsg` |
| 5 | ★ 依赖 | **`_rsa.txt`**（不在包里） |
| 6 | ★★★ 票据魔数 | **`0xEFBDADDE`**（`DE AD BD EF` 小端） |
| 7 | ★★★ 票据公式 | **`ticket[k] = (k*31 + 7) & 0xFF`**（k=4..127） |
| 8 | ★ 旧版错误 | `DE AD BD EF + 04 05 06...`（递增，非三方） |
| 9 | ★★★ **名字位置（应答）** | **`+0x21`（33），17 字节** |
| 10 | ★★ **名字位置（请求）** | **`+14`，16 字节**（客户端自己填） |
| 11 | ★ `sessionKey` | **`+0x61`（97），24 字节** |
| 12 | ★ 尾部标记 | **`+0x79`（121）= `'3' 'U' '"'`** |
| 13 | ★★★ 最小改动 | **只覆盖 33..50 这 17 字节** |
| 14 | ★★★★★ **UTF-8 截断** | 按**字符边界**回退（不切断多字节字符） |
| 15 | ★★★ `TASK_MAP` | 5 项 +1，**`32→57` 是 +25** |
| 16 | ★★ DER 编码 | `_der_len` / `_der_int`（补 0x00）/ `_pem` |

---

## 七、结论

### 1. ★★★★★ **必须发 TLS `close_notify`** 是协议硬要求

★ **⇒ http.sys 不发 ⇒ 客户端 `SSLEOFError`。**

### 2. ★★★★★ 票据的 128 字节布局已完全定案（含三个关键偏移）

```
+0x21（33）  username   17 字节   ← ★ 权威名字位置
+0x61（97）  sessionKey 24 字节
+0x79（121） '3' 'U' '"'
```

### 3. ★★★ **`TASK_MAP` 的 `32→57` 是唯一大跳**（+25）

★ **⇒ 与补丁后的 `32→10` 呼应：未签名 vs 已签名两条路径。**

### 4. ★★★ **UTF-8 截断必须按字符边界**（否则半个字符 ⇒ 乱码）

### 5. ★★ 票据壳是**线性同余公式**（`k*31+7`），不是递增字节

### 6. ★★ DER/PEM 是**手工实现**的（不依赖外部库）

---

## 八、下一步

- `fake_auth_tls.py` 剩余（第 110 行起）—— `build_pem_files` / `make_context` / `build_response` / `handle`
- `stun_local.py`（7,618 B）
- `force_display_name.py`（19,288 B）
- `bundle\` 五个证书文件
