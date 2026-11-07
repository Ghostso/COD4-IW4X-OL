# 149 · 可破坏物、计时统计、原生 pmove ABI、UDP 传输

## 一、范围

本报告完整学习 **4 个文件**：

- `sv_destructible_mp.hpp`（107 行）
- `sv_frame_diagnostics.hpp`（59 行）
- `sv_native_pmove_mp.hpp`（前 100 行，ABI 断言部分）
- `sv_network_mp.hpp`（69 行）

`server_mp` 进度推进到 **127/154**。

## 二、可破坏物：溢出伤害必须结转到下一阶段

### 2.1 三层层级

```text
SvDestructibleStageDefinition{ health, replacementModel }
SvDestructibleDefinition{ type, stages[], destroyedModel }
SvDestructibleState{ stageIndex, health, destroyed }
```

注释点明关键设计：

> 显式状态避免从**重复的血量值**推断阶段。IMMEDIATE：如果两个阶段血量相同，靠比较血量无法知道现在是哪个。

`SvDestructibleDamageResult{ state, enteredStages[], enteredDestroyedState }` —— `enteredStages` 可以**一次进入多个**（溢出结转）。

### 2.2 引用来源与准入门

> 只准入**精确的 CODOL MapEnt 类型名**、且其状态血量序列存在于原始 IW4 脚本中的定义；这是脚本数据，不是原生布局。

`TODO(CODOL)` 写得很有约束力：

> 在找到它们各自的 title-local 状态表与表现之前，**不要加** `tropical` / `ratnest02` / `tubetvsound` / `ceiling-fan` 变体。

即：**宁可不支持，也不要套一个 IW4 的表**。

### 2.3 表现解析

`SvResolvedDestructiblePresentation`：

- `stageModelIndexes`（与 stages 一一对应）；
- `destroyedModelIndex`；
- `stageEvents`（外层与 stages 一一对应）；
- `destroyedEvents`。

注释："asset 索引与事件计划在 owner 注册前解析、事务地提交。" 空 `stageEvents` 表示"没有恢复的表现副作用"——**明确区分空与未恢复**。

`SV_ApplyDestructibleEntityDamage(def, presentation, payload, state, currentModelIndex)` 返回 `SvEntityDamageMutation`（候选，不是提交）。

## 三、帧计时：七个桶，1/2/5/10/20/50 ms

```text
buckets[0] : <= 1 ms
buckets[1] : <= 2 ms
buckets[2] : <= 5 ms
buckets[3] : <= 10 ms
buckets[4] : <= 20 ms
buckets[5] : <= 50 ms
buckets[6] : > 50 ms
```

`record()` 用 `find_if` 找第一个满足 `microseconds <= threshold` 的阈值；**一个都不满足时 `find_if` 返回 end ⇒ 下标 6**，正好是"超过 50 ms"桶。这个写法让七桶的语义只有一处定义。

`take()` 读出并清零（窗口式采样）。

`SvTimingWindow` 记 `count / total / last / maximum / buckets[7]`，`averageMicroseconds()` 在 count 为零时返回 0。

## 四、原生 pmove：ABI 逐字段钉死

### 4.1 两个结构的尺寸

```text
usercmd_s = 0x2C
pmove_t   = 0x12C
```

### 4.2 那段"复查过、没变"的论证

注释说明为什么要写这段：

> **已在本 build（1649370）上核对且未变**——记录下来是因为"与 3.3.3.3 树完全相同"是一个**怀疑**，而退役一个怀疑的方法是去核对，不是让它保持模糊。

核对方式：

```text
Pmove    A 0x41E860 / C 0x41DCD0
（各自只有一个调用点，各自只在一个地方调 PmoveSingle）
两者以相同的位移遍历 pmove_t：
    0x00, 0x04, 0x08, 0x0C, 0x1E, 0x28, 0x60, 0x128
0x128 是 0x12C 结构的最后一个 dword
0x1E 是 cmd + 0x1A = forwardMove
⇒ 两个布局都成立
```

**而在两个 profile 之间确实移动了的每一个位移，都是通过 pmove_t 第一个成员到达的 playerState 偏移**：

```text
0x2A8/0x2AC -> 0x30C/0x310
0x28/0x2C/0x30 -> 0x3C/0x40/0x44
```

netfield 表与之一致 ⇒ **这些差异佐证了 §34，而不是与本节矛盾**。这是一条很干净的方法论：区分"结构本身的位移"与"结构成员指向的位移"。

### 4.3 `SvNativeUserCmd` 的字段与断言

```text
+00 commandTime (u32)
+04 buttons     (u32)
+08 angles[3]   (u32×3)
+14 weapon      (u16)
+16 offHandIndex
+18 lastWeaponAltModeSwitch
+1A forwardMove (i8)
+1B rightMove   (i8)
+1C conditionalAngle (f32)
+20 conditionalByte
+21 padding21
+22 conditionalElevenBits (u16)
+24 selectedLocation[3]
+27 selectedDirection[2]
+29 padding29[3]
```

static_assert 钉死：`sizeof == 0x2C`、`buttons @0x04`、`angles @0x08`、`weapon @0x14`、`forwardMove @0x1A`、`conditionalAngle @0x1C`。

### 4.4 `SvNativePmove` 的字段与断言

```text
+000 playerState (byte*)
+004 cmd
+030 oldcmd
+05C traceMask
+060 numTouch
+064 touchEntities[32] (i32)
+0E4 bounds
+0FC xySpeed
+100 proneChange
+104 mantleStarted
+105 padding105[3]
+108 mantleEndPosition[3]
+114 mantleDuration
+118 viewChangeTime
+11C viewChange
+120 torsoPitch
+124 waistPitch
+128 handler
+129 padding129[3]
```

static_assert：`sizeof(void*)==4`（"CODOL native ABI requires x86"）、`sizeof == 0x12C`，以及**十四个字段偏移逐个断言**。

这些断言的价值：**编译器在任何一处布局漂移时立刻失败**，而不是在活客户端上表现为"动不了"或"穿墙"。

## 五、UDP 传输

```text
MaxPacketsPerFrame = 64
MaxPacketSize      = 65'507     // UDP 最大载荷
默认端口            = 28960      // CoD 系列默认
```

`SvNetworkStatus`：bound / port / packetsReceived / packetsSent / lastPacketReceivedTime / lastPacketSentTime / lastSocketError。

`SvPeerNetworkStatus` 按 peer 记：`sendAttempts / sendSucceeded / sendFailed / bytesSent / lastSendTime / lastSendBytes / lastSendError`。

`peerStatus_` 用 `unordered_map<uint64_t, ...>`，键是 peer——与之前报告里 socket 层的 `(ipv4<<16)|port` 一致。

`NET_Frame(ServerCore&, now)` 与 `NET_SendPackets(span, now)` 分开：**收帧与发帧是两个阶段**，中间是 ServerCore 的 world frame。这与 Appmain 的 0-8 帧阶段划分吻合。

`mutex_` 保护 status 与 peerStatus_——因为控制线程（日志/状态查询）与帧线程并发访问。

## 六、关键结论

1. **可破坏物的阶段必须显式存**，不能从血量反推（重复血量值会歧义）；真值来自 IW4 脚本表，且只接受**精确类型名**。
2. **pmove ABI 的核对方法值得复用**：区分"结构位移"与"结构首成员指向的位移"——前者必须相同，后者变了反而是佐证。
3. **十四个 offsetof 断言**把 ABI 漂移变成编译错误，而不是活客户端上的"动不了"。
4. **UDP 收/发分离**（`NET_Frame` 与 `NET_SendPackets`）是帧阶段划分在传输层的对应物。

## 七、未闭合点

- CODOL 专有的可破坏物变体（tropical / ratnest02 / tubetvsound / ceiling-fan）全部未支持，且明确禁止套用 IW4 的表。
- `NET_SendPackets` 的 64 包/帧上限与 `MaxPacketSize` 在 MTU 层面没有分片逻辑（分片在 FAT 帧层，见其他报告）。
