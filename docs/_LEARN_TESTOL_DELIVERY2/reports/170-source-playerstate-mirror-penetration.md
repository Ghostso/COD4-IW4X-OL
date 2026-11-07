# 170 · playerstate 镜像线程、穿透深度

## 一、范围

本报告学习 **2 处实现**：

- `ClientCommandTrace.cpp` 419–598 行（playerstate 镜像）
- `NativeWeaponBindings.cpp` 378–434 行（穿透深度）——**该文件在本组读取范围内完整**

## 二、`cg` 的三条指令与三个全局

```text
mov edx, dword_82C3B58                 ; RVA 0x7EC3B58  索引
mov esi, dword_1C1D188[edx*4]          ; RVA 0x181D188  数组
xor esi, 0FBB2C97Ah                    ; 键
```

注释补充了一个尺寸事实：

> 三个全局都住在 `.data`，**其虚拟大小是 229.8 MB 对磁盘上的 10.5 MB**。

即 `.data` 的 `SizeOfRawData` 与 `VirtualSize` 差二十倍——这是 BSS 占大头。这也解释了为什么用 RVA 而不是"扫文件找字符串"。

### 2.1 未设置槽位显式处理

```cpp
// AN UNSET SLOT XORS TO THE KEY ITSELF. Zero ^ key is a 4 GB-ish pointer that VirtualQuery
// would reject anyway, but saying it here makes the "not in a match yet" case explicit
// rather than a mystery in the unresolved counter.
if (!obfuscated) return nullptr;
```

`0 ^ 0xFBB2C97A = 0xFBB2C97A`，一个约 4 GB 的指针。`VirtualQuery` 会拒，但**显式写出来让"还没进比赛"成为一个明确状态**而不是未解析计数里的谜。

## 三、三个镜像区域及各自的理由

```cpp
struct Region { const char* name; size_t offset; size_t bytes; bool fromCg; };

{ "ps",  0x000000, PlayerStateBytes(0x3B78), true  },
{ "ci",  0x180C50, 0x450 * 18,               true  },
{ "clc", 0x000000, 0x400,                    false },
```

注释写得很清楚：

- **`ps`**：`cg + 0`，246 字段的 playerState，**已经 116/120 验证过**；
- **`ci`**：`cg + 0x180C50`，clientInfo，步长 `0x450` —— "名字、模型、军衔"。**从 `CG_DrawCompassBlip` 读出**：`clientInfo = cg + 0x180C50 + 0x450*clientNum`；
- **`clc`**：命令环基址，**它就是 clientConnection**：它的环坐在 `+524628`，所以它的头部持有序列计数器。

`clc` 的理由最巧：

> 采样它是为了**经验性地找到快照边界**——命令分派器的**唯一调用者是 158 KB 函数里的五个位置**，那不是一个该钩的东西，**而一个每秒约 20 次跳动的计数器无论如何就是那条边界。**

即：**钩不了就采样**，而一个自然跳动的计数器承担了同样的观测作用。

`0x3B78` = 246 个 netfield 覆盖 `0x0..0x3B74` 再往后一个字。**这个数来自 `playerstate-0x00DA8540.tsv`，不是估的。**

`0x450 * 18` = clientInfo 表 18 个槽 —— 与全项目 18 客户端上限一致。

## 四、镜像线程：只在**字变化**时输出

```cpp
while (PsRecording) {
    cg = resolveCg(); clc = resolveClc();
    if (!cg) { ++PsUnresolved; Sleep(interval); continue; }
    ++PsSamples;
    memcpy(&commandTime, cg, 4);          // 索引 0 = commandTime，join key
    lock(PsGate);
    for each region:
        base = fromCg ? cg+offset : clc;
        if (!readable(base, bytes)) continue;       // 逐区域跳过，不中止整轮
        memcpy(current, base, bytes);
        if (!seeded) { previous = current; seeded = true; continue; }
        for (offset = 0; offset+4 <= bytes; offset += 4)
            if (was != now)
                fprintf("%lu,%u,%s,0x%05zX,%u,%u\n", tick, commandTime, name, offset, was, now);
        previous = current;
    fflush();
    Sleep(interval);
}
```

### 4.1 `commandTime` 是 join key

> `commandTime` 是 playerState 索引 0、偏移 0 —— **demoq.py 每次变化时打印的第一个字段**。**它是 join key：两边都能引用它，而谁都不必猜对方的时钟。**

### 4.2 逐区域 `continue` 而不是 `break`

一个区域不可读只跳过它，其余区域继续。**这是"部分可用优于全不可用"**。

### 4.3 4 字节对齐扫描

`offset += 4`，`offset+4 <= bytes` —— 只比 4 字节字。这与 `playerstate-...tsv` 的 netfield 表是 4 字节字对齐的一致，也解释了为什么"246 字段"能按字覆盖。

**代价**：1/2 字节字段的变化会表现为它所在那 4 字节字的变化，无法区分同字内两个字段。这是**刻意接受的**，因为目标是"与 demoq.py 的直接比对"。

### 4.4 三个计数器

```text
PsSamples     成功采样轮数
PsChanges     变化的字数
PsUnresolved  cg 解析失败次数
```

**与命令追踪的 `Recorded`/`Unreadable` 完全同构** —— 成功与失败的计数必须并列。

### 4.5 先 flush 再 Sleep

```cpp
std::fflush(PsOutput);
Sleep(PsInterval);
```

顺序正确：**先落盘再等**，而不是等完再落盘（后者会让最后一批数据在崩溃时丢失）。

## 五、不是钩子，是线程

注释（在函数入口上方）：

> playerState 只是我们**能读的内存**。一个 trampoline 会把我们的代码放到引擎自己的执行路径上，**毫无收益**——**而那条路径正是在它按帧跑时一次杀死三个客户端的那个**。读取不能。

这与头文件里的"钩子用于事件；状态只需要读取器"完全一致。

`PsInterval = 50` 默认 —— 20 Hz，与零售服务端节拍一致。

## 六、穿透深度：一次乘法与一次除法

### 6.1 四道前置

```cpp
!weaponAssetIndex || > MaximumWeaponAssetIndex    → 拒绝
!surfaceType || surfaceType >= BulletSurfaceTypeCount (31)  → 拒绝
!valid() || 线程不符                              → 拒绝
```

`surfaceType >= 31` 与之前报告里"表面索引空间 0..30"一致。

### 6.2 取 WeaponDef

```cpp
slot = ((const uint8_t* const*)module_ + WeaponDefinitionsRva) + weaponAssetIndex;
definition = *slot;
if (definition) { ... }
```

`definition` 为空时**不报错**，直接落到 `completed=false` → 返回 nullopt。

### 6.3 原生调用

```cpp
double (*)(const void*, int32) at module_ + 0x02EC00
= BG_GetSurfacePenetrationDepth
```

返回 **double**（不是 float）——这是原生自己的返回类型。

### 6.4 那两步缩放

```cpp
penetrationScale = *(const float*)(definition + 3704);   // 0xE78
lossScale        = *(const float*)(definition + 3708);   // 0xE7C
if (lossScale == 0.0f) lossScale = 1.0f;

depth = (float)surfaceFactor * penetrationScale / lossScale;
```

注释：

> OLFinal `sub_5923C0` 把材质表乘以 `WeaponDef+0xE78`，然后按 `+0xE7C` 缩放厚度损失（**零表示 1.0**）。**返回等效深度，这样源循环可以保留 `damage -= thickness / depth`。**

即：源侧的循环用 `damage -= thickness / depth`，所以这里返回的是**等效深度**而不是直接返回损失。

`0xE78 = 3704`、`0xE7C = 3708` —— 两个相邻 float。**`lossScale == 0` 视为 1.0** 是原生语义（除零保护）。

### 6.5 结局校验

```cpp
return completed && isfinite(depth) && depth >= 0.0f && depth <= MaximumWeaponDamageRange
    ? optional{depth} : nullopt;
```

`MaximumWeaponDamageRange = 1000000.0f` —— 与 `sv_weapon_fire_mp.hpp` 里的常量一致。

`depth` 初值 `quiet_NaN()`，所以"没算"与"算出 NaN"都会在 `isfinite` 处被拒。

## 七、关键结论

1. **"钩不了就采样"**：158 KB 函数里的五个调用点不该钩，而一个每秒 20 次跳动的计数器承担同样的观测作用。
2. **`commandTime` 是跨工具 join key**——两边都能引用，都不必猜对方时钟。
3. **逐区域跳过而非中止**，部分可用优于全不可用。
4. **4 字节对齐扫描是刻意的取舍**：与 demoq.py 直接可比，代价是同字内字段无法区分。
5. **未设置的混淆槽位要显式判**，让"还没进比赛"成为明确状态。
6. **零缩放的替代值是 1.0**，这是原生语义而非防御性默认。

## 八、未闭合点

- `installPlayerStateTrace` 的安装部分与 `startFpsProbe` 未在本组读取。
- clientInfo 的 `cg + 0x180C50` 只核对过"名字/模型/军衔"三类字段，其余未验证。
