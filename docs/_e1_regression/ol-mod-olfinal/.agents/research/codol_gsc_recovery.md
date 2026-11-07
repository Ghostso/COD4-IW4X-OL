# CODOL GSC 恢复证据记录

## 2026-08-03 初始调查

### 静态容器清单

目标目录为 CODOL 3.3.3.3 QA build。扫描结果为 0 个 loose `.gsc/.csc/.cas`、362 个 `.ifs`（88 个 `ff_*`、274 个 `lf_*`）和 3 个旧 Alwaysoffline `ffotd` loose `.ff`。IFS 名称包含 common gametype、具体 MP 地图以及 coop/survival/zombie zone，但尚未逐包提取内部 XAsset，不能据文件名推断服务端 GSC 是否存在。

### XAsset 类型边界

`g_assetNames` 位于 `0x00CE0EA0`，共 46 项；`rawfile` 是 type `36`。未观察到 BO2 `scriptparsetree` 或 Ghosts `scriptfile` 类型。`RawFile` size handler 对 type `36` 返回 `16`，name handler 读取 header 指针所指结构的首个 dword。

`0x004A1620` 的 CODOL-local 控制流进一步确认：

- `+0x08` 是 plain length，调用方容量使用 `len + 1`；
- `+0x04 == 0` 时从 `+0x0C` 复制 `len + 1`；
- `+0x04 != 0` 时把 `+0x0C` 和 compressed length 交给 inflate 链，并向 destination 输出 `len` bytes 后补 NUL。

因此当前 RawFile 结构与 IW4 常见布局一致，但该结论来自 CODOL 本体，不是从 IW4 直接移植。

### 原生批量枚举入口

BO1 server PDB 中存在：

```cpp
void DB_EnumXAssets_FastFile(
    XAssetType type,
    void (*callback)(XAssetHeader, void*),
    void* data,
    bool includeOverride);
```

它遍历 hash、调用 callback，并可沿 `nextOverride`。BO1 还存在 `DB_GetAllXAssetOfType_FastFile(type, assets, maxCount)`。

在独立 CODOL idalib session 中复核 DB hash table `0x01BC9F20` 的 `66` 个直接 xref 后，没有发现 callback 形式的通用 enum。`0x0049ED90` 是保留的 `DB_GetAllXAssetOfType` 等价入口：

```text
EDI = optional XAssetHeader output array
[ESP+4] = XAssetType
EAX = matching asset count
```

它调用 `0x004040B0(&0x021F7DB4)` 获取 DB hash 读锁，遍历 80000 buckets，按 28-byte `XAssetEntry` 的 type `+0`、header `+8`、nextHash `+20` 收集结果，最后 `InterlockedDecrement` 解锁。它不接受 maxCount，也不沿 `nextOverride`。调用方必须先传 `EDI=0` 取数量，再预留足够数组；dumper 额外留出增长空间，并按名称调用 `DB_FindXAssetHeader(type=36, allowCreateDefault=0)` 取得当前 active header。

两个本体调用点验证了 ABI：`0x004553A0` 把本地数组放入 `EDI`、栈上传 type `0`；`CCS_InitializeConstantConfigStrings 0x005850B0` 对 type `44` 使用同一入口并排序返回 headers。

`RawFile`、`DB_GetAllXAssetOfType` 和 `DB_GetRawBuffer` 的稳定名称与原型已经写入 CODOL 主 i64。全库 Hex-Rays cache 刷新 `32971/32971` 成功并保存；刷新后 caller 与目标函数能按字段名和 register ABI 反编译，未对尚不明确的 `XAssetEntry`/override layout 添加猜测类型。

### 当前 dump 实现

`tools/runtime/CodolXAssetDump.py` 不复制内部 hash traversal。Frida 在独立 executable page 建立两个 32-bit thunk：

- cdecl wrapper 把 Python/JS 的 output 参数转移到 `EDI` 后调用 `0x0049ED90`；
- cdecl wrapper 把 RawFile 参数转移到 `ECX` 后调用 `0x004A1620`。

manifest 总是包含当前所有 RawFile metadata；默认 payload filter 为 `*.gsc/*.csc/*.cas`，也可 `--list-only` 或 `--all`。输出路径经过 Windows reserved name 和 traversal 清理，单文件默认限制为 64 MiB，payload 记录 SHA-256。`CodolXAssetManifestDiff.py` 离线比较 manifest，不把 header/buffer 地址或枚举 index 的进程差异误报为 asset 变化。

`CodolRawFileClassify.py` 离线读取 manifest 指向的全部 payload，不用扩展名决定脚本类型。它记录首部 bytes、entropy、printable ratio、encoding、known magic、文本语法特征与 SHA-256 一致性。当前已知 compiled GSC header 来自 gsc-tool 覆盖的较新格式：`80 47 53 43 0D 0A 00 <version>`；未命中只表示不属于这个已知 header，不能排除 IW4/CODOL 世代私有格式。

### 大厅与局内运行结果

2026-08-03 使用同一活动客户端完成两次 `client-native-forced` dump。结果目录只保存在 `.runtime/xassets/`，仓库文档记录可复核摘要：

| 状态 | RawFile | GSC source | metadata error |
| --- | ---: | ---: | ---: |
| lobby | 348 | 2 | 0 |
| `mp_crash_tropical/sd` | 376 | 2 | 0 |

大厅文件：

| 名称 | bytes | SHA-256 |
| --- | ---: | --- |
| `maps/mp/mp_ui_viewer_fx.gsc` | 1080 | `0AE3197EB630C73A4C90D7EC7A8A7AEBC6AC6F960403135F1BC09DF55CBA4A9E` |
| `maps/createfx/mp_ui_viewer_fx.gsc` | 2519 | `0CC749723686E74B089A3BBC14C3DA146CD67B187740959D9C7AEC4407E2F4BD` |

局内文件：

| 名称 | bytes | SHA-256 |
| --- | ---: | --- |
| `maps/mp/mp_crash_tropical_fx.gsc` | 1292 | `06619DC58C9C894D24CA50B0E34AAE1BA61843227EDD256D1999A98EDC598AB8` |
| `maps/createfx/mp_crash_tropical_fx.gsc` | 32942 | `13C2628FC3D342B220EAF451A7A77602157700194D279671655731A82911C844` |

四个文件都是本体解压得到的可读 GSC source。局内相对大厅 added `37`、removed `9`；新增项包括地图 FX GSC、`common_dog/mp_crash_tropical` animlist、地图 vision、多个 gametype const baseline 和零长度 zone marker。未观察到 `sd.gsc`、`_globallogic.gsc`、`_callbacksetup.gsc`、`_class.gsc`、`_weapons.gsc`。这证明当前客户端加载集合主要保留地图表现所需 source，不能仅凭运行池继续声称未扫描 IFS/FF 中绝对没有 server gametype scripts。

### 全 payload 内容扫描

随后在同一局内状态使用 `--all` 将 `376/376` 个 payload 直接保存到 `.runtime/xassets/20260803_mp_crash_tropical_sd_all_rawfiles/`，总量约 14.15 MiB，没有 dump error。离线分类结果如下：

| 内容分类 | 数量 | 结论 |
| --- | ---: | --- |
| `gsc_source` | 2 | 两个 `mp_crash_tropical_fx.gsc` source |
| `engine_script_text` | 2 | `mp/playeranim.script` 与 `playeranim_defines.script` 动画 DSL |
| `other_text` | 340 | vision、cfg、rmb、atr、animlist 等可读数据 |
| `binary` | 14 | 3 个 Scaleform `GFX`、11 个 `IWCB000` const baseline |
| `empty` | 18 | zone/asset marker |

`playeranim.script` 为 76967 bytes，以 Character Animation Script 注释和 `ANIMATIONS/STATE` grammar 组织；`playeranim_defines.script` 为 1506 bytes，以 `DEFINES` 和 `set ... = ...` grammar 组织。它们会影响角色动画状态选择，但不是 GSC VM source，不能当作缺失 gametype server logic。24 个非空 `.atr` 与 3 个 `.animlist` 主要是动画名和分组清单，未命中这两种脚本 grammar。

14 个二进制的 magic 均已解释，没有命中 `80 47 53 43 0D 0A 00 <version>`，也没有遗留未知 magic 二进制。这个结果只说明当前 loaded RawFile pool 中没有额外高置信 GSC/compiled-GSC 候选；未知 CODOL header、嵌在其他 XAsset 类型中的脚本、未加载 zone 和 IFS/FF 中未索引内容仍是开放边界。

### 地图 FX consumer 与客户端 compiler 边界

从两个实际路径的当前 CODOL xref 出发，确认以下链路：

- `CG_StartClientSideEffects 0x00435F60` 构造 `maps/mp/%s_fx.gsc` 与 `maps/createfx/%s_fx.gsc`；
- `CG_LoadClientEffectMapping_FastFile 0x00435E20 -> CG_ParseClientEffectMapping 0x00435B00` 读取 RawFile 后只识别 `level._effect[...] = loadfx(...)`；
- `CG_LoadClientEffects_FastFile 0x00435920 -> CG_ParseClientEffects 0x00435740` 读取 RawFile 后只识别 createfx 生成的 entity/effect/sound 文本。

这些函数的控制流、职责与 KisakCOD `src/cgame_mp/cg_client_side_effects_mp.cpp` 一致。CODOL 版本增加了本体 `DB_GetRawBuffer` 解压和额外 createfx grammar，但仍是专用文本解析器，不生成 parse tree、不查 function handle、不执行 script thread。

为避免依赖字符串表，进一步直接扫描 CODOL IDB bytes：整个 EXE 只有两处 `.gsc\0`，就是上述两个格式串；没有 `.csc/.cas`、`%s.gsc`、`Scr_LoadScript`、`Scr_AddSourceBuffer`、`ScriptCompile`、`clientscripts` 或 `script_loading`。枚举 `DB_FindXAssetHeader 0x0049E7D0` 的全部 `528` 个 code xref，并读取每个 call 前 24 bytes 后，只有 `25` 个调用点直接压入 type `36`。逐函数归类覆盖 animation script、animlist、animtree、client FX、vision、shock、cfg、CSV、JSON、GFX、const baseline 等，未发现通用 GSC reader。

BO1 PDB 的 `Scr_LoadScriptInternal -> Scr_AddSourceBuffer -> Scr_ReadFile_FastFile` 用作结构对照：它明确构造 `%s.gsc/%s.csc`、以 RawFile type 读取 source，并按 GSC/CSC 特殊格式解压后进入 parser/compiler。CODOL 没有相应字符串、立即数 RawFile caller 或 BO1 函数签名匹配。该负证据不能绝对排除间接 wrapper 或完全不同的 compiled asset，但与缺失专用 script XAsset type、运行 pool 缺失 server scripts 共同支持“客户端通用 GSC compiler/VM 已裁剪”。

调查中还确认 idalib-mcp 的跨 IDB strings cache 会污染结果：切换到 BO1 后，CODOL `find_regex` 曾返回 BO1 `cscr_*.cpp` 字符串及相同地址；直接读取 CODOL 对应地址得到零或无关 bytes。所有这类结果已撤销，以上结论只使用 `server_health` 确认的 CODOL IDB、`get_bytes/find_bytes`、当前 xref 与反编译。此失败模式已写入项目必读规则。

### 脚本职责粗对照

同日按本地参考目录清点 `.gsc`：IW3 Mod Tools `894`（gametype `40`、createfx `47`），用户提供的 IW4 目录 `1479`（`50/61`），BO2 archive `2364`（`60/58`），IW6 archive `1722`（`62/74`）。这些版本都能看到 `_callbacksetup/_class/_globallogic/_weapons` 及 `sd/dm/war` 等典型职责链。BO1 archive 的目录布局和覆盖率不同，路径统计为零不能解释为 BO1 没有 gametype scripts。

### 残留脚本痕迹

当前四个可读 `.gsc` 中包含 `#include common_scripts\\utility;`、`#include common_scripts\\_createfx;` 和 `codescripts/$default` 等 createfx 文本，但客户端只通过 `maps/mp/%s_fx.gsc` 与 `maps/createfx/%s_fx.gsc` 两个固定格式串读取它们。`CG_ParseClientEffects 0x00435740` 是该文本的专用消费者，不生成 GSC source，也不是通用 compiler/parser 入口。只有后续 IFS/FF 索引发现新的 script source/bin 或独立 loader 证据时，才重新评估客户端脚本能力。

### 参考格式差异

Jekyll 的 BO2 `ScriptParseTree` 常见字段为 `name/len/buffer`；Ghosts `ScriptFile` 常见字段为 `name/compressedLen/len/bytecodeLen/buffer/bytecode`。CODOL 的资产类型表没有这两种专用 pool，因此当前 dumper不能读取这些结构。

IW4x `GSC/Script.cpp` 展示了 loose source discovery、`main/init` handle 和 gametype lifecycle 的结构蓝本，但它依赖游戏本体已有 `Scr_LoadScript` 与 server VM。当前 CODOL 客户端没有这组入口，因此只能参考其模块边界，不能直接复用客户端调用路线；authoritative loader、compiler/bytecode contract、builtin/notify 和 VM lifecycle 应在 `ol_game_server` 中恢复，并由实际 CODOL script bytes 或服务端行为约束。

## 待验证

1. 对 IFS 内全部 FF 建立离线 asset index，补足运行时未加载 zone，并保留 container/zone/hash；
2. 若发现 server script source/bin，记录真实 header、tables、checksum 和 loader ownership；若未发现，则明确以服务端 gameplay contract 选择 VM/compiler 基线；
3. 在 `ol_game_server` 做无副作用最小 compile/load/execute round-trip，优先 loose source/bin，并在退回大厅或重新进图时重建 VM；
4. 接通 function handle、thread、builtin/notify 与 server frame lifecycle 后，再恢复玩家生成和基础 gametype 脚本。
