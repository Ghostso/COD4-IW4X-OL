# CODOL 服务端 builtin 恢复矩阵

更新时间：2026-08-03

## 问题与判定边界

本调查回答三个不同问题，不能混成一次字符串搜索：

1. BO1 server/client VM 实际注册了哪些 function 和 method；
2. 同版本脚本与跨版本 IW4 脚本实际调用了其中哪些名称；
3. CODOL 客户端是否还保留可复用 native，以及 `ol_game_server` 是否已有对应 authoritative 语义。

BO1 的答案来自 resolver 直接绑定表，不来自散落字符串。CODOL 当前未发现通用 GSC/CSC resolver、compiler 或 VM，因此同名字符串只能定位候选，不能证明注册、ABI 或 native 存在。即使客户端仍有同源表现或预测函数，玩家 inventory、damage、spawn、entity 和 match rule 仍必须由 server binding 承担。

完整机器可读结果由 [`../../tools/reverse/catalogs/codol_builtin_matrix.json`](../../tools/reverse/catalogs/codol_builtin_matrix.json) 单点维护，生成器为 [`../../tools/reverse/CodolBuiltinMatrix.py`](../../tools/reverse/CodolBuiltinMatrix.py)。

## BO1 直接绑定链

BO1 `2011-08-31` Windows x86 server i64 的顶层分派为：

```text
GetFunction(scriptInstance)
  server -> Scr_GetFunction 0x00660A50
  client -> CScr_GetFunction 0x004F27F0

GetMethod(scriptInstance)
  server -> Scr_GetMethod 0x006615C0
  client -> CScr_GetMethod 0x004FB030
```

每个 `BuiltinFunctionDef/BuiltinMethodDef` 都是 12 bytes：`name* + handler* + type/reserved`。专用 method resolver 虽不读取第三个字段，汇编仍以 `imul index, 0xC` 访问；早期 8-byte stride 摘要已证伪。server method 的真实优先级为 player、script entity、vehicle、HUD、helicopter、actor、generic；client function/method 都先查 common table，再查 project-specific table。

| 绑定表 | 数量 | VA | resolver |
| --- | ---: | --- | --- |
| server functions | 383 | `0x00E08510` | `Scr_GetFunction` |
| server generic methods | 234 | `0x00E09708` | `BuiltIn_GetMethod` |
| player methods | 154 | `0x00CB4540` | `Player_GetMethod` |
| script entity methods | 18 | `0x00CC8550` | `ScriptEnt_GetMethod` |
| vehicle methods | 89 | `0x00CC8E30` | `ScriptVehicle_GetMethod` |
| HUD methods | 26 | `0x00CB8480` | `HudElem_GetMethod` |
| helicopter methods | 27 | `0x00CBFFA0` | `Helicopter_GetMethod` |
| actor methods | 77 | `0x00D359D8` | `Actor_GetMethod` |
| client functions | 154 | `0x00E038B0` | `CScr_GetFunction` |
| client project functions | 26 | `0x00E04080` | `CScr_GetFunctionProjectSpecific` |
| client methods | 111 | `0x00C8A6A0` | `CScr_GetMethod` |
| client project methods | 29 | `0x00C8E660` | `CScr_GetMethodProjectSpecific` |

总计 1328 个原始表项、1165 个唯一 `kind:name` binding、1142 个唯一文本名。按 binding 统计，846 个 server-only、181 个 client-only、138 个在 server/client VM 都注册。function 与 method 即使同名也不是同一入口，例如 `function:spawn` 和 `method:spawn` 必须分开保留。

## 脚本 corpus 覆盖

`COD-GSC-Source/BO1-GSC` 当前有 497 个 GSC 和 108 个 CSC，命中 448 个 server builtin 名称和全部 165 个已出现 client builtin 名称。这个数字不能解释为 BO1 MP 的完整最小集：该 archive 的 `maps/mp` 只有 `mp_mountain.gsc`，缺少典型 MP `_globallogic/_playerlogic/_weapons/war/sd`，其大部分内容属于 SP/Zombies。它适合证明 builtin 被实际使用，不适合单独决定 CODOL MP 优先级。

`COD-GSC-Source/IW4-GSC` 的 1573 个 GSC 命中 515 个 BO1 同名 binding。该列只用于跨代调用频率和职责参考；在取得 IW4 对应完整注册表前，不能称为 IW4 builtin 全集，也不能把 IW4 名称直接绑定到 CODOL。

## CODOL 客户端与服务端所有权

对 CODOL EXE 的 standalone C string locator 只命中 51 个 BO1 名称。该结果不表示“客户端只剩 51 个 builtin”，也不表示这些名称仍是 builtin：客户端通用 VM 已被裁剪，同源 native 可能没有脚本名，剩余字符串也可能属于 UI、日志或其他 parser。后续 `native_match` 只能由 CODOL i64 xref、反汇编、数据流或运行证据晋级。

当前已经确认客户端保留的不是 server builtin handler，而是 gameplay 消费和预测链：

- `Pmove 0x0041E860 -> PmoveSingle 0x0041DBA0`、ground trace、jump、mantle 和 `PM_Weapon 0x00429320`；
- snapshot/playerstate parser 与 prediction；
- `CG_SelectWeapon -> CL_SetUserCmdWeapons -> CL_FinishMove` 的 weapon selection/usercmd 回程；
- native clipMap capsule trace `0x00459C20`；
- DObj/XAnim/viewmodel 消费链的部分入口。

这些函数说明客户端能预测和呈现 server state，不会替代 authoritative inventory、spawn、damage 或 entity world。未来 server script registry 应把 builtin handler 绑定到 `ol_game_server` 的稳定 C++ gameplay API，而不是反向调用客户端 `CG_*/CL_*` 完成权威状态。

## 首个可玩闭环

以下是当前 P0 binding 与实现成本。`wrapper` 指底层 server state 已存在，仍需参数校验、VM value 转换和错误语义；`partial` 指已有主要状态但缺少重要 side effect；`missing` 指底层 gameplay 仍需先恢复。

| 分组 | binding | 当前判断 |
| --- | --- | --- |
| 已实现 | `method:getvelocity`, `method:isonground` | VM 无关 registry 已从 `SvServerWorld` 返回 authoritative vector/bool，并校验 player receiver 与 `Playing` 状态 |
| 已实现（普通 ammo pool） | `method:setweaponammoclip`, `method:setweaponammostock` | BO1 handler 与 GSC 均确认 `(weaponName, count)`；world API 只改 owned weapon clip/pool、夹紧范围并由下一帧 snapshot 回读。CODOL clip-only weapon flag 尚未定位，stock 对该分支保留 TODO |
| 部分已有 | `method:setorigin`, `method:setplayerangles` | per-player state 已存在；仍需 teleport/input baseline、link/collision 和 delta-angle side effect |
| 部分已有 | `method:giveweapon`, `method:takeweapon`, `method:takeallweapons`, `method:switchtoweapon` | held/current weapon、ammo 和 drop/raise 已存在；缺通用 inventory mutation、正确背包 asset ownership 和完整 viewmodel/presentation |
| 部分已有 | `method:spawn` | Playing transition、spawnGeneration、POF_PLAYER 和初始 collision 已有；缺完整 ClientSpawn、entity/model/loadout reset 与 notify |
| 部分已有 | `method:allowjump`, `method:freezecontrols`, `method:disableweapons`, `method:enableweapons` | jump/weapon/input 路径存在，但尚无 authoritative gate 和对应 CODOL flag/state 语义 |
| 尚缺 | `method:allowads`, `method:allowsprint`, `method:setspawnweapon` | ADS/sprint 和 spawn weapon lifecycle 尚未恢复 |
| 尚缺 | `method:setperk`, `method:unsetperk`, `method:clearperks` | perk storage、net state、movement/weapon effect 和 lifecycle 均未恢复 |
| 尚缺 | `method:finishplayerdamage`, `method:suicide` | 只有 health netfield；缺 bullet/damage、death、obituary、respawn 和 match rule |
| 部分已有 | `method:setmodel` | generation-safe `ET_SCRIPTMOVER` 已通过宿主 XModel/CCS resolver 更新 snapshot `modelIndex`；部件/tag、碰撞和完整 destructible side effect 仍缺 |
| 尚缺 | `function:spawn`, `method:delete` | 缺面向脚本的通用 gentity allocation/free、类型初始化、link/unlink 和完整 snapshot lifecycle |

语言级 `thread/wait/waittill/notify/endon` 不属于普通 engine builtin 表，而是 VM scheduler、event 和 thread lifetime 语义，也属于最小脚本运行时 P0。P1 再加入 HUD、score/team/rank、objective、announcer/killcam 和 match completion；vehicle/helicopter/actor AI、cinematic/createfx 与 developer 功能后置。

## 下一步

1. 已建立 server-side `kind:name` registry、value/object/error contract，并完成四个首批 wrapper；handler 只调用明确的 `SvServerWorld` API。
2. 暂停横向增加 wrapper，优先恢复真实 loadout ownership、稳定移动、完整 ClientSpawn/entity/model 和第一人称表现等底层 gameplay；这些能力稳定后再接对应 partial binding。
3. 对 partial/missing 项按 BO1 handler xref、BO2/Ghosts server 结构和 CODOL client consumer 逐项恢复底层语义；CODOL wire/运行证据最终裁决。
4. 取得更完整 BO1 MP GSC 后重算实际调用优先级；当前 BO1 archive 覆盖不足不得伪装成完整 MP 需求集。
