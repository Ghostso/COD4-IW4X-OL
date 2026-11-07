# 280 · **§187o 的钉 dm 被取消**（`booking refused` 的实测）、八个控制消息、noclip 的边沿

## 一、范围

本报告学习 `Appmain.cpp` 2134–2360 行。

## 二、控制消息的**八种类型**（从本段可见）

```text
① QueryEndpoint          空载荷，返回 endpoint
② QueryGameplayStatus    空载荷，返回 gameplay payload
③ DebugGrantBattery      optional slot (< 18)
④ SetNoclip              解码请求
⑤ SessionStart           解码会话，排队
⑥ UpdateLoadout          u64 userId + loadout
⑦ PlayAnnouncer          u16 参数
⑧ ConfigureSession       （§279）
```

**⇒ 八个。**

### 2.1 三个**空载荷**消息

```text
QueryEndpoint          `!payload.empty()` ⇒ InvalidMessage
QueryGameplayStatus    `!payload.empty()` ⇒ InvalidMessage
DebugGrantBattery      `payload.empty()` ⇒ valid（无目标）
```

**⇒ 两个严格拒绝非空，一个把空当作"无目标"。**

### 2.2 而 `InvalidMessage` vs `Rejected` 的区分

```text
InvalidMessage    载荷格式错（协议错）
Rejected          载荷对但业务拒绝
```

**⇒ 两级。**

**⇒ 而 `QueryGameplayStatus` 用 `payload.empty() ⇒ Rejected`** —— 所以"编码失败"是 `Rejected` 而不是 `InvalidMessage` ✓

## 三、`DebugGrantBattery` 的**五项**

```php
optional<uint32> target;
bool valid = message.payload.empty();
if (!message.payload.empty())
{
    uint32 slot{};
    const auto parsed = from_chars(payload.data(), payload.data()+size, slot);
    valid = parsed.ec == errc{} && parsed.ptr == end && slot < 18;
    if (valid) target = slot;
}
const bool accepted = valid && Server.debugGrantFactoryBattery(message.peerIpv4, target);
```

### 3.1 三层

```text
空载荷 ⇒ valid（无目标 ⇒ 给发送者的客户端）
非空   ⇒ from_chars + 全消费 + slot < 18
然后   ⇒ debugGrantFactoryBattery(ipv4, target)
```

### 3.2 而 `slot < 18` 是 `MaximumGameClients`

**⇒ 第五次正确的 `from_chars`。**

### 3.3 而 `message.peerIpv4` 参与授权

**⇒ 所以"给哪个客户端"由**源地址**决定（当 `target` 为空时）。**

**⇒ 与 §280 后面 noclip 的同一模式** ✓

## 四、`SetNoclip` 的**边沿日志**（本组第二重要）

```php
const auto resolved = Server.setPlayerNoclipForSender(
    request->userId, message.peerIpv4, request->enabled, request->holdMilliseconds);

// SILENT WHEN HEALTHY. The poller repeats twice a second
// while the key is down, and a line per repeat would bury
// every other diagnostic in the log. Only the EDGES speak,
// plus every failure -- a request that resolves to nobody
// is the one thing worth hearing about every time.
static std::map<uint32, bool> announced;
auto &last = announced[message.peerIpv4];
if (last != request->enabled || !resolved)
{
    last = request->enabled;
    logGameServer("noclip " + (request->enabled ? "on" : "off") +
        " from=" + ipv4Text(message.peerIpv4) +
        (resolved ? " client=" + resolved->clientNum + " xuid=" + resolved->xuid +
            (resolved->ambiguous ? " (SHARED ADDRESS, took the lowest active slot)" : "")
            : " NO ACTIVE CLIENT AT THAT ADDRESS"));
}
```

### 4.1 三层

```text
1. 【只在边沿发声】—— 按键按住时轮询器一秒重复两次
2. ⇒ 每次重复一行会埋掉其它所有诊断
3. ⇒ 【边缘】发声，加上【每一次失败】
```

### 4.2 而"每一次失败"总是发声

**⇒ `!resolved` ⇒ 每次都打。**

**⇒ 因为"解析到没有人"是唯一值得每次都听的事。**

**✓ 一个精确的规则。**

### 4.3 而 `announced[peerIpv4]`

**⇒ 每个源地址一个"上次状态"。**

**⇒ 而 `auto &last = announced[message.peerIpv4]` 会**插入**默认值 `false`（如果不存在）。**

**⚠ 所以第一次 `enabled == false` 时 `last == false` ⇒ **不打印**。**

**⇒ 这是一个小缺陷** —— "第一次关"不会记录。

**⇒ 但无实际影响（因为默认就是关）。**

### 4.4 而 `resolved->ambiguous` 的**共享地址**

```php
resolved->ambiguous ? " (SHARED ADDRESS, took the lowest active slot)" : ""
```

**⇒ 所以多个客户端在同一个源地址（NAT/本机多开）⇒ 取**最低的活跃槽**。**

**⇒ 与 §278 的 `optionalClient` 用 `0xFFFFFFFF` 同族（明确的哨兵/规则）。**

### 4.5 而 `request->holdMilliseconds`

**⇒ 说明 noclip 有一个"保持时长"** —— 所以按键松开时自动关。

**⇒ 与"轮询器一秒重复两次"配合。**

## 五、**§187o 的钉 dm 被取消**（本组最重要的一段）

### 5.1 那段原始论证（§187o）

```php
// PIN THE GAMETYPE HERE, AT THE ONE FUNNEL EVERY PATH USES.
//
// Section 187o. The first attempt pinned it in
// CODOL_GameServerConfigureBooking, next to
// readClientBookingSelection -- and the served gametype stayed
// `cha`, because a SessionStart arrives as a CONTROL MESSAGE with
// its booking already decided by the backend dispatcher and never
// passes through that export at all. Measured: no `PINNED` line and
// `configureGameState entry booked=cha` in the same cycle.
//
// WHY IT MATTERS: dm.lua leaves every player at team None so
// `issameteam` is false for every pair and everyone is damageable;
// cha.lua puts players on real sides. Two players on one side cannot
// hurt each other, which is what "I still can't do damage" is.
//
// The MAP and members still come from the real booking. Only the
// gametype is pinned, until team assignment splits two players.
```

### 5.2 四层

```text
1. 第一次在 `CODOL_GameServerConfigureBooking` 里钉 —— 而服务的 gametype 仍是 `cha`
2. 因为 SessionStart 作为【控制消息】到达，booking 已由后端派发器决定
3. ⇒ 【从不经过那个 export】
4. 实测：同一个周期里没有 `PINNED` 行而 `configureGameState entry booked=cha`
```

### 5.3 而**为什么钉 `dm`**

```text
dm.lua    每个玩家的队伍是 None ⇒ `issameteam` 对每一对都是 false ⇒ 人人可伤害
cha.lua   把玩家放到真实的两侧 ⇒ 同侧两个玩家不能互相伤害 ⇒ "我还是打不出伤害"
```

**⇒ 所以钉 `dm` 是为了**绕过**"没有队伍分配"这个缺失。**

**⇒ 与 §270 的 `gameTypeIsTeamless` 是**配套的两半**：**

```text
§270  推导出哪些 token 本来就是无队伍的 ⇒ 那些【不需要】钉
§280  对需要钉的 token ⇒ 钉到 dm
```

### 5.4 而**取消**的理由（中文注释）

```php
// ★★★ 2026-10-07 05:3x -- **取消 §187o 的「钉 dm」（单变量；d28 实测根因）**：
//   d28 实测在下一站被拒：
//     `booking refused: match rules invalid booked=dm engine=dm
//      version=796 score=0 time=2 roundSwitch=1 roundLimit=7 winLimit=4`
//   —— 后端按 **sd 形状**下发规则（有局数、无分数上限），而这里把 gametype
//   钉成 dm 后，`DedicatedSession::valid()` 按 ffa/dm 严格校验 ⇒ 必然拒绝。
//   黄金自然轮（老外 `20260812_sd_objectives_v7`）就是直接服务
//   `26/0/mp_crash_tropical/sd`，并闭合了 SessionStart/world/gamestate/snapshot。
//   ⇒ 现在**直接服务客户端自己 booked 的 gametype**；§187o 的双人伤害问题
//   留待团队分配修复后再处理（不在这里静默改语义）。
```

### 5.5 六层

```text
1. 后端按【sd 形状】下发规则：有局数（roundLimit=7）、无分数上限（score=0）
2. 而这里把 gametype 钉成 dm
3. ⇒ `DedicatedSession::valid()` 按 ffa/dm **严格校验** ⇒ 必然拒绝
4. 实测错误：`booking refused: match rules invalid booked=dm engine=dm ...`
5. 黄金自然轮直接服务 `26/0/mp_crash_tropical/sd` 并闭合了整条链
6. ⇒ 现在**直接服务客户端自己 booked 的 gametype**
```

### 5.6 而"留待团队分配修复后再处理（不在这里静默改语义）"

**⇒ 这是一个**重要的原则** —— 不静默改语义。**

**⇒ 与 §237 里"§187p 的回退针对的是老外双人测试的 team 模式问题"对照：**

```text
§237  回退到 3.3.3.3 的偏移（因为正确偏移会 serve cha ⇒ 双人无法伤害）
§280  取消钉 dm（因为钉了会被 valid() 拒绝）
```

**⚠ 两个决定**方向相反**？**

**⇒ §237 说"回退因为目标改成进图"；§280 说"取消钉因为进不去"。**

**⇒ 所以**现在**的做法是：**

```text
gametype   用客户端自己 booked 的（不钉）
booking    用 3.3.3.3 的偏移（读不到，回退到命令行 --gametype）
```

**⇒ 两者一致：**都用"客户端/命令行给的"而不是"我们改的"。**

**✓ 所以 §237 与 §280 是同一个方向（不静默改），只是表面相反。**

### 5.7 而 `pinnedSession = *session` 但**不再修改**

```php
auto pinnedSession = *session;
...
DedicatedSessionStarts.push_back({ .requestId = message.requestId, .session = pinnedSession });
```

**⚠ `pinnedSession` 现在**只是一个拷贝** —— 那个 `auto pinnedSession = *session;` 是取消钉 dm 之后的**遗留。*

**⇒ 命名仍叫 `pinnedSession` 而实际上**没有钉**。**

**⇒ 这是一处过时的命名** —— 与 §237 的"注释滞后"同族。

## 六、`SessionStart` 的**三段**

```php
const auto session = decodeSessionStart({payload});
if (!session) { logGameServer("SessionStart rejected: invalid payload"); return InvalidMessage; }

auto pinnedSession = *session;
{
    const std::lock_guard lock(DedicatedControlMutex);
    DedicatedSessionStarts.push_back({ message.requestId, pinnedSession });
    DedicatedSessionConsumption.queued(message.requestId);
}
logGameServer("SessionStart queued request=" + requestId + " map=" + mapName +
    " gametype=" + gameType + " members=" + members.size());
return Accepted;
```

### 6.1 三项

```text
解码
排队 + 标记 consumption.queued
日志（四个量）
```

### 6.2 而 `DedicatedSessionConsumption.queued(requestId)`

**⇒ 一个"消费追踪器"** —— 与 §271 的 `DedicatedSessionConsumptionTracker` 一致。

**⇒ 所以每次排队都登记，后面在游戏线程消费时对账。**

## 七、`UpdateLoadout` 的**三层**

```php
if (message.payload.size() < sizeof(uint64)) return InvalidMessage;
uint64 userId{};
memcpy(&userId, payload.data(), 8);
const auto loadout = decodeLoadout({ payload.data() + 8, payload.size() - 8 });
if (!userId || !loadout || !valid(*loadout)) { logGameServer("...invalid payload"); return InvalidMessage; }
{ lock; DedicatedLoadoutUpdates.push_back({ requestId, userId, *loadout }); }
logGameServer("UpdateLoadout queued request=" + N + " user=" + N + " classMask=" + N);
return Accepted;
```

### 7.1 四项

```text
size >= 8
userId 非零
decodeLoadout 成功
valid(*loadout)
```

### 7.2 而 `!userId` 是**零检查**

**⇒ 因为 userId 0 可能是"未登录"。**

### 7.3 而 `classMask` 在日志里

**⇒ 与 §241 的 `classMask=3` 相关。**

## 八、`PlayAnnouncer` 的**边界拒绝**（本组第三重要）

```php
if (message.payload.size() < sizeof(uint16)) return InvalidMessage;
uint16 announcerParameter{};
memcpy(&announcerParameter, payload.data(), 2);
// The SAME bound queueLocalSound enforces. A parameter below
// the constant-string base would address the MAP's alias
// table and play whatever ambience that index happens to
// hold, which is the 100..102 mistake of section 112b in a
// new costume - so it is refused rather than played.
if (announcerParameter < ...)  // ← 待读
```

### 8.1 三层

```text
1. 与 `queueLocalSound` 强制【同一个界】
2. 低于常量串基址的参数会寻址【地图的】别名表
3. ⇒ 播放那个索引碰巧持有的任何环境音
4. = §112b 的 `100..102` 错误【换了个装束】
```

### 8.2 而"换了个装束"

**"in a new costume"** —— 同一个错误在另一个参数上重现。

**⇒ 与 §261 的"两个池同一数字不同语义"同族。**

**⇒ 所以这个检查是**跨字段的类型安全**。**

## 九、关键结论

1. **八种控制消息**（ConfigureSession / QueryEndpoint / QueryGameplayStatus / DebugGrantBattery / SetNoclip / SessionStart / UpdateLoadout / PlayAnnouncer）。
2. **`InvalidMessage`（协议错）与 `Rejected`（业务拒绝）两级**。
3. **`slot < 18`** 是 `MaximumGameClients`。
4. **noclip 只在边沿发声 + 每次失败发声** —— 因为轮询器一秒重复两次。
5. **`announced[peerIpv4]` 的隐式插入会吞掉"第一次关"** —— 一个无害的小缺陷。
6. **`ambiguous` ⇒ 取最低活跃槽**。
7. **§187o 的钉 dm 第一次放在错误的漏斗里**（SessionStart 是控制消息，不经那个 export）。
8. **钉 dm 的理由是 `dm.lua` 让队伍为 None ⇒ `issameteam` 恒 false**。
9. **取消的理由是后端按 sd 形状下发规则而 dm 的 `valid()` 严格校验 ⇒ 必然拒绝**，实测 `booking refused: match rules invalid`。
10. **"不在这里静默改语义"** —— 一个重要的原则。
11. **`pinnedSession` 现在只是拷贝** —— 命名过时。
12. **§237 与 §280 表面相反实际同向**（都用"客户端/命令行给的"而非"我们改的"）。
13. **`PlayAnnouncer` 的边界拒绝** —— "§112b 的 100..102 错误换了装束"。

## 十、未闭合点

- `PlayAnnouncer` 的具体下界。
- `ensureDedicatedControlServer` 是否还有更多消息类型。
- `DedicatedSessionConsumption` 的对账逻辑。
- `Appmain.cpp` 2360 行之后未读取。
