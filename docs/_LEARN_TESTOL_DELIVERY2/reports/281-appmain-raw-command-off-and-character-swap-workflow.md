# 281 · **`SendRawCommand` 的默认关闭**、`swap` 五队列、"编辑文件再打下一局"的换角色工作流

## 一、范围

本报告学习 `Appmain.cpp` 2353–2575 行。

## 二、`PlayAnnouncer` 的**两个界**

```php
if (announcerParameter < CodolGameServer::SoundAliasConstantStringBase ||
    announcerParameter >= CodolGameServer::LocalSoundEventParameterMaximum)
{
    logGameServer("PlayAnnouncer rejected: parameter " + N + " is outside the announcer band");
    return InvalidMessage;
}
```

### 2.1 两个界

```text
>= SoundAliasConstantStringBase        下界（常量串基址）
<  LocalSoundEventParameterMaximum     上界
```

**⇒ 与 §261 的 `SoundAliasConstantStringBase + relativeIndex < SoundAliasEventParameterLimit` **同一思想**但用不同的上界名。**

**⚠ `SoundAliasEventParameterLimit` 与 `LocalSoundEventParameterMaximum` 是两个名字。**

**⇒ 可能是同一个值的两个别名。**

### 2.2 而"band"（带）

**⇒ 所以播音员参数占用一个**连续的区间**。**

**⇒ 与 §261 的"1432/1507 是语言前缀"一致 —— 那些在他的 band 里。**

## 三、**`SendRawCommand` 的默认关闭**（本组最重要的一段）

```php
// OPT-IN ONLY. A malformed binary reliable command can
// desync the netchan or take the client down -- section
// 181's `%` crash is the precedent -- so this stays off
// unless someone has deliberately switched it on.
std::size_t length{};
char allow[8]{};
const auto enabled =
    getenv_s(&length, allow, sizeof(allow), "OLMOD_ALLOW_RAW_COMMAND") == 0 &&
    length && allow[0] == '1';
if (!enabled || message.payload.empty())
{
    logGameServer("SendRawCommand refused: set OLMOD_ALLOW_RAW_COMMAND=1 to replay raw wire bytes into a live match");
    return InvalidMessage;
}
```

### 3.1 三层

```text
1. 一个畸形的二进制可靠命令可以让 netchan 失步或把客户端打下来
2. 先例：§181 的 `%` 崩溃
3. ⇒ 除非有人刻意打开，否则保持关闭
```

### 3.2 而 `%` 崩溃的先例

**§181（`EngineBindings.hpp`）** —— 从编号看在 181–190 段。

**⇒ noclip 或别的补丁？**

**⇒ 而从上下文看**是一个**可靠命令**引起的崩溃。**

**⇒ 所以"原始字节重放"是一个**危险的工具** —— 而它的默认关闭是正确的。**

### 3.3 而 `getenv_s` 的**第 8 种环境变量解析**

```php
getenv_s(&length, allow, sizeof(allow), "OLMOD_ALLOW_RAW_COMMAND") == 0 && length && allow[0] == '1'
```

### 3.4 三项

```text
getenv_s 成功
长度非零
首字符 '1'
```

**⇒ 第八种模式。**

**⇒ 与 §239 的 `getenv_s` 同族（在 `EngineBindings.cpp` 里也有 `getenv_s`）。**

### 3.5 ⚠ **`length` 是"需要的长度（含 NUL）"**

**⇒ 所以 `length` 非零意味着变量存在且至少有一个字符。**

**✓ 与 `allow[0] == '1'` 配合是正确的。**

## 四、`Booking` 的**兜底**

```php
if (message.type != MessageType::Booking)
{
    return Response{ .status = ResponseStatus::UnsupportedMessage };
}
if (message.payload.empty() || message.payload.size() > MaximumPayloadSize)
{
    return Response{ .status = ResponseStatus::InvalidMessage };
}
const std::lock_guard lock(DedicatedControlMutex);
DedicatedBookingCommands.push_back(message.payload);
return Response{ .status = ResponseStatus::Accepted };
```

### 4.1 三层

```text
非 Booking 且前面都不匹配 ⇒ 【UnsupportedMessage】（第三种状态）
空载荷或超长 ⇒ InvalidMessage
否则 ⇒ 排队
```

### 4.2 而 `Booking` 是**最后**的兜底判断

**⇒ 因为它是"最常见"的消息类型。**

**⚠ 但这个顺序意味着：每一条 Booking 消息都要先过**十一个 `if`**。**

**⇒ 一个性能问题（虽然极小）。**

**⇒ 而更清晰的做法是把 `Booking` 放在前面。**

### 4.3 而 `MaximumPayloadSize`

**⇒ 与 §281 的"畸形命令可以让 netchan 失步"一致 —— 需要一个上界。**

## 五、`overriddenCharacterItem`：**换角色的工作流**（本组第二重要）

```php
// OLMOD(character-swap): WHICH CHARACTER SHOULD THIS PLAYER WEAR?
//
// Read EVERY time a session is consumed, so changing a character costs a
// re-queue rather than a rebuild and a relaunch. Two sources, in order:
//
//   1. OLMOD_CHARACTER_ITEM=<id>        -- the launch-time override.
//   2. Ayria\Logs\olmod-character.txt   -- ONE number; read fresh, so
//                                          editing the file and playing the
//                                          next match is the whole workflow.
//
// 0 means "no override", which is byte-identical to the behaviour before any
// of this existed. Only a NUMBER is accepted: resolving a name needs the
// catalogue, and that is a 60,000-lookup sweep this thread must not run.
uint32 overriddenCharacterItem()
{
    if (const auto *const value = std::getenv("OLMOD_CHARACTER_ITEM"); value && value[0])
    {
        const auto parsed = std::strtoul(value, nullptr, 10);
        if (parsed > 0 && parsed <= 0xFFFFu) return (uint32)parsed;
    }
    std::wstring buffer(MAX_PATH, L'\0');
    const auto size = GetModuleFileNameW(nullptr, buffer.data(), MAX_PATH);
    if (!size) return 0;
    buffer.resize(size);
    const auto path = std::filesystem::path(buffer).parent_path() / L"Ayria" / L"Logs" / L"olmod-character.txt";
    std::ifstream in(path);
    if (!in) return 0;
    std::string text;
    std::getline(in, text);
    const auto parsed = std::strtoul(text.c_str(), nullptr, 10);
    return parsed > 0 && parsed <= 0xFFFFu ? (uint32)parsed : 0;
}
```

### 5.1 两个来源，按顺序

```text
① OLMOD_CHARACTER_ITEM=<id>            启动时覆盖
② Ayria\Logs\olmod-character.txt       一个数字；每次新鲜读取
```

### 5.2 而"编辑文件再打下一局就是整个工作流"

**⇒ 与 §275 的"`config_mp.cfg` 可以跳过加密"同族** —— **文件作为配置面。**

**⇒ 而"每次会话消费时读"** ⇒ 换角色花一次重排队而不是重建。

### 5.3 而"只接受数字"的理由

```php
// resolving a name needs the catalogue, and that is a 60,000-lookup sweep this thread must not run.
```

**⇒ "解析一个名字需要目录，而那是一次 60,000 查找的扫描，这个线程绝不能跑。"**

**⇒ 第六次"60,000 查找"的警告**（§239 的 60,249、§243 的 60,249、§244、§259/§260 的 1700/1023、§281 的 60,000）。

### 5.4 `0` 表示"无覆盖"

**⇒ "与任何这些存在之前的行为逐字节相同"** —— 一个**向后兼容**的设计。

### 5.5 ⚠ **`std::strtoul` 两处都不检查**

```cpp
const auto parsed = std::strtoul(value, nullptr, 10);
if (parsed > 0 && parsed <= 0xFFFFu) return (uint32)parsed;
```

**⇒ `"abc"` ⇒ 0 ⇒ 不走这个分支 ⇒ 回退到文件。**

**⇒ 实际上 `strtoul` 的"0"恰好等于"无覆盖" ⇒ **无害**。**

**⇒ 而 `"12345abc"` ⇒ 12345 ⇒ 接受。**

**⚠ 一个宽松但无害的解析。**

### 5.6 而文件名 `olmod-character.txt`

**⇒ `Ayria/Logs/olmod-character.txt`** —— 与 §243 的 `Ayria/Logs/*.csv`、§277 的 `Ayria/Assets/OlMod/GameScripts` 同级。

## 六、`processDedicatedControlMessages` 的**五队列 `swap`**（本组第三重要）

```php
std::deque<std::string> commands;
std::deque<QueuedDedicatedSessionStart> sessions;
std::deque<QueuedDedicatedSessionStart> deferredSessions;
std::deque<QueuedLoadoutUpdate> loadoutUpdates;
std::deque<std::uint16_t> announcerAuditions;
std::deque<std::vector<std::uint8_t>> rawCommands;
{
    const std::lock_guard lock(DedicatedControlMutex);
    commands.swap(DedicatedBookingCommands);
    sessions.swap(DedicatedSessionStarts);
    loadoutUpdates.swap(DedicatedLoadoutUpdates);
    announcerAuditions.swap(DedicatedAnnouncerAuditions);
    rawCommands.swap(DedicatedRawCommands);
}
```

### 6.1 五个 `swap`

```text
commands
sessions
loadoutUpdates
announcerAuditions
rawCommands
```

**⇒ **局部 deque 与全局 deque 交换** ⇒ 持锁时间 = 五次 swap（O(1) 每个）。**

**⇒ 然后**不持锁**处理。**

**✓ 这是正确的"缩短临界区"模式。**

### 6.2 而 `deferredSessions` **未被 swap**

**⇒ 它是**只为这个函数**的局部变量。**

**⇒ 所以"被延后的会话"在本地处理。**

**⇒ 待读它的用法。**

### 6.3 而五队列的**处理顺序**

```text
① rawCommands        发送原始命令
② announcerAuditions 播放播音员
③ loadoutUpdates     刷新 loadout
④ sessions           处理会话
⑤ （deferredSessions 在 sessions 之后）
```

**⇒ 顺序有意义** —— 原始命令与播音员立即发，loadout 与会话按序。

## 七、`rawCommands` 的**十六进制回显**

```php
for (const auto &raw : rawCommands)
{
    const auto clients = Server.sendRawCommand(raw);
    std::string hex;
    for (const auto byte : raw)
    {
        static constexpr char Digits[] = "0123456789abcdef";
        hex += Digits[byte >> 4];
        hex += Digits[byte & 0xF];
    }
    logGameServer("SendRawCommand sent " + raw.size() + " bytes clients=" + clients + " " + hex);
}
```

### 7.1 四项

```text
字节数
接收客户端数
十六进制内容
```

### 7.2 而"回显整个命令"

**⇒ 因为这是一个**危险工具**，所以每一条都完整记录。**

**✓ 正确的审计。**

### 7.3 而 `Digits` 是 `static constexpr` 在循环内

**⚠ 每个元素都会重新声明？**

**⇒ 不 —— `static constexpr char Digits[]` 是**函数级静态** ⇒ 只初始化一次。**

**⇒ 但写在循环体内**在可读性上不好**。**

**⇒ 与 §271 的 `static constexpr char Digits[]` 在 `SNAPHEX` 里也是循环内**同族。**

## 八、`announcerAuditions` 与 `loadoutUpdates` 的处理

```php
for (const auto announcerParameter : announcerAuditions)
{
    const auto clients = Server.playAnnouncerLine(announcerParameter);
    logGameServer("PlayAnnouncer sent p " + N + " clients=" + clients);
}

for (const auto &update : loadoutUpdates)
{
    const auto applied = refreshMemberLoadout(update.userId, update.loadout);
    logGameServer((applied ? "UpdateLoadout applied" : "UpdateLoadout FAILED") +
        " request=" + N + " user=" + N + " classMask=" + N);
}
```

### 8.1 两处都报告 `clients` / `applied`

**⇒ 所以"发了但没送到"与"没发"可分。**

## 九、`sessions` 的**四段**

```php
for (const auto &queued : sessions)
{
    const auto &session = queued.session;
    // ① 构建 roster
    std::vector<SessionRosterMember> roster;
    roster.reserve(session.members.size());
    transform(session.members, back_inserter(roster), [](member) {
        return SessionRosterMember{ .xuid = member.userId, .username = member.username };
    });

    // ② 合并 classMask
    uint32 requestedClassMask{};
    for (const auto &member : session.members) requestedClassMask |= member.loadout.classMask;

    // ③ 标记 processing
    { lock; DedicatedSessionConsumption.processing(queued.requestId, requestedClassMask); }

    // ④ 暂存 roster
    if (!Server.stageSessionRoster(queued.requestId, roster))
    {
        logGameServer("session roster rejected request=" + requestId);
        { lock; DedicatedSessionConsumption.failed(SessionRosterRejected, -1, 0); }
        continue;
    }

    // ⑤ failSession 回滚 lambda
    const auto failSession = [&](stage, failedClassIndex, resolvedClassMask) {
        static_cast<void>(Server.rollbackSessionRoster(queued.requestId));
        { lock; DedicatedSessionConsumption.failed(stage, failedClassIndex, resolvedClassMask); }
        ...
    };
```

### 9.1 五段

```text
① roster（xuid + username）
② classMask 的按位或合并
③ processing 标记
④ stageSessionRoster（失败 ⇒ failed + continue）
⑤ failSession 回滚 lambda
```

### 9.2 而 `requestedClassMask |= member.loadout.classMask`

**⇒ **所有成员的 classMask 按位或**。**

**⇒ 所以"这个会话需要哪些职业"是所有人的并集。**

**⇒ 与 §241 的"classMask=3 是硬门槛"相关** —— 而这个并集可能更大。

### 9.3 而 `failSession` 的**三项**

```text
rollbackSessionRoster(requestId)
DedicatedSessionConsumption.failed(stage, failedClassIndex, resolvedClassMask)
（还有后续，待读）
```

**⇒ **先回滚再标记失败**。**

**⇒ 与 §239 的"六次回滚 + 基线保留"同族。**

### 9.4 而 `failedClassIndex = -1` 表示"不特定于某个职业"

**⇒ 与 §271 的 `currentCharacter{-1}` 同一手法。**

## 十、关键结论

1. **`PlayAnnouncer` 的两个界**：`>= SoundAliasConstantStringBase` 且 `< LocalSoundEventParameterMaximum`。
2. **`SoundAliasEventParameterLimit` 与 `LocalSoundEventParameterMaximum` 可能是同一值的两个名字**。
3. **`SendRawCommand` 默认关闭** —— 畸形可靠命令可以让 netchan 失步或打挂客户端（§181 的 `%` 崩溃）。
4. **`getenv_s` 是第八种环境变量解析**。
5. **`Booking` 是最后的兜底判断** ⇒ 每条 Booking 都要先过十一个 `if`。
6. **`overriddenCharacterItem` 的两个来源**（环境变量 → 文件），"编辑文件再打下一局"就是整个工作流。
7. **"只接受数字因为解析名字需要 60,000 查找"** —— 第六次 60,000 警告。
8. **`0` = 无覆盖 ⇒ 与之前逐字节相同** —— 向后兼容。
9. **`std::strtoul` 的宽松解析在这里无害**（0 恰好等于"无覆盖"）。
10. **五队列 `swap`** 缩短临界区（O(1) 每次），然后不持锁处理。
11. **`rawCommands` 的十六进制回显** —— 危险工具必须完整审计。
12. **`sessions` 的五段**：roster → classMask 并集 → processing → stage → failSession 回滚。
13. **`requestedClassMask` 是所有成员的**并集**。
14. **`failedClassIndex = -1`** 表示不特定。

## 十一、未闭合点

- `SoundAliasEventParameterLimit` 与 `LocalSoundEventParameterMaximum` 是否同值。
- §181 的 `%` 崩溃的具体机制。
- `deferredSessions` 的用法。
- `Appmain.cpp` 2575 行之后未读取。
