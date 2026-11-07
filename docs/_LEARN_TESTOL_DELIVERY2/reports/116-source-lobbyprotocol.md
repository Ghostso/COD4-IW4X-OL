# 学习报告 116（重开）— `LobbyProtocol`（90 + 866 行）

**学习范围**：`LobbyProtocol.hpp`（2,967 B / 90 行）+ `.cpp`（41,030 B / 866）
**性质**：全实测（**两文件逐行读完**）
**★★★★★ 本报告收录八个重大发现**：①**`secrets.txt` 五键通道与"503,664 组合零命中"** ②**`0xC8` 28 字节头与 `0x81` 应答的验证** ③**`0x82` 的 authInfo 位布局（bit 83 不对齐）** ④**`0x83` 必须回显客户端 challenge（两次实测）** ⑤**"0x83 不能延迟"的实测** ⑥**`0x85` 帧的完整加密格式** ⑦**`lenfield` 的两个可接受值** ⑧**"只推不回"的最终处置**

---

## 一、★★★★★ **`secrets.txt` 五键通道（含 503,664 组合零命中）**

### 1.1 ★★★★★ 完整注释（第 160–182 行，逐字）

```cpp
// THE VERIFIED SESSION KEYS COME OUT OF THE CLIENT PROCESS, NOT OUT OF THE WIRE.
// docs/LSG-我方规格.md section 8. The Python lobby that reaches the menu does not
// derive anything: it reads the snapshot nt10.py takes out of the client's memory
// (nt10.py:732-759) and uses it verbatim --
//
//     decrypt      <- **aes_out**    (lobby_server.py:570 -> decrypt_task_frame)
//     requestHmac  <- **hmac_out**   (same call)
//     encrypt      <- **aes_in**     (lobby_server.py:603 -> build_task_reply_objects)
//     responseHmac <- **hmac_in**    (same call)
//     responseId   <- **challenge**  (lobby_server.py:652 -> build_stage2, the 0x83 body)
//
// We keep that whole channel and change only who writes the file: the C#/Python
// stack used an external reader because a server process reading the game's memory
// is blocked; this backend simply consumes the same file. Format unchanged:
//
//     pid <dec>            state <dec>
//     challenge <hex8>     aes_out <hex16>   aes_in <hex16>
//     hmac_out  <hex20>    hmac_in  <hex20>
//
// Path: **`OLMOD_LSG_SECRETS`**, defaulting to `./secrets.txt`.
// A near-miss against the AuthSession derivation was worth **503,664 combinations
// with zero hits** (tools/lsg_probe/derive_sweep.py), so this is not a shortcut --
// it is **the only source that reproduces the client's keys**.
```

### ★★★★★ 五个键的完整映射

| 字段 | 来源文件键 | 目标 |
|---|---|---|
| **`decrypt`** | ★ **`aes_out`** | 解密入站 |
| **`requestHmac`** | ★ **`hmac_out`** | 验证入站 HMAC |
| **`encrypt`** | ★ **`aes_in`** | 加密出站 |
| **`responseHmac`** | ★ **`hmac_in`** | 生成出站 HMAC |
| **`responseId`** | ★ **`challenge`** | `0x83` 的 body |

★★★ **⇒ 注意**交叉命名**：**
```
**`aes_out`** ⇒ 用作文档里的 **`decrypt`**（客户端"出"的密钥,我们用来"解"）
**`aes_in`**  ⇒ 用作文档里的 **`encrypt`**（客户端"入"的密钥,我们用来"加"）
        ↓
★★★ ⇒ 从**客户端视角**命名,从**服务端视角**使用
```

### ★★★★★ `secrets.txt` 的 7 行格式

```
pid <dec>            state <dec>
challenge <hex8>     aes_out <hex16>   aes_in <hex16>
hmac_out  <hex20>    hmac_in  <hex20>
```

| 键 | 格式 | 大小 |
|---|---|---|
| **`pid`** | 十进制 | — |
| **`state`** | 十进制 | — |
| **`challenge`** | **hex 8** | **8 字节** |
| **`aes_out`** | **hex 16** | **16 字节** |
| **`aes_in`** | **hex 16** | **16 字节** |
| **`hmac_out`** | **hex 20** | **20 字节** |
| **`hmac_in`** | **hex 20** | **20 字节** |

★★ **⇒ 与报告（`nt10.py` 的 `secrets.txt` 7 行）**完全一致** ✓**

### ★★★★★ 503,664 组合零命中

```
"A near-miss against the AuthSession derivation was worth **503,664 combinations
 with zero hits** (tools/lsg_probe/derive_sweep.py)"
        ↓
★★★★★ ⇒ **即：从 AuthSession 派生密钥这条路被彻底排除**
   ⇒ `secrets.txt` 是**唯一能复现客户端密钥的来源**
```

★ **⇒ 与报告 116 第 7 节的"两客户端密钥不同"呼应（不可能有共享值）。**

### ★★★ 路径环境变量

```cpp
std::string lobbySecretsPath()
{
    const auto *path = std::getenv("**OLMOD_LSG_SECRETS**");
    return path && *path ? std::string(path) : std::string("**secrets.txt**");
}
```

★★ **⇒ `OLMOD_*` 累计 **22 个**。**

---

## 二、★★★★★ **`0xC8` 28 字节头与 `0x81` 应答的验证**

### 2.1 ★★★★★ 客户端头校验（第 626–641 行）

```cpp
void LobbyProtocol::processClientHeader(const std::span<const std::uint8_t> frame)
{
    if (frame.size() != **28** || readU32(frame, 0) != **0xC8** || readU32(frame, 4) != **0xC8**)
        throw std::runtime_error("expected 0xC8 client header ACK");

    transcript_.insert(transcript_.end(), frame.begin() + 8, frame.end());
    const auto ack = buildHeaderAck(frame);
    transcript_.insert(transcript_.end(), ack.begin(), ack.end());
    emit(ack);
    phase_ = LobbyPhase::clientAuth;
    report("LSG_CAPTURE client_header=" + hexString(frame));
    report("Accepted LSG client header ACK.");
}
```

★★★ **⇒ 客户端头是 **28 字节**,偏移 0 与 4 **都是 `0xC8`**。**
**⇒ 且 **`transcript_` 只取 `frame.begin() + 8` 之后**（跳过前 8 字节）。**

### ★★★★★ `0x81` 应答的**两版对照**（第 131–157 行，逐字）

```cpp
// OUR VERIFIED 0x81 HEADER ACK -- docs/LSG-我方规格.md section 3, ported from
// lobby_server.py's build_handshake_reply (codol_crypto.py:279-288):
//
//     u32 LE **22** | **0x00** | **0x81** | u32 LE **0xDC** | 8 random bytes | hello[20:28]
//
// The constant above is a captured sample and differs from the verified reply in
// **two bytes and in its tail**: it carries **0xAB at +4** (verified: **0x00**),
// **0xD2 at +6** (verified: **0xDC**), and a **FROZEN nonce tail**
// `71 79 FC B0 85 93 16 51` where the verified server **echoes the client's own
// 8-byte nonce from hello[20:28]**. The captured bytes are kept only as the fallback
// tail for a short hello.
// Measured verified bytes (lobby_srv.log, 2026-10-03 13:57:41):
//     `16 00 00 00 00 81 dc 00 00 00 c1 c0 e5 7b 35 85 0a 46 51 49 dd 31 1f fc 23 ef`
```

### ★★★★★ 两版的完整对照

| 偏移 | **捕获样本** | **验证过的** | 差异 |
|---|---|---|---|
| **0–3** | `16 00 00 00` | `16 00 00 00` | — |
| **4** | ★ **`AB`** | ★★ **`00`** | ★ 不同 |
| **5** | `81` | `81` | — |
| **6** | ★ **`D2`** | ★★ **`DC`** | ★ 不同 |
| **7–9** | `00 00 00` | `00 00 00` | — |
| **10–17** | `70 E2 FD C0 B6 6A 34 92` | ★★★ **`C1 C0 E5 7B 35 85 0A 46`** | ★★ **随机 8 字节** |
| **18–25** | ★★ **`71 79 FC B0 85 93 16 51`**（**冻结**） | ★★★ **`51 49 DD 31 1F FC 23 EF`**（**回显客户端 nonce**） | ★★★ **不同机制** |

★★★ **⇒ 三处差异：**
```
① 偏移 4：`AB` → **`00`**
② 偏移 6：`D2` → **`DC`**
③ 偏移 18–25：**冻结常量** → **回显客户端的 `hello[20:28]`**
```

### ★★★ `buildHeaderAck` 的实现（第 144–157 行）

```cpp
std::array<std::uint8_t, 26> buildHeaderAck(const std::span<const std::uint8_t> hello)
{
    std::array<std::uint8_t, 26> ack{};
    ack[0] = **0x16**;                    // 长度 22
    ack[4] = **0x00**;                    // ★ 验证值
    ack[5] = **0x81**;                    // 类型
    ack[6] = **0xDC**;                    // ★ 验证值
    fillRandom(std::span<std::uint8_t>(ack).subspan(**10**, **8**));   // ★ 8 随机字节
    if (hello.size() >= **28**)
        std::copy_n(hello.begin() + **20**, 8, ack.begin() + **18**);  // ★ 回显
    else
        std::copy(ServerHeaderAck.begin() + 18, ServerHeaderAck.end(), ack.begin() + 18);
    return ack;
}
```

★★★ **⇒ 完整的 26 字节：**
```
`16 00 00 00`（长度 22）+ `00` + `81` + `DC 00 00 00`
+ **8 随机字节**（偏移 10–17）
+ **`hello[20:28]`**（偏移 18–25）
```

---

## 三、★★★★★ **`0x82` 的 authInfo 位布局（bit 83 不对齐）**

### 3.1 ★★★★★ 完整注释（第 77–92 行，逐字）

```cpp
// LAYOUT, from Shared/BitBuffer.cs. The buffer is constructed with
// **dataHasTypeCheckedBit=false**, which prepends one bit and starts reading at bit 1,
// so offsets are relative to authInfo's own bit 0 and **TypeChecked starts FALSE**:
//
//     **serviceId   8 bits**        untagged (TypeChecked false at construction)
//     **unknown     1 bit**         untagged (the caller sets TypeChecked=false for it)
//     **titleId     5 + 32 bits**   tagged   (TypeChecked set true first)
//     **ivSeed      5 + 32 bits**   tagged
//     **authInfoData            1024 bits**
//
// The tag is **5 bits** because `BitBufferDataType::MaxType` is **0x20**. That puts the
// data at **bit 83**, which is **NOT byte-aligned** -- which is exactly why this needs a
// bit reader and cannot be a byte offset eyeballed off a captured frame.
```

### ★★★★★ 完整的位布局

| 字段 | 位宽 | 累计位偏移 | 标记 |
|---|---|---|---|
| **`serviceId`** | **8** | **8** | 无 tag |
| **`unknown`** | **1** | **9** | 无 tag |
| **`titleId`** | **5 + 32 = 37** | **46** | ★ 有 tag |
| **`ivSeed`** | **5 + 32 = 37** | ★★ **83** | ★ 有 tag |
| **`authInfoData`** | **1024** | 83 + 1024 = **1107** | — |

★★★★★ **⇒ 三个精确数字：**
```
**tag = 5 位**（因为 `BitBufferDataType::MaxType` = **`0x20`** = 32 ⇒ 需要 5 位）
数据起点 = **bit 83**
        ↓
★★★ **83 不是 8 的倍数**（83 / 8 = 10.375）
   ⇒ **必须用位读取器,不能用字节偏移**
```

### ★★★★★ `sessionKeyFromClientAuth` 的完整实现（第 94–119 行）

```cpp
std::optional<std::array<std::uint8_t, 24>> sessionKeyFromClientAuth(
    const std::span<const std::uint8_t> frame)
{
    // frame is `[u32 size][0xAB][0x82][authInfo][clientVerify]`; the caller has already
    // checked the two type bytes.
    constexpr std::size_t AuthInfoOffset = **6**;
    constexpr std::size_t AuthInfoBytes = **139**;
    constexpr std::size_t AuthInfoDataBytes = **128**;
    if (frame.size() < AuthInfoOffset + AuthInfoBytes) return std::nullopt;

    AuthInfoBitReader reader(frame.subspan(AuthInfoOffset, AuthInfoBytes));
    if (!reader.skip(**8**) ||                      // serviceId
        !reader.skip(**1**) ||                      // unknown bool
        !reader.skip(TypeTagBits + **32**) ||       // titleId
        !reader.skip(TypeTagBits + **32**))         // ivSeed
    {
        return std::nullopt;
    }

    std::array<std::uint8_t, AuthInfoDataBytes> data{};   // ★ 128 字节
    if (!reader.readBytes(data)) return std::nullopt;

    std::array<std::uint8_t, **24**> key{};
    std::copy_n(data.begin(), key.size(), key.begin());   // ★ 前 24 字节
    return key;
}
```

### ★★★★★ 四个精确常量

| 常量 | 值 | 说明 |
|---|---|---|
| **`AuthInfoOffset`** | **6** | authInfo 在帧里的偏移 |
| **`AuthInfoBytes`** | **139** | authInfo 的总字节数 |
| **`AuthInfoDataBytes`** | **128** | `authInfoData` 的字节数 |
| **session key 长度** | **24** | 取 `authInfoData` 的**前 24 字节** |

★★★ **⇒ 139 字节 vs 1107 位：**
```
**1107 位 / 8 = 138.375** ⇒ 向上取整 **139** 字节 ✓
```

### ★★★★★ "session key 在客户端自己的 auth 帧里"（第 63–75 行，逐字）

```cpp
// THE SESSION KEY IS IN THE CLIENT'S OWN AUTH FRAME. It is not minted here and it is
// not looked up: the auth server issues a **128-byte server ticket** whose **first 24
// bytes are the key**, and the client forwards that ticket verbatim. The C# reference
// implementation this is ported from does exactly one line for it --
// `var sessionKey = authInfoData[..24];` at **LobbyServer/Client.cs:339** -- and its own
// comment says the ticket is "minted and the client forwarded verbatim".
//
// Deriving the keys from this backend's AuthSession instead was **the whole [100] bug**:
// with `OLMOD_CLAIM_LOBBY=1` this backend owns the lobby while the C# AuthServer owns
// auth, so that AuthSession is **empty**, deriveSessionKeys produced the **wrong
// decrypt/HMAC pair**, and the client's first encrypted 0x86 threw in
// processServiceMessage and **dropped the connection**. **Two clients also get DIFFERENT
// keys, so no single shared value could ever have worked.**
```

★★★★★ **⇒ 三个关键事实：**
```
① ★★★ **auth server 发 128 字节 server ticket,前 24 字节就是密钥**
   ⇒ 客户端**逐字转发**（`LobbyServer/Client.cs:339`：`var sessionKey = authInfoData[..24];`）
        ↓
② ★★★ **整个 [100] bug 的根源**：从 AuthSession 派生
   ⇒ 在 `OLMOD_CLAIM_LOBBY=1` 下 AuthSession 是**空的** ⇒ 派生出**错误的密钥对**
   ⇒ 客户端第一个加密 0x86 抛异常 ⇒ **断连**
        ↓
③ ★★★★★ **"Two clients also get DIFFERENT keys, so no single shared value could ever
   have worked."**
```

---

## 四、★★★★★ **`0x83` 必须回显客户端 challenge（两次实测）**

### 4.1 ★★★★★ 完整注释（第 286–310 行，逐字）

```cpp
// LOCAL OVERRIDE (DSH, 2026-10-05) -- WAIT FOR THE CLIENT'S OWN CHALLENGE BEFORE THE 0x83.
//
// THE CLIENT COMPARES THE 0x83 PAYLOAD WITH ITS OWN `sub+0x5FC` VALUE AND ABORTS THE WHOLE
// HANDSHAKE ON A MISMATCH. **Two independent measurements** (client side, n10run logs):
//
//   run2  n10run-20261005-160612.txt:  **5E8=0 C8=1 -> 5E8=2 C8=2**
//                                      [secrets] 快照已写 state=2 challenge=235f79cfe2f3ef15
//                                      **5E8=0 C8=4**          <- rolled back, sockets closed
//         backend sent response_id=**725FFE7FF73D29B6**  (the PREVIOUS session's challenge)
//   run3  n10run-20261005-160719.txt:  **5E8=2 -> 5E8=3 -> 5E8=0 C8=4**
//         backend sent response_id=**72AB8E3A22892AB9**  (the DERIVED fallback, no snapshot at all)
//
// and the reference implementation that DID work does exactly this wait:
//   m3-lobby.stdout.log / re-lobby.out.log:
//     [00:10:23] -> 0x83 (14 字节) = `0a 00 00 00 00 83 f0 43 41 24 48 d7 b2 49`
//                [challenge 来源: 内存快照, **等待 0.45s**]
//     [00:10:23] <- 0x85 (130 字节) 密钥快照还没就绪, 先攒着
//     [00:10:24] [keys] 拿到会话密钥 pid=11620 state=3 challenge=f043412448d7b249
//                ★ 解密成功 #1 ...
//   i.e. lobby_server.py **waits ~0.45 s** for the state-2 snapshot before answering, and the
//   connection then stays up for **minutes** (15:06:25 -> 15:09:36, **87 decrypted frames**).
```

### ★★★★★ 两次失败的完整记录

| run | 状态变化 | backend 发的 `response_id` | 结果 |
|---|---|---|---|
| **run2** | `5E8=0 C8=1` → `5E8=2 C8=2` → ★★ **`5E8=0 C8=4`** | ★ **`725FFE7FF73D29B6`**（**上一轮的 challenge**） | **回滚,套接字关闭** |
| **run3** | `5E8=2` → `5E8=3` → **`5E8=0 C8=4`** | ★ **`72AB8E3A22892AB9`**（**派生回退,无快照**） | 同上 |

★★★★★ **⇒ 三个精确的变量名/值：**
```
**`5E8`** ⇒ 一个状态字（`0` = 失败,`2`/`3` = 进展）
**`C8`**  ⇒ 另一个状态字（`1`/`2` 正常,★ **`4` = 回滚**）
**`sub+0x5FC`** ⇒ 客户端用来比对的自身 challenge 值
        ↓
★★★ ⇒ **`5E8=0 C8=4` 是"握手被客户端中止"的精确签名**
```

### ★★★ 成功的那次（逐字）

```
`[00:10:23] -> 0x83 (14 字节) = `**`0a 00 00 00 00 83 f0 43 41 24 48 d7 b2 49`**`
   [challenge 来源: 内存快照, **等待 0.45s**]
`[00:10:23] <- 0x85 (130 字节) 密钥快照还没就绪, 先攒着`
`[00:10:24] [keys] 拿到会话密钥 pid=11620 state=3 challenge=f043412448d7b249`
   ★ **解密成功 #1 ...**
        ↓
★★★ 连接保持 **15:06:25 → 15:09:36**（**87 个解密帧**）
```

★★★★★ **⇒ 完整的 `0x83` 帧（14 字节）：**
```
`0a 00 00 00`（长度 10）+ `00` + `83` + **8 字节 challenge**
        ↓
★ 而 challenge = **`f043412448d7b249`**（与 `[keys]` 行一致 ✓）
```

★★ **⇒ 且客户端"**密钥快照还没就绪,先攒着**"⇒ 说明客户端**容忍延迟**。**

### ★★★★★ 但**不能在 `0x83` 前等待**（第 686–706 行，逐字）

```cpp
// LOCAL OVERRIDE (DSH, 2026-10-05) -- **DELIBERATELY NO WAIT HERE. READ THIS BEFORE ADDING ONE.**
//
// ...
//   2026-10-05 16:06:36 run, **700 ms wait** before the 0x83 (adoptFreshSnapshot(..., 700)):
//     Connected to LSG/lobby server for formal-zone-lsg.codol.qq.com.
//     LSG snapshot is still the previous session's after waiting; continuing with it ...
//     Completed LSG key exchange.
//     Disconnected from LSG/lobby server for formal-zone-lsg.codol.qq.com.
//   The client **closed the connection itself, without ever sending a 0x85**, and showed
//   `[100] 无法连接大厅服务`. The previous run, which sent the 0x83 **with no delay at all**,
//   got all the way to the client's first 0x85. So **the LSG handshake will not tolerate a
//   delayed 0x83**.
```

★★★★★ **⇒ 一个精确的矛盾与解法：**
```
`waitForFreshChallenge` 需要等 challenge（成功那次等了 **0.45 s**）
        ↓
★★★ 但**在这里等 700 ms ⇒ 客户端直接关闭连接**（"without ever sending a 0x85"）
   ⇒ 显示 **`[100] 无法连接大厅服务`**
        ↓
★★★★★ ⇒ **"the LSG handshake will not tolerate a delayed 0x83"**
        ↓
★★★ 解法：**不在 `0x83` 前等,而是在 HMAC 失败时重读快照并重试同一帧**
   （`processServiceMessage` 里的 `adoptFreshSnapshot`）
```

★★ **⇒ 这是一个**"看起来合理的修复反而更糟"的实测**（与报告 113 的 H2 同类）。**

### ★★★★★ `waitForFreshChallenge` 的实际超时（第 721 行）

```cpp
if (waitForFreshChallenge(keys_, staleSnapshotFingerprint_, **3000**, freshNote))
```

★★★ **⇒ 实际传的是 **3000 ms**（注释里说 0.45 s 是参考实现的值）。**
**⇒ 所以这里**等 3 秒**——与"不能延迟"矛盾?**
**⇒ 但注意：`waitForFreshChallenge` 在**读不到新 challenge 时才等**；若已就绪则**立即返回**。**

★ **⇒ 而 `adoptFreshSnapshot` 在 HMAC 失败路径上等 **2000 ms**（第 373 行）。**

---

## 五、★★★★★ **`0x85` 帧的完整加密格式**

### 5.1 ★★★★★ `encodeEncryptedLobbyMessage`（第 452–495 行）

```cpp
std::vector<std::uint8_t> encodeEncryptedLobbyMessage(
    const std::span<const std::uint8_t> payload,
    const std::span<const std::uint8_t> aesKey,
    const std::span<const std::uint8_t> hmacKey,
    const std::uint32_t sequence,
    const std::span<const std::uint8_t> iv,
    const std::uint8_t messageType)
{
    std::vector<std::uint8_t> plaintext;
    plaintext.reserve(payload.size() + 20);
    appendU32(plaintext, 0);                       // ★ 长度占位
    plaintext.push_back(messageType);              // ★ 类型
    plaintext.insert(plaintext.end(), payload.begin(), payload.end());
    plaintext.resize((plaintext.size() + 15) & ~std::size_t(15));   // ★ 16 字节对齐
    const auto encodedSize = messageType == **0x86**
        ? static_cast<std::uint32_t>(payload.size())
        : static_cast<std::uint32_t>(plaintext.size() - 4);          // ★★ 两个不同公式
    for (unsigned int index = 0; index != 4; ++index)
        plaintext[index] = static_cast<std::uint8_t>(encodedSize >> (index * 8));

    const auto ciphertext = aesCbcEncrypt(plaintext, aesKey, iv);
    std::vector<std::uint8_t> frame;
    frame.reserve(34 + ciphertext.size());
    appendU32(frame, static_cast<std::uint32_t>(**30** + ciphertext.size()));   // ★ 长度
    frame.push_back(**0xAB**);
    frame.push_back(**0x85**);
    appendU32(frame, sequence);
    frame.insert(frame.end(), iv.begin(), iv.end());                 // ★ 16 字节 IV
    frame.insert(frame.end(), ciphertext.begin(), ciphertext.end());
    const auto signature = hmacSha1(frame, hmacKey);
    frame.insert(frame.end(), signature.begin(), signature.begin() + **8**);   // ★ 8 字节 HMAC
    return frame;
}
```

### ★★★★★ 完整的 `0x85` 帧结构

| 偏移 | 大小 | 内容 |
|---|---|---|
| **0–3** | 4 | ★ **长度 = `30 + ciphertext.size()`** |
| **4** | 1 | ★ **`0xAB`** |
| **5** | 1 | ★ **`0x85`** |
| **6–9** | 4 | `sequence` |
| **10–25** | **16** | ★★ **IV** |
| **26–…** | **ciphertext** | ★ **AES-CBC 密文** |
| **末尾 8** | **8** | ★★ **HMAC-SHA1 的前 8 字节** |

★★★ **⇒ 完整算式：**
```
`4（长度）+ 1（AB）+ 1（85）+ 4（seq）+ 16（IV）= **26** 字节头`
`+ ciphertext + 8（HMAC）= **34 + ciphertext**`
        ↓
★★★ ⇒ 而长度字段 = **`30 + ciphertext.size()`** ⇒ `4 + 30 = 34` ✓ **自洽**
```

### ★★★★★ 内层明文的两个长度公式（第 469–479 行，逐字）

```cpp
// MEASURED 2026-10-03, and deliberately NOT changed (docs/LSG-移植差异清单.md
// difference 3). Our Python writes `len(inner)` here (21 for an empty TLV body,
// codol_crypto.py:257) and the client accepts it. The archived real-server frame
// this file's own test reproduces byte-for-byte -- tests/backend/DemonwareTests.cpp
// :2521, decrypted with the test's own keys, see tools/lsg_probe/capture_lenfield.py
// -- carries **0x1C = 28** for that same **21-byte body**, i.e. exactly this expression.
// **Two accepted values for one field means it is not a [100] candidate**, so the
// captured-real-server behaviour (and the byte-for-byte regression) stays.
```

★★★★★ **⇒ 三个精确数字：**
```
Python 写 **`len(inner)` = 21**（空 TLV 体）
真实服务器帧写 **`0x1C = 28`**
        ↓
★★★ ⇒ **同一字段两个值都被接受** ⇒ **"not a [100] candidate"**（不是故障候选）
        ↓
★★★★★ 所以保留**真实服务器的行为**（**字节级回归测试**）
```

★ **⇒ 第 5 条是**"两个值都被接受 ⇒ 不追"的精确判断**（与报告 114 的"权威源码 vs 实测"呼应）。**

### ★★★ `decodeEncryptedLobbyMessage` 的校验（第 497–526 行）

```cpp
if (frame.size() < **50** || readU32(frame, 0) + 4 != frame.size() ||
    frame[4] != 0xAB || frame[5] != 0x85)
    throw std::runtime_error("invalid encrypted lobby frame");

const auto signedSize = frame.size() - **8**;
const auto signature = hmacSha1(frame.first(signedSize), hmacKey);
if (!constantTimeEqual(frame.last(8), std::span(signature).first(8)))
    throw std::runtime_error("**lobby frame HMAC mismatch**");

const auto ciphertext = frame.subspan(**26**, frame.size() - **34**);
if (ciphertext.empty() || ciphertext.size() % **16** != 0)
    throw std::runtime_error("invalid lobby ciphertext length");
const auto plaintext = aesCbcDecrypt(ciphertext, aesKey, frame.subspan(**10**, **16**));
const auto encodedSize = readU32(plaintext, 0);
const auto messageType = plaintext[**4**];
const auto payloadSize = messageType == **0x86** ? encodedSize : encodedSize - 1;
```

★★★ **⇒ 五个精确常量：最小 **50** 字节 / HMAC 尾 **8** / 密文起点 **26** / IV 偏移 **10** / IV 长 **16**。**

★★ **⇒ 且 `constantTimeEqual` 用**常数时间比较**（第 425–435 行）：**
```cpp
std::uint8_t difference{};
for (...) difference |= left[index] ^ right[index];
return difference == 0;
```

---

## 六、★★★★★ **三阶段状态机**

### 6.1 ★★★★★ 完整流程（第 609–624 行 + 各处理器）

```cpp
switch (phase_)
{
    case LobbyPhase::clientHeader:    processClientHeader(frame);    break;
    case LobbyPhase::clientAuth:      processClientAuth(frame);      break;
    case LobbyPhase::established:     processServiceMessage(frame);  break;
}
```

### ★★★★★ 三阶段的完整流程

| 阶段 | 入站 | 出站 | 状态转换 |
|---|---|---|---|
| **`clientHeader`** | ★ `0xC8` 28 字节头 | ★ **`0x81`** 26 字节应答 | → `clientAuth` |
| **`clientAuth`** | ★ `0xAB 0x82` auth 帧 | ★ **`0x83`** 14 字节 | → `established` |
| **`established`** | ★ `0xAB 0x85` 加密帧 | ★ `0x85` 加密应答 + 推送 | — |

★★★ **⇒ 三种帧类型：`0x81`（头应答）/ `0x83`（stage2）/ `0x85`（加密）。**

### ★★★ `receive` 的分帧（第 558–589 行）

```cpp
while (input_.size() >= 4)
{
    const auto payloadSize = readU32(input_, 0);
    if (payloadSize > **MaxFrameSize**) { input_.clear(); report("Rejected oversized LSG frame."); return; }
    // DW3's 0xC8 client header is a **fixed 28-byte record**. Its first dword is a
    // **generation marker**, unlike normal length-prefixed frames.
    const auto frameSize = phase_ == LobbyPhase::clientHeader && payloadSize == **0xC8**
        ? std::size_t{ **28** }
        : static_cast<std::size_t>(payloadSize) + 4;
    if (input_.size() < frameSize) return;
    ...
}
```

★★★★★ **⇒ `0xC8` 的**特殊处理**：**
```
正常帧 ⇒ 长度字段 = **载荷长度** ⇒ 帧长 = `payloadSize + 4`
`0xC8` 头 ⇒ **第一个 dword 是"generation marker",不是长度**
   ⇒ 帧长**固定 28**
        ↓
★★★ ⇒ 这是一个**协议特例**（必须特判）
```

★ **⇒ `MaxFrameSize = **1024 × 1024**` = 1 MB。**

### ★★★ `processFrame` 的零长度特例（第 609–616 行）

```cpp
if (readU32(frame, 0) == 0)
{
    constexpr std::array<std::uint8_t, 4> Zero{};
    emit(Zero);
    return;
}
```

★★ **⇒ 长度字段为 0 时 ⇒ **回 4 个零字节**（保活/心跳?）。**

### ★★★ 推送队列（第 829–854 行）

```cpp
void LobbyProtocol::flushQueuedPushes()
{
    if (phase_ != LobbyPhase::established) return;      // ★ 只在 established 时发

    std::deque<DecodedLobbyMessage> pushes;
    { std::scoped_lock lock(pushMutex_); pushes.swap(queuedPushes_); }
    for (const auto &push : pushes)
    {
        std::array<std::uint8_t, 16> iv{};
        fillRandom(iv);
        const auto encoded = encodeEncryptedLobbyMessage(
            push.payload, keys_.encrypt, keys_.responseHmac, ++outgoingSequence_, iv,
            push.messageType);
        emit(encoded);
        report("LSG_PUSH type=" + std::to_string(push.messageType) + " payload=" + hexString(push.payload));
    }
}
```

★★★ **⇒ 推送在 `takeOutput` 里 flush（第 593 行），且**只在 `established` 阶段**。**

### ★★★★★ `suppressReply` 的最终处置（第 800–810 行）

```cpp
// ★ 2026-10-05 22:5x -- LOCAL OVERRIDE (DSH): "只推不回".
// The Python baseline that reached maps sets `_FLAGS["skip_ack"] = True` in its `0x06/14`
// `mmbook` branch (`lobby_server.py:291`) and then skips the 0x85 reply entirely
// (`:1616-1622`).  See ServiceResponse::suppressReply for the full quote.
if (response->suppressReply)
{
    report("LSG_NO_REPLY service=" + ... + " task=" + ...
        + " -- suppressReply (\"只推不回\", py 原始 _FLAGS[\"skip_ack\"])");
    return;
}
```

★★★ **⇒ `suppressReply` 机制**仍然存在**,但（报告 112）`decodeLocalCommand` **不再设置它**。**
**⇒ 所以这条分支**实际不会触发**（但保留了机制与日志）。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`secrets.txt` 五键映射** | **`decrypt ← aes_out`** / **`requestHmac ← hmac_out`** / **`encrypt ← aes_in`** / **`responseHmac ← hmac_in`** / **`responseId ← challenge`** |
| 2 | ★★★ **交叉命名** | `aes_out`→`decrypt`、`aes_in`→`encrypt`（**从客户端视角命名**） |
| 3 | ★★ 7 行格式 | `pid` / `state` / `challenge`(**hex8**) / `aes_out`(**hex16**) / `aes_in`(**hex16**) / `hmac_out`(**hex20**) / `hmac_in`(**hex20**) |
| 4 | ★★★★★ **503,664 组合零命中** | `tools/lsg_probe/derive_sweep.py` ⇒ **从 AuthSession 派生这条路被彻底排除** |
| 5 | ★★ 路径 | **`OLMOD_LSG_SECRETS`**（默认 `./secrets.txt`）⇒ `OLMOD_*` 累计 **22 个** |
| 6 | ★★★ **`0xC8` 头 = 28 字节** | 偏移 0 与 4 **都是 `0xC8`**；`transcript_` 只取 `frame.begin()+8` 之后 |
| 7 | ★★★★★ **`0x81` 两版三处差异** | 偏移 4：**`AB`→`00`**；偏移 6：**`D2`→`DC`**；偏移 18–25：**冻结常量 → 回显 `hello[20:28]`** |
| 8 | ★★★ `0x81` 的 26 字节 | `16 00 00 00` + `00` + `81` + `DC 00 00 00` + **8 随机** + **`hello[20:28]`** |
| 9 | ★★★★★ **`0x82` 位布局** | `serviceId 8` + `unknown 1` + `titleId 5+32` + `ivSeed 5+32` + `authInfoData 1024` |
| 10 | ★★★★★ **数据起点 = bit 83** | **83 不是 8 的倍数** ⇒ **必须用位读取器**；tag **5 位**（`MaxType` = **`0x20`**） |
| 11 | ★★★ 四个常量 | `AuthInfoOffset` **6** / `AuthInfoBytes` **139** / `AuthInfoDataBytes` **128** / key **24** |
| 12 | ★★★ 139 的由来 | **1107 位 / 8 = 138.375** ⇒ 向上取整 **139** ✓ |
| 13 | ★★★★★ **session key 的来源** | **auth server 发 128 字节 ticket,前 24 字节是密钥**,客户端**逐字转发**（`Client.cs:339`） |
| 14 | ★★★★★ **`[100]` bug 的根源** | 从 AuthSession 派生 ⇒ `OLMOD_CLAIM_LOBBY=1` 下 **AuthSession 为空** ⇒ 错误密钥 ⇒ **断连** |
| 15 | ★★★★★ **"两客户端密钥不同"** | "**no single shared value could ever have worked**" |
| 16 | ★★★★★ **`0x83` 两次失败** | run2：`5E8=0 C8=1`→`5E8=2 C8=2`→**`5E8=0 C8=4`**（发了**上一轮**的 `725FFE7FF73D29B6`）；run3：`5E8=2`→`5E8=3`→**`5E8=0 C8=4`**（发了**派生**的 `72AB8E3A22892AB9`） |
| 17 | ★★★★ **失败签名** | **`5E8=0 C8=4`** = 握手被客户端中止；客户端比对 **`sub+0x5FC`** |
| 18 | ★★★★★ **成功那次** | `0a 00 00 00 00 83 **f0 43 41 24 48 d7 b2 49**`（14 字节）；**等 0.45 s**；连接保持 **15:06:25→15:09:36**（**87 个解密帧**） |
| 19 | ★★★ 客户端容忍 | "**密钥快照还没就绪, 先攒着**" |
| 20 | ★★★★★ **但 0x83 前不能等** | 等 **700 ms** ⇒ 客户端**直接关闭连接**（"without ever sending a 0x85"）⇒ **`[100] 无法连接大厅服务`** |
| 21 | ★★★★★ 结论 | "**the LSG handshake will not tolerate a delayed 0x83**" ⇒ 改在 **HMAC 失败时重读快照并重试** |
| 22 | ★★ 两个超时 | `waitForFreshChallenge` **3000 ms**（就绪则立即返回）/ `adoptFreshSnapshot` **2000 ms** |
| 23 | ★★★★★ **`0x85` 帧结构** | `4(长度=30+ct) + 1(AB) + 1(85) + 4(seq) + 16(IV) + ct + 8(HMAC)` |
| 24 | ★★★ 算式自洽 | `4 + 30 = 34` = `4+1+1+4+16+8` ✓ |
| 25 | ★★★★★ **内层长度两个值** | Python 写 **21**（空 TLV 体）；真实服务器写 **`0x1C = 28`** ⇒ **两个都被接受** ⇒ **"not a [100] candidate"** |
| 26 | ★★★ 解码五常量 | 最小 **50** 字节 / HMAC 尾 **8** / 密文起点 **26** / IV 偏移 **10** / IV 长 **16** |
| 27 | ★★ `constantTimeEqual` | `difference \|= left[i] ^ right[i]` ⇒ **常数时间** |
| 28 | ★★★ **三阶段** | `clientHeader`(`0xC8`/`0x81`) → `clientAuth`(`0x82`/`0x83`) → `established`(`0x85`) |
| 29 | ★★★★★ **`0xC8` 是协议特例** | 第一个 dword 是 **"generation marker"不是长度** ⇒ 帧长**固定 28** |
| 30 | ★★ `MaxFrameSize` | **1 MB** |
| 31 | ★★ 零长度特例 | 长度字段为 0 ⇒ **回 4 个零字节** |
| 32 | ★★★ 推送队列 | 只在 **`established`** 阶段 flush；在 `takeOutput` 里 |
| 33 | ★★★ `suppressReply` | 机制**仍在**,但 `decodeLocalCommand` **不再设置** ⇒ 实际不触发 |

---

## 八、结论

### 1. ★★★★★ **`secrets.txt` 是唯一能复现客户端密钥的来源**（503,664 组合零命中）

★ **⇒ 且五个键有**交叉命名**（`aes_out` → `decrypt`）。**

### 2. ★★★★★ **`0x82` 的 authInfo 数据起点是 bit 83（不对齐）**

★ **⇒ 必须用位读取器；tag 5 位因为 `MaxType = 0x20`。**

### 3. ★★★★★ **session key 就在客户端的 auth 帧里（128 字节 ticket 的前 24 字节）**

★ **⇒ 而从 AuthSession 派生是**整个 `[100]` bug 的根源**（`OLMOD_CLAIM_LOBBY=1` 下为空）。**

### 4. ★★★★★ **`0x83` 必须回显客户端自己的 challenge,但**不能在它之前等待**

```
等待（0.45 s）⇒ 成功（87 个解密帧）
等 700 ms 在 0x83 前 ⇒ **客户端直接关闭连接**
        ↓
★★★ 解法：**在 HMAC 失败时重读快照并重试同一帧**
```

### 5. ★★★★★ **`0x85` 帧的完整结构被还原**（`4+1+1+4+16+ct+8`）

### 6. ★★★★ **内层长度字段有两个都被接受的值**（21 与 28）⇒ 不追

### 7. ★★★★ **`0xC8` 头是协议特例**（第一个 dword 不是长度,帧长固定 28）

### 8. ★★★ **三阶段状态机 + 推送只在 `established`**

---

## 九、下一步

- `LobbyProtocol.cpp` 已全文完成
- `StatsService`（875 行）/ `Profiles2Service`（630 行）/ `ClanService`（623 行）
- `Storage2Service`（450 行）/ `Friends2Service`（325 行）
- `ContentUnlock2Service` / `TencentService` / `TitleUtilitiesService`
- `SharedRoom*` / `Servers.cpp`（624 行）
