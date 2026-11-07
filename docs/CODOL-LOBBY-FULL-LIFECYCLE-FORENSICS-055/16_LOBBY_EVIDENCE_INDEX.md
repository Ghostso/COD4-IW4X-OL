# 16 — 大厅证据索引（说明）

> 数据源：`LOBBY_EVIDENCE_INDEX.json`（74 条：64 个 run 日志 + 10 份文档/二进制）。

---

## 1. 主证据：64 个 run 的 `lobby_srv.log`

每个 run 一条记录，含：
- 绝对/相对路径
- **SHA-256**（本轮重新计算）
- `requests`（解密成功的请求数）
- `events`（日志行数）

其中 **56 个**有解密记录（另有 8 个 run 的日志虽有但无 `解密成功` 行，属启动失败或不完整轮）。

---

## 2. 关键 run 一览（本专项反复引用）

| run | SHA-256 前缀 | 角色 |
|---|---|---|
| `ONCE_20261026_220815` | `BF650058EA8027F0` | **最后一次成功连接** |
| `ONCE_20261026_233111` | `495B9501823E8CB1` | 第一次失败（紧邻成功 83 分钟） |
| `ONCE_20261027_202345` | `FC9843E1778EDCA1` | 证明房间路径**也能**走到 mmstart |
| `ONCE_20261028_224009` | `264E9D716CB265CA` | 首次出现行为差异 |
| `ONCE_20261029_103202` | `EFA502A834214B6F` | E1（B2 形态，未走到 mmstart） |
| `ONCE_20261029_002046` | 见索引 | 最新一轮房间路径 |

---

## 3. 文档类证据

| ID | 路径 | 用途 |
|---|---|---|
| `DOC-ROOM_PROTOCOL_COMPLETE_20261028.md` | `docs/` | 房间三层结构（209 条样本） |
| `DOC-ROOM_DIRECTION_SPLIT_20261028.md` | `docs/` | 上下行格式不同 |
| `DOC-ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md` | `docs/` | 路由键 = roomId 高低 32 |
| `DOC-LOBBY_TRAFFIC_GAP_20261027.md` | `docs/` | 20 个订阅零推送 |
| `DOC-AB_MEMBERCOUNT_RESULT_20261027.md` | `docs/` | memberCount A/B |
| `DOC-GATE_B_INIT_PATH_20261027.md` | `docs/` | 状态机归属 |
| `DOC-DUMP_FORENSICS.md` | `runs/E1_.../` | `0x637000` 位流实测 |
| `DOC-e1.pcapng` | `runs/E1_.../` | 156 B = 0 包 |
| `DOC-lobby_server.py` | `CODOL_VERIFIED_GOLDEN_20261019/` | 服务端分派源码 |
| `DOC-CONNECTION_REGRESSION_DIFFERENTIAL.md` | 053 目录 | 34 run 分离矩阵 |

---

## 4. 证据等级标注规则

本专项统一使用四档：

| 标记 | 含义 | 例 |
|---|---|---|
| `L` | 真实日志/字节证明 | `mmstart` 原文、请求序列 |
| `S` | 源码推断 | "服务端应写 coop_map.txt" |
| `R` | 历史报告声称 | "客户端等了 1~2 秒" |
| `?` | 无证据 | "用户在 UI 点了哪个按钮" |

**每份文档内的关键结论都标了这些档。**

---

## 5. 缺失的证据（大厅专项范围内）

| 缺失 | 影响 |
|---|---|
| 任意一轮的网络抓包 | BP-06 无法从字节层确认 |
| 成功轮的客户端内存转储 | BP-04（MyEventHandler）无法确认 |
| 10-24/25 的 run 目录 | 只能引用二手文档 |
| `.gfx` 反编译 | BP-01 无法推进 |
