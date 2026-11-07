# 269 · `EngineMsgWriter` 收尾、`armNativeFaultWitness` 的客户端载荷 —— **`EngineBindings.cpp` 全文读完**

## 一、范围

本报告学习 `EngineBindings.cpp` 18434–18488 行（文件末尾），并对整个文件做一次总账。

## 二、`MSG_WriteBits` 的**单条件**

```cpp
void EngineMsgWriter::MSG_WriteBits(const std::int32_t value, const std::uint32_t bits)
{
    if (!message_.overflowed)
        bindings_.MSG_WriteBits(message_, value, bits);
}
```

### 2.1 只有 `!overflowed`

**⇒ 没有对 `bits` 的范围检查、没有对 `value` 的符号检查。**

**⇒ 所以 `MSG_WriteBits` 原语被**完全信任**。**

**⇒ 与 `MSG_WriteData` 的四项检查**不对称**。**

**⚠ 这是一个设计选择** —— 因为 `MSG_WriteBits` 的溢出检测在原生函数内部（它自己有 `overflowed` 检查）。

**⇒ 而 `MSG_WriteData` 我们自己做 memcpy，所以必须自己检查。**

**✓ 合理。**

## 三、`MSG_WriteString` 的**NUL 拒绝**

```cpp
void EngineMsgWriter::MSG_WriteString(const std::string_view value)
{
    if (message_.overflowed || value.find('\0') != std::string_view::npos)
    {
        message_.overflowed = 1;
        return;
    }
    const std::string terminated(value);
    bindings_.MSG_WriteString(message_, terminated.c_str());
}
```

### 3.1 两项

```text
!overflowed
value 不含 NUL          ← 【关键】
```

### 3.2 **为什么拒绝内部 NUL**

**⇒ 因为 `MSG_WriteString` 原语写的是 C 字符串（遇 NUL 停）。**

**⇒ 如果 `value` 内部有 NUL，写入会**提前截断**，而 `cursize` 会**小于**预期 ⇒ 后续字节偏移全错。**

**⇒ 所以标记 `overflowed` 而不是静默截断** ✓

**⇒ 与 §257 的"内部 NUL ⇒ 拒绝"同族。**

### 3.3 而 `std::string terminated(value)` 保证 NUL 结尾

**⇒ 因为 `value` 是 `string_view`（可能不 NUL 结尾）。**

**⇒ 所以必须拷贝一份。**

**⇒ 与 §243 里 `resolveKillstreakWeapon` 的 `std::string ownedName(name)` 同族。**

## 四、`data()` 的**空返回**

```cpp
std::span<const std::uint8_t> EngineMsgWriter::data() const
{
    if (message_.cursize <= 0)
        return {};
    return { message_.data, (size_t)message_.cursize };
}
```

### 4.1 三项

```text
cursize <= 0   ⇒ 空 span        （含 overflowed 导致的负值？）
否则            ⇒ [data, cursize)
```

**⚠ 如果 `overflowed` 但 `cursize > 0`，返回**部分数据**。**

**⇒ 所以调用者必须先查 `overflowed()`。**

**⇒ 而 §268 的 `validateMessageBindings` 正是先检查 `overflowed` 再用 `data()`** ✓

### 4.2 `cursize <= 0` 而不是 `== 0`

**⇒ 防负值**（虽然 `cursize` 不应为负）。

## 五、`armNativeFaultWitness`（本组最重要的一段）

```cpp
// Let the CLIENT arm the same witness. The dedicated arms it around native
// animation init; the client has no equivalent choke point, and the crash worth
// catching happens there. HANDOFF section 152w.
void armNativeFaultWitness(void *const module)
{
    armVectoredFaultWitnessImpl(static_cast<std::uint8_t *>(module));
}
```

### 5.1 三层

```text
1. 专用服把它装在【原生动画初始化】周围
2. 客户端【没有等价的咽喉点】
3. ⇒ 而值得抓的崩溃发生在客户端
```

### 5.2 而"值得抓的崩溃"与 §255 的六份 `ClientException`

**§255**：

```text
6 份 ClientException，最内层帧都是 sub_779510 +0x230
其中 3 份先于本批次
```

**⇒ 所以这个 `armNativeFaultWitness` 的存在理由就是**抓那些**。**

**⇒ 而 §255 的 `profileSlotProbeEnabled` 的判定是"暗示而不是证明"。**

### 5.3 `static_cast<std::uint8_t*>(module)`

**⇒ 把 `void*` 转成字节指针，因为 `armVectoredFaultWitnessImpl` 需要做地址算术。**

### 5.4 而它是一个**自由函数**而不是成员

**⇒ 因为客户端侧可能没有 `EngineBindings` 实例。**

## 六、**`EngineBindings.cpp` 的总账**

### 6.1 体量

```text
917,344 字节
~17,867 行（Get-Content 计） / 18,488（Read 计，因混合行尾）
```

### 6.2 学过的分段（266 份报告覆盖的第一批从 1 起）

| 行段 | 报告 | 主题 |
|---|---|---|
| 1–2205（hpp） | 181–190 | `EngineBindings.hpp` |
| 192–213 | 192–213 | DObj 步长、VEH、栈扫描、AVX 适配器、前缀守卫、玻璃上限 |
| 214–222 | 214–222 | `bind()` 五段、80 项 `valid()`、稀疏槽、两种变体 |
| 223–239 | 223–239 | 插值选择器、三个时钟、DObj 三层、`0x118..0x168`、镜像事务 |
| 8897–9242 | 239–240 | 布局对照、两个 `call_once`、附件在武器**之前** |
| 9242–9505 | 241 | 160 字节记录、四武器=两职业、`missing_playerstate` 三死假设 |
| 10038–10320 | 242 | 384 位掩码、`__usercall` 探针、桶式查找 |
| 10323–10702 | 243 | 诊断路径、686 对照、零与错地址 |
| 11023–11213 | 244 | 空白 `enabled` 三次判定、14 表 `-?.y` 见证 |
| 11285–11695 | 245 | `volatile` 是载荷、`stage`/`faultStage`、两次遍历 |
| 11697–12050 | 246 | alpha 七态机、客户端恒真、发布手法 |
| 12050–12450 | 247 | 代际哨兵、zone 借用、材质路由五项 |
| 12450–12850 | 248 | 九位 presence、四级回退链、XModel 三层偏移 |
| 12863–13250 | 249 | 流式 15 秒等待、`+0x10/+0x18`、48 个 XAnim 槽 |
| 13222–13650 | 250 | 骨骼审计、`XSurface` 0x54、两代偏移对照 |
| 13597–14050 | 251 | 模板审计四类行、`3/2/4` 三字节、附件翻译 |
| 14050–14450 | 252 | `0x514` 界、本地化键当武器名、六级跳过 |
| 14450–14755 | 253 | `** <weapon> 0 0 <ids>`、FMJ、键空间不匹配 |
| 14850–15050 | 254 | 技能两表 192 位 MSB/LSB 相反、`profile +1` |
| 15045–15260 | 255 | `ProfileManagerRva` 不是指针、`NULL/EMPTY/UNREADABLE` |
| 15437–15850 | 256 | 两级捕获、九槽 vs 十二宽、十一项选择名 |
| 15850–16050 | 257 | `custom1..5`、`MapEnts` 两种命名、三项界 |
| 16050–16250 | 258 | 触发体三层、玻璃两关系 27/27、162 方向 |
| 16250–16450 | 259 | `5236` 记录、170–320 ms、`_stricmp` |
| 16442–16650 | 260 | XAnimParts 六偏移、动画树 BST、165–300 ms |
| 16650–17030 | 261 | 脚本串池、声音别名三源、`63` 次失败 |
| 17030–17250 | 262 | `0x077D8188` 头表、16 类型穷举、碰撞图 |
| 17216–17450 | 263 | `TRACE CENSUS`、**两个 trace 参数互换** |
| 17450–17650 | 264 | **第三个 trace ABI**、12 字节当 40 字节缓冲 |
| 17650–17850 | 265 | **这个 build 没有 SV_Trace**、319/319、四 vs 二调用者 |
| 17850–18050 | 266 | `result.fraction` 预置、`toLocal`、`walkable 0.7` |
| 18050–18250 | 267 | 两种预置、半径 vs 子弹 trace、七个拒绝 |
| 18250–18450 | 268 | actor 700..707、`isLinked` 我们写零、512 不是 256 |
| 18434–18488 | 269 | 收尾 |

### 6.3 **本文件的五个最重要发现**

#### ① **三个 trace 函数三种 ABI，且两个在 build 之间参数互换**

```text
worldTrace_                    栈 4 + EDX(mask) + EDI(end)          add esp, 10h
transformedCapsuleTrace_       栈 5 + ECX(targetBounds) + EDX(end)  add esp, 14h
transformedBrushModelTrace_    栈 6 + ECX(targetOrigin) + EDX(start) add esp, 18h
```

**而 `transformedBrushModelTrace_` 在 build 之间 `start ↔ result` 互换 ⇒ 往 12 字节 vec3 写 40 字节。**

#### ② **这个 build 没有 SV_Trace**

```text
3.3.3.3  SVTrace 0x005FB940 → 5 个函数的链
1649370  一个都没有
替代品    0x0046E780 是【客户端】的通用 trace（叶子 319/319 与客户端相同、6% 与服务端）
实证      专用服的 centity 数组为空 ⇒ 每实体 clip 恒返回 hitType=0
反向证据  两个 clip 助手从 4 个调用者降到 2 个
```

#### ③ **"实体半边死了、世界半边活着"**

```text
能站在地上走路       ⇒ 世界碰撞活（WorldTrace 真的共享）
打不到实体           ⇒ 实体碰撞死（服务端 clip 被删）
```

**而 §268 的 actor 700..707 是**第二层**缺陷**（`isLinked` 我们写零、`SV_LinkEntity` 从未被调）。

#### ④ **键/命名空间不匹配是贯穿全文件的失败模式**

```text
§250  骨骼名用附件表 ⇒ 返回武器名 ⇒ 死亡特效全失效
§253  附件表的低半部是 interned name id 而不是附件索引
§261  脚本串池 vs 附件串表是两个池
§262  CCS 头表地址 0x077D8188 vs 3.3.3.3 的 0x2DF7CE8
```

**⇒ 数字吻合但命名空间错 ⇒ 检查通过而语义全错。**

#### ⑤ **"沉默 / 噪声读起来像健康" 贯穿全文件（九次以上）**

```text
§225  闩锁让三个状态从未出现
§234  只读健康的那一半（43/47 而死亡全失败）
§235  读错偏移导致提前返回
§239  相同日志放在不跑的路径上
§243  零与错地址读起来一样
§255  EMPTY 被分类成 UNREADABLE
§256  门控在 currentCharacterIndex 里 ⇒ 失败读成"索引不可用"
§261  一个过滤器在两次扫描前清空输入 ⇒ "从未回答过"
§268  256 字节缓冲让自检因空间不足而失败
```

### 6.4 本文件的**五个"跨参照"教训**

```text
① 一个常量来自错误 build 的三大实例
     0x3FF/0x3FE 十位界（§240）           ⇒ 1024 以上的武器全废
     0x400 武器表大小（§252）              ⇒ 276 个武器全废
     0x112/0x11A svFlags 偏移（§265）
② 三个 trace ABI 各不相同，逐个核实
③ "与参照逐字节相同"可能是失败证据（§253 的 `** 646 0 0 8738 9321`）
④ "正确的偏移 + 正确提交 = 游戏坏了"（§237，因为队伍分配不支持）
⑤ 同一个常量被改三次，每次理由不同（§237，`67056` 组）
```

### 6.5 本文件的**五个"性能教训"**

```text
§259  1023×2 次跨进程配置串读 ⇒ 170–320 ms/次生成
§260  1700 次读 ⇒ 165–300 ms/次，11 个人机 = 8–13 s
§239  60,249 次 item 查找阻塞 bridge 线程 ⇒ 加载屏
§268  先宽相再摆 DObj 姿态（第三次"昂贵操作放最窄集合"）
§261  findAlias 的 O(n²) 规范化
```

## 七、关键结论

1. **`MSG_WriteBits` 只查 `!overflowed`** —— 因为原语自己检测溢出。
2. **`MSG_WriteString` 拒绝内部 NUL** —— 否则写入会静默截断而 `cursize` 错。
3. **`data()` 在 `overflowed` 时仍返回部分数据** ⇒ 调用者必须先查 `overflowed()`。
4. **`armNativeFaultWitness` 让客户端装同一个见证器** —— 因为客户端没有咽喉点而崩溃在那里。
5. **`EngineBindings.cpp` 917,344 字节 / ~18,488 行全部读完**，由报告 181–269 覆盖。
6. **五个最重要发现**：三种 trace ABI + 参数互换、这个 build 没有 SV_Trace、实体半边死世界半边活、键/命名空间不匹配、沉默读起来像健康。
7. **五个跨参照教训**、**五个性能教训**。

## 八、下一步

按用户既定的范围顺序，接下来是：

```text
Appmain.cpp            565,999 B
sv_snapshot_mp.cpp   1,466,951 B
sv_main_mp.cpp         657,426 B
localnetworking（6 个）
platformwrapper（7 个）
client_bridge（2 个）
backend/（Demonware 52 + 若干）
shared/
source\ 的非 src（docs 75 / tools 148 / assets 55 / tests 24 / distribution 7 / .agents 59 / references 12 / 根 14）
```
