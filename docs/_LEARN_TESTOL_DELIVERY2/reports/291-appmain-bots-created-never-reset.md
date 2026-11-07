# 291 · **`BotsCreated` 从不重置 ⇒ 第三/四张地图没有 bot**、`resolveUs ≈ elapsedUs` 的耗时拆分、738 个官方 bot 名

## 一、范围

本报告学习 `Appmain.cpp` 4560–4780 行。

## 二、`configureGameStateImpl` 的**四个收尾**

```php
// ① 角色未变
const auto finalCharacter = Dedicated
    ? optional{ prepared.members.front().characterIndex }
    : Bindings.currentCharacterIndex();
if (!finalCharacter || *finalCharacter != prepared.members.front().characterIndex)
{ failed(CharacterChanged); return false; }

// ② 会话资产 replace
CodolGameServer::SessionAssetRegistry nextSessionAssets;
if (!nextSessionAssets.replace(std::move(registeredSessionMembers)))
{ failed(PreparedLoadoutMismatch); return false; }

// ③ 服务端提交
if (!Server.configureGameState(std::move(gameState), sessionGeneration))
{ failed(ServerCommitFailed); return false; }

// ④ 原子交换 + 待定世界资产
{
    const std::lock_guard lock(LoadoutMutex);
    RegisteredSessionAssets = std::move(nextSessionAssets);
}
const std::lock_guard lock(WorldAssetMutex);
PendingWorldAsset = PendingWorldAssetRequest{ .mapName, .gameType, .mapEntities };
GameStateConfiguration.accepted();
return true;
```

### 2.1 **"先构建新副本、后原子交换"**

```text
① 构建 nextSessionAssets（不碰全局）
② Server.configureGameState 提交
③ 只有【都成功】才 `RegisteredSessionAssets = move(next)`
```

**⇒ 与 §248 的"发布顺序"同族 —— 一个**事务式**的提交流程。**

### 2.2 而顺序是"服务端提交**在**本地交换**之前**"

**⚠ 如果 `Server.configureGameState` 成功而之后 `RegisteredSessionAssets = move` 抛异常（不会，因为是 move），状态会不一致。**

**✓ move 赋值不抛。**

### 2.3 而 `finalCharacter` 的**第三次检查**

```php
Dedicated  ⇒  prepared.members.front().characterIndex（【不查引擎】）
Client     ⇒  Bindings.currentCharacterIndex()
```

**⇒ 专用服**不再查** —— 因为它就是用 prepared 的值。**

**⇒ 所以比较恒等** ⇒ 对专用服这个检查**恒通过**。

**⚠ 所以这个检查只在客户端有意义。**

## 三、`configureGameState` 的**三段**

```cpp
uint64 sessionGeneration{};
{ const std::lock_guard lock(LoadoutMutex); if (PreparedLoadouts) sessionGeneration = PreparedLoadouts->sessionGeneration; }
const auto configured = configureGameStateImpl(mapName, gameType, checksum, checksumFeed);
if (!configured && sessionGeneration)
    static_cast<void>(Server.rollbackSessionRoster(sessionGeneration));
if (configured && sessionGeneration != BotsSessionGeneration)
{
    BotsSessionGeneration = sessionGeneration;
    BotsCreated = 0;
}
return configured;
```

### 3.1 三段

```text
① 读 sessionGeneration
② 失败 ⇒ rollbackSessionRoster
③ 成功且【代际变了】⇒ 重置 bot 预算
```

## 四、**`BotsCreated` 从不重置 ⇒ 第三/四张地图没有 bot**（本组最重要的一段）

### 4.1 那段注释

```php
// B1(D10 fix): bot accounting is PER SESSION. These used to live next to
// configureBotClients and never reset, so every session after the first
// saw requested <= BotsCreated at :4400 and never even tried to create a
// bot -- the third/fourth map had none (measured 2026-10-10). The counter
// now belongs to the session generation that configured it.
std::uint32_t BotsCreated{};
std::uint64_t BotsSessionGeneration{};
```

### 4.2 四层

```text
1. `BotsCreated` 过去住在 `configureBotClients` 旁边且**从不重置**
2. ⇒ 第一次之后的每个会话都看到 `requested <= BotsCreated`
3. ⇒ **从没尝试创建一个 bot** ⇒ 第三/四张地图没有（实测 2026-10-10）
4. ⇒ 计数器现在**属于配置它的那个会话代际**
```

### 4.3 **"`requested <= BotsCreated` 就跳过"**

**⇒ 一个"已达配额"的判断**在**跨会话**时失效。**

**⇒ 与 §283 的 `>=` 把真人判成人机**同族 —— **一个状态跨了不该跨的边界。**

**⇒ 这是"状态的作用域错了"的第二个实例。**

### 4.4 而修复用**代际**

```cpp
if (configured && sessionGeneration != BotsSessionGeneration)
{
    BotsSessionGeneration = sessionGeneration;
    BotsCreated = 0;
}
```

**⇒ 两个条件**：

```text
configured              只有成功才重置
代际 != 上次              同一个会话重复配置不重给预算
```

**⇒ 而注释解释"重复配置同一会话会创建重复 bot"。** ✓

## 五、`BotSpawnRequests` 的**三个理由**

```php
// SWITCH: OLMOD_BOTS=<n>, read the same way every other OLMOD_* switch in
// this tree is read -- std::getenv, right here in the frame path. Default
// 0 = off. Nothing is created until the world is fully configured, because
// the spawn request has to find the map's own spawn points.
//
// MANUAL DOOR: CODOL_GameServerRequestBots(n) raises BotSpawnRequests and
// this function consumes it on the next frame. A plain counter rather than a
// direct call, because that export may be invoked from any thread while
// Server is owned by the frame thread.
std::atomic<uint32> BotSpawnRequests{};
```

### 5.1 三层

```text
① `OLMOD_BOTS=<n>` 默认 0
② 世界完全配置之前【什么都不创建】（因为 spawn 请求要找到地图自己的出生点）
③ 手动门：`CODOL_GameServerRequestBots(n)` 提高计数器而下一帧消费
```

### 5.2 **"一个普通计数器而不是直接调用"**

**⇒ 因为那个 export 可以从**任何线程**被调用而 `Server` 由帧线程拥有。**

**⇒ 与 §281 的八个队列同族**（控制线程 → 游戏线程）。**

**⇒ 第九个队列（用一个 `atomic<uint32>` 而不是 deque，因为只需要累加）。**

## 六、`BotXuidBase` 的**第三次出现**

```cpp
constexpr uint64 BotXuidBase = 0x0B07'0000'0000'0000ull;
```

**⇒ 与 §283 的重复声明**同一个值** ✓

**⇒ 而注释说"写在日志里逐字节"以便追溯。**

**⇒ 与 §283 的"区间判定 `[base, base+4096)`"配套。**

## 七、**`resolveOfficialBotClass` 的耗时拆分**（本组第二重要）

### 7.1 那段中文注释

```php
// ★★★ 2026-10-14（③c-2）—— 实机三段拆分已定死：`resolveUs ≈ elapsedUs`（0.68–1.42 s/次）、
//   `createUs` 仅 75–92 µs、`restUs=0` ⇒ **那 0.47–1.4 s 全在"职业解析"这一层**。
//   这一层再拆成两笔，为下一刀（缓存 or 修真因）提供判据：
//     lookupUs = `Bindings.resolveWeaponConfigStringIndex(name)`（按名字查武器定义）
//     readUs   = `Bindings.readWeaponSelection(asset, selection)`（读该定义的登记项）
```

### 7.2 五个数

```text
resolveUs ≈ elapsedUs     0.68–1.42 s/次
createUs                  75–92 µs
restUs                    0
0.47–1.4 s                全在"职业解析"这一层
```

### 7.3 三层

```text
1. 三段拆分明确定死：`resolveUs ≈ elapsedUs`
2. 而 `createUs` 只有 75–92 µs，`restUs = 0`
3. ⇒ **那 0.47–1.4 s 全在"职业解析"**
4. ⇒ 再拆成 `lookupUs` 与 `readUs` 两笔
```

### 7.4 而**这与 §260 的修复直接相关**

**§260**：`resolveWeaponConfigStringIndex` 原来是"每次线性扫 1700 条"，实测 **165–300 ms/次**，11 个人机 = 8–13 s。

**⇒ 而这里说 `resolveUs` 是 **0.68–1.42 s/次**。**

**⚠ 比 165-300 ms 大 4 倍。**

**⇒ 可能**这份注释是在 §260 修复之前**写的，或者每个职业解析**两次**（primary + secondary）× 两个候选（bare + `_mp`）= 最多 4 次查找。**

**⇒ 4 × 165-300 ms = 0.66-1.2 s** ✓ **完全对上了！**

**⇒ 所以 `0.68–1.42 s` 是 **4 次查找**的合计。**

### 7.5 而 `resolveWeapon` 的**两个候选**

```cpp
const std::string bare(weaponName);
for (const std::string &candidate : { bare, bare + "_mp" })
{
    const auto asset = Bindings.resolveWeaponConfigStringIndex(candidate);
    ++lookupCalls;
    if (!asset || !*asset) continue;      // ← 【bare 失败则试 _mp】
    ...
}
```

**⇒ 所以每个武器最多 **2 次查找**。**

**⇒ 而每个职业 **2 个武器** ⇒ 最多 4 次。**

**✓ 与 7.4 的算术吻合。**

### 7.6 而"裸名先试"

```php
// THE CSV SHIPS BASE NAMES AND THIS BUILD'S DEFINITIONS END IN _mp. The live
// census (1163 resident weapon definitions) holds scarsapr_mp / m9_mp / ... and
// no bare scarsapr / m9, so both forms are tried -- bare first -- and a class
// whose weapons do not resolve falls back to the host clone instead of inventing
// an index. Measured 2026-10-11: coltanaconda is resident under neither form, so
// class 5 keeps the clone and the fallback line says so.
```

### 7.7 四层

```text
1. CSV 出货的是【基础名】而本 build 的定义以 `_mp` 结尾
2. 活普查（1163 个常驻武器定义）持有 `scarsapr_mp`/`m9_mp`/… 而**没有裸 `scarsapr`/`m9`**
3. ⇒ 两种形式都试 —— **裸名先**
4. 一个职业的武器解析不出来 ⇒ 回退到**宿主的克隆**而不是发明一个索引
5. 实测 2026-10-11：`coltanaconda` 在两种形式下都不常驻 ⇒ **职业 5 保持克隆**且回退行说明了
```

### 7.8 **"裸名先试"是浪费**

**⇒ 因为已知本 build 的定义以 `_mp` 结尾 ⇒ 裸名**必然失败**。**

**⚠ 所以每次查找都是"先失败一次再成功"⇒ 双倍开销。**

**⇒ 这正是 §260 优化前 4 次查找的原因。**

**⇒ 而"裸名先"的理由是：`The CSV ships base names` —— 所以理论上可能有两种。**

**⇒ 但实测"没有裸 `scarsapr`/`m9`"。**

**⚠ 可以改成 `_mp` 先试 ⇒ 减半开销。**

### 7.9 而**1163 个常驻武器定义**

**⇒ 与 §285 的 `1163..1213` 的起始索引 1163 是同一个数？**

**⚠ 巧合。**

**⇒ 但 §285 说 1163 是**第一个动态武器的索引**而这里说 1163 是**武器定义的总数**。**

**⚠ 两个不同的语义、同一个数字 —— 值得指出。**

## 八、`BOTTRACE|class-resolve` 的**六个字段**

```php
"BOTTRACE|class-resolve index=" + index + " class=" + trace +
" lookupUs=" + lookupUs + " lookupCalls=" + lookupCalls +
" readUs=" + readUs + " readCalls=" + readCalls +
" totalUs=" + since(stageBegin)
```

### 8.1 七个

```text
index / class
lookupUs / lookupCalls
readUs / readCalls
totalUs
```

### 8.2 而"一行一次（每局 11 次）"

**⇒ 所以 11 个 bot × 1 行 = 11 行。**

**⇒ 与"11 个人机"一致** ✓

### 8.3 而 `OLMOD_BOT_CLASS_TIMING=0` 可关

**⇒ 第十一种环境变量解析**（`!(value && value[0] == '0')` 与 §287 的 `OLMOD_DMZ_LOOT_BAND` 相同）。

## 九、**738 个官方 bot 名**

```php
// The display name handed to createBotClient used to be "BOT<n>". The 21-generation
// client ships its own bot name pool -- 738 UTF-8 names, read out of the live
// process and embedded verbatim in codol_bot_names.hpp. This generation's pool is
// what the game itself shows; the 2697/Antia roster belongs to another generation
// and does not contain any of these names.
```

### 9.1 四层

```text
1. 显示名过去是 `"BOT<n>"`
2. 21 代客户端自带一个 bot 名池 —— **738 个 UTF-8 名**，从活进程读出并逐字节嵌入 `codol_bot_names.hpp`
3. ⇒ 这一代的池才是游戏自己显示的
4. 而 **2697/Antia 名册属于另一代**且不含这些名
```

### 9.2 而"2697/Antia"的排除

**⇒ 与 §288 的"`ab_1mc_lead_taken_01`"类似 —— **代际**区分。**

**⇒ 与 §272 的"client_names"??**

**⇒ 总之："不要用另一代的名册"。**

### 9.3 而"契约是**调用者提供批次**"

```php
// The reference launcher feeds a per-match batch through the GSC dvars
// scr_codol_botname0..15, i.e. the contract is "the caller supplies the batch".
// The same contract is honoured here as OLMOD_BOT_NAMES="Name1,Name2,...";
// unset or empty falls back to the shipped pool, cycled by slot index. No name is
// invented: the fallback is the client's list and the override is the caller's.
```

### 9.4 四层

```text
1. 参考启动器通过 GSC dvar `scr_codol_botname0..15` 每局喂一批
2. ⇒ 契约是"**调用者提供批次**"
3. ⇒ `OLMOD_BOT_NAMES="Name1,Name2,..."` 履行同一个契约
4. 未设置 ⇒ 回退到出货池，**按槽索引循环**
5. ⇒ **没有名字被发明**：回退是客户端的列表，覆盖是调用者的
```

**⇒ 与 §279 的"参数化 > 枚举"同族** —— 第六次。

### 9.5 而**16 个 dvar 槽**（`0..15`）

**⇒ 所以每局最多 16 个名字**（而实际 11 个 bot）。

## 十、`OLMOD_BOT_NAMES` 的**手写 CSV 解析**

```php
std::vector<std::string> supplied;
std::string current;
for (const char *cursor = value;; ++cursor)
{
    if (*cursor != ',' && *cursor != '\0') { current.push_back(*cursor); continue; }
    while (!current.empty() && (current.front() == ' ' || current.front() == '\t'))
        current.erase(current.begin());
    while (!current.empty() && (current.back() == ' ' || current.back() == '\t'))
        current.pop_back();
    if (!current.empty()) supplied.push_back(current);
    current.clear();
    if (*cursor == '\0') break;
}
```

### 10.1 三层

```text
逐字符累加到 ','
去前后空格与制表
非空则收录
'\0' 时 break
```

### 10.2 ⚠ **`current.erase(current.begin())` 是 O(n) 每个字符**

**⇒ 对一个 738 名的池不显著（因为只在启动时跑）。**

**⇒ 但 `erase(begin())` 在循环里是 O(n²)。**

**⚠ 一处可优化点。**

### 10.3 而**只去空格与制表，不去 `\r`**

**⚠ 与 §252 的 `aliasedWeaponName` 处理 `\r` **不同**。**

**⇒ 所以一个 CRLF 结尾的名会带 `\r`。**

## 十一、关键结论

1. **四个收尾步骤**是事务式的（先构建 next、后原子交换）。
2. **专用服的 `finalCharacter` 检查恒通过**（因为两边同源）。
3. **`BotsCreated` 从不重置 ⇒ 第三/四张地图没有 bot** —— "状态的作用域错了"的第二个实例。
4. **修复用会话代际 + 两个条件**（`configured` 且代际变了）。
5. **`BotSpawnRequests` 是第九个"控制线程 → 游戏线程"的通道**（用 atomic 累加）。
6. **`resolveUs ≈ elapsedUs` = 0.68–1.42 s**，而 `createUs` 只有 75–92 µs。
7. **两个候选（bare + `_mp`）× 两个武器 = 4 次查找** ⇒ 与 §260 的 165-300 ms × 4 = 0.66-1.2 s **算术吻合**。
8. **"裸名先试"是浪费** —— 因为已知本 build 的定义以 `_mp` 结尾。
9. **1163 是"武器定义总数"而 §285 的 1163 是"第一个动态武器索引"** —— 同一个数字两种语义。
10. **738 个官方 bot 名**从活进程读出并逐字节嵌入 `codol_bot_names.hpp`。
11. **"2697/Antia 名册属于另一代"** —— 代际区分。
12. **`scr_codol_botname0..15` 的契约是"调用者提供批次"** ⇒ `OLMOD_BOT_NAMES` 履行同一契约。
13. **手写 CSV 解析用 `erase(begin())` 是 O(n²)**，且不去 `\r`。

## 十二、未闭合点

- `1163` 的两种语义是否有混淆。
- `OLMOD_BOT_NAMES` 的 `\r` 处理。
- `resolveWeaponConfigStringIndex` 在 §260 修复后是否还有 0.68-1.42 s。
- `Appmain.cpp` 4780 行之后未读取。
