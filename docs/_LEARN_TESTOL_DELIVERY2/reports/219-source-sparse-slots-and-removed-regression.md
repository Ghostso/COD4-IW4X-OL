# 219 · 稀疏槽必须压紧：`attachment[4] = nullptr` 如何让玩家永久卡在加载屏

## 一、范围

本报告学习 `EngineBindings.cpp` 4908–5107 行。

## 二、`resolveCharacterModelNames` 的十项前置

```cpp
1. module_ / characterRecordFillDefaults_ / characterRecordToSelectionNames_ 非空
2. characterModelResolutionEnabled()
3. customization.characterItemId != 0
4. CharacterItemDecodeKeyRva 可读
5. decodeKey = *(u32*)(module_ + CharacterItemDecodeKeyRva)
6. decodeKey != 0xFFFFFFFF
```

### 2.1 那条"零必须像桩一样失败"

```cpp
// NO CHARACTER, NO RESOLUTION, AND SAY SO RATHER THAN GUESSING. Every match this
// build ran before section 67 arrived here with a zero, because nothing carried
// the id; a zero must fail the same way the stub did rather than resolve to
// whatever definition index 0 happens to be.
```

**"零必须像桩一样失败，而不是解析成定义索引 0 恰好是什么"**

### 2.2 那条"镜像里是 0xFFFFFFFF、运行时是真值"

```cpp
// The key is 0xFFFFFFFF in the IMAGE and a real value at runtime, so a
// still-unwritten key is a "not ready yet", not a defect. Resolving against it
// would encode entry 0 as something the engine then decodes to garbage.
```

**与 §186 里"两个候选键的镜像值都是 0xFFFFFFFF"完全对应** —— 而在运行时它是真值。

**所以 `0xFFFFFFFF` 是"尚未初始化"的哨兵**，不是错误。

## 三、记录合成：先填 0，再填服装

```cpp
record[0] = encodeCharacterItemId(customization.characterItemId, decodeKey);

for (entry = 1; entry < record.size() && entry < customization.recordItemIds.size(); ++entry)
{
    itemId = customization.recordItemIds[entry];
    if (!itemId) continue;
    record[entry] = encodeCharacterItemId(itemId, decodeKey);
    if (decodeCharacterItemId(record[entry], decodeKey) != itemId) return false;
}
```

### 3.1 为什么"先填服装"很重要

```cpp
// THE EQUIPPED OUTFIT, BEFORE THE DEFAULTS. sub_619AD0 fills only the entries
// that are still EMPTY, so a piece written here survives and the character's
// own default for that entry is the thing that gets displaced -- which is
// exactly what wearing an outfit means.
```

**"`sub_619AD0` 只填空的条目，所以写在这里的件会存活，而角色自己在该条目的默认值是被换掉的那个 —— 这正是'穿套装'的意思。"**

**顺序是语义**：先填 = 覆盖默认；后填 = 被默认覆盖。

### 3.2 每个条目都自检

```cpp
if (decodeCharacterItemId(record[entry], decodeKey) != itemId) return false;
```

**"键在我们脚下移动了会编码出引擎解码成不同物品的东西，而失败会表现为错误的模型而不是错误。"**

**这是 §201 的"对称往返"的应用** —— 但这里**不是证明算术正确**（那由 static_assert 做），**而是证明算术被应用到了 THIS key**。

注释（对 entry 0 的那条）：

> **廉价的自我检查，而它与单元测试不冗余：测试证明算术，这个证明算术被应用到了这个 key 上。**

### 3.3 调用 `sub_619AD0`

```cpp
((CharacterRecordFillDefaults)characterRecordFillDefaults_)(
    record.data(), (int)customization.characterItemId);
```

**两个参数**：记录数组、角色物品 id。

## 四、`filled` 的构建：`section-67-record-witness`

```cpp
std::string filled;
for (index = 0; index < record.size(); ++index)
{
    filled += (index ? "," : "");
    filled += record[index].present
        ? std::to_string(decodeCharacterItemId(record[index], decodeKey))
        : std::string{ "-" };
}
```

### 4.1 为什么必须解码引擎写的结果

```cpp
// OLMOD(section-67-record-witness): DECODE WHAT THE ENGINE PUT THERE. Two of the
// five names the first live run produced were the wrong family -- fpa_goose and
// boo_empty where the client's own tables say fpa_infbasea and boo_infbasea --
// and changing the variant selector moved the SUFFIXES without moving those two,
// so the cause is upstream of the naming.
```

**推理链**：

```text
1. 五个名字里有两个来自错误的族
2. 改变变体选择器只移动了后缀，没移动那两个
3. ⇒ 原因在"命名"的上游
```

### 4.2 "名字是有损视图，id 才是记录"

```cpp
// Names are a lossy view of the record: they are what sub_80E110 made of it.
// The ids ARE the record, and comparing them against
//     545 cha_infbasea -> [0, 532, 525, 529, 1099, 115, 0, 0, 0, 0, 0, 0]
// says in one line whether sub_619AD0 filled the entries this side expected or
// whether the dedicated process resolves 545 to a different character record
// than the client does. Those are two very different defects and the names
// cannot tell them apart.
```

**两种缺陷**：

```text
A. sub_619AD0 没有填我们期望的条目
B. dedicated 进程把 545 解析成与客户端不同的角色记录
```

**而名字无法区分 A 与 B** —— 只有 id 能。

### 4.3 那条黄金值

```text
545 cha_infbasea -> [0, 532, 525, 529, 1099, 115, 0, 0, 0, 0, 0, 0]
```

**十二条目，索引 0 是 0** —— 因为条目 0 被 `sub_619AD0` 清了吗？

**注意 §218 里 `characterModelNames` 的示例是**：

```text
545 -> fpa_goose, boo_empty, fja_infbasea, han_infbasea, hea_socomb, -, ...
      count=5, slots 0..4
```

**所以条目 0 的值（0）并不参与名字** —— 因为 `sub_61B6C0` 跳过条目 0。

**而条目 1..5 的值 `532,525,529,1099,115` 对应五个名字** ✓

**条目 6..11 全为 0** ⇒ 没有更多件 ⇒ `dst[5..9]` 都是 null ⇒ count = 5 ✓

**完全一致。**

## 五、那次稀疏槽的完整崩溃链

这是本组最重要的一段。

### 5.1 两个实例对照

```text
545 -> fpa_goose, boo_empty, fja_infbasea, han_infbasea, hea_socomb, -, ...
       count=5, slots 0..4          DENSE   -- spawns

686 -> fpa_cowprestigea, boo_empty, fja_indian, han_cowprestigea,
       hea_zmcowboy, -, heg_cowprestigea, -, ...
       count=6, slots 0,1,2,3,4,6   SPARSE  -- attachment[4] = nullptr
```

**关键差异**：

```text
545：槽 0..4 连续，count = 5
686：槽 0,1,2,3,4,6，中间缺 5，count = 6
```

**如果不压紧**，`modelNames[5]` 会是 `nullptr`（因为槽 5 空），而 `modelNames[6]` 是 `heg_cowprestigea`，`count = 6`。

**那么 `modelNames[0..6)` 里 `modelNames[5] == nullptr`。**

### 5.2 `BG_UpdatePlayerDObj` 的解引用

```text
BG_UpdatePlayerDObj 0x0040AB30 walks the attachment array reading the FIRST
BYTE of every candidate before it checks whether the string is empty
(`if (!*(_BYTE *)*v16) break;` at 0x0040AD5A), so that null is dereferenced,
```

**`*(_BYTE *)*v16`** —— **先解引用再判空**。

**所以 `*v16 == nullptr` 时会崩。**

**这是一个顺序问题**：

```c
if (!*(_BYTE *)*v16) break;    // 先解引用 *v16，再看第一个字节
```

**正确写法应该是**：

```c
if (!*v16 || !**v16) break;
```

**但引擎写的是前者** —— 所以**它假定数组里没有 null**。

### 5.3 五步连锁

```text
1. 访问违例
2. 毒化原生实体镜像
3. endFrame 回滚
4. 该帧不发布任何 playerState
5. 每个快照被拒为 `missing_playerstate`
6. 玩家【永远】停在加载屏
```

**"玩家永远停在加载屏"** —— 这是一个非常具体的终端症状。

### 5.4 M4A1 为什么侥幸能用

```text
The M4A1 fixture spawned only because character 545 happens to be dense.
```

**"M4A1 夹具能出生只因为角色 545 恰好是稠密的"** —— **测试通过是因为选了幸运的样本**。

**这与 §215 里"编译通过 + 六个测试套件通过 ≠ 运行时正确"是同一族教训。**

## 六、压紧的实现与理由

```cpp
for (index = 0; index < names.size(); ++index)
{
    if (!names[index]) continue;
    if (!readableSpan((const uint8_t*)names[index], 1))
    {
        modelNames = {};
        resolvedModelCount = 0;
        return false;
    }
    slots += (resolvedModelCount ? "," : "") + std::to_string(index);
    modelNames[resolvedModelCount] = names[index];
    ++resolvedModelCount;
}
```

### 6.1 为什么"不能保留槽位索引"

```cpp
// COMPACT. DO NOT KEEP THE SLOT INDEX -- THAT IS THE SPARSE-COUNT CRASH.
// `resolvedModelCount` is a POPULATION COUNT, and every consumer downstream reads
// it as a LENGTH: the DObj fill writes modelNames[1 .. resolvedModelCount) into
// the attachment array, and the post-check compares the created DObj's models
// against modelNames[0 .. resolvedModelCount).
```

**`resolvedModelCount` 是"数量"而不是"最大索引"** —— 而所有下游都把它当**长度**用。

**"不压紧 = 把稀疏索引当长度"** —— 于是在 `[0, count)` 范围内留下空洞。

### 6.2 为什么"空洞等效于截断"

```cpp
// The engine's own loop breaks at the first EMPTY string, so a hole is a
// truncation to it either way; compacting keeps the models the character
// actually has and can never place a null in the range.
```

**引擎自己在第一个空串处 break** ⇒ **空洞后的东西本来就读不到**。

**所以压紧不丢失信息** —— 只是把"读不到的"去掉。

### 6.3 那条"不可读的非空指针比 null 更糟"

```cpp
if (!readableSpan((const uint8_t*)names[index], 1))
{
    // A non-null pointer that cannot be read is worse than a null one: it
    // would reach the DObj build and fault there instead of here.
    modelNames = {};
    resolvedModelCount = 0;
    return false;
}
```

**"一个非空但不可读的指针比 null 更糟：它会到达 DObj 构建并在那里 fault 而不是在这里"**

**"在边界处失败比在下游失败好"** —— 因为下游的失败会毒化镜像并导致"永久加载屏"。

### 6.4 `slots` 的诊断串

```cpp
slots += (resolvedModelCount ? "," : "") + std::to_string(index);
```

**记录的是"原始槽位索引"** —— 所以日志里能看出稀疏性（如 `0,1,2,3,4,6`）。

**这与 `modelNames` 的压紧相反**：**存储压紧、日志保留原索引**。

## 七、那段"被移除的回归"：本组另一个重点

### 7.1 被移除的是什么

```text
A per-name findXAsset(AssetTypeXModel, name, false) probe used to run here,
to keep resolvedModelCount equal to what the engine would actually register.
```

**每个名字一次 `findXAsset`** —— 用来让 `resolvedModelCount` 等于引擎实际会注册的数量。

### 7.2 为什么它是灾难

```text
THIS FUNCTION IS CALLED EVERY FRAME FOR EVERY PLAYER
(updateServerPlayerDObj runs in the Presentation phase),
so that added eleven asset lookups -- each asking dbFindXAssetHeader AND
dbIsXAssetDefault -- plus a std::string, per frame, per player,
where there had been none.
```

**每帧每玩家 11 次 × 2 个 DB 调用 + 一个 `std::string`**。

### 7.3 实测症状

```text
the dedicated's frame thread went from ~1 stall/minute to ~39/minute
    (FRAMESTALL wallUs=1,245,604 threadCpuUs=1,125,000,
     stack through EngineBindings.cpp)
```

**从 1 次/分钟到 39 次/分钟** —— 而 `wallUs=1.24 秒` 一次停顿。

### 7.4 更严重的连锁

```text
the control port stopped answering inside the 500 ms submit budget --
socketError=10060 on ConfigureSession/QueryEndpoint,
findSessions returned ZERO candidates,
and the client's match button did nothing at all.
```

**五步**：

```text
1. 帧线程停顿 1.24 秒
2. 控制口在 500 ms 预算内不响应
3. socketError=10060（WSAETIMEDOUT）
4. findSessions 返回零候选
5. 客户端的比赛按钮什么都不做
```

**"比赛按钮什么都不做"的根因是"每帧 11 次 asset 查找"** —— 这是一条很难想像的因果链。

### 7.5 而且它**从未生效**

```text
And it NEVER FIRED in the one run it was deployed for: no
`character models DROPPED` line was ever written, because every name
it probed was in fact present. It bought nothing and cost the match.
```

**"它没有买到任何东西，却付出了整场比赛"**

**这是本报告最值得记的一句。**

### 7.6 保留的那部分

```text
The layout diagnostic below is KEPT: it is a readableSpan plus an
integer compare, it logs only on a change, and it is what says WHICH
count disagreed if server_dobj_layout ever fails again.
```

**"一个 `readableSpan` 加一次整数比较，只在变化时记录"** —— 成本可接受。

**"移除昂贵的、保留廉价的"** 是正确的取舍。

## 八、关键结论

1. **`decodeKey == 0xFFFFFFFF` 是"尚未初始化"，不是错误**。
2. **"先填服装再填默认"是语义，不只是顺序** —— `sub_619AD0` 只填空条目。
3. **自检不是证明算术（那由 static_assert 做），而是证明算术被应用到了这个 key**。
4. **名字是有损视图，id 才是记录** —— 只有 id 能区分"填错"与"解析错"。
5. **稀疏槽不压紧 = `attachment[4] = nullptr` = 引擎先解引用再判空 = 崩溃**。
6. **崩溃的五步连锁终点是"玩家永远停在加载屏"**。
7. **M4A1 夹具能过只因角色 545 恰好稠密** —— 幸运样本掩盖了缺陷。
8. **每帧 11 次 asset 查找让帧线程停顿 1.24 秒，控制口超时，比赛按钮失效** —— 而且它从未生效过。

## 九、未闭合点

- `server_dobj_layout` 诊断的完整实现（5107 行之后）未读取。
- `EngineBindings.cpp` 5107 行之后未读取。
