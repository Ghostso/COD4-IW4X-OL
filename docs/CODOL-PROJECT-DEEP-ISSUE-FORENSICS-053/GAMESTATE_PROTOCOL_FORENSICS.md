# GameState 协议取证

> 判定口径（全文强制）：**发送成功 ≠ 接收成功 ≠ 解析成功 ≠ 状态转换成功 ≠ 渲染成功**。
> 本文件逐段标注证据停在哪一层。

---

## 1. 现状一句话

服务端能构造并加密发送 Gamestate；客户端在 2026-10-23 的实机上**回报过 `gamestateupdate <n>`**，
说明它至少收到了并开始了加载流程。但**没有任何一次证据表明它完成了 `CA_GAMESTATE → CA_PRIMED`**。

---

## 2. 全部历史实现版本

| 版本 | 文件 / 形态 | 大小 | 说明 |
|---|---|---|---|
| 样本 | `firingrange-gamestate.bin` | **283 B**（2026-10-26 起）/ 259 B（更早） | 靶场样本 |
| C 编码器 | `battle_service.c:send_gamestate()` | — | 读文件 + 加 4 B seq + XOR |
| 动态适配 | `battle_service.c:_gs_adapt_dynamic()` | — | 改 header 的 map/gametype |
| Python 参照 | `battle_server.py`（legacy） | 70,203 B | 已废弃 |

> **注意文件大小已变化**：早期报告写 259 B，`ONCE_20261026_220815/kit/firingrange-gamestate.bin`
> 实测 **283 B**。这两个不是同一份。引用旧结论时必须注明。

---

## 3. 服务端编码（可读源码）

`src/battle/battle_service.c:374-409`

```c
static int send_gamestate(codol_battle_service_t *svc, codol_battle_assoc_t *a)
{
    uint8_t state[1200];
    uint8_t payload[1208];
    ...
    n = fread(state, 1, sizeof(state), fp);
    if (n < 16 || n > 1100) { ... return -1; }        /* ← 硬上限 1100 */

    if (_gs_adapt_dynamic(state, sizeof(state), &n, room_path) == 0) ...

    seq = svc->netchan_seq++;
    total = 4 + (int)n;
    payload[0..3] = seq (LE);
    memcpy(payload + 4, state, n);
    mask = (uint8_t)((seq ^ 1) & 0xFF);
    for (i = 8; i < total; i++) payload[i] ^= mask;   /* ← 前 8 字节不参与掩码 */
    send_frame(svc, a, payload, total);
}
```

| 项 | 值 |
|---|---|
| 输入 | `firingrange-gamestate.bin` + `./active_room.json` |
| 输出 | 加密帧 |
| 前置 | `a->key_ready`（密钥交换完成） |
| 副作用 | `gamestate_attempts++` |
| 失败返回 | 文件打不开 / 尺寸越界 → -1（只打 WARN） |
| 硬编码 | 上限 1100 B；`i` 从 8 开始（跳过 seq + 4 字节 state 头） |

### 3.1 已知的硬约束

| 约束 | 位置 | 风险 |
|---|---|---|
| `state` 缓冲 1200 B | `:376` | 超过即失败 |
| `n > 1100` 拒绝 | `:389` | **任何多 configstring 的地图都可能被拒** |
| 最多 5 次 | `:611` | 失败后本会话不再发 |
| 2 s 重试间隔 | `:613` | — |

---

## 4. 与客户端的状态对应

`docs/PVE_STUCK_INVESTIGATION_20261027.md §4` 解出的 11 态（`0x005C8060`）：

```
0 CA_DISCONNECTED  1 CA_CINEMATIC  2 CA_LOGO   3 CA_CONNECTING  4 CA_CHALLENGING
5 CA_LOADING       6 CA_CONNECTED  7 CA_SENDINGSTATS  8 CA_GAMESTATE
9 CA_PRIMED       10 CA_ACTIVE
```

**服务端可观测的对应点**：

| 客户端状态 | 服务端能看到的信号 | 本项目的证据 |
|---|---|---|
| CA_CONNECTING (3) | `RX_OOB cmd='connect …'` | ✅ 10-26 成功轮 |
| CA_SENDINGSTATS (7) | `RX_OOB cmd='stats'` + `STATS_COMPLETE` | ✅ 同上 |
| CA_GAMESTATE (8) | `RX_OOB cmd='gamestateupdate N'` | ⚠️ 有记录（2026-10-23 前后），**当前轮次未见** |
| CA_PRIMED (9) | **无信号** | ❌ 从未观测 |
| CA_ACTIVE (10) | `RX_CLIENT_GAME_HEADER` 开始带 usercmd | ✅ messageAck 递增（历史） |

**★ 关键**：`CA_PRIMED` 与 `CA_ACTIVE` 之间**服务端没有任何可观测信号**。
所以"客户端是否进入 CA_ACTIVE"只能从"是否开始发 usercmd"反推。

---

## 5. 字段表

| Offset | Length | Field | Encoding | 证据等级 |
|---|---|---|---|---|
| 0 | 4 | netchan seq | LE u32 | S-impl + C-bytes |
| 4 | 1 | cmd | 必须 == 3 | S-impl；**客户端读点未定位** |
| 5 | 4 | ver | LE u32 | S-impl；语义 UNKNOWN |
| 9 | n | mapName | NUL 结尾 ASCII | S-impl + 动态适配依赖它 |
| — | n | gameType | NUL 结尾 ASCII | 同上 |
| — | 4 | field4 | LE u32 | S-impl；语义 UNKNOWN |
| … | — | configstring[0] | `\key\value\…` | 部分（`_cs_replace_kv` 未接线） |
| 末尾 44 B | 44 | **未解析** | — | **UNKNOWN** |

**证据等级说明**：全部为 `S-impl`（我们构造的）+ 部分 `C-bytes`（客户端回报了 `gamestateupdate`）。
**没有** `C-state` 级证据（没有一次证明客户端因 configstring 而改变状态）。

---

## 6. 已知的失败输入 / 成功输入

| 输入 | 结果 | 出处 |
|---|---|---|
| 283 B 靶场 gamestate | 客户端回报 `gamestateupdate` | 10-26 成功轮（间接） |
| 动态适配后的 map=mp_raid | **未实机验证** | 代码存在（`:302`），无 run 证明 |
| `_gs_adapt_dynamic` 对非 3 cmd 的输入 | 直接返回 -1（不改） | `:331` |

**没有"已知失败输入"的完整清单** —— 从未系统性地改过 gamestate 并观察。

---

## 7. 客户端消费证据状态

| 问题 | 答案 | 依据 |
|---|---|---|
| 客户端收到了吗？ | **是（历史上）** | `gamestateupdate` 回报 |
| 解析了吗？ | **UNKNOWN** | 无日志、无内存 |
| 状态转换到 CA_PRIMED 了吗？ | **UNKNOWN** | 无信号 |
| 地图加载了吗？ | **是（历史上）** | 10-24 `RUNENC4BIT` 进图 |
| 渲染了吗？ | **是（历史上，用户确认）** | 用户报告"能进游戏" |

**矛盾点**：历史上"进图"成功，但 gamestate 的消费路径从未被单独证明。
可能解释：进图依赖的主要是 **snapshot**，gamestate 只是"必要但不充分"。

---

## 8. 与 ISSUE-0020 的关系

**Gamestate 与"零收包"无关**：
gamestate 是在 UDP 握手完成**之后**才发的；零收包意味着连握手都没发生。

⇒ 本文件的所有内容在 ISSUE-0020 解决前**都无法实机验证**。

---

## 9. 未解问题清单

| # | 问题 | 需要的证据 |
|---|---|---|
| G1 | 末尾 44 字节是什么 | 改一个字节，看客户端反应（单变量） |
| G2 | `ver`/`field4` 语义 | 同上 |
| G3 | configstring `index_bits()` 编码 | 同上 |
| G4 | 1100 B 上限是否真实 | 造一个 1101 B 的 gamestate 试 |
| G5 | 客户端是否真的读 configstring | 改 configstring[0] 的 map 名，观察行为 |
| G6 | CA_PRIMED 的触发条件 | 无服务端信号，只能靠"开始发 usercmd"反推 |

---

## 10. 结论

**当前状态**：发送链路 `S-impl` 完整；消费证据只到 `C-bytes`（一次 `gamestateupdate`）。
**没有任何 `C-state` 级证据。**

要推进，必须：
1. 先解决 ISSUE-0020（能连上）。
2. 然后做 G5（改 configstring 单变量），这是唯一能证明"客户端在读 gamestate"的实验。
