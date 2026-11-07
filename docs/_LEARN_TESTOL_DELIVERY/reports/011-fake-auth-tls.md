# 学习报告 011 — fake_auth_tls.py 逐行（17,600 B / 413 行）

**学习范围**：`bundle\fake_auth_tls.py` 全文
**核心发现**：**三处交付包内必然失败的硬缺陷**，其中一处是我上次亲自撞上的

---

## 一、这个模块在链条里的位置

```
dwauth.ini 写:
    formal-zone-auth.codol.qq.com  3074
    formal-zone-lsg.codol.qq.com   3074
hosts 写:
    127.0.0.1  formal-zone-auth.codol.qq.com    ← auth (TLS)
    127.0.0.2  formal-zone-lsg.codol.qq.com     ← lsg  (明文)

本模块 = 127.0.0.1:3074 的 TLS /auth/ 假服务
```

★ **关键情报（行 13）**：

> 以前我们用 **8443/8446** —— 那两个端口**客户端根本不会去连**。

★★ 这是**一条会浪费时间的历史教训**：端口不是"随便挑一个能监听就行"，
必须是 `dwauth.ini` 里写的那个。而且 **auth 和 lsg 同端口不同 IP**：
- `127.0.0.1:3074` = auth（TLS）
- `127.0.0.2:3074` = lsg（明文）

**同端口靠绑定不同回环 IP 区分** —— 这是整个方案的核心拓扑假设。

---

## 二、为什么不用 http.sys（行 15-18）

> 实测 **http.sys 关闭连接时不发 TLS close-notify**
> （客户端会看到 `SSLEOFError: EOF occurred in violation of protocol`）。
> 这里用 Python 的 `ssl` 自己收尾，**close_notify 一定会发出去**。

### 实现（行 382-388）

```python
try:
    ss.settimeout(1.5)
    ss.unwrap()          # ← 这一步才发 close_notify
    log("  TLS close-notify 已发")
except Exception as e:
    log("  close-notify: %r" % (e,))
```

★★ **`ss.unwrap()` 不是 `ss.close()`**：
- `close()` = 直接断 TCP，**不发** close_notify
- `unwrap()` = 发 close_notify，再做 TLS 正常收尾

★ **这是 OpenSSL 的硬性契约**：客户端收到没有 close_notify 的 EOF，
在很多语言里会**抛异常而不是当正常结束**。CODOL 客户端显然是这样。

---

## 三、票据（ticket）的 128 字节布局

### 壳：`TICKET` 常量（行 41）

```python
TICKET = bytes([0xDE,0xAD,0xBD,0xEF]) + bytes((k*31+7)&0xFF for k in range(4,128))
```

来源注释（行 38-40）：
> 票据公式来自三方 **CodolLocalLobbyServer.cs**：
> `ticket[0..3] = DE AD BD EF`；`ticket[k] = (k*31+7) & 0xFF` (k=4..127)
> （旧版我们写成 `DE AD BD EF + 04 05 06...`，与三方不同）

### 真正的字段布局（行 51-62，抄自 `Auth3Protocol.cpp:142-160`）

```cpp
ByteVector ticket(128);
writeU32(ticket,  0, 0xEFBDADDE);   // = DE AD BD EF (小端)
ticket[4] = 0;
writeU32(ticket,  5, identity.titleId);
writeU32(ticket,  9, now);
writeU32(ticket, 13, 0x7FFFFFFF);
writeU64(ticket, 17, 0);
writeU64(ticket, 25, identity.userId);
std::copy_n(username.begin(), min(17, len), ticket.begin() + 33);   // ★ 名字
std::copy(sessionKey.begin(), ..., ticket.begin() + 97);           // ★ 会话密钥
ticket[121]='3'; ticket[122]='U'; ticket[123]='"';
```

```
偏移    大小    内容
0x00    4      魔数 DE AD BD EF
0x04    1      0
0x05    4      titleId
0x09    4      now（时间戳）
0x0D    4      0x7FFFFFFF
0x11    8      0
0x19    8      userId
0x21    17     ★ displayName
0x61    24     ★ sessionKey（到 0x79）
0x79    3      '3' 'U' '"'
0x7C    4      （末尾，128-124）
```

★★ **`+97 (0x61)` 起是会话密钥** —— 这跟记忆中"128 字节服务器票据前 24 字节就是密钥"的
说法**不一样**！

★ 需要核对：记忆里说的是"认证服务器签发 128B 服务器票据，其**前 24 字节**就是密钥"。
而这里 `sessionKey` 在 `+97`。

**两种可能**：
- (a) 记忆是对的 ⇒ 这里 `+97` 是**另一个**字段（`Auth3Protocol.cpp` 的 userId/名字段）
- (b) 记忆记错了

**必须回源码核。** 这是**整个方案最关键的 24 字节**，不能靠记忆。

### 三方 shim 只覆盖 `+0x21..+0x31`（行 67-68）

> 本 shim 的 ticket 壳还是三方那套模式字节，这里**只覆盖 +33..+50 这 17 字节**，
> 其余一个字节不动（**最小改动，避免把已经跑通的认证弄坏**）。

★ **但这就意味着**：本 shim 发出的 ticket 的 `+0x61` 是**模式字节** `(k*31+7)`，
**不是真会话密钥**。

★★ **那么会话密钥从哪来？** —— 这正是 `nt10.py` 要做的（报告 005 的密钥快照）。
**auth 的 ticket 里没有密钥，密钥是 `nt10.py` 从客户端内存读的。**

---

## 四、UTF-8 截断的字符边界回退（行 71-78）★ 最实用的一段

```python
encoded = name.encode("utf-8")
while len(encoded) > 17:
    name = name[:-1]
    encoded = name.encode("utf-8")
raw[33:33+len(encoded)] = encoded
```

### 注释原文（行 71-73）

> 甲方要求把名字改成中文（「笑死了」）。ticket 的 +33 只有 17 字节，
> **直接 `[:17]` 会把多字节字符从中间切断**，客户端拿到半个 UTF-8 序列就是乱码。
> 改成按**字符边界**回退，直到 UTF-8 字节数 <= 17。

★★ **这是一个通用的坑**：定长字节字段截断字符串，**绝不能按字节切**，
必须按字符边界回退。

★ **反例**：`"笑死了"` = `E7 AC 91 E6 AD BB E4 BA 86` = 9 字节，能装下。
但 `"这是一个很长的中文名字"` = 33 字节，必须回退到 5 个字符（15 字节）。

---

## 五、★ 缺陷 1：`_rsa.txt` 不存在 —— 启动必崩

### 代码（行 115-135）

```python
def build_pem_files():
    key = {}
    with open(os.path.join(ROOT, "_rsa.txt")) as f:   # ← 硬依赖
        ...
```

### 调用点（行 398-400）

```python
if __name__ == "__main__":
    certfile, keyfile = build_pem_files()   # ← 第一行就崩
    CONTEXT = make_context(certfile, keyfile)
```

### 实测

```
--- _rsa.txt 是否存在 ---
False
```

★ **`bundle\` 里只有**：`_ca.cer`、`_ca.pem`、`_leaf2_chain.pem`、`_leaf2.cer`、`_leaf2.key`
—— **`_rsa.txt` 没有**。

★★ **所以按字面执行 `python fake_auth_tls.py` 会立刻 `FileNotFoundError`。**
这是我上次亲测撞上的第一个错误（错误 1）。

### 但注意：`_leaf2_chain.pem` + `_leaf2.key` **已经存在**

```
_leaf2_chain.pem   2343 B   ← 完整的 leaf + CA 链
_leaf2.key         1675 B   ← 已经是 PKCS#1 PEM
```

**`build_pem_files()` 的全部产出，包里已经有了。**
所以**正确的用法是跳过 `build_pem_files()`，直接用现成的两个文件**。

★ **这正是我上次的修法**（记忆错误 1 的修复）。

### ★★ 为什么 `_rsa.txt` 会缺？

`make_local_ca.ps1` 生成 `_rsa.txt`（导出的 RSA 参数），然后 `build_pem_files()`
把它转成 PEM。**但 `make_local_ca.ps1` 已经直接把 `_leaf2.key` 写出来了**（行 131-134
只是重写一遍）。

**所以 `_rsa.txt` 是中间产物，打包时被当成"缓存"排除了 —— 但代码还硬依赖它。**

★ **这是"打包者认为是中间产物、代码认为是输入"的经典错配。**

---

## 六、★ 缺陷 2：`display_name()` 的两个候选路径都不存在

### 代码（行 207-213）

```python
game = os.path.dirname(os.path.abspath(__file__))
for cand in (r"D:\repo\03-live\client\TESTOL",
             os.path.join(game, "..", "..", "TESTOL")):
    if os.path.isdir(os.path.join(cand, "Ayria", "Assets", "Alwaysoffline")):
        game = os.path.abspath(cand)
        break
root = os.path.join(game, "Ayria", "Assets", "Alwaysoffline")
```

### 实测

```
D:\repo\03-live\client\TESTOL                        ->  False
...\bundle\..\..\TESTOL                              ->  False
```

★ **两个都 False。**

★★ **而且第二个候选本身就错**：`bundle\..\..\TESTOL` = `F:\桌面\ol\TESTOL`
—— **凭空少了一层**。作者的开发布局可能是
`D:\repo\03-live\client\TESTOL\bundle\`，`..\..\TESTOL` 才成立。
交付包是 `TESTOL 完整交付版\bundle\`，`..\..\` 已经跑到 `F:\桌面\ol\` 了。

### 后果

`root` 指向不存在的目录
→ 三个读路径全部 `except` 吞掉
→ **返回 `("Client青", "hardcoded fallback")`**

★ **所以交付包里显示名恒为 `Client青`**，无论改 `Identity.json` 什么。

★★ **但这不崩溃** —— 因为它有兜底。这是**静默降级**，比崩溃更隐蔽。

---

## 七、`display_name()` 的完整读取顺序（行 196-254）

```
1. Ayria\Assets\Platformwrapper\Platform.json  →  platformUserId (去前导 0) = uid
2. Ayria\Assets\Alwaysoffline\1004\<uid>\Identity.json  →  displayName     ★ 权威
3. Ayria\Assets\Alwaysoffline\1004\*\Identity.json      →  第一个有 displayName 的
4. Ayria\Assets\Alwaysoffline\Identity.json             →  username        （迁移种子）
5. 兜底 "Client青"
```

### 校验条件（行 240-241）

```python
if doc.get("schemaVersion") != 1:   # ★ 必须 schemaVersion == 1
    continue
```

★ **`schemaVersion` 不等于 1 的会被跳过** —— 这是一个严格门槛。

### `sanitize()` 的历史（行 215-222）★ 一段已纠正的 bug

```python
# ★ 原来只放行 ASCII 32..126，中文会被整串滤掉、回退到根种子。
#   甲方要求中文名（「笑死了」），所以改成"只丢控制字符"
text = "".join(ch for ch in value if ord(ch) >= 32 and ord(ch) != 127)[:16]
```

★★ **原实现（只放行 ASCII）会让中文名直接失效**，`return None` → 回退兜底。
**修法**：只过滤控制字符（`<32` 和 `127`），其余全保留。

★ **注意截断仍按 16 字符**，字节长度由 `build_ticket` 的 17 字节上限单独管。
**两层限制，职责分离** —— 这是个好设计。

### 注释里揭示的架构真相（行 189-194）★★ 最重要的一段

> 老外的设计里这条应答由他的 `legacyAuth`（`PendingStreamServer`，**明文流**）产生，
> 名字取自 `PlayerIdentityStore`。
> **但那个明文流服务器与本客户端的 TLS 不兼容**
> （`Servers.cpp:153-181` 那个 `OLMOD_CLAIM_LEGACY_AUTH` 门就是为此加的），
> 所以这条 TLS 应答由本 shim 出 —— **那就必须把名字接到同一个权威档案上**。

★★ **这解释了为什么有两个 auth 实现**：
- 老外的 `Auth3Protocol.cpp` 走**明文流**（`legacyAuth`）
- 本客户端**要 TLS**，不兼容
- 所以本包用 Python `ssl` 出 TLS 应答（`fake_auth_tls.py`）
- 为此还加了 `OLMOD_CLAIM_LEGACY_AUTH` 环境变量门让插件**让出**这条路

★ **这与 `OLMOD_CLAIM_LOBBY` 是同一个设计模式**：
"插件默认想管，但可以设环境变量让它让出，交给 Python 侧管"。

---

## 八、`build_response()` 的应答结构（行 257-332）

### 三层嵌套（行 275-317）

```python
fields = ('"member_position":"1","estimated_wait_time":"0","next_poll_after":"1",'
          '"iv_seed":"%s",'
          '"client_ticket":"%s","client_ticket_size":"128",'
          '"server_ticket":"%s","server_ticket_size":"128",'
          '"lsg_server_ticket":"%s","lsg_server_ticket_size":"128"')

js = ('{"ret":0,"code":700,"auth_task":%d,"status":0,"success":true,%s,'
      '"data":{%s},"profile":{"id":1,"name":"%s"},"extra_data":"%s"}')
#      ↑ 扁平层                          ↑ data 内层        ↑ 名字   ↑ 转义的 JSON 字符串
```

```
{
  "ret": 0, "code": 700, "auth_task": N, "status": 0, "success": true,
  "member_position":"1", ... "lsg_server_ticket":"...",     ← 扁平层（同 fields）
  "data": { ...上面一模一样的 fields... },                    ← 内层重复
  "profile": { "id": 1, "name": "笑死了" },                  ← 名字（界面用）
  "extra_data": "<JSON 转义成的字符串>"                       ← ★ 名字（协议用）
}
```

★★ **字段在顶层和 `data` 内层**放两遍** —— 注释说"三方就是都放"。
说明客户端**两个位置都会读**（或版本不同读不同位置）。

### `extra_data` 是**字符串**不是对象（行 297 注释）

> `{ "extra_data", extraData.dump() }` ← 注意：值是一个**字符串**（JSON 转义）

★ **这是 Demonware 的常见形态**：嵌套 JSON 以字符串形式返，客户端二次 parse。

### `extra_data` 的五个字段（行 304-312）

```python
{"encrypted_register_codoid_data": b64("Shippo fuute, mofu-mofu!"),
 "encrypted_codoid":               b64("Hedgehogscience0"),
 "extended_data":                  "<预制的 base64 长串>",
 "time_to_live":                   9999,
 "username":                       b64(name)}      ← ★ 名字真正的载体
```

★ **前两个是**老外的占位常量**（`Shippo fuute, mofu-mofu!` / `Hedgehogscience0`）——
**逐字抄的**，说明它们**不校验内容**，只要存在且格式对。

★★ **`extended_data` 是一个预制 base64**：
```
eyJfX3YiOjEsImFsZyI6IlJTQS1PQUVQIiwiZW5jIjoiQTEyOENCQy1IUzI1NiIsImtpZCI6InVtYl8xIn0=
```
**解出来是**：`{"__v":1,"alg":"RSA-OAEP","enc":"A12OCBC-HS256","kid":"umb_1"}`
（注意 `A12OCBC` 可能是 `A128CBC` 的 OCR/拷贝错误 —— 值得校对）

★ 后面 `.` 分隔的三段是 JWE 的 dummy payload（`[Encrypted data.. much secret..]`）。

**这是一个**手搓的 JWE 壳**，内容全是假数据** —— 只要结构对，客户端就接受。

### `TASK_MAP`（行 80）

```python
TASK_MAP = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 57}
```

★ **`auth_task` 必须按这个表回**：请求 `0` → 回 `1`，请求 `32` → 回 `57`。
不在表里 → 一律回 `1`（行 268：`TASK_MAP.get(int(task), 1)`）。

★★ **`0→1, 10→11, 12→13, 24→25, 26→27` 都是 +1**，只有 **`32→57`** 是 +25。
说明 32 是**特殊的跳跃**（可能是"提交验证码"或"二次认证"）。

---

## 九、DW-\* 响应头（行 321-331）

```
DW-Ticket-Seed: <iv_seed 回显>
DW-Client-Ticket-Size: 128
DW-Client-Ticket: <TICKET_B64>
DW-Server-Ticket-Size: 128
DW-Server-Ticket: <TICKET_B64>
X-Local-Emulator: unsigned-protocol-experiment
```

★ 注释说"校验器会读" —— **除 JSON body 外还有 HTTP 头这一路**。
★ `X-Local-Emulator` 是自报家门的调试头，**客户端不看**（老外自己加的标记）。

★★ **注意 `DW-Client-Ticket` 和 `DW-Server-Ticket` 是**同一个值**（都是 `TICKET_B64`）
—— 而 JSON body 里 `client_ticket`/`server_ticket`/`lsg_server_ticket` **也是同一个**。

★ **三者全同** ⇒ 说明客户端**不校验它们之间的差异**，只要非空且有 128 字节就行。

---

## 十、HTTP 处理细节（行 335-395）

### Expect: 100-continue（行 364-366）

```python
if b"100-continue" in head.lower() and len(body) < clen:
    ss.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
```

★ **客户端发了 `Expect: 100-continue` 就必回 `100`**，否则它会等超时。

### `Connection: close`（行 329）

★ **每个请求一个 TCP 连接**，不做 keep-alive。配合 `close_notify` = 干净收尾。

### 超时（行 337 `conn.settimeout(30)`；行 384 `ss.settimeout(1.5)`）

★ 收请求 30 秒，收尾 1.5 秒。**收尾超时短** = 不为了 close_notify 卡住。

---

## 十一、★ 缺陷 3：`display_name()` 里 `game` 变量永远不更新（隐蔽 bug）

等等 —— 重读 207-213：

```python
game = os.path.dirname(os.path.abspath(__file__))     # = bundle 目录
for cand in (r"D:\repo\...", os.path.join(game, "..","..","TESTOL")):
    if os.path.isdir(...):
        game = os.path.abspath(cand)
        break
root = os.path.join(game, "Ayria", "Assets", "Alwaysoffline")
```

**如果两个候选都不存在，`game` 保持 = `bundle` 目录**，
于是 `root = bundle\Ayria\Assets\Alwaysoffline` —— **也不存在**。

★ 所以这不是第 3 个缺陷，是第 2 个缺陷的延伸：**三条路径全不存在的兜底**。

**撤销"缺陷 3"，只记 2 个硬缺陷。**

---

## 十二、这一块的结论

### 硬缺陷（交付包内必现）

| # | 缺陷 | 后果 | 修法 |
|---|---|---|---|
| 1 | `_rsa.txt` 缺失 | **启动即 `FileNotFoundError`** | 跳过 `build_pem_files()`，直接用现成的 `_leaf2_chain.pem`+`_leaf2.key` |
| 2 | game 路径两个候选都不存在 | **显示名恒为 `Client青`**（静默降级） | 加正确候选或外部传参 |

### 学到的契约

1. **auth 在 `127.0.0.1:3074`（TLS），lsg 在 `127.0.0.2:3074`（明文）** —— 同端口不同 IP。
2. **必须发 TLS close_notify（`unwrap()` 不是 `close()`）**，否则客户端 SSLEOFError。
3. **ticket 128 字节**：魔数 `DE AD BD EF` + `(k*31+7)` 壳，名字在 `+0x21` 17 字节。
4. **名字有两条路**：`profile.name`（界面）+ `extra_data.username`(b64)（协议），**都要给**。
5. **`extra_data` 是 JSON 字符串**不是对象，五个字段，前两个内容是占位常量。
6. **`auth_task` 按 `TASK_MAP` 回**，`32→57` 是唯一大跳。
7. **字段在顶层和 `data` 内层放两遍**，三个 ticket 是同一个值。
8. **UTF-8 定长字段截断必须按字符边界回退**。

---

## 十三、待验证（关键）

- [ ] ★★ **会话密钥在 ticket 的哪一段？** 记忆说"前 24 字节"，本文件抄的
      `Auth3Protocol.cpp` 说 `+97` 起 24 字节。**必须回源码核对。**
- [ ] `A12OCBC-HS256` 是否应为 `A128CBC-HS256`（拷贝错误？）
- [ ] `TASK_MAP` 的 `32→57` 是哪个认证阶段
- [ ] `_rsa.txt` 是否在 `make_local_ca.ps1` 的产物清单里（应加回打包）
- [ ] `Platform.json` 的 `platformUserId` 在交付包里存在吗
