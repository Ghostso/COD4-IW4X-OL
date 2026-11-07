# 270 · `gameTypeIsTeamless` 由脚本 diff 推导、`2566829241` vs `994462206` 的校验和错配、两个 64 KB 缓冲

## 一、范围

本报告学习 `Appmain.cpp` 1–180 行（文件开头）。

## 二、33 个 `#include`

### 2.1 五组

```text
本目录（game_server）   ClientNoclipHotkey / EngineBindings / codol_bot_* / SessionAssetRegistry /
                        GameStateConfiguration / ClientProcessPatches / DisconnectWitness /
                        ClientAnimtreeHook / ClientRenderFrameHook / DedicatedSessionConsumption /
                        DedicatedProcessPatches / ClientCommandTrace / FrameHook
相邻目录               ../client_bridge/ClientSessionBridge.hpp
                        ../shared/{DedicatedControl, ProcessRole, RuntimeLog}.hpp
server_mp（24 个）      sv_bullet_mp / sv_client_events_mp / sv_const_baselines_mp /
                        sv_destructible_mp / sv_frame_diagnostics / sv_gamestate_mp /
                        sv_battlechatter_mp / sv_main_mp / sv_mapents_mp / sv_network_mp /
                        sv_playlist_mp / sv_script_source_mp / sv_zm_navgraph_mp /
                        sv_bot_nav_mp / sv_zm_special_mp / sv_zm_factory_room_patch
标准库                  28 个
```

### 2.2 **前两个 include 在 `#define WIN32_LEAN_AND_MEAN` 之**前

```cpp
#include "server_mp/sv_zm_special_mp.hpp"
#include "server_mp/sv_zm_factory_room_patch.hpp"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
```

**⇒ 两个游戏头文件先于 Windows。所以它们不能依赖 Windows 类型。**

**⇒ 这是一个有意的顺序。**

### 2.3 **`EngineBindings.cpp` 里的 `EngineBindings.hpp` 是 133 KB**

**⇒ 而 `Appmain.cpp` 566 KB。**

**⇒ 所以这个项目最大的两个文件都服务同一个绑定面。**

## 三、**`gameTypeIsTeamless` 的六个 token**（本组最重要的一段）

### 3.1 那段完整的推理

```php
// THE GAMETYPE PIN'S REASON DOES NOT APPLY TO EVERY GAMETYPE, AND PINNING THEM ALL
// BREAKS THE MAPS THAT SHIP AN ADDON. Section 187o pins a booked gametype to `dm`
// because a TEAM script puts two players on one side and `issameteam` then blocks
// all damage. That reason is about the SCRIPT, so the test is the script:
//
//     assets/game_scripts/gametypes/<token>.lua  IS dm.lua  ->  already teamless,
//                                                                nothing to pin
//     cha.lua, sd.lua, zm.lua                    differ      ->  real sides, pin
//
// Pinning a teamless token is not merely redundant, it is HARMFUL. Section 152o:
// the token selects the FASTFILE SET, and the client loads whatever ITS PLAYLIST
// says. On `mp_battlecity` the client loads base + `dmz_addon` and computes
// 2566829241, while a dedicated pinned to `dm` loads base only and computes
// 994462206 -- the exact mismatch §152n diagnosed, reaching the player as the level
// -file dialog. `mp_nuked` hid this for months because `cha` has no addon there, so
// pinning cha->dm changes no file and the checksums agree anyway.
```

### 3.2 五层

```text
1. §187o 把预定的 gametype 钉到 `dm`，因为 TEAM 脚本把两个玩家放同一侧而 `issameteam` 挡住全部伤害
2. 那个理由是关于【脚本】的 ⇒ 所以测试就是脚本
3. 钉一个【本来就无队伍】的 token 不只是冗余，是【有害】
4. 因为 token 选择【fastfile 集合】，而客户端加载【它自己 playlist 说的】
5. ⇒ `mp_battlecity` 上客户端加载 base + `dmz_addon` 算出 2566829241，而钉到 `dm` 的专用服只加载 base 算出 994462206
```

### 3.3 两个校验和

```text
2566829241    客户端（base + dmz_addon）
994462206     专用服（base only）
```

**⇒ 而"这正是 §152n 诊断的那处错配，以**关卡文件对话框**的形式到达玩家"。**

### 3.4 而 `mp_nuked` **掩盖了这问题几个月**

```text
`cha` 在那里没有 addon ⇒ 钉 cha->dm 不改变任何文件 ⇒ 校验和本来就一致
```

**⇒ 一个"在某张地图上看不出问题"的经典情形。**

### 3.5 **推导方法是"diff 脚本"**

```php
// DERIVED BY DIFFING THE SCRIPTS, not chosen. Re-derive with:
//     for g in *.lua; do diff -q dm.lua $g; done
// and revisit this list if any of these ever stops being a dm.lua copy -- giving
// dmz.lua real duo teams, for instance, would put `dmz` back on the pinned side.
```

### 3.6 三条

```text
推导方式：对 dm.lua 做 diff
可复现命令：`for g in *.lua; do diff -q dm.lua $g; done`
失效条件：如果某个不再是 dm.lua 的副本（例如给 dmz.lua 真队伍）⇒ 移回"钉"的一侧
```

**⇒ 这是一个**可复现、可审计**的推导** —— 而不是"我试出来了"。

### 3.7 六个 token

```cpp
return gameType == "dm" || gameType == "dmz" || gameType == "zarena" ||
    gameType == "zhunt" || gameType == "coop" || gameType == "td";
```

```text
dm         死亡竞赛
dmz         ?
zarena     僵尸竞技场
zhunt      僵尸猎杀
coop       合作
td         团队死亡？  ← 【"td" 可能是 TDM 的缩写，那它【有】队伍！】
```

**⚠ `"td"` 在列表里而名字暗示"team deathmatch"。**

**⇒ 但从"是 dm.lua 的副本"这个判据看，`td.lua` 可能确实与 `dm.lua` 相同（只是一个别名）。**

**⇒ 值得指出这个可疑项。**

### 3.8 与 §237 的"正确的偏移让服务器成为僵尸服"的关系

**§237**："正确的读取 + 正确提交 = 游戏坏了（因为队伍分配还不支持对立侧）"

**⇒ 而 §270 的 `gameTypeIsTeamless` 是那个问题的一个**部分解**：**

```text
teamless 的 token    ⇒ 不钉（保持原样，因为本来就没队伍）
有队伍 的 token      ⇒ 钉到 dm（避免 issameteam 挡伤害）
```

**⇒ 所以**现在**项目选择"钉有队伍的到 dm"而不是"实现队伍分配"。**

**⇒ 与 §237 里"回退到 3.3.3.3 的偏移"是同一类**功能降级**。**

## 四、`BulletTraceDiagnostics = false`

```cpp
// The locational hit probe was useful while validating player damage, but
// walking every collision entity and formatting a large line for every
// bullet is far too expensive for normal play (especially automatic fire).
constexpr bool BulletTraceDiagnostics = false;
```

### 4.1 三层

```text
1. 定位命中探针在验证玩家伤害时有用
2. 但走每一个碰撞实体并为每颗子弹格式化一大行 ⇒ 对正常游戏太贵
3. 尤其是自动开火
```

**⇒ 与 §266 的 `hitboxTraceLogCounter_ < 128` 是同一个问题的两种解法**：

```text
§270  编译期 `constexpr false`    【完全关闭】
§266  运行期计数封顶 128          【采样】
```

### 4.2 而 `constexpr` 意味着**零运行时开销**

**⇒ 编译器会消除 `if (BulletTraceDiagnostics)` 的所有分支。**

## 五、`currentThreadCpuMicroseconds` 的**两项**

```cpp
FILETIME created{}, exited{}, kernel{}, user{};
if (!GetThreadTimes(GetCurrentThread(), &created, &exited, &kernel, &user))
    return nullopt;
const auto ticks = [](const FILETIME &time) {
    return (uint64{time.dwHighDateTime} << 32) | time.dwLowDateTime;
};
return (ticks(kernel) + ticks(user)) / 10u;
```

### 5.1 三项

```text
GetThreadTimes 成功
FILETIME 拼成 64 位
(kernel + user) / 10     → 微秒
```

### 5.2 **`/ 10` 是 FILETIME 的 100ns 单位 → 微秒**

**⇒ `1 微秒 = 10 × 100ns`** ✓

### 5.3 而这是**线程 CPU 时间**而不是墙钟

**⇒ 与 `elapsedMicroseconds`（墙钟）互补。**

**⇒ 所以这个文件里两种计时都用。**

**⇒ 与 §263 的 `TRACE CENSUS`（墙钟）与 `ActorCapsuleCost`（墙钟）不同 —— 这里多了 CPU 时间。**

## 六、`formatTimingWindow` 的**三段**

```php
std::string result = std::to_string(timing.lastMicroseconds) + "/" +
    std::to_string(timing.averageMicroseconds()) + "/" +
    std::to_string(timing.maximumMicroseconds) + " buckets=";
for (index) { result += (index ? "," : "") + std::to_string(timing.buckets[index]); }
```

### 6.1 格式

```text
<last>/<avg>/<max> buckets=<b0>,<b1>,...
```

### 6.2 而 `buckets` 是一个直方图

**⇒ 与 §144 里"timing 7 buckets"相关**（但那是不同的子系统）。

## 七、两个 64 KB 缓冲

```cpp
std::vector<std::uint8_t> buildGameState(...) {
    std::vector<std::uint8_t> buffer(64 * 1024);
    EngineMsgWriter message(Bindings, buffer);
    if (!SV_WriteGameState(message, gameState, clientNum, reliableSequence)) return {};
    const auto data = message.data();
    return { data.begin(), data.end() };
}

std::vector<std::uint8_t> buildSnapshot(...) {
    const auto timingStart = RuntimeClock::now();
    std::vector<std::uint8_t> buffer(64 * 1024);
    EngineMsgWriter message(Bindings, buffer);
    SvSnapshotWriteFailure failure{};
    if (!SV_WriteSnapshot(message, frame, baseline, clientNum, deltaMessageDistance, initializeBaselineCache, ...))
    ...
}
```

### 7.1 **两个都用 64 KB**

**⇒ 而 §268 的 `validateMessageBindings` 用 512 字节（因为只写一个测试 gamestate）。**

**⇒ 所以 64 KB 是**生产**大小。**

### 7.2 ⚠ **每次调用都分配 64 KB 的 `std::vector`**

**⇒ 如果 `buildSnapshot` 每帧每客户端调用一次（例如 20 Hz × 18 客户端 = 360 次/秒）⇒ 每秒 23 MB 的分配。**

**⇒ 这是一个**潜在的性能问题**。**

**⇒ 但 `<vector>` 的分配器可能复用（如果大小相同）。**

### 7.3 而 `buildGameState` 的 `return {}` 失败

**⇒ 一个空 `vector`** —— 而不是 `nullopt`。

**⇒ 所以调用者必须检查 `empty()`。**

### 7.4 而 `buildSnapshot` 的 `timingStart` **未被使用**

```cpp
const auto timingStart = RuntimeClock::now();
...
```

**⚠ 而从这 180 行看不到 `timingStart` 的使用** —— 它应该在后面用于记录耗时。

**⇒ 待读。**

### 7.5 `buildSnapshot` 的**七个参数**

```text
frame
baseline
clientNum
deltaMessageDistance
initializeBaselineCache
clientPrediction
（加上 Bindings 是全局的）
```

**⇒ 六个显式参数。**

**⇒ `deltaMessageDistance` 是 `uint8`** —— 与记忆里"`deltaMessageDistance`"相关。

## 八、全局对象

```cpp
CodolGameServer::EngineBindings Bindings;
CodolGameServer::SvTimingAccumulator ServerFrameTiming;
CodolGameServer::SvTimingAccumulator NetworkSendTiming;
std::array<SvTimingAccumulator, MaximumGameClients> SnapshotBuildTiming;
```

### 8.1 四组

```text
Bindings                【一个】全局绑定实例
ServerFrameTiming       服务端帧
NetworkSendTiming       网络发送
SnapshotBuildTiming     【每客户端】快照构建
```

### 8.2 而 `Bindings` 是**唯一**的

**⇒ 所以整个 `Appmain.cpp` 共用一个绑定实例** ✓ 与 §261 的"全局自由函数共享注册表"一致。

## 九、关键结论

1. **两个 `sv_zm_*` 头在 `Windows.h` 之前** —— 所以它们不依赖 Windows 类型。
2. **`gameTypeIsTeamless` 由 `diff dm.lua` 推导**，有可复现命令与失效条件。
3. **`2566829241` vs `994462206`** 是"客户端加载 addon 而专用服没有"的校验和错配 ⇒ 关卡文件对话框。
4. **`mp_nuked` 因 `cha` 在那里没有 addon 而掩盖了问题几个月**。
5. **`"td"` 在 teamless 列表里是一个可疑项**（名字暗示 team deathmatch）。
6. **`BulletTraceDiagnostics = false`**（编译期）与 §266 的运行期计数封顶是同一问题的两种解法。
7. **`currentThreadCpuMicroseconds` 的 `/10`** 是 100ns → 微秒。
8. **墙钟与 CPU 时间两种计时都在用**。
9. **两个 64 KB 缓冲**，每次调用都分配 —— 潜在的性能问题。
10. **`buildGameState` 失败返回空 `vector`** 而不是 `nullopt`。
11. **`timingStart` 在 1–180 行内未被使用**。
12. **`Bindings` 是唯一的全局绑定实例**。

## 十、未闭合点

- `"td"` 是否真的与 `dm.lua` 相同。
- `2566829241` / `994462206` 是 CRC32 还是别的算法。
- `buildSnapshot` 的 `timingStart` 用途。
- 64 KB 缓冲的分配频率。
- `Appmain.cpp` 180 行之后未读取（文件 566 KB）。
