# CODOL 3.19 对局内逆向路线（2026-10-23）

> 证据基座：`run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin`
> 目标：按依赖顺序闭合对局协议、状态语义、事件系统和战斗逻辑。
> 纪律：只记录已验证事实；推断和未闭合项必须显式标注。

## 状态图例

- `DONE`：已有可复核证据和产物
- `ACTIVE`：当前阶段正在推进
- `PARTIAL`：已有可复核主体，但仍存在显式未闭合子项
- `TODO`：尚未开始
- `BLOCKED`：缺少必要证据，且没有安全的静态推进路径

## 总体顺序

### Phase 0：基线台账与证据约束

- 状态：`DONE`
- 产物：
  - protected 文件哈希基线
  - 对局 netField 表清单
  - 18 张数组元素布局
  - codec/bitstream 初步规范
- 验收：
  - 所有对局字段表可按地址和类型复现
  - 运行产物只进 `run_codol_001/runs/<RUN_ID>/`

### Phase 1：消息外层、opcode 和客户端接收链

- 状态：`PARTIAL`（核心接收链与已用 handler 已绑定；完整 `svc_*`/`clc_*` 错误边界尚未逐项闭合并列在缺口矩阵）
- 必逆内容：
  1. `CL_ParseServerMessage` 的实际入口
  2. `svc_*` opcode 分发表
  3. `clc_*` 客户端命令 opcode
  4. 消息缓冲、长度、对齐、截断和错误处理
  5. `gamestate / configstring / baseline / snapshot / EOF` 的边界
- 已知锚点：
  - `MSG_ReadByte = 0x66ED70`
  - `MSG_ReadShort = 0x66EDC0`
  - `MSG_ReadLong = 0x66EE10`
  - `MSG_ReadData = 0x66F0C0`
  - `MSG_ReadBits = 0x66EC30`
  - `MSG_ReadBit = 0x447190`
- 当前已识别链路：
  - `0x4F8D70`：客户端帧循环，反复取包
  - `0x675140`：消息队列取包
  - `0x5C2260`：单包解析/分发外层，强候选 `CL_ParseServerMessage`
  - `0x674EB0 / 0x674E10`：解析前连接状态/序号比较
  - `0x674740`：packet body 解析候选
  - `0x470A60`：剩余负载解密/XOR 还原
  - `0x473A50`：后续服务端命令/消息处理入口
- 其它候选：
  - `0x5BC6xx`
  - 其它调用 `MSG_ReadByte/ReadShort/ReadLong` 的分发函数
- 当前 opcode 分发表（`0x473A50` 内）：
  - `0` -> `0x471E90`：未定类
  - `1` -> `0x4737E0`：gamestate/系统信息候选
  - `2` -> `0x4738A0`：configstring 更新，已由读取格式确认
  - `3` -> `0x473260`：serverCommand 候选
  - `4` -> 默认溢出处理
  - `5` -> `0x473C3E`：直接返回/结束候选
- 已确认：opcode 2 handler 会读取 `4B sequence + 2B index + length/data`，
  并写入 `cl+0x80154 + (index&0x1FF)*0x400`，这是 configstring 更新证据。
- 当前 opcode 分发表（`0x473A50` 内）：
  - `0` -> `0x471E90`：gamestate 候选，包含文件/下载/资源初始化调用
  - `1` -> `0x4737E0`：configstring 候选，读取 4B 索引 + NUL string，写入 `cl+0x80154` 槽
  - `2` -> `0x4738A0`：serverCommand 候选，读取 4B seq + 2B length + data，写入命令槽
  - `3` -> `0x473260`：snapshot 候选，进入 `0x472be0 / 0x472d80` 快照状态链
  - `4` -> 默认异常/溢出处理，matchdata 候选
  - `5` -> `0x473C3E`：EOF/结束
- 已确认：opcode 2 handler 会读取 `4B sequence + 2B index + length/data`，
  并写入 `cl+0x80154 + (index&0x1FF)*0x400`。
  该缓冲区是 512 个 0x400 槽位，是 configstring/服务端命令缓存的关键结构。
- 产物：
  - opcode 表
  - 每个 handler 的地址和输入输出
  - 消息长度/错误语义
- 验收：
  - 对一条真实客户端或 capture 消息，能逐 opcode 走到 handler
  - 不依赖“结构相似”作为最终判定

### Phase 2：Gamestate 和 configstring

- 状态：`DONE`（2026-10-23，字节级闭环）
- 下一轮硬目标：**一次追完 Phase 2，不再拆分**
- Phase 2 完成必须同时满足：
  1. 明确 `0x471E90` 是否为 gamestate handler，并拆出完整读取顺序
  2. 明确 `0x4737E0` 和 `0x4738A0` 各自是 configstring 还是 serverCommand
  3. 完整解析 configstring 索引、sequence、length/index、字符串边界
  4. 解释运行期 `[765] = "1159"` 如何落到 `cl+0x80154` 槽位
  5. 给出可运行的 gamestate/configstring 解码器和编码器
  6. 用现有 `firingrange-gamestate.bin` 完成至少一次 decode/encode 对拍
- 必逆内容：
  1. `CL_ParseGamestate` 入口
  2. configstring 索引空间和数量
  3. `index + string` 记录格式
  4. configstring 增量更新格式
  5. baseline/EOF 边界
  6. 服务端 gamestate 生成规则
- 已知锚点：
  - configstring 信息表：`0x32AD060`
  - InfoString 解析：`0x4E8660`
  - InfoString 读取：`0x4E88D0`
  - `northyaw` 读取：`0x4EC171`
  - 样本：`tests/fixtures/firingrange-gamestate.bin`
  - 样本中 `configstring[765] = "1159"`
- 产物：
  - gamestate 解码器
  - gamestate 编码器
  - configstring 清单和索引表
- 验收：
  - 客户端接受重建 gamestate
  - configstring 数量和关键值可核对
  - 小地图、武器、地图信息不依赖固定模板

### Phase 3：Snapshot codec 精确实现

- 状态：`PARTIAL`（141B 历史黄金向量字节级一致；但实机报告显示该载荷未被客户端 ack，124B 读向量可完整消费，写入器仍冲突）
- 必逆内容：
  1. 45 个 codec 分支的完整公式
  2. 压缩浮点格式
  3. 角度、时间、定点数的边界语义
  4. 变化位、游程、最后变化索引的精确写法
  5. baseline 初始化
- 关键函数：
  - `0x670FF0` ReadDeltaStruct
  - `0x670D30` ReadDeltaField
  - `0x6701D0` ReadDeltaField2
  - `0x677E10` WriteDeltaStruct
  - `0x676E00` WriteDeltaField
  - `0x66F060 / 0x66F9E0 / 0x66FC00 / 0x66FC40 / 0x66FCF0 / 0x66FEE0`
  - `0x675A70 / 0x6769A0 / 0x676030`
- 产物：
  - Python 参考 codec
  - C 端精确 codec
  - 离线 encode/decode 对拍工具
- 验收：
  - `decode(encode(x)) == x`
  - 与客户端写路径逐字节一致
  - 官方快照无剩余未知分支

### Phase 4：netField 字段语义和 baseline

- 状态：`DONE`（51/87 playerState、17/24 entityState 已命名，其余保留结构语义）
- 必逆内容：
  1. playerState 字段语义
  2. entityState 字段语义
  3. 18 张数组元素布局的实体类型和字段语义
  4. baseline/default 值
  5. 哪些字段客户端预测，哪些服务端权威
- 关键读取函数：
  - `0x471560`
  - `0x471980`
  - `0x671170`
  - `0x671B60`
  - `0x671D80`
- 产物：
  - 字段语义表
  - baseline 模板
  - state 生成器
- 验收：
  - 快照中的位置、生命、武器、状态字段可在客户端正确生效

### Phase 5：Usercmd、可靠命令和输入闭环

- 状态：`DONE`（600+15 向量 0 mismatch，可靠背包命令通过）
- 必逆内容：
  1. 官方 3.19 usercmd 读取函数
  2. `clc_move / clc_reliable / clc_stringcmd` 绑定
  3. 序号、ack、重发规则
  4. 背包/武器/开火/ADS/换弹命令语义
- 已知锚点：
  - 项目侧解析器：`src/world/usercmd.c`
  - `gamestateupdate`：`0xDB4700`
  - 发送/构造点：`0x473200`
  - 出站命令队列：`0x5C0F50`
  - 入站连接/命令分派：`0x5C0FD0`
- 产物：
  - 官方 usercmd 规范
  - 输入回复和可靠命令状态机
- 验收：
  - 客户端进图后持续上报真实按键
  - 开火、ADS、换弹、切换武器均由服务端正确接收

### Phase 6：Event、scoreboard 和比赛状态

- 状态：`DONE`（46 个事件命令、handler xref、scoreboard 无独立 netField 表）
- 必逆内容：
  1. 事件 opcode 和 handler
  2. 击杀/死亡/计分/回合/目标消息
  3. 比赛结束和玩家踢出
  4. 可靠命令溢出和丢失恢复
- 已知字符串：
  - `EXE_MATCHENDED`：`0xDBB314`
  - `EXE_PLAYERKICKED`：`0xDBB334`
  - `EXE_PLAYERKICKED_SPY_KARMA`：`0xDBB458`
  - `EXE_PLAYERKICKED_AS_WISH`：`0xDBB4D0`
  - `EXE_LOSTRELIABLECOMMANDS`：`0xDBB5E8`
  - `EXE_SERVERCOMMANDOVERFLOW`：`0xDBB584`
  - `EXE_AWAITINGGAMESTATE`：`0xDC5F1C`
- 产物：
  - 事件表
  - scoreboard/round/objective 消息模型
- 验收：
  - 击杀、死亡、得分和回合状态能被客户端识别

### Phase 7：战斗逻辑和世界数据

- 状态：`ACTIVE`
- 2026-10-23 追加：WeaponAttach 记录结构已逐资产验证；`0x31xxxxxx` 引用为共享字符串/资源槽位，尚未能和文件偏移一一直接解引用。运行时只应用已确认的 scalar 字段，引用字段保留原始 token。
- 当前进展（2026-10-23）：
  - 状态补充：Phase 7 的附件标量子集已可运行；IW4X 对照已确认 12B tuple 的首字段是 type，type<16/39 走流内字符串读取；第二字段是 index 字段槽位。3.19 的共享槽位仍需 type-43 reader 的 accessor 证据，不能把 token 当文件指针。
  - ClipMap：已从 3.19 coop zone 闭合 27 planes、4 materials、27 brushsides、30 brushes、30 bounds/contents；29 个 script_brushmodel AABB 已接入碰撞。
  - WeaponDef：已从 3.19 common_mp XAssetList 定位 1134 个 type-28 资产，恢复 890 个名称和 18 把 firingrange 武器参数；已闭合距离伤害、20 项 hit-location 倍率与头部伤害 API。3.19 zone 已直接闭合六段伤害 `+0xD10`、六段距离 `+0xD28` 和 20 项位置倍率 `+0xD4C`；OLFinal 的 `+0xBB4/+0xBCC/+0xBF0` 已否定，`+0x810..+0x824/+0xAC0` 仍只作未验证候选。
  - WeaponAttach：285 个 type-43 资产、4912 条 12B 记录已解析；73 个资产含本地字符串表，3750 条引用记录保留共享槽位原始 token；44 个附件、94 条安全 scalar 已进入运行表，545 条 string/resource 记录仍显式 skipped。
  - 产物：`PHASE7_COMBAT_WORLD_INVENTORY_20261023.md`、`INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`、`fixtures/coop_train_clipmap_20261023.json`、`fixtures/common_mp_weapondefs_20261023.json`。
- 必逆内容：
  1. 武器定义、配件、伤害、弹道、弹药
  2. 换弹、开镜、切换武器
  3. 出生点、碰撞、重力、移动
  4. actor、载具、炮塔、loot
  5. 游戏模式、目标、回合和计分
- 已知入口：
  - listen server：`0x5AD350 / 0x5ADD76`
  - snapshot 写路径：`0x6783B0 / 0x6784E0 / 0x678740`
  - `.ff` 解包和地图实体工具
- 产物：
  - 武器/伤害/实体逻辑
  - 世界和碰撞数据
  - 游戏模式状态机
- 验收：
  - 稳定移动、开火、命中、换弹、计分和目标状态

### Phase 8：实机验证和证据闭环

- 状态：`TODO`
- 必逆/必备证据：
  1. IIPS、Auth、Lobby、Battle 时间戳
  2. 同一 client PID
  3. gamestate/configstring dump
  4. 快照 encode/decode 对拍
  5. 成功阈值证据
- 纪律：
  - 每次实验独立 `run_codol_001/runs/<RUN_ID>/`
  - 单次只创建一个客户端，不自动重启
- 验收：
  - 每个声明都有时间戳和可复核输入

## 当前优先级

1. Phase 7：闭合命中盒、护甲/穿透、爆炸/投掷物、actor/vehicle/objective
2. Phase 7：继续闭合 WeaponAttach 共享字符串槽与 ADS/recoil 生效公式
3. Phase 8：按独立 run 规则完成同一 PID 的完整对局实机证据

完整缺口矩阵见 `docs/INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`。

## 当前不做的方向

- 不再追 TQOS/TDR 平台层，除非发现游戏业务直接调用证据
- 不重建整棵游戏树
- 不修改受保护资产
- 不在没有新隔离 run 目录的情况下做实机实验


