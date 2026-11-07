# CODOL 3.19 对局内战斗数据面追踪（2026-10-23）

> 证据：`run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin`（ImageBase `0x400000`）
> 目的：区分“netField 快照表”和“整个战斗系统使用的其它协议/数据面”。

## 1. netField 表范围复核

以 `netField_t` 模式扫描 `0xDA0000–0xDB0000` 后得到 78 个原始候选。

候选一：

- `0xDA1F90`，10 项，xref `0x793F44`
- `0xDA2018`，16 项，xref `0x794085`
- `0xDA28D8`，6 项，xref `0x793F55`
- `0xDA2BB0`，16 项，xref `0x792987`
- `0xDA980C`，23 项，xref `0x6618D1 / 0x662BEF`

这些候选的实际引用代码位于位宽/位流打包逻辑中，内容也不是
`{offset,bits,hint}` 形式的对局字段表，因此判为**非 netField 表**。

已确认的 netField 表族为：

1. `0xDA8078` playerState，87 项
2. `0xDA63E8` entityState，24 项
3. `0xDA90A8` struct3，9 项
4. `0xDA9138` subStruct，42 项
5. `0xDA8520` bigStruct，246 项
6. `0xDA9330` 类型表引用的 18 张数组元素布局，每张 64 项

其中数组元素类型表为 24 个 type 项，按 `table_ptr` 去重后是 18 张不同布局。
类型 0、5、11、16、17、18、20 共享 `0xDA4608`。

结论：**当前证据没有发现第六类之外的额外 netField 表。**
但这只覆盖 netField/静态字段表，不等于覆盖整个战斗协议。

## 2. 其它战斗数据面

### 2.1 gamestate / configstring

已知常量/入口：

- configstring 信息表基址：`0x32AD060`
- InfoString 解析：`0x4E8660`
- InfoString 读取：`0x4E88D0`
- `northyaw` 读取点：`0x4EC171`
- worldspawn/地图初始化链：`0x4EC500`，调用者 `0x61707D`
- 样本：`tests/fixtures/firingrange-gamestate.bin`，259 B

样本中已确认的字符串/结构证据：

- `0x09`：`coop_train_mp_firingrange`
- `0x23`：`coop`
- `0x31`：世界配置字符串，含 `g_gametype`、`g_hardcore`、`mapname`、`scrub_game_allowkillcam` 等
- `0xC1`：`cod`
- `0xC5`：`1`
- `0xCA` 附近：`e0 0 0 1`
- `0xD0`：`fd 02`（小端 `0x02FD=765`）+ `1159`，与已知 `configstring[765]` 对应
- `0xD8` 后为二进制块/基线数据，尚未完全解析
- 提取工具：`tools/gamestate_strings.py`
- 提取结果：`fixtures/firingrange-gamestate-strings.json`

已有运行期实测（来源于 2026-10-22 的另一轮客户端内存读取，非本静态 dump）：

- 客户端紧凑 configstring 缓冲基址：`0x0C47A48D`
- 当时仅 9 条，格式为连续 NUL 拼接，不是固定 stride/指针数组
- `[0]` 为 world/info string
- `[2]="cod"`、`[3]="1"`、`[4]="0 0 0 1"`、`[5]="1159"`
- `[6..8]` 为武器/配件串

这说明静态样本中的字符串偏移与运行期 configstring 顺序可以作为同一协议的
两段证据，但还需要把它们与 `CL_ParseServerMessage` 的读取点绑定。

**状态：部分。** 已知 configstring 存储、读取点和样本位置，但尚未闭合
“网络消息字节 → configstring 索引 → 字符串存储 → 地图/world 初始化”的完整静态链。

### 2.2 usercmd / 输入

项目侧已有可用解析器：

- `src/world/usercmd.c`
- `include/codol_usercmd.h`

已确认格式包括：

- 首部 opcode 3 bit，`opcode==2` 为可靠命令文本段
- 命令数量 1 字节
- time、buttons、pitch/yaw/roll、move、weapon 等 delta 字段
- 可靠命令文本格式：`seq(4B) + NUL-terminated ASCII`

当前状态：解析器已通过项目侧 600 组生成用例和 15 条真实 body 对拍；
但官方客户端中对应的 3.19 读取函数尚未绑定到符号/入口。

### 2.3 reliable command / 服务端命令

已知字符串和位置：

- `gamestateupdate`：`0xDB4700`
- 发送/构造点：`0x473200`
- 调用点：`0x4547D0`、`0x4732F0`、`0x4734E4`、`0x5C054D`、`0x5C0592`
- 客户端命令队列：`0x5C0F50`
- 入站连接/命令分派：`0x5C0FD0`
- 入站分派调用者：`0x5C1AEC`、`0x614D14`

已识别的 OOB/响应字符串：

- `challengeResponse`：`0xDBFEE8`
- `connectResponse`：`0xDBFF0C`
- `statResponse`：`0xDBFF30`

**状态：部分。** OOB/队列地址已定位，服务端强可靠命令的完整 opcode 分派和消费链尚未闭合。

### 2.4 事件、计分、击杀提示

已找到相关字符串族，但尚无可信的直接消费者：

- `scoreboard`：`0xDAF908` 等
- `EXE_MATCHENDED`：`0xDBB314`
- `EXE_PLAYERKICKED`：`0xDBB334`
- `EXE_PLAYERKICKED_SPY_KARMA`：`0xDBB458`
- `EXE_PLAYERKICKED_AS_WISH`：`0xDBB4D0`
- `EXE_CONFIGSTRINGMISMATCH`：`0xDB46E4`
- `EXE_LOSTRELIABLECOMMANDS`：`0xDBB5E8`
- `EXE_AWAITINGGAMESTATE`：`0xDC5F1C`

**状态：未闭合。** 需要继续找 opcode dispatch 到事件/计分 handler 的链。

## 3. 消息原语进展

已定位客户端 packet 消费链的强候选：

- `0x675140`：从消息队列取出一个待处理 packet
- `0x4F8D70`：客户端帧循环，反复调用 `0x675140`
- `0x5C2260`：对单个 packet 执行解析/分发，循环调用者包括
  `0x4F8CD6 / 0x4F8D60 / 0x4F8ED8`
- `0x674EB0`：解析前的连接状态/序号校验
- `0x674740`：在 `0x5C23A0` 被调用，是 packet body 解析候选
- `0x674E10`：结构比较器，供 `0x674EB0` 使用
- `0x470A60`：对剩余负载执行 XOR/解密还原
- `0x473A50`：后续服务端命令/消息处理入口

当前判断：`0x5C2260` 很可能就是 `CL_ParseServerMessage` 或其直接外层；
`0x674740` 负责 packet body，后续由 `0x470A60` 解密并交给 `0x473A50`。
下一步需要从 `0x674740` 和 `0x473A50` 中提取 opcode 分支表。

已在 3.19 客户端静态代码中确认：

- `0x66ED70`：`MSG_ReadByte`
- `0x66EDC0`：`MSG_ReadShort`
- `0x66EE10`：`MSG_ReadLong`
- `0x66F0C0`：`MSG_ReadData`（有边界检查的连续字节复制）
- `0x66EC30`：`MSG_ReadBits`
- `0x447190`：`MSG_ReadBit`

`0x66ED70` 的直接调用者已枚举 30 个。当前确认的邻近候选包括
`0x5BC6xx` 的 party/session 字段解析器，以及 `0x674740` 附近的
字段序列化器；它们都还不能直接认定为 `CL_ParseGamestate`。
下一步需要用 `MSG_ReadShort`/`MSG_ReadLong` 与 configstring 长度字段的组合
来锁定真正的 `CL_ParseGamestate`。

## 4. 下一步固定目标

1. 在官方客户端内定位 `CL_ParseServerMessage` / `CL_ParseGamestate` 的实际地址。
2. 解析 `firingrange-gamestate.bin` 的二进制块，确认 configstring、baseline、EOF 的边界。
3. 把 `gamestate/configstring` 的索引表和字符串写入点补齐。
4. 绑定 usercmd 的官方读取函数地址。
5. 最后再追 scoreboard/event/reliable 的 service opcode。

## 5. 边界

- 本轮未启动游戏客户端、战斗服或注入器。
- 未修改 `REF_LOBBY_KIT`、`CODOL_VERIFIED_GOLDEN_20261019`。
- 本文只记录当前静态证据能达到的结论。
