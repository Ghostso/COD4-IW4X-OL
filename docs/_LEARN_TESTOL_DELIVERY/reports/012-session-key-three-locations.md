# 学习报告 012 — 会话密钥的"三个 24 字节"（消解报告 011 的疑问）

**学习范围**：`Auth3Protocol.cpp` + `LobbyProtocol.cpp` 交叉核对
**核心发现**：报告 011 标注的"矛盾"是我把一个字段当成了另一个 —— 实际有**三处独立的 24 字节**，各司其职

---

## 一、三处 24 字节，先分清

| # | 位置 | 代码 | 方向 | 含义 |
|---|---|---|---|---|
| ① | `makeTicket` 的 ticket `+97` | `Auth3Protocol.cpp:155` | **服务端→客户端** | ticket 内部回填 |
| ② | `codo_request` 的 `+32` | `Auth3Protocol.cpp:212` | **客户端→服务端** | task28/32 请求携带 |
| ③ | `authInfoData` 的前 24 字节 | `LobbyProtocol.cpp:116-118` | **客户端→LSG** | ★ **LSG 真正用的密钥** |

★★ **三者不是同一个字段。** 我上次把 ① 和 ③ 混为一谈，才以为矛盾。

---

## 二、② `codo_request` 的 `+32`（Auth3Protocol.cpp:199-213）

```cpp
void consumeTask28CodoRequest(const Json &extra, AuthIdentity &identity)
{
    const auto encoded = valueString(extra, "codo_request");
    const auto decoded = base64Decode(encoded);
    if (decoded.size() < 56)
        return;

    identity.userId = readU64(decoded, 6);                        // +0x06: userId
    const auto name = std::span(decoded).subspan(14, 16);         // +0x0E: 名字 16 字节
    const auto terminator = std::find(name.begin(), name.end(), 0);
    identity.username.assign(name.begin(), terminator);
    std::copy_n(decoded.begin() + 32,                        // +0x20: ★ 密钥 24 字节
                identity.sessionKey.size(),
                identity.sessionKey.begin());
}
```

```
codo_request 解码后布局（≥56 字节）
+0x00   6       （未用/头）
+0x06   8       userId (u64)
+0x0E   16      用户名（NUL 结尾）
+0x20   24      ★ 会话密钥
+0x38   ...     （余额，共 ≥56）
```

★ **这印证了 `fake_auth_tls.py` 注释里那句话**（行 64-65）：
> 客户端自己也会在请求 ticket 的 **+14 起 16 字节名字**

**`+14 = 0x0E` —— 逐字节吻合。**

### ★★ 这是关键：密钥是**客户端送上来的**

不是服务端生成的。客户端在 task28 里把自己的密钥交给 auth 服务端。

**那么客户端从哪拿到的密钥？** —— 往下看 ③。

---

## 三、③ `authInfoData` 的前 24 字节（LobbyProtocol.cpp:63-118）

### 注释原文（行 63-68）

> **THE SESSION KEY IS IN THE CLIENT'S OWN AUTH FRAME.** It is not minted here and it is
> not looked up: the auth server issues a 128-byte server ticket whose first 24 bytes
> are the key, and the client **forwards that ticket verbatim**.
> The C# reference does exactly one line — `var sessionKey = authInfoData[..24];`

### 帧结构（行 77-91）

```
authInfo 块（139 字节）
  bit 0     8 bits    serviceId          （无 tag）
  bit 8     1 bit     unknown bool       （无 tag）
  bit 9     5+32       titleId            （tagged）
  bit 46    5+32       ivSeed             （tagged）
  bit 83    1024      ★ authInfoData（128 字节）—— 不是字节对齐！
```

★ **`bit 83` 不是字节对齐** —— 注释明确说：
> 这正是为什么需要 **bit reader**，不能用"从抓包里目测的字节偏移"。

### 读取（行 103-118）

```cpp
AuthInfoBitReader reader(frame.subspan(6, 139));   // AuthInfoOffset = 6
skip(8); skip(1); skip(5+32); skip(5+32);          // → bit 83
std::array<uint8_t,128> data{};
reader.readBytes(data);
std::array<uint8_t,24> key{};
std::copy_n(data.begin(), 24, key.begin());        // ★ 前 24 字节
```

### 帧的外层（行 97-98）

```cpp
// frame is [u32 size][0xAB][0x82][authInfo][clientVerify];
constexpr std::size_t AuthInfoOffset = 6;
```

```
+0x000  u32   size
+0x004  u8    0xAB
+0x005  u8    0x82
+0x006  139   authInfo（含 128 字节 authInfoData）
+0x08B  ...   clientVerify
```

### ★★ 所以"前 24 字节"指的是 **`authInfoData` 的前 24 字节**

而 `authInfoData` = **auth 服务器发给客户端的那个 ticket 本身**（客户端原样转发）。

**回到 `makeTicket`：ticket 的 `+0..+4` 是魔数 `DE AD BD EF`。**
**那 `authInfoData[0:24]` = `DE AD BD EF 00 ...` —— 不是密钥！**

★ **这说明 `fake_auth_tls.py` 发出的 ticket 里，`+0` 的 24 字节是模式字节，不是密钥。**
**客户端转发过去，LSG 读到的是假密钥。**

---

## 四、① `makeTicket` 的 `+97` 到底是什么（Auth3Protocol.cpp:142-160）

```cpp
ByteVector makeTicket(const AuthIdentity &identity)
{
    ByteVector ticket(128);
    writeU32(ticket,  0, 0xEFBDADDE);        // DE AD BD EF
    ticket[4] = 0;
    writeU32(ticket,  5, identity.titleId);
    writeU32(ticket,  9, now);
    writeU32(ticket, 13, 0x7FFFFFFF);
    writeU64(ticket, 17, 0);
    writeU64(ticket, 25, identity.userId);
    copy_n(username, min(17,len), ticket+33);   // +0x21 名字
    copy(identity.sessionKey, ticket+97);       // +0x61 ★ 密钥
    ticket[121]='3'; ticket[122]='U'; ticket[123]='"';
    return ticket;
}
```

### ★ 关键：`+97` 的密钥**只在对 task28 加密时用**（行 276-278）

```cpp
auto ticket = makeTicket(identity);
if (authTask == 28)
    ticket = encryptTicket(ticket, identity.sessionKey);   // ★ 3DES-CBC
```

```cpp
ByteVector encryptTicket(ticket, sessionKey) {
    EVP_EncryptInit_ex(ctx, EVP_des_ede3_cbc(), nullptr, sessionKey.data(), CodolTicketIv.data());
    ...  // 128 字节整块，不补位
}
```

★★ **所以 `+97` 的密钥是"用来 3DES 加密整个 ticket"的**。
加密后 **`+97` 那 24 字节已被密文覆盖** —— 出厂值不重要。

**这是一个自洽的设计**：
- task28 之前：ticket 明文，`+97` = 密钥（但会被加密抹掉）
- task28：用密钥 3DES 加密整张 ticket → 客户端拿到密文
- 客户端**用同一个密钥解密** → 拿到明文 ticket
- 客户端转发明文 ticket 给 LSG

★ **task28 是一次"密钥握手"**：服务端证明"我知道密钥"，客户端验证。

### ★★ 那 LSG 读 `authInfoData[0:24]` 为什么能拿到密钥？

**因为客户端解密后，可能不是原样转发 ticket，而是在 `authInfoData` 前 24 字节填入密钥！**

`LobbyProtocol.cpp:64-65` 说的是 "the client forwards **that ticket** verbatim"，
而 C# 参照是 `sessionKey = authInfoData[..24]`。

**两种可能**：
- (a) 客户端转发时，`authInfoData` **不是** ticket，而是一个结构，前 24 = 密钥
- (b) 客户端转发 ticket，`ticket[0:24]` 真的就是密钥（即 `makeTicket` 的 `+0` 魔数不是固定的）

**这必须实测。** 但注意 `LobbyProtocol.cpp:121-124`：

```cpp
constexpr std::array<uint8_t,24> DefaultSessionKey{
    'S','h','i','p','p','o',' ','f','u','u','t','e',',',' ','m','o','f','u','-','m','o','f','u','!'
};
```

★★ **`DefaultSessionKey` = `"Shippo fuute, mofu-mofu!"` —— 正好 24 字节，且正好是
`fake_auth_tls.py` 里 `encrypted_register_codoid_data` 的明文内容！**

```
fake_auth_tls.py:306
    base64.b64encode(b"Shippo fuute, mofu-mofu!")
                    ↑ 就是这个 24 字节
```

**所以链路是**：
```
auth shim 的 extra_data.encrypted_register_codoid_data = b64("Shippo fuute, mofu-mofu!")
        ↓ 客户端解码
客户端把它当会话密钥（DefaultSessionKey）
        ↓ 放进 authInfoData[0:24] 或 codo_request[+32]
LSG 服务端读到
```

★★★ **这是重大发现：`DefaultSessionKey` 是一个**固定常量**，不是随机的。**

**但这与"503,664 组合 0 命中、密钥必须从内存读"矛盾！**

**解释**：`DefaultSessionKey` 是 **fallback**（行 531、648-660）：

```cpp
sessionKey_ = DefaultSessionKey;                          // :531 初始
...
const auto forwarded = sessionKeyFromClientAuth(frame);   // :650 客户端 ticket 优先
if (forwarded) {
    sessionKey_ = *forwarded;
    report("LSG session key taken from the client ticket.");
} else {
    report("LSG client ticket unreadable; falling back to the AuthSession key.");
}
keys_ = deriveSessionKeys(sessionKey_, transcript_);       // :660
```

★ **优先级**：客户端 ticket > AuthSession > Default。

★★ **但在本客户端的实际运行中，真实密钥是随机的**（这就是 nt10.py 存在的理由）。
`DefaultSessionKey` 只是"如果读不到就假设是这个"。

---

## 五、为什么"从 AuthSession 推导"是 [100] bug

注释原文（行 70-75）：

> Deriving the keys from this backend's AuthSession instead was the whole [100] bug:
> with `OLMOD_CLAIM_LOBBY=1` this backend **owns the lobby** while the **C# AuthServer owns
> auth**, so that AuthSession is **empty**, `deriveSessionKeys` produced the wrong
> decrypt/HMAC pair, the client's first encrypted `0x86` threw in
> `processServiceMessage` and **dropped the connection**.
> **Two clients also get DIFFERENT keys, so no single shared value could ever have worked.**

★★ **这是本项目最贵的一条教训**（对应 `[100] bug`）：
- **大厅**和**认证**被**拆到两个进程**
- 大厅进程的 `AuthSession` 是**空的**
- 用它推导密钥 → 全错
- 表现：**客户端第一条加密消息就断连**

★ **"两个客户端拿到不同密钥"** 说明密钥是**每会话随机**的 ——
这就是为什么**必须从客户端内存读**，不能图省事用常量。

---

## 六、验证过的六元组（LobbyProtocol.cpp:159-180）

```
decrypt      <- aes_out      (lobby_server.py:570 -> decrypt_task_frame)
requestHmac  <- hmac_out     (同一次调用)
encrypt      <- aes_in
responseHmac <- hmac_in
responseId   <- challenge
```

```
challenge  <hex8>
aes_out    <hex16>
aes_in     <hex16>
hmac_out   <hex20>
hmac_in    <hex20>
```

★ **5 个值共 80 字节 = 8+16+16+20+20**，从 `nt10.py` 的快照文件读（报告 005 的地址链）。

★★ **注意方向映射**：
- 客户端 `aes_out` = 服务端 `decrypt`
- 客户端 `aes_in` = 服务端 `encrypt`

**这是"客户端视角"的命名**，服务端要反过来用。**搞反就全解不开。**

---

## 七、`hite 协议头 ACK` 的两个版本（LobbyProtocol.cpp:125-157）

### 抓包样本（`ServerHeaderAck`）

```cpp
{ 0x16,0,0,0, 0xAB,0x81,0xD2,0,0,0, 0x70,0xE2,0xFD,0xC0,0xB6,0x6A,0x34,0x92,
  0x71,0x79,0xFC,0xB0,0x85,0x93,0x16,0x51 }
```

### 实测验证过的构造（`buildHeaderAck`）

```
u32 LE 22 | 0x00 | 0x81 | u32 LE 0xDC | 8 random bytes | hello[20:28]
```

```
+0x00  4  22 (小端 16 00 00 00)
+0x04  1  0x00            ← 抓包样本是 0xAB ✗
+0x05  1  0x81
+0x06  1  0xDC            ← 抓包样本是 0xD2 ✗
+0x07  1  0x00
+0x08  2  0x00 0x00
+0x0A  8  random
+0x12  8  hello[20:28]    ← 抓包样本是固定 71 79 FC B0 ... ✗
```

### ★★ 三处差异，逐条说明

| 偏移 | 抓包样本 | 实测正确 | 差异 |
|---|---|---|---|
| `+4` | `0xAB` | `0x00` | ★ 抓包帧的类型字节，不是 ACK 的 |
| `+6` | `0xD2` | `0xDC` | ★ |
| `+0x12..0x1A` | `71 79 FC B0 85 93 16 51` | `hello[20:28]` | ★★ **回显客户端的 8 字节 nonce** |

**实测正确值（`lobby_srv.log` 2026-10-03 13:57:41）**：
```
16 00 00 00 00 81 dc 00 00 00 c1 c0 e5 7b 35 85 0a 46 51 49 dd 31 1f fc 23 ef
```

★★★ **`+0x12` 回显 `hello[20:28]`** 是最关键的一条：
**这个 ACK 不是一个固定常量，而是要把客户端的 nonce 抄回去。**

★ 抓包样本的尾部 `71 79 FC B0 ...` 是**那一帧客户端的 nonce**，
被误当成"服务端固定值"。**这是典型的"从单次抓包硬编码"的坑。**

★★ **注释说抓包样本"只作为短 hello 的兜底尾巴"保留** —— 保留了但不该用。

---

## 八、Auth3 应答（Auth3Protocol.cpp:300-313）与 Python shim 的对照

### C++ 版

```cpp
Json response{
    { "client_ticket", ticket64 },
    { "server_ticket", ticket64 },
    { "code", "700" },
    { "extra_data", extraData.dump() },              // ★ 字符串
    { "auth_task", std::to_string(authTask + 1) },   // ★ 恒 +1
    { "identity", <hex> },
    { "iv_seed", std::to_string(ivSeed) },
};
```

### Python shim 版

```python
TASK_MAP = {0:1, 10:11, 12:13, 24:25, 26:27, 32:57}      # ★ 32→57 不是 +1
js = '{"ret":0,"code":700,"auth_task":%d,"status":0,"success":true,%s,"data":{%s},...'
```

### ★★ 三处差异

| 项 | C++ | Python shim |
|---|---|---|
| `auth_task` | **恒 `+1`** | **`TASK_MAP`**，`32→57` |
| `code` | **字符串 `"700"`** | **数字 `700`** ★ |
| `data` 内层 | **没有** | **有** |
| `ret`/`status`/`success` | **没有** | **有** |

★★ **`code` 类型不同（字符串 vs 数字）** —— 如果客户端严格校验类型，两者必有一个错。
**实测跑通的是 Python 版**（`fake_auth_tls.py` 有完整的踩坑注释），
所以 **`code` 用数字**。

★ **`auth_task` 的 `32→57`** 说明 C++ 版的"恒 +1"**在这个客户端上是错的**。
`32+1=33 ≠ 57`。

★★ **这证实了"老外的 backend 与本客户端不完全兼容"** ——
两套实现是**分别逆向同一协议**，细节不同。

---

## 九、这一块的结论

### 三处 24 字节（消解报告 011 的疑问）

| 位置 | 谁写 | 谁读 | 是"真密钥"吗 |
|---|---|---|---|
| `makeTicket` `+97` | auth 服务端 | 只有 3DES 加密用 | **否**（出厂值会被密文覆盖） |
| `codo_request` `+32` | 客户端 | auth 服务端 | **是**（客户端上报） |
| `authInfoData[0:24]` | 客户端转发 | **LSG 服务端** | ★ **是（LSG 实际用的）** |

★★ **报告 011 说"记忆说前24字节，本文件说 +97"—— 两者都对，指的不是同一个字段。**

### 关键教训

1. **`DefaultSessionKey` = `"Shippo fuute, mofu-mofu!"`（24 字节）**
   = `encrypted_register_codoid_data` 的明文 —— **是个固定常量**，只作 fallback。
2. **真实密钥每会话随机** ⇒ 必须从客户端内存读（`nt10.py`）。
3. **方向映射**：客户端 `aes_out` = 服务端 `decrypt`，`aes_in` = `encrypt`。**搞反全解不开。**
4. **`0x81` ACK 的 `+0x12` 必须回显 `hello[20:28]`**，不是固定字节。
   **从单次抓包硬编码固定值是典型陷阱。**
5. **[100] bug 的根因**：大厅/认证拆进程 ⇒ AuthSession 空 ⇒ 推导密钥全错 ⇒ 首条 `0x86` 断连。
6. **C++ 版与 Python shim 有实质差异**（`auth_task` 映射、`code` 类型、`data` 内层），
   **实测跑通的是 Python 版**。

---

## 十、待验证（关键）

- [ ] ★★ **`authInfoData` 到底是 ticket 原样，还是含 `[0:24]=密钥` 的另一个结构？**
      （C# 参照说 `authInfoData[..24]` 是密钥；`makeTicket` 的 `+0` 是魔数 —— 二者冲突）
- [ ] `AuthInfoBitReader` 的 `readBytes` 是否按 bit 83 起读 128 字节（138.4 字节总长 → 末端截断？）
- [ ] `DefaultSessionKey` 在真实运行中是否真的被用到（日志里搜 "falling back"）
- [ ] `CodolTicketIv` 常量值
- [ ] task32 的 `codo_request_size_bits` 默认 10 的含义
- [ ] `fake_auth_tls.py` 不处理 `codo_request` ⇒ 客户端送来的密钥被丢弃？影响如何？
