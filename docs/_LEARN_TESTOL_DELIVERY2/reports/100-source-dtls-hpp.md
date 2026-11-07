# 学习报告 100（重开）— `qcommon\net_dtls_cod.hpp`（7,620 B / 212 行）

**学习范围**：`game_server\qcommon\net_dtls_cod.hpp` 全文
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录五个重大发现**：①**`bdCommonAddr` 是 67 字节不是 37（"expected DER SEQUENCE"）** ②**完整的 Demonware DTLS 包格式（三种包 + 16 字节头）** ③**密钥派生的 4 个尺寸** ④**密钥刷新的竞态（per-peer 快照）** ⑤**`18` 个 peer 与 `120` 秒会话生命周期**

---

## 一、★★★★★ **`bdCommonAddr` 是 67 字节,不是 37（一个已修正的致命偏移）**

### 1.1 ★★★★★ 完整注释（第 84–88 行，逐字）

```cpp
// 67, not 37. A bdCommonAddr on the wire is 67 bytes; the 37 here was the short form, and
// it makes every field after it 30 bytes early and the whole packet 30 bytes short. The C#
// GameServer hit exactly this and was corrected the same way -- at the old offsets the
// security id came out of the 00FF00FF0000 sentinel run and the ECC parse started
// mid-sentinel, giving "expected DER SEQUENCE".
std::array<std::uint8_t, 67> commonAddress{};
```

### ★★★★★ 完整的因果链

```
① ★★★ **`bdCommonAddr` 在线上是 67 字节**
   而代码里写的是 **37**（"the short form"）
        ↓
② ★★★ 后果：**其后每个字段都提前 30 字节**,**整个包短 30 字节**
        ↓
③ ★★★★★ **具体症状（逐字）**：
   · **`securityId` 从 `00FF00FF0000` 哨兵串里取出来**
   · **ECC 解析从哨兵中间开始** ⇒ 报 **"expected DER SEQUENCE"**
        ↓
④ ★★★ **C# GameServer 撞过同一个错,并以同样方式修正**
```

★★★ **⇒ 这是**一个 30 字节偏移错误制造的一整串假发现**（与 memory 里"一处 6 字节偏移错误
制造了一批假发现"**完全同类**）。**

★★ **⇒ 且给出了**可识别的指纹**：**
```
若看到 **`"expected DER SEQUENCE"`** ⇒ **首先怀疑 `bdCommonAddr` 的长度**
若看到 **`securityId` 里有 `00FF00FF0000`** ⇒ **同样是偏移错误**
```

### ★★★★★ `DtlsCookieEchoPacket` 的精确布局（第 79–94 行）

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0** | 2 | `verificationTag` |
| **2** | 2 | `counter` |
| **4** | 2 | `clientTag` |
| ★ **6** | **67** | ★★★ **`commonAddress`（`bdCommonAddr`）** |
| **73** | 8 | `securityId` |
| **81** | **100** | `publicKey` |
| **181** | — | （合计） |

★★★★★ **⇒ 总长 = 2+2+2+67+8+100 = **181 字节**。**
**⇒ 若用 37 ⇒ 总长 **151**,且**后面全错位 30 字节** ✓ 与注释完全一致。**

---

## 二、★★★★★ **三种 Demonware DTLS 包**

### 2.1 ★★★★★ `DtlsDataPacket`（第 43–67 行）

```cpp
struct DtlsDataPacket
{
    static constexpr std::uint8_t PacketType = **0x06**;
    static constexpr std::uint8_t Version    = **0x02**;
    static constexpr std::size_t HeaderSize  = **16**;

    std::uint16_t verificationTag{};
    std::uint16_t sequenceNumber{};
    std::array<std::uint8_t, 8> authenticator{};
    std::uint16_t encryptedSize{};
    std::vector<std::uint8_t> payload;
};
```

### ★★★★★ 16 字节头的精确布局

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0** | 1 | ★ `PacketType = 0x06` |
| **1** | 1 | ★ `Version = 0x02` |
| **2** | 2 | `verificationTag` |
| **4** | 2 | `sequenceNumber` |
| **6** | **8** | ★★ **`authenticator`**（HMAC 截断到 8 字节） |
| **14** | 2 | `encryptedSize` |
| **16** | … | `payload` |

★★★ **⇒ `1 + 1 + 2 + 2 + 8 + 2 = **16** ✓（`HeaderSize = 16`）**

★★ **⇒ `authenticator` 只有 **8 字节** ⇒ 是 **HMAC-SHA1 截断到 8 字节**（因为 `hmacKey` 是 24 字节 = SHA1 长度）。**

### ★★★ 三个包类型

| 结构 | 说明 |
|---|---|
| **`DtlsDataPacket`** | ★ `PacketType 0x06` / `Version 0x02` / 头 **16** 字节 |
| **`DtlsInitPacket`** | `verificationTag` + `counter` + `initTag` + `securityId[8]` |
| **`DtlsCookieEchoPacket`** | ★★ 见第一节（**181 字节**） |

### ★★★ `DtlsInitPacket` 的布局（第 69–77 行）

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0** | 2 | `verificationTag` |
| **2** | 2 | `counter` |
| **4** | 2 | `initTag` |
| **6** | 8 | `securityId` |
| **14** | — | 合计 |

★ **⇒ `DtlsInitPacket` = **14 字节**。**

---

## 三、★★★★★ **密钥派生的 4 个精确尺寸**

### 3.1 ★★★ `DtlsSessionConfig`（第 15–29 行）

```cpp
class DtlsSessionConfig
{
public:
    static constexpr std::size_t SecurityKeySize = **16**;
    bool configureFromDemonwareDescriptor(std::span<const std::uint8_t> descriptor);
    ...
    std::array<std::uint8_t, SecurityKeySize> securityKey_{};
};
```

★★ **⇒ `securityKey` = **16 字节**（AES-128 密钥长度）。**

★★ **⇒ `configureFromDemonwareDescriptor` ⇒ 密钥来自 **Demonware 描述符**（不是硬编码）。**

### 3.2 ★★★★★ `DtlsSessionKeys`（第 31–41 行）

```cpp
struct DtlsSessionKeys
{
    std::array<std::uint8_t, **20**> digest{};              // ★ SHA1 长度

    static DtlsSessionKeys derive(std::span<const std::uint8_t> sharedMaterial);
    [[nodiscard]] std::array<std::uint8_t, **16**> aesKey() const;
    [[nodiscard]] std::array<std::uint8_t, **24**> hmacKey() const;
    [[nodiscard]] std::array<std::uint8_t, **16**> iv(
        std::uint16_t sequenceNumber,
        std::uint16_t verificationTag) const;
};
```

### ★★★★★ 四个尺寸的完整表

| 项 | 尺寸 | 说明 |
|---|---|---|
| **`digest`** | ★ **20** | **SHA-1 输出**（160 位） |
| **`aesKey()`** | ★ **16** | **AES-128** 密钥 |
| **`hmacKey()`** | ★★ **24** | ★ 不是 20 ⇒ **HMAC-SHA1 但密钥 24 字节** |
| **`iv(...)`** | ★ **16** | **AES 块大小**（128 位） |

★★★ **⇒ 第 3 条值得注意：`hmacKey` 是 **24** 字节而不是 20。**
**⇒ 若 `digest` 只有 20 字节,24 字节的 `hmacKey` 必然**从别处扩展**（可能重复填充）。**
**⇒ 这解释了为什么 `authenticator` 是 8 字节（HMAC 截断）。**

### ★★★ `iv` 的两个参数（第 38–40 行）

```cpp
[[nodiscard]] std::array<std::uint8_t, 16> iv(
    std::uint16_t sequenceNumber,
    std::uint16_t verificationTag) const;
```

★★★ **⇒ IV 由 **`sequenceNumber` + `verificationTag`** 派生 ⇒ 每包唯一。**
**⇒ 与 `DtlsDataPacket` 的 `verificationTag` / `sequenceNumber` **两个头字段**对应。**

### ★★★ `derive(sharedMaterial)`（第 35 行）

★ **⇒ 从 `sharedMaterial` 派生** ⇒ 与 `DtlsKeyPair::sharedMaterial(...)` 的输出对接。**

---

## 四、★★★★★ **ECDH 密钥交换的 4 个尺寸**

### 4.1 ★★★ `DtlsKeyPair`（第 96–115 行）

```cpp
class DtlsKeyPair
{
public:
    DtlsKeyPair();
    explicit DtlsKeyPair(std::span<const std::uint8_t> privateScalar);
    ...
    [[nodiscard]] std::array<std::uint8_t, **100**> publicKey() const;
    [[nodiscard]] std::array<std::uint8_t, **44**> sharedMaterial(
        std::span<const std::uint8_t, **100**> peerPublicKey,
        std::span<const std::uint8_t, **16**> securityKey) const;
};
```

### ★★★★★ 四个尺寸

| 项 | 尺寸 | 说明 |
|---|---|---|
| **`publicKey()`** | ★★ **100** | 公钥（**与 `DtlsCookieEchoPacket::publicKey[100]` 一致**） |
| **`peerPublicKey`** | **100** | 对端公钥（同尺寸） |
| **`securityKey`** | **16** | 与 `DtlsSessionConfig::SecurityKeySize` 一致 |
| **`sharedMaterial()`** | ★★ **44** | ★ 共享材料输出 |

★★★ **⇒ `100` 字节的公钥 + `44` 字节的共享材料 ⇒ 一个**非常规的 ECC 尺寸**：**
```
**100 字节公钥** ⇒ 若是不压缩点：`0x04 || X || Y`
   ⇒ (100 − 1) / 2 = **49.5** ⇒ 不是整数
   ⇒ ★★ 若是 **`0x04 || X || Y` + 填充** ⇒ 或**压缩点 + 填充**
        ↓
★ 可能：**secp384r1**（48 字节坐标）⇒ `1 + 48 + 48 = **97**` ⇒ 再加 3 字节填充 = **100**
   ⇒ 或 **secp521r1**（66 字节坐标）⇒ `1 + 66 + 66 = 133` > 100
        ↓
★★★ ⇒ 最可能 **secp384r1**（97 → 100 含填充）
   ⇒ 而 `44` 字节共享材料 = **X 坐标 48 字节的截断** 或 **SHA-384 输出 48 的截断**
        ↓
★ **未实测,记录为推断**
```

★★ **⇒ `publicKey` 的 100 字节与 `DtlsCookieEchoPacket::publicKey[100]` **完全一致** ✓**

### ★★★ 三处"100 字节公钥"的一致性

| 位置 | 尺寸 |
|---|---|
| `DtlsCookieEchoPacket::publicKey` | **100** |
| `DtlsKeyPair::publicKey()` | **100** |
| `DtlsKeyPair::sharedMaterial(peerPublicKey)` | **100** |

★★★ **⇒ 三处一致 ⇒ 这是一个**硬性的线上格式常量**。**

---

## 五、★★★★★ **三个协议函数**

### 5.1 ★★★ 完整签名（第 117–126 行）

```cpp
[[nodiscard]] std::vector<std::uint8_t> NET_DtlsNatIntroReply(
    std::span<const std::uint8_t> packet);

[[nodiscard]] std::vector<std::uint8_t> NET_DtlsInitAck(
    std::span<const std::uint8_t> packet,
    PeerAddress peer,
    std::uint16_t serverTag,
    std::uint32_t timestamp);

[[nodiscard]] std::vector<std::uint8_t> NET_DtlsCookieAck(
    std::span<const std::uint8_t> packet,
    std::span<const std::uint8_t, 100> serverPublicKey);
```

### ★★★★★ 三个握手阶段

```
① **`NET_DtlsNatIntroReply`**   ⇒ **NAT 介绍应答**（只有包,无额外参数）
        ↓
② **`NET_DtlsInitAck`**         ⇒ **INIT 应答**（需要 peer + serverTag + **timestamp**）
        ↓
③ **`NET_DtlsCookieAck`**       ⇒ **COOKIE 应答**（需要 **100 字节服务端公钥**）
```

★★ **⇒ 与 `DtlsPeerState` 三态**完全对应**：**
```cpp
enum class DtlsPeerState : std::uint8_t
{
    Empty,          // ① NAT intro 之前
    CookieIssued,   // ② INIT 已应答,COOKIE 已发
    Established,    // ③ COOKIE_ECHO 已验,会话建立
};
```

### ★★★ `DtlsPacketResultKind` 的 4 种（第 135–141 行）

```cpp
enum class DtlsPacketResultKind : std::uint8_t
{
    Ignored,            // 忽略
    Reply,              // ★ 需要回复
    AuthenticatedData,  // ★★ 认证通过的数据
    Rejected,           // 拒绝
};
```

### ★★★ `DtlsPacketResult`（第 143–149 行）

```cpp
struct DtlsPacketResult
{
    DtlsPacketResultKind kind{ DtlsPacketResultKind::Ignored };
    std::vector<std::uint8_t> reply;        // ★ 要发回的字节
    std::vector<std::uint8_t> plaintext;    // ★ 解密后的明文
    std::string reason;                     // ★ 诊断
};
```

---

## 六、★★★★★ **密钥刷新的竞态（per-peer 快照）**

### 6.1 ★★★★★ 完整注释（第 184–187 行，逐字）

```cpp
// The Demonware descriptor may be refreshed while multiple peers
// are completing DTLS. Keep the key selected at INIT per peer;
// using the mutable global descriptor during COOKIE_ECHO races
// the two clients onto different key material.
std::array<std::uint8_t, DtlsSessionConfig::SecurityKeySize> securityKey{};
std::array<std::uint8_t, DtlsSessionConfig::SecurityKeySize> previousSecurityKey{};
bool hasPreviousSecurityKey{};
```

### ★★★★★ 完整的竞态描述

```
① ★★★ **Demonware 描述符可能在多个 peer 完成 DTLS 时被刷新**
        ↓
② ★★★ 若在 `COOKIE_ECHO` 阶段**读可变的全局描述符**
   ⇒ **两个客户端会被竞态到不同的密钥材料**
        ↓
★★★ 修复：**在 `INIT` 阶段就把密钥快照到每个 peer**
   ⇒ 后续 `COOKIE_ECHO` 用 **per-peer 的快照**
```

★★ **⇒ 这是**"全局可变状态 + 并发握手"的经典竞态**。**
**⇒ 且保留 `previousSecurityKey` + `hasPreviousSecurityKey` ⇒ 支持**密钥轮换时的平滑过渡**。**

### ★★★★★ `PeerSession` 的完整字段（第 175–198 行）

```cpp
struct PeerSession
{
    bool valid{};
    PeerAddress peer{};
    DtlsPeerState state{ DtlsPeerState::Empty };
    std::uint32_t lastActivityTime{};
    std::uint16_t serverTag{};
    std::uint16_t clientTag{};
    std::array<std::uint8_t, 8> securityId{};
    std::array<std::uint8_t, 16> securityKey{};          // ★ 当前
    std::array<std::uint8_t, 16> previousSecurityKey{};  // ★ 上一把
    bool hasPreviousSecurityKey{};
    std::optional<DtlsKeyPair> keyPair;                  // ★ ECDH 密钥对
    std::optional<DtlsSessionKeys> keys;                 // ★ 派生的会话密钥
    std::optional<DtlsSessionKeys> previousKeys;         // ★ 上一组
    bool usingPreviousKeys{};                            // ★ 当前用哪组
    std::uint16_t lastClientSequence{};                  // ★ 防重放
    std::uint16_t nextServerSequence{ 1 };               // ★ 从 1 开始
    bool clientSequenceReceived{};
};
```

★★★ **⇒ 三个"双份"设计：**
```
① `securityKey` / `previousSecurityKey`     ⇒ 密钥轮换
② `keys` / `previousKeys`                   ⇒ 会话密钥轮换
③ `lastClientSequence` / `nextServerSequence` ⇒ 序列号（**16 位**）
```

★★ **⇒ `nextServerSequence` 从 **1** 开始（与报告 099 的 `outgoingSequence{ 1 }` **同一约定**）。**

### ★★★★★ `DtlsPeerSystem` 的构造参数（第 154–156 行）

```cpp
explicit DtlsPeerSystem(
    std::size_t maxPeers = **18**,
    std::uint32_t sessionLifetimeMilliseconds = **120'000**);
```

★★★★★ **⇒ 两个默认值：**
```
**`maxPeers = 18`**          ⇒ ✓ **与报告 093 的 `MaximumSessionMembers = 18`
                              和报告 071 的 `MaximumGameClients (18)` 完全一致**
                               ⇒ ★★★ **第四次跨文件验证**
**`sessionLifetimeMilliseconds = 120,000`** ⇒ **2 分钟**
```

★ **⇒ 第 1 条是**第四次**在 18 这个数字上的交叉确认（093 / 071 / 090 / 100）。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`bdCommonAddr` = 67 字节** | **不是 37**；用 37 ⇒ **其后全提前 30 字节、整包短 30** |
| 2 | ★★★★★ **症状指纹** | `securityId` 从 **`00FF00FF0000`** 哨兵里取出；ECC 解析从哨兵中间开始 ⇒ **`"expected DER SEQUENCE"`** |
| 3 | ★★ 前例 | **C# GameServer 撞过同一个错,以同样方式修正** |
| 4 | ★★★★★ **`DtlsCookieEchoPacket` = 181 字节** | `verificationTag(2) + counter(2) + clientTag(2) + **commonAddress(67)** + securityId(8) + publicKey(100)` |
| 5 | ★★★★★ **`DtlsDataPacket` 16 字节头** | `PacketType(1)=**0x06** + Version(1)=**0x02** + verificationTag(2) + sequenceNumber(2) + **authenticator(8)** + encryptedSize(2)` |
| 6 | ★★ `authenticator` = 8 字节 | HMAC 截断 |
| 7 | ★★ `DtlsInitPacket` = 14 字节 | `verificationTag(2) + counter(2) + initTag(2) + securityId(8)` |
| 8 | ★★★ **密钥 4 尺寸** | `digest` **20**（SHA-1）/ `aesKey` **16**（AES-128）/ `hmacKey` ★ **24**（不是 20）/ `iv` **16** |
| 9 | ★★★ `iv` 两参数 | `sequenceNumber` + `verificationTag` ⇒ **每包唯一** |
| 10 | ★★ `securityKey` = 16 | 来自 **Demonware 描述符**（`configureFromDemonwareDescriptor`） |
| 11 | ★★★★★ **ECDH 4 尺寸** | `publicKey` **100** / `peerPublicKey` **100** / `securityKey` **16** / `sharedMaterial` ★ **44** |
| 12 | ★★ 100 字节的一致性 | `DtlsCookieEchoPacket::publicKey` / `DtlsKeyPair::publicKey()` / `sharedMaterial(peerPublicKey)` **三处都是 100** |
| 13 | ★★★ 100 字节的推断 | 若 `0x04||X||Y` ⇒ (100−1)/2 = 49.5 不整 ⇒ 最可能 **secp384r1**（97 + 3 填充）；★ **未实测** |
| 14 | ★★★ **三阶段握手** | `NET_DtlsNatIntroReply` → `NET_DtlsInitAck`（需 serverTag + timestamp）→ `NET_DtlsCookieAck`（需 **100 字节服务端公钥**） |
| 15 | ★★ `DtlsPeerState` 三态 | **`Empty` / `CookieIssued` / `Established`** ⇒ 与三阶段对应 |
| 16 | ★★ `DtlsPacketResultKind` 4 种 | `Ignored` / `Reply` / **`AuthenticatedData`** / `Rejected` |
| 17 | ★★★★★ **密钥刷新竞态** | 描述符可能被刷新 ⇒ 若 `COOKIE_ECHO` 读全局 ⇒ **两个客户端竞态到不同密钥材料** ⇒ 修复：**`INIT` 时快照到 per-peer** |
| 18 | ★★★ 三处"双份"设计 | `securityKey`/`previous` · `keys`/`previousKeys` · `lastClientSequence`/`nextServerSequence` |
| 19 | ★★ `nextServerSequence` | 从 **1** 开始（与 099 的 `outgoingSequence{1}` 同约定） |
| 20 | ★★★★★ **`maxPeers = 18`** | ✓ 与 093 的 `MaximumSessionMembers` / 071 的 `MaximumGameClients` / 090 一致 ⇒ **第四次交叉验证** |
| 21 | ★★ 会话生命周期 | **120,000 ms = 2 分钟** |

---

## 八、结论

### 1. ★★★★★ **`bdCommonAddr` 67 vs 37 是一个 30 字节偏移错误,有精确的症状指纹**

```
用 37 ⇒ 其后全提前 30 字节、整包短 30
        ↓
★★★ 症状：`securityId` 从 **`00FF00FF0000`** 哨兵里取出,
         ECC 解析从哨兵中间开始 ⇒ **`"expected DER SEQUENCE"`**
        ↓
★★★★★ ⇒ **看到 `"expected DER SEQUENCE"` 首先怀疑 `bdCommonAddr` 长度**
```

### 2. ★★★★★ **Demonware DTLS 的三阶段握手与三种包被完整还原**

```
**`DtlsInitPacket` 14 B** → **`DtlsCookieEchoPacket` 181 B** → **`DtlsDataPacket` 16 B 头 + 载荷**
        ↓
★ `DtlsDataPacket` = `0x06` + `0x02` + tag + seq + **8 字节 authenticator** + size
```

### 3. ★★★★★ **密钥刷新的竞态是"全局可变状态 + 并发握手"的经典案例**

★ **⇒ 修复：**`INIT` 时快照到 per-peer**,后续 `COOKIE_ECHO` 用快照。**

### 4. ★★★★★ **`maxPeers = 18` 是 `18` 这个数字的第四次交叉确认**

★ **⇒ 与 `MaximumSessionMembers`（093）/ `MaximumGameClients`（071）/ 插件服务数（090）一致。**

### 5. ★★★ **ECDH 的 100 字节公钥与 44 字节共享材料**（最可能 secp384r1,未实测）

### 6. ★★★ **`hmacKey` 是 24 字节而不是 20**（与 SHA-1 的 20 不符 ⇒ 有扩展）

---

## 九、下一步

- `qcommon\net_dtls_cod.cpp`（34,426 B / **765 行**）—— 实现层（含实际的 ECC 与 HMAC 运算）
- `qcommon\msg_mp.cpp` / `.hpp` / `com_math.hpp` / `net_types.hpp`
