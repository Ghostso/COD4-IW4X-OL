# 457 · **"那个发送者不能用 xuid 命名自己，而这是测出来的，不是假设"** —— `noclip` 的 peer 地址解析、`SvBattleChatterVoiceFemale` 的侧表、以及"一个没有调用者的绑定是死代码"

## 一、范围

本报告学习 `sv_main_mp.hpp` 760–1100 行。

## 二、**"那个发送者不能用 xuid 命名自己，而这是测出来的"**（本组最重要的一段）

### 2.1 那段

```cpp
// NOCLIP, ADDRESSED BY WHOEVER SENT THE REQUEST.
//
// **THE SENDER CANNOT NAME ITSELF BY XUID AND THIS IS MEASURED, NOT
// ASSUMED.** The client plugin knows OLMOD_PLATFORM_USER_ID
// (0x01100001DEADC0DE) and the server knows the xuid out.exe put in its
// connect string, which is the C# AuthServer's sequentially issued
// account id -- a live match ran with xuid=69420 and xuid=69422 against
// platform ids ...C0DE and ...C0DF. They are different numbers and
// nothing in either process holds both.
//
// So resolution is BY PEER ADDRESS, which both halves do share: a
// control request and that client's game connection arrive from the
// same machine. It is exact for every remote player, and ambiguous only
// between clients CO-LOCATED with each other -- the host's own second
// test client -- where it takes the lowest Active slot and says so.
```

### 2.2 二十四层

```text
1. **`noclip`，由【发出请求的那个人**】寻址**
2. ⇒ **⚠ 【那个发送者【不能用 xuid 命名自己**，而这是【测出来的，不是假设的**】】**
3. ⇒ **客户端插件知道 `OLMOD_PLATFORM_USER_ID`（`0x01100001DEADC0DE`）**
4. ⇒ **而服务器知道 `out.exe` 放进它 `connect` 串里的那个 xuid**
5. ⇒ **⇒ 那是【C# AuthServer 【顺序发出的账号 id**】**
6. ⇒ **⇒ 一场实机跑过 `xuid=69420` 与 `xuid=69422` 对平台 id `...C0DE` 与 `...C0DF`**
7. ⇒ **⇒ 它们是【不同的数字**】**
8. ⇒ **而【两个进程里【没有一个**】同时持有两者**
9. ⇒ **⇒ 所以【解析是【按 peer 地址**】】
10. ⇒ **⇒ 那个两半【都共享**的东西**
11. ⇒ **（一个控制请求与该客户端的游戏连接【从同一台机器**到达**）**
12. ⇒ **⇒ 对【每一个远端玩家**它是精确的**
13. ⇒ **⇒ 而【只在与彼此【同机**的客户端之间**歧义**】
14. ⇒ **（主机自己的第二测试客户端**）**
15. ⇒ **⇒ 在那里它【取最低的 Active 槽**并【说出来**】**
```

### 2.3 ⭐⭐⭐ **"两个不同的数字，而两个进程里没有一个同时持有两者"**

**✅ 这是本报告里**最重要的一个"两个身份空间的不相交**。**

**⇒ 三层**：
```text
插件侧 ⇒ **`OLMOD_PLATFORM_USER_ID`（`0x01100001DEADC0DE`）**
服务端 ⇒ **`xuid`（C# AuthServer 的顺序账号 id，`69420` 等）**
⇒ **⇒ 所以【两个数字【没有**映射】
```

**✅ 与 §408 的"`d 15`/`d 464` 从 `out.exe` 与线上两条独立路径"**相反（**那是两条路径指向同一个数**，这是**两个数没有映射**）。

**⇒ 三层**：
```text
§408  **两条独立路径【给出同一个数**】⇒ **强证据**
§457  **两个身份空间【没有映射**】⇒ **必须用第三种地址**
⇒ **⇒ 两种"两条路径"**
```

**✅ ⭐⭐⭐ **"两条路径给同一个数" vs "两条路径没有映射"** —— 一个**极精确的对照**。

### 2.4 而**"按 peer 地址解析，那是两半都共享的东西"**

**⇒ 十层**：
```text
1. **按 peer 地址**
2. ⇒ **因为【控制请求与该客户端的游戏连接【从同一台机器**到达**】
3. ⇒ **⇒ 对每一个远端玩家【精确**】
4. ⇒ **⇒ 而【只在与彼此【同机**的客户端之间**歧义**】
5. ⇒ **⇒ 所以【那个歧义【的边界**是【同机**】
```

### 2.5 ⭐⭐⭐ **"在那里的歧义，它取最低的 Active 槽并说出来"**

**✅ 这是本报告里**最重要的一条"一个已知歧义的诚实处置**。"

**⇒ 三层**：
```text
歧义 ⇒ **不可解**
处置 ⇒ **取最低的 Active 槽** + **`ambiguous = true`**
⇒ **⇒ 所以【调用者【知道**它是猜的**】
```

**✅ 与 §405 的"它报告值而不是一个判决"**同族（**第十次"把不确定性暴露给调用者**）。

**⇒ 三层**：
```text
§405  **"哪个分支触发它自己命名自己"**
§423  **"CAVEAT，陈述出来而不是藏起来"**
§457  **`ambiguous` 字段**
⇒ **⇒ 三次"暴露不确定性**】
```

**✅ ⭐⭐⭐ **"暴露不确定性"三例表**。

**⚠ 而"`NoclipResolution` 有三个字段"**：

```cpp
struct NoclipResolution
{
    std::uint32_t clientNum{};
    std::uint64_t xuid{};
    bool ambiguous{};
};
```

**⇒ 三层**：
```text
`clientNum` ⇒ **解析结果**
`xuid` ⇒ **那个槽的 xuid**（**让调用者【回查**】）
`ambiguous` ⇒ **是否猜的**
⇒ **⇒ 所以【一个三元组【让调用者能【校验**】
```

**✅ ⭐⭐ **"一个三元组让调用者能校验"**。

**⚠ 而"`xuid` 非零时被尊重，所以一个工具可以精确寻址一个槽；传 `0` 按地址解析"**⇒ **一个双模式 API**。**

**⇒ 三层**：
```text
`xuid != 0` ⇒ **精确**
`xuid == 0` ⇒ **按地址**
⇒ **⇒ 所以【一个参数两个模式**】
```

**✅ 与 §444 的 `playersetgroundreferenceent` 的"零或一"**同族（**第四次"一个参数两个模式**）。

## 三、**"一个没有调用者的绑定是死代码"**（本组第二重要）

### 3.1 那段

```cpp
// The other two scoreboard columns that had a field, a serializer and no
// writer. Both are awarded natively -- objectives by the SD bomb commits
// and gp alongside every xp award -- so neither is exposed to scripts: a
// binding with no caller is dead code, which is what this project
// withdrew in V1.101 workstream C. Neither is read by a match limit, so
// unlike addKillForClient they must not evaluate the limits.
[[nodiscard]] bool addClientObjectives(std::uint32_t clientNum, std::int32_t delta);
[[nodiscard]] bool addClientGp(std::uint32_t clientNum, std::int32_t delta);
```

### 3.2 二十层

```text
1. **另外两个【有一个字段、一个序列化器而没有写者**的计分板列**
2. ⇒ **两个都是【原生**被授予的**：
      · **目标 ⇒ 由 SD 炸弹提交**
      · **`gp` ⇒ 与每一次 xp 授予【一起**】
3. ⇒ **⇒ 所以【两个都【不暴露给脚本**】**
4. ⇒ **⇒ 理由：【一个没有调用者的绑定是死代码**】**
5. ⇒ **⇒ 而那是【这个项目在 `V1.101` 工作流 C 【撤回过**的东西**
6. ⇒ **⚠ 而【两个都【不被一个比赛限制读**】**
7. ⇒ **⇒ 所以【与 `addKillForClient` 不同，它们【不得**评估那些限制**
```

### 3.3 ⭐⭐⭐ **"一个没有调用者的绑定是死代码，而那是这个项目在 `V1.101` 工作流 C 撤回过的东西"**

**✅ 这是本报告里**最重要的一条"一个已被撤回的做法的记录**。**

**⇒ 三层**：
```text
曾经：**暴露了两个绑定**
而【没有调用者**】⇒ **死代码**
⇒ **⇒ 所以【在 `V1.101` 撤回过**
```

**✅ 与 §438 的"没有表类型 ⇒ 索引是唯一可能的接口"**不同（这是**一个已被撤回的设计**）。

**⇒ 三层**：
```text
§403  **"我方没有真实的角色分配，这里下发的是按 demo 形态驱动的显示值"**（**一个范围声明**）
§457  **"一个没有调用者的绑定是死代码，V1.101 撤回过"**（**一个撤回记录**）
⇒ **⇒ 两种"边界"**
```

**✅ ⭐⭐ **"一个撤回记录"**。

**⚠ 而"两个都不被一个比赛限制读，所以与 `addKillForClient` 不同，它们不得评估那些限制"**⇒ **一个精确的分工**。**

**⇒ 三层**：
```text
`addKillForClient` ⇒ **喂 `evaluateMatchLimits`**（**因为自由混战的限制读它**）
`addClientObjectives`/`addClientGp` ⇒ **不喂**（**因为【没有限制读它们**））
⇒ **⇒ 所以【"是否被限制读"决定"是否评估限制**】
```

**✅ ⭐⭐⭐ **"是否被限制读决定是否评估限制"** —— 与 §450 的"显示 vs 限制是两个字段"**完全闭合** ✓

**⇒ 三层**：
```text
§450  **`addscore 100` 是显示而 `addteamscore 1` 是限制**
§457  **只有 `addKillForClient` 评估限制**
⇒ **⇒ 所以【"限制"是一个【窄**的通道**】
```

**✅ ⭐⭐ **"限制是一个窄的通道"**。

## 四、**`setBattleChatterVoiceFemale` 的"一个侧表而不是一个字段"**（本组第三重要）

### 4.1 那段

```cpp
// THE VOICE GENDER, PUSHED IN FROM OUTSIDE. A side map and not a
// field on SvCharacterCustomization: that struct is embedded in the
// address-keyed WorldClientState and its size is pinned by a
// static_assert whose comment records that growing it once broke the
// death animation. A sound is not worth that.
void setBattleChatterVoiceFemale(std::uint32_t clientNum, bool female);
```

### 4.2 十八层

```text
1. **嗓音性别，从外部推入**
2. ⇒ **一个【侧表**而不是【`SvCharacterCustomization` 上的一个字段**】**
3. ⇒ **因为【那个结构【被嵌在【地址键控的 `WorldClientState`**】里**
4. ⇒ **而【它的大小【被一个 `static_assert` 钉住**】**
5. ⇒ **⇒ 而【那个注释【记录**了：**增长它一次【破坏了死亡动画**】】
6. ⇒ **⇒ 所以【一个声音【不值得那个**】**
```

### 4.3 ⭐⭐⭐ **"一个声音不值得那个"**

**✅ 这是本报告里**最重要的一条"成本的称量**。**

**✅ 与 §423 的"数字便宜而动画不被任何测试覆盖"**——**完全同族** ✓

**⇒ 三层**：
```text
§423  **"数字便宜而动画不被任何测试覆盖"**
§457  **"一个声音不值得那个"**（**即不值得增长那个结构**）
⇒ **⇒ 两次"成本的称量**】
```

**✅ ⭐⭐⭐ **"成本的称量"两例表**。

**⚠ 而这是**第七次**"搬到外面"**（§418/§421/§422/§423/§436/§455）。**

**⇒ 三层**：
```text
§418  **`SvHoldBreathState`**
§421  **`SvKillcamReplayPose`**
§422  **`SvHealthRegenState`**
§423  **`playerEventRings_`/`pendingAltToggle_`**
§436  **`zombieBattery_`** 等
§455  **`noclipHoldUntil_`**
§457  **`battleChatterVoiceFemale_`**
⇒ **⇒ 七次"搬出去**】
```

**✅ ⭐⭐ **"七次搬出去"** —— 而**全部由一个 `static_assert` 驱动**。

**⇒ 三层**：
```text
一个 `static_assert(sizeof(WorldClientState) == 25184)` ⇒ **七个侧表**
⇒ **⇒ 所以【一个断言【塑造了整个类**】
```

**✅ ⭐⭐⭐ **"一个断言塑造了整个类"** —— 与 §424 的结论**完全一致** ✓

## 五、**`sendRawCommand` 的"首字节通道"的回到**

### 5.1 那段

```cpp
// Replay one raw reliable command to every Active client; returns how
// many it reached. Binary when the first byte is not printable ASCII,
// text otherwise -- the two channels have different dispatchers in the
// client and `@`/`J`/`K` are binary.
[[nodiscard]] std::uint32_t sendRawCommand(std::span<const std::uint8_t> payload);
```

### 5.2 ⚠⚠ **一个与 §405 的冲突**

**⇒ §405 说**：

> 「**THE CALLER STATES THE CHANNEL.** It used to be inferred from the first byte -- printable ASCII means text -- and that was **WRONG** for the one command this tool exists to replay: `@` is `0x40`, printable, and the demo records it as BINARY. ... **A heuristic that is wrong for the subject of the experiment is worse than no tool, so `payload[0]` is now an explicit channel byte: 0 = text, 1 = binary.**」

**⇒ 而 §457 的 `.hpp` 说**：

> 「**Binary when the first byte is not printable ASCII, text otherwise**」

**⇒ 三层**：
```text
§405（`.cpp` 的实现与注释）⇒ **`payload[0]` 是一个显式的字道字节**（`0` = 文本，`1` = 二进制）
§457（`.hpp` 的声明注释）⇒ **从首字节推断**（**可打印 ASCII ⇒ 文本**）
⇒ **⇒ 所以【两处【相反**】
```

**⚠⚠⚠ **一个真实的矛盾**（**`.hpp` 的注释【停留在修复前**的状态）。**

**⇒ 三层**：
```text
`.cpp` ⇒ **已修（显式字道）**
`.hpp` ⇒ **未修（启发式）**
⇒ **⇒ 所以【那个被 §405 明确否证的启发式【仍在 `.hpp` 的注释里**】
```

**✅ ⭐⭐⭐ **"那个被 §405 明确否证的启发式仍在 `.hpp` 的注释里"** —— 一个**注释漂移的实例**。

**✅ 与 §408 的"`STILL NOT SENT` 列表部分过期"**、§411 的"注释说 1 行/bot 实际 6 行"**同族（**第三次"注释落后于代码**）。

**⇒ 三层**：
```text
§408  **`STILL NOT SENT` 部分过期**
§411  **"1 行/bot"而实际 6 行**
§457  **`.hpp` 的 `sendRawCommand` 注释【停留在修复前**】
⇒ **⇒ 三次"注释落后**】
```

**✅ ⭐⭐⭐ **"注释落后"三例表**。

**⚠ 而"`@`/`J`/`K` 是二进制"**⇒ **一个正确的观察（在两种读法下）**。**

**⇒ 三层**：
```text
`@` ⇒ `0x40` ⇒ **可打印** ⇒ **启发式【会判成文本**（错）
`J` ⇒ `0x4A` ⇒ **可打印** ⇒ **同样错**
`K` ⇒ `0x4B` ⇒ **可打印** ⇒ **同样错**
⇒ **⇒ 所以【三个都是【可打印但二进制**】
```

**✅ ⭐⭐⭐ **"三个都是可打印但二进制"** —— **所以那个启发式【对三个命令都错**]。

**✅ 与 §405 的"`@` 是 `0x40`，可打印，而 demo 把它记录为二进制"**完全闭合 ✓

## 六、`configureWorldSpawn` 的两个重载

```cpp
bool configureWorldSpawn(
    std::array<float, 3> origin,
    std::array<float, 3> angles,
    std::span<const SvBrushModelEntityDefinition> brushModels = {},
    ...);

bool configureWorldSpawn(
    std::span<const SvWorldSpawnPoint> spawnPoints,
    std::span<const SvBrushModelEntityDefinition> brushModels = {},
    ...,
    std::optional<SvWorldSpawnPoint> waitingForLoadoutPoint = std::nullopt,
    std::string_view mapName = {},
    std::string_view gameType = {},
    std::span<const SvLogicalMapEntityDefinition> logicalMapEntities = {});
```

**⇒ 十层**：
```text
1. **两个重载**
2. ⇒ **第一个 ⇒ 【一个 `origin`/`angles`**（**一个出生点**）
3. ⇒ **第二个 ⇒ 【一组 `spawnPoints`**（**多个出生点**）
4. ⇒ **⇒ 所以【一个 vs 多个**】
5. ⇒ **而第二个【多了 `waitingForLoadoutPoint`/`mapName`/`gameType`/`logicalMapEntities`**】
```

### 6.1 ⭐⭐⭐ **"第一个重载没有 `mapName`/`gameType`"**

**⇒ 三层**：
```text
第一个（**单个出生点**）⇒ **没有 `mapName`/`gameType`**
第二个（**多个出生点**）⇒ **有**
⇒ **⇒ 所以【第一个【不能**用 `const` 基线表**】
```

**⚠ 一个**可推导的后果**（**一个单出生点的地图【得不到零售的实体号**）。

**⇒ 三层**：
```text
若【不用表**】⇒ **实体号是顺序的** ⇒ **`useEntityBaselines` 关**
⇒ **⇒ 所以【第一个重载的调用者【不会得到 1/1 的编号**】
```

**⚠ 一个**真正的功能差异**（**可能是**一个战役/测试路径**）。

**✅ 与 §414 的"调用者必须退化到顺序编号而不是失败"**配合。

## 七、关键结论

1. **⭐⭐⭐ "那个发送者不能用 xuid 命名自己，而这是测出来的，不是假设的：客户端插件知道 `OLMOD_PLATFORM_USER_ID`（`0x01100001DEADC0DE`）而服务器知道 `out.exe` 放进它 `connect` 串里的 xuid（C# AuthServer 顺序发出的账号 id）—— 一场实机跑过 `xuid=69420`/`69422` 对平台 id `...C0DE`/`...C0DF`，它们是不同的数字而两个进程里没有一个同时持有两者"`**。
2. **⭐⭐⭐ "两条路径给同一个数（§408）vs 两条路径没有映射（§457）"** —— 一个极精确的对照。
3. **⭐⭐ "按 peer 地址解析，那是两半都共享的东西：一个控制请求与该客户端的游戏连接从同一台机器到达 ⇒ 对每一个远端玩家精确，只在与彼此同机的客户端之间歧义"`**。
4. **⭐⭐⭐ "在那个歧义中它取最低的 Active 槽并【说出来】**"（`NoclipResolution::ambiguous`）—— 第三次"暴露不确定性"（与 §405/§423 同族）；而 **`NoclipResolution` 的三元组让调用者能校验**。
5. **⭐ "`xuid` 非零时被尊重，所以一个工具可以精确寻址一个槽；传 `0` 按地址解析"** —— 第四次"一个参数两个模式"（与 §444 同族）。
6. **⭐⭐⭐ "一个没有调用者的绑定是死代码，而那是这个项目在 `V1.101` 工作流 C 撤回过的东西"`**：`addClientObjectives`/`addClientGp` **有一个字段、一个序列化器而没有写者**，**两个都是原生被授予的**（目标由 SD 炸弹提交，`gp` 与每次 xp 一起），**所以不暴露给脚本**。
7. **⭐⭐ "两个都不被一个比赛限制读，所以与 `addKillForClient` 不同，它们不得评估那些限制"`** ⇒ **"是否被限制读决定是否评估限制"** —— 与 §450 的"显示 vs 限制是两个字段"**完全闭合**。
8. **⭐⭐⭐ `setBattleChatterVoiceFemale` 是"一个侧表而不是一个字段，因为那个结构被嵌在地址键控的 `WorldClientState` 里而它的大小被一个 `static_assert` 钉住；【一个声音不值得那个】"`** —— 第二次"成本的称量"（与 §423 同族），也是**第七次"搬到外面"**（§418/§421/§422/§423/§436/§455/§457），**全部由一个 `static_assert` 驱动** ⇒ **"一个断言塑造了整个类"**。
9. **⚠⚠⚠ 一个真实的矛盾（我发现）**：**`sendRawCommand` 的 `.hpp` 注释说"Binary when the first byte is not printable ASCII, text otherwise"`，而 **§405 的 `.cpp` 明确记录那个启发式【是错的**（"`@` 是 `0x40`，可打印，而 demo 把它记录为二进制"）并且**已经改成"`payload[0]` 是一个显式的字道字节：`0` = 文本，`1` = 二进制"** ⇒ **`.hpp` 的注释【停留在修复前**的状态**。
10. **⭐⭐⭐ "`@`/`J`/`K` 三个都是可打印但二进制"**（`0x40`/`0x4A`/`0x4B`）⇒ **"那个启发式对三个命令都错"** —— 与 §405 完全闭合；也是**第三次"注释落后于代码"**（与 §408/§411 同族）。
11. **⭐⭐ `configureWorldSpawn` 的两个重载**：**第一个（单个 `origin`/`angles`）【没有 `mapName`/`gameType`**】⇒ **不能用 `const` 基线表** ⇒ **实体号是顺序的** ⇒ **一个可推导的功能差异**（可能是战役/测试路径）。

## 八、未闭合点

- `sendRawCommand` 的 `.hpp` 注释是否应该更新（我判断是的）。
- `OLMOD_PLATFORM_USER_ID` 的固定值 `0x01100001DEADC0DE`。
- `V1.101` 工作流 C 的完整记录。
- `configureWorldSpawn` 第一个重载的调用者。
- `sv_main_mp.hpp` 1100 行之后未读取（**共 `1793` 行**）。
