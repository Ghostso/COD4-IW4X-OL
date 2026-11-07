# 04_MOVEMENT_EVIDENCE_MATRIX

**核心工作包 C:** 用新增移动物理资料做交叉验证。
**口径:** 移动资料 = **项目侧参考/实验产物**(`DIRECT_ARTIFACT_EVIDENCE`),
**不是**官方客户端反汇编。不得据此推导"官方客户端内部一定如此"。
**三分离:** 字段宽度已测出 ≠ 字段语义已知 ≠ 完整消息格式已恢复。

---

## C1. usercmd 与角度

### C1.1 混合编码读取过程与字段边界

来源:`reference/CodolClientCommandReader.cs`(`MixedReader` / `ReadInput`)。

| 步骤 | 依据行 | 说明 | 等级 |
|---|---|---|---|
| 混合游标 | `MixedReader{data,cursor,bit}`;`Bytes(n)` 走 `cursor`(字节对齐),`Bits(n)` 走 `bit`(位游标) | 字节读与位读**共享同一缓冲但独立游标**(两种游标并存) | DIRECT_ARTIFACT |
| 首 3 位 | `uint opcode=r.Bits(3)` | 消息首字段 = 3 位 opcode | DIRECT_ARTIFACT |
| reliable 循环 | `while(opcode==2)` → `seq=Bytes(4); text=Text()` | opcode==2 时为**可靠命令串**,序列号 4 字节 + ASCII 串 | DIRECT_ARTIFACT |
| 计数 | `count=Bytes(1)`;`1..32` | 一包可含 1–32 条 usercmd | DIRECT_ARTIFACT |
| 逐条字段 | `Time,Buttons,Pitch,Yaw,Roll,Move,Weapon,Word22,Word24,Word34,PackedAngle,Byte32,Extra[5]` | `UserCommand` 结构 | DIRECT_ARTIFACT |
| Delta 规则 | `Delta(old,key,w,aligned)= Bits(1)==0 ? old : (aligned?Bytes(w/8):Bits(w)) ^ key` | 1 位"是否变化";变化则按 `aligned` 选字节或位读,再异或 key | DIRECT_ARTIFACT |

### C1.2 yaw 编码与 `angle × 360/65536`

| 断言 | 证据 | 等级 |
|---|---|---|
| `yaw` 为 `ushort`(16 位),`Delta(...,16,aligned:true)` | 源码 `c.Yaw=(ushort)r.Delta(old.Yaw,firstKey,16,true)` | DIRECT_ARTIFACT |
| 换算 `度 = 原始 × 360/65536` | `docs/CODOL_MOVEMENT_PHYSICS_20261004.md` §3.1:`59664→-32.26°`、`19032→104.55°` | DIRECT_ARTIFACT(文档),**REPORT_ONLY**(原始 `camera-motion.json` 不在 ZIP 内) |
| 官方把收到的 usercmd yaw **原样回声**到 viewangles | §3.1 两帧对照 | REPORT_ONLY(同上,`camera-motion.json` 缺失) |

> 换算公式的**独立佐证**:结构化追踪 `demo-player-fields-trace.json` 里 idx18/19 的 `bit` 宽度为
> `375-376=1bit`(对齐短整型)且 `codec=-87`;快照 idx18/19 被项目侧命名为 yaw/pitch。
> 这只证明"字段是 16 位对齐短整型",**不**独立证明"官方视其为角度"。

### C1.3 前进/后退/横移与 yaw 的关系

`docs/CODOL_MOVEMENT_PHYSICS_20261004.md` §3(17139 条实跑输入日志):

```
move=1(前进) dir-yaw =   0.00
move=8(右横移) dir-yaw = +90.00
move=4(左横移) dir-yaw = -90.00
move=2(后退) dir-yaw = 180.00
```

| 断言 | 来源 | 等级 |
|---|---|---|
| `move` 为 4 位,枚举 1/2/4/8 | `c.Move=Delta(old.Move,firstKey,4)` + 文档 | DIRECT_ARTIFACT |
| 前进=yaw、横移=yaw±90、后退=yaw+180 | 实跑日志统计 | DIRECT_ARTIFACT(项目侧) |

### C1.4 参考实现与实验记录一致性 / 测试向量 vs 真实日志

| 证据 | 类型 | 等级 |
|---|---|---|
| `usercmd-native-vectors.json`:20 组(case `idle/move/equipment/special/snapshot-baseline` × key `0,1,0x12345678,0xFFFFFFFF`),含 `baseline`+`body`+`commands` | **合成/测试向量**(用于验证编解码往返) | DIRECT_ARTIFACT |
| 17139 条 `move!=0` 输入日志 | **真实运行日志**(靶场实跑) | DIRECT_ARTIFACT(项目侧) |

> **限定:** 这些资料只证明**项目侧解码器正确处理已知向量与本次实跑**;
> **不**能推导"官方客户端所有 usercmd 字段均已复原"。

---

## C2. snapshot 与字段宽度

来源:`demo-player-fields-trace.json`(`fields[].cursor` = 该字段载荷在混合缓冲的起始字节)、
`scripts/demo_parse.py`(宽度表)、`reference/CodolMotionSnapshot.cs`(写侧)。

**trace 自身限制(必须随表传播):**
`scope = "offline position branch trace; copy and security initialization omitted; not live packet validation"`,
且 `error = RuntimeError('Unclassified call 0xc42d81')` ⇒ **该 trace 是一次未完成的离线跟踪**。

字段矩阵(`evidence/c02_snapshot_field_widths.tsv` 为原始导出):

| idx | trace offset | codec | cursor | 宽度(字节,由相邻 cursor 差) | 已知/推断语义 | 语义来源 | 原始字节/trace 复核 | 与 2697/OLD 直接对应 |
|---|---|---|---|---|---|---|---|---|
| 0 | `0x0` | -97 | 9 | — | commandTime(写侧) | CodolMotionSnapshot.cs | trace(值861) | 否 |
| 3 | `0x2c0` | -16 | 11 | 2 | weaponTime | 写侧 | trace(591) | 否 |
| 4 | `0x568` | -70 | 13 | 2 | presence+4B(i4) | demo_parse 量测 | trace(3155) | 否 |
| 7 | `0xdc` | 12 | 18 | 5 | 推断/未知 | demo_parse 宽=12 位 | trace | 否 |
| 8 | `0x30` | -88 | 19 | 1 | x(float) | 写侧 | trace=1161822208(=1234.0f) | 否 |
| 9 | `0x2bc` | 12 | 23 | 4 | 推断 | 量测宽=12 | trace | 否 |
| 10 | `0x38` | -88 | 25 | 2 | z(float) | 写侧 | trace | 否 |
| 11 | `0x34` | -88 | 29 | 4 | y(float) | 写侧 | trace | 否 |
| 12 | `0x2c` | 8 | 33 | 4 | 推断 | 宽=8 | trace=0 | 否 |
| 13 | `0x40` | -88 | 34 | 1 | vy(float) | 写侧 | trace | 否 |
| 14 | `0x3c` | -88 | 38 | 4 | vx(float) | 写侧 | trace | 否 |
| 15 | `0x100` | -8 | 42 | 4 | 推断(值0⇒无载荷) | 量测 | trace | 否 |
| 16 | `0x44` | -88 | 42 | 0 | float(量测) | 量测 | trace | 否 |
| 17 | `0x2cc` | 6 | 46 | 4 | weaponState(6位) | 写侧 | trace=1 | 否 |
| 18 | `0x164` | -87 | 47 | 1 | yaw(u16 对齐) | 写侧 | trace | 否 |
| 19 | `0x160` | -87 | 49 | 2 | pitch(u16 对齐) | 写侧 | trace | 否 |
| 20 | `0xc` | 32 | 52 | 3 | flags/ADS(32位) | 写侧 | trace=2048 | 否 |
| 29 | `0x168` | -87 | 56 | 4 | roll(u16 对齐) | 写侧 | trace | 否 |
| 30 | `0x298` | -88 | 58 | 2 | float(量测) | 量测 | trace | 否 |
| 34 | `0x170` | -88 | 63 | 5 | float(写侧常量60f) | 写侧 | trace | 否 |
| 38 | `0x16c` | -8 | 68 | 5 | u8(写侧 60) | 写侧 | trace=60 | 否 |
| 39 | `0x3f8` | 11 | 69 | 1 | weapon(11位) | 写侧 | trace=1263 | 否 |
| 45 | `0xb8` | -100 | 71 | 2 | presence+2B(语义未知) | 量测 | trace | 否 |
| 47 | `0xc0` | 11 | 74 | 3 | 实体/相机索引(11位) | 量测 | trace=2046 | 否 |
| 54 | `0x10` | -102 | 76 | 2 | presence+31 flag bits | 写侧 | trace | 否 |
| 57 | `0x4c` | 11 | 81 | 5 | 11位 | 量测 | trace=2047 | 否 |
| 58 | `0x2a8` | 0 | 82 | 1 | float(量测) | 量测 | trace | 否 |
| 59 | `0x158` | 8 | 87 | 5 | u8(量测) | 量测 | trace=2 | 否 |
| 60 | `0xb0` | 16 | 88 | 1 | **movementSpeed**(写侧190) | 写侧+playerstate | trace=190 | 否 |
| 61 | `0x1fc` | 16 | 90 | 2 | **groundEntity**(写侧2047) | 写侧+playerstate | trace=2047 | 否 |
| 63 | `0xa4` | 16 | 93 | 3 | **gravity**(写侧800) | 写侧+playerstate | trace=800 | 否 |
| 64 | `0x6a8` | 0 | 95 | 2 | 末尾字段(量测) | 量测 | trace | 否 |

**结论:**
- 宽度对**部分**字段已量出(`DIRECT_ARTIFACT_EVIDENCE`);
- **语义**绝大多数**未定**(idx 7/9/12/15/16/30/45/47/57/58/59/64 等仍是数字/量测);
- **没有任何字段**与 2697/OLD 参考实现建立直接对应(`否` 列全为否) ⇒ 不得称为"完整消息格式已恢复"。

---

## C3. PlayerState 与预测态

来源:`playerstate-motion-trace.json`(权威/离线轨迹)、`reference/playerstate-fields.json`(offset/codec 表)、
`scripts/battle_server.py`、`scripts/nt10.py`、`docs` §2/§9/§11.3。

### C3.1 预测态与权威态的识别依据

`docs` §9.1 判据:`f2c != 0` 或 `pm_flags ∉ {0, 0x10}`,加严 `pm_flags < 0x10000 且 f2c < 0x10000`;
首选"z 离群"候选(权威副本 z 恒等于下发常量)。

| 问题 | 答案 |
|---|---|
| 两个识别依据是否**相互独立**? | **否。** `f2c/pm_flags` 与"z 离群"都来自**同一份候选结构扫描**,且 §11.3 明确记录过锚点误收(OR 判据收到 `0x18004000` 的假结构)。⇒ 该判别是 `INFERRED`,**非**独立双证据。 |

### C3.2 字段证据表

| 字段 | 内存偏移 | 直接证据 | 值域/行为 | 等级 |
|---|---|---|---|---|
| `pm_type` | `+0x04` | `playerstate-fields.json` + `nt10` | `0`(正常) | DIRECT_ARTIFACT |
| `pm_flags` | `+0x0c` | 同上;docs §2 | 权威`0`/预测`0x2020`,`0x10`=开镜 | DIRECT_ARTIFACT |
| `f2c` | `+0x2c`(idx12) | `playerstate-fields.json` idx12 offset `0x2c` codec 8 | `0`/非`0` | DIRECT_ARTIFACT(offset) / `INFERRED`(判别义) |
| `commandTime` | idx0 | `CodolMotionSnapshot` + trace | 最新=预测 | DIRECT_ARTIFACT |
| `origin` x/y/z | `+0x30/+0x34/+0x38` | `playerstate-fields.json` idx8/11/10 + trace | 出生点`48,-572,-116` | DIRECT_ARTIFACT |
| `velocity` x/y/z | `+0x3c/+0x40/+0x44` | idx14/13/16 | 权威=下发值;预测=自有 | DIRECT_ARTIFACT |
| `gravity` | `+0xa4` | idx63 + trace=800 | 800 | DIRECT_ARTIFACT |
| `movementSpeed` | `+0xb0` | idx60 + trace=190 | 190 | DIRECT_ARTIFACT |
| `cameraEntity` | `+0xc0` | idx47 + trace=2047 | 2047 | DIRECT_ARTIFACT |
| `groundEntity` | `+0x1fc` | idx61 + trace=2047 | 2047 | DIRECT_ARTIFACT |

> **重要区分:** 上表 `offset` 来自**内存结构观察**(`playerstate-fields.json` + 探针),
> **不与**网络 snapshot 的 idx 边界等价(见 §C4)。内存布局与网络编码格式**分别论证**。

### C3.3 镜像预测态改善移动行为的证据

`docs` §9.3 四次对照(1/2/3/4)、§10 定量:

| 配置 | 方向=yaw | 重力/爬箱 | z 峰峰 |
|---|---|---|---|
| 镜像+40Hz+lead50 | 是(有延迟) | 是 | 大 |
| 镜像+128Hz+lead25 | 是 | 是 | 82.66 |
| **镜像+128Hz+lead0** | 是 | 是 | **23.66** |
| 镜像+10Hz+lead0 | 否 | 否 | — |

⇒ "镜像确实让移动变成客户端自己的 Pmove"有**多组对照实跑**支持(`DIRECT_ARTIFACT`);
但**原始 `pred_trace.txt`/`n10*.txt` 不在 ZIP 内**,定量值只能 `REPORT_ONLY`。

### C3.4 橡皮筋解释的时序数据是否足够

- 文档给出机理("回发上一 tick 预测值 → 客户端重新播种预测 → 相互拉扯")并给出逐 tick 统计;
- **但** `pred_trace.txt` 与逐 tick 数据**不在 ZIP 内**,ZIP 内仅 `evidence/battle_srv_excerpt.log` 摘录。
- ⇒ 橡皮筋的**机理解释** = `INFERRED`;`REPORT_ONLY`(时序原始数据缺失)。

---

## C4. 移动业务链与通用 decoder 的对应关系

对应矩阵(只允许 `DIRECT_MAPPING / PARTIAL_MAPPING / STRUCTURAL_SIMILARITY_ONLY / CONTRADICTED / UNKNOWN / BLOCKED`):

| 项目 | 断言 | 裁定 | 依据 |
|---|---|---|---|
| `0x87C110` ↔ usercmd? | — | **CONTRADICTED** | `0x87C110` 唯一调用者 `0x85D49D` 在 TQOS;引用 `tdr_net.c`;usercmd 解码在**另一套**低地址/项目侧实现 |
| `0x87D5A0` ↔ snapshot? | — | **CONTRADICTED** | 4/4 调用者在 TQOS;引用 TDR net-buffer 诊断;无 snapshot 消费者边 |
| `0x879AC0` netfield 行为 ↔ 移动快照字段? | — | **STRUCTURAL_SIMILARITY_ONLY** | 有"变长长度前缀 + 跳表分派",与 snapshot 字段宽度表**外形相似**,但无共享缓冲/字段值/调用关系 |
| `0x87BE00` 接收链 ↔ 上述消费者? | — | **CONTRADICTED** | 链只进入 TQOS 描述符;无到玩家/快照状态的写 |
| 直接交叉引用? | — | **UNKNOWN**(无) | 全映像 dword 引用扫描 = 0 |
| 共享缓冲区? | — | **CONTRADICTED** | TQOS 用自身栈缓冲(`esp+0x5000`,上限 `0x4EBC`);移动快照用项目侧构造的 `CodolMotionSnapshot` 字节 |
| 字段值对应? | — | **UNKNOWN** | 未见同一字段值同时出现在 TQOS 缓冲区与移动快照 |
| 仅宽度相似/结构相似/命名相似? | — | **是** | 这是当前唯一的"相似性"来源 |

> **结论:不得写成"已找到官方 usercmd/snapshot 解码器"。**
> `0x87C110/0x87D5A0` 与移动语义的关系目前是 **CONTRADICTED**(因其归属 TQOS),
> 而移动语义的**唯一证据**来自**项目侧实现与实验**,非官方客户端。

---

## C5. 三分离声明

| 层次 | 已有 | 缺失 |
|---|---|---|
| 内存结构(PlayerState/预测态) | 项目侧偏移表 + 探针验证 | 官方符号/结构定义 |
| Demo / 离线格式(demo_parse、trace) | 宽度表(部分)+ 未完成 trace | 完整字段语义、`camera-motion.json` |
| 网络协议(线格式) | 项目侧构造的 snapshot 字节 + 实跑 | **官方收发链到消费者的直接证据** |
