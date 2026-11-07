# 160 · netchan 接收与发送、三类客户端诊断探针、会话消费跟踪

## 一、范围

本报告学习 **4 处**：

- `qcommon/net_chan_mp.cpp` 869–1160 行（收包解析、发包、分片发送）——**该文件完整读完**
- `ClientCommandTrace.hpp`（81 行，完整）
- `DedicatedSessionConsumption.hpp`（109 行，完整）

## 二、客户端包头：13 字节

```text
+0..3   sequence
+4      serverId
+5..8   messageAcknowledge
+9..12  reliableAcknowledge
+13..   编码后的命令流
```

`ClientHeaderSize = 13`。

四条拒绝：

```text
sequence == 0 或 > 0x1FFFFFFF          "fragmented or invalid sequence"
messageAcknowledge > 0x1FFFFFFF        "outside the netchan sequence range"
sequence <= incomingSequence（已收到过）"duplicate or out-of-order"
reliable acknowledge 超出服务端序列      "exceeds the server sequence"
```

注意第一条的措辞：**分片标志位已经被 `rawSequence` 剥离后重建了**，所以走到这里 sequence 仍越界就说明重组流本身有问题。

## 三、两级 XOR：包体与字段

```cpp
decoded = Netchan_XorCommands(encodedCommands,
            challenge ^ serverId ^ messageAcknowledge,
            resolvedServerReliableCommand);

userCmdKey = checksumFeed ^ messageAcknowledge
           ^ Com_HashKey(resolvedServerReliableCommand);
```

**这是两个完全不同的密钥**：

- **包级**：`challenge ^ serverId ^ messageAcknowledge`，滚动 XOR 整个命令流；
- **字段级**：`checksumFeed ^ messageAcknowledge ^ Com_HashKey(relCmd)`，用于 usercmd 内部每个 delta 字段。

而 `Com_HashKey` 的输入是**服务端可靠命令的文本**——它必须来自 `reliableCommandResolver` 按 `parsed.reliableAcknowledge` 去查环。这就是为什么之前报告里说"key 无法从解码后的字节恢复"。

## 四、可靠命令序列必须严格 +1

```cpp
if (lastClientReliableSequence != 0 &&
    command.sequence != lastClientReliableSequence + 1)
    → "client reliable command sequence skipped from A to B"
```

注释：

> 一旦客户端命令游标存在，**每一条新记录都必须是下一个序列**。**跳号不能通过接受后面的文本来修复**：下一个 usercmd 的 key 是从可靠环条目导出的，**这么做会把之后所有包变成看起来很像的 XOR 噪声**。
>
> 第一条观察到的记录可能从 1 以上开始，因为连接建立可能早于这个源侧槽位——正如捕获里的 sequence-7 夹具。

这条与"重复旧 usercmd 不整包拒绝"形成对照：**usercmd 重复是无害的幂等，可靠命令跳号会让密钥错位**，所以一个是接受后丢弃、一个是立即拒绝。

## 五、发包：两条路径

### 5.1 未达到分片阈值

```text
payload = u32(reliableAcknowledge) + xor(commands, challenge ^ sequence)
result  = u32(sequence) + payload
++outgoingSequence
```

### 5.2 达到或超过 1154 字节

```text
if (payload.size() > 0x20000) 返回空
unsentFragments = true
reliableFragments = true      ← 选择性重传
unsentLength / unsentBuffer
fragmentSendCount.fill(0)
fragmentAcknowledgements.fill(0)
lowestFragmentSendCount = 0
→ TransmitNextFragment
```

注释说明了为什么必须是 `reliableFragments`：

> 分片消息使用 CODOL 的**选择性重传**传输。**bit30 声明那个模式**，对端返回 **bit29 加 128 位确认位图**，而 **`outgoingSequence` 只在每一片都被确认后才推进**。把这些当作**只有 bit31 的 fire-and-forget** 发送，会让一次丢失的 gamestate 或大快照分片**丢弃整条消息**。

## 六、分片发送：选择性重传的选择逻辑

```text
allAcknowledged = reliableFragments && 每一片都被 ACK
if (allAcknowledged) → ++outgoingSequence，清状态，返回空

if (reliableFragments):
    循环：找 fragmentSendCount[i] <= lowestFragmentSendCount 且未 ACK 的片；
          找不到就 ++lowestFragmentSendCount 再找
else:
    找第一个 fragmentSendCount[i] == 0 的片（严格按序）
```

**`lowestFragmentSendCount` 是一个阶梯**：它把所有片按"已发送次数"分层，先补齐发送次数最少的那一层。这是无显式 RTT 估计的选择性重传——**谁发得最少就重发谁**，天然实现了轮转公平。

`goto fragment_selected` 从双层循环里跳出来——这是少数 `goto` 用得恰当的地方（跳出内层并携带索引）。

### 6.1 分片头

```text
u32( outgoingSequence | (reliableFragments ? 0xC0000000 : 0x80000000) )
u8  fragmentIndex
u8  lastFragmentIndex
u16 fragmentStride (1154)
u16 fragmentLength
载荷
```

注意 `0xC0000000 = 0x80000000 | 0x40000000`（分片 + reliable），而不可靠只有 `0x80000000`。

### 6.2 推进时机

```text
可靠：只在"全部 ACK"时 ++outgoingSequence
不可靠：最后一片发出后立即 ++outgoingSequence 并清状态
```

这正是"放弃前确保送达"与"发完即忘"的分野。

## 七、`ClientCommandTrace`：三个探针，各有各的理由

### 7.1 为什么钩 `sub_614C00` 而不是 126 个 case 的 switch

> 剧场回放跑的是 out.exe 里**真实的客户端代码路径**——同样的解析、同样的分派、同样的处理器——所以这里的钩子观察到的是**零售服务端输出被零售客户端消费**，而我们同时也离线解码同一份 demo。**这是线本身给不了的东西：客户端对每个动词做了什么。**
>
> **目标是 `sub_614C00`（RVA 0x214C00），不是它下面那个 126-case switch。** 词汇表有**三个分派点**——`sub_613A40` 的 switch、`sub_614AC0` 处理 `'!'` 子帧、`sub_614C00` 自己处理断开路径。**`sub_614C00` 是唯一一个在分裂之前看到全部三者的。**

### 7.2 "频率就是安全论证"

> 零售 dm demo 在 **621 秒里 1478 条可靠命令**——约 **2.4/s**。2026-08-24，一个挂在**每帧**函数 `sub_54FDA0` 上的 Frida 钩子在 100–180 fps 下**同时崩掉三个在跑的客户端**；同一天没问题的两个探针只在**罕见路径**上触发。**这是罕见的那种。**

### 7.3 路径必须是绝对路径

> 写到**可执行文件旁边**的 `Ayria\Logs\client-commands.csv`。**不是相对路径**：`weapon-slots.csv` 曾经用相对路径打开，从客户端工作、**从 dedicated 静默什么都不做**，而审计两种情况下都报告了它的计数。

### 7.4 `installPlayerStateTrace`：不挂钩子的理由

> **不挂钩子。**我们已经在进程内，所以这是一条按定时器读内存的分离线程——**它不可能扰动它观察的代码**，而 trampoline 永远可能。**钩子用于事件；状态从来只需要一个读取器**，而"永不钩每帧函数"的整个危险在这里根本不适用。

**为什么值得 246 个字段**：

> `playerstate-0x00DA8540.tsv` 带 **246 个 netfield 跨 15,220 字节**，而**从未与除它自己之外的任何东西核对过**。剧场回放用零售客户端自己的代码把一份**零售 demo** 解码进那个结构，而我们离线解码同样的字节——**所以两者不一致的每一个字段都是我们的 codec 错了或者我们命名错了，一致的每一个字段都被验证了。**

输出规则：

> **只在一个 4 字节字变化时输出一行**，与 `demoq.py` 打印的规则相同，所以两边**可直接比对而不需要先对齐**。

### 7.5 `startFpsProbe`：`com_maxfps` 的上限是整数除法

```cpp
if (maxfps > 0) minMsec = 1000 / maxfps;   // 整数除法：200 → 5 ms
while (timeGetTime() - last < minMsec) Sleep(1);
```

> dvar 在 `0x004FC400` 注册，默认 200、最小 0、**最大 200**，所以图形菜单里没有任何东西能要求更多。`Com_Frame` 的限制器（`0x004FE220`，它自己的 profiler 作用域名就叫 "max fps spin"）然后做上面那段。
>
> `Sleep(1)` 加毫秒粒度的时钟把 5 ms 超到约 5.3，**这就是玩家看到的 ~186-190**。**零完全跳过限制器**（`minMsec` 保持 1），而零在 dvar 自己的范围内，**所以它是绕过那个天花板的唯一路径。**

报告时机：

> `set` 写值；采样总是跑。**在 `sampleMs` 之后报告到 game-server 日志，绝不在 bridge 的请求路径上**——一次同步返回的多秒测量正是一次让比赛卡住的原因。

## 八、`DedicatedSessionConsumption`：17 个阶段

```text
None / Queued / Processing
MapAssetLoadFailed / WaitingForMapAssets
ConfigStringGenerationResetFailed / WaitingForClientReadiness
WaitingForConfigStringGeneration / ConstantConfigStringsInitializationFailed
WeaponRegistryUnavailable / WeaponRegistryInitializationFailed
CharacterPresentationFailed / WeaponLoadoutFailed / ConfigureBookingFailed
Accepted / WorldInitializationFailed / SessionRosterRejected
```

跟踪器方法：`queued` / `processing` / `failed` / `waiting` / `accepted` / `characterFailure` / `status`。

**`waiting` 与 `failed` 分开**——等待不是一个错误，而"卡在等待"与"失败"的排查方向完全不同。

`queued()` 有一个细节：

```cpp
if (!status_.processedRequestId)
    status_.stage = Queued;
```

即**一旦处理过任何请求，后续入队不再把阶段改回 `Queued`**——避免迟到的入队请求覆盖已完成的阶段。

`characterFailure(failure, recordIndex, itemId)` 记录三个维度，其中 `recordIndex` 默认 `0xFFFFFFFF`（无效哨兵）。

与上一份报告的 `GameStateConfigurationTracker` 不同，这个跟踪器**没有 mutex 也没有日志**——它是纯状态快照，由调用方决定何时记日志。

## 九、关键结论

1. **两级 XOR 密钥**：包级用 `challenge^serverId^msgAck`，字段级用 `checksumFeed^msgAck^HashKey(relCmd)`；后者依赖可靠环文本，无法从字节反推。
2. **可靠命令必须严格 +1**，跳号会让后续所有包的 XOR 变成"看起来很像的噪声"；而 usercmd 重复只需接受后丢弃。
3. **分片必须 reliable**：只用 bit31 的 fire-and-forget 会让一次丢片毁掉整条消息（gamestate / 大快照）。
4. **`lowestFragmentSendCount` 是分层轮转**——无 RTT 估计的选择性重传。
5. **钩子频率就是安全论证**：2.4/s 的罕见路径可以钩，每帧函数会把三个客户端一起崩掉。
6. **状态只需要读取器**，不需要钩子；钩子用于事件。
7. **`com_maxfps` 的 200 上限是整数除法 + Sleep(1) 的结果**，零是唯一绕过路径。

## 十、未闭合点

- `Netchan_Process` 中 `moveCommandCount` 之后的水位线判定在 `ServerCore` 侧，不在本文件。
- 三个探针的实现（`.cpp`）不在本组。
- `DedicatedSessionConsumptionTracker` 没有互斥，调用方必须保证单线程。
