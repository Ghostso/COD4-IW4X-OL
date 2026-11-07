# GSC 恢复模块

## 责任与目标

本模块负责恢复 CODOL 缺失的服务端 game script 链路，包括脚本发现与导出、反编译和编译、加载与链接、VM 生命周期、game notify，以及在此基础上的 gameplay 脚本。服务端脚本记为 GSC（通常为 `.gsc`），客户端脚本按 CODOL 资料暂记为 CAS（通常为 `.cas`）；在资产清单证明两者格式和所有权前，不把它们混为同一种文件。

首批 gameplay 目标是玩家模型与基本操作初始化、perk、地图通用逻辑，以及 TDM、SD 和固定复活点团队模式。它们最终必须进入 authoritative server 生命周期，不能用客户端临时状态或硬编码 weapon/playerstate 永久替代。

2026-08-12 起，固定复活点团队模式以 CODOL 的正式 gametype 名 `cha` 进入 production source。`assets/game_scripts/gametypes/cha.lua` 在 `player_killed` 后请求 3000 ms 延迟复活，并激活 `cha/airdrop_pallet` gameobjects；脚本只拥有模式策略，受控 `method:respawn` builtin 验证目标确实是已死亡的 `Playing` 玩家，实际状态重置继续走 `SV_ClientSpawn`。SD source 不调用该 primitive，保持单生命边界，等待 round owner 统一复活。Lua source 的离线加载、事件注册和 builtin 合同已有回归，尚无自然多人死亡/复活证据；CHA 计分、时限、半场和胜负仍未实现。

## 当前 CODOL 证据

游戏目录静态扫描未发现 loose `.gsc/.csc/.cas`。现有 362 个 IFS 包中有 88 个 `ff_*` 和 274 个 `lf_*`，文件名可见 `ff_init_common_gametype_mp`、`ff_init_mp_crash_tropical` 以及 MP、coop、survival、zombie zones；这些名称只证明 container/zone 存在，不证明客户端仍携带完整服务端脚本。旧 `Ayria_/Assets/Alwaysoffline` 下的 3 个 loose `ffotd` 文件不是当前 GSC 输入。

活动 CODOL 客户端共有 46 种 XAsset，`rawfile` 为 type `36`。类型表没有 BO2 的 `scriptparsetree`，也没有 Ghosts 的 `scriptfile`，因此不能直接套用较新 COD 的 ScriptFile dumper。客户端若保留脚本，当前最可靠入口是 `RawFile`。

CODOL-local i64 已确认以下入口：

- `g_assetNames = 0x00CE0EA0`；
- `DB_FindXAssetHeader = 0x0049E7D0`；
- `DB_GetAllXAssetOfType = 0x0049ED90`；
- `DB_GetRawBuffer = 0x004A1620`。

`DB_GetAllXAssetOfType` 自行取得 DB hash 读锁并遍历 80000 个 bucket。该构建未发现 BO1 形式的 callback `DB_EnumXAssets`；等价的批量入口把输出 `XAssetHeader *` 放在 `EDI`，type 作为唯一栈参数，可先用空输出取数量、再填充数组。`RawFile` 为 CODOL-local 16-byte layout：

```cpp
struct RawFile {
    const char* name;      // +0x00
    int compressedLen;     // +0x04, 0 means buffer is already plain
    int len;               // +0x08, excludes trailing NUL
    const char* buffer;    // +0x0C
};
```

上述 `RawFile` partial struct、两个 DB 函数名和已确认原型已写入 CODOL 主 i64；类型应用后全库 `force_recompile` 为 `32971/32971`，重新反编译能直接显示 `rawfile->compressedLen/len/buffer` 与 `assets[v2]`，并已保存数据库。

`DB_GetRawBuffer` 使用 `ECX=RawFile*`、栈上传入 destination/capacity，并按上述长度复制或解压。`tools/runtime/CodolXAssetDump.py` 已封装两个最小 x86 thunk，使用原生 DB 锁和解压逻辑，先输出完整 RawFile manifest，再默认只导出 `.gsc/.csc/.cas` 候选；`--all` 可把当前 pool 的全部 payload 直接落盘。工具不写 asset pool，不修改 FF/IFS，并用 `DB_FindXAssetHeader(..., allowCreateDefault=0)` 将枚举到的名称解析到当前 active override；dumped payload 记录 SHA-256。`CodolXAssetManifestDiff.py` 可离线比较两份 manifest，忽略进程地址和枚举下标，只按名称、长度、压缩长度和已有 payload hash 报告 added/removed/changed。

`CodolRawFileClassify.py` 对已落盘 payload 做纯离线内容分类，不依赖后缀。报告记录前 32 bytes、Shannon entropy、ASCII/Unicode printable ratio、已知 magic、文本语法特征和 hash 一致性，并区分 `gsc_source`、`known_compiled_gsc_magic`、`engine_script_text`、`other_text`、`binary`、`empty`。已知 compiled header 当前只采用 `80 47 53 43 0D 0A 00 <version>`；未命中该 magic 或被列为未知二进制都不能证明不是 CODOL 私有脚本格式。

2026-08-03 的 `client-native-forced` 首轮运行已经完成：大厅枚举 `348` 个 RawFile，局内 `mp_crash_tropical/sd` 枚举 `376` 个，两次均无 metadata 错误。大厅只出现 `maps/mp/mp_ui_viewer_fx.gsc` 和 `maps/createfx/mp_ui_viewer_fx.gsc`；局内替换为 `maps/mp/mp_crash_tropical_fx.gsc` 和 `maps/createfx/mp_crash_tropical_fx.gsc`。四个 payload 均由 `DB_GetRawBuffer` 解压为可直接阅读的 GSC source，而非 bytecode。局内相对大厅新增 `37`、卸载 `9` 个 RawFile；新增项包含地图 FX GSC、animlist、vision、const baseline 和 zone marker，但未出现 `sd.gsc`、`_globallogic.gsc`、`_callbacksetup.gsc`、`_class.gsc` 或 `_weapons.gsc`。

这说明当前已加载的客户端 zone 保留地图 FX source，却没有暴露典型 authoritative gametype 脚本。结论只覆盖运行时 asset pool：它强烈支持“服务端 gameplay GSC 已从客户端裁剪”，但不能证明这些文件在尚未扫描的 IFS/FF 中绝对不存在。

同一局内状态的全部 `376/376` RawFile payload 已直接 dump 到 `.runtime/xassets/20260803_mp_crash_tropical_sd_all_rawfiles/files/`。内容分类得到 `2 gsc_source + 2 engine_script_text + 340 other_text + 14 binary + 18 empty`。两个非 GSC 后缀脚本是 `mp/playeranim.script`（76967 bytes）和 `mp/playeranim_defines.script`（1506 bytes），属于 `ANIMATIONS/STATE/DEFINES` Character Animation Script DSL，不是 GSC VM source。14 个二进制均由头部归为 3 个 Scaleform `GFX` 和 11 个 `IWCB000` const baseline；没有命中上述已知 compiled GSC magic，也没有剩余未知 magic 二进制。`.atr` 与 `.animlist` 是可读动画名清单，但未表现出 GSC 或 player animation state DSL。此扫描提高了当前加载集的覆盖率，仍不能排除其他 zone、FF 内部未加载 asset 或尚未知的 CODOL bytecode header。

地图 FX source 的消费链已经闭环。`CG_StartClientSideEffects 0x00435F60` 构造 `maps/mp/%s_fx.gsc` 与 `maps/createfx/%s_fx.gsc`；`CG_LoadClientEffectMapping_FastFile 0x00435E20 -> CG_ParseClientEffectMapping 0x00435B00` 解析 `level._effect/loadfx` 映射，`CG_LoadClientEffects_FastFile 0x00435920 -> CG_ParseClientEffects 0x00435740` 解析 createfx entity 文本。CODOL 控制流与 KisakCOD `cg_client_side_effects_mp.cpp` 逐项吻合，证明 `.gsc` 在这里是客户端表现数据的命名，不代表进入 GSC VM。

对 CODOL 当前 EXE 做 raw byte 搜索只得到上述两处 `.gsc\0`，没有 `.csc/.cas`、`%s.gsc`、`Scr_LoadScript`、`Scr_AddSourceBuffer` 或 `ScriptCompile`。全部 `528` 个 `DB_FindXAssetHeader` code xref 中，只有 `25` 个调用点在调用前直接压入 RawFile type `36`；这些调用点已全部归入 animation DSL、animlist/animtree、FX、vision、cfg/CSV/JSON/GFX 等专用消费者，没有通用 GSC reader。BO1 `Scr_ReadFile_FastFile` 的结构蓝本会显式查 RawFile type、识别 `.gsc/.csc` 并解压 source；CODOL 未发现同构入口。当前最合理结论是客户端通用 GSC compiler/VM 已被裁剪，除非后续 IFS/FF 或间接 wrapper 证据推翻；此前从跨 i64 污染的 strings cache 得到的 `cscr_*.cpp`/VM 错误串已经撤销。

BO1 server i64 的 builtin resolver 已形成可重复生成的直接绑定矩阵：12 张 function/method 表共 1328 个原始注册、1165 个唯一 `kind:name` binding。绑定以 `name* -> handler* -> type/reserved` 的 12-byte 表项和 resolver xref 为证据，不靠字符串推断；server method 顺序为 player、script entity、vehicle、HUD、helicopter、actor、generic。CODOL 客户端未发现对应 VM resolver，因此其同名字符串只作 locator，不能判定 native 存在。authoritative builtin registry 已开始在 `ol_game_server` 落地：`method:getvelocity/isonground/setweaponammoclip/setweaponammostock` 共用 VM 无关的 value/object/error contract，只读或受控修改 server world；客户端保留的 Pmove、prediction、weapon selection 和表现链仍只作为状态消费者。

## C++、脚本与逆向工具边界

IW3/IW4/BO1/BO2/Ghosts 等参考实现首先用于恢复框架职责：识别哪些状态必须由 C++ authoritative core 持有，哪些算法需要和客户端 prediction/wire 严格同构，哪些 mode、spawn、perk、damage/death/respawn 与 match lifecycle 适合由脚本编排。随后以该边界反查 CODOL 的 xref、descriptor、wire bytes 和运行行为，避免漏掉客户端已经消费的 C++ 字段或把 engine primitive 重写进脚本；参考游戏不能替代 CODOL 证据。

开发链分为三层：Frida 负责动态发现、ABI 验证、只读 trace 与一次性 hook；`ol_game_server` C++ 负责稳定的 `EngineBindings`、协议、authoritative world 和受控 builtin registry；Lua/GSC 一类 VM 只负责 gameplay orchestration。脚本不能获得“任意 EXE 地址调用”、LuaJIT FFI、任意内存读写或通用 hook 后门，因为这种接口会把玩法绑定到客户端 build 地址、线程、ABI 和生命周期，并把临时逆向结论变成长期依赖。Frida 中重复验证且边界稳定的能力，应提升为有类型、有所有权、有错误契约和测试的 C++ builtin，再开放给脚本。

Lua 作为近期 server-side gameplay VM 里程碑推进，不再等待客户端 IFS/FF 全量索引才验证脚本链路。当前已选定官方 Lua `5.4.8` static 与薄 C API adapter：语义稳定、x86/MSVC 支持明确、可直接约束标准库，并能无损复用现有 `ScriptValue/ScriptObjectRef/ScriptBuiltinRegistry`。LuaJIT 的 Lua 5.1 语义和 FFI 会扩大任意地址/ABI 暴露面，不作为默认；当前也没有引入 `sol2` 或 Luau，因为最小 C adapter 已足以闭环且没有证据表明额外框架能降低总复杂度。

Lua 基线已完成 VM generation、内存 text source、现有 `kind:name` builtin adapter、脚本名/traceback/结构化 `print` 日志、`undefined -> nil`，以及 source size、allocator memory、instruction budget。标准库不开放 `package/io/os/debug/load/dofile/loadfile`，也没有 FFI、lightuserdata、文件系统或任意地址入口。`ServerCore` 现持有 VM，在 world 的 `beginFrame/clientThink/endFrame` 完成后派发 `ClientSpawned/ClientDisconnected/WeaponSwitchStarted` 到 `codol.on` callback；`PlayerDamage` 的强类型 callback 已接到普通非穿透玩家命中，受控 `finishplayerdamage` 可完成非致死 mutation，或原子提交普通未链接玩家的 partial `player_die` 并在下一帧派发带 attribution 和原生动画时长的 `PlayerKilled`。延后一帧只为避免当前 Lua event span 在 builtin 内扩容失效，不改变死亡状态的同帧提交；reset/换图会清空 deferred event。独立 authoritative `SvTeam` 由背包/menu 请求暂存并在 loadout 成功时原子提交，world 与只读 `method:issameteam` 只消费已提交值；视觉 `SvCharacterFaction` 不承担 team ownership，`None` 不视为同队。common callback 现按经典 `0=无伤害/1=目标全伤/2=攻击者半伤/3=双方半伤` 编排，mode 3 通过受限 `finishsharedplayerdamage` 将两个目标一次验证后原子提交；SD 当前显式默认 `0`，但 playlist/game-rule 来源和 native no-protection/特殊 producer 豁免仍待恢复。`ClientImpacts` 另走专用即时 ABI：command commit 与 collision relink 后、entity handler 前，按 source-then-target 调用 `codol.on("entity_touch", function(receiver, other, event) ...)`；镜像 pair 非法或试图从通用 world-event ABI 派发会在任何 callback 前拒绝。换 gamestate 或禁用 server 会销毁旧 generation，callback 错误保留结构化 traceback且不打断 server frame。

production loose source loader 已接入 world-spawn 边界：从 EXE 根目录下固定的 `Ayria/Assets/OlMod/GameScripts` 依次组合可选 `common.lua`、`gametypes/<gametype>.lua`、`maps/<map>.lua`，map/gametype 复用严格 ASCII booking 名称约束，单文件与组合 source 都受 VM 总大小上限限制；Lua 本身没有路径参数和文件 API。源码缺失、读取失败、编译失败或运行失败均写入 `CodolGameServer.log`，失败 generation 会重新恢复“所有带标签 brush inactive”的保守状态。`function:setmapgameobjects` 是首个 map/gametype builtin：只接受最多 32 个非空、最长 64-byte 标签，以空白分词做 exact token 匹配，一次校验、一次提交，普通无标签 brush 始终 active。首个 `assets/game_scripts/gametypes/sd.lua` 按 IW4/BO2/Ghosts `_gameobjects.gsc` 的职责使用 `sd/bombzone/blocker/airdrop_pallet` allow-list；标签列表属于脚本，C++ 不含模式特判。项目脚本由分发 manifest 以 `replace` 安装，启动日志记录 source、generation、文件顺序以及 total/tagged/active brush 数。

地图 Lua 还可返回一个受限 metadata table；当前唯一字段是 `minimap_material`。该声明只选择地图 compass material，不保存角点、north yaw 或 wire index：这些 authoritative 数据继续由 C++ 从 native configstring 与真实 MapEnts 计算并原子提交。metadata reader 使用独立、无标准库 Lua state，并限制 source 大小、VM 内存和执行指令数；存在但损坏、超限或无限循环的地图文件会 fail closed，不会让 dedicated 无界等待。`mp_crash_tropical.lua` 声明 CODOL 自身资产 `compass_map_mp_crash_dlc`；`mp_nuked.lua` 声明的 `compass_map_mp_nuked` 又由 CODOL `lf_init_mp_nuked_V3.ifs` 文件表中的同名 `.iwi` 直接确认。两者都不复制地图坐标；Nuketown 当前只有静态资产与离线 metadata 证据，仍待自然进图截图。

自然 run `.runtime/natural-match/20260810_lua_gametype_owner_v2/` 已闭合 production loader：dedicated 记录 `generation=1`、`files=gametypes/sd.lua`、`brushModels=185 taggedBrushModels=28 activeBrushModels=161`，脚本 `print` 同 generation 排出；保守基线仍明确为 157 active，说明 4 个 SD allow-list brush 由脚本而非 C++ 特判激活。`custom3` 出生并完成 2 秒前进，最终 authoritative commandTime `6841/6841`、think failure `none/0`；客户端 snapshot/playerstate parser `100/100`、零 overflow/`Com_Error`。唯一 server ingress reject 是建连前非 CODOL packet。没有 source 时 touch consumer 保持 inert。C++ 继续持有 Pmove、prediction 对称算法、weapon timer、snapshot/wire、collision、entity primitives 和资源所有权；Lua 负责编排 `ClientSpawn`、gametype、perk、damage/death/respawn 与 match lifecycle。

受控脚本线程调度现已补齐第一阶段：`codol.thread(function)` 创建由当前 VM generation 强持有的 coroutine，`codol.wait(milliseconds)` 只接受 `0..86400000` 的整数，并以 authoritative `serverTime` 计算唤醒时刻。调度器只在 `world.beginFrame` 之后、处理新 client command 之前恢复线程；`wait(0)` 因而明确表示下一 server frame，不会在同一调用栈递归恢复。每个 generation 默认最多挂起 256 个线程、每帧最多恢复 64 个，每次启动或恢复仍受独立 instruction budget；callback 可以跨帧等待，异常保留 source traceback且只终止当前线程。`reload/reset` 通过销毁整个 Lua state 一次性撤销旧 generation 的 callback、registry reference 和挂起线程。当前尚缺通用 game notify、对象生命周期取消和 GSC `endon` 等价语义；因此调度器已经足够承载不绑定对象销毁的有限模式时序，但还不能宣称具备完整 COD 脚本线程模型。

上述最后一句是目标边界，不是当前覆盖率声明。现有 `sd.lua` 只激活 `sd/bombzone/blocker/airdrop_pallet` 并选择友伤默认值；`common.lua` 接管 `player_damage -> finishplayerdamage`，`cha.lua` 仅实现击杀计分和 C++ queue 驱动的延迟复活。SD 的 round/bomb/use/score/timer/side-switch/objective/sound orchestration 目前仍集中在 `ServerCore` C++，这是通用 notify、`endon` 和对应 typed builtin 尚未恢复时的过渡 owner。2026-08-16 的 `scr_sd_timelimit` 被误当整场全局时限、导致第三回合无法结算，正说明模式策略长期留在 C++ 容易偏离 IW4/BO1/Ghosts 的 GSC 职责。迁移时保留 C++ 的 server frame、定时调度、trigger/contact、generation-safe entity、Pmove、damage、snapshot/wire 和原子 mutation primitive；下一步补 notify/对象线程取消及 round/bomb/objective/sound builtin，再按参考 GSC 的函数边界逐块迁移 SD 编排，并让同一组 C++ 回归约束迁移前后结果。迁移完成前，现有 C++ SD owner 仍是 production 权威实现，不能一边保留自动执行、一边再让 Lua 重复结算。

详细函数证据与参考差异见 [`../research/codol_gsc_recovery.md`](../research/codol_gsc_recovery.md)；完整 builtin 清单、corpus 限制和 P0 实现分层见 [`../research/codol_builtin_recovery.md`](../research/codol_builtin_recovery.md)。

## 六阶段恢复计划

1. **清点与导出**：大厅与 `mp_crash_tropical/sd` 的 RawFile inventory、当前局内 pool 全 payload dump、内容分类和两阶段 diff 已完成。下一步扩展到 IFS/FF 离线全量索引，并继续按 zone 来源保存名称和 hash；只有全量结果才能把“未加载”与“客户端包中已删除”分开。
2. **反编译与编译**：从 IFS/FF 全量索引确认是否存在 server script source/bin，再记录实际 magic、header、endianness、string/function tables 和 checksum。优先复用或扩展 `gsc-tool` 或 COD server VM/compiler，但兼容性必须由实际 CODOL script bytes 和行为校验，不因语法看似 IW4/BO1 就宣布兼容。若客户端包确实不含 server script bin，则以需要恢复的 CODOL gameplay source、已提取 BO1 binding contract 和选定 VM 定义最小 round-trip，而不是伪造一个不存在的客户端格式。
3. **加载与快速重载**：authoritative gameplay script 由 `ol_game_server` 的 server frame、spawn、notify 和 match lifecycle 承载，不要求 CODOL 客户端加载 server script。VM、builtin adapter、受控 thread/wait 调度、spawn/disconnect、即时 entity-touch dispatch、generation reset、受控 loose source loader、map/gametype 选择、生产日志出口与首个自然实机闭环均已完成；下一步按 gameplay 需要补通用 notify、对象生命周期取消/`endon` 与其他模式 source。退回大厅或重新进图时销毁旧 generation 后重建 VM，不在活跃 VM 中原地替换 bytecode，因为旧 handle、string table 和协程可能引用旧内存。FF/IFS 只用于提取原始证据或最终需要兼容官方资产时的可选输入，不再把修改客户端 FF/IFS 当作 server 脚本开发前置条件。
4. **完整输入集**：前三阶段稳定后，接收并索引用户从全部 IFS/FF 提取的 GSC bin，保留 zone 来源和 hash，避免不同版本或同名 override 混淆。
5. **职责差分**：以 CODOL 文件清单为主键，对比 IW3/IW4/BO1 及后续同架构 COD，形成通用脚本、mode 脚本、server-only 缺失和 CODOL 特有功能矩阵。参考优先级由具体函数/格式相似度决定，不固定只看一个游戏。
6. **按需恢复 gameplay**：先补玩家生成、模型、操作、perk 和地图通用初始化，再补 TDM、SD、固定复活点团队模式；每一步都通过 authoritative server 状态、client parser 和局内行为共同验证，随后再扩展 damage/death/respawn 与 match completion。

## 验证与边界

首轮 `lobby` 和 `mp_crash_tropical_sd` 清单已保存在被 Git 忽略的 `.runtime/xassets/`。后续差分仍必须区分“未加载”“客户端被删除”“存在于未扫描 zone”三种情况；单次 asset pool 缺失不能直接推断文件不存在。地图 FX 已确认为专用客户端文本解析链，不是通用 compiler 入口；下一步准备提取 IFS 内全部 FF 离线索引，并据真实资产覆盖率选择 server-side VM/compiler，不应无证据在客户端补造脚本 VM。

每个最小脚本测试需要记录：输入 source/bin hash、编译器版本、加载入口、zone/map/gametype、VM generation、function handle、执行/notify 证据和退出后的资源状态。需要人工判断玩法语义时再请用户测试；文件清点、格式识别、差分和 crash/日志收集应自动化。

## 参考资料

- `E:/Source/Repos/CoD4-Mod-Tools/raw`：官方 IW3 source 和基础脚本职责参考；
- `E:/codol_research/ref/COD-GSC-Source`：多代 COD 脚本归档，需核对来源和反编译质量；
- `E:/codol_research/ref/GSCLSP`：语法和编辑支持参考；
- `E:/codol_research/ref/gsc-tool`：反编译、编译和格式实现参考；
- `E:/codol_research/ref/Jekyll`：不同代 ScriptParseTree/ScriptFile dump 方法参考；
- `E:/codol_research/iw4x-client`：loose script discovery 与 gametype lifecycle 结构蓝本；
- `E:/codol_research/IW4`：IW4 配置和脚本内容对照。

参考游戏只提供结构蓝本；函数名、结构体和格式最终以 CODOL i64、xref、实际 RawFile bytes、loader 行为和运行证据为准。
