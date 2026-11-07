# CODOL 动态闭合交接（2026-10-24）

> 交接范围：只处理**对局内动态闭合**。静态表、武器表、OLmod 兼容性不是本阶段目标。
> 最新基线：`run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040`
> 结论：`PARTIAL`。已进入对局，但尚未完成可操作、可命中、可死亡/复活、可计分的动态闭环。

## 1. 一句话结论

大厅与战斗服握手链路已打通，客户端能进入 `coop_train_mp_firingrange`；当前首要阻断是
**客户端在 `0x80000427` 之后改用 FAT/分片帧发送输入，而 `battle_service.c` 全部跳过**。
在 FAT 重组接入并通过实机验收前，不能声称动态闭合。

用户补充的两个验收项必须保留：

1. 出生点必须离开房顶，不能继续停在 `-116`。
2. 训练靶场必须按其原生目标验证；当前没有计分/命中/死亡/复活证据，不能把“能进图”算完成。

## 2. 本轮已确认事实（有证据）

### 2.1 运行与进入对局

- 客户端 PID：`17848`
- C 战斗服 PID：`19984`
- 客户端只启动一次；本轮无自动重启。
- 客户端 `gamestateupdate`：`1 -> 2 -> 3 -> 4 -> 5 -> 6`。
- 战斗服日志确认：
  - `Map: mp_firingrange`
  - `TX_GAMESTATE seq=1 state=259B`
  - `TX_SNAPSHOT` 持续到 `seq=12750`
  - 最后一次快照位置 `525.1,-1447.0,-116.0`
- 因此“进图”已成立，但不能据此推断战斗动态已成立。

### 2.2 成功形态（不要破坏）

本轮成功来自以下组合：

- `coop_map.txt = coop_train_mp_firingrange`
- Lobby 下发：
  - `map=coop_train_mp_firingrange`
  - `GameType=0x1000007`
  - `MaxPlayers=1`
- `mmstart` 使用 `map coop_train_mp_firingrange`
- C 战斗服**默认启动，不带 `--map`**，实际加载 `mp_firingrange`
- 没有 `firingrange-battle.enabled`

历史上创建该开关会让 Lobby 用 `--map coop_train_mp_firingrange` 启动战斗服，
随后客户端在 stage 1 后 `cancelConnect`。因此：

> 当前成功形态是“Lobby/mmstart 地图名”和“战斗服默认地图名”故意不一致。
> 在没有新证据前，不要强行把两者对齐，也不要重新创建 `firingrange-battle.enabled`。

### 2.3 保护资产完整性

- `protected_preflight.json` 与 `protected_postflight.json` 的 `name/size/sha256` 全部一致。
- 结果为 `MATCH`。
- 受保护资产未被本轮修改。

### 2.4 FAT 阻断的量化证据

日志：`kit/_c_battle_out.txt`

- 客户端帧头总数：`6576`
- FAT 帧头（`head & 0x80000000`）：`5514`
- 正常 usercmd 日志：`5529` 条（分布在 FAT 切换之前）
- 最后一个正常帧：`head=0x00000426`
- 第一个 FAT 帧：`head=0x80000427`
- 从 `0x427` 开始，日志持续出现：
  - `RX_CLIENT_GAME_HEADER ... head=0x8000xxxx`
  - `RX_FAT_HEADER ... (跳过 usercmd 解析)`
- 典型 FAT 包：
  - `head=0x80000427 bytes=1164`
  - 同 head 随后又有 `bytes=20`
  - 后续常见 `1164/904/692/724/...`
- FAT 段内 `FIRE/HIT/DAMAGE/DEATH/RESPAWN/SCORE/GAME_OVER` 计数全部为 `0`。

注意：同一 `head` 会出现两个不同长度、不同 `messageAck` 的包。仅按
“相同 sequence 合并”不够，必须解析分片元数据并按偏移写入。

## 3. 代码现状与问题定位

### 3.1 `battle_service.c`

文件：`CODOL_SERVER_319_20261021/src/battle/battle_service.c`

关键位置：

- `handle_plain()`：约 464 行
- FAT 判定与跳过：约 504-517 行
- usercmd 正常解析：约 520-612 行

当前代码：

```c
bool fat = (head & 0xE0000000u) != 0;
if (fat)
    CODOL_LOG_INFO("[battle] RX_FAT_HEADER ... (跳过 usercmd 解析)");
if (!fat) {
    /* 解密 body、解析 usercmd、处理 reliable */
}
```

问题：

- `0x80000000` 已被识别，但没有进入重组流程。
- 当前对 `plain` 的布局假设是普通帧：13B 头 + body。
- FAT 帧头不是这个布局，不能直接把 `plain+13` 交给 `codol_usercmd_parse()`。
- `ack` 的提取位置也只对普通帧成立；FAT 帧中出现了明显异常的 `messageAck`，
  说明不能复用普通帧字段偏移。

### 3.2 `netchan.c`

文件：`CODOL_SERVER_319_20261021/src/netchan/netchan.c`

已有发送分片：

- `CODOL_NETCHAN_FRAGMENT_BIT = 0x80000000`
- `codol_netchan_transmit()` 对超长消息分片
- `codol_netchan_transmit_next_fragment()` 写 `fragment_start` 和 `fragment_length`

已有接收框架：

- `codol_netchan_process()` 读取 `fragment_start/fragment_length`
- 将片写入 `fragment_buffer`

但**尚未接入 `battle_service`**，且现有接收逻辑有已知缺陷：

```c
chan->fragment_length = fragment_start + fragment_length;
...
if (fragment_start + fragment_length < chan->fragment_length) return false;
```

这会把“当前片的结束位置”当作“整条消息总长度”，因此只要不是最后一片就永远无法
判断完成；并且没有记录已收到的区间、没有处理重复/乱序片、没有总长度上限检查。

### 3.3 测试现状

`CODOL_SERVER_319_20261021/tests/test_netchan.c` 当前只验证：

- 普通帧线头
- 往返
- 重包丢弃
- 递增 sequence
- 发送端能发出 3 个分片

它**没有把分片喂回 `codol_netchan_process()` 验证接收重组**。
因此现有 `test_netchan` 的 `ALL PASSED` 不能证明 FAT 接收已闭合。

本轮已运行：

- `build/Debug/test_netchan.exe`：通过，但覆盖面不足。
- `build/Debug/test_static_closure.exe`：通过。
- 这两个结果只能作为回归基线，不能作为动态闭合证据。

### 3.4 出生点

相关代码：

- `battle_service.c:150`：`codol_player_init(..., 48,-572,-116)`
- `world.c:80`：实体 origin `48,-572,-116`
- `include/codol_clipmap_approx.h:10`：`CODOL_GROUND_Z (-116.0f)`
- `src/world/collision.c`：`codol_ground_z = -116.0f`
- 地图实体证据：`_map_extract/coop_train_spawns.json`
  - `info_player_start_so = 48 -572 -116`

矛盾点：

- 地图实体串确实写着 `-116`，但实机报告“出生在房顶”。
- 当前快照从 `48,-572,-116` 开始，后续位置到 `525.1,-1447.0,-116.0`，
  z 始终为 `-116`。
- 现有注释已记录地板约在 `-128..-124`，但碰撞常量仍是 `-116`。
- 因此不能仅凭实体串把 `-116` 当作“真实脚底地面”；需要区分：
  - 地图实体 origin 的语义（可能是眼位/参考点，不是碰撞地面）；
  - 当前 clipmap/ground plane 的语义；
  - 客户端预测位置与服务端快照位置。

在拿到地图真实地面 trace 或客户端预测位置证据前，不要盲改 `-116 -> -128` 后直接宣布修复。

### 3.5 训练靶场计分

相关代码：

- `world.c:31`：所有地图硬编码 `gametype = "dm"`
- `world.c:32-34`：`score_limit=30`、`time_limit=600000`、`respawn_delay=3000`
- `gamemode.c`：已有内部 `team_score`、`respawn_at_ms`、`GAME_OVER` 状态机
- `snapshot.c`：当前快照主要发送 playerState/装备/运动字段，
  没有看到客户端可见的 kill/death/score 事件消费链

需要区分三种情况：

1. **靶场原生不计分**：应验证命中反馈、靶标状态、训练目标，而不是强行显示 DM 分数。
2. **服务端内部计分但客户端不显示**：需要找到对应的 client state/event 写路径。
3. **真实多人模式计分**：需要切换到真实 multiplayer map/gametype，并实现
   `EXE_MATCHENDED`、score/death 等事件和 player/client state 更新。

Phase 6 文档已确认：

- `scoreboard` 没有独立 netField 表；
- score 数据来源是已复制的 player/client state；
- kill/death/score 属于 UI/state 渲染项；
- match state 通过事件与服务端命令传播。

因此不能通过伪造一个“scoreboard 包”来解决，必须找到状态字段和事件写路径。

## 4. 下一轮必须遵守的顺序

### Step 0：环境与完整性检查

- 确认无残留 `codoMP_client_shipRetail.exe`、`codol_battle_server.exe`。
- 确认 3074 无监听、28960 无 UDP endpoint。
- 新 run 目录：`run_codol_001/runs/<RUN_ID>/`。
- 运行前后写 `protected_preflight.json` / `protected_postflight.json` 并比较哈希。
- 单次调用最多启动一个客户端；早退后不自动重启。

### Step 1：先做离线 FAT 解码（不启动客户端）

目标：从已有 `_c_battle_out.txt` 中提取 FAT 原始帧，确认真实布局。

必须确认：

- `head` 的哪一位是 fragment 标志；
- sequence 如何从 `head` 还原；
- qport 是否存在、宽度和位置；
- `fragment_start` 的字节序/宽度；
- `fragment_length` 的字节序/宽度；
- 总长度字段是否存在，或由最后一片推导；
- 每片 payload 的 XOR 掩码是否与普通帧相同；
- 同 head 多包的关系（是分片，还是不同消息复用 sequence）。

禁止先写“看起来合理”的解析器再接实机。先让离线样本能稳定重组出
`codol_usercmd_parse()` 可接受的 body。

### Step 2：修 `codol_netchan_process()` 的接收状态

至少需要：

- 按 peer 保存重组状态，不能全局共享；
- 记录 `expected_total`（如果协议有）；
- 记录已收区间，支持乱序/重复片；
- 拒绝越界、重叠冲突、超长消息；
- 只在完整后返回 `true`；
- 完整后重置状态，允许下一条消息；
- 不要把“当前片结束位置”当总长度。

### Step 3：把 FAT 重组接入 `battle_service`

要求：

- FAT 帧先完成重组，再走普通帧同一套：
  - 可靠命令解析；
  - `codol_usercmd_parse()`；
  - `codol_equipment_step()`；
  - `codol_battle_service_apply_usercmd()`。
- 保留普通帧路径，不要回归现有已工作的 `0x00000426` 之前逻辑。
- 日志必须区分：
  - `RX_FAT_FRAGMENT`
  - `RX_FAT_REASSEMBLED`
  - `RX_FAT_INVALID`
- 记录每条重组消息的 `head/sequence/total/received/parse_result`。

### Step 4：离线测试先闭合

扩展 `test_netchan.c`：

- 发送 3000B -> 逐片喂接收端 -> 断言完整 payload 与原始 3000B 完全一致；
- 乱序片；
- 重复片；
- 缺片；
- 超长/越界；
- 两条连续分片消息；
- 普通帧与分片帧交替。

只有离线测试全绿，才允许创建新 run。

### Step 5：单客户端实机验证 FAT

新一轮只验证 FAT，不顺手改出生点或计分。

验收证据必须来自同一客户端 PID：

- FAT 重组成功日志；
- FAT 之后重新出现 `USERCMD`；
- `W/A/S/D` 对应 `forwardmove/rightmove` 变化；
- 鼠标对应 `yaw/pitch` 变化；
- 开火对应 `FIRE`；
- 命中对应 `HIT`；
- 伤害对应 `DAMAGE`；
- 死亡/复活对应 `DEATH/RESPAWN`（如果靶场原生支持）；
- 至少一条时间戳链路完整。

如果 FAT 后仍无 `USERCMD`，停止，不要继续改出生点。

### Step 6：出生点闭合

在 FAT 输入可用后再处理，因为需要区分：

- 客户端自己的预测位置；
- 服务端权威位置；
- 快照是否发送 z；
- 当前 `omit` 策略；
- 真实 clipmap 地面高度。

必须用地图 clipmap/实体数据做一次真实向下 trace，得到脚底接触面。
禁止仅凭“-128 看起来更像地板”就改常量。

验收：

- 客户端离开房顶；
- 落地后能移动、跳跃；
- 不出现穿地、橡皮筋、无限下落；
- 快照位置与客户端预测位置在可接受误差内。

### Step 7：靶场目标/计分闭合

先确定靶场原生语义：

- 是否有 score；
- 是否有命中反馈；
- 靶标是否有 health/state；
- 是否有 round/match end；
- 客户端由哪个 player/client state 字段渲染。

若靶场原生不计分：

- 明确记录 `NO_SCORE_BY_DESIGN`；
- 用命中、靶标状态、训练目标作为验收，不伪造 DM 分数。

若需要计分：

- 使用真实 multiplayer gametype/map；
- 从 `playerState/clientState` 写入 score/death；
- 接入 `EXE_MATCHENDED` 等事件；
- 验证客户端 scoreboard 和 match end。

## 5. 当前不要做的事

- 不要重新创建 `firingrange-battle.enabled`。
- 不要为了对齐地图名而修改已成功的 Lobby/战斗服组合。
- 不要在 FAT 未闭合时继续调出生点 z。
- 不要用“能进图”“快照在发”代替动态闭合。
- 不要伪造客户端计分包。
- 不要修改受保护资产。
- 不要在没有离线测试的情况下直接启动客户端试 FAT。

## 6. 关键文件索引

### 运行证据

- `run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/dynamic_status.json`
- `run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/kit/_c_battle_out.txt`
- `run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/kit/lobby_srv.log`
- `run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/chain.txt`
- `run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/protected_preflight.json`
- `run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/protected_postflight.json`
- `run_codol_001/runs/DYNAMIC_CLOSURE_MINIMAL_20261024_0040/kit_manifest.json`

### 代码

- `CODOL_SERVER_319_20261021/src/battle/battle_service.c`
- `CODOL_SERVER_319_20261021/src/netchan/netchan.c`
- `CODOL_SERVER_319_20261021/include/codol_netchan.h`
- `CODOL_SERVER_319_20261021/include/codol_types.h`
- `CODOL_SERVER_319_20261021/src/world/player.c`
- `CODOL_SERVER_319_20261021/src/world/collision.c`
- `CODOL_SERVER_319_20261021/src/world_assets/world.c`
- `CODOL_SERVER_319_20261021/src/world/gamemode.c`
- `CODOL_SERVER_319_20261021/src/battle/snapshot.c`

### 文档与地图证据

- `CODOL_SERVER_319_20261021/docs/PHASE7_COMBAT_WORLD_INVENTORY_20261023.md`
- `CODOL_SERVER_319_20261021/docs/PHASE6_EVENT_SCOREBOARD_DONE_20261023.md`
- `CODOL_SERVER_319_20261021/docs/HANDOFF_20261022_MAINLINE.md`
- `_map_extract/coop_train_spawns.json`
- `_map_extract/coop_train_entities.txt`
- `CODOL_SERVER_319_20261021/fixtures/coop_train_clipmap_20261023.json`

## 7. 交接判定

| 项目 | 状态 | 证据 |
|---|---|---|
| 大厅/战斗服握手 | 已完成 | 本轮日志 |
| gamestate 1-6 | 已完成 | `_c_battle_out.txt` |
| 快照 ACK/持续发送 | 已完成 | `seq=12750` |
| 正常 usercmd（FAT 前） | 已完成 | `USERCMD=5529` |
| FAT 分片接收 | 未完成 | 5514 个 FAT 帧被跳过 |
| FAT 后 usercmd | 未完成 | 从 `0x427` 起无 USERCMD |
| 移动/射击实机 | 未完成 | FIRE/HIT 计数 0 |
| 伤害/死亡/复活 | 未完成 | 对应日志 0 |
| 离开房顶 | 未完成 | z 持续 `-116` |
| 靶场计分/目标 | 未定义/未验证 | 无客户端可见证据 |
| 受保护资产完整性 | 通过 | pre/post 哈希 MATCH |

最终状态：**动态链路 PARTIAL，下一阻断点为 FAT 分片接收重组。**
