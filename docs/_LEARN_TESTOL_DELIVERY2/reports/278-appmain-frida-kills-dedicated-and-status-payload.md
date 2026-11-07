# 278 · **Frida 三次中两次杀掉专用服**、`GameplayClientStatus` 的六十二个字段、`schema 5`

## 一、范围

本报告学习 `Appmain.cpp` 1704–1920 行。

## 二、`dedicatedEndpointStatus` 的**四个字段**

```php
const auto server = Server.status();
const auto transport = Network.status();
return {
    .sessionConfigured = server.sessionConfigured,
    .enabled = server.enabled,
    .bound = transport.bound,
    .port = transport.port,
};
```

### 2.1 四个

```text
sessionConfigured    会话已配置
enabled              已启用
bound                端口已绑定
port                 端口
```

**⇒ 两个来自 `Server`、两个来自 `Network`。**

## 三、`dedicatedGameplayStatusPayload` 的**两级结构**

```php
const auto source = Server.gameplayPresentationStatus();
OlMod::DedicatedControl::GameplayStatus status{
    .serverTime = source.serverTime,
    .sd = { ... 十八个字段 ... },
};
status.clients.reserve(source.clients.size());
for (const auto &sourceClient : source.clients) { ... }
```

### 3.1 两层

```text
GameplayStatus
  ├─ serverTime
  ├─ sd（拆弹模式，18 个字段）
  └─ clients[]（每客户端 62 个字段）
```

## 四、`sd` 的**十八个字段**

```php
.roundConfigured .roundArmed .roundCompleted .roundsPlayed
.roundWinner .roundEndReason
.bombConfigured .bombPhase
.attackers .defenders .attackersAlive .defendersAlive
.carrierClientNum .planterClientNum .defuserClientNum
.plantedSiteLabel
.phaseStartServerTime .plantedServerTime
```

### 4.1 六组

```text
回合      configured / armed / completed / roundsPlayed / winner / endReason
炸弹      configured / phase
队伍      attackers / defenders / attackersAlive / defendersAlive
角色      carrier / planter / defuser
站点      plantedSiteLabel
时间      phaseStart / planted
```

### 4.2 而 `plantedSiteLabel` 是**单字符**

```php
.plantedSiteLabel = (uint32)(
    source.sd.bomb.plantedSiteLabel && source.sd.bomb.plantedSiteLabel->size() == 1
    ? (unsigned char)((*source.sd.bomb.plantedSiteLabel)[0]) : 0),
```

**⇒ 只有长度为 1 时才取那个字符，否则 0。**

**⇒ 所以站点标签是 `"A"` 或 `"B"`（单字符）** ✓

### 4.3 而 `optionalClient` 的**哨兵**

```php
const auto optionalClient = [](const std::optional<uint32> value) {
    return value.value_or(std::numeric_limits<std::uint32_t>::max());
};
```

**⇒ `nullopt ⇒ 0xFFFFFFFF`** —— 而不是 0（因为 0 是合法的客户端号）。

**⇒ 与 §235 的 `INT32_MIN`、§242 的 `addressable` 同族**（用不可能的值）。

## 五、`schema 5` 与 **Frida 的失败**（本组最重要的一段）

```php
// OLMOD(locational-hit-readout): schema 5. Frida cannot sample this
// - CodolGameServerControl.py --pid <dedicated> terminated the
// dedicated two runs out of three - so the authoritative origin and
// the last committed bullet trace travel over the control socket
// instead. start + (end - start) * fraction is the world point the
// server resolved the hit to, and subtracting the TARGET's origin
// from the same sample gives its height above their feet.
```

### 5.1 五层

```text
1. schema 5
2. Frida【不能】采样这个 —— `CodolGameServerControl.py --pid <dedicated>`
   在三次运行里有两次【终止了专用服】
3. ⇒ 所以权威的 origin 与最后一次提交的子弹 trace 走【控制 socket】
4. `start + (end - start) * fraction` 是服务端解析到的世界点
5. 而从同一个样本里减去【目标】的 origin 得到它离脚的高度
```

### 5.2 **"三次里两次杀掉专用服"**

**⇒ 与 §275 的"frida attach 40+ 次全失败"**是不同的失败**：**

```text
§275  frida 在客户端 attach 失败（虚拟空间 1998 MB）
§278  frida 在专用服 attach 【成功但终止了它】
```

**⇒ 两个进程两个问题。**

**⇒ 而结论相同：**必须走控制 socket 而不是 Frida。**

### 5.3 而 `start + (end - start) * fraction` 的数学

**⇒ 这正是 §273 的 `axis(index)` lambda 的同一个公式** ✓

**⇒ 两处独立实现同一插值。**

### 5.4 而"减去目标 origin 得到离脚高度"

**⇒ 与 §273 的 `hitZ = axis(2) - target->origin[2]` **完全相同** ✓

**⇒ 所以这个控制 socket 的字段就是 §273 的 `bullet-hit` 日志的程序化版本。**

## 六、`GameplayClientStatus` 的**六十二个字段**

### 6.1 七组

```text
身份（2）      clientNum, gameplayState, team                → 3
可靠通道（7）  reliableSequence, reliableAcknowledge,
               incomingSequence, outgoingSequence,
               messageAcknowledge,
               lastPacketReceivedTime, peerIpv4, peerPort     → 8
UDP（7）       sendAttempts, sendSucceeded, sendFailed,
               bytesSent, lastSendTime, lastSendBytes, lastSendError
usercmd 队列   pendingUserCmdCount,
（6）          oldest/newest/lastReceived/lastDispatched/lastExecuted/
               lastDiscarded（6 个时间）
丢弃计数（3）  discardedUnsupportedUserCmds, discardedRejectedUserCmds,
               lastDiscardedRejectedUserCmdTime
think（4）     clientThinkLastAttempted/LastCommitted/
               FailureStage/FailureCount
输入（6）      lastDispatchedButtons/Angles/Weapon/Offhand/
               ForwardMove/RightMove
快照掩码（2）  snapshotPlayerEntityMask, snapshotClientInfoMask
世界（3）      origin, viewAngles, health
子弹（9）      bulletCommandTime, bulletStart, bulletEnd, bulletFraction,
               bulletHitType, bulletHitEntityNum, bulletModelIndex,
               bulletPartName, bulletPartGroup, bulletResult
目标（数组）   objectives[]
可靠命令（数组）recentReliableCommands[]
```

**⇒ 我数到约 50 个标量 + 2 个数组。**

**⇒ 加上 `sd` 的 18 个，整个 payload 是**约 70 个字段**。**

### 6.2 而**六个 usercmd 时间点**

```text
oldestPendingUserCmdTime
newestPendingUserCmdTime
lastReceivedUserCmdTime
lastDispatchedUserCmdTime
lastExecutedUserCmdTime
lastDiscardedUserCmdTime
```

**⇒ 六个阶段：收到 → 派发 → 执行 与 待处理 → 丢弃。**

**⇒ 与记忆里"usercmd per-packet capacity 32"、"duplicate usercmd accepted then discarded"相关。**

**⇒ 所以这六个时间点直接暴露"卡在哪个阶段"。**

### 6.3 而 `optionalClient` 在这六个上**全部**用

```php
.oldestPendingUserCmdTime = optionalClient(sourceClient.oldestPendingUserCmdTime),
...
```

**⇒ 所以"从未有过"⇒ `0xFFFFFFFF`。**

## 七、`lastDiscardedRejectedUserCmdTime` 的**三层嵌套**

```php
.lastDiscardedRejectedUserCmdTime = optionalClient(
    ingress && ingress->lastDiscardedRejectedUserCmd
        ? std::optional{ ingress->lastDiscardedRejectedUserCmd->commandTime }
        : std::nullopt),
```

### 7.1 三层

```text
ingress 存在
  ⇒ lastDiscardedRejectedUserCmd 存在
    ⇒ 取它的 commandTime
```

**⇒ 两层 `optional` 嵌套（`optional<optional<uint32>>` 塌缩成一个）。**

**⚠ `std::optional{ optional<uint32> }` 会得到 `optional<optional<uint32>>` 而 `optionalClient` 期望 `optional<uint32>`。**

**⇒ 但 `optionalClient` 的签名是 `(std::optional<std::uint32_t> value)`，所以会**隐式转换**。**

**⇒ 而 `optional<optional<T>>` 到 `optional<T>` 的转换在 C++ 里是**未定义/不存在的**。**

**⚠ 这可能是一处需要编译器容忍的写法。**

**⇒ 实际上 `std::optional{ ingress->...->commandTime }` 是 `optional<uint32>`，因为 `commandTime` 是 `uint32` 而不是 `optional`。**

**✓ 所以是 `optional<uint32>` ⇒ 正确。**

**⇒ 我读错了。`->commandTime` 直接是 `uint32`。**

## 八、`lastDispatched` 的**六个字段**

```php
.lastDispatchedButtons = lastDispatched ? lastDispatched->buttons : 0,
.lastDispatchedAngles = lastDispatched
    ? std::array<uint32,3>{ angles[0], angles[1], angles[2] }
    : std::array<uint32,3>{},
.lastDispatchedWeapon = lastDispatched ? (uint32)lastDispatched->weapon : 0u,
.lastDispatchedOffhand = lastDispatched ? (uint32)lastDispatched->offHandIndex : 0u,
.lastDispatchedForwardMove = lastDispatched ? (int32)lastDispatched->forwardMove : 0,
.lastDispatchedRightMove = lastDispatched ? (int32)lastDispatched->rightMove : 0,
```

### 8.1 六个

```text
buttons
angles[3]
weapon
offHandIndex
forwardMove
rightMove
```

### 8.2 而 `forwardMove`/`rightMove` 是**有符号**

**⇒ `(int32)` 转换** —— 因为它们可以负（后退/左移）。

**⇒ 与记忆里"fwd/right 518/832"相关** —— 那是**正的**。

### 8.3 而 `angles` 是 `uint32`

**⚠ 而 §273 的 `targetYaw` 从 `entity.angles[1]` 取，那是 `float`。**

**⇒ 所以 `UserCmd::angles` 是 `uint32`（打包的角度）而 `entity.angles` 是 `float[3]`。**

**⇒ 两个不同的角度表示。**

## 九、`objectives[]` 的**两个字段**

```php
client.objectives[index] = {
    .state = (uint32)sourceClient.objectives[index].state,
    .icon = sourceClient.objectives[index].icon,
};
```

**⇒ `state` + `icon`。**

**⇒ 而 `icon` 是数值（不是字符串）。**

## 十、`recentReliableCommands[]` 的**两个字段**

```php
client.recentReliableCommands.push_back({
    .sequence = sourceCommand.sequence,
    .command = sourceCommand.command,
});
```

**⇒ `sequence` + `command`（字符串）。**

**⇒ 与记忆里"Reliable command ring capacity 512"相关 —— 这里的 `recentCommands` 可能是那个环的快照。**

## 十一、`bullet` 的**十个字段**

```php
.bulletCommandTime      （默认 UINT32_MAX）
.bulletStart
.bulletEnd
.bulletFraction
.bulletHitType
.bulletHitEntityNum     （默认 BulletNoneEntityNum）
.bulletModelIndex
.bulletPartName
.bulletPartGroup
.bulletResult
```

### 11.1 十个

**⇒ 而 `bulletCommandTime` 的默认是 `UINT32_MAX`** 而不是 0（与 `optionalClient` 一致）。

### 11.2 而这十个是 §272/§273 的**程序化暴露**

```text
§272 的 `bullet-penetration-result` 日志
§273 的 `bullet-hit` 日志
§278 的 `.bullet*` 字段
```

**⇒ 三种形式：日志、程序化字段。**

**⇒ 而 §272 的日志有 12 个量、§273 的 `bullet-hit` 有 14 个、这里的 `.bullet*` 有 10 个 —— **重叠但不相同**。**

## 十二、`source` 与 `status` 的**两次 `Server.` 调用**

```php
const auto source = Server.gameplayPresentationStatus();     // ← 一次
...
for (const auto &sourceClient : source.clients)
{
    const auto ingress = Server.clientIngressStatus(sourceClient.clientNum);       // ← 每客户端
    const auto peerTransport = ingress ? Network.peerStatus(ingress->peer) : nullopt;
    const auto think = Server.worldClientThinkStatus(sourceClient.clientNum);      // ← 每客户端
    const auto worldPlayerState = Server.worldPlayerState(sourceClient.clientNum);  // ← 每客户端
    const auto bullet = Server.worldBulletExecutionStatus(sourceClient.clientNum);  // ← 每客户端
}
```

### 12.1 **每客户端四次额外 `Server.` 调用 + 一次 `Network.`**

**⇒ 如果 `source.clients` 有 18 个 ⇒ 90 次调用。**

**⚠ 而这是控制 socket 的 payload 生成 —— 按需调用还是每帧？**

**⇒ 如果每帧生成，这是一个明显的开销。**

**⇒ 但从"控制 socket"看，应该是**按请求**生成。**

**⇒ 待读调用点。**

### 12.2 ⚠ **`source` 与后续调用可能不一致**

**⇒ `gameplayPresentationStatus()` 返回一个快照，而后续四次调用各取**当前**值。**

**⇒ 所以这个 payload 是**多个时刻的混合**。**

**⚠ 这可能导致"客户端 A 的 reliableSequence 与客户端 B 的 origin 来自不同帧"。**

**⇒ 对于诊断可以接受，但对于精确重放不行。**

**⇒ 而 §278 开头的注释说"从**同一个样本**里减去目标的 origin"** —— 但 `sourceClient` 与 `worldPlayerState` 是**两次调用**。

**⚠ 所以"同一个样本"这个说法**与实现不符**。**

**⇒ 因为 `worldPlayerState(clientNum)` 与 `sourceClient.origin` 可能不同。**

**⇒ 但注释说的是"从同一个样本里减去目标的 origin" —— 而 `target->origin` 在 §273 里来自 `collisionEntities`，那是 trace 时的快照。**

**⇒ 所以在 §273 里确实是同一个样本，而这里只是**暴露**它们。**

**✓ 所以注释说的是 §273 的做法，这里只是搬运。**

## 十三、关键结论

1. **Frida 在专用服三次中两次杀掉它**，与 §275 的客户端 attach 失败是两个问题。
2. **结论相同：走控制 socket 而不是 Frida。**
3. **`start + (end - start) * fraction`** 与 §273 的 `axis()` lambda 同一公式。
4. **"减去目标 origin 得到离脚高度"** 与 §273 的 `hitZ` 完全相同。
5. **`optionalClient` 用 `0xFFFFFFFF` 而非 0** —— 因为 0 是合法客户端号。
6. **`plantedSiteLabel` 只在长度为 1 时取字符** —— 所以是 `"A"`/`"B"`。
7. **`GameplayClientStatus` 约 50 个标量 + 2 个数组**，加上 `sd` 的 18 个共约 70 个字段。
8. **六个 usercmd 时间点**直接暴露"卡在哪个阶段"（收到/派发/执行/待处理/丢弃）。
9. **`forwardMove`/`rightMove` 是有符号**（可负）。
10. **`UserCmd::angles` 是 `uint32` 而 `entity.angles` 是 `float[3]`** —— 两个表示。
11. **`bullet*` 的十个字段是 §272/§273 日志的程序化版本**，三种形式重叠但不相同。
12. **每客户端四次额外 `Server.` 调用** —— 18 客户端 = 90 次。
13. **payload 是多个时刻的混合**（`source` 快照 + 四次当前值）。

## 十四、未闭合点

- `dedicatedGameplayStatusPayload` 的调用频率（按请求还是每帧）。
- `BulletNoneEntityNum` 的具体值（与 §273 一致）。
- `recentReliableCommands` 是否就是 512 环的快照。
- `Appmain.cpp` 1920 行之后未读取。
