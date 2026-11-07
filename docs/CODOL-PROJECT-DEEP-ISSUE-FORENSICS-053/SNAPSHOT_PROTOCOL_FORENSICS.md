# Snapshot 协议取证

> 判定口径：**发送 ≠ 接收 ≠ 解析 ≠ 状态转换 ≠ 渲染**。
> Snapshot 是本项目**唯一有 `C-ack` 级证据**的协议段。

---

## 1. 现状一句话

快照能被客户端确认（messageAck 持续递增，历史最高 4272），但**位置字段不被采纳**，
实体段**收得下但看不见**。

---

## 2. 历史实现版本

| 版本 | 编码 | 首帧字节 | 结果 |
|---|---|---|---|
| 2026-10-22 二进制 | 索引 run **4 位/步长 15** | 105 | ✅ 进图 |
| 2026-10-23 二进制 | 按表宽 **7 位**（"修正"） | 103 | ❌ 卡"等待玩家数据" |
| 2026-10-24 改回 4 位 | 4 位/步长 15 | 103 | ✅ 进图（messageAck 4272） |
| 2026-10-24 按参照重写 | 与三份参照逐字节一致 | 141 / 119 | ❌ 卡住（已回退） |
| 2026-10-24 裸值修复 | 11 字段 XOR→裸值 | — | ⚠️ 一半成（用户确认弹药/换弹正常） |
| 2026-10-25 实体段 | 插入在 `0x05` 之前 | 176（ents=8） | ⚠️ 收得下，看不见 |

---

## 3. 服务端编码（可读源码）

`src/battle/battle_service.c:421-591` → `codol_snapshot_build()`（`src/battle/snapshot.c`）

关键行：

```c
/* battle_service.c:425 */
uint8_t snap[512], payload[520];          /* ← TX 上限 512 B */

/* :486 */
omit = svc->snapshot_sent;                /* 首帧发位置，之后不发 */

/* :512-539 */
n = codol_snapshot_build(snap, sizeof(snap), 0, server_time,
                         svc->processed_input_time, !svc->snapshot_sent,
                         px, py, pz, pitch, yaw, roll, pvx, pvy,
                         aim_fraction, aiming, omit,
                         false,                    /* idx61 = 空中 */
                         (uint16_t)0,              /* ET6 武器子实体号 = 0 */
                         &svc->snap_from, &svc->snap_cur, &eq,
                         ent_count > 0 ? ents : NULL, ent_count);

/* :541 */
svc->snap_from = svc->snap_cur;           /* ← 基线在 send 之前前移 */
```

| 项 | 值 |
|---|---|
| 输入 | `svc->player`（位置/视角）、`svc->equip`、`svc->world->entities[]` |
| 输出 | 位流 |
| 前置 | `a->key_ready` |
| 副作用 | `snap_from` 前移、`input_baselines[]` 写入 |
| 失败返回 | `w.overflow` → -1 |
| 硬编码 | 512 B 缓冲；idx61 恒 false；ET6 号恒 0 |

---

## 4. 字段表（已验证 / 未验证）

| 段 | 字段 | 编码 | 证据等级 | 备注 |
|---|---|---|---|---|
| 头 | header | `first` bit + flags | `C-ack` | — |
| — | serverTime | u32 | `C-ack` | 基数 1000 无出处 |
| — | command_time | u32 | `C-ack` | 来自 usercmd ack |
| 索引 | 索引 run | **4 位/步长 15** | `C-state` | 改 7 位即失败 |
| 位置 | x/y/z | f32（omit 控制） | `C-ack` + `C-state`（不采纳） | ISSUE-0025 |
| 视角 | pitch/yaw/roll | i16 | `C-ack` | — |
| — | idx20 pm_flags | `aiming?0x10:0` | 未归因 | 可能是 PMF_SPRINTING |
| — | idx61 groundEntityNum | 恒 2047 | `C-state`（2046 → 飞行模式） | — |
| 装备 | 槽位/弹药 | 位域 | `C-state`（弹药/换弹正常） | 裸值修复后确认 |
| 实体 | entity section | removed/changed/newEntity/6 位/3 位 | `C-ack`（不判废） | **不可见** |
| 终止 | `0x05` | 1 byte | `C-ack` | 实体段必须在其之前 |

---

## 5. 已知的失败输入

| 输入 | 症状 | 出处 |
|---|---|---|
| 141 B（参照改写版，omit=0） | 卡"等待玩家数据"，head 只到 0x62 | `REFENCODER_20261024_1150`（**目录不在盘上**） |
| 119 B（参照改写版，omit=1） | 同上，head 0x8C | `REFENC_OMIT1_20261024_1153`（不在盘上） |
| 103 B（7 位索引） | 同上 | `HEAD_CLEAN_20261024_1048`（不在盘上） |
| idx61 = 2046 恒定 | 飞行模式 + 开镜失效 | `SNAPSHOT_RAWFIX_20261024_1357`（不在盘上） |

**★ 全部四个失败实验的 run 目录已不在磁盘上** ⇒ 只能引用二手文档。

---

## 6. 客户端消费证据

| 层 | 状态 | 证据 |
|---|---|---|
| 发送 | ✅ | `TX_SNAPSHOT seq=N bytes=M` |
| 接收 | ✅ | `RX_CLIENT_GAME_HEADER messageAck=` 递增 |
| 解析 | ✅ | 索引编码改错即失败 ⇒ 说明读到了那一位 |
| 状态转换 | ⚠️ 部分 | 弹药/换弹正常；位置不采纳 |
| 渲染 | ⚠️ | 玩家可见但位置由客户端自己算 |

**这是全项目唯一能证明"客户端确实在按位读我们的包"的地方。**
（对应 ISSUE-0041 的收包边：至少在快照这一侧，位流被客户端正确消费了。）

---

## 7. 关键结论：快照不是零收包的原因

零收包发生在 UDP 握手之前；快照在握手之后。
⇒ `UNWIRED` / 快照问题全部**不影响** ISSUE-0020。

---

## 8. 实体段专项

`battle_service.c:497-510`：

```c
if (svc->world && flag_file_exists(svc->entities_flag_path)) {
    for (wc = 0; wc < CODOL_MAX_ENTITIES && ent_count < 8; wc++) {
        const codol_entity_state_t *e = &svc->world->entities[wc];
        if (e->in_use && e->type != 0) {
            ents[ent_count].number = e->number;
            ents[ent_count].type   = e->type;
            ents[ent_count].x = ...; y = ...; z = ...;
            ent_count++;
        }
    }
}
```

| 缺口 | 后果 |
|---|---|
| 无 `model_index`（`entity.c` memset 为 0） | 无模型可画 |
| 实体号 0..7 = 客户端自己的槽位 | 与客户端实体冲突 |
| 上限 8 | 334 个地图实体只能发 8 个 |
| 512 B 缓冲 | 最多约 10 个实体 |

**未做的关键对照**：畸形实体段（截断）看 ack 是否中断 —— 即 ISSUE-0024 的 E 实验。

---

## 9. 未解问题

| # | 问题 | 需要的证据 |
|---|---|---|
| S1 | 512 B 上限能否放宽 | 扩缓冲 + 单条大快照 |
| S2 | 实体 model_index 从哪来 | 需要 configstring 绑定 |
| S3 | 实体号空间怎么分配 | 需要知道客户端的 maxclients |
| S4 | 位置为何不被采纳 | ISSUE-0025 |
| S5 | 实体段是否真被解析 | 畸形对照 |

---

## 10. 结论

**Snapshot 是当前证据最强、问题最"局部"的一段。**

- 编码可用（能进图、能确认）
- 失败点明确（位置权威、实体可见）
- 但**全部依赖先解决 ISSUE-0020**（否则连不上，什么都验不了）

建议在 ISSUE-0020 解决后，**优先做 S5（畸形实体段对照）**，它成本最低且能一次性回答"实体段有没有被读"。
