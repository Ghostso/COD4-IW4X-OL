# CODOL 动态闭合 —— FAT 分片接手计划与现状（2026-10-24 夜）

> 接手对象：`HANDOFF_20261024_DYNAMIC_CLOSURE.md` 的首个阻断点
> （客户端从 `head=0x80000427` 起改用 FAT 分片帧，战斗服全部跳过）。
> 结论：**该阻断点在代码与离线层面已闭合**；剩下的是实机验收与出生点/计分。
> 本轮 run 目录：`run_codol_001/runs/FAT_OFFLINE_20261024_0200/`

---

## 0. 一句话

FAT 帧的真实布局已经**定死**（不是 CoD4x 那一套），重组已实现，
战斗服已接上，离线测试 **22/22 全绿**（其中 FAT 专项 7 项）。
下一步只剩"开一局实机确认 FAT 之后重新出现 USERCMD"。

---

## 1. 最重要的发现：FAT 布局既不是我们的假设，也不是三方参考的假设

之前两处都在猜，且**都猜错了**：

| 来源 | 原来的做法 | 结果 |
|---|---|---|
| 本项目 `src/netchan/netchan.c` | 照 CoD4x(IW3)：`qport + fragmentStart(4) + fragmentLength(2)` | 布局完全不对，且接收完成判据本身有 bug |
| 三方 C# `CodolLocalBattleServer.cs` | **压根没有分片处理** —— 只判 `(seq & 0xE0000000)==0`，非 0 就 `else if` 落到 `UNIMPLEMENTED` | 所以三方也过不去这里 |

**权威来源**（本机自带，离线可查）：
`_e1_regression/ol-mod-olfinal/src/game_server/qcommon/net_chan_mp.cpp`
其中 `CODREF(netchan_fragment)` 直接指向 `CODOL Netchan_Process 0x005A5960`，并写明：

> sequence flags `0x80000000` fragmented / `0x40000000` reliable /
> `0x20000000` fragment acknowledgement. Its fragment header is **index,
> last-index, 1154-byte stride and payload length**; it is **not** the older
> qport/start/length layout.

### 1.1 分片帧布局（共 10 字节头）

| 偏移 | 宽度 | 字段 | 说明 |
|---|---|---|---|
| 0 | u32 LE | 序号 \| 标志 | 序号掩码 `0x1FFFFFFF`；`0x80000000`=分片、`0x40000000`=分片且要求确认、`0x20000000`=分片确认包 |
| 4 | u8 | `fragmentIndex` | 本片下标（从 0） |
| 5 | u8 | `lastFragmentIndex` | 末片下标 |
| 6 | u16 LE | `fragmentStride` | **恒 = 1154** |
| 8 | u16 LE | `fragmentLength` | 本片负载字节数 |
| 10 | … | 负载 | |

关键点：**分片头里没有 serverId/qport**。分片切的是「序号之后的整条消息」，
而 `serverId(1) + messageAck(4) + reliableAck(4)` 那 9 字节**落在负载里**。
所以重组 = `u32(序号) ‖ 各片负载按 index*stride 拼接`，得到的正是
**与普通帧布局完全相同的消息**（13 字节头：serverId(1)+messageAck(4)+reliableAck(4)），
可以直接丢给现有那套解析。

### 1.2 用基线日志独立交叉验算（不依赖参照，自证）

基线 `_c_battle_out.txt` 里 seq `0x426` 还是普通帧、`0x427` 起变 FAT，数字链条自洽：

| 项 | 值 | 推算 |
|---|---|---|
| seq 0x426 普通帧 | `bytes=1153` | post-seq = 1149 **< 1154 ⇒ 不分片** |
| seq 0x427 大包 | `bytes=1164` | fragmentLength = 1164−10 = **1154 = stride**（index 0，满片） |
| seq 0x427 小包 | `bytes=20` | fragmentLength = 20−10 = **10**（index 1，末片） |
| 该消息 post-seq 长 | 1164 | 1154+10，`lastFragmentIndex=1` ⇒ **2 片** ✓ |
| 阈值 | 1164 ≥ 1154 | 正好跨过 ⇒ 从这一帧开始分片 ✓ |

另外解释了一个此前的怪现象：旧代码把 `[5..8]` 当 `messageAck` 读并 `&0x1FFFFFFF`，
于是只剩 `fragmentLength` 的**低 5 位** —— 这正是手工统计里
「`plain[8]` 低 5 位 = `(bytes−10) mod 32`」这条 24/24 规律的全部原因。
（`plain[5]=0x01` 其实是 `lastFragmentIndex=1`，`plain[6..7]=0x0482=1154` 就是 stride。）

### 1.3 交接文档 Step 1 的前提**不成立**（重要，避免后人再找一遍）

Step 1 写的是「从已有 `_c_battle_out.txt` 中提取 FAT 原始帧，确认真实布局」。
**做不到**：`RX_BODY` 原始字节转储写在 `if (!fat)` 分支里、且限前 200 帧，
而 FAT 从第 5529 帧才开始 —— 日志里**没有任何 FAT 帧的原始字节**，
只有 `head` / `bytes` / 被误读的 `ack` 三个字段。
本轮是用「ol-mod 的参照实现」+「这三个字段的交叉验算」解的，两者互相印证，
所以结论是确定的，不是猜的。

---

## 2. 已完成的改动（已编译、已测）

| 文件 | 改动 |
|---|---|
| `include/codol_types.h` | 新增 `CODOL_FAT_*` 常量块（含布局注释与 1.2 的验算）+ `codol_fat_reassembler_t`（128 位收片位图 + 4+K 重组缓冲）；`codol_netchan_t` 增加 `fat` 字段 |
| `include/codol_netchan.h` | 声明 `codol_fat_receive()` / `codol_fat_reset()` |
| `include/codol_battle.h` | `codol_battle_assoc_t` 增加 `fat` 状态 + `fat_frames/fat_reassembled/fat_invalid` 计数（**按 peer 独立**，不全局共享） |
| `src/netchan/netchan.c` | 实现 `codol_fat_receive()`（边界校验 / 重复片忽略 / 乱序可收 / 收全即返回整条消息 / RELIABLE 位回分片确认）；`codol_netchan_process()` 的分片分支**从 CoD4x 布局改写成 CODOL 布局**，并删掉原来那个「把当前片结束位置当总长度」的坏判据 |
| `src/battle/battle_service.c` | 把普通帧解析路径抽成 `handle_netchan_frame()`；`handle_plain` 里 FAT 分支改为：先 `codol_fat_receive()` 重组，收全后**走同一个 `handle_netchan_frame()`**；新增日志 `RX_FAT_FRAGMENT` / `RX_FAT_REASSEMBLED` / `RX_FAT_INVALID`；密钥交换时 `codol_fat_reset()`（重连后序号回 1，残留半条消息会挡住新会话） |
| `CMakeLists.txt` | `test_static_closure` 补 `src/msg/msg.c` + `src/netchan/netchan.c`（原来没链 netchan，新增符号解析不到） |
| `tests/test_netchan.c` | 新增 FAT 专项 7 项：顺序重组 3000B 逐字节一致 / 乱序(2,0,1) / 重复片忽略 / 缺片不误判完成 / 边界（步长不符·截断·idx>last·非末片短片）全拒 / 两条连续分片消息 / 经 `codol_netchan_process` 普通帧与分片帧交替 |

**验证结果**（VS 2022 Build Tools cmake）：

```
100% tests passed, 0 tests failed out of 22
--- CODOL 3.19 分片(FAT)重组 ---
ok   FAT 顺序     3000B -> 3 片 -> 3004B 逐字节一致
ok   FAT 乱序     (2,0,1) 仍逐字节一致
ok   FAT 重复片   重复片被忽略, 重组仍一致
ok   FAT 缺片     未收全 -> 返回 0(不误判完成)
ok   FAT 边界     步长/截断/idx>last/非末片短片 全部拒绝
ok   FAT 连续     第二条分片消息独立重组正确
ok   FAT process  普通帧/分片帧交替, 重组载荷正确
```

---

## 3. 下一步（按顺序，一次只动一个变量）

### Step 5（唯一需要你在场的一步）实机验证 FAT

离线已绿，可以开 run 了。**但验收项里有"按键对应 forwardmove/rightmove 变化、
鼠标对应 yaw/pitch 变化、开火对应 FIRE"，这些必须有真人在键盘前操作**，
所以这一步我不替你跑，等你在的时候。

```bash
cd "D:\BaiduNetdiskDownload\使命召唤OL" && python -I run_codol_001\run_frozen_chain_once.py
```

（或沿用你平时那条 `run_all.py … --out <名字>.txt`。单次调用只起一个客户端，
早退不自动重启 —— AGENTS.md 的单次规则。）

判据（全部来自**同一个客户端 PID**）：

1. `_c_battle_out.txt` 出现成片的 `RX_FAT_FRAGMENT … 收全` 与 `RX_FAT_REASSEMBLED`；
2. `RX_FAT_INVALID` 应为 0 或极少（若非 0，把那一行原样贴给我，里面有 head/idx/last/stride/frag_len，能直接定位）；
3. **FAT 之后重新出现 `USERCMD`**（这是本轮的关键判据）；
4. 按 W/A/S/D → `USERCMD … F=/R=` 跟着变；
5. 转鼠标 → `yaw/pitch` 跟着变；
6. 开火 → `FIRE`；命中 → `HIT`；伤害 → `DAMAGE`。

**如果第 3 条没出现**：停下，不要继续动出生点。把 `RX_FAT_*` 三行原样发我。

### Step 6 出生点闭合（要等 FAT 可用之后）

交接文档已写明：**不能**只凭「-128 看起来更像地板」就改常量。
需要先区分「地图实体 origin 语义 / clipmap 地面 / 客户端预测位置」。
可利用的离线素材：`run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/kit/player_origin.txt`
（541 KB，是客户端内存里读出来的**真实玩家位置**轨迹）与 `player_origin_hex.txt`。
建议下一步先拿这两个文件做离线分析，再决定是否改 `CODOL_GROUND_Z`。

### Step 7 靶场目标/计分闭合

先定性靶场原生语义（有没有 score / 命中反馈 / 靶标 health / round end），
若原生不计分就记 `NO_SCORE_BY_DESIGN`，**不要伪造 DM 分数**。

---

## 4. 边界与已知不足（如实记录）

1. **普通帧路径我一行没动**（保留在原 `else` 分支里的内联代码），
   代价是同一段逻辑在 `handle_netchan_frame()` 里重复了一份。
   这是**故意的**：交接文档要求"不要回归现有已工作的 `0x00000426` 之前逻辑"。
   等实机 FAT 验收通过后再做那次清理（把普通帧也改成调用同一个函数）。
2. **服务端发送侧的分片格式没改**，仍是 CoD4x 布局。实际不触发
   （服务端消息最大也就 gamestate 259B，远小于 1154）。
3. 重组缓冲上限 `CODOL_FAT_MAX_MESSAGE = 32768`。实测消息约 2.2 KB，
   余量足够；超限会打 `RX_FAT_INVALID` 并丢弃而不是截断。
4. `RELIABLE` 分片的确认应答（`0xA0000000` 包）按参照实现写了，但**实测客户端不带这一位**，
   所以这条路径**没有实机证据**，只是对齐引擎行为。
5. 本轮**没有**启动过客户端 —— 上面的实机判据全部**未经实机验证**。

---

## 5. 受保护资产状态

`run_codol_001/runs/FAT_OFFLINE_20261024_0200/protected_preflight.json`：

| 文件 | 结果 |
|---|---|
| `run_all.py` / `nt10.py` / `lobby_server.py` / `fake_auth_tls.py` / `codol_crypto.py` / `make_local_ca.ps1` | **MATCH** |
| `battle_selftest.py` / `battle_server.py` | **MATCH** |
| `write_dwauth.py`（AGENTS.md 保护项，不在 `_golden_hashes.json` 里） | **MATCH**（与上一轮 preflight 逐位相同） |
| `marketplace_store.py` | **MISMATCH** —— 磁盘 50022B/`e44358f0…`，清单 46226B/`28b4a1be…`。**最后修改时间 2026-10-16 17:32**，即 8 天前、本轮之前就已是这个状态，不是本轮造成的。该项目自己的 `run_frozen_chain_once.py` 把 marketplace 明确列为"业务模块，永不允许阻塞启动链体检" |

**本轮没有改动 `REF_LOBBY_KIT` 下任何文件**，也没有生成证书/写运行态进去。
本轮改的 `CODOL_SERVER_319_20261021`（战斗服 C 源）不在 AGENTS.md 的保护清单里。

---

## 6. 关键文件索引

- 交接文档：`HANDOFF_20261024_DYNAMIC_CLOSURE.md`
- 布局权威参照：`_e1_regression/ol-mod-olfinal/src/game_server/qcommon/net_chan_mp.cpp`
  （及 `net_chan_mp.hpp`：`NetchanSequenceMask=0x1FFFFFFF`、`NetchanFragmentSize=1154`、
  `NetchanMaximumFragments=128`、`NetchanMaximumFragmentedMessage=0x20000`）
- 三方（**无分片处理**）对照：`CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/_extracted/reference/CodolLocalBattleServer.cs`
- 本轮代码：`CODOL_SERVER_319_20261021/{include/codol_types.h,include/codol_netchan.h,include/codol_battle.h,src/netchan/netchan.c,src/battle/battle_service.c,tests/test_netchan.c,CMakeLists.txt}`
- 本轮 run：`run_codol_001/runs/FAT_OFFLINE_20261024_0200/`
