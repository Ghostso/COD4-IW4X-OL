# 425 · **"证据只有在下一场游戏产生它时才存在"** —— `sv_client_mp.cpp` 的连接层：OOB 握手、`ProfileStats` 的 `27×1238`、以及 trace 默认开

## 一、范围

本报告学习 `sv_client_mp.cpp` 1–420 行（`SV_SnapshotAssemblyFailureName`、OOB 协议、`ProfileStats` 分块、`mr` 菜单响应）。

## 二、**"trace 默认开，因为证据只有在下一场游戏产生它时才存在"**（本组最重要的一段）

### 2.1 那段

```php
// ---- Scoreboard-downlink trace (ticket 20261011-27000, section B) ----
//
// The producer at queueScoreboardResponse() has no logging at all, which
// is why "TAB shows nothing" could not be attributed to the server or the
// client from a live log. The trace is ON by default -- the evidence only
// exists if the next game session produces it -- and bounded, because the
// trigger is a client reliable 's' plus the match-end pushes: a client
// that re-sent 's' every frame would otherwise flood the log. Set
// OLMOD_SCOREBOARD_TRACE=0 to silence it.
constexpr std::uint32_t ScoreboardTraceLineBudget = 200;
```

### 2.2 二十层

```text
1. **`queueScoreboardResponse()` 的生产者【完全没有日志**】**
2. ⇒ **⇒ 那就是为什么"TAB 什么也不显示"【不能从一份实机日志里归因**】**
3. ⇒ **到服务器还是到客户端**
4. ⇒ **⇒ trace **默认开**】
5. ⇒ **因为【证据【只有在下一场游戏产生它时才存在**】】**
6. ⇒ **而它是【有界的**】**
7. ⇒ **因为触发器是一个客户端的可靠 `s` 加比赛末的推送**
8. ⇒ **一个【每帧重发 `s`**】的客户端【否则会淹没日志**】**
9. ⇒ **⇒ 预算 `200` 行**
10. ⇒ **`OLMOD_SCOREBOARD_TRACE=0` 静默它**
```

### 2.3 ⭐⭐⭐ **"证据只有在下一场游戏产生它时才存在"**

**✅ 这是本报告里**最重要的一条"取证的时间性"**。**

**⇒ 三层**：
```text
若 trace 默认关 ⇒ **下一场不产生日志**
⇒ **而那时用户再报告 ⇒ 【又要等一场**】
⇒ **⇒ 所以【默认开是唯一能【在故障发生时**】有证据的做法**
```

**✅ 与 §418 的"事后在这个服务器自己的录制 demo 里测量"**同族（**第三次"证据必须在发生时捕获"）。

**⇒ 三层**：
```text
§402  **`PREMATCH|` 从 `INF` 提到 `Warn`**（因为 `warn` 下不可见）
§418  **事后在录制 demo 里测量**（因为改动当时没测）
§425  **trace 默认开**（因为证据只有在下一场产生）
⇒ **⇒ 三次"取证的时间窗**】
```

**✅ ⭐⭐⭐ **一个"取证时间窗"的三例表**。

### 2.4 而**"有界，因为一个每帧重发 `s` 的客户端会淹没日志"**

**⇒ 六层**：
```text
1. **有界 ⇒ `200` 行**
2. ⇒ **因为触发器是【客户端可靠 `s`**】**
3. ⇒ **⇒ 而一个【每帧重发**】的客户端会【淹没**】日志**
4. ⇒ **⇒ 所以【"默认开 + 有界"**】是一个组合
5. ⇒ **而到预算时【记一行 `trace-budget-exhausted`**】**
6. ⇒ **⇒ 所以【"用完"本身是可见的**】**
```

**✅ ⭐⭐ **"用完本身是可见的"** —— 与 §409 的"日志停滞 `LOGSTALL`"**互补。

**⇒ 三层**：
```text
§409  太多 ⇒ **`LOGSTALL ... prefix=SDTRACE|advance-blocked`**（**系统层面的停滞**）
§425  太多 ⇒ **`trace-budget-exhausted lines=200`**（**应用层面的自限**）
⇒ **⇒ 两个层次，一个是被动发现，一个是主动声明**
```

**✅ ⭐⭐ **一个"日志自限"的实例**。

**⚠ 而"`std::atomic<uint32_t> written` + `fetch_add`"⇒ **一个无锁计数器**。**

**⇒ 三层**：
```text
`fetch_add(1)` ⇒ **原子递增**
`index > budget` ⇒ **静默丢弃**
`index == budget` ⇒ **记一行**
⇒ **⇒ 所以【恰好 `201` 行输出**】（`0..199` 是 `200` 行正文 + `200` 是宣告）
```

**✅ 一个**精确的计数**。

## 三、**`ProfileStats` 的 `27 × 1238`**（本组第二重要）

### 3.1 那段

```cpp
constexpr std::uint8_t OobPrefix[]{ 0xFF, 0xFF, 0xFF, 0xFF };
constexpr std::uint8_t ProfileStatsPrefix[]{
    0xFF, 0xFF, 0xFF, 0xFF, 's', 't', 'a', 't', 's', 0,
};
constexpr std::size_t ProfileStatsChunkCount = 27;
constexpr std::size_t ProfileStatsChunkSize = 1238;
```

### 3.2 十四层

```text
1. **OOB 前缀 = `0xFF 0xFF 0xFF 0xFF`**（**四字节**）
2. ⇒ **那是 Quake 系的【带外**】标记**
3. ⇒ **而 `ProfileStats` 的前缀是【OOB + `"stats\0"`**】
4. ⇒ **⇒ 所以【`stats` 是一个 OOB 请求**】
5. ⇒ **分块：`27` 块 × `1238` 字节**
6. ⇒ **⇒ 总共 `33426` 字节**
7. ⇒ **而 `27 × 1238 = 33426`**
```

**⇒ 五层**：
```text
`27` 个块
`1238` 字节/块
⇒ **⇒ 而 `1238` 是一个【刻意的**】值**（**不是 `1024` 或 `1200`**）
```

**⚠ 而"`1238`"⇒ **为什么这个数？**

**⇒ 三层**：
```text
若 MTU = `1264`（常见）
则 `1238 + 26`（IP/UDP 头）= `1264`
⇒ **⇒ 所以 `1238` 可能是【MTU 减去头**】
```

**✅ 一个**可推导的解释**（推断，需标注）。

### 3.3 而**"`stats` 请求会触发 27 个分块"**

**⇒ 四层**：
```text
1. **客户端发 OOB `stats` 请求**
2. ⇒ **服务器回【`27` 个 OOB 包**】**
3. ⇒ **⇒ 所以【这是一个【分片协议**】**
4. ⇒ **而每一片都是独立的 OOB 包**（**没有序列号**）
```

**⚠ 而"没有序列号"⇒ **所以顺序由 UDP 保证？不，UDP 不保证。**

**⇒ 三层**：
```text
若分片【有序**】⇒ 重排会破坏数据
若分片【各自独立**】⇒ **一个丢失 = 一个块缺失**
⇒ **⇒ 所以【这个协议依赖【客户端重试**】或【容忍缺失**】
```

**✅ 一个**未闭合的设计问题**。

## 四、**`isLanPeer` 的五个网段**（本组第三重要）

```cpp
bool isLanPeer(const PeerAddress peer)
{
    const auto first = static_cast<std::uint8_t>(peer.ipv4 >> 24);
    const auto second = static_cast<std::uint8_t>(peer.ipv4 >> 16);
    return first == 10 || first == 127 ||
        (first == 169 && second == 254) ||
        (first == 172 && second >= 16 && second <= 31) ||
        (first == 192 && second == 168);
}
```

**⇒ 十层**：
```text
1. **`10.x.x.x`** ⇒ RFC1918 私有
2. ⇒ **`127.x.x.x`** ⇒ loopback
3. ⇒ **`169.254.x.x`** ⇒ link-local（**APIPA**）
4. ⇒ **`172.16..31.x.x`** ⇒ RFC1918 私有
5. ⇒ **`192.168.x.x`** ⇒ RFC1918 私有
6. ⇒ **⇒ 五个网段 = 完整的私有 + 环回 + 链路本地**
7. ⇒ **用于【LAN 客户端识别**】（**可能是放宽的认证或更高的速率**）
```

**✅ 与 §422 的"两扇电动门不是两个 `10000` 的购买"**不同（这是**一个网络层判据**）。

**⚠ 而"`first == 127`"⇒ **回环**。**

**✅ 与项目记忆的"`iips.ini` 指向不可达的 `10.231.2.181`"**——**`10.x` 在这个清单里。**

## 五、**`mix32` 的哈希**

```cpp
std::uint32_t mix32(std::uint32_t value)
{
    value ^= value >> 16;
    value *= 0x7FEB352Du;
    value ^= value >> 15;
    value *= 0x846CA68Bu;
    value ^= value >> 16;
    return value;
}
```

**⇒ 六层**：
```text
1. **两轮 `xor-shift + multiply`**
2. ⇒ **常数 `0x7FEB352D` 与 `0x846CA68B`**
3. ⇒ **⇒ 这是【`lowbias32`**】哈希（**一个已知的良好 32 位混合器**）
4. ⇒ **两次乘法的低位熵低 ⇒ 所以先 `>> 16`**
5. ⇒ **⇒ 一个【标准的 finalizer**】
```

**✅ 与 §425 二 的"`challengeDiagnostics` 的 `unordered_map<uint64, uint8>`"**配合（**可能用于 challenge 生成**）。

## 六、**`parseUserInfo` 的 `\key\value\` 格式**

```cpp
std::optional<std::unordered_map<std::string, std::string>> parseUserInfo(
    const std::string_view userInfo)
{
    if (userInfo.empty() || userInfo.front() != '\\' || userInfo.size() > 1024)
        return std::nullopt;

    std::unordered_map<std::string, std::string> values;
    std::size_t cursor = 1;
    while (cursor <= userInfo.size())
    {
        const auto keyEnd = userInfo.find('\\', cursor);
        if (keyEnd == std::string_view::npos || keyEnd == cursor)
            return std::nullopt;
        const auto valueStart = keyEnd + 1;
        const auto valueEnd = userInfo.find('\\', valueStart);
        const auto key = userInfo.substr(cursor, keyEnd - cursor);
        const auto value = userInfo.substr(
            valueStart,
            valueEnd == std::string_view::npos
                ? userInfo.size() - valueStart
                : valueEnd - valueStart);
        values.insert_or_assign(std::string(key), std::string(value));
        if (valueEnd == std::string_view::npos)
            break;
        cursor = valueEnd + 1;
    }
    return values;
}
```

**⇒ 十二层**：
```text
1. **必须以 `\` 开头** ⇒ 否则拒绝
2. ⇒ **大小上限 `1024`** ⇒ **防 DoS**
3. ⇒ **格式 `\key\value\key\value...`**
4. ⇒ **空 key（`keyEnd == cursor`）⇒ 拒绝**
5. ⇒ **最后一个 value 可以【没有闭合 `\`**】
6. ⇒ **⇒ 所以【`\name\foo` 与 `\name\foo\` 都合法**】
7. ⇒ **用 `insert_or_assign`** ⇒ **重复 key 后者胜**
8. ⇒ **⇒ 一个【宽容**】的解析器**
```

**✅ 与 §425 五 的 `mix32`**不同（这是**协议解析**）。

**⚠ 而"`insert_or_assign`"⇒ **一个"后者胜"的策略**。**

**⇒ 三层**：
```text
若用 `insert` ⇒ **第一个胜**
若用 `insert_or_assign` ⇒ **最后一个胜**
⇒ **⇒ 所以【选择后者意味着【后发**的值优先**】
```

**✅ ⭐ **一个"重复键策略"的选择**。

**✅ 与 §407 的"`d 792` 写两次而 `mat`/`offmat` 换位"**同族（**第二次"重复写入的语义"）。

## 七、**`takeQuoted` 的"必须只有一对引号"**

```cpp
std::optional<std::string_view> takeQuoted(std::string_view &input)
{
    input = trimLeft(input);
    if (input.size() < 2 || input.front() != '"')
        return std::nullopt;
    const auto closing = input.find_last_of('"');
    if (!closing)
        return std::nullopt;
    const auto value = input.substr(1, closing - 1);
    if (!trimLeft(input.substr(closing + 1)).empty())
        return std::nullopt;
    input = {};
    return value;
}
```

**⇒ 八层**：
```text
1. **必须以 `"` 开头**（**且至少 `2` 字节**）
2. ⇒ **用 `find_last_of('"')`** ⇒ **最后一个引号**
3. ⇒ **而 `if (!closing)`** ⇒ **`closing == 0` ⇒ 拒绝**（**同一个引号**）
4. ⇒ **⇒ 所以【`""`（空串）也会被拒绝**】（**因为 `closing == 0`**）
5. ⇒ **而【尾部必须只有空白**】**
6. ⇒ **⇒ 所以【`"a" extra` 被拒绝**】
7. ⇒ **但 `"a"b"` ⇒ `closing = 3`，`value = "a"b`** ⇒ **一个内嵌的引号被接受**
```

**⚠ 一个**边界行为**：`""` 被拒绝而 `"a"b"` 被接受。**

**⇒ 三层**：
```text
`""` ⇒ `closing = 0` ⇒ **拒绝**
`"a"b"` ⇒ `closing = 3` ⇒ **值 `a"b`** ⇒ **接受**
⇒ **⇒ 所以【空引号串不可表达**】
```

**✅ 一个**可实现性缺口**（空字符串不能作为参数）。

## 八、**`SV_ParseMenuResponse` 的严格五 token**

```cpp
std::optional<ClientMenuResponse> SV_ParseMenuResponse(
    std::string_view command,
    const std::uint32_t expectedServerId,
    const SvGameState &gameState)
{
    const auto name = takeCommandToken(command);
    const auto serverIdToken = takeCommandToken(command);
    const auto menuIndexToken = takeCommandToken(command);
    const auto response = takeCommandToken(command);
    if (!name || *name != "mr" || !serverIdToken || !menuIndexToken || !response ||
        takeCommandToken(command) || response->empty())
    {
        return std::nullopt;
    }
    ...
}
```

**⇒ 十层**：
```text
1. **四个 token：`mr` / serverId / menuIndex / response**
2. ⇒ **而第五个 `takeCommandToken` 必须【为空**】**
3. ⇒ **⇒ 所以【多余 token ⇒ 拒绝**】**
4. ⇒ **而 `response->empty()` ⇒ 拒绝**
5. ⇒ **`serverId != expectedServerId` ⇒ 拒绝**
6. ⇒ **`menuIndex >= ScriptMenuConfigStringCount` ⇒ 拒绝**
7. ⇒ **⇒ 所以【一个五重严格**】的解析**
```

### 8.1 ⭐⭐ **"第五个 token 必须为空"**

**✅ 一个"精确 token 数"的手法**（**用一个额外的 `takeCommandToken` 消耗并检查**）。

**✅ 与 §403 的"单变量实验"**不同（这是**一个防注入的严格性**）。

**⇒ 三层**：
```text
若只检查前四个 ⇒ **`mr 1 2 3 garbage` 会通过**
多检查一个 ⇒ **`garbage` 让它失败**
⇒ **⇒ 所以【"多消耗一个并检查它为空"**是一个惯用法**
```

**✅ ⭐⭐ **一个"精确消耗"的惯用法**。

**⚠ 而"`name != "mr"`"⇒ **`mr` 是菜单响应**。**

**✅ 与 §403 的"菜单"**——**`ScriptMenuConfigStringCount` 与 `gameState.scriptMenus`**。

## 九、关键结论

1. **⭐⭐⭐ "trace 默认开，因为【证据只有在下一场游戏产生它时才存在】"`** —— 第三次"取证的时间窗"（与 §402 的日志级别、§418 的事后测量同族）。
2. **⭐⭐ "有界（`200` 行），因为触发器是客户端可靠 `s` 加比赛末推送，一个每帧重发 `s` 的客户端会淹没日志"`**；而**到预算时记一行 `trace-budget-exhausted lines=200`** ⇒ **"用完本身是可见的"**，与 §409 的 `LOGSTALL`（系统层面）互补（**应用层面的自限**）。
3. **⭐ `std::atomic<uint32_t> written` + `fetch_add` ⇒ 恰好 `201` 行输出**（`0..199` 正文 + `200` 宣告）。
4. **⭐ OOB 前缀 `0xFF×4`（Quake 系的带外标记），而 `ProfileStats` 的前缀是 OOB + `"stats\0"`**。
5. **⭐ `ProfileStats` 分 `27` 块 × `1238` 字节 = `33426` 字节**；`1238` 可能是 **MTU 减去 IP/UDP 头**（推断）。
6. **⚠ 27 个独立的 OOB 包没有序列号 ⇒ 顺序与完整性依赖客户端重试或容忍缺失**（未闭合）。
7. **⭐ `isLanPeer` 的五个网段完整覆盖**：`10/8`、`127/8`、`169.254/16`（APIPA）、`172.16-31/12`、`192.168/16`。
8. **⭐ `mix32` 是 `lowbias32` 哈希**（两轮 `xor-shift + multiply`，常数 `0x7FEB352D`/`0x846CA68B`）。
9. **⭐⭐ `parseUserInfo` 的 `\key\value\` 解析**：**必须以 `\` 开头、上限 `1024`、空 key 拒绝、最后一个 value 可以没有闭合 `\`**、**重复 key 后者胜**（`insert_or_assign`）。
10. **⚠ `takeQuoted` 的一个边界行为**：**`""`（空串）被拒绝**（因为 `closing == 0`）而 **`"a"b"` 被接受**（值 `a"b`）⇒ **空字符串不能作为参数**。
11. **⭐⭐ `SV_ParseMenuResponse` 的"第五个 token 必须为空"** —— 一个"精确消耗"的惯用法，防 `mr 1 2 3 garbage` 通过。

## 十、未闭合点

- `1238` 是否由 MTU 推出。
- `ProfileStats` 的 27 块是否有序列号或校验。
- `challengeDiagnostics` 的用途（`unordered_map<uint64, uint8>`）。
- `ScriptMenuConfigStringCount` 的值。
- `sv_client_mp.cpp` 420 行之后未读取（**共 `4500` 行**）。
