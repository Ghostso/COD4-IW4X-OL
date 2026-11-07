# 学习报告 101（重开）— `qcommon\net_dtls_cod.cpp`（34,426 B / 831 行）

**学习范围**：`game_server\qcommon\net_dtls_cod.cpp` 全文（**831 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录六个重大发现**：①**`securityKey` 是常量 `0x01×16`（三条独立证据定因）** ②**ECC 是 P-224（不是 P-384）** ③**`sharedMaterial` = ECDH 28 字节 + securityKey 16 字节** ④**AES-128-CTR 用 ECB 手工实现（小端计数器）** ⑤**cookie echo 支持 219/189 两种尺寸** ⑥**密钥轮换的双组回落**

---

## 一、★★★★★ **`securityKey` 是常量 `0x01 × 16`（三条独立证据）**

### 1.1 ★★★★★ 完整注释（第 180–194 行，逐字）

```cpp
// ★★★ 2026-10-07 10:0x -- **DTLS securityKey 改为常量 0x01*16**（进图最后一步的定因；单变量）。
//
// 定因（三条独立证据，全部本轮实测）：
//   ① 离线复算命中（`99-Tmp\dtls_crack.py`）：拿 d33 现场（established 行带出的
//      ECDH28 + 失败包全文）逐一试候选密钥，**只有 `01*16` 与失败包 MAC
//      `fd43e8589e49bdec`（seq=17, tag=040d, 54B）逐字节吻合**；记录密钥、
//      `secrets.txt` 的 aes/hmac、challenge 等全部候选 0 命中。
//   ② C# 参考战斗服原文（`00-reference\third-party\reference\CodolLocalBattleServer.cs:418`）：
//      `byte[] securityKey=new byte[16]; for(...) securityKey[i]=1;`
//      `exchange.DeriveTransportKey(publicKey, securityKey);` —— 同一常量约定。
//   ③ d33 判据日志：tag 检查通过、仅 HMAC 不过 ⇒ 除 securityKey 外全部正确。
//
// 历史：此前按"记录里 16 字节 `Session.SecurityKey`"装填（同 `keyFingerprint=` 日志），
// 与客户端实际使用的常量不符 ⇒ 每个 type=6 数据包都被 `DTLS data authentication failed`
// 拒绝 ⇒ 卡"等待连接"。descriptor 现在只作为"已配置"的触发器使用（形状不参与）。
```

### ★★★★★ 三条独立证据的完整拆解

| # | 证据 | 精确数据 |
|---|---|---|
| **1** | ★★★ **离线复算命中**（`99-Tmp\dtls_crack.py`） | 拿 d33 现场（**ECDH28 + 失败包全文**）逐一试候选 ⇒ **只有 `01*16` 与失败包 MAC `fd43e8589e49bdec`（seq=17, tag=040d, 54B）逐字节吻合**；记录密钥 / `secrets.txt` 的 aes/hmac / challenge **全部 0 命中** |
| **2** | ★★ **C# 参考实现原文**（`CodolLocalBattleServer.cs:418`） | `byte[] securityKey=new byte[16]; for(...) securityKey[i]=1;` + `exchange.DeriveTransportKey(publicKey, securityKey);` ⇒ **同一常量约定** |
| **3** | ★★★ **d33 判据日志** | **tag 检查通过、仅 HMAC 不过** ⇒ **除 `securityKey` 外全部正确** |

### ★★★★★ 修复前后的症状对比

```
修复前：按"记录里 16 字节 `Session.SecurityKey`"装填
        ↓
★★★ 每个 **type=6** 数据包都被 `DTLS data authentication failed` 拒绝
   ⇒ 卡在"**等待连接**"
        ↓
修复后：`securityKey_.fill(0x01)` ⇒ 通过
```

### ★★★★★ 修复后的实现（第 195–198 行）

```cpp
(void)descriptor;                  // ★ descriptor 只作"已配置"的触发器
securityKey_.fill(0x01);           // ★★★ 常量
configured_ = true;
return true;
```

★★★ **⇒ `descriptor` 的**形状完全不参与**（`(void)descriptor`）⇒ 只当"已配置"开关。**

---

## 二、★★★★★ **ECC 是 P-224（不是 P-384）**

### 2.1 ★★★★★ 完整的曲线证据

```cpp
EC_KEY_new_by_curve_name(**NID_secp224r1**)            // 第 396 / 406 行
...
if (privateScalar.empty() || privateScalar.size() > **28**)  // 第 404 行
...
std::array<std::uint8_t, **28**> raw{};                 // encodeInteger，第 161 行
...
if (keySize.size() != 1 || keySize[0] != **28**)        // 第 472 行
    throw std::invalid_argument("CODOL DTLS public key is not P-224");
...
const auto size = ECDH_compute_key(output.data(), **28**, point, impl_->key, nullptr);  // 第 497 行
if (size != **28**) throw ...
```

★★★ **⇒ 五处一致：`NID_secp224r1` / 私钥 ≤ 28 字节 / 坐标 28 字节 / `keySize[0] == 28` / ECDH 输出 28 字节。**

★★★★★ **⇒ **P-224（secp224r1）**,不是 P-384。**
**⇒ 报告 100 推断"最可能 secp384r1"**是错的,已由实现证伪。**

### ★★★ 为什么公钥是 100 字节（P-224 的 28 字节坐标）

```
`publicKey()` 的构造（第 449–458 行）：
    content = { **0x03, 0x02, 0x07, 0x00, 0x02, 0x01, 0x1C** }   // 7 字节前缀
            + encodedX                                           // DER INTEGER
            + encodedY                                           // DER INTEGER
    output[0] = **0x30**（DER SEQUENCE）
    output[1] = content.size()
        ↓
★★★ 每个坐标：`0x02` + 长度 + 28 字节 = **30 字节**（若最高位为 1 则 31,含前导 0）
        ↓
★★★ 总计 ≈ 2 + 7 + 30 + 30 = **69**（典型）
   ⇒ 上限 **98**（`if (content.size() > 98) throw`）
   ⇒ 字段固定 **100 字节**（剩余补零）
        ↓
★★★★★ ⇒ **100 是字段宽度,不是 DER 长度**
```

★★ **⇒ 前缀 `{0x03, 0x02, 0x07, 0x00, 0x02, 0x01, 0x1C}` 的语义：**
```
`0x03 0x02 0x07 0x00`  ⇒ **BIT STRING**（2 字节内容：`07 00`）
`0x02 0x01 0x1C`       ⇒ **INTEGER 1 字节 = 0x1C = 28**
        ↓
★★★ ⇒ **`0x1C = 28` = P-224 的坐标字节数** ✓
   ⇒ 这是一个**自定义的"密钥格式声明"**
```

### ★★★ `encodeInteger` 的 DER 编码（第 159–172 行）

```cpp
std::array<std::uint8_t, 28> raw{};
BN_bn2binpad(value, raw.data(), 28);                    // ★ 固定 28 字节
std::vector<std::uint8_t> encoded{ **0x02** };           // INTEGER
const auto leadingZero = (raw.front() & 0x80) != 0;     // ★ 最高位为 1 ⇒ 需要前导 0
encoded.push_back(static_cast<std::uint8_t>(raw.size() + leadingZero));
if (leadingZero) encoded.push_back(0);
encoded.insert(encoded.end(), raw.begin(), raw.end());
```

★★★ **⇒ 标准 DER INTEGER 编码：最高位为 1 时**补前导 0**（防止被当成负数）。**
**⇒ 所以坐标可能是 **30 或 31 字节**。**

---

## 三、★★★★★ **`sharedMaterial` = ECDH 28 + securityKey 16 = 44**

### 3.1 ★★★★★ 完整实现（第 461–503 行）

```cpp
std::array<std::uint8_t, 44> DtlsKeyPair::sharedMaterial(
    const std::span<const std::uint8_t, 100> peerPublicKey,
    const std::span<const std::uint8_t, 16> securityKey) const
{
    // ① 解析对端公钥：0x30 (SEQUENCE) → 0x03 (BIT STRING) → 0x02 (28) → 0x02 (X) → 0x02 (Y)
    const auto [sequence, ignored] = readTlv(peerPublicKey, 0, **0x30**);
    auto [format, offset] = readTlv(sequence, 0, **0x03**);
    if (format.size() != 2 || format[0] != **0x07** || format[1] != **0x00**)
        throw std::invalid_argument("CODOL DTLS public key has an unknown format");
    auto [keySize, next] = readTlv(sequence, offset, **0x02**);
    if (keySize.size() != 1 || keySize[0] != **28**)
        throw std::invalid_argument("CODOL DTLS public key is not P-224");
    auto [xBytes, afterX] = readTlv(sequence, offset, **0x02**);
    auto [yBytes, afterY]  = readTlv(sequence, afterX, **0x02**);
    // ② 验证点在曲线上
    EC_POINT_is_on_curve(group, point, context) == 1;
    // ③ ECDH
    const auto size = ECDH_compute_key(output.data(), **28**, point, impl_->key, nullptr);
    if (size != 28) throw ...;
    // ④ 尾部拼上 securityKey
    std::copy(securityKey.begin(), securityKey.end(), output.begin() + **28**);
    return output;      // ★ 28 + 16 = 44
}
```

### ★★★★★ **44 = 28 + 16** 的精确分解

```
`output[0..27]`  ⇒ **ECDH 共享密钥（P-224 = 28 字节）**
`output[28..43]` ⇒ **`securityKey`（16 字节,即 `0x01 × 16`）**
        ↓
★★★★★ **总计 44 字节** ✓
```

★★★ **⇒ 这解释了报告 100 的"`sharedMaterial` 是 44 字节"：**
```
**44 = P-224 的 ECDH 输出（28）+ securityKey（16）**
        ↓
★ 而不是"P-384 坐标截断"
```

### ★★★ `readTlv` 的严格校验（第 145–157 行）

```cpp
if (offset + 2 > data.size() || data[offset] != expectedTag || data[offset + 1] & 0x80)
    throw std::invalid_argument("invalid CODOL DTLS public-key TLV");
const auto size = static_cast<std::size_t>(data[offset + 1]);
const auto start = offset + 2;
if (start + size > data.size())
    throw std::invalid_argument("truncated CODOL DTLS public-key TLV");
```

★★★ **⇒ 三条校验：**
```
① 标签必须匹配
② ★★ **`data[offset+1] & 0x80` ⇒ 拒绝长格式长度**（只支持单字节长度）
③ 长度不能超出数据
```

★ **⇒ 第 ② 条 ⇒ **只支持 < 128 字节的 TLV**（P-224 的 30 字节满足）。**
**⇒ 报错串 **`"invalid CODOL DTLS public-key TLV"`** ⇒ 与报告 090 在插件字符串面发现的**完全一致** ✓**

---

## 四、★★★★★ **AES-128-CTR 用 ECB 手工实现（小端计数器）**

### 4.1 ★★★★★ 完整实现（第 99–143 行）

```cpp
std::vector<std::uint8_t> aesCtrLittleEndian(
    const std::span<const std::uint8_t> input,
    const std::span<const std::uint8_t, 16> key,
    const std::span<const std::uint8_t, 16> iv)
{
    if (input.empty()) return {};
    const auto blockCount = (input.size() + 15) / 16;
    std::vector<std::uint8_t> counters(blockCount * 16);
    std::array<std::uint8_t, 16> counter{};
    std::copy(iv.begin(), iv.end(), counter.begin());
    for (std::size_t block = 0; block < blockCount; ++block)
    {
        std::copy(counter.begin(), counter.end(), counters.begin() + block * 16);
        // ★★ 小端递增：从低字节开始进位
        for (auto &byte : counter)
        {
            if (++byte != 0) break;
        }
    }

    const auto context = EVP_CIPHER_CTX_new();
    std::vector<std::uint8_t> stream(counters.size());
    const auto ok = EVP_EncryptInit_ex(context, **EVP_aes_128_ecb()**, nullptr, key.data(), nullptr) &&
        EVP_CIPHER_CTX_set_padding(context, **0**) &&
        EVP_EncryptUpdate(context, stream.data(), &written, counters.data(), ...) &&
        EVP_EncryptFinal_ex(context, stream.data() + written, &finalized);
    ...
    for (std::size_t index = 0; index < input.size(); ++index)
        output[index] = input[index] ^ stream[index];
}
```

### ★★★★★ 三个精确的实现选择

```
① ★★★ **用 ECB 加密计数器块,再异或** ⇒ 这就是 **CTR 模式的手工实现**
   （OpenSSL 有 `EVP_aes_128_ctr`,但这里刻意手写）
        ↓
② ★★★★ **计数器是**小端递增**：
   `for (auto &byte : counter) { if (++byte != 0) break; }`
   ⇒ **从 `counter[0]`（最低字节）开始进位**
   ⇒ 与标准 CTR（大端）**相反**
        ↓
③ ★★ `EVP_CIPHER_CTX_set_padding(context, **0**)` ⇒ **关闭填充**
   （否则 ECB 会给最后一块补 PKCS#7）
```

★★★ **⇒ 第 ② 条是**一个关键的兼容性细节**：**
```
标准 CTR ⇒ 计数器**大端**递增（从最后字节进位）
本实现   ⇒ 计数器**小端**递增（从第一字节进位）
        ↓
★★★ ⇒ 若用标准 CTR 实现,加密结果**完全不同**
   ⇒ 这解释了函数名为什么叫 `aesCtrLittleEndian`
```

★ **⇒ 第 ① 条的手写理由：OpenSSL 的 CTR 用大端计数器 ⇒ 无法直接用。**

### ★★★★★ IV 的派生（第 240–252 行）

```cpp
std::array<std::uint8_t, 16> DtlsSessionKeys::iv(
    const std::uint16_t sequenceNumber,
    const std::uint16_t verificationTag) const
{
    std::vector<std::uint8_t> seed;
    seed.reserve(6);
    appendU32(seed, sequenceNumber);      // ★ 4 字节（u16 扩展成 u32）
    appendU16(seed, verificationTag);     // ★ 2 字节
    const auto digestValue = sha1(seed);  // ★ 6 字节输入 → SHA1
    std::array<std::uint8_t, 16> result{};
    std::copy_n(digestValue.begin(), result.size(), result.begin());   // ★ 取前 16
    return result;
}
```

★★★ **⇒ IV = `SHA1(sequenceNumber(u32 LE) || verificationTag(u16 LE))` 的前 16 字节。**

### ★★★ 密钥派生的完整链（第 218–238 行）

```cpp
DtlsSessionKeys DtlsSessionKeys::derive(const std::span<const std::uint8_t> sharedMaterial)
{
    if (sharedMaterial.size() != **44**)
        throw std::invalid_argument("CODOL DTLS shared material must be 44 bytes");
    return { .digest = **sha1(sharedMaterial)** };     // ★ digest = SHA1(44 字节)
}

std::array<std::uint8_t, 16> DtlsSessionKeys::aesKey() const
{
    std::copy_n(digest.begin(), **16**, result.begin());   // ★ 前 16 字节
}

std::array<std::uint8_t, 24> DtlsSessionKeys::hmacKey() const
{
    std::copy(digest.begin(), digest.end(), result.begin());   // ★ 20 字节 + 4 字节零填充
}
```

★★★★★ **⇒ `hmacKey` 的 24 字节之谜解开了：**
```
`digest` = **20 字节**（SHA1）
        ↓
`aesKey()`  = `digest[0..15]`  ⇒ **16 字节**
`hmacKey()` = `digest[0..19]` + **4 字节零** ⇒ **24 字节**
        ↓
★★★ ⇒ 报告 100 的疑问（"hmacKey 是 24 而不是 20"）的答案：
   **数组声明为 24,但只填前 20,后 4 字节保持零**
   ⇒ ★ 所以 **HMAC 的密钥实际上是 20 字节 + 4 个零**
```

★★ **⇒ 这**不影响 HMAC 结果**（HMAC 会把短密钥补零到块大小），但**密钥长度参数是 24**。**

---

## 五、★★★★★ **`DtlsDataPacket` 的认证与加密范围**

### 5.1 ★★★★★ `authenticatedBytes()`（第 269–278 行）

```cpp
std::vector<std::uint8_t> output{ PacketType, Version };   // ★ 2 字节
appendU16(output, verificationTag);                        // ★ 2
appendU16(output, sequenceNumber);                         // ★ 2
appendU16(output, encryptedSize);                          // ★ 2
output.insert(output.end(), payload.begin(), payload.end()); // ★ 全部 payload
```

★★★★★ **⇒ 被认证的字节 = `type + version + tag + seq + size + 全部 payload`（**不含 authenticator 本身**）。**
**⇒ 共 `2+2+2+2 = 8` 字节头 + payload。**

★★ **⇒ 与 `HeaderSize = 16` 的差别：**16 − 8 = **8 字节正是 `authenticator`**（不参与认证）。**

### ★★★ `verify`（第 280–284 行）

```cpp
const auto expected = hmacSha1(authenticatedBytes(), keys.hmacKey());
return **CRYPTO_memcmp**(expected.data(), authenticator.data(), authenticator.size()) == 0;
```

★★ **⇒ 用 `CRYPTO_memcmp`（常数时间比较）⇒ 防时序攻击。**
**⇒ 且只比**前 8 字节**（`authenticator.size() == 8`）。**

### ★★★★★ `decrypt` 的**加密前缀 + 明文后缀**（第 286–298 行）

```cpp
auto output = aesCtrLittleEndian(
    std::span(payload).**first(encryptedSize)**,   // ★ 只加密前 encryptedSize 字节
    key, ivValue);
output.insert(output.end(), payload.begin() + encryptedSize, payload.end());  // ★ 后缀原样
```

★★★★★ **⇒ 一个**部分加密**的设计：**
```
`payload[0 .. encryptedSize-1]` ⇒ **加密**
`payload[encryptedSize .. end]`  ⇒ ★★★ **明文（原样附加）**
        ↓
★★★ ⇒ 且 `parse` 校验 `encryptedSize <= payload.size()`（第 264 行）
```

★★ **⇒ 这意味着**一条 DTLS 数据包可以"头部加密 + 尾部明文"**。**
**⇒ 可能的用途：尾部是**不需要保密的元数据**（如校验或填充）。**

### ★★★ `build` 的顺序（第 300–327 行）

```cpp
DtlsDataPacket candidate{
    .verificationTag = verificationTag,
    .sequenceNumber = sequenceNumber,
    .encryptedSize = static_cast<std::uint16_t>(plaintext.size()),   // ★ 全部加密
    .payload = aesCtrLittleEndian(plaintext, key, ivValue),
};
const auto signature = hmacSha1(candidate.authenticatedBytes(), keys.hmacKey());
std::copy_n(signature.begin(), **candidate.authenticator.size()**, candidate.authenticator.begin());
```

★★ **⇒ 发送侧 `encryptedSize = plaintext.size()` ⇒ **全部加密**（没有明文后缀）。**
**⇒ 即：**接收侧支持明文后缀,但发送侧从不产生它**。**

---

## 六、★★★★★ **四个包的精确格式（实现层）**

### 6.1 ★★★★★ `DtlsInitPacket::parse`（第 329–340 行）

```cpp
if (packet.size() != **16** || packet[0] != **0x01** || packet[1] != **0x02**)
    throw std::invalid_argument("not a supported CODOL DTLS init packet");
result = {
    .verificationTag = readU16(packet, **2**),
    .counter         = readU16(packet, **4**),
    .initTag         = readU16(packet, **6**),
};
std::copy_n(packet.begin() + **8**, 8, result.securityId.begin());
```

★★★ **⇒ `DtlsInitPacket` 实际是 **16 字节**（不是报告 100 推的 14）：**
```
`type(1)=0x01 + version(1)=0x02 + verificationTag(2) + counter(2) + initTag(2) + securityId(8)`
= **16** ✓
```

★★ **⇒ 报告 100 的 14 字节**少算了 `type + version` 2 字节**，已更正。**

### ★★★★★ `DtlsCookieEchoPacket::parse` 的**双尺寸支持**（第 342–381 行）

```cpp
// THE PACKET SIZE FOLLOWS THE ADDRESS THE LOBBY ADVERTISED. A bdCommonAddr is 67 bytes on
// the wire, but an older session record carried the 37-byte short form, and the client
// echoes back whatever it was given -- so both **219** and **189** are real and the offsets
// after the address move with it. Deriving them from the size keeps the captured
// **189-byte** fixture parsing while a live out.exe client's **219-byte** echo also works.
//
// Getting this wrong is not a clean failure: at the short offsets the security id comes out
// of the 00FF00FF0000 sentinel run and the ECC parse starts mid-sentinel, which surfaces as
// "expected DER SEQUENCE" rather than as a length problem.
constexpr std::size_t LongAddressSize  = **67**;
constexpr std::size_t ShortAddressSize = **37**;
constexpr std::size_t AddressOffset    = **44**;
constexpr std::size_t SecurityIdSize   = **8**;
constexpr std::size_t PublicKeySize    = **100**;
```

### ★★★★★ 两个精确的包尺寸

| 形式 | 算式 | **总长** |
|---|---|---|
| **长地址** | `44 + 67 + 8 + 100` | ★★ **219** |
| **短地址** | `44 + 37 + 8 + 100` | ★★ **189** |

★★★★★ **⇒ 219 与 189 都**真实存在**（客户端回显它收到的形式）。**
**⇒ 且 `AddressOffset = **44**` ⇒ 地址之前有 **44 字节**的头。**

### ★★★★★ 44 字节头的分解（据 parse 的读取顺序）

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0** | 1 | `type = 0x03` |
| **1** | 1 | `version = 0x02` |
| **2** | 2 | `verificationTag` |
| **4** | 2 | `counter` |
| **6** | 2 | ★★ **必须是 `0x02 0x02`**（校验 `packet[6] == 0x02 && packet[7] == 0x02`） |
| **8** | 2 | `clientTag` |
| **10** | **34** | ★★★ **未使用/保留的 34 字节**（44 − 10 = 34） |
| **44** | 67/37 | `commonAddress` |
| **44+A** | 8 | `securityId` |
| **44+A+8** | 100 | `publicKey` |

★★★ **⇒ 偏移 10–43 的 **34 字节**在 parse 里**完全没被读**（只是跳过）。**
**⇒ 而 `packet[6..7] == 0x02 0x02` 是一个**魔数校验**。**

### ★★★ 三种请求包的 `type` / `version` 对

| 包 | `packet[0]` | `packet[1]` |
|---|---|---|
| **NAT intro** | **`0x0D`**（请求）/ **`0x0C`**（应答） | 任意（`readU16(packet,1) >= 2`） |
| **INIT** | **`0x01`** | **`0x02`** |
| **COOKIE_ECHO** | **`0x03`** | **`0x02`** |
| **DATA** | **`0x06`** | **`0x02`** |

### ★★★★★ 三个应答包的精确构造

#### ① `NET_DtlsNatIntroReply`（第 505–513 行）

```cpp
if (packet.size() != **29** || packet[0] != **0x0D** || readU16(packet, 1) < 2)
    return {};
auto output = std::vector(packet.begin(), packet.end());
output[0] = **0x0C**;      // ★ 只改第一个字节
```

★★★ **⇒ NAT intro 请求是 **29 字节**,应答是**同样的 29 字节,只把 `0x0D` 改成 `0x0C`**。**

#### ② `NET_DtlsInitAck`（第 515–538 行）

```cpp
std::vector<std::uint8_t> output{ **0x02, 0x02** };
appendU16(output, init.initTag);
appendU16(output, 0);
appendU32(output, timestamp);
appendU32(output, 0);
appendU16(output, serverTag);      // ★ 出现两次
appendU16(output, serverTag);      // ★
appendU16(output, init.initTag);   // ★ 回显
appendU16(output, 0);
appendU16(output, 0);
appendIpv4(output, peer.ipv4);
appendU16(output, peer.port);
output.insert(output.end(), init.securityId.begin(), init.securityId.end());
```

★★★ **⇒ INIT_ACK = `0x02 0x02` + 若干字段 + **IPv4 + port** + securityId(8)。**
**⇒ 且 `serverTag` **连续写两次**（可能是有意的双字段或历史遗留）。**

★★ **⇒ `if (!serverTag) throw` ⇒ **serverTag 必须非零**。**
**⇒ 而 `NET_DtlsPacket` 里：`session->serverTag = entropy ^ (entropy >> 16); if (!serverTag) serverTag = 1;`**

#### ③ `NET_DtlsCookieAck`（第 540–551 行）

```cpp
std::vector<std::uint8_t> output{ **0x04, 0x02** };
appendU16(output, echo.clientTag);
appendU16(output, 0);
output.insert(output.end(), serverPublicKey.begin(), serverPublicKey.end());  // ★ 100 字节
output.insert(output.end(), echo.securityId.begin(), echo.securityId.end());  // ★ 8 字节
```

★★★ **⇒ COOKIE_ACK = `0x04 0x02` + clientTag(2) + 0 + **公钥(100)** + securityId(8) = **114 字节**。**

---

## 七、★★★★★ **握手状态机与密钥轮换**

### 7.1 ★★★★★ 完整的 `NET_DtlsPacket` 分派（第 565–740 行）

```
`packet[0] == 0x0D`（NAT intro）
    ⇒ 回复 `NET_DtlsNatIntroReply`（29 字节,`0x0C` 开头）
        ↓
`packet[0] == 0x01`（INIT）
    ⇒ `allocateSession(peer)`（满则拒 "DTLS peer slots are full"）
    ⇒ `*session = {}`（★ 完全重置）
    ⇒ `state = CookieIssued`
    ⇒ **快照 `securityKey`**（+ `previousSecurityKey` 若不同）
    ⇒ `serverTag = entropy ^ (entropy >> 16)`，为 0 则取 1
    ⇒ `keyPair.emplace()`（★ 生成 P-224 密钥对）
    ⇒ 回复 `NET_DtlsInitAck`
        ↓
`packet[0] == 0x03`（COOKIE_ECHO）
    ⇒ 必须已有 `CookieIssued` 会话且 `keyPair`
    ⇒ 校验 `verificationTag == serverTag` 且 `clientTag == clientTag` 且 `securityId` 相同
    ⇒ `sharedMaterial(echo.publicKey, session->securityKey)` ⇒ `keys = derive(...)`
    ⇒ ★ 若有 `previousSecurityKey` ⇒ 也算一组 `previousKeys`
    ⇒ `state = Established`
    ⇒ `nextServerSequence = 1`
    ⇒ 回复 `NET_DtlsCookieAck`
    ⇒ ★★★ **`.reason` 带出 `skey= / shared= / cli=` 的十六进制**（调试用）
        ↓
`packet[0] == 0x06`（DATA）
    ⇒ 必须 `Established` 且 `keys`
    ⇒ 校验 `verificationTag == serverTag`
    ⇒ `verify(*keys)`；失败则试 `verify(*previousKeys)` ⇒ **成功则切换到 previous**
    ⇒ 序列号防重放（见下）
    ⇒ 返回 `AuthenticatedData` + `decrypt`
```

### ★★★★★ 序列号防重放的精确判据（第 712–723 行）

```cpp
if (session->clientSequenceReceived)
{
    const auto delta = static_cast<std::uint16_t>(
        data.sequenceNumber - session->lastClientSequence);
    if (**!delta** || **delta >= 0x8000**)
        return Rejected("DTLS data sequence was replayed or stale");
}
```

★★★★★ **⇒ 两条规则（16 位环形序列）：**
```
① `delta == 0`    ⇒ **重放**（同一序列号）
② `delta >= 0x8000` ⇒ ★★★ **过期**（在环上"往回"超过一半）
        ↓
★★★ ⇒ 即：**只接受 `1 <= delta <= 0x7FFF` 的新包**
   ⇒ 允许**乱序**（最多向前 32,767）
   ⇒ 拒绝**重放**与**太旧**
```

★ **⇒ 这是**16 位序列号的经典窗口判据**（无显式窗口,靠"半环"分界）。**

### ★★★ 密钥轮换的三层回落（第 697–711 行）

```cpp
if (!data.verify(*session->keys))
{
    if (!session->previousKeys || !data.verify(*session->previousKeys))
    {
        return Rejected("DTLS data authentication failed (hmac pkt=" + toHex(packet) +
                        " skey=" + toHex(session->securityKey) + ")");
    }
    session->keys = std::move(session->previousKeys);
    session->previousKeys.reset();
    session->usingPreviousKeys = true;
}
```

★★★ **⇒ 三层：**
```
① 当前 `keys` 验 ⇒ 通过
② 否则试 `previousKeys` ⇒ 通过则**永久切换到 previous**（`keys = previousKeys`）
③ 都失败 ⇒ 拒绝,且**报错带出完整包十六进制 + securityKey**
```

★★ **⇒ 第 ③ 条的报错串 `toHex(packet)` ⇒ **把整包十六进制打进日志**（便于离线定因）。**
**⇒ 这正是报告 101 第一节那三条证据能成立的原因（日志里带全了现场）。**

### ★★★ `rememberSecurityKey` 的双组保留（第 754–767 行）

```cpp
if (hasLastSecurityKey_ && std::equal(securityKey.begin(), ..., lastSecurityKey_.begin()))
    return;                                  // ★ 相同 ⇒ 不动
if (hasLastSecurityKey_)
{
    previousSecurityKey_ = lastSecurityKey_;
    hasPreviousSecurityKey_ = true;
}
std::copy(securityKey.begin(), ..., lastSecurityKey_.begin());
```

★★★ **⇒ 只保留**最近两组**：**
```
新密钥来了 ⇒ 旧密钥进 `previousSecurityKey_`
        ↓
★★★ 理由（第 575–577 行）："CODOL may **refresh ConfigureSession per native client**.
 Keep the **two most recent** descriptor keys so peers whose **INIT raced that refresh**
 can still authenticate their first data packet."
```

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`securityKey` = `0x01 × 16`** | 三条独立证据：①离线复算（`dtls_crack.py`,MAC **`fd43e8589e49bdec`**,seq=17, tag=040d, 54B）②C# 参考 `CodolLocalBattleServer.cs:418` ③d33 日志（tag 过、仅 HMAC 不过） |
| 2 | ★★★ 修复前的症状 | 每个 **type=6** 包被 `DTLS data authentication failed` 拒绝 ⇒ 卡"**等待连接**" |
| 3 | ★★ `descriptor` 的角色 | **只作"已配置"触发器**（`(void)descriptor`） |
| 4 | ★★★★★ **ECC = P-224（`NID_secp224r1`）** | 五处一致：私钥 ≤**28** / 坐标 **28** / `keySize[0]==28` / ECDH 输出 **28** ⇒ ★ **证伪报告 100 的 P-384 推断** |
| 5 | ★★★ **公钥 100 字节是字段宽度** | DER 实际 ≈ **69**,上限 **98**（`if > 98 throw`），剩余补零 |
| 6 | ★★★ **公钥前缀** | `{0x03,0x02,0x07,0x00,0x02,0x01,**0x1C**}` ⇒ `0x1C = 28` = **P-224 坐标字节数** |
| 7 | ★★ `encodeInteger` | 标准 DER INTEGER；最高位为 1 时**补前导 0** ⇒ 坐标 **30 或 31** 字节 |
| 8 | ★★★★★ **`sharedMaterial` = 44** | **ECDH 28（P-224）+ `securityKey` 16** ⇒ ★ 解开报告 100 的疑问 |
| 9 | ★★★ `readTlv` 三条校验 | 标签匹配 / ★ **拒绝长格式长度（`& 0x80`）** / 长度不越界 ⇒ 报错串 **`"invalid CODOL DTLS public-key TLV"`** ✓ 与报告 090 一致 |
| 10 | ★★★★★ **AES-128-CTR 手写实现** | 用 **`EVP_aes_128_ecb`** 加密计数器块再异或；★ **计数器小端递增**（从 `counter[0]` 进位）；`set_padding(0)` |
| 11 | ★★★★ **小端计数器是关键** | 标准 CTR 是大端 ⇒ 用 OpenSSL 的 `EVP_aes_128_ctr` **结果完全不同** ⇒ 故函数名 `aesCtrLittleEndian` |
| 12 | ★★★ **IV 派生** | **`SHA1(sequenceNumber(u32 LE) \|\| verificationTag(u16 LE))` 的前 16 字节** |
| 13 | ★★★★★ **密钥派生链** | `digest = SHA1(44 字节)`；`aesKey = digest[0..15]`（16）；**`hmacKey = digest[0..19] + 4 字节零`（24）** ⇒ ★ 解开报告 100 的 24 之谜 |
| 14 | ★★★★★ **认证范围** | `type + version + tag + seq + size + 全部 payload`（**8 字节头 + payload**），**不含 authenticator** |
| 15 | ★★ `verify` | **`CRYPTO_memcmp`**（常数时间）只比**前 8 字节** |
| 16 | ★★★★★ **`decrypt` 的部分加密** | `payload[0..encryptedSize-1]` 加密；**`payload[encryptedSize..]` 原样明文附加**；但 `build` 侧 `encryptedSize = plaintext.size()` ⇒ **发送侧从不产生明文后缀** |
| 17 | ★★★ **`DtlsInitPacket` 实际 16 字节** | `0x01 0x02 + tag(2) + counter(2) + initTag(2) + securityId(8)` ⇒ ★ **更正报告 100 的 14 字节** |
| 18 | ★★★★★ **cookie echo 双尺寸** | 长 **219**（67 字节地址）/ 短 **189**（37 字节地址）；`AddressOffset = 44` |
| 19 | ★★★ **44 字节头** | `type(1)+ver(1)+tag(2)+counter(2)+`**`0x02 0x02`(2)**`+clientTag(2)+`**34 字节未使用** |
| 20 | ★★★ 四种包的 type/version | NAT intro **0x0D→0x0C** / INIT **0x01/0x02** / COOKIE_ECHO **0x03/0x02** / DATA **0x06/0x02** |
| 21 | ★★★ **NAT intro 29 字节** | 应答 = **同 29 字节,只改首字节 `0x0D`→`0x0C`** |
| 22 | ★★ **INIT_ACK** | `0x02 0x02` + … + **IPv4 + port** + securityId(8)；★ `serverTag` **连写两次** |
| 23 | ★★ **COOKIE_ACK = 114 字节** | `0x04 0x02` + clientTag(2) + 0 + **公钥(100)** + securityId(8) |
| 24 | ★★★★★ **序列号防重放** | `delta == 0` ⇒ 重放；`delta >= 0x8000` ⇒ 过期 ⇒ **只接受 `1..0x7FFF`**（允许乱序最多 32,767） |
| 25 | ★★★ 密钥轮换三层 | 当前 keys → `previousKeys`（成功则**永久切换**）→ 拒绝（**报错带完整包十六进制 + securityKey**） |
| 26 | ★★ `rememberSecurityKey` | 只保留**最近两组**（理由：ConfigureSession 可能被刷新,INIT 竞态的 peer 仍需验首个数据包） |
| 27 | ★★★ 调试串 | `established skey=… shared=… cli=…`（**这是那三条证据能成立的原因**） |

---

## 九、结论

### 1. ★★★★★ **`securityKey` 是常量 `0x01 × 16`,有三条独立证据**

```
① **离线复算**：只有 `01*16` 与失败包 MAC `fd43e8589e49bdec` 逐字节吻合
② **C# 参考实现**：`for(...) securityKey[i]=1;`
③ **d33 日志**：tag 过、仅 HMAC 不过 ⇒ 除 securityKey 外全对
        ↓
★★★ 修复前：每个 type=6 包都被拒 ⇒ **卡"等待连接"**
```

### 2. ★★★★★ **ECC 是 P-224,不是 P-384**（证伪报告 100 的推断）

### 3. ★★★★★ **两个"尺寸之谜"都被解开**

```
`sharedMaterial = 44`  ⇒ **ECDH 28（P-224）+ securityKey 16**
`hmacKey = 24`         ⇒ **SHA1 的 20 字节 + 4 字节零**
        ↓
★ 且 `publicKey = 100` ⇒ **字段宽度**,DER 实际 ≈ 69（上限 98）
```

### 4. ★★★★★ **AES-128-CTR 是手写的,且计数器小端递增**

★ **⇒ 这是与标准 CTR 的**唯一但决定性**的差异（用 OpenSSL 的 CTR 结果完全不同）。**

### 5. ★★★★ **cookie echo 支持 219/189 双尺寸**（因为客户端回显它收到的地址形式）

### 6. ★★★★ **序列号防重放用"半环"判据**（`1 ≤ delta ≤ 0x7FFF`）

### 7. ★★★ **密钥轮换的三层回落 + 只保留最近两组**

### 8. ★★★ **调试日志带出 `skey=/shared=/cli=` 与完整包十六进制**（这正是定因能成功的原因）

---

## 十、下一步

- `qcommon\msg_mp.cpp`（27 行）/ `.hpp`（40 行）/ `com_math.hpp`（22 行）/ `net_types.hpp`（12 行）
- 然后 `backend\Demonware\`（52 文件 / 549,733 B）
