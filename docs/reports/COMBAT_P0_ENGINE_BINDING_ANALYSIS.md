# COMBAT_P0_ENGINE_BINDING_ANALYSIS — 引擎绑定失败路径、数据来源与最小诊断方案

**任务**：COMBAT-P0 — 定位并解决战斗服务器引擎绑定阻塞（阶段一：只读调查与测试设计）
**日期**：2026-10-11
**工作树**：**F** = 活动基准；**D** = 冻结副本。**本轮实测：`EngineBindings.cpp`（871,806 B / SHA-256 `E624A8A1AFF2BB59F57CCD1D37BF1FD609D0573FFD505DB5BD6CD32C3E07465B`）与 `EngineBindings.hpp`（126,514 B / `9ACE87313419DB58DC41EE6F4F38612A0970525BAF24CBF924462AD1BA88C72E`）在 F 与 D **逐字节相同**。** `ClientProcessPatches.cpp` 亦相同。仅 `Appmain.cpp` 与 `FrameHook.cpp` 两树不同（F 较新）。
**执行边界**：只读。未启动/附加/注入/暂停/终止/重启任何进程；未做运行时实验；未读/改客户端进程内存；未启用尺寸容差；未删除或绕过门禁；未改 RVA/ABI/协议常量；未改启动器/TCLS/Ayria/大厅链；未构建/部署；未提交/推送/重置/清理。
**配套**：`COMBAT_P0_FAILURE_PATHS.json`（机器可读失败路径与守卫表）、`COMBAT_P0_VALIDATION_PLAN.md`、`COMBAT_P0_SHA256_MANIFEST.txt`。

> **本文件的唯一判据**：定位"当前服务器初始化的第一个实际阻塞点"。**不把门禁变绿、端口监听或工具运行成功当作成果。**

---

## 0. 结论速览

| # | 问题 | 结论 |
|---|---|---|
| 1 | `bind()` 有多少失败返回路径？ | **9 处 `return false`** + 1 处成功返回；其中**3 处静默**（无日志），6 处写日志。另在 4 个位置的**子分支**（`TimeDateStamp`/`SizeOfImage`/`NT 签名`；3+6 具名守卫成员）无法从日志区分。 |
| 2 | `TimeDateStamp` 与 `SizeOfImage` 是否同一条件分支？ | **是。** 二者与 `nt->Signature` 一起位于 `EngineBindings.cpp:3662-3664` 的**同一个 `if`**，短路 `||`，**不记录是哪一项失败**。 |
| 3 | 82 条守卫在门禁之后的执行顺序？ | 门禁 → 3 具名（native entity）→ 6 具名（player DObj）→ **66 条未具名 `||` 链**（源码顺序）→ 指针赋值 → runtime_slots → message_bindings → glass_bridge → commit。**`bind()` 内实际守卫 = 75 = 9 具名 + 66 链**。"82"是文件内 `std::equal(` 总出现次数（含 7 处非 `bind()` 守卫）。 |
| 4 | 三次相同日志能否确定失败分支？ | **不能。** 只能把范围限定到"3 个静默早退点之一"。其余一切（含全部 75 条守卫、runtime_slots/message/glass）都会在**同一日志文件**留下痕迹，而它们没有出现。 |
| 5 | 绑定数据来源是否可追溯？ | **是，且已逐项落到提交。** 宿主门禁与 `ComFrameRva` 引入于 `d4c6f0a`（2026-07-31，3.3.3.3 值）；`55fcdbf`（2026-08-18）整体翻转到 `out.exe`/1649370。 |
| 6 | 战斗创建入口是否已定位？ | **未定位。** `Createserver` 不是入口（返回 `nullptr`）；已确认的只有"插件加载 → 初始化 → 门禁 → 帧钩子 → 控制面 → 会话"链；原版"战斗/会话创建"函数为 UNKNOWN。 |
| 7 | 第一个实际阻塞点是什么？ | **`EngineBindings::bind()` 的宿主映像身份门禁**，具体是 `3656 / 3660 / 3662-3666` 三处静默早退之一；**精确分支在现有证据下不可判定**（见 §1.5）。 |

---

## 1. 任务 A：引擎绑定的真实失败路径

### 1.1 失败路径总表（要求格式）

> 行号以 **F 树**为准（F/D 对 `EngineBindings.cpp` 相同）。`bind()` 范围 = **`EngineBindings.cpp:3647-4216`**；`valid()` 在 `4218` 起。

| 失败路径 ID | 源码位置 | 判断条件 | 日志行为 | 返回结果 | 被阻断的后续步骤 |
|---|---|---|---|---|---|
| **P0-01** | `3654-3656` | `module_ = GetModuleHandleW(nullptr)` 为 null ⇒ `!module_` | **静默（无日志）** | `false` | 全部（P0-02…P0-11、指针赋值、commit）、`installFrameHook`、`Com_Frame` hook、`onServerFrame`、`NET_Frame`、28960 监听、DTLS 会话、gamestate/snapshot、对局 |
| **P0-02** | `3658-3660` | `dos->e_magic != IMAGE_DOS_SIGNATURE` | **静默（无日志）** | `false` | 同上 |
| **P0-03/04/05** | `3661-3667` | **单个 `if`**，`nt->Signature != IMAGE_NT_SIGNATURE` **OR** `nt->FileHeader.TimeDateStamp != ExpectedTimestamp` **OR** `nt->OptionalHeader.SizeOfImage != ExpectedImageSize` | **静默（无日志）**；**不记录实际值，也不记录是哪一项** | `false` | 同上 |
| **P0-06** | `3669-3693` | 3 条具名前缀守卫（`SVLinkEntity` / `SVUnlinkEntity` / `SV_Trace`），`||` 链内**首个失败者具名** | **写日志**：`RuntimeLog::Channel::GameServer`，`native entity binding prefix mismatch function=<name>`（`3688-3691`） | `false` | P0-07…P0-11、指针赋值、`installFrameHook` 及其后全部 |
| **P0-07** | `3695-3742` | 6 条具名前缀守卫（`native lerp-frame accessor initializer` / `BG_PlayerAnimation` / `BG_UpdatePlayerDObj` / `DObjFree` / `Com_ServerDObjCreate` / `Com_GetServerDObj`），链内首个失败者具名 | **写日志**：同通道，`player DObj binding prefix mismatch function=<name>`（`3737-3740`） | `false` | P0-08…P0-11 及之后全部 |
| **P0-08** | `3744-4023` | **66 条未具名 `||` 链**（`std::equal`），整条链只产生**一条**日志 | **写日志**：同通道，`engine binding validation failed stage=function_prefixes`（`4019-4021`）；**不指出是哪一条守卫** | `false` | P0-09…P0-11 及之后全部 |
| **P0-09** | `4144-4155` | runtime slot: `!writableBytes(pmoveTraceHandlerSlot_, sizeof(Trace)*2)` 或 `pmoveTraceHandlerSlot_[0] != clientPmoveTrace_` 或 `[1] != nullptr` 或 `!writableBytes(animConditionBasePointer_)` 或 `!writableBytes(animScriptDataPointer_)` 或 `!writableBytes(mantleAnims_, sizeof(void*)*2)` | **写日志**：同通道，`engine binding validation failed stage=runtime_slots`（`4151-4153`） | `false` | P0-10、P0-11、commit 及之后全部 |
| **P0-10** | `4199-4205` | `!validateMessageBindings()`（`EngineBindings.cpp:17911`） | **写日志**：同通道，`engine binding validation failed stage=message_bindings`（`4201-4203`） | `false` | P0-11、commit 及之后全部 |
| **P0-11** | `4206-4212` | `!installBrushTraceGlassBridge(module_)` | **写日志**：同通道，`engine binding validation failed stage=glass_bridge`（`4208-4210`） | `false` | commit（`bindingCommitted_.store(true)`）及之后全部 |
| — | `4214-4215` | 全部通过 | 无 | **`true`**，并 `bindingCommitted_.store(true)`（`4214`） | — |

**"被阻断的后续步骤"的完整后缀（贯穿 P0-01…P0-11）**：
`installFrameHook(Bindings, onServerFrame)`（`Appmain.cpp:8128`）→ 前置 `bindings.valid()`（`FrameHook.cpp:63`，失败写 `frame hook install rejected op=installFrameHook reason=invalid-bindings`）→ 在 `module_ + 0x0FEA20` 写 `0xE9` 相对跳转 → `Com_Frame` 每帧调用 `comFrameHook` → `runServerFrame` → `onServerFrame`（`Appmain.cpp:6437`）→ `ensureDedicatedControlServer()` / `processDedicatedControlMessages()` → `Network.NET_Frame`（`:6633`）→ 后端 `ConfigureSession` → `Network.start()` → `bind(0.0.0.0:28960)` → DTLS 会话 → gamestate/snapshot → 客户端进图 → 对局。

### 1.2 每个失败路径的日志通道（同一通道的证据）

- `bind()` 的 3 处具名 + 3 处阶段日志全部使用 **`OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, …)`**。
- 通道→文件映射（`src/shared/RuntimeLog.cpp`）：`:60` 通道名 `"game-server"`（`Channel::Backend` 才是 `"backend"`）；`:77` 文件名 `L"CodolGameServer.log"`；前缀形如 `[<role>/<channel>]`（`roleName()`：`client` / `dedicated` / 默认 `combined`）。
- `Appmain.cpp:7135` 的 `logGameServer("engine binding failed")` 走**同一个**通道与文件。
⇒ **结论**：`bind()` 的任何**非静默**失败都会与 `engine binding failed` 出现在**同一个日志文件的同一批次**里。

### 1.3 `TimeDateStamp` 与 `SizeOfImage` 是否同一分支

**是。**（`EngineBindings.cpp:3662-3664`）

```cpp
const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(module_ + dos->e_lfanew);
if (nt->Signature != IMAGE_NT_SIGNATURE ||
    nt->FileHeader.TimeDateStamp != ExpectedTimestamp ||
    nt->OptionalHeader.SizeOfImage != ExpectedImageSize)
{
    return false;
}
```

三个条件短路求值于**一个 `if`**；`return false` 在 `3666`。**代码不写日志、不记录 effective/expected、不记录哪一项不符。**
常量：`ExpectedTimestamp = 0x6096930A`（`EngineBindings.hpp:438`）、`ExpectedImageSize = 0x0E5D6000`（`:439`）、`ComFrameRva = 0x0FEA20`（`:440`）。

### 1.4 82 条守卫在门禁之后的执行顺序

门禁（`3647-3667`）之后，守卫按以下顺序执行（源码顺序 = `||` 短路顺序）：

1. **P0-06** `3669-3693`：3 条具名（`SV_LinkEntity` → `SV_UnlinkEntity` → `SV_Trace`）。
2. **P0-07** `3695-3742`：6 条具名（`native lerp-frame accessor initializer` → `BG_PlayerAnimation` → `BG_UpdatePlayerDObj` → `DObjFree` → `Com_ServerDObjCreate` → `Com_GetServerDObj`）。
3. **P0-08** `3744-4023`：**66 条未具名 `||` 链**，顺序如下（`index 名称 @ RVA`）：
   1 `ComFramePrefix` @0x0FEA20 · 2 `DBFindXAssetHeaderPrefix` @0x09CF30 · 3 `DBIsXAssetDefaultPrefix` @0x09D3D0 · 4 `DBLinkXAssetEntryPrefix` @0x09DA10 · 5 `MsgInitPrefix` @0x26E720 · 6 `MsgWriteBitsPrefix` @0x26E840 · 7 `MsgWriteStringPrefix` @0x26EA90 · 8 `LevelZoneLoadPrefix` @0x09E600 · 9 `CollisionMapLoadPrefix` @0x262D90 · 10 `CollisionWorldLinkPrefix` @0x269A40 · 11 `CCSClearPrefix` @0x261610 · 12 `CCSInitializePrefix` @0x261A30 · 13 `CCSGetConstantStringPrefix` @0x261C50 · 14 `TracePrefix` @0x06EA60 · 15 `WorldTracePrefix` @0x268220 · 16 `TransformedBrushModelTracePrefix` @0x268470 · 17 `TransformedCapsuleTracePrefix` @0x268560 · 18 `CalcTraceExtentsPrefix` @0x269460 · 19 `PointTraceToEntitiesPrefix` @0x06E6D0 · 20 `DObjGeomTracelinePartBitsPrefix` @0x3831C0 · 21 `DObjContentsTracelinePartBitsPrefix` @0x383360 · 22 `DObjTracelinePrefix` @0x3825F0 · 23 `DObjContentsTracelinePrefix` @0x383290 · 24 `PointTraceStaticModelsPrefix` @0x26A3D0 · 25 `DObjCalcSkelPrefix` @0x3847A0 · 26 `BGGetPlayerEyePositionPrefix` @0x0123B0 · 27 `BulletEndposPrefix` @0x192230 · **28 `ByteDirectionsPrefix` @0xA51C70（12 字节 DATA 常量，非代码）** · 29 `ViewMovementDamageKickPrefix` @0x0353E0 · 30 `ViewMovementIdleAnglesPrefix` @0x0355D0 · 31 `ViewMovementBobAnglesPrefix` @0x035770 · 32 `ViewMovementAdsBobPrefix` @0x035910 · 33 `WeaponMovementBasePrefix` @0x034520 · 34 `WeaponMovementSwayPrefix` @0x034680 · 35 `WeaponMovementRecoilPrefix` @0x034C20 · 36 `WeaponMovementBobPrefix` @0x034E20 · 37 `SetWeaponMovementAnglesPrefix` @0x034F90 · 38 `AnglesToQuaternionPrefix` @0x3853E0 · 39 `AngleVectorsPrefix` @0x367890 · 40 `MatrixMultiplyPrefix` @0x3653E0 · 41 `AxisToAnglesPrefix` @0x3667B0 · 42 `PmoveSinglePrefix` @0x01CB40 · 43 `PMSetPitchValuesPrefix` @0x01DB40 · 44 `PlayerStateToEntityStatePrefix` @0x0116F0 · 45 `BGAnimScriptEventPrefix` @0x007E10 · 46 `BGFindAnimsPrefix` @0x004D80 · 47 `BGAnimParseAnimScriptPrefix` @0x007530 · 48 `BGLoadAnimTreesPrefix` @0x00B130 · 49 `ScrCreateObjectPrefix` @0x34CED0 · 50 `ScrPrecacheAnimTreesPrefix` @0x34AF50 · 51 `BGFindAnimTreesPrefix` @0x00B210 · 52 `BGFinalizePlayerAnimsPrefix` @0x004FE0 · 53 `MantleCreateAnimsPrefix` @0x00CCA0 · 54 `HunkAllocXAnimPrefix` @0x368220 · 55 `WeaponLookupPrefix` @0x02F2F0 · 56 `WeaponResolverPrefix` @0x02F3E0 · 57 `AttachmentLookupPrefix` @0x02F650 · 58 `WeaponRegistryResetPrefix` @0x02F160 · 59 `WeaponRegistryInitializePrefix` @0x02FE80 · 60 `ZoneLoadedPrefix` @0x09F180 · 61 `CharacterCurrentItemsCopyPrefix` @0x219E90 · 62 `CurrentCharacterGetPrefix` @0x2B87C0 · 63 `CharacterSlotGetPrefix` @0x10FF30 · 64 `CharacterRecordFillDefaultsPrefix` @0x219AD0 · 65 `CharacterRecordToSelectionNamesPrefix` @0x21B6C0 · 66 `ConfigStringGetPrefix` @0x114880
   > `index 9/10` 的 `CollisionMapLoadRva`/`CollisionWorldLinkRva` 在 `EngineBindings.hpp:755-756`；`index 1` 的 `ComFramePrefix` 期望字节 `55 8B EC 56 57`（定义见 `EngineBindings.cpp:755-757`）。
   > 完整逐条数据（含期望字节）见 `COMBAT_P0_FAILURE_PATHS.json` 的 `unnamed_guard_chain.guards[]`。
4. `4025-4143`：指针赋值块（part 1）——**无失败点**。
5. **P0-09** `4144-4155`：runtime_slots。
6. `4156-4198`：指针赋值块（part 2）+ 三处 `CODDIFF` 显式置空（`worldCharacterModelResolve_ = nullptr; characterSelectionResolve_ = 0; weaponSlotReadStaged_ = 0;`）——**无失败点**。
7. **P0-10** `4199-4205`：`validateMessageBindings()`。
8. **P0-11** `4206-4212`：`installBrushTraceGlassBridge(module_)`。
9. `4213-4215`：`CCS_Initialized()`（丢弃返回值）、`bindingCommitted_.store(true)`、`return true`。

### 1.5 `bind()` 失败的后果与"三次相同日志"的判定力

**消费点**（`Appmain.cpp:7133-7137`）：

```cpp
if (!Bindings.bind())
{
    logGameServer("engine binding failed");
    return;                       // initialize() 直接返回
}
```

**因此没有执行的后续步骤**：`installFrameHook`（`:8128`）→ `installClientInputPatches`（`:8130`）→ `logGameServer("game server frame hook installed|failed")`；`Installed` 保持 `false`；`ensureInstalled()` 永远返回 false；所有 `CODOL_GameServerGet*` 导出返回 false；`Com_Frame` 未被 hook；`onServerFrame` 从不执行；`ensureDedicatedControlServer()` 从不执行（28961 从不监听）；`Network.start()` 从不执行（28960 从不监听）。

**三次真实日志（`E:\CODOL_SANDBOX\RUN001\Ayria\Logs\CodolGameServer.log`，582 B / 6 行）**：

```
[2026-10-10 15:47:48] [combined/game-server] engine binding failed
[2026-10-10 15:47:48] [combined/game-server] LOGSTALL lockUs=0 fileUs=913 consoleDebugUs=143018 prefix=engine binding failed
[2026-10-10 15:48:28] [combined/game-server] engine binding failed
[2026-10-10 15:48:28] [combined/game-server] LOGSTALL lockUs=0 fileUs=359 consoleDebugUs=141923 prefix=engine binding failed
[2026-10-10 15:50:14] [combined/game-server] engine binding failed
[2026-10-10 15:50:14] [combined/game-server] LOGSTALL lockUs=0 fileUs=386 consoleDebugUs=138151 prefix=engine binding failed
```

**可判定**：失败发生在 **P0-01 / P0-02 / P0-03|04|05** 三者之一。理由（本轮独立核实）：
1. `bind()` 只有 3 处静默 `return false`（`3656 / 3660 / 3666`）；其余 6 处**必然**先写日志。
2. `bind()` 的日志与 `logGameServer` **同通道、同文件、同前缀**（`RuntimeLog.cpp:60,77`）。
3. 实际日志中**不存在**任何 `native entity binding prefix mismatch` / `player DObj binding prefix mismatch` / `stage=function_prefixes|runtime_slots|message_bindings|glass_bridge` 行。

**不可判定**：**具体是哪一个静默分支**。因为 P0-03/04/05 共用同一个 `if`（§1.3），代码既不记录 effective 值也不记录分支。
**不得据此断言**：三次相同日志**不能**推出 `SizeOfImage` 是失败项；`TimeDateStamp` 也可能已不符（历史 `OL.exe` 案例中门禁因时间戳不符而失配）；`nt->Signature` 同理。
**反证条件**：若实际部署的插件（`6D493B82…`，2026-10-09 13:49）与当前源码树（F 构建 `DBA7273A…`，2026-10-10 12:52）在 `bind()` 的日志行为上存在差异，或 `RuntimeLog` 初始化失败导致日志静默丢弃，则"无 stage 日志 ⇒ 静默分支"这一推断不成立。**故 P1（部署件陈旧）必须先于任何结论性判断解决。**（该源级比对本轮**未做**——属构建/部署范围。）

### 1.6 帧钩子、`Com_Frame` 与 `NET_Frame` 的真实源码关系（F 树）

```
installFrameHook(Bindings, onServerFrame)            Appmain.cpp:8128（服务器角色）/ :7155（非服务器角色）
  └─ CodolGameServer::installFrameHook                FrameHook.cpp:59-116
       ├─ if (!bindings.valid())              → 日志 reason=invalid-bindings，return false   :63-67
       ├─ if (!callback)                      → 日志 reason=null-callback，return false      :68-72
       ├─ if (OriginalComFrame)               → 日志 reason=already-installed，return false  :73-79
       ├─ target = bindings.module() + EngineBindings::ComFrameRva(0x0FEA20)                 :81
       ├─ trampoline = VirtualAlloc(HookSize(5)+5, RWX)                                      :82-91
       ├─ copy_n(target,5,trampoline); trampoline[5]=0xE9; rel32 → target+5                   :93-96
       ├─ VirtualProtect(target,5,RWX) 失败   → 日志 reason=protect-failed + 原始 error       :99-106
       └─ target[0]=0xE9; rel32 → &comFrameHook; FlushInstructionCache                        :108-114

每帧：
  Com_Frame（宿主 RVA 0x0FEA20，被 5 字节 jmp 改向）
    └─ comFrameHook（__declspec(naked)）                FrameHook.cpp:37-49
         ├─ call dword ptr [OriginalComFrame]   ← 先执行原函数
         ├─ pushfd / pushad
         ├─ call runServerFrame                 :31-35
         │    └─ Callback(GetTickCount())  ==  onServerFrame
         └─ popad / popfd / ret
```

**`NET_Frame` 的归属（关键纠正）**：`Network.NET_Frame(Server, now)` 是**项目源码函数**（`src/game_server/server_mp/sv_network_mp.cpp`，由 `onServerFrame` 在 `Appmain.cpp:6633` 调用），**不是**原版引擎函数。原版 `NET_Frame` 的对应物为 **UNKNOWN**。

### 1.7 RVA 数量与守卫数量的核对，以及历史计数差异的解释

**本轮在相同文件（F 与 D 逐字节相同）上的实测**：

| 量 | 实测值 | 提取口径 |
|---|---|---|
| `static constexpr … *Rva = …` 声明 | **145** | 144 单行 + 1 跨行（`NativeLerpFrameAccessorInitializeRva`，`EngineBindings.hpp:562-563` = `0x003C70`） |
| `std::equal(` 出现总数 | **82** | 全文 |
| `bind()` 内的守卫 | **75** | 9 具名 + 66 未具名链 |
| 未具名 `||` 链长度 | **66** | `3744-4023` |
| 具名守卫 | **9** | 3（native entity）+ 6（player DObj） |
| 定义的前缀/后缀数组 | **79** | 77 单行 + 2 跨行（`NativeLerpFrameAccessorInitializePrefix`、`DObjContentsTracelinePartBitsPrefix`） |
| 定义但**未用于** `bind()` | **4** | `WorldCharacterModelResolvePrefix`、`CharacterSelectionResolvePrefix`、`WeaponSlotReadStagedPrefix`（三者在 1649370 上**故意不绑定**，见 `EngineBindings.cpp:3712-3718 / 4093-4094 / 4156-4166 / 4185-4186` 的 `CODDIFF`）与 `GfxImageInitializePrefix`（在 `bind()` **之外**的 `:11864` 惰性使用） |
| `bind()` 之外的 `std::equal(` | **7** | 见下表 |

**`bind()` 之外那 7 处的性质**（用于解释"82 不是守卫数"）：

| 行 | 性质 |
|---|---|
| `2991` | **非映像守卫**：反汇编/指令比较 |
| `4286` | 运行时惰性前缀检查（vectoangles 访问器） |
| `4331` | 运行时惰性前缀检查（`BG_EvaluateTrajectory`） |
| `11864` | 运行时前缀检查（`GfxImageInitializePrefix`） |
| `12027` | **非映像守卫**：alpha 武器贴图 slotHeader 数据比较 |
| `12039` | **非映像守卫**：constants 数据比较 |
| `12155` | 运行时 `exactPrefix` lambda（`ScriptStringIntern` / `XModelStreamQueue`） |

**历史计数差异的逐项解释**：

| 历史数字 | 出处 | 解释（本轮证据） |
|---|---|---|
| **66** | commit `55fcdbf` 提交信息："102 RVA constants, **66 byte prefixes**, 14 dedicated-process patch sites"；同提交称 `verify-bindings.py` 对 `out.exe` 离线重放 "all **66** `std::equal` guards … 66 pass, 0 fail" | **= 今天的未具名 `||` 链长度（66）**，且当年尚未拆分出今日的 9 条具名守卫（具名守卫引入于 `772b530`/`c941ecc`/`09de8f7`，见 §2）。即"66"从一开始就指**链**，不是全部守卫。 |
| **82** | `CODOL_SERVER_PROGRESS_20261009.md:185`、`COMBAT_SERVER_RECOVERY_BASELINE.md:25` | **= 全文 `std::equal(` 出现次数（82）**，含 7 处非 `bind()` 项（其中 3 处根本不是映像守卫）。**它不是守卫总数。** |
| **79 / 78** | `artifact_provenance.json:38-41`（"78/79 guards mismatch"） | "78/79"是**离线重放的结果分母**：对 79 个前缀数组逐一比对加壳映像，78 个不匹配，唯一匹配者是**数据常量** `ByteDirectionsPrefix`（`index 28`，12 字节 float）。它**不是**守卫计数。 |
| **145** | 本轮实测；亦见 `FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md:80,161,480` | **正确**（`static constexpr … *Rva` 声明数）。 |
| **146** | `CODOL_SERVER_PROGRESS_20261009.md:184`、`COMBAT_SERVER_RECOVERY_BASELINE.md:25` | **假阳性**：`CURRENT_CHARACTER_GET_RVA` 只出现在 `EngineBindings.hpp:854` 的**注释**里（"// CURRENT_CHARACTER_GET_RVA = 0x2B87C0 and calls it every run"）。把注释计入即得 146。 |
| **102 / 109** | commit `55fcdbf` 提交信息（102）；本轮 `git show 55fcdbf^:…hpp` 实测 109 | 翻转提交**删除 7 个常量**（`WorldCharacterModelResolve`、`CharacterSelectionResolve`、`WorldCharacterModelNameTable`、`WorldCharacterModelSlotBases`、`CharacterModelsInitialized`、`WeaponSlotReadStaged`、`CurrentCharacterGet`）⇒ 109 → 102；此后增至今日 145。 |
| **170 / 104** | `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` §4.2（"**170 个 RVA + 104 个 prefix 守卫**"，称 `EngineBindings.cpp` 17,419 行） | **对当前文件不可复现**：同一文件（`E624A8A1…`）实测 145 RVA / 75 守卫。17,419 是该文件的**非空行**数（`Measure-Object -Line`），不是不同版本。**该报告的这两个数字无证据支持，登记为冲突。** |

---

## 2. 任务 B：绑定数据的来源追溯

**标记**：`[直接证据]` 有源码或版本证据 · `[仅历史报告]` · `[UNKNOWN]`。

### 2.1 `TimeDateStamp` 与 `SizeOfImage` 常量的引入提交

| 项 | 结论 | 标记 | 已复核 | 检测方式 |
|---|---|---|---|---|
| 门禁常量与 `ComFrameRva` 的**引入** | commit `d4c6f0a3b2e997f1144d767d1f519315b2d50a2e`（2026-07-31，作者 `dest1yo`，"Migrate CODOL reconstruction to ol-mod"）；当时值 `ExpectedTimestamp=0x57611E31`、`ExpectedImageSize=0x0C72A000` | **直接证据** | 本轮 `git show '55fcdbf^:src/game_server/EngineBindings.hpp'` + `-S 'ComFrameRva'`（`--diff-filter=A`） | git |
| **翻转到 1649370** | commit `55fcdbfbc68c4844fd10abb1e3921733bc0597b2`（2026-08-18，作者 `eden`）：`ExpectedTimestamp 0x57611E31 → 0x6096930A`、`ExpectedImageSize 0x0C72A000 → 0x0E5D6000` | **直接证据** | 本轮 `git show 55fcdbf^:…` 与 `55fcdbf:…` 双读 | git |
| 同提交的 RVA/前缀同步翻转 | 提交信息："flip the host gate, **the RVAs and the prefixes together**"；改 `EngineBindings.cpp`、`EngineBindings.hpp`、`DedicatedProcessPatches.cpp`、`ServerCoreTests.cpp`（345 insertions / 284 deletions） | **直接证据** | `git show --stat 55fcdbf` | git |
| 提交信息的关键断言 | "ExpectedTimestamp/ExpectedImageSize are checked FIRST in bind(), so until now **nothing below them had ever executed on an OLfinal host** and every RVA and prefix in the file still held 3.3.3.3 values." | **直接证据（提交信息）** | 全文 `git log -1 --format=%B 55fcdbf` | git |
| 依赖说明 | "Flipping the gate alone does not disable those, it **ARMS** them against a build they do not describe." | **直接证据（提交信息）** | 同上 | git |
| `EngineBindings.hpp:434-435` 的**过期注释** | 由 `ae850959`（2026-08-16，作者 `dest1yo`）写入，仍写 `0x57611E31, 0x0C72A000`；**翻转提交未更新它** | **直接证据** | `git blame -L 434,440` | git |
| 宿主身份常量的**适用目标** | `out.exe`（build 1649370，SHA-256 `044c396c…257f9`）；**不是**加壳零售件 | **直接证据** | `EngineBindings.hpp:438-439` + §2.4 | 源码+git |

### 2.2 `Com_Frame` RVA `0x0FEA20` 的来源

| 项 | 结论 | 标记 |
|---|---|---|
| 引入 | 与门禁同批：`d4c6f0a`（2026-07-31）；当前值 `0x0FEA20`（`EngineBindings.hpp:440`） | **直接证据** |
| 翻转 | `55fcdbf`（"the RVAs … together"）将其从 3.3.3.3 值改为 1649370 值；本工作区**无法独立复核 3.3.3.3 时的具体数值**（除非读取 `d4c6f0a` 版本文件） | **直接证据（有翻转）；3.3.3.3 具体值 [UNKNOWN]** |
| 期望字节 | `55 8B EC 56 57`（5 B），`EngineBindings.cpp:755-757`（`ComFramePrefix`） | **直接证据** |
| 用途 | `installFrameHook` 在该 RVA 写 5 字节 `0xE9` 相对跳转 | **直接证据**（`FrameHook.cpp:81-114`） |
| 该 RVA 的**运行时字节** | **UNKNOWN**（从未在真实目标上测得；加壳件磁盘字节为 `03 C1 E0 06 50`，结构性不匹配） | **UNKNOWN** |

### 2.3 82（=75 实际）条前缀守卫的来源与适用版本

| 项 | 结论 | 标记 |
|---|---|---|
| 未具名 `||` 链（66） | 由 `55fcdbf` **整批翻转**到 1649370 值（"the RVAs and the prefixes together"）；提交信息记为 "66 byte prefixes" | **直接证据** |
| 具名守卫 3 条（`SV_LinkEntity`/`SV_UnlinkEntity`/`SV_Trace`） | 引入于 `772b530`（2026-08-10，"Recover embedded server entity bindings"） | **直接证据**（`git log -S SVLinkEntityPrefix`） |
| 具名守卫 `DObjFreePrefix` | 引入于 `c941ecc`（2026-08-10，"Restore live player server DObj models"） | **直接证据** |
| 具名守卫 `NativeLerpFrameAccessorInitializePrefix` / `BGPlayerAnimationPrefix` / `BGUpdatePlayerDObjPrefix` | 引入于 `09de8f7`（2026-08-11，"Restore native DObj locational tracing"） | **直接证据** |
| `ByteDirectionsPrefix`（数据常量守卫） | 引入于 `dcbc3c9`（2026-08-11，"Restore nonpenetrating bullet glass effects"）；比对的是 **12 字节浮点数据**（`4F 96 06 BF 00 00 00 00 44 C4 59 3F`），**不是代码** | **直接证据** |
| 守卫的**适用目标** | `out.exe` / build 1649370（由 `55fcdbf` 整体翻转；提交信息称离线重放对 `out.exe` 66/66 通过、对 `OL.exe` 门禁失配且 66 中 55 条失败） | **直接证据（提交信息）**；**本轮未独立重放** |
| 守卫在**当前加壳客户端运行时映像**上是否成立 | **UNKNOWN**（从未执行过一次） | **UNKNOWN** |

### 2.4 其他关键 RVA、结构偏移与调用约定

| 类别 | 内容 | 标记 |
|---|---|---|
| RVA 常量总数 | 145（`EngineBindings.hpp`），全部由 `55fcdbf` 及其后的恢复提交按 `out.exe`/1649370 建立（`55fcdbf` 时为 102，之后增至 145） | **直接证据（计数）**；逐条 RVA 的推导工具链证据在 CODOL-main 仓库的 `re/OLFINAL-FFA-HANDOFF.md` §18（**本工作区不可复核**）→ 该部分 **仅历史报告** |
| 调用约定 | `PmoveSingle`(`__cdecl`)、`PM_SetPitchValues`(EAX+stack)、`CM_WorldTrace`(EDX/EDI)、`CM_TransformedBrushModelTrace`(ECX/EDX, cleanup 0x18)、`SV_Trace`(ECX/EDX, cleanup 0x10)、`BG_PlayerStateToEntityState`(EAX/ECX)、`QuatToAxis`(EAX/ECX) 等 | **仅历史报告**（`.agents/modules/reverse_engineering.md` 的行号转引；本轮**未**逐条重读 IDA 结论） |
| 结构偏移 | `playerState_s=0x3564`、`usercmd_s=0x2C`、`pmove_t=0x12C`、`trace_t=0x28`、`entityState_s=0x110`、`DObj_s=0xCC`、`characterInfo_t=0x3B8`、`hudelem_s=0xA8` | **仅历史报告** |
| `CM_LoadMap` / `CM_LinkWorld` custom ABI | `ECX=mapName`、栈 `bspName/gameType`、`EAX` 返回 collision checksum | **仅历史报告**（`game_server.md:271-275`） |

### 2.5 现有代码是否隐含依赖"去壳映像 / 特定映像布局 / 特定构建版本"

**是，且是多层的：**

1. **显式构建身份**：`ExpectedTimestamp` + `ExpectedImageSize` 共同把宿主钉死在 **`out.exe` / build 1649370**（`EngineBindings.hpp:438-439`）。
2. **全部 RVA 由该构建推导**：145 个常量 + 75 条守卫的期望字节均面向 `out.exe` 的**去壳布局**（`55fcdbf` 提交信息）。
3. **映像布局依赖**：`module_ + Rva` 形式的指针运算假定 RVA 在运行时映像中指向同一段代码；`ServerDObjGetSuffix` 用 `ServerDObjGetRva + 5` 假定入口后第 5 字节的固定字节。
4. **对"数据常量"的依赖**：`ByteDirectionsPrefix` 与 `ByteDirectionsRva=0xA51C70` 比对浮点数据；`ConstantConfigStringChecksumRva`、`GametypeDvarCacheRva` 等是**全局变量地址**，与映像基址/布局绑定。
5. **构建差异已被代码显式承认**：三处 `CODDIFF` 注明"3.3.3.3 有、OLfinal 无"（`WorldCharacterModelResolve`、`CharacterSelectionResolve`、`WeaponSlotReadStaged`），并把它们**删除/置空**而非保留（`55fcdbf` 提交信息："SEVEN CONSTANTS WERE DELETED RATHER THAN UPDATED"）。
6. **不得推出的结论（任务明令 + 本轮独立确认）**：
   - ❌ 时间戳相同 ⇒ 二进制兼容（`0x6096930A` 是秒级时间戳，非唯一标识；加壳器常保留它）。
   - ❌ 映像大小不同 ⇒ 所有 RVA 失效（`bind()` 在这类比较上**从未执行到第二项**）。
   - ❌ 磁盘 `SizeOfImage=0x0E659000 ≠ 0x0E5D6000` ⇒ 宿主身份判负（门禁读的是**运行时映像**，不是磁盘加壳头）。

---

## 3. 任务 C：最小诊断方案

**总原则**：**默认不放宽 `SizeOfImage`**；不删除、不绕过任何门禁；不改变判定语义与守卫执行顺序。方案分三层，**第 1、2 层是纯日志与纯数据层，零判定语义变更**。

### 3.1 第 1 层：宿主映像身份门禁具名化（**纯日志，判定结果逐位不变**）

**问题**：`3655-3667` 的 3 处静默早退使三次实机日志的信息量为零。

**最小改动**（只改 `EngineBindings.cpp`，不动 `bind()` 的返回值）：

```cpp
// 语义完全不变：仍按 module → DOS → NT 的顺序短路；仍返回 false。
module_ = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
if (!module_) { logBinding(BindingStage::HostImageModuleMissing); return false; }

const auto *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module_);
if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
    logBinding(BindingStage::HostImageDosMagic,
               /*effective*/ dos->e_magic, /*expected*/ IMAGE_DOS_SIGNATURE);
    return false;
}
const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(module_ + dos->e_lfanew);
if (nt->Signature != IMAGE_NT_SIGNATURE) {
    logBinding(BindingStage::HostImageNtSignature, nt->Signature, IMAGE_NT_SIGNATURE);
    return false;
}
if (nt->FileHeader.TimeDateStamp != ExpectedTimestamp) {          // ← 拆分，顺序不变
    logBinding(BindingStage::HostImageTimestamp,
               nt->FileHeader.TimeDateStamp, ExpectedTimestamp);
    return false;
}
if (nt->OptionalHeader.SizeOfImage != ExpectedImageSize) {        // ← 拆分，顺序不变
    logBinding(BindingStage::HostImageSize,
               nt->OptionalHeader.SizeOfImage, ExpectedImageSize);
    return false;
}
```

**日志格式建议**（稳定、可机读、可被现有 `CodolGameServer.log` 承载）：

```
engine binding failed stage=host_image_timestamp effective=0x6096930A expected=0x6096930A
engine binding failed stage=host_image_size      effective=0x0E659000 expected=0x0E5D6000
engine binding failed stage=host_image_nt_signature effective=0x00004550 expected=0x00004550
engine binding failed stage=host_image_dos_magic effective=0x5A4D expected=0x5A4D
engine binding failed stage=host_image_module_missing
```

**兼容性**：`Appmain.cpp:7135` 的 `engine binding failed` **保留原样**（下游工具/报告已引用该串）；新日志作为**追加行**写在同一文件同一通道。**不修改** `FrameHook.cpp` 既有的 `reason=` 文案。

**语义等价性证明要求**（必须随实现提供）：对同一 `MODULE` 输入，改动前后 `bind()` 的**布尔返回值逐位相同**；对四种失配输入分别返回 false，对全通过输入返回 true。由第 3 层纯数据测试直接证明。

### 3.2 第 2 层：复合守卫稳定 ID + 首个失败者具名（**纯日志，判定结果逐位不变**）

**问题**：66 条 `||` 链只产生一条 `stage=function_prefixes`，不指出是哪一条。

**最小改动**：把 66 条 `||` 表达式改写为**顺序等价的逐条判定**（短路语义与顺序完全一致）：

```cpp
for (const ByteGuard &g : kFunctionPrefixGuards) {   // 数组顺序 == 现源码顺序
    if (!std::equal(g.begin(), g.end(), module_ + g.rva)) {
        logBinding(BindingStage::FunctionPrefix, g.id, g.rva, g.begin(), g.size());
        return false;
    }
}
```

`kFunctionPrefixGuards` 的元素由 `COMBAT_P0_FAILURE_PATHS.json` 的 `unnamed_guard_chain.guards[]` **逐项生成**（`index`/`id`/`prefix`/`rva`/`offset`/`bytes`），保证：

- **稳定 ID**：建议 `id` 取 `Prefix` 名去掉 `Prefix` 后缀（如 `ComFrame`、`WeaponResolver`），并保留 `index`（1..66）与 `rva`。
- **顺序不变**：数组按 `index` 升序，逐条 `continue`，首个失败即 `return false`——与 `||` 短路等价。
- **期望/实际值**：日志给出 `expected=<8 hex bytes>` 与 `effective=<read 的实际字节>`（只读比较，**不调用**被守卫函数）。
- **具名块同理**：`P0-06`（3 条）与 `P0-07`（6 条）改为同构的具名表，**保留现有 `function=<name>` 文案**以兼容既有阅读习惯，并追加 `id=/index=/rva=/expected=/effective=`。

**日志格式建议**：

```
engine binding validation failed stage=function_prefixes guard=ComFrame index=1 rva=0x0FEA20 expected=55 8B EC 56 57 effective=55 8B EC 56 57
engine binding validation failed stage=function_prefixes guard=WeaponResolver index=56 rva=0x02F3E0 expected=55 8B EC 56 8B 75 effective=00 00 00 00 00 00
```

> **注意**：`ByteDirectionsPrefix`（`index 28`）比较的是**数据**，日志里应标注 `kind=data`，避免把它当成代码前缀。

### 3.3 第 3 层：`EngineBindings` 的测试覆盖 —— **纯数据判定层**（**不为测试而运行引擎绑定**）

**现状（本轮核实）**：`EngineBindings.cpp` **不在任何测试目标内**（`xmake.lua` 的 `game_server_core` 不含它；只有生产插件 `ol_game_server` 编译它）。现有 8 个测试目标都无法在不链接 18k 行插件边界的情况下覆盖 `bind()`。

**因此不建议**"把 `EngineBindings.cpp` 直接塞进测试目标"（会把 9 个零测试文件之一的巨大依赖面引入测试，且 `bind()` 会真实读取**当前进程**的映像，测试进程里必然是错的映像 ⇒ 测试只能得到"失败"）。

**建议的最小可测设计：抽出纯判定层**（新增一个**不依赖 Windows/不读进程内存**的小单元）：

```cpp
// EngineBindingDecision.hpp —— 纯数据，无 I/O
namespace CodolGameServer::BindingDecision {

struct ImageFacts {                 // 由调用方从真实模块读出后填入
    bool      modulePresent;
    std::uint16_t dosMagic;
    std::uint32_t ntSignature;
    std::uint32_t timeDateStamp;
    std::uint32_t sizeOfImage;
};
struct Expectation {
    std::uint32_t timeDateStamp;
    std::uint32_t sizeOfImage;
};
enum class HostImageStage {            // 稳定 ID，供日志与测试共用
    Ok, ModuleMissing, DosMagic, NtSignature, TimeDateStamp, SizeOfImage
};
struct HostImageVerdict {
    HostImageStage stage;
    std::uint32_t  effective;
    std::uint32_t  expected;
};
HostImageVerdict evaluateHostImage(const ImageFacts &, const Expectation &);

struct ByteGuard { const char *id; std::uint32_t rva; const std::uint8_t *expected; std::size_t size; bool isData; };
struct GuardReader { virtual bool read(std::uint32_t rva, std::uint8_t *out, std::size_t n) const = 0; };
struct GuardVerdict { bool ok; const char *id; std::uint32_t rva; std::size_t index; };
GuardVerdict firstFailingGuard(std::span<const ByteGuard>, const GuardReader &);
}
```

**测试设计（不需要 CODOL 客户端、不读真实进程内存）**：

| 用例 | 输入 | 期望 |
|---|---|---|
| T1 | `modulePresent=false` | `stage=ModuleMissing` |
| T2 | DOS magic 错 | `stage=DosMagic` |
| T3 | NT signature 错 | `stage=NtSignature`（**T4/T5 不得被执行**） |
| T4 | 时间戳错、尺寸对 | `stage=TimeDateStamp`，`effective`/`expected` 正确 |
| T5 | 时间戳对、尺寸错 | `stage=SizeOfImage`，`effective=0x0E659000`，`expected=0x0E5D6000` |
| T6 | 全部对 | `stage=Ok` |
| T7 | 66 条守卫全对 | `firstFailingGuard.ok==true` |
| T8 | 仅 `index k` 错 | 返回 `index==k`、`id`、`rva` 与期望一致（对 k=1、28、66 各测一次） |
| T9 | 多个错 | 返回**最小 index**（顺序性） |
| T10 | reader 越界/读取失败 | 归类为失败且不崩、不调用任何被守卫函数 |
| T11 | **语义等价回归**：同一 `ImageFacts` 集合，旧 `if` 逻辑与新分层结果逐位一致 | 全等（可用表驱动） |
| T12 | 守卫表与源码一致性 | 从 `COMBAT_P0_FAILURE_PATHS.json` 生成的表条数 == 66，`id/index/rva/expected` 与 hpp/cpp **逐项一致** |

**为什么这满足"不改变原有绑定语义"**：纯判定层只做**比较**，没有指针发布、没有写内存、没有调用；`bind()` 只是把同样的输入喂给它并按同样顺序短路。

### 3.4 关于 `SizeOfImage` 容差开关的评估（**结论：本任务不建议引入，且本任务不授权在真实客户端启用**）

| 评估维度 | 结论 |
|---|---|
| 严格门禁是否足以完成诊断？ | **足以完成第 1 层诊断**（确定失败分支）；但**不足以**回答"加壳件运行时代码是否与目录一致"——因为门禁一旦拒绝，75 条守卫永不执行。该问题是 R-A/R-B 裁定的核心未知（U-01/U-02）。 |
| 是否必须用容差才能回答？ | **不必。** 更小、更安全的替代是 §4 的**只读字节采样**：在插件内读 `module_+0x0FEA20` 与 `module_+0x8371A` 的字节并写日志，**完全不经过门禁**，即可回答"运行时字节是否与期望一致"。这比放开尺寸门禁**风险更低**（不发布任何指针）。 |
| 若仍提出容差，必须满足的三项（本任务仅登记为条件，不实施） | ① **为什么严格门禁不足**：只有当"运行时 `SizeOfImage` 保持加壳值"且"运行时字节与目录一致"同时成立时，才需要据此提出常量修订；前者可由只读采样先行判定，故容差**不是必需**。② **如何避免其他守卫在错误映像上执行**：容差必须**只跳过 `SizeOfImage` 一项**，`TimeDateStamp` 与全部 75 条守卫**保持强制**；且守卫只做只读字节比较，绝不调用被守卫函数。③ **默认行为如何与当前完全一致**：必须由**显式环境变量**开启（未设置时逐位等价），并附 §3.3-T11 的差分测试证明。 |
| 本任务是否授权 | **不授权**在真实客户端上启用任何容差。 |

---

## 4. 任务 D：战斗创建与初始化的关系（只读追踪）

### D.1 服务器模块加载后，谁负责触发服务器初始化？

**直接证据**：`CodolGameServer.Localnet32` 被 `Localnetworking` 的 `Bridge::claimsHost/start` 枚举并以 `LoadLibraryW` 载入（`Localnetworking.cpp:367-379`）。载入即触发 `DllMain(DLL_PROCESS_ATTACH)` → `initialize()`（`Appmain.cpp:9538-9543`）。
此外插件导出 `onStartup(bool)`（`:8156`）与 `onInitialized(bool)`（`:8161`），二者都调用 `initialize()`（`:8158` / `:8163`）。`initialize()` 由 `StartupMutex` + `Installed` 早退保护，**幂等**（`Appmain.cpp:7012-7017`）。
**调用 `onStartup`/`onInitialized` 的主体是归档 `Bootstrapper32.dll`**：**仅历史报告**（该 DLL 为二进制，本工作区无其调用点证据；2026-10-10 的 `Bootstrapper32.log` 只记了 2 个 `.Ayria32` 插件加载，未记 `.Localnet32` 生命周期）。

### D.2 `combined` 与 `dedicated` 的服务器初始化路径差异

**直接证据**（`ProcessRole.hpp:17-50`；`Appmain.cpp:7012-7162` / `:8128-8132`）：

| 步 | `combined`（默认） | `dedicated` | `client` |
|---|---|---|---|
| `role` 来源 | `OLMOD_PROCESS_ROLE` 未设/未知 | `=dedicated` | `=client` |
| `installUnsignedFastfilePatch()`（`:7022-7035`） | 执行 | 执行 | 执行 |
| client 单实例 mutex patch（`:7100-7109`） | 不执行（仅 Client） | 不执行 | 执行 |
| `installDedicatedProcessPatches()`（`:7111-7132`） | **不执行** | **执行，失败即 return**（先于 `bind()`） | 不执行 |
| `Bindings.bind()`（`:7133-7137`） | 执行 | 执行 | 执行 |
| alpha weapon gamestate patch（`:7138-7152`） | 不执行 | 不执行 | 可选（`OLMOD_ALPHA_WEAPONS=1`） |
| `runsGameServer(role)` | true（`role != Client`） | true | **false** |
| 帧钩子 | `installFrameHook(Bindings, onServerFrame)` | 同左 | 同左（但 `onServerFrame` 内立即因 `!runsGameServer` 返回） |
| `onServerFrame` 内 | 继续到 DedicatedControl + `NET_Frame` | 同左 | `Appmain.cpp:6603-6604` 直接 return |
| `runsBackend(role)` | true | **false** | true |

⇒ `dedicated` **多一道前置门**（`installDedicatedProcessPatches`），`client` **不跑游戏服务器**，`combined` 兼跑 backend 与游戏服务器（listen-server）。
**2026-10-10 的三次运行均为 `combined`**（日志前缀 + 启动器 `Launch_OLMod.bat` 未设环境变量、无参数）。

### D.3 `installFrameHook` 的前置条件

**直接证据**（`FrameHook.cpp:59-116`）：
1. `bindings.valid()` 为真（`valid()` = `bindingCommitted_ && 一大批非空指针`，`EngineBindings.cpp:4218+`）——否则 `reason=invalid-bindings`。
2. `callback` 非空——否则 `reason=null-callback`。
3. `OriginalComFrame == nullptr`（未安装过）——否则 `reason=already-installed`（**良性**，可用 `isFrameHookInstalled()` 确认）。
4. `VirtualAlloc` 蹦床成功；`VirtualProtect(target, 5, RWX)` 成功。
⇒ 因此 **`bind()` 失败使 `valid()` 为 false，帧钩子在第一个前置条件处即被拒绝**（并写 `invalid-bindings`）。**2026-10-10 的日志中没有该行**——因为 `initialize()` 在 `bind()` 失败时已 `return`，**根本没走到 `installFrameHook`**。

### D.4 战斗创建入口是否已定位，证据在哪里？

**未定位。** 已核实的事实：
- `Createserver`（`Appmain.cpp:8155-8163` 区间，F 树）返回 `nullptr`；注释说明该导出只为"让归档的 Localnetworking 加载器保留本模块"；它是 **hostname 认领 ABI**，不是战斗创建入口。**直接证据（源码）**。
- 客户端侧候选（`QuickMatch 0x6F2C10`、`0x6E4A20`、`mmbook accepted 0x6E6F60`、`mmstart 0x6E6BF0`）**仅有静态逆向记录**，且 `0x6E4A20` 明确被记录为"进入 `MatchMaking_FIND_SERVERS_Query` 路径，**不是** authoritative server startup"。**仅历史报告**。
- 原版引擎中独立的"战斗/会话创建"函数：**UNKNOWN**。
- 协议逆向线（另一条线）已定位到 `15/5 findSessions → 6/14 mmbook/mmstart`，但其应答帧格式 UNKNOWN，且两线关系 UNKNOWN。**仅历史报告**。

### D.5 `Com_Frame` Hook 与地图初始化、游戏模式初始化、网络会话之间已确认的关系

**直接证据（源码）**：
- Hook 触发链：`Com_Frame` → `comFrameHook` → `runServerFrame` → `onServerFrame`（每帧）。
- **网络会话**：`onServerFrame` → `ensureDedicatedControlServer()`（`:6606`，定义 `:2072-2126`）→ 收到 `ConfigureSession` 时执行 `Server.configureSessionDescriptor(descriptor) && Network.start()`，成功后 `Server.setEnabled(true)`（`:2094-2098`），并写 `ConfigureSession accepted|rejected bytes=… endpoint=…`。
- **地图/世界初始化发生在`SessionStart` 消费循环内，而不是在帧钩子或 ConfigureSession 时**：`Appmain.cpp:2564-2591` 先 `Bindings.zoneLoaded(mapName)`，再 `Bindings.initializeLevelWorld(mapName, gameType)`（→ `CM_LoadMap`/`CM_LinkWorld`，`EngineBindings.cpp:4552`）；失败写 `world initialization failed map=…` 并 `failSession(WorldInitializationFailed)`；成功写 `world initialized map=…`。随后 `CCS_Clear()`（`:2592-2599`）。
- **游戏模式/规则**：由 booking 侧 `configureMatchRules`（`sv_main_mp.cpp:1772`）与 gamestate（`configureGameState`，`:1635`）承载；`SessionStart` 是控制消息（`Appmain.cpp:2212-2270` 解码并入队）。
⇒ **已确认顺序**：`Com_Frame` hook（每帧）→ 控制面 `ConfigureSession`（开服 + 监听）→ `SessionStart`（地图/世界/CCS/booking/gamestate）。
⇒ **注意**：**"帧钩子安装成功"与"端口监听"与"进对局"是三件不同的事**；三者在本项目历史上**都未发生过**。

### D.6 28960 监听在当前架构中由哪条后端路径触发？

**直接证据**：
```
backend ──ConfigureSession（DedicatedControl 28961）──▶ Appmain.cpp:2087-2098
   ├─ Server.configureSessionDescriptor(std::span(descriptor))   sv_main_mp.cpp:1563
   ├─ Network.start()                                            sv_network_mp.cpp:20
   │     └─ socket bind(0.0.0.0:28960)                           win_net.cpp:113
   └─ Server.setEnabled(true)                                    sv_main_mp.cpp:1166
```
另有一条**非后端**路径：导出 `CODOL_GameServerSetEnabled(true)`（`Appmain.cpp:8176-8185`）会调用 `Network.start()`。**该导出在树内无调用方**（历史报告记为"仅 Frida 工具 3 处引用"，**树外**）。
⇒ **监听不是战斗创建入口**；它由**后端会话配置**触发。**2026-10-10 三次运行中 28960 从未监听**（且 `Network.start()` 根本未被执行，因为 `bind()` 已失败）。

### D.7 已确认 / 仅历史推断 / 必须真实运行才能确认

| 环节 | 源码证据 | 仅历史推断 | 必须真实运行 |
|---|---|---|---|
| 插件加载（`LoadLibraryW`） | ✅ `Localnetworking.cpp:367-379` | — | — （已被 2026-10-10 证实） |
| `initialize()` 触发 | ✅ `DllMain:9538-9543`、`onStartup/onInitialized:8156-8163` | 谁调用 `onStartup/onInitialized`（Bootstrapper32） | — |
| 角色分流 | ✅ `ProcessRole.hpp:17-50`、`Appmain.cpp:7017-7162` | 生产是否设 `OLMOD_PROCESS_ROLE` | 启动脚本环境 |
| `bind()` 门禁与守卫 | ✅ `EngineBindings.cpp:3647-4216` | 各 RVA/前缀的**推导过程**（在 CODOL-main 仓库） | **运行时映像的 PE 头与关键 RVA 字节** |
| 帧钩子安装 | ✅ `FrameHook.cpp:59-116` | — | `game server frame hook installed|failed` |
| 控制面 28961 | ✅ `Appmain.cpp:2072-2126`、`DedicatedControl.hpp:16` | — | 是否真的收到 `ConfigureSession` |
| 28960 监听 | ✅ `sv_network_mp.cpp:20`、`win_net.cpp:113` | — | `bound=1` / `port≠0` |
| `SessionStart` → 地图/世界 | ✅ `Appmain.cpp:2212-2270, 2564-2591`、`EngineBindings.cpp:4552` | 真实 booking 描述符字节 | `world initialized map=…` |
| gamestate / snapshot | ✅ `sv_main_mp.cpp:1635`、`server_mp/*` | 真实客户端解析结果 | 客户端 `CL_ParseGamestate`/`CL_ParseSnapshot` |
| 战斗创建入口（客户端） | — | 候选地址（`0x6E4A20` 等） | **必须由真实运行/更深静态证据确认** |

---

## 5. 对验收标准的逐条回应

| # | 验收标准 | 本文件对应 | 状态 |
|---|---|---|---|
| 1 | 所有绑定失败返回路径已枚举 | §1.1（9 条 + 子分支）、`COMBAT_P0_FAILURE_PATHS.json` | **满足** |
| 2 | 当前门禁失败的具体分支已被证据确定，或说明为什么证据不足 | §1.5：限定到 3 个静默分支之一；**明确说明不足**（同一 `if`、无 effective 日志、部署件与源码可能不同） | **满足（含明确的"不足"结论）** |
| 3 | 关键 RVA、守卫与 ABI 的来源得到追溯 | §2（逐项标记 直接证据 / 仅历史报告 / UNKNOWN） | **满足**（ABI/结构偏移部分标记为**仅历史报告**，本轮未独立复核） |
| 4 | 已形成不改变严格门禁语义的最小诊断方案 | §3（三层，默认不放宽尺寸；含测试设计与等价性证明要求） | **满足** |
| 5 | 战斗创建入口与服务器初始化路径的已知、未知部分清楚分离 | §4（D.1–D.7） | **满足** |
| 6 | 下一项真实实验有明确目的、授权边界与停止条件 | `COMBAT_P0_VALIDATION_PLAN.md` | **满足** |
| 7 | 工作区与 `GOLDEN-LOBBY-001` 基线保持不变 | §6 | **满足** |

---

## 6. 本轮实际执行的边界核对

| 禁止项 | 执行情况 |
|---|---|
| 启动/附加/注入/暂停/终止/重启任何进程 | **未执行**（0 次） |
| 在真实客户端上执行新的运行时实验 | **未执行** |
| 读取或修改真实客户端进程内存 | **未执行**（只读磁盘文件与日志） |
| 启用 `SizeOfImage` 容差 | **未执行**；§3.4 结论为"本任务不建议引入、不授权启用" |
| 删除或绕过映像身份门禁 | **未执行** |
| 修改 RVA / 函数地址 / 结构偏移 / ABI / 协议常量 | **未执行**（源码零字节改动） |
| 修改启动器 / TCLS / Ayria / 大厅启动链 | **未执行** |
| 构建或部署生产产物 | **未执行** |
| 提交 / 推送 / 重置 / 清理工作区 | **未执行** |

本轮**唯一写入**：四份交付物（本文件、`COMBAT_P0_FAILURE_PATHS.json`、`COMBAT_P0_VALIDATION_PLAN.md`、`COMBAT_P0_SHA256_MANIFEST.txt`）。
`GOLDEN-LOBBY-001` 及其 `REF_LOBBY_KIT` 副本：本轮**只读**（未打开写入）。F/D 两树源码：**零字节改动**。
