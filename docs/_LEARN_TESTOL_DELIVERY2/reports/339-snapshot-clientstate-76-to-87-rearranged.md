# 339 · **`writeUnaryFieldIndex` 的 32 位分块**、**`clientState` 从 76 项变 87 项且被【重排】**、`port-netfield-indices.py` 的盲区

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 5179–5400 行。

## 二、**`writeUnaryFieldIndex` 的 32 位分块**（本组第二重要）

### 2.1 那段

```cpp
void writeUnaryFieldIndex(MsgWriter &message, uint32 fieldIndex, int32 &lastFieldIndex)
{
    const auto delta = (int32)fieldIndex - lastFieldIndex;
    auto skipped = (uint32)(delta - 1);
    // OLMOD(clientinfo-wire-adapter): MsgWriter intentionally bounds
    // one bit operation to 32 bits. CODOL's unary clientInfo index can
    // span a larger unknown-field gap (for example 34 -> 46), so emit
    // the same zero run in bounded chunks without changing the wire.
    while (skipped > 32)
    {
        message.MSG_WriteBits(0, 32);
        skipped -= 32;
    }
    if (skipped) message.MSG_WriteBits(0, skipped);
    message.MSG_WriteBits(1, 1);
    lastFieldIndex = (int32)fieldIndex;
}
```

### 2.2 五层

```text
1. **`MsgWriter` 故意把一次位操作限制到 32 位**
2. ⇒ **CODOL 的 unary clientInfo 索引可以跨越更大的未知字段间隔**（例如 **34 → 46**）
3. ⇒ 所以**以有界的块发出同一段零游程而不改变线格式**
4. ⇒ `> 32` 时每次发 32 个零
5. ⇒ 最后发剩余的零 + 一个 1
```

### 2.3 **"以有界的块发出而不改变线格式"**

**✅ 三层**：

```text
1. 一次写 N 个零位
2. ⇒ 与分块写 N 个零位 ⇒ **线上字节相同**
3. ⇒ 所以这是**实现限制**而不是**格式变化**
```

**✅ 一个**正确的适配**。**

### 2.4 而 **`while (skipped > 32)` 而不是 `>= 32`**

**⇒ 三层**：

```text
1. `skipped == 32` ⇒ 循环不进
2. ⇒ 然后 `if (skipped)` ⇒ `MSG_WriteBits(0, 32)`
3. ⇒ **所以 32 由最后一个写处理**
```

**✓ 正确（且避免了**零长度写**）。**

### 2.5 而 `34 → 46` 的**例子**

**⇒ `delta = 46 - 34 = 12` ⇒ `skipped = 11`。**

**⚠ 11 < 32 ⇒ 不分块。**

**⇒ 所以那个例子**不触发分块**。**

**⚠ 可能是"从 12 到 46"或其它。**

**⇒ 但注释举例不当**（或我读错了 `delta`）。

## 三、**`writeSkippedFieldIndex` 的分块**（本组第三重要）

```cpp
void writeSkippedFieldIndex(MsgWriter &message, uint32 fieldIndex,
    int32 &lastFieldIndex, uint32 skipBits)
{
    const auto delta = (int32)fieldIndex - lastFieldIndex;
    if (delta == 1) message.MSG_WriteBits(1, 1);
    else
    {
        message.MSG_WriteBits(0, 1);
        const auto chunkMaximum = (1u << skipBits) - 1;
        auto remaining = (uint32)(delta - 1);
        while (remaining >= chunkMaximum)
        {
            message.MSG_WriteBits(chunkMaximum, skipBits);
            remaining -= chunkMaximum;
        }
        message.MSG_WriteBits(remaining, skipBits);
    }
    lastFieldIndex = (int32)fieldIndex;
}
```

### 3.1 四层

```text
① `delta == 1` ⇒ 一个 1 位
② 否则 ⇒ 一个 0 位
③ `delta - 1` 用 `skipBits` 宽的块，每块最大值 `2^skipBits - 1`
④ `remaining >= chunkMaximum` ⇒ 发一个满块并减
```

### 3.2 而 **`>= chunkMaximum` 而不是 `>`**

**⇒ 三层**：

```text
1. `remaining == chunkMaximum` ⇒ 循环**进**（发一个满块 ⇒ remaining = 0）
2. ⇒ 然后 `MSG_WriteBits(0, skipBits)` ⇒ **一个终止的 0 块**
3. ⇒ **所以一个恰好满块的跳号会用两个块（满 + 零）**
```

**⚠ 而如果条件改成 `> chunkMaximum`：**

```text
remaining == chunkMaximum ⇒ 循环不进 ⇒ 最后一个块是满的
⇒ 而**解码器无法区分"满块继续"与"满块终止"**
```

**✅ 所以 `>=` 是**正确的**（必须留一个非满块作终止）。**

**✅ 与 §323 的 `writePlayerStateFieldIndex` 的 `while (remaining >= 15)`**完全一致** ✓**

### 3.3 而三个 `skipBits`

```text
PlayerState    4 位（§323）
HudElem        3 位（§325）
agentState     3 位（§338）
```

**⇒ 三种，而两个是 3 位。**

## 四、**`clientState` 从 76 项变 87 项且被重排**（本组最重要的一段）

### 4.1 那段

```php
// CODDIFF(1649370): clientState_s went from 76 netfields to 87 and
// was REARRANGED rather than grown -- field 1 moved from +0x68 to
// +0x40, and +0x58..+0x64 carry four 6-bit tag fields on 3.3.3.3
// and four 32-bit fields here. Offset matching and monotone
// alignment both give wrong answers on this table, and
// port-netfield-indices.py never saw any of it because these
// indexes are spelled as bare integers rather than as
// `constexpr ...Field = N`.
```

### 4.2 八层

```text
1. **`clientState_s` 从 76 个 netfield 变成 87 个**
2. ⇒ **而它是被【重排】而不是被【增长】**
3. ⇒ **字段 1 从 `+0x68` 移到 `+0x40`**
4. ⇒ **而 `+0x58..+0x64` 在 3.3.3.3 上携带四个 6 位 tag 字段而在本 build 上是四个 32 位字段**
5. ⇒ **偏移匹配与单调对齐【都给出错误答案】在这个表上**
6. ⇒ `port-netfield-indices.py` **从未看到任何这些**
7. ⇒ **因为这些索引被写成【裸整数】而不是 `constexpr ...Field = N`**
```

### 4.3 **"偏移匹配与单调对齐都给出错误答案"**

**✅ 三层**：

```text
1. 通常用**偏移匹配**（同一个偏移 ⇒ 同一个字段）
2. ⇒ 或用**单调对齐**（索引按顺序对应）
3. ⇒ **而在这个表上两者都错**
```

**⚠ 因为它是**重排**的。**

**✅ 与 §314 的"三处矛盾"、§316 的"数据均匀 -0x20 但代码不均匀"同族**（第三十六次"不能假设同构"）。

### 4.4 而 **`port-netfield-indices.py` 的盲区**

**⇒ 三层**：

```text
1. 那个工具扫描 `constexpr ...Field = N` 形式的声明
2. ⇒ **而这些索引是【裸整数】**
3. ⇒ **所以工具完全没看到**
```

**✅ **第五次"工具盲区"**：**

```text
记忆    目录级 grep 跳过二进制
§305    grep 漏非限定类内调用
§318    数组初始化器对两个工具不可见
§337    （同一工具的另一面）
§340    裸整数索引对 port-netfield-indices.py 不可见
```

### 4.5 而 `clientState` 的**四个 `FieldValue`**

```php
struct FieldValue
{
    uint32 fieldIndex{};
    uint32 value{};
    uint32 baseline{};
    uint32 bits{};
};
```

**⇒ 四项。**

**✅ 一个**表驱动的 clientInfo 写入**（`fieldIndex` / `value` / `baseline` / `bits`）。**

### 4.6 而**两个字段常量**

```cpp
// EXACT CURRENT CLIENT (out.exe 0x54BD53..0x54BD56): native
// clientState+0x40 is copied into characterInfo+0xA4. The Factory
// HUD reads that destination as its battery/points numerator.
// CODREF(out.exe 0x00DA8078, 0x0054BD7A): field 0 is an
// 11-bit raw ET6 weapon-child reference, not parent-plus-one.
constexpr uint32 ClientInfoLivingWeaponField = 0;
constexpr uint32 ClientInfoZombieBatteryField = 1;
```

**⇒ 四层**：

```text
1. **`out.exe 0x54BD53..0x54BD56`：原生 `clientState+0x40` 被拷进 `characterInfo+0xA4`**
2. ⇒ **Factory HUD 把那个目的地读作它的电池/点数额**
3. ⇒ `CODREF(out.exe 0x00DA8078, 0x0054BD7A)`：**字段 0 是一个 11 位的裸 ET6 武器子引用，不是父加一**
4. ⇒ 所以 **`ClientInfoLivingWeaponField = 0`** 而 **`ClientInfoZombieBatteryField = 1`**
```

### 4.7 而 **`+0x40` 是 `clientState` 的第 1 字段**

**⇒ 与 §338 的"`team` 是 `clientState` 索引 21 在 `+0x08`"配合。**

**⚠ 两个不同的表？**

**⇒ §338 的是**24 项 `0x58` 描述符**（`0x00C54298`）而这里是 **87 项**（`0x00DA8078`）。**

**✅ 所以**两张不同的表**：**

```text
0x00C54298        24 项   clientState_s（0x58 字节）   team 索引 21
0x00DA8078        87 项   clientInfo（另一个结构）     字段 0/1
```

**⚠ 而 §316 的 `ClientInfoFieldCount = 87`。**

**✅ 与"从 76 项变 87 项"**完全一致** ✓**

### 4.8 而"**字段 1 从 `+0x68` 移到 `+0x40`**"

**⇒ 三层**：

```text
1. 3.3.3.3 的字段 1 在 `+0x68`
2. ⇒ 本 build 的在 `+0x40`
3. ⇒ **位移 `-0x28` = -40**
```

**⚠ 而 `-0x20` 是数据区的均匀位移。**

**⇒ 所以**字段位移是 `-0x28`** 而**数据区是 `-0x20`**。**

**⚠ 两个不同的位移 ⇒ 所以"重排"确实发生了。**

**✅ 与 §4.2 的"重排而不是增长"一致。**

## 五、`writeClients` 的**三个合并路径**

```cpp
if (emitPlayers == baselineEmitsPlayers)
{
    if (emitPlayers) emitList(clients, baseline);
    emitList(agents, agentBaseline);
}
else
{
    emitList(currentEntries, mergedBaseline);
}
message.MSG_WriteBits(0, 1);
```

### 5.1 三层

```text
① 两帧同一命名空间策略 ⇒ **两次独立的 emitList**（客户端 + agents）
② 否则 ⇒ **一次合并的 emitList**
③ 最后终止位
```

### 5.2 而那段

```php
// Preserve the byte-identical established writer when both frames use
// the same namespace policy. The merged path exists only for a policy
// transition, where removals and additions must share one slot walk.
```

**⇒ 三层**：

```text
1. **当两帧用同一命名空间策略时保留字节相同的既有写入器**
2. ⇒ **合并路径只在策略过渡时存在**
3. ⇒ **那时移除与添加必须共享一次槽遍历**
```

**✅ 一个**向后兼容的分层**。**

**⇒ 与 §337 的"与 `8584acf` 逐字节兼容"同族。**

### 5.3 而 `currentEntries` 的**排序**

```cpp
auto currentEntries = agents;
if (emitPlayers) currentEntries.insert(end, clients.begin(), clients.end());
sort(currentEntries, {}, &SvClientState::clientNum);
```

**⇒ 三层**：

```text
① agents 拷贝
② 若 emitPlayers ⇒ 追加 clients
③ 按 `clientNum` 排序
```

**✅ 与 §284 的"`playerNames` 按 xuid 排序"同族（确定性要求）。**

## 六、关键结论

1. **`writeUnaryFieldIndex` 的 32 位分块** —— 因为 `MsgWriter` 限制一次位操作到 32 位。
2. **"以有界的块发出同一段零游程而不改变线格式"** —— 实现限制而非格式变化。
3. **`while (skipped > 32)` 让 32 由最后一个写处理**（避免零长度写）。
4. **`writeSkippedFieldIndex` 的 `>= chunkMaximum` 必须有**（否则解码器无法区分满块继续与终止）。
5. **三个 `skipBits`**（playerState 4 / HudElem 3 / agentState 3）。
6. **⭐ `clientState_s` 从 76 项变 87 项且被【重排】**。
7. **字段 1 从 `+0x68` 移到 `+0x40`**（位移 `-0x28`）而**数据区均匀 `-0x20`** ⇒ **重排确实发生**。
8. **"偏移匹配与单调对齐都给出错误答案"**。
9. **`port-netfield-indices.py` 的盲区：裸整数索引** —— **第五次工具盲区**。
10. **两张不同的表**（`0x00C54298` 24 项 vs `0x00DA8078` 87 项）。
11. **`clientState+0x40` → `characterInfo+0xA4`** 是 Factory HUD 的电池/点数额。
12. **字段 0 是 11 位裸 ET6 武器子引用，不是父加一**。
13. **三个合并路径**（同策略两次 emitList / 过渡时一次合并）。
14. **"合并路径只在策略过渡时存在"**。

## 七、未闭合点

- `34 → 46` 那个例子的分块（算下来不触发）。
- `clientState_s` 与 `clientInfo` 两张表的完整关系。
- 字段 1 的 `+0x40` 与 `+0x68` 之间被挪走了什么。
- `sv_snapshot_mp.cpp` 5400 行之后未读取（27,016 行，进度 20%）。
