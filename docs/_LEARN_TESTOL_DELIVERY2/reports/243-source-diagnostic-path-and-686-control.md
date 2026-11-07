# 243 · 诊断文件必须放在可执行文件旁、`686` 那个对照、`零与错地址读起来一样`

## 一、范围

本报告学习 `EngineBindings.cpp` 10323–10702 行。

## 二、`diagnosticPath`：**下一次一样的坑**

### 2.1 那次事故

```text
BESIDE THE RUNTIME LOG, NOT BESIDE THE WORKING DIRECTORY.

weapon-slots.csv was opened on the relative path "Ayria\Logs\...", which works
from the CLIENT (its working directory is the game folder) and silently does
nothing from the DEDICATED, whose is not. The audit ran, reported its counts,
wrote no file, and said nothing about it -- `if (stream)` swallowed the failure.
```

**四层**：

```text
1. 相对路径 "Ayria\Logs\..." 在【客户端】能工作（CWD 是游戏目录）
2. 在【专用服】静默什么都不做（CWD 不是）
3. 审计跑了、报了自己的计数、【一个文件都没写】
4. 而且【什么都没说】—— `if (stream)` 吞掉了失败
```

### 2.2 实现

```cpp
std::wstring buffer(MAX_PATH, L'\0');
const auto size = GetModuleFileNameW(nullptr, buffer.data(), (DWORD)buffer.size());
if (!size) return {};
buffer.resize(size);
return std::filesystem::path(buffer).parent_path() / L"Ayria" / L"Logs" / fileName;
```

**`GetModuleFileNameW(nullptr, ...)`** = 当前 **EXE** 的路径 ⇒ 与 CWD 无关。

### 2.3 `if (stream)` 吞掉失败 —— 这是**同一个防御被写在了两处**

**§242 的 `invokeOwnershipResolver` 用 `__try` 把"探针坏了"与"答案是假"分开**；**这里是 `if (stream)` 把"写失败"与"没什么可写"合并了** —— **方向相反**。

**所以这个文件里同时存在"主动区分"与"静默合并"两种做法。**

## 三、`auditItemNames`：写 CSV 不写日志

```cpp
// Written to a CSV rather than the runtime log because it is 20,000-odd lines: a
// log is for events, and burying a cycle's real events under a data dump would
// make the next problem harder to see, not easier.
```

**"日志是给事件用的，把一个周期的真实事件埋进数据转储下面会让下一个问题更难看见，而不是更容易。"**

### 3.1 范围与语义

```cpp
// The range is the catalogue's own: ids 100..60348 per re/demo-re/marketplace/items.csv.
// Ids that resolve to nothing are skipped rather than written as blanks, so the file's
// line count IS the number of items this client can name.
```

```text
100 .. 60348              ← 目录自己的范围
解析不出的【跳过】而不是写空行
⇒ 行数 = 这个客户端能命名的物品数
```

**"行数就是答案"** —— 一个把统计量编码进文件形状的设计。

### 3.2 那个专用服跳过

```cpp
if (OlMod::processRole() == OlMod::ProcessRole::Dedicated)
{
    write("item name sweep: skipped in the dedicated -- the item tables it needs "
          "belong to the client");
    return;
}
```

**"它需要的物品表属于客户端"** —— 与 §243 后面的 `probeOwnership` 同一个理由。

### 3.3 那个数字 60249 vs 60348

```text
循环范围  100..60348  ⇒ 60249 个候选
日志      "X of 60249 ids resolve to a name"
```

**`60348 - 100 + 1 = 60249`** ✓ —— 与 §239 里"60,249 次 item 查找"**同一个数字**。

**这确认了 §239 的 `auditItemNames` 就是那个阻塞 bridge 线程的东西。**

## 四、`characterCatalog`：**名字 → id 需要全表扫描**

### 4.1 为什么

```cpp
// THE SWEEP IS THE ONLY WAY TO TURN A NAME BACK INTO AN ID: the item
// table is indexed by id and there is no reverse index.
```

**"物品表按 id 索引而没有反向索引"** ⇒ 只能扫 60249 个 id 逐个查名。

### 4.2 三个来源的**交集**

```text
mp/coCharItemStatsTable.csv 的 column 0   = 角色的【内部名】
readItemInternalName(itemId)              = 每个 id 的内部名
交集 ⇒ catalog
```

**"表格的行就是答案"** —— 而列 0 恰好是 `readItemInternalName` 返回的那个字符串串。

**这就是 `resolveSessionRewards` 匹配角色的方式**（后面会看到）。

### 4.3 `static` + `mutex` + `built` 的手写单次

```cpp
static std::mutex mutex;
static std::vector<uint32> catalog;
static bool built = false;
const std::lock_guard lock(mutex);
if (built) return catalog;
built = true;
```

**`built` 在**真正工作之前**置 true** —— 与 `std::call_once` 的语义不同：

```text
std::call_once   失败会重试
这里             失败也标记已建 ⇒ 永不重试
```

**这是一处有意的"失败即缓存"** —— 与 §239 里"两个 `call_once`"形成对照。

### 4.4 那句"调用方必须不在帧线程上"

```cpp
// Same range and same shape as auditItemNames, done once and cached -- which is
// why the caller must be off the frame thread.
```

**又一次**（§239 的 60,249 次、§219 的每帧 11 次）。

### 4.5 写 `character-catalog.csv`

```cpp
// AND WRITE IT DOWN. "Which ids are characters" is the question the operator
// actually has, and a log line is not a list.
```

**"日志行不是一个列表"** —— 同样的分层（事件 → 日志；列表 → 文件）。

## 五、`probeOwnership`：**686 那个对照**（本组最重要的一段）

### 5.1 那次事故

```text
The first run of this probe reported all four items NOT owned -- including item
686, the character the player was wearing at that moment. The control caught it:
the patch logs under [client/game-server] and the probe logged under
[dedicated/game-server]. Two processes, both out.exe.
```

**五层**：

```text
1. 四个物品全报 NOT owned
2. 其中包括 686 —— 玩家【当时正穿着】的角色
3. 686 是对照，它抓住了问题
4. 补丁的日志打 [client/game-server]，探针的打 [dedicated/game-server]
5. 【两个进程，都是 out.exe】
```

### 5.2 那句判断

```text
The dedicated has no logged-in player and no inventory, so "not owned" is the
CORRECT answer there and says nothing whatever about the client.
```

**"专用服没有登录的玩家也没有库存，所以『未拥有』在那里是【正确答案】，对客户端什么都没说。"**

### 5.3 那句代价

```text
Without the 686 control that would have read as "the patch does not work", and
the next hours would have gone into a patch that was fine.
```

**"没有 686 那个对照，这会被读成『补丁不工作』，接下来几个小时会花在一个本来就好的补丁上。"**

### 5.4 方法是"用一个必然为真的事实作对照"

**这是一条可复用方法**：

```text
先找一个【答案已知】的输入（玩家正穿着的角色必须 OWNED）
⇒ 如果它也报 NOT owned ⇒ 问题在探针，不在被测对象
```

**与 §239 的 `index` + `record0`、§240 的"同一 id 是否跨 class"、§241 的"两 class fixture"是同一族 —— 差分/对照。**

## 六、七个探针的三类

```cpp
struct Probe { uint32 itemId; const char *name; const char *why; };
static constexpr std::array<Probe, 7> Probes{ {
    { 686, "cha_COWprestigeA", "the character worn now -- owned either way, so a NO here means the probe itself is wrong" },
    { 14368, "melhammer_mp", "grant position 10630, far past the wire's 8460" },
    { 14386, "molotovcocktail_mp", "grant position 10666, far past the wire's 8460" },
    { 24308, "muz_slnc45smgveprlaborday", "grant position 10479, likewise" },
    { 11281, "scope_med", "NEVER SOLD -- no sku grants it" },
    { 17097, "shotgun_fn2000", "NEVER SOLD -- no sku grants it" },
    { 10435, "cam_kawaiirsrt3", "NEVER SOLD -- no sku grants it" },
} };
```

### 6.1 三类

```text
①  对照（必然 owned）                      686
②  超出线上缓冲区（不可能真 owned）          14368 / 14386 / 24308
③  从未售出（任何合法途径都拿不到）          11281 / 17097 / 10435
```

### 6.2 第二类的论证

**"`grant position 10630, far past the wire's 8460`"**

```text
授予列表位置 10630 > 接收缓冲 8460 ⇒ 【不可能】在库存哈希里
⇒ 如果报 owned，唯一能造成它的是补丁
```

**这是一个"上界证明"** —— 与 §236 里"`first > count` 说明边界算错"同族，但这里是**用来构造一个不可能为真的事实**。

### 6.3 第三类更强

```text
NEVER SOLD -- no sku maps to these, so no purchase could ever have granted
them and they cannot be in the inventory by any legitimate route.
1,675 of the catalogue's 21,740 are like this.
```

**"1,675 / 21,740 是这样的"** —— 而探针挑了三个。

**"如果它们报 owned，补丁不在乎一个物品是否曾经可购买。"**

## 七、`invokeOwnershipResolver` 的调用与 `+4`

```cpp
std::array<std::uint32_t, 32> record{};     // 128 字节
if (!invokeOwnershipResolver(resolver, itemId, record.data(), returned)) { ...FAULTED... }
const auto owned = *(const uint16*)((const uint8*)record.data() + 4);
```

### 7.1 三条输出

```text
owned        record 字节 +4 的 uint16
returned     函数的 EAX
quantity     record[2]（dword 2 = 字节 8）
```

### 7.2 "The resolver writes up to +44"

**"它最多写到 +44；给它远多于此。"** ⇒ 128 字节足够。

**而 `+4` 是 `owned`** —— 前面 4 字节是别的东西（可能是 id 或 flags）。

### 7.3 FAULT 的措辞

```cpp
"ownership probe: FAULTED calling the resolver for " + name +
" -- the RVA or the calling convention is wrong, and nothing else here means anything"
```

**"RVA 或调用约定是错的，而这里别的什么都不意味着什么"** —— 与 §242 里 `__try` 的设计目的一致。

## 八、`reportUnlockAllCoverage`：**零与错地址读起来一样**（本组第二重要）

### 8.1 那句更正

```cpp
// AN EMPTY LIST AND A WRONG ADDRESS READ THE SAME. This said "EMPTY, this is
// all of them" and called it proof, and a zero from any unrelated page would
// have said exactly that -- the guard below only catches an implausibly LARGE
// count. So do not conclude from the zero: ASK THE RESOLVER.
```

**"一个空列表和一个错地址读起来一样。这里曾写着『空，这就是全部』并称之为证明，而任何不相关页面的零都会说完全同样的话 —— 下面的守卫只抓住不合理地【大】的计数。所以不要从零得出结论：问解析器。"**

### 8.2 三层处理

```text
excluded == 0        ⇒ 【不结论】，调用 probeOwnership() 实测
excluded > 4096      ⇒ 【不是黑名单，是坏指针或坏 RVA】
excluded 在 1..4096  ⇒ 打印列表
```

### 8.3 三个理由

```text
// A list this long is not a blocklist, it is a bad pointer or a bad RVA.
```

**"这么长的列表不是黑名单，是坏指针或坏 RVA"**

```cpp
// It reads LATE rather than at patch time: sub_5DE440 fills the list from a
// comma-separated string at runtime, so a read during startup would report an
// empty list whether or not one arrives later.
```

**"它在【晚】的时候读而不是在打补丁时读：`sub_5DE440` 在运行时从一个逗号分隔串填充这个列表，所以在启动时读会报告一个空列表 —— 无论之后是否有东西到达。"**

### 8.4 这是"沉默读起来像健康"的**第五次**，但这次是**主动避免**

```text
§225  闩锁让三个状态从未出现过
§234  只读健康的那一半
§235  读错偏移导致提前返回
§239  相同的日志行放在错误的路径上
§243  零与错地址读起来一样
```

**而 §243 是**唯一一个在代码里显式写出这个陷阱的**。

## 九、`auditRewardTable`：逐列转储与转义

```cpp
output << '"';
for (const char ch : cell.value_or("<UNREADABLE>"))
{
    if (ch == '"') output << '"';        // ← CSV 双引号转义
    output << ch;
}
output << '"';
```

### 9.1 三个细节

```text
1. 每个单元格【都】加引号（不论内容）
2. 双引号加倍（CSV 标准）
3. 读不出 ⇒ "<UNREADABLE>" 字面量（不是空）
```

### 9.2 那句"保留每一列，包括表头行"

```cpp
// Checkpoint 70: runtime ID/name/cost/icon/alternate cost are columns 0/1/4/15/40.
// Preserve every column, including any header rows.
```

**`columns 0/1/4/15/40`** 与后面 `resolveSessionRewards` 的 `read(0, runtimeId) / read(4, normalCost) / read(40, persistentCost)` **完全一致** ✓

### 9.3 文件名带 PID

```cpp
const auto fileName = L"reward-table-" + std::to_wstring(GetCurrentProcessId()) + L".csv";
```

**为什么要 PID** —— 因为客户端与专用服**并行运行**，同名文件会互相覆盖。

**这与 §243 的 `diagnosticPath` 一起构成了"多进程安全"的完整方案。**

### 9.4 那句"离线副本不可信"

```cpp
// The offline copy of this table cannot answer this: codol_stringtable_extract.py
// resolves 57% of its string-pool back-references and prints another weapon's text
// for the rest -- the type95techslime row comes out carrying SF_WEAPON_AA12GATOR_MP_DESC.
```

**"离线副本解析了 57% 的字符串池回引，其余打印出【另一个武器的文本】—— `type95techslime` 那一行带着 `SF_WEAPON_AA12GATOR_MP_DESC`。"**

**这是一个具体的、可核对的错误样例** —— 而不是"离线表不可靠"的空断言。

**"已加载的表是唯一可信的副本，而服务器已经有它了。"**

## 十、`resolveUavWeapon` 的五步（与 §239 的 `resolveWeaponDefinition` 不同）

```cpp
constexpr auto name = "killstreak_uav_mp";
const auto index = weaponLookup_(name);
if (!index || index > MaximumWeaponAssetIndex) return nullopt;
const auto actualName = readWeaponDefinitionName(index);
if (!actualName || *actualName != name) return nullopt;      // ← 回读校验
... ammo/clip/capacity 边界 ...
```

### 10.1 **按名字查 + 回读校验**

**"Index1188 in the retail demo is load-order evidence, not an ABI."**

**"零售 demo 里的 1188 号是加载顺序的证据，不是 ABI"** —— 所以**不硬编码 index**，而是按名查再回读。

**这是 §236 里"不要重新推导，它们是测量过并被佐证的"的**反面**：这里**拒绝**使用测量到的 index，因为它的性质是"加载顺序"而不是"契约"。

### 10.2 边界 2047 / 2046 / 511

```cpp
ammo > 2047           ← 11 位
clip > 2046           ← 11 位，全一是 sentinel
capacity > 511        ← 9 位
```

**与 §240 里 `0x7FF`(2047) / `0x7FE`(2046) / `0x1FF`(511) 完全一致** ✓

**这是同一组线宽在第二处的使用。**

### 10.3 读的长度

```cpp
if (!readableSpan(definition, WeaponAimDownSightOffset + 1)) return nullopt;
```

**只验证到 `WeaponAimDownSightOffset + 1`** —— 因为后面只读这个偏移之前的字段（含 overlay）。

**但 `WeaponOverlayReticleOffset` 与 `WeaponAimDownSightOffset` 的先后关系是隐含假设。**

## 十一、`resolveKillstreakWeapon`：**参数化**

```cpp
std::optional<SvRewardWeapon> EngineBindings::resolveKillstreakWeapon(
    const std::string_view name) const
```

**同一个五步，只是 `name` 变成参数** —— 而 `resolveUavWeapon` 与 `resolveAc130Weapon` 是它的两个硬编码特例。

**代码里三份几乎相同的实现**：

```text
resolveUavWeapon             name = "killstreak_uav_mp"
resolveAc130Weapon           name = "killstreak_ac130_mp"
resolveKillstreakWeapon      name = 参数
```

**这是本文件里最明显的一处重复** —— 一个有 `std::string_view` 版本的函数本可以替代前两个。

**而注释说"不重复造轮子"（`resolveKillstreakWeapon` 的"刀V"注释），但前两个没有改用。**

### 11.1 `std::string ownedName(name)` 的理由

```cpp
const std::string ownedName(name);
const auto index = weaponLookup_(ownedName.c_str());
```

**因为 `weaponLookup_` 要 `const char*` 而 `string_view` 不保证 NUL 结尾** ⇒ 必须拷贝。

**而回读校验用 `*actualName != ownedName`** —— 与 `string_view` 比较也可以，但统一成 `std::string` 更省心。

## 十二、`resolveBaseWeaponAssetIndex` 的**不同**上界

```cpp
if (!index || index >= BaseWeaponAssetCount) return nullopt;
```

**`>= BaseWeaponAssetCount`** 而前三个用 **`> MaximumWeaponAssetIndex`**。

### 12.1 两个上界

```text
MaximumWeaponAssetIndex    ← 连杀武器（可以是模块化的）
BaseWeaponAssetCount       ← 基础武器（只到随包的 1300 左右）
```

**"base" 与 "any" 是两个不同的边界** —— 与 §236 里 `firstDynamicWeaponAssetIndex` 的边界讨论同族。

## 十三、`resolveSessionRewards` 的两个阶段

### 13.1 阶段一：`SV_ResolveProfileRewards` + 回调

```cpp
auto resolved = SV_ResolveProfileRewards(request.rewardItemIds,
    [&](uint32 catalogId) -> optional<SvRewardDefinition> {
        const auto name = readItemInternalName(catalogId);
        for (r = 0; r < table->rowCount; ++r) {
            const auto rowName = readStringTableCell(row[1]);      // ← 列 1
            if (!rowName || *rowName != *name) continue;
            ... read(0, runtimeId) / read(4, normalCost) / read(40, persistentCost) ...
        }
    });
```

**三列**：`0 = runtimeId`、`4 = normalCost`、`40 = persistentCost` —— 与 §9.2 的 Checkpoint 70 一致。

**而匹配用的是 **列 1**（名字）**。

### 13.2 `from_chars` 的完整消费

```cpp
return parsed.ec == std::errc{} && parsed.ptr == text->data() + text->size();
```

**两项** —— 成功 + **消费了整个 token**。

**这正是 §179 里"`from_chars` 必须消费整个 token"的同一条规则的第二次出现。**

### 13.3 阶段二：角色名 → `modPersistKillstreak`

```cpp
const auto characterName = readItemInternalName(request.characterItemIds[0]);
const auto *characters = readStringTable(..., "mp/coCharItemStatsTable.csv", 3);
for (r ...) {
    if (*name != *characterName) continue;
    for (c = 2; c < columnCount; c += 6) {
        const auto property = readStringTableCell(row[c]);
        if (!property) return nullopt;           // ← 读不出 ⇒ 整个失败
        if (property->empty()) break;            // ← 空 ⇒ 停止
        if (*property == "modPersistKillstreak") { resolved->persistentCosts = true; break; }
    }
    break;
}
```

### 13.4 三个关键点

```text
1. characterItemIds[0] 是【目录 id】不是 characterIndex    ← 注释明说
2. 属性列从 2 开始，步长 6
3. 空属性 ⇒ 【停止】（不是 continue）
```

**"`characterItemIds` 是十二项服装记录，不是一个按 `characterIndex` 索引的数组。第零项已经是一个目录 id。"**

**这是 §239 里"两个数组都十二长"混淆的第三次防护** —— 三个不同的地方都专门写了这条。

### 13.5 空属性停 vs 读不出失败

```text
读不出（nullopt）  ⇒ 整个函数返回 nullopt
空串              ⇒ break（正常结束）
```

**区分了"表损坏"与"属性列用完了"** —— 与 §235 的 `readConfigString` 同族。

## 十四、关键结论

1. **相对路径在两个进程里行为不同** —— 必须用 `GetModuleFileNameW`。
2. **`if (stream)` 吞掉失败** vs **`__try` 主动区分** —— 同一个文件里两种做法并存。
3. **列表 → CSV、事件 → 日志** —— 反复出现的分层。
4. **`60348 - 100 + 1 = 60249`** 确认了 §239 的阻塞源。
5. **`built = true` 在真正工作之前** ⇒ 失败即缓存，与 `call_once` 不同。
6. **686 对照是"用一个必然为真的事实验探针"** —— 没有它会浪费几个小时。
7. **三类探针：对照 / 超出线上缓冲（不可能真）/ 从未售出（不可能合法）**。
8. **零与错地址读起来一样** —— 所以 `excluded == 0` 时**调用探针**而不是下结论。
9. **`sub_5DE440` 在运行时填列表** ⇒ 启动时读会得到空。
10. **离线表的具体错误样例**：`type95techslime` 带 `SF_WEAPON_AA12GATOR_MP_DESC`。
11. **连杀武器按名字查 + 回读，拒绝 index** —— 因为 1188 是加载顺序不是 ABI。
12. **`resolveKillstreakWeapon` 已参数化但两个特例未改用** —— 三份重复实现。

## 十五、未闭合点

- `resolveUavWeapon` / `resolveAc130Weapon` 与 `resolveKillstreakWeapon` 的三份重复。
- `WeaponOverlayReticleOffset` 是否必然在 `WeaponAimDownSightOffset` 之前。
- `EngineBindings.cpp` 10702 行之后未读取（本批已续读到 11090）。
