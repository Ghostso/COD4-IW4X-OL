# 470 · **"如果你改这个字符串，你必须**在同一个提交里**重新生成 `SvGameStateFixtureBytes`**"** —— `sv_gamestate_mp.cpp/.hpp` 的 `12761/14/11` 三个宽度、一次 `6800 → 12246` 的修正、以及一个"三周三次调试"的警告

## 一、范围

本报告学习 `sv_gamestate_mp.cpp`（**`1,045` 行**）与 `sv_gamestate_mp.hpp`（**`727` 行**）全文件：动态材质注册、效果配置串的双向映射、`14`/`11`/`10`/`11`/`8`/`9`/`4`/`14` 八个宽度、`formatServerInfo` 的十键、玩家名的两种编码、`SV_ValidateGameState` 的十四组不变量、两张武器表的位流、以及 `%` 那条**活体**配置串更新命令。

## 二、**"如果你改这个字符串，你必须**在同一个提交里**重新生成 `SvGameStateFixtureBytes`"**（本组最重要的一段）

### 2.1 那段

```cpp
// RETAIL'S OWN SERVERINFO KEYS, measured -- see
// re/demo-re/20-zm-actor-lifecycle.md 12.13 and 12.19. `cs 0` on all
// four zm captures carries these ten keys, byte-identical across
// three maps, and in THIS order (serverinfo is sorted by key, which
// is why the numeric keys lead and ui_* trails scr_*).
//
// THEY ARE NOT DECORATION. sub_515340 -- the client's gamestate
// parse -- reads "mapname", "g_gametype", then atoi("2482"), then
// calls the gametype classifier sub_514E70, then atoi("g_hardcore").
// Two of the keys it reads are ones this server used to omit, so
// they resolved to atoi("") == 0 where retail gets 24.
//
// IF YOU CHANGE THIS STRING YOU MUST REGENERATE SvGameStateFixtureBytes
// IN THE HEADER IN THE SAME COMMIT. EngineBindings::bind() re-derives
// this writer's output at every launch and compares it to that array;
// a mismatch fails stage=message_bindings, the plugin never comes up
// on EITHER side, and the client reports "your level file differs from
// the server's" -- which looks nothing like a serverinfo problem and
// has now cost three separate debugging sessions.
```

### 2.2 二十四层

```text
1. **零售自己的 `serverinfo` 键【是被测量的**】
2. ⇒ **`cs 0` 在【四份 zm 抓包里【携带这十个键**】】
3. ⇒ **⇒ 而在【三张地图上【字节相同**】】
4. ⇒ **⇒ 而【以【这个顺序**】
5. ⇒ **⇒ 因为【`serverinfo` 【按【键**排序】
6. ⇒ **⇒ 所以【数字键【在前**而 `ui_*` 【在 `scr_*` 【之后**】
7. ⇒ **⚠ 【它们不是装饰**】**
8. ⇒ **`sub_515340`（客户端的 gamestate 解析）【读** `"mapname"`、`"g_gametype"`】
9. ⇒ **⇒ 然后 `atoi("2482")`**
10. ⇒ **⇒ 然后【调用【那个模式分类器 `sub_514E70`**】】
11. ⇒ **⇒ 然后 `atoi("g_hardcore")`**
12. ⇒ **⇒ 而【它读的两个键【是这个服务器【曾经【省略**的】】
13. ⇒ **⇒ 所以【它们【解析成 `atoi("") == 0`**】
14. ⇒ **⇒ 而【零售【得到 `24`**】
15. ⇒ **⚠ 而【若你改这个字符串【你必须【在同一个提交里【重新生成**那个数组**】
16. ⇒ **⇒ 因为 `EngineBindings::bind()` 【每次启动【重新推导**这个写者的输出**】
17. ⇒ **⇒ 并【与那个数组【比较**】
18. ⇒ **⇒ 而【一个不匹配【失败 `stage=message_bindings`**】】
19. ⇒ **⇒ 而【插件【在【两边【都起不来**】】
20. ⇒ **⇒ 而【客户端【报告【"your level file differs from the server's"**】】
21. ⇒ **⇒ 而那【看起来【完全不像**一个 `serverinfo` 的问题**】
22. ⇒ **⇒ 而它【已经【花掉三次独立的调试会话**】
```

### 2.3 ⭐⭐⭐ **"那看起来完全不像一个 serverinfo 的问题，而它已经花掉三次独立的调试会话"**

**✅ 这是本报告里**最重的一条"一个错误消息【指向【一个错误的子系统**。**

**✅ 与 §467 的"一个回落比一个失败更危险"**、§469 的"一个错的『成功』比一个失败坏"**——**同族**（**第三次"一个误导性的症状**）。

**⇒ 三层**：
```text
真正的错因 ⇒ **`serverinfo` 的一串键**
可见的症状 ⇒ **"你的关卡文件与服务器的不同"**
⇒ **⇒ 所以【那个症状【指向【fastfile/checksum**，而【不是【gamestate**
```

**✅ ⭐⭐⭐ **"那个症状指向 fastfile/checksum，而不是 gamestate"** —— 一个**极精确的误诊方向**。

**⚠ 而 `checksumFeed` 【确实【是 gamestate 的一部分**】**（`SV_WriteGameState` 的 `MSG_WriteLong(gameState.checksumFeed)`）。

**⇒ 十层**：
```text
`checksumFeed` ⇒ **一个客户端校验的种子**】
⇒ **⇒ 而【一个 gamestate 的字节差异【可能【被客户端【解释成【一个 checksum 失配**】
⇒ **⇒ 所以【那个"关卡文件不同"【可能【真的【源自【gamestate 的字节**】
```

**✅ ⭐⭐⭐ **"那个『关卡文件不同』可能真的源自 gamestate 的字节"** —— 而 **这就是为什么那条警告值三周**。

**⚠ 而"每条 `bind()` 都会重推并比较"**⇒ **一个"启动时的自校验**"**。

**⇒ 三层**：
```text
`bind()` ⇒ **每次启动【重推**那个写者的输出**
⇒ **⇒ 与 `SvGameStateFixtureBytes` 比较**
⇒ **⇒ 所以【那个数组【是一个【黄金向量**（golden vector）**
```

**✅ ⭐⭐⭐ **"那个数组是一个黄金向量"** —— 与 §389 的"黄金向量"**同族**。

### 2.4 而**十个键的精确内容**

```cpp
auto result = std::string(
        "\\2482\\24"
        "\\2485\\4"
        "\\2490\\214"
        "\\2491\\0"
        "\\3056\\2"
        "\\g_gametype\\") + gameState.gameType +
    "\\g_hardcore\\0"
    "\\mapname\\" + gameState.mapName +
    "\\scr_game_allowkillcam\\1"
    "\\scr_team_fftype\\0";
```

**⇒ 十六层**：
```text
1. `\2482\24`
2. `\2485\4`
3. `\2490\214`
4. `\2491\0`
5. `\3056\2`
6. `\g_gametype\<gt>`
7. `\g_hardcore\0`
8. `\mapname\<map>`
9. `\scr_game_allowkillcam\1`
10. `\scr_team_fftype\0`
⇒ **⇒ 十个键：【五个数字 / 五个名字**】
```

**✅ ⭐⭐⭐ **"五个数字，五个名字"** —— 而 **"数字键在前"** 正是**排序**的结果（`"2482" < "g_gametype"` 按字节）。

**⚠ 而 `ui_scorelimit`/`ui_timelimit`/`ui_halftime` 【被【追加【在【后面**】**（若 `uiGameRules` 存在）。

**⇒ 三层**：
```text
十个【固定**键**
⇒ **⇒ 而【三个 `ui_*` 【条件性**追加**
⇒ **⇒ 所以【`serverinfo` 【有【两个**形状**】
```

**✅ ⭐⭐ **"`serverinfo` 有两个形状"** —— 而**那个黄金向量【只有一个形状**（`uiGameRules` 为空）。

**⇒ 十层**：
```text
黄金向量：`\2482\24...\scr_team_fftype\0`（**十个键**）
⇒ **⇒ 所以【那个 fixture 【对应【一个【没有 `uiGameRules`**的 gamestate**】
```

**✅ ⭐⭐ **"那个 fixture 对应一个没有 uiGameRules 的 gamestate"** —— 一个**精确的适用范围**。

### 2.5 而**`scr_game_allowkillcam` 的三次翻转**

```cpp
// ★ 2026-10-18（甲方：「killcam 空白，现在连 UI 都没有」「死亡摄像机位置在
//   击杀者击杀时的位置」）——诊断：服务端**从未交付过 killcam**
//   （`sv_main_mp.cpp` 的 `killCamRecordingAvailable = false` ⇒ 走 2697 的
//   cancel 分支），但这里仍宣告 `scr_game_allowkillcam 1` ⇒ 客户端按"有回放"
//   自行切镜头：没有数据（画面空白）、连带把死亡 UI 拿掉、镜头停在击杀者身上。
//   ⇒ 28370 反转：**录制已打开（killCamRecordingAvailable=true）⇒ 宣告改回 1**，
//     否则客户端直接不申请回放（实测：有 UI、但 killcam 不播）。
//   回放（A2）落地后把 `killcamPlaybackImplemented` 置 true 即可恢复成 1。
"\\scr_game_allowkillcam\\1"
```

**⇒ 二十四层**：
```text
1. **甲方报告：「killcam 空白，现在连 UI 都没有」「死亡摄像机位置在击杀者击杀时的位置」**
2. ⇒ **诊断：服务端【从未交付过 killcam**】
3. ⇒ **（`sv_main_mp.cpp` 的 `killCamRecordingAvailable = false`**）
4. ⇒ **⇒ 所以【走 2697 的 `cancel` 分支**】
5. ⇒ **⚠ 但这里【仍宣告 `scr_game_allowkillcam 1`**】
6. ⇒ **⇒ 所以【客户端【按"有回放"【自行切镜头**】
7. ⇒ **⇒ 而【没有数据**⇒【画面空白**】
8. ⇒ **⇒ 而【连带【把死亡 UI 拿掉**】
9. ⇒ **⇒ 而【镜头【停在【击杀者**身上**
10. ⇒ **⇒ 反转：**录制已打开 ⇒ 宣告改回 `1`**】
11. ⇒ **⇒ 否则【客户端【直接【不申请回放**】
12. ⇒ **（实测：有 UI、但 killcam 不播）**】
```

**✅ ⭐⭐⭐ **"有 UI、但 killcam 不播"** —— 一个**极精确的实测对照**。

**✅ 与 §467 的"没有武器也没有手"**——**同族**（**第三次"一个宣告【与【一个能力**不符 ⇒ 一个可见的崩坏**）。

**⇒ 三层**：
```text
§467  **`NO_SPAWN_POINT` ⇒ 一个加载了的地图 + 没有武器 + 没有手**
§468  **回落到默认材质 ⇒ 每个表面画错**
§470  **宣告 `allowkillcam 1` 而没有数据 ⇒ 空白画面 + 死亡 UI 消失 + 镜头停错**
⇒ **⇒ 三次"一个【宣告**与【现实**的分裂**】
```

**✅ ⭐⭐ **"一个宣告与现实的分裂"三例表**。

**⚠ 而"三次翻转（`1` → `0` → `1`）"**⇒ **一个"能力标志**"的**依赖图**。

**⇒ 十层**：
```text
`killCamRecordingAvailable = true` ⇒ **`allowkillcam 1`** ✓
`killCamRecordingAvailable = false` ⇒ **`allowkillcam 0`**（或【不宣告**）
`killcamPlaybackImplemented = true` ⇒ **`allowkillcam 1`**（**A2 落地后**）
⇒ **⇒ 所以【那个宣告【是【两个**能力标志的函数**】
```

**✅ ⭐⭐⭐ **"那个宣告是两个能力标志的函数"** —— 而**注释【写出了那个函数**。**

**⚠ 而"三个 dvar 已撤回**"（`sv_botDifficulty`/`sv_botFov`/`codol_botNaturalStance`）**⇒ "在查清之前不再下发任何新 dvar"**。**

**⇒ 十层**：
```text
三个 dvar 【一上线【就伴随【"名字异常 + 全解锁失效 + 存档被重置"**】
⇒ **⇒ 而【回滚 V1.217 后【名字【立刻正常**】
⇒ **⇒ 所以【根因【落在【"往 gamestate 里【塞客户端可见下发内容**"**这条线上**】
⇒ **⇒ 而 `ui_ac130usetime` 【也被【撤下**（"已按 P0 单变量撤下"）**
```

**✅ ⭐⭐⭐ **"根因落在『往 gamestate 里塞客户端可见下发内容』这条线上"** —— 一个**极重要的运营结论**。

**✅ 与 §468 的"一个错的 weaponClass 会看起来像一个移植的 bug 好几周"**——**同族**（**第二次"一个改动【有【长尾**的误诊**）。

### 2.6 而**一个真实的编译陷阱**

```cpp
//   ⚠ 必须写成 `result +=`：只写字符串字面量是无副作用表达式，编译器会直接丢弃
//     （本刀第一次构建产物里 `ui_ac130usetime` 计数为 0，就是这个原因）。
// result += "\\ui_ac130usetime\\40";
```

**⇒ 十层**：
```text
1. **一行【单独的字符串字面量【是一个【无副作用**的表达式**】
2. ⇒ **⇒ 所以【编译器【直接【丢弃**它**】
3. ⇒ **⇒ 而【那一刀【第一次构建【产物里【那个键【计数为 `0`**】
4. ⇒ **⇒ 而【那【正是【这个原因**】
```

**✅ ⭐⭐⭐ **"那一刀第一次构建产物里那个键计数为 0，就是这个原因"** —— 一个**极精确的自我记录**。

**✅ 与 §465 的"注释说 REFUSES 而代码不拒绝"**——**不同**（那是一个**逻辑缺陷**，这是一个**语言陷阱**）。

## 三、**`12761 / 14 / 11` 三个宽度与一次 `7058 → 12761`**（本组第二重要）

### 3.1 那段

```cpp
// CODREF(sv_send_client_gamestate): widths and table limits below come
// from CODOL CL_ParseGameStateMessage and its weapon-table consumers.
// On 1649370 that pair is A 0x46DB20 <-> C 0x472D80, line for line.
//
// CODDIFF(1649370): the configstring table grew 7058 -> 12761, so the
// explicit index widened 13 -> 14 bits, and the weapon block grew
// 900 -> 1700 entries, so the weapon index widened 10 -> 11.
constexpr std::uint16_t MaxConfigStrings = 0x31D9;
constexpr std::uint32_t ConfigStringIndexBits = 14;
constexpr std::uint32_t WeaponIndexBits = 11;
```

### 3.2 二十四层

```text
1. **`0x31D9 = 12761`**（**`3×4096 + 1×256 + 13×16 + 9`**）
2. ⇒ **⇒ 而【旧的 `7058`**】
3. ⇒ **⇒ 所以【`7058 < 8192` ⇒ `13` 位够**】而【`12761 > 8191` ⇒ 必须 `14` 位**】
4. ⇒ **⇒ 而【武器块【`900 → 1700`**】
5. ⇒ **⇒ 所以【`900 < 1024` ⇒ `10` 位够**】而【`1700 > 1023` ⇒ 必须 `11` 位**】
```

**✅ ⭐⭐⭐ **两个宽度【都不是【一个选择，是【一个【必然**】**

**⇒ 十二层**：
```text
`2^13 = 8192 > 7058` ✓ ；`2^13 = 8192 < 12761` ✗ ⇒ **`14` 位**
`2^10 = 1024 > 900` ✓ ；`2^10 = 1024 < 1700` ✗ ⇒ **`11` 位**
⇒ **⇒ 所以【两个位宽【各自【被【一个具体的数**决定**
```

**✅ ⭐⭐⭐ **"两个位宽各自被一个具体的数决定"** —— 一个**极精确的推导**。

### 3.3 而**"`> 0x3FF` 曾写在**九处**"**

```cpp
// CODDIFF(1649370): THE WEAPON INDEX BOUND LIVES HERE AND NOWHERE ELSE.
// `> 0x3FF` -- 3.3.3.3's ten-bit bound -- was written into NINE separate places in
// this tree, and correcting one of them left the other eight rejecting exactly the
// weapons a real class produces: the live gamestate reports firstDynamicWeapon=1224,
// so every modular weapon is above 1023. This project has now paid for the same
// one-struct-many-files mistake three times (bind()'s gamestate fixture, the
// per-weapon attachment count, this), so the bound is defined once and derived from
// the block size it actually comes from.
constexpr std::uint16_t MaximumWeaponAssetIndex = WeaponConfigStringCount - 1;
static_assert(MaximumWeaponAssetIndex < (1u << 11), ...);
```

### 3.4 二十四层

```text
1. **`> 0x3FF`（3.3.3.3 的十位界）曾写在【九处**】
2. ⇒ **⇒ 而【改正其中一处【让【其余八处【仍然【拒绝【一个真实类【会产生**的那些武器**】
3. ⇒ **⇒ 因为【活的 gamestate 【报告 `firstDynamicWeapon = 1224`**】
4. ⇒ **⇒ 所以【每一个模块化武器【都在 `1023` 之上**】
5. ⇒ **⚠ 而这个项目【已经【为【同一个"**一个结构、多个文件**"的错误【付过【三次**】
6. ⇒ **（`bind()` 的 gamestate fixture / 每个武器的挂载数 / 这个**）**
7. ⇒ **⇒ 所以【那个界【在这里【被定义一次**】
8. ⇒ **⇒ 而【从【它实际来自的那个块大小【推导**】
```

### 3.5 ⭐⭐⭐ **"改正其中一处让其余八处仍然拒绝一个真实类会产生的那批武器"**

**✅ 这是本报告里**最重要的一条"一个值【写在【九处**的**病灶**"**。**

**✅ 与 §466 的"`Skipped` 的五个 classname"**、§467 的"`mp_<gametype>_spawn` 形式"**——**同族**（**第三次"一个枚举/常量【的【多处**副本**）。

**⇒ 三层**：
```text
改一处 ⇒ **八个旧界【存活**】
⇒ **⇒ 所以【一半的武器【被接受**而【另一半【被拒绝**】
⇒ **⇒ 而【那个症状【看起来【像一个【解析**错误**，不是【一个【常量**错误**】
```

**✅ ⭐⭐⭐ **"那个症状看起来像一个解析错误，不是一个常量错误"**。

**✅ ⭐⭐⭐ **"这个项目已经为同一个『一个结构、多个文件』的错误付过三次：`bind()` 的 gamestate fixture / 每个武器的挂载数 / 这个"** —— **一个三次重复的病灶**。

**⇒ 三层**：
```text
第一次 ⇒ **`bind()` 的 fixture**
第二次 ⇒ **每个武器的挂载数**
第三次 ⇒ **武器索引界（九处）**
⇒ **⇒ 所以【那个教训【是【"定义一次，从源推导**"**】
```

**✅ ⭐⭐⭐ **"定义一次，从源推导"** —— 一个**极清晰的教训**。

**⚠ 而"`static_assert(MaximumWeaponAssetIndex < (1u << 11))`"**⇒ **一个【编译期**的保证**。

**⇒ 三层**：
```text
`WeaponConfigStringCount - 1 = 1699 < 2048` ✓
⇒ **⇒ 所以【一个【未来**的 `WeaponConfigStringCount` 增长【会【在编译期【失败**】
```

**✅ ⭐⭐⭐ **"一个未来的增长会在编译期失败"** —— 与 §468 的 `static_assert(sizeof(void*) == 4)`**同族**（**第二次"一个 `static_assert` 【是一个【行为**"**）。

### 3.6 而**`6800 → 12246` 的修正**

```cpp
// CODDIFF(1649370): 6800 -> 12246, +5446, NOT the +608 a global vote
// proposed. 7408 would land inside the weapon block itself. out.exe's
// consumer sub_590A60 reads byte_77DB226, and that address minus the
// configstring class table byte_77D8250 is exactly 0x2FD6 = 12246.
constexpr std::uint16_t WeaponCountConfigStringIndex = 12246;
```

**⇒ 十六层**：
```text
1. **`6800 → 12246`（`+5446`）**
2. ⇒ **⚠ 而不是【一个"全局投票"提议的 `+608`**】
3. ⇒ **⇒ 因为【`7408` 【会【落在【武器块【本身【里面**】】
4. ⇒ **⇒ （`7408` 在 `5960..7659` 之间 ⇒ 是【一个武器槽**）**
5. ⇒ **⇒ 而 `out.exe` 的消费者 `sub_590A60` 【读 `byte_77DB226`**】
6. ⇒ **⇒ 而【那个地址【减【那个配置串类表 `byte_77D8250`**】
7. ⇒ **⇒ 【恰好是 `0x2FD6 = 12246`**】
```

**✅ ⭐⭐⭐ **"`7408` 会落在武器块本身里面"** —— 一个**极精确的否决理由**。

**⚠ 而独立性验证**：`5960 ≤ 7408 < 5960+1700 = 7660` ✓ **落在块内**。

**⇒ 三层**：
```text
`WeaponConfigStringBase = 5960`
`WeaponConfigStringCount = 1700` ⇒ **`5960..7659`**
`7408` 【在【那个区间**】⇒ **⇒ 所以【它会【覆盖【一个武器**】
```

**✅ ⭐⭐⭐ **"它会覆盖一个武器"** —— **一个 `+608` 的提议【会造成【一个武器【被一个计数**覆盖**。

**✅ 与 §463 的"一个夹会把那个 bug 藏在 slot 14 的弹药里"**——**同族**（**第三次"一个错的偏移【会【静默地覆盖**"**）。

**⚠ 而独立验证 `0x2FD6`**：`2×4096 + 15×256 + 13×16 + 6 = 8192 + 3840 + 208 + 6 = 12246` ✓

**⇒ 三层**：
```text
`0x2FD6` 的十进制 = `12246` ✓
⇒ **⇒ 与【那个常量【一致**】
```

**✅ ⭐⭐ **"与那个常量一致"** —— 一个**精确的算术闭合**。

## 四、**八个位宽的总表**

```text
MaxConfigStrings              = 0x31D9 = 12761
ConfigStringIndexBits         = 14
WeaponIndexBits               = 11
SimpleWeaponTableCountBits    = 10
ModularWeaponTableCountBits   = 11
ModularValue8Bits             = 8
ModularValue9Bits             = 9
AttachmentCountBits           = 4
AttachmentIndexBits           = 14
```

### 4.1 而**"两张表的计数宽度不同，而 3.3.3.3 看不出来"**

```cpp
// CODDIFF(1649370): the two weapon tables carry SEPARATE count widths
// and 3.3.3.3 could not show it - there all four of these fields were
// ten bits, so one shared WeaponIndexBits was indistinguishable from
// four constants. Here the simple table's count is still ten bits
// (C 0x472E8C) while the modular table's is eleven (C 0x472F99).
```

**⇒ 二十层**：
```text
1. **两张表【携带【分开的**计数宽度**】
2. ⇒ **⚠ 而【3.3.3.3 【看不出来**】】
3. ⇒ **⇒ 因为【那里【这四个字段【都是十位**】
4. ⇒ **⇒ 所以【一个共享的 `WeaponIndexBits` 【与【四个常量【不可区分**】
5. ⇒ **⇒ 而在这里【简单表的计数仍是十位**（`0x472E8C`）**
6. ⇒ **⇒ 而【模块化表的【是十一位**（`0x472F99`）**
```

### 4.2 ⭐⭐⭐ **"那里四个字段都是十位，所以一个共享常量与四个常量不可区分"**

**✅ 这是本报告里**最漂亮的一条"一个退化情形【掩盖【一个结构**"**。**

**✅ 与 §468 的"`semantic` 不能区分 `normalMap` 与 `detailMap`"**——**同族**（**第二次"一个粗粒度的键【掩盖**一个精细的差别**）。

**⇒ 三层**：
```text
3.3.3.3：四个字段【都是 `10`** ⇒ **一个常量【完全等价**】
1649370：`10`/`11`/`10`/`11`** ⇒ **必须【四个**常量**
⇒ **⇒ 所以【一个【旧的**共享常量【在【新的 build**【错一半**】
```

**✅ ⭐⭐⭐ **"一个旧的共享常量在新的 build 上错一半"** —— 一个**极清晰的迁移风险**。

**⚠ 而这也是**§414 的"平台化"**的另一个实例**。**

**⇒ 三层**：
```text
§414  **`288/397` 的平台化**（**一个编号规则【在一个 build 上【不成立**）
§470  **四个十位字段【在一个 build 上【退化成一个**】
⇒ **⇒ 两次"一个 build 的具体性【只【在一个 build 上【可见**】
```

**✅ ⭐⭐ **"一个 build 的具体性只在一个 build 上可见"两例**。

## 五、**`SV_ValidateGameState` 的十四组不变量**

### 5.1 十四组

```text
① playerNames.size() <= PlayerNameConfigStringCount（18）
② 每个 clientNum ∈ [0,18)：有名字 ⇒ 那个 cs 存在且等于预期；无名字 ⇒ 那个 cs 不存在
③ mapName/gameType 非空、无 '\0'、无 '\\'
④ serverInfo 存在且等于 formatServerInfo(gameState)（**逐字节重推**）
⑤ systemInfo 的空性 ⇔ uiGameRules 的空性
⑥ uiGameRules && 三个 ui_* 值匹配
⑦ gameName 存在且 == "cod"
⑧ mapCenter 存在且 parseMapCenter 往返一致
⑨ northYaw 与 miniMap 的存在性互相等价，且都与它们各自的 cs 存在性等价
⑩ northYaw 有限且 formatFloat 往返一致
⑪ miniMap 的 formatMiniMap 往返一致
⑫ configStrings.size() <= INT16_MAX
⑬ 每个 (index, value)：index < 12761、无 '\0'、**不在武器块里**
⑭ 每个 (index, value)：若在 server material 块里，则必须有 firstDynamic 且 index >= base+firstDynamic 且 value 非空且 < 64
```

### 5.2 ⭐⭐⭐ **"serverInfo 存在且等于 `formatServerInfo(gameState)`" —— 一个【逐字节重推】**

**✅ 与 §468 的"`p == storage.size()` 是唯一的『完全理解』证明"**——**同族**（**第二次"一个【重推**的相等**）。

**⇒ 三层**：
```text
§468  **`p == storage.size()`**（**一个走过的证明**）
§470  **`serverInfo->second == formatServerInfo(gameState)`**（**一个重推的证明**）
⇒ **⇒ 两次"一个【重推**是【唯一**的验证方式**
```

**✅ ⭐⭐⭐ **"一个重推是唯一的验证方式"** —— 而**这正是 §470 二 的"黄金向量"的**第二个实例**。

### 5.3 而**第 ⑬ 组的"不在武器块里"**

```cpp
for (const auto &[index, value] : gameState.configStrings)
{
    if (index >= MaxConfigStrings || value.find('\0') != std::string::npos ||
        validWeaponConfigStringIndex(index) || ...)
        return false;
}
```

**⇒ 十层**：
```text
1. **武器块（`5960..7659`）【不能【出现在 `configStrings` 里**】
2. ⇒ **⇒ 因为【它们【走【两张独立的**表**】
3. ⇒ **⇒ 所以【一个【重复**的武器【会被【拒绝**】
```

**✅ ⭐⭐⭐ **"武器块的项不能出现在 configStrings 里，因为它们走两张独立的表"** —— 一个**极清晰的互斥**。

**✅ 与 §469 的"`simpleWeaponConfigStrings` 与 `modularWeaponConfigStrings` 互斥"**——**完全闭合** ✓

**⇒ 三层**：
```text
§469  **`SV_AddSimpleWeaponConfigString` ⇒ `if (modular.contains(index)) return false;`**
§469  **`SV_AddModularWeaponConfigString` ⇒ `if (simple.contains(index)) return false;`**
§470  **`if (validWeaponConfigStringIndex(index)) return false;`**
⇒ **⇒ 三层【互斥**】
```

**✅ ⭐⭐⭐ **"三层互斥"** —— **一个不变量在【三个层次**上被保证**。

### 5.4 而**第 ⑫ 组的"`<= INT16_MAX`"**

```cpp
gameState.configStrings.size() >
    static_cast<std::size_t>(std::numeric_limits<std::int16_t>::max())
```

**⇒ 十层**：
```text
`configStrings.size()` ⇒ **`<= 32767`**
而【`MaxConfigStrings = 12761`**】⇒ **⇒ 所以【那个界【永远【不会【被触发**】
```

**⚠ 一个【可能过时的界**】**（`12761 < 32767`）。**

**⇒ 三层**：
```text
若【每个 index 【唯一**】⇒ **size <= 12761 < 32767** ⇒ **那个判据【恒真**】
⇒ **⇒ 所以【那个检查【是【一个【冗余**的界**】
```

**✅ ⭐⭐ **"那个检查是一个冗余的界"** —— 一个**可质疑但不危险的冗余**。

**⚠ 而它有【一个可能的理由**】。**

**⇒ 三层**：
```text
写者【用 `MSG_WriteShort(count)`**（**`uint16`**）⇒ **`65535` 是【真正的**上限**
⇒ **⇒ 所以【那个 `INT16_MAX` 【不是【从写者**推导的**
```

**✅ ⭐⭐⭐ **"那个 `INT16_MAX` 不是从写者推导的"** —— 一个**值得注意的缺口**（`65535` 才是写者的界，而 `12761` 是表的界）。

## 六、**两张武器表的位流：一个"顺序连续 ⇒ 一个位"的编码**

### 6.1 那段

```cpp
message.MSG_WriteBits(static_cast<std::int32_t>(records.size()), countBits);
auto previous = -1;
for (const auto &[configStringIndex, value] : records)
{
    const auto sequential = static_cast<int>(configStringIndex) == previous + 1;
    message.MSG_WriteBits(sequential ? 1 : 0, 1);
    if (!sequential)
        message.MSG_WriteBits(configStringIndex, ConfigStringIndexBits);
    writeValue(message, value);
    previous = configStringIndex;
}
```

### 6.2 二十层

```text
1. **先写【计数**（`countBits`）**
2. ⇒ **⇒ 然后【每一项：一个位【说"是否【与上一项【连续**"】】
3. ⇒ **⇒ 若不连续【再写【14 位的绝对索引**】
4. ⇒ **⇒ 然后【类型自己的数据**】
5. ⇒ **⇒ 所以【一个【连续的族【只花【一个位【每个**】】
```

### 6.3 ⭐⭐⭐ **"一个连续的族只花一个位每个"**

**✅ 与 §466 的"`ordinal` 在 `continue` 之前 `++`"**——**不同**（那是一个**计数**，这是一个**差分编码**）。

**⇒ 三层**：
```text
若【`1700` 个武器【全部连续**】⇒ **`1700` 位 + `1700 × 11` 位 = `20400` 位**
若【不连续**】⇒ **`1700 × (1 + 14 + 11)` = `44200` 位**
⇒ **⇒ 所以【那个一位【省下【`23800` 位 = `2975` 字节**】
```

**✅ ⭐⭐⭐ **"省下 2975 字节"** —— 一个**可推导的量化**。

**⚠ 而 `previous = -1` 是【必须的**】**。**

**⇒ 六层**：
```text
若【`previous = 0`**】⇒ **index `0` 【会【被当成【不连续**】
而【`previous = -1`**】⇒ **index `0` == `-1 + 1` ⇒ 连续** ✓
⇒ **⇒ 所以【那个初值【是【必须的**】
```

**✅ ⭐⭐ **"那个初值是必须的"**。

**⚠ 而 `SV_WriteGameState` 的 configstring 表【用【同一个把戏**】**（`previous = -1`）。**

**⇒ 三层**：
```text
`writeWeaponConfigStringTable` ⇒ `previous = -1`
`SV_WriteGameState` 的 configstring 循环 ⇒ `previous = -1`
⇒ **⇒ 两处【同一个编码**】
```

**✅ ⭐⭐ **"两处同一个编码"**。

### 6.4 而**模块化值的位布局**

```cpp
baseWeaponAssetIndex   → 11 bits
value8                 →  8 bits
optionalValue9 != 0    →  1 bit
[optionalValue9]       →  9 bits
attachmentCount        →  4 bits
each attachment        → 14 bits
```

**⇒ 十六层**：
```text
1. **`base` ⇒ `11`**
2. **`value8` ⇒ `8`**
3. **`value9` 的存在位 ⇒ `1`**
4. **`value9` ⇒ `0` 或 `9`**
5. **挂载数 ⇒ `4`**（**`0..15`**）
6. **每个挂载 ⇒ `14`**
⇒ **⇒ 所以【最小 `11+8+1+4 = 24` 位，最大 `24 + 9 + 15×14 = 243` 位**】
```

**✅ ⭐⭐⭐ **"最小 24 位，最大 243 位"** —— 一个**可推导的范围**。

**⚠ 而"`attachmentAssetIndexes.size() >= (1u << AttachmentCountBits)` ⇒ 拒绝"**⇒ **`size` 最多 `15`**。

**⇒ 十层**：
```text
`1 << 4 = 16` ⇒ **`size >= 16` ⇒ 拒绝** ⇒ **`size <= 15`**
⇒ **⇒ 所以【那个 `4` 位字段【恰好【能表示【`0..15`**】
```

**✅ ⭐⭐ **"那个 4 位字段恰好能表示 0..15"** — 一个**精确的匹配**。

**⚠ 而 `ModularValue9Bits = 9` ⇒ `0..511`，而 `1 << 9 = 512`** ⇒ **`optionalValue9 >= 512` ⇒ 拒绝** ✓

**⚠ 而 `AttachmentIndexBits = 14`，而界是 **`>= (1 << 14) - 1`** ⇒ **最大 `16382`**（不是 `16383`）。

**⇒ 十层**：
```text
`1 << 14 = 16384` ⇒ **`>= 16383` ⇒ 拒绝** ⇒ **`<= 16382`**
⇒ **⇒ 所以【`16383` 【是【一个【保留值**】（**可能是 `0x3FFF` 一个哨兵**）
```

**✅ ⭐⭐⭐ **"`16383` 是一个保留值"** —— 与 §416 的 `2047`/`2046` **同族**（**第四次"一个上界【被【留作【一个哨兵**）。

**⇒ 三层**：
```text
§416  **`EntityNumNone = 2047` / `EntityNumWorld = 2046`**（**`11` 位的顶**）
§468  **`InlineFollows = 0xFFFFFFFF`**（**`32` 位的顶**）
§470  **`AttachmentIndex >= 16383` ⇒ 拒绝**（**`14` 位的顶**）
⇒ **⇒ 三次"一个【上界**被留作哨兵**】
```

**✅ ⭐⭐ **"一个上界被留作哨兵"三例表**。

## 七、**`%` 那条活体命令的"VERB 后是一个位对齐的载荷"**

### 7.1 那段

```cpp
// VERB then a BIT-ALIGNED payload. out.exe's dispatcher (sub_614AC0)
// consumes the leading byte and hands the reader (sub_612640) a cursor at
// byte 1, so the first bit written here is the first bit read there. The
// 'J'/'K' scoreboard patches prove this framing on the same channel.
message.MSG_WriteByte(WeaponConfigStringUpdateVerb);
// bit==1 selects the high updatable range (base 5960); the 11-bit field is
// then the index MINUS that base, which equals the weapon asset index.
message.MSG_WriteBits(1, 1);
message.MSG_WriteBits(weaponAssetIndex, WeaponIndexBits);
SV_WriteModularWeaponConfigStringValue(message, configString);
```

### 7.2 二十四层

```text
1. **`VERB` 一个字节**（`'%'` = `37`）**
2. ⇒ **⇒ 然后【一个【位对齐**的载荷**】
3. ⇒ **⇒ 因为【`out.exe` 的派发器 `sub_614AC0` 【吃掉【那个前导字节**】
4. ⇒ **⇒ 而【把【读器 `sub_612640` 【交给【一个【在字节 `1`** 的光标**】
5. ⇒ **⇒ 所以【这里【写的第一个位【就是【那里【读的第一个位**】
6. ⇒ **⇒ 而【`'J'`/`'K'` 记分板补丁【在【同一条通道上【证明**了这个框架**】
7. ⇒ **⇒ 然后【一个位 `1` ⇒ 选【高可更新区间**（基 `5960`）**
8. ⇒ **⇒ 然后【那个 `11` 位字段【是【索引【减那个基**】
9. ⇒ **⇒ 而【那【等于【那个武器资产索引**】
```

### 7.3 ⭐⭐⭐ **"这里写的第一个位就是那里读的第一个位"**

**✅ 与 §405 的"`sendRawCommand` 的显式通道字节"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§405  **`sendRawCommand` 【用【一个显式**的通道字节（**不用【首字节可打印性**判据）**
§470  **`%` 命令【用【一个显式**的动词字节（`37`）**
⇒ **⇒ 两次"一个【显式**的字节**
```

**✅ ⭐⭐⭐ **"两次显式的字节"**。

**⚠ 而"`WeaponConfigStringDynamicBase = 5960`【等于** `WeaponConfigStringBase`"**⇒ **"那就是为什么一个武器资产索引【直接**穿过那个 11 位字段**"**。**

**⇒ 十层**：
```text
`DynamicBase = 5960` 与 `ConfigStringBase = 5960` 【相同**】
⇒ **⇒ 所以【一个【绝对索引 `5960 + N` 的【相对值【就是 `N`**】
⇒ **⇒ 而【`N` 【就是【那个武器资产索引**】
⇒ **⇒ 所以【不需要【一个减法**】
```

**✅ ⭐⭐⭐ **"不需要一个减法，因为两个基恰好相同"** —— 一个**极精巧的巧合**（或**设计**）。

**⚠ 而"那个区间有两个**"（`bit==1` ⇒ 高区间，`bit==0` ⇒ 低区间**）**。

**⇒ 三层**：
```text
`bit == 1` ⇒ **高区间（基 `5960`）**
`bit == 0` ⇒ **低区间（基 `0`？）**
⇒ **⇒ 所以【那个位【选【两个**基**
```

**✅ ⭐⭐ **"那个位选两个基"** —— 而**这里【只用【高区间**（因为武器都在 `5960+`）。

## 八、**`SV_EncodePlayerName` 的"从『可打印』放宽到『无控制符』"**

### 8.1 那段

```cpp
// ★ 2026-10-07 15:0x -- 「可打印」放宽到「无控制符」：名字线编码 = GBK 字节
//   （`Lifetime丷` = `... 81 52`），0x7E 上限会把 CJK 名拒掉 ⇒ 名册校验/
//   connect 名比较全挂。base64 逐字节编码逻辑不变。
if (username.empty() || username.size() > 16 ||
    std::ranges::any_of(username, [](const unsigned char value) {
        return value < 0x20 || value == 0x7F;
    }))
    return std::nullopt;
```

### 8.2 二十层

```text
1. **旧的判据：可打印**（`0x20..0x7E`）**
2. ⇒ **⚠ 而【`0x7E` 的上限【会把【CJK 名【拒掉**】
3. ⇒ **⇒ 因为【名字线编码【是【GBK 字节**】
4. ⇒ **⇒ （`Lifetime丷` = `... 81 52`**）**
5. ⇒ **⇒ 所以【名册校验 / `connect` 名比较【全挂**】
6. ⇒ **⇒ 新的判据：无控制符**（`>= 0x20` 且 `!= 0x7F`）**
7. ⇒ **⇒ 而【base64 逐字节编码【逻辑不变**】
```

### 8.3 ⭐⭐⭐ **"`0x7E` 的上限会把 CJK 名拒掉，所以名册校验与 connect 名比较全挂"**

**✅ 与 §469 的"`name.size() > 15` ⇒ 拒绝"**——**一个对照**（那里是**表**的界，这里是**编码**的界）。

**⇒ 三层**：
```text
`sv_script_lua` 的 `15` ⇒ **表的步长**（**`20 - 4 - 1`**）
`sv_gamestate` 的 `16` ⇒ **一个名字的字节上限**
⇒ **⇒ 两个不同的界【各自【被【一个结构**决定**
```

**✅ ⭐⭐ **"两个不同的界各自被一个结构决定"**。

**⚠ 而 `0xFE` 的帧定界**：

```cpp
result.push_back(static_cast<char>(0xFE));
result.append(*encoded);
result.push_back(static_cast<char>(0xFE));
```

**⇒ 十层**：
```text
`0xFE` + base64 + `0xFE`
⇒ **⇒ 所以【一个【帧定界**的名字**
⇒ **⇒ 而 `0xFE` 【是一个【非 ASCII** 的定界符**
```

**✅ ⭐⭐⭐ **"一个帧定界的名字，用 `0xFE` 作定界符"** —— 与 §433 的"`\x14`/`\x15` 分隔符"**同族**（**第二次"一个非 ASCII 定界符**）。

**⇒ 三层**：
```text
§465  **`\x14` / `\x15`**（**提示规则的分隔**）
§470  **`0xFE`**（**玩家名的帧定界**）
⇒ **⇒ 两个【不同的非 ASCII** 定界符**
```

**✅ ⭐⭐ **"两个不同的非 ASCII 定界符"**。

**⚠ 而 `encoded.reserve((username.size() + 2) / 3 * 4)`**⇒ **一个**精确**的上界**。**

**⇒ 六层**：
```text
`n` 字节 ⇒ **`ceil(n/3) × 4`** 个 base64 字符**
而 `(n + 2) / 3 * 4` 【正是【那个 `ceil`**】
⇒ **⇒ 所以【那个 `+2` 【是【一个【整数**的向上取整**
```

**✅ ⭐⭐ **"那个 `+2` 是一个整数的向上取整"**。

**⚠ 而 `'='` 的填充**（`remaining <= 1` 或 `<= 2`）**⇒ 标准 base64** ✓

**⇒ 三层**：
```text
`remaining > 1 ? alphabet[...] : '='`
`remaining > 2 ? alphabet[...] : '='`
⇒ **⇒ 标准**的 `=` 填充**
```

**✅ ⭐⭐ **"标准的 `=` 填充"**。

## 九、**`SV_RegisterModularWeaponConfigString` 的"连续的动态索引"**

### 9.1 那段

```cpp
// CODDIFF(sv_send_client_gamestate): ol-mod allocates deterministic
// contiguous dynamic indexes because the removed CODOL backend/server
// registry is unavailable. Existing non-contiguous state fails closed.
...
std::size_t dynamicOffset{};
for (const auto &[index, _] : gameState.modularWeaponConfigStrings)
{
    const auto expectedIndex = static_cast<std::uint32_t>(
        WeaponConfigStringBase) + firstDynamicWeaponAssetIndex + dynamicOffset;
    if (index != expectedIndex)
        return std::nullopt;
    ++dynamicOffset;
}
```

### 9.2 二十四层

```text
1. **ol-mod 【分配【确定性的【连续的**动态索引**】
2. ⇒ **⇒ 因为【被移除的 CODOL 后端/服务器注册表【不可用**】
3. ⇒ **⇒ 所以【一个【已有的【不连续**状态【fail closed**】
4. ⇒ **⇒ 而那个循环【检查【每一个**已有项【是否【在【它的预期位置**】
```

### 9.3 ⭐⭐⭐ **"已有的不连续状态 fail closed，而不是被重新编号"**

**✅ 与 §467 的"一个不可解决的矛盾 ⇒ 拒绝"**——**同族**（**第十二次"全或无）。

**⇒ 三层**：
```text
重新编号 ⇒ **旧客户端【的索引【失效**】
fail closed ⇒ **一个【明确的**错误**
⇒ **⇒ 所以【fail closed 是【唯一**的正确选择**
```

**✅ ⭐⭐⭐ **"fail closed 是唯一正确的选择"**。

**⚠ 而"若【同一个 `configString` 已存在**】**⇒ 返回**它**（**但只在【它 ≥ `firstDynamic`** 时**）**。

**⇒ 十层**：
```text
`existing == configString` ⇒ **找到**一个相同的**
⇒ **⇒ 若【它的索引 `>= firstDynamic`**⇒ **返回**它** ✓
⇒ **⇒ 否则 `nullopt`**（**它在【动态区【之外**）
```

**✅ ⭐⭐ **"它在动态区之外 ⇒ 拒绝"** —— 一个**精确的区间**检查**。

**✅ 与 §469 的"`5` 个 `WeaponClasses` 值缺 `2`/`4`"**——**不同**（那是一个**覆盖**的缺口，这是一个**区间**的检查）。

## 十、**`SV_PopulateRequiredConfigStrings` 的"重建所有派生的字符串"**

```cpp
// OLMOD(gamestate-required-projection): rebuild all derived strings
// from authoritative source fields so stale identities/rules cannot
// survive into a newly constructed gamestate.
```

### 10.1 二十四层

```text
1. **从【权威源字段**重建**所有【派生**的字符串**
2. ⇒ **⇒ 所以【一个【陈旧的**身份/规则【不能【存活**进【一个新构造的 gamestate**】
3. ⇒ **⇒ 而【名字区【先【全删**（`erase`）再【重写**】
```

### 10.2 ⭐⭐⭐ **"先全删再重写，所以一个陈旧的身份不能存活"**

**✅ 与 §426 的"进入世界的客户端刚刚把它的快照状态扔掉了"**——**同族**（**第三次"先清再建**）。

**⇒ 三层**：
```text
§426  **`slot->snapshotHistory = {}`**（**一个结构**的清除**）
§437  **`commitSessionRoster` 的 ADOPT vs WIPE**
§470  **名字区【先 `erase` 全部** 再重写**
⇒ **⇒ 三次"先清**再建**】
```

**✅ ⭐⭐⭐ **"先清再建"三例表**。

**⚠ 而 `MatchEndTimeConfigStringIndex = 15` 的 `0` 语义**：

```cpp
// CODREF(sv_send_client_gamestate): the HUD countdown reads
// configstring 15 as an absolute match END time in server-time ms and
// displays (end - serverTime) / 1000. A zero time limit means "no
// limit", and the clock must then be absent rather than expired.
if (gameState.uiGameRules->timeLimitMinutes) { ...insert... }
else { gameState.configStrings.erase(MatchEndTimeConfigStringIndex); ... }
```

**⇒ 十层**：
```text
1. **`cs 15` ⇒ 一个【绝对的比赛结束时间**（`server-time ms`）**
2. ⇒ **⇒ 而客户端显示 `(end - serverTime) / 1000`**】
3. ⇒ **⇒ 而【`timeLimitMinutes == 0` ⇒ "没有限制"**】
4. ⇒ **⇒ 所以【那个时钟【必须【缺席**而不是【过期**】
```

**✅ ⭐⭐⭐ **"必须缺席而不是过期"** —— 与 §467 的"一个空的台座不是错的台座"**完全同族**（**第五次"缺席优于错误**）。

**⇒ 三层**：
```text
若【写 `0`**】⇒ **`(0 - serverTime) / 1000` 【是一个【巨大的负数**】⇒ **时钟【显示【一个荒谬的**值**
若【缺席**】⇒ **客户端【不显示**时钟**
⇒ **⇒ 所以【缺席**正确**
```

**✅ ⭐⭐⭐ **"写 0 会让时钟显示一个荒谬的值"** —— 一个**极精确的算术**。

**⚠ 而"`matchEndTime = matchStartServerTime + timeLimitMinutes × 60 × 1000`"**⇒ **`uint64`** 的乘法**。

**⇒ 三层**：
```text
`timeLimitMinutes` 是【一个整数**】
`× 60000` ⇒ **最大【几分钟到几小时**】
⇒ **⇒ 而 `uint64` 【保证【不会溢出**】
```

**✅ ⭐⭐ **"`uint64` 保证不会溢出"**。

**⚠ 而 `PREM|cs15 endTime=...` 的日志**⇒ **一个**取证**的行**。

**⇒ 三层**：
```text
`PREM|cs15 endTime=<n> start=<n> limitMin=<n>`（**存在**）
`PREM|cs15 ABSENT (uiGameRules.timeLimitMinutes=0)`（**缺席**）
⇒ **⇒ 两个分支【各自【有一行**】
```

**✅ ⭐⭐⭐ **"两个分支各自有一行"** —— 与 §469 的"`ZMTICK Lua callbacks=N`"**同族**（**第四次"一个有界的诊断**）。

## 十一、**`SV_PerfBaseline` 的"一次性的环境变量快照"**

```cpp
bool SV_PerfBaseline()
{
    static const bool baseline = [] {
        std::size_t length{};
        char value[8]{};
        return getenv_s(&length, value, sizeof(value), "OLMOD_PERF_BASELINE") == 0 &&
            length > 0 && value[0] == '1';
    }();
    return baseline;
}
```

**⇒ 十层**：
```text
1. **`static const` ⇒ 【只算【一次**】
2. ⇒ **⇒ 所以【一个【启动后【改的环境变量【不影响**它**
3. ⇒ **⇒ 而【`char value[8]` 与 `sizeof(value)`**⇒ **一个【有界**的读**
4. ⇒ **⇒ 而【`value[0] == '1'` ⇒ 只认 `"1"` 开头**
```

**✅ ⭐⭐⭐ **"一个启动后改的环境变量不影响它"** —— 一个**正确的一次性快照**。

**✅ 与 §469 的"`static std::vector<unique_ptr<...>> published`"**——**同族**（**第四次的 `static` 一次性**）。

**⇒ 三层**：
```text
§468  **`static std::vector<std::unique_ptr<...>> published`**（**永不释放**）
§469  **`static const bool baseline`**（**一次性的环境读**）
⇒ **⇒ 两次 `static` 的一次性**
```

**✅ ⭐⭐ **"两次 static 的一次性"**。

**⚠ 而"`SV_PerfBaseline()` ⇒ 跳过【那六条 vision**"**。**

**⇒ 三层**：
```text
若【`baseline`**】⇒ **vision 六条【不下发**】
⇒ **⇒ 所以【那是一个【性能基线**的模式**】
```

**✅ ⭐⭐ **"一个性能基线的模式"**。

## 十二、关键结论

1. **⭐⭐⭐ "如果你改这个字符串，你必须**在同一个提交里**重新生成 `SvGameStateFixtureBytes`：`bind()` 每次启动重推这个写者的输出并与那个数组比较，一个不匹配失败 `stage=message_bindings`，插件在**两边**都起不来，而客户端报告 **"your level file differs from the server's"** —— 那看起来完全不像一个 `serverinfo` 的问题，而它**已经花掉三次独立的调试会话**"`** —— 第三次"一个误导性的症状"（与 §467/§468 同族），而**病因是 `checksumFeed` 确实在 gamestate 里**。
2. **⭐⭐⭐ 零售的 `serverinfo` 十条键**（`\2482\24` / `\2485\4` / `\2490\214` / `\2491\0` / `\3056\2` / `\g_gametype\<gt>` / `\g_hardcore\0` / `\mapname\<map>` / `\scr_game_allowkillcam\1` / `\scr_team_fftype\0`）—— **"五个数字在前，因为 serverinfo 按键排序"`**；而 `sub_515340` **读 `mapname`、`g_gametype`、`atoi("2482")`、调 `sub_514E70`、再 `atoi("g_hardcore")`** ⇒ **"两个它读的键是我们曾经省略的，所以它们解析成 `atoi("") == 0` 而零售得到 `24`"`**。
3. **⭐⭐⭐ `scr_game_allowkillcam` 的完整病历**：**宣告 `1` 而 `killCamRecordingAvailable = false`（走 2697 的 cancel 分支）⇒ 客户端按"有回放"自行切镜头 ⇒ 【画面空白 + 死亡 UI 被拿掉 + 镜头停在击杀者身上】**；反转后 ⇒ **"有 UI、但 killcam 不播"`** ⇒ **"那个宣告是两个能力标志（`killCamRecordingAvailable` / `killcamPlaybackImplemented`）的函数"`**。
4. **⭐⭐⭐ 三个 dvar 撤回的运营结论**：`sv_botDifficulty`/`sv_botFov`/`codol_botNaturalStance` 一上线就伴随 **"名字异常 + 全解锁失效 + 存档被重置"**，回滚 V1.217 后名字立刻正常 ⇒ **"根因落在『往 gamestate 里塞客户端可见下发内容』这条线上，在查清之前不再下发任何新 dvar"`**。
5. **⭐⭐⭐ 一个真实的编译陷阱**：`result += "\\ui_ac130usetime\\40";` 注释掉的那行旁边写着 **"只写字符串字面量是无副作用表达式，编译器会直接丢弃（本刀第一次构建产物里 `ui_ac130usetime` 计数为 0，就是这个原因）"`**。
6. **⭐⭐⭐ 三个宽度都是必然**：**`7058 → 12761` ⇒ `13 → 14` 位**（`2^13 = 8192` 恰好在两者之间）；**`900 → 1700` ⇒ `10 → 11` 位**（`2^10 = 1024` 同样）；**独立验证 `0x31D9 = 12761` ✓**。
7. **⭐⭐⭐ "`> 0x3FF`（3.3.3.3 的十位界）曾写在**九处**，改正其中一处让其余八处仍然拒绝一个真实类会产生的那批武器——活跃的 gamestate 报告 `firstDynamicWeapon = 1224`，所以每个模块化武器都在 `1023` 之上"`** ⇒ **"这个项目已经为同一个『一个结构、多个文件』的错误付过三次（`bind()` 的 fixture / 每个武器的挂载数 / 这个）"`** ⇒ **"定义一次，从它实际来自的那个块大小推导"`**，并由 `static_assert(MaximumWeaponAssetIndex < (1u << 11))` 在编译期兜住。
8. **⭐⭐⭐ `WeaponCountConfigStringIndex` 的 `6800 → 12246 (+5446)`，而"不是一个全局投票提议的 `+608`"，因为 `7408` 会落在武器块本身里面**（独立验证：`5960 ≤ 7408 < 7660` ✓）；证据是 **`sub_590A60` 读 `byte_77DB226`，而那个地址减 `byte_77D8250` 恰是 `0x2FD6 = 12246`**（独立验证 ✓）。
9. **⭐⭐⭐ "两张表的计数宽度不同，而 3.3.3.3 看不出来——那里四个字段都是十位，所以一个共享的 `WeaponIndexBits` 与四个常量不可区分；这里简单表的计数仍是十位（`0x472E8C`）而模块化表的是十一位（`0x472F99`）"`** —— 一个**退化情形掩盖一个结构**（与 §468 的 `semantic` 同族）。
10. **⭐⭐⭐ `SV_ValidateGameState` 的十四组不变量**，其中最精确的两条：**④ `serverInfo` 存在且等于 `formatServerInfo(gameState)`（逐字节重推）** 与 **⑬ 武器块（`5960..7659`）的项**不能**出现在 `configStrings` 里**（"它们走两张独立的表"）⇒ **与 §469 的 `simple`/`modular` 互斥构成三层**。
11. **⭐⭐⭐ 武器表的位流是一个差分编码**（"是否与上一项连续"一个位，否则 14 位绝对索引，`previous = -1` 使 index `0` 计为连续）⇒ **"一个连续的族只花一个位每个"`**，独立算得 **`1700` 个全连续省 `23800` 位 = `2975` 字节**；而配置串表用**同一个把戏**。
12. **⭐⭐ 模块化值的位布局**：`base 11 + value8 8 + 存在位 1 + [value9 9] + 挂载数 4 + 每个挂载 14` ⇒ **"最小 24 位，最大 `24 + 9 + 15×14 = 243` 位"`**；而 **`AttachmentIndexBits = 14` 的界是 `>= (1<<14)-1` ⇒ 最大 `16382`，"`16383` 是一个保留值"`** —— 第三次"一个上界被留作哨兵"（与 §416 的 `2047`/`2046`、§468 的 `0xFFFFFFFF` 同族）。
13. **⭐⭐⭐ `%`（`37`）那条活体命令的"VERB 后是一个位对齐的载荷"**：`sub_614AC0` 吃掉前导字节、把 `sub_612640` 交给**字节 1** 的光标 ⇒ **"这里写的第一个位就是那里读的第一个位"`**，而 `'J'`/`'K'` 记分板补丁在同一条通道上证明了这个框架；**`WeaponConfigStringDynamicBase = 5960` 恰等于 `WeaponConfigStringBase` ⇒ "不需要一个减法"`**。
14. **⭐⭐⭐ `SV_EncodePlayerName` 的"从『可打印』放宽到『无控制符』"**：**`0x7E` 的上限会把 CJK 名拒掉（`Lifetime丷` = `... 81 52`）⇒ 名册校验与 connect 名比较全挂`**；而**帧定界 `0xFE` + base64 + `0xFE`**（第二次"一个非 ASCII 定界符"，与 §465 的 `\x14`/`\x15` 同族）；`reserve((n+2)/3*4)` 是**整数向上取整**。
15. **⭐⭐⭐ `SV_RegisterModularWeaponConfigString` 的"连续的动态索引"** ⇒ **"一个已有的不连续状态 fail closed，而不是被重新编号"`** —— 第十二次"全或无"；而重用一个已存在的相同 `configString` **只在它的索引 `>= firstDynamicWeaponAssetIndex` 时**，否则 `nullopt`。
16. **⭐⭐⭐ `SV_PopulateRequiredConfigStrings` 的"从权威源字段重建所有派生的字符串，所以一个陈旧的身份/规则不能存活进一个新构造的 gamestate"`**，而名字区**先全 `erase` 再重写** ⇒ 第三次"先清再建"（与 §426/§437 同族）。
17. **⭐⭐⭐ `cs 15` 的"`timeLimitMinutes == 0` ⇒ 时钟**必须缺席而不是过期**"**：因为客户端显示 `(end - serverTime) / 1000`，写 `0` 会显示**一个巨大的负数** ⇒ **"写 0 会让时钟显示一个荒谬的值"`** —— 第五次"缺席优于错误"（与 §467 的"一个空的台座不是错的台座"同族）；两个分支**各自有一行 `PREM|cs15 ...`** 取证日志。
18. **⭐ 一个可质疑的冗余**：`configStrings.size() > INT16_MAX` 恒真（因为每个 index `< 12761` 唯一）⇒ **"那个 `INT16_MAX` 不是从写者推导的"`**（写者用 `MSG_WriteShort`，真正的界是 `65535`）。
19. **⭐⭐ `SV_PerfBaseline` 的 `static const bool`** ⇒ **"一个启动后改的环境变量不影响它"`** —— 一个正确的一次性快照，而 `baseline` 时**六条 vision 不下发**。

## 十三、`sv_gamestate_mp` 全文件总览

**`.cpp`：`1,045` 行。`.hpp`：`727` 行。**

**`28` 个函数**（`.cpp`）：
```text
 20 SV_RegisterDynamicServerMaterials
 63 SV_EffectConfigStringToEventParameter     78 SV_EffectEventParameterToConfigString
116 validWeaponConfigStringIndex             122 highestWeaponAssetIndex
139 populateWeaponCountConfigString          150 parseMapCenter
177 parseUnsignedToken                       198 formatFloat
208 formatMiniMap                            231 formatServerInfo
306 formatSystemInfo                         319 writeWeaponConfigStringTable
348 SV_FormatPlayerNameConfigString          362 SV_EncodePlayerName
404 SV_PerfBaseline                          415 SV_PopulateRequiredConfigStrings
553 SV_SetMapCenterConfigString              566 SV_SetMiniMapConfigStrings
589 SV_AddSimpleWeaponConfigString           613 SV_AddModularWeaponConfigString
649 SV_ParseModularWeaponConfigString        689 SV_RegisterModularWeaponConfigString
737 SV_ValidateGameState                     931 SV_WriteWeaponConfigStrings
956 SV_WriteModularWeaponConfigStringValue   980 SV_WriteWeaponConfigStringUpdateCommand
997 SV_WriteGameState
```

**配置串带表**（`.hpp`）：
```text
    0  serverinfo                 1  systeminfo              2  gamename ("cod")
   13  fog                       15  match end time         16  map center
   23  match winner             463  ui_scorelimit         464  ui_timelimit
  465  ui_halftime              479  match end ui           792  objective marker
  856..951  hint strings (96)   1413  obituary
 2452..2469 player names (18)  2554  north yaw            2555  minimap
 2557  vision naked            2558  vision night         2559  vision missilecam
 2560  vision thermal          2561  vision pain          2562  vision overlay
 2568..3591 model (1024)      3624  sound aliases (512)  4136..4535 effect (400)
 4808..4871 script menus (64) 4872..5895 server materials (1024)
 5960..7659 weapons (1700)    7669..11764 anims (4096)
11861  timescale            12246  weapon count
```

**`MaxConfigStrings = 0x31D9 = 12761`**。

**`3` 个 `static_assert` 级保证**：`MaximumWeaponAssetIndex < (1u << 11)`；`MaxConfigStrings` 与 `ConfigStringIndexBits` 的 `14`；`SvGameStateFixtureBytes` 的 `280` 字节与 `512` 字节的 `bind()` 缓冲区（"`256` 在 `280` 处溢出"）。

**`13` 个 RVA / 反汇编锚点**：
```text
0x46DB20  CL_ParseGameStateMessage（A 端）
0x472D80  那个消费者（C 端）
0x472E8C  简单武器表的计数宽度（10 位）
0x472F99  模块化武器表的计数宽度（11 位）
0x472C70  模块化武器值的读器
sub_515340 客户端的 gamestate 解析
sub_514E70 模式分类器
sub_590A60 武器计数配置串的消费者（byte_77DB226）
byte_77D8250 configstring 类表
sub_614AC0 二进制命令派发器（case 0 = 配置串更新）
sub_612640 那个读器
CL_SetConfigString
0x0046CE80 vision 的即时设置器
```

**`1` 个黄金向量**：`SvGameStateFixtureBytes[280]`，**"对上一个 fixture 共享一个 `27` 字节的相同前缀与一个 `129` 字节的相同后缀，而唯一不同的区域是 serverinfo 的值本身"`** ⇒ **独立验证：`280 - 27 - 129 = 124` 字节的 serverinfo 值**。

## 十四、`SvGameStateFixtureBytes` 的逐字节核对（本轮实地解码）

我把那 `280` 个字节抄出来跑了三遍解码器，**已经核实到的部分**：

```text
[0]        0x03                  ServerCommandGameState
[1..4]     00 00 00 00           long reliableSequence = 0
[5..13]    "mp_crash" 00         WriteString mapName
[14..17]   "tdm" 00              WriteString gameType
[18..21]   00 00 00 00           long configStringChecksum = 0
[22]       0x04                  ServerCommandConfigString
[23..24]   0A 00                 short count = 10
...        10 条配置串（见下）...
[274]      0x05                  ServerCommandEof
[275..278] 00 00 00 00           **只有 4 个零**
[279]      0x05                  ServerCommandEof
```

**`10` 条配置串的实际内容**（按出现顺序，逐字节读出）：

```text
0  \2482\24\2485\4\2490\214\2491\0\3056\2\g_gametype\tdm
   \g_hardcore\0\mapname\mp_crash\scr_game_allowkillcam\1\scr_team_fftype\0
1  cod
2  0 0 0
3  "mp_crash" 0
4  "default_night_mp" 0
5  "thermal_mp" 0
6  "thermal_mp" 0          ← 前面多一个 0x57
7  "mp_crash" 0
8  "mp_crash" 0
9  0 0 1 1                 ← 前面多一个 0xE5 0x02
```

**三条新的确认**：

1. **`serverinfo` 是【十条键**】，与 `formatServerInfo` 的字面量**逐字节一致**（`\2482\24` … `\scr_team_fftype\0`）⇒ **"那个黄金向量确实对应一个 `uiGameRules` 为空的 gamestate"** 得到证实（否则会有 `ui_scorelimit` 一族）。
2. **`10` 条里没有 index `2554`（north yaw）也没有 `2555`（minimap）** ⇒ **那个 fixture 的 gamestate 没有迷你地图**（`SV_SetMiniMapConfigStrings` 从未被调用），这正是 §470 五 第 ⑨ 组不变量 `northYaw.has_value() == miniMap.has_value() == (cs 存在)` 的**两边都为空**那一侧。
3. **`vision naked` 的 `0xFD 0xC9` 按 14 位小端解出恰好 `2557`**（`0xFD | ((0xC9 & 0x3F) << 8)` = `0xFD + 0x900` = `2557`）⇒ **那个 `14` 位索引宽度在现场字节上是可证实的**，不是只从 `MaxConfigStrings` 推出来的。

**未解出的部分**（诚实标注）：每条配置串**前面**那个"是否连续"位与 `MSG_WriteString` 的字符区之间的**边界**我没能对上（`0x57` / `0xE5 0x02` 这类前缀字节的位分配不符合"先 1 位 seq 再 14 位 index"的直读）。这不影响上面三条结论 —— 它们各自只依赖**命令字节、计数、字符串内容与那一条 2557**。

## 十五、未闭合点

- `SvGameStateFixtureBytes` 里"seq 位 / index 位 / 字符串起始"三者的精确边界（见上）。
- `0x57`（在第四条 vision 之前）与 `0xE5 0x02`（在 `0 0 1 1` 之前）的位语义。
- `_c` / `2708` / `28370` 等刀号与 `findings` 的对应。
- `MaximumServerCollisionEntityNum` 的确切值。
- 下一个文件：`sv_bullet_mp.cpp`（`49,355` 字节）。
