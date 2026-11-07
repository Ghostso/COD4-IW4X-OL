# 158 · netchan 解码器、WinSock 传输、帧钩子、gamestate 配置跟踪

## 一、范围

本报告学习 **5 个文件**：

- `qcommon/net_chan_mp.cpp` 前 550 行（usercmd 解码器）
- `win32/win_net.hpp`（45 行，完整）+ `.cpp` 前 120 行
- `FrameHook.hpp`（12 行，完整）
- `GameStateConfiguration.hpp`（151 行，完整）

## 二、usercmd 解码器：一次"一位之差"的完整病理

### 2.1 读取器

```cpp
class ClientCommandReader {
    readBits(count)      按位读，LSB 优先
    readByte/readShort/readLong/readString
    consumedBits()       诊断用：位游标位置
};
```

`readBits` 的位序：`(data_[bit/8] >> bitInByte) & 1` 放在结果的第 `index` 位 —— **每个字节内 LSB 先出**。

`readString(capacity)` 找 NUL，若 `size >= capacity` 拒绝。

### 2.2 键控读取

```cpp
readKey(reader, key, bits):
    encoded = readBits(bits)
    return encoded ^ (key & bitMask(bits))
```

`readDelta`：

```cpp
changed = readBits(1)
if (!changed) → true，取 baseline
encoded = readValue()
value = encoded ^ (key & bitMask(bits))
```

即：**先读 1 位 changed；未变则用基线**。这正是"空闲客户端完美解析"的原因——所有字段都走 baseline 分支，一位也不多。

### 2.3 那一段病变过程

注释写得极清楚：

> **这些是武器索引，而这里它们是十一位。** `sv_gamestate_mp.cpp` 已经带着推导——"武器块从 900 长到 1700，所以武器索引从 10 位拓到 11 位"，`WeaponIndexBits = 11`——**而本解码器是 3.3.3.3 的逐字拷贝，仍在读十位。**
>
> **它就按"每个字段少一位"必然的方式失败**：一个 delta 字段在**未变化时不花任何成本**，所以空闲客户端解析得完美——日志里是几百条干净命令。**玩家一出生、手里有武器，字段就开始变化，三个字段各少读一位，流就滑位了。**报出来的失败永远是 trailer，而那只是伤害变得可见的地方——trace 显示 buttons 那时解成 `0x146574C3`，各种门随机打开。

三个武器索引字段：`weapon` / `lastWeaponAltModeSwitch` / `offHandIndex`，每个 11 位。

### 2.4 差分链的四层

```text
1. deltaTime(1) + byte 或 long
2. changed(1)  → 未变则读 3 位 trailer 且必须 == 7
3. full(1)
4. fieldKey = full ? key : commandTime ^ key
5. attack(1) → buttons 最低位
6. angles[0..1] 各 16 位
7. movement 4 位（forward/right 各 ±>10 编码成掩码）
8. 若 !full → 读 3 位 trailer 且必须 == 2，返回
9. extendedKey = commandTime ^ key
10. angles[2] 16 位
11. buttons 29 位（左移 1 位后合并 attack 位）
12. 三个武器索引各 11 位
13. 按 buttons 位：0x20000 → selectedLocation[3] 各 8 位
              0x200000 → selectedDirection[2] 各 8 位
              0x4     → conditional{angle 16, byte 8, elevenBits 11}
14. 3 位 trailer 且必须 == expectedTrailer(5)
```

### 2.5 移动的 ±10 阈值

```cpp
movementMask: forward > 10 → 1，< -10 → 2；right 同理 4/8
setMovementMask: 1 → +127，2 → -127
```

即**行走意图被量化成 4 位掩码**，恢复时变成 ±127。这是线格式，不是服务端决策——服务端看到的是 ±127 或 0。

### 2.6 conditional 角的两组常数

```cpp
baselineAngle = (int16)(baseline.conditionalAngle * 182.0444488525391f)
conditionalAngle = (float)(int16)value * 0.0054931640625f
```

`182.0444... = 65536/360`（度→短角），`0.0054931... = 360/65536`（短角→度）——与 `com_math.hpp` 的两个比例完全一致，只是这里写成了字面量而不是引用常量。

### 2.7 `UserCmdTrace`：为什么 trailer 不是罪魁

```cpp
struct UserCmdTrace {
    deltaTime, changed, full, buttons;
    selectedLocation, selectedDirection, conditional;   // 三个门
    bitsAtTrailer;                                      // 位游标位置
};
```

注释：

> usercmd 读取器能撑过几百条命令然后失步，这意味着**某个空闲路径从不触及的字段上，宽度或门是错的**——只有玩家出生并按键时才显露。**一个拒绝原因点名的永远是最后失败的检查，绝不是吃错位数的那个字段**，而这两者按构造就是不同的字段：**trailer 只是伤害变得可见的地方。**

> 所以记录走的分支和每一个条件门，让调用方把它打印在原始位旁边。然后可以**手工对着位流找失步**，而不是每猜一次再跑一轮。

`bitsAtTrailer` 尤其重要：**同样的失败原因，不同的位游标位置，就能区分"这里错"与"前面某处错"**。

### 2.8 命令流的解析顺序

```text
loop:
    terminal = readBits(3)
    if terminal == 2 (Reliable):
        最多 256 条；sequence(long) + string(<1024)
        continue
    if terminal > 3: 未知，拒绝
    terminal ∈ {MoveDelta(0), MoveNoDelta(1)}:
        count = readByte()
        必须 ∈ [1, 32]
```

**32 条上限**与之前报告里 `PendingUserCmdCapacity = 32` 完全对应——CODOL 客户端单包最多 32 条。

### 2.9 那段关于"基线起点"的实战教训

这是本组最有价值的一段：

> **链的起点是已确认的 playerState 基线。**
>
> `CL_WritePacket 0x005B2C10` 在选择 `clc_move`/`clc_moveNoDelta` **之前**调一次 `MSG_SetDefaultUserCmd 0x0066F170`，把那个本地命令存为第一个基线，然后**只在包内的 `MSG_WriteDeltaUsercmdKey` 循环里推进基线**。**它从不以上一个包的 usercmd 作为包起点。**
>
> **上一个命令的覆盖在 Wetwork 的炮塔过场里是致命的。**它把按钮 `0x4` 跨包边界保留下来，于是本读取器进入了可选的 35 位 conditional 块，**而客户端是按清零的默认值编码并省略了它**。于是每一个已出生玩家的包都在 trailer 上失败，**没有任何鼠标输入到达 pmove**。

即：错误地沿用上一条 usercmd 当基线，会让一个按钮位跨越包边界"粘住"，进而让读取器读一个客户端根本没写的可选块。

## 三、WinSock 传输

### 3.1 建立顺序（每一步失败都 close）

```text
WSAStartup(2,2)
socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
ioctlsocket(FIONBIO, 1)           非阻塞
setsockopt(SO_BROADCAST, TRUE)
bind(0.0.0.0:port)
getsockname()  → 记录实际端口（port=0 时由系统分配）
```

注释：`SO_BROADCAST` 开着——大厅发现/局域网可能需要广播。

### 3.2 状态

```text
socket_  = uintptr_t(-1) 表示无效
port_    = 绑定后读回的实际端口
lastError_
winsockStarted_
```

`close()` 同时 `closesocket` 与 `WSACleanup`，并把 `winsockStarted_` 清回 false。

`NetPacketResult` 三态：`Empty / Received / Error`——**空与非空、错误与空分开**。

## 四、帧钩子

```cpp
using FrameCallback = void (*)(std::uint32_t nowMilliseconds);
bool installFrameHook(const EngineBindings&, FrameCallback);
```

**只有这一个函数**。签名说明两件事：

1. 回调是**裸函数指针**不是 `std::function`——避免在引擎线程里做任何分配；
2. 时间由引擎传进来（`nowMilliseconds`），不由插件自己取时钟。

## 五、gamestate 配置跟踪：18 个阶段，一个都不曾上报

### 5.1 阶段枚举（18 项）

```text
None / Processing / InvalidChecksum / MapCenterUnavailable
CharacterUnavailable / PreparedLoadoutMismatch
DynamicWeaponRangeUnavailable
PrimaryDependencyRegistrationFailed / PrimaryWeaponRegistrationFailed
SecondaryDependencyRegistrationFailed / SecondaryWeaponRegistrationFailed
CharacterChanged / ServerCommitFailed / Accepted
DynamicWeaponRegistryUnavailable / DynamicWeaponRegistryRegistrationFailed
MiniMapUnavailable / ObjectiveMaterialUnavailable
```

### 5.2 那段说明为什么需要它

> 下面每一个阶段都是 gamestate 可能配置失败的一种不同方式，**而它们没有一处被上报过**：不在日志里，也不在 dedicated 控制口上。在 loadout 解析器更早拒绝、这段代码够不着的时候，这还能忍。**它在 booking 开始成功的那一刻就不再能忍了**，因为帧线程然后停在这段里的某处，**而最后打印的那一行是唯一说明停在哪里的东西。**

### 5.3 跟踪器的设计

```cpp
processing()               ++attemptCount，重置 mask/failedClassIndex，记日志
dynamicWeaponRange(idx)    记 firstDynamicWeaponAssetIndex
registeredClass(classIdx)  registeredClassMask |= 1 << classIdx
failed(stage, classIdx)    记日志
accepted()                 记日志，含 classMask 与 firstDynamicWeapon
status()                   mutex 保护返回快照
```

`failed` 与 `accepted` 都**带日志**，`processing` 也带——所以"卡住"表现为**最后一行是 `stage=processing` 而没有后续**，这正是注释描述的症状。

`registeredClassMask` 是位掩码，所以"注册到第几个失败的"能一眼看出。

`std::mutex` 保护——因为这个状态由帧线程写、由控制线程读。

## 六、关键结论

1. **一位之差在空闲时完全不可见**：delta 字段未变时不花成本，所以只有玩家出生并按东西时才暴露。这类缺陷**必须在有武器、有输入的场景下测**。
2. **trailer 只是伤害可见的地方**，不是出错的地方。要让诊断带上**每个条件门与位游标位置**，才能手工对位流。
3. **基线起点必须是客户端自己的 `MSG_SetDefaultUserCmd`**，沿用上一包会把按钮位跨包粘住，进而读一个不存在的可选块。
4. **每一条失败路径都必须有独立名字**（18 个阶段），否则"卡住"只剩最后一行日志。
5. **帧回调用裸函数指针**，不引入分配。

## 七、未闭合点

- `NetUdpSocket` 的 `NET_GetPacket` 只读到 120 行，后续（peer 解析）未在本组。
- `installFrameHook` 的实现不在本组。
