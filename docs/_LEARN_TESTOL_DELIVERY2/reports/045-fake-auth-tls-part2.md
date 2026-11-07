# 学习报告 045（重开）— `fake_auth_tls.py` 证书构造与显示名解析

**学习范围**：第 110–239 行（`build_pem_files` / `make_context` / `_get_str` / `display_name`）
**性质**：全实测
**★★★ 本报告收录**TLS 套件的降级策略**与**显示名三级回退的完整逻辑**

---

## 一、★★★★ `build_pem_files`（第 115–135 行）

```python
def build_pem_files():
    key = {}
    with open(os.path.join(ROOT, "_rsa.txt")) as f:          # ★★★ 硬依赖
        for ln in f:
            if "=" in ln:
                k, _, v = ln.strip().partition("=")
                key[k] = base64.b64decode(v)
    body = _der_int(b"\x00") + b"".join(
        _der_int(key[n]) for n in
        ("Modulus", "Exponent", "D", "P", "Q", "DP", "DQ", "InverseQ"))
    key_pem = _pem("RSA PRIVATE KEY", b"\x30" + _der_len(len(body)) + body)
    leaf = open(os.path.join(ROOT, "_leaf2.cer"), "rb").read()
    chain = _pem("CERTIFICATE", leaf)
    ca = os.path.join(ROOT, "_ca.pem")
    if os.path.exists(ca):
        chain += open(ca, "r").read()
    kp = os.path.join(ROOT, "_leaf2.key")
    cp = os.path.join(ROOT, "_leaf2_chain.pem")
    open(kp, "wb").write(key_pem.encode())      # 二进制写, 强制 LF
    open(cp, "wb").write(chain.encode())
    return cp, kp
```

### ★★★★★ 完整的输入/输出

**输入（3 个）**：
```
_rsa.txt      ← ★★★ 不存在！⇒ FileNotFoundError
_leaf2.cer    ← DER 证书
_ca.pem       ← CA 证书
```

**输出（2 个）**：
```
_leaf2.key         ← PKCS#1 PEM（RSA 私钥）
_leaf2_chain.pem   ← 叶 + CA 的 PEM 链
```

### ★★★ RSA 八元组的顺序

```python
("Modulus", "Exponent", "D", "P", "Q", "DP", "DQ", "InverseQ")
```

★★★ **⇒ 这是 PKCS#1 `RSAPrivateKey` 的标准字段顺序：**
```
version (0)
modulus      n
publicExponent e
privateExponent d
prime1       p
prime2       q
exponent1    dp
exponent2    dq
coefficient  qinv
```

★ **⇒ 代码里 `_der_int(b"\x00")` 就是 `version = 0`。**

### ★★ `"wb"` + `.encode()` —— 强制 LF（第 133 行注释）

```python
open(kp, "wb").write(key_pem.encode())      # 二进制写, 强制 LF
```

★★★ **⇒ 用**二进制模式**写，避免 Windows 把 `\n` 转成 `\r\n`。**

★★ **⇒ 这解释了上一轮报告 018 实测的"PEM 全用 LF 换行"**。**

### ★★★ `_rsa.txt` 的格式

```python
if "=" in ln:
    k, _, v = ln.strip().partition("=")
    key[k] = base64.b64decode(v)
```

★★ **⇒ 每行 `<名称>=<base64>` 格式（`Modulus=...` 等）。**

---

## 二、★★★★★ `make_context` 的 TLS 降级策略（第 138–152 行）

```python
def make_context(certfile, keyfile):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1        # ★ 允许 TLS 1.0
    except Exception:
        pass
    # 客户端只提供老的 RSA/DHE-CBC 套件(AES128-SHA/AES256-SHA 等)
    for cs in ("ALL:@SECLEVEL=0", "DEFAULT:@SECLEVEL=0"):
        try:
            ctx.set_ciphers(cs)
            break
        except Exception:
            continue
    ctx.load_cert_chain(certfile, keyfile)
    return ctx
```

### ★★★★★ 三处**安全降级**

| # | 降级 | 值 | 原因 |
|---|---|---|---|
| **1** | **最低 TLS 版本** | **`TLSv1`**（1.0） | 客户端只支持老版本 |
| **2** | **密码套件** | **`ALL:@SECLEVEL=0`** | ★ 允许弱套件 |
| **3** | **安全级别** | **`SECLEVEL=0`** | ★ 允许 RSA/DHE-CBC |

★★★ **⇒ 注释（第 144 行，逐字）：**
> **"客户端只提供老的 RSA/DHE-CBC 套件(AES128-SHA/AES256-SHA 等)"**

★★ **⇒ 两个具体套件：**
```
AES128-SHA
AES256-SHA
```

★★★ **⇒ 这是**2015 年前的 TLS 配置**（现代 OpenSSL 默认禁用）。**

★ **⇒ `@SECLEVEL=0` 是**唯一能启用这些套件的方式**（OpenSSL 3.0+）。**

★★ **⇒ 两层回退：先试 `ALL:@SECLEVEL=0`，失败则 `DEFAULT:@SECLEVEL=0`。**

---

## 三、★★★★ `_get_str` —— 不依赖 JSON 库的字段提取（第 155–179 行）

```python
def _get_str(body, key):
    """从请求 JSON 里粗取一个字段值(不依赖严格 JSON 解析)。"""
    i = body.find(('"%s"' % key).encode())
    if i < 0:
        return ""
    j = body.find(b":", i)
    if j < 0:
        return ""
    k = j + 1
    while k < len(body) and body[k:k + 1] in (b" ", b"\t"):
        k += 1
    if body[k:k + 1] == b'"':
        e = k + 1
        while e < len(body):
            if body[e] == 0x5C:            # ★ 反斜杠转义
                e += 2
                continue
            if body[e] == 0x22:            # ★ 双引号结束
                break
            e += 1
        return body[k + 1:e].decode("utf-8", "replace")
    e = k
    while e < len(body) and body[e:e + 1] not in (b",", b"}", b"\r", b"\n"):
        e += 1
    return body[k:e].decode("utf-8", "replace").strip()
```

### ★★★★★ 完整的手写 JSON 解析

```
① 找 `"<key>"` 
② 找后面的 `:`
③ 跳过空格/Tab
④ 若下一个字符是 `"` ⇒ 解析字符串（处理 `\` 转义）
   否则 ⇒ 解析到 `,` / `}` / CR / LF
⑤ UTF-8 解码（errors="replace"）
```

★★★ **⇒ 两个要点：**
```
① ★ 处理 `\` 转义（`0x5C` ⇒ 跳过 2 字节）
② ★★ 不依赖 `json` 库 ⇒ 容错性更强（畸形 JSON 也能提取）
```

★ **⇒ 注释："不依赖严格 JSON 解析" —— 因为客户端发的请求可能不规范。**

---

## 四、★★★★★ `display_name()` 的完整逻辑（第 182–239 行）

### 4.1 ★★★ 为什么必须改（第 185–188 行，逐字）

```python
# 为什么必须改：客户端界面上的名字**不是**从 LSG 拿的，是**从这条认证应答的
# `profile.name`** 拿的。原来这里硬编码 `Client青`，所以无论把
# `Ayria\Assets\Alwaysoffline\1004\<UID>\Identity.json` 的 `displayName` 改成什么，
# 客户端显示的都还是 `Client青` —— 实测（甲方 2026-10-05 17:0x：改名没生效）。
```

★★★★★ **⇒ 关键的因果发现：**
```
客户端界面上的名字
        ↓
**不是**从 LSG 拿的
        ↓
★ 是从**这条认证应答的 `profile.name`** 拿的
        ↓
原来硬编码 `Client青` ⇒ 无论怎么改 Identity.json 都无效
```

★★★ **⇒ 这与上一轮报告 014 的 `force_display_name.py` 的结论**互为补充**：**
```
服务端通道（本文件）：profile.name
客户端自造（force_display_name）：Windows 账户名 + Client
```

### 4.2 ★★★ 老外的设计与不兼容（第 190–194 行，逐字）

```python
# 老外的设计里这条应答由他的 `legacyAuth`（`PendingStreamServer`，明文流）产生，名字取自
# `PlayerIdentityStore`（`backend.md`：Auth3 ticket/response、LSG、房间成员与大厅显示
# 均使用 backend 档案中的名字）。但那个明文流服务器与本客户端的 TLS 不兼容
# （`Servers.cpp:153-181` 那个 `OLMOD_CLAIM_LEGACY_AUTH` 门就是为此加的），
# 所以这条 TLS 应答由本 shim 出 —— **那就必须把名字接到同一个权威档案上**。
```

★★★★ **⇒ 完整的架构解释：**
```
老外：legacyAuth（PendingStreamServer，**明文流**）
        ↓ 名字取自 PlayerIdentityStore
        ↓
★ 但明文流服务器与本客户端的 **TLS 不兼容**
        ↓
（Servers.cpp:153-181 的 OLDMOD_CLAIM_LEGACY_AUTH 门就是为此加的）
        ↓
★ 所以这条 TLS 应答由本 shim 出
        ↓
★★★ 那就必须把名字**接到同一个权威档案**上
```

★★ **⇒ 这与报告 033 的 `OLMOD_CLAIM_LEGACY_AUTH`**完全呼应**。**

### 4.3 ★★★ 三级回退（第 196–202 行，逐字）

```python
# 读取顺序：
#   1. `Ayria\Assets\Alwaysoffline\1004\<UID>\Identity.json` 的 `displayName`（权威）
#      <UID> 优先取 `Assets\Platformwrapper\Platform.json` 的 `platformUserId` 去掉前导零；
#      取不到就扫 `1004\*` 里第一个有 `Identity.json` 的目录。
#   2. 根迁移种子 `Ayria\Assets\Alwaysoffline\Identity.json` 的 `username`
#   3. 兜底 `Client青`（保持与旧行为一致，便于回退对照）
```

★★★ **⇒ 三级回退：**
```
① 1004\<UID>\Identity.json 的 displayName     ★ 权威
   <UID> = Platform.json 的 platformUserId 去前导零
   或扫 1004\* 找第一个有 Identity.json 的
        ↓
② Ayria\Assets\Alwaysoffline\Identity.json 的 username   ← 迁移种子
        ↓
③ 兜底 "Client青"
```

★★ **⇒ 第 ① 步的 `lstrip("0")` 与上一轮报告 017 的发现**一致**：**
```
"01100001DEADC0DE"  →  lstrip("0")  →  "1100001DEADC0DE"（★ 15 位）
```

★★★ **⇒ 而包内 `1004\` 下**没有** `<UID>` 目录（报告 017 已确认）⇒ 第 ① 步必然落空。**

★ **⇒ 所以**实际走第 ② 步** ⇒ 名字 = `Alwaysoffline`（报告 017 的结论）。**

### 4.4 ★★★ 游戏目录的两个候选（第 207–213 行）

```python
game = os.path.dirname(os.path.abspath(__file__))
# fake_auth_tls.py 在 Workmd 基线目录里，游戏目录要另外找
for cand in (r"D:\repo\03-live\client\TESTOL", os.path.join(game, "..", "..", "TESTOL")):
    if os.path.isdir(os.path.join(cand, "Ayria", "Assets", "Alwaysoffline")):
        game = os.path.abspath(cand)
        break
root = os.path.join(game, "Ayria", "Assets", "Alwaysoffline")
```

★★★ **⇒ 两个候选：**
```
① D:\repo\03-live\client\TESTOL        ← 作者机器
② <bundle>\..\..\TESTOL                ← ★ 少一层（上一轮已指出）
```

★★ **⇒ 第二个候选 `<bundle>\..\..\TESTOL` = `F:\桌面\ol\TESTOL` —— **不存在**（报告 011 已确认）。**

### 4.5 ★★★ `sanitize` 的两次修正（第 215–222 行）

```python
def sanitize(value):
    if not isinstance(value, str):
        return None
    # ★ 2026-10-05 21:5x -- 原来只放行 ASCII 32..126，中文会被整串滤掉、回退到根种子。
    #   甲方要求中文名（「笑死了」），所以改成"只丢控制字符"，其余（含中文）保留；
    #   截断仍按 16 **字符**，字节长度由 build_ticket 的 17 字节上限单独管。
    text = "".join(ch for ch in value if ord(ch) >= 32 and ord(ch) != 127)[:16]
    return text or None
```

★★★★ **⇒ 一次**重要的行为修正**：**
```
原来：只放行 ASCII 32..126  ⇒ 中文被**整串滤掉** ⇒ 回退到根种子
        ↓
改成：只丢控制字符（< 32 和 127），其余（含中文）保留
        ↓
★ 截断仍按 **16 字符**（不是字节）
★ 字节长度由 `build_ticket` 的 **17 字节上限**单独管
```

★★★ **⇒ 两层限制，职责分离：**
```
sanitize    →  16 **字符**（语义层）
build_ticket →  17 **字节**（协议层）
```

★ **⇒ 这是**正确的分层设计**（报告 044 已记录 `build_ticket` 的字符边界回退）。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ `build_pem_files` 输入 | **`_rsa.txt`（缺失！）** / `_leaf2.cer` / `_ca.pem` |
| 2 | 输出 | `_leaf2.key`（PKCS#1）/ `_leaf2_chain.pem` |
| 3 | RSA 八元组 | `Modulus/Exponent/D/P/Q/DP/DQ/InverseQ` |
| 4 | ★ 写文件 | **`"wb"` + `.encode()`** ⇒ 强制 LF |
| 5 | ★★★ 最低 TLS | **`TLSv1`（1.0）** |
| 6 | ★★★ 密码套件 | **`ALL:@SECLEVEL=0`** |
| 7 | ★★ 具体套件 | **`AES128-SHA` / `AES256-SHA`**（RSA/DHE-CBC） |
| 8 | ★ 两层回退 | `ALL:@SECLEVEL=0` → `DEFAULT:@SECLEVEL=0` |
| 9 | ★★ `_get_str` | **手写 JSON 解析**（处理 `\` 转义，不依赖 `json` 库） |
| 10 | ★★★★★ **名字的真实来源** | **认证应答的 `profile.name`**（不是 LSG） |
| 11 | ★★★ 老外的 legacyAuth | **明文流**，与客户端 TLS **不兼容** |
| 12 | ★★ `OLMOD_CLAIM_LEGACY_AUTH` | 为此而加的让出门 |
| 13 | ★★★ 三级回退 | `1004\<UID>\Identity.json` → 根种子 → **`"Client青"`** |
| 14 | ★★ `<UID>` 来源 | `platformUserId` **`lstrip("0")`** ⇒ 15 位 |
| 15 | ★★★ 实际落点 | **`1004\` 无 `<UID>` 目录 ⇒ 走第 ② 步 ⇒ `Alwaysoffline`** |
| 16 | ★★ 两个候选 | `D:\repo\...` / `<bundle>\..\..\TESTOL`（**均不存在**） |
| 17 | ★★★ `sanitize` 修正 | 原来只放行 ASCII ⇒ **中文被滤掉**；改成只丢控制字符 |
| 18 | ★★ 两层限制 | `sanitize` **16 字符** / `build_ticket` **17 字节** |

---

## 六、结论

### 1. ★★★★★ **`profile.name` 是名字的真实来源**（不是 LSG）

★ **⇒ 这解释了"改 `Identity.json` 无效"的现象。**

### 2. ★★★ **TLS 必须降级到 `TLSv1` + `@SECLEVEL=0`**

★ **⇒ 因为客户端只提供 `AES128-SHA` / `AES256-SHA`（2015 年前的套件）。**

### 3. ★★★ **`_rsa.txt` 缺失 ⇒ `build_pem_files` 必然崩溃**（报告 001 已确认）

### 4. ★★★ **三级回退实际落到第 ② 步**（`1004\` 无 `<UID>` 目录）

★ **⇒ 名字 = `Alwaysoffline`。**

### 5. ★★★ **`sanitize` 的两次修正**（ASCII → 只丢控制字符）

### 6. ★★ **两层限制分离**（字符层 16 / 字节层 17）

---

## 七、下一步

- `fake_auth_tls.py` 剩余（第 239 行起）—— `build_response` / `handle` / `main`
- `stun_local.py`（7,618 B）
- `force_display_name.py`（19,288 B）
- `bundle\` 五个证书文件
