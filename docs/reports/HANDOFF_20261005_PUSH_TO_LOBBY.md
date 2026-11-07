# CODOL 推进至大厅 · 2026-10-05 下午轮次

> 承接 `HANDOFF_20261005_SESSION_1347.md`。本轮照 F: 盘「已成功进过大堂」的
> 配方对齐了本仓库实现, 修掉两个真实缺口, 并做了 8 轮实跑验证。
> **未进入大厅**, 但把卡点收敛到了一个可打点的具体位置。

---

## 0. 结论

```
已修:  ① 任务应答的 seq 语义   ② 数据下发(此前一律回空对象)
已验:  两端(加解密/应答结构/分派表)字节级对齐, 离线往返通过
未进:  客户端仍停在 "认证后不推进", 卡在建立大厅连接对象之前
```

**这不是回归, 也不是本轮引入的问题** —— 它就是 13:47 会话文档 §4 记录的
那个卡点, 只是现在有了更精确的定位(见 §3)。

---

## 1. 对照 F: 盘配方找到的两个真实缺口

参考实现 `F:\桌面\ol\大厅\`（用户确认**进过大堂**）的成功轮
`logs\lobby_srv.log` 有 **69+ 条**任务, 横跨 service 71/10/8/80/93/3/9/102/68/28/4/21;
而本仓库至今**只收到 4 条 `71/*`** 就断流。差在两处：

### 1.1 应答 seq 语义反了（已修）

```
参考实现: build_task_reply_objects(..., r["seq"], r["task"], srv_seq, ...)
           ↑ seq 回显请求 seq;  srv_seq 只用作 replyId

本仓库旧: build_task_reply(..., task_seq, d["task"], d["seq"])
           ↑ seq 用独立递增计数器, reply_id 才回显
```

已改为与参考实现一致：seq 回显、replyId 自增。主路径与积压帧补答路径
都已改（`lobby_plain_probe.py`）。

### 1.2 数据下发一律回空对象（已修）

F: 盘配方 §9.2 第 8 条把「一律回空对象」明确列为失败原因
（`EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`）。参考实现按 `(service, task)`
分派真实数据；本仓库 `build_task_reply` 的 `objects` 恒为 `()`。

已照抄分派表 + 搬来数据目录：

| 文件 | 改动 |
|---|---|
| `CODOLServer\lobby_server\data\`（新增） | 从 F: 盘复制：`publisher_files/`(10)、`player_profiles/{public,secure}.result`、`user_files/`、`player-account.json` |
| `lobby_plain_probe.py` | 新增 `serialize_file_data()` / `_requested_name()` / `_read_account()` / `_balance_object()` / `reply_objects()`；两处应答调用接入分派 |

分派表（照抄参考实现）：

```
10/21  发行方配置  -> publisher_files/<请求名>      (0x13 0x08 + u32 len + data)
10/12  用户文件    -> user_files/<请求名>
8/1    档案 public -> player_profiles/public.result (原始字节)
8/2    档案 secure -> player_profiles/secure.result
80/130 余额 CP     -> 03 01 08 <u32>
93/1   余额 GP     -> 03 02 08 <u32>
```

⚠️ 注意：本仓库至今解出的任务**全是 `service=71`**，一条 `10/21` 都没收到。
所以这份分派表目前是「装上了但还没被触发」——它解决的是客户端**继续往下走之后**
的那一步。

---

## 2. 新增的透传开关（修端口错配）

诊断中发现：观察器写入客户端大厅 globals 的端口（`--lobby-port-3074`，默认 3074）
此前**无法从驱动命令行覆盖**，而 ps1 链又不透传，导致驱动侧的 `--plain-port`
与客户端实际拨的端口可能对不上。

| 文件 | 改动 |
|---|---|
| `CODOLServer\_mainline\_e57a5c_experiment.py` | 新增 `--observer-lobby-port`（默认 8446），透传给 ps1 的 `-LobbyPort3074` |
| `run_codol_001\capture_elevated_network.ps1` | 新增 `$LobbyPort3074` 参数并转发给 `elevated_ifs1_observer.ps1`（两处调用点） |
| `CODOLServer\_mainline\_shm_watch_publish.py`（新增） | 等游戏进程出现后发布 TAS SHM（等价于 `_multiround.py` 的等待线程） |

---

## 3. ★ 卡点精确定位（下一轮从这里开始）

用 `aboprobe_run\*_state.csv` 最后一行做逐字段对照，差异极其干净：

| 字段 | 健康轮 `113927` | 本轮 `144204` | 含义 |
|---|---|---|---|
| `flag_61f` | `372974593` | **`0`** | ← 主差 |
| `lobby_sub` | `2` | **`0`** | 大厅子对象未建立 |
| `lobby_singleton` | `1007400136` | **`0`** | 未创建 |
| `lobConn4f4` | `1008499720` | **空** | 连接对象指针 |
| `lobReq5e8` | `3`（0x83 完成） | **`0`** | 握手根本没开始 |
| `lobReq5ec` | `4` | **`0`** | 收包计数 0 |
| `cfg_applied` | `1` | `1` | 相同 |
| `lobby_port9780` | `8446` | `3074` | 见 §2 |
| 尾部魔数 | — | `efbeadde` / `3735928559`(0xDEADBEEF) | 票据已就位 |

**含义**：客户端拿到了合法票据（0xDEADBEEF 魔数在位）、`cfg_applied=1`，
但**从未创建大厅连接对象**，因此没有 `CONN_D9` / `POST83` / 任何 0x82/0x83/0x85。
它在 `t=38.3 s` 以 `exitcode=0` **主动退出**——正好是大厅连接时刻（约 39 s）之前。

这与 F: 盘 `HANDOFF.md` §2 的实测结论同构：在那条线上 `0xBA9980` / `0xBC3E10`
**被调用 0 次**，客户端根本不走那段 exe 应答处理代码。

### 下一轮建议（按此顺序）

1. **确认 `flag_61f` 是什么**：健康轮 372974593，本轮恒 0。它是唯一的主差，
   且名字上就是个「门」。先在观察器里给它加一条采样，看它在健康路径下
   是何时、由谁写成的。
2. **确认 `0xB9A470` 到底有没有被调用**（13:47 文档 P2 的前置）——否则打点是空转。
3. 在此之前**不要**再改应答内容/端口/补丁组合：本轮已证明参数层面与健康轮一致
   （见 §4），继续 A/B 是空转。

---

## 4. 本轮实跑记录（8 轮，全未进大厅）

| 轮次 | 关键参数 | 结果 |
|---|---|---|
| `141522` | `--no-poke` + 3074 | life=100.0，无 CONN_D9；`--no-poke` 会连 `PokeLobbyGlobals` 一起关掉 |
| `142207` | 带 poke, 默认 lobby-port | `auth_task=32`（DSA 签名路径），无 CONN_D9 |
| `142554`/`142803` | 带 poke, `--plain-port 8446` | `DW_ACCOUNT_ERROR`；发现 `--plain-port` 未透传给观察器 |
| `143305`/`143515` | 加 `--observer-lobby-port 8446` | `auth_task=10`（正确路径），仍 `DW_ACCOUNT_ERROR` |
| `143856` | + SHM 发布 | 客户端 10.2 s 早退（发布过早），`states=[]` |
| `144014`/`144204` | 回退 `--observer-lobby-port 3074`（与 12:59 健康轮一致） | `auth_task=10` + 200 + close-notify 全通，仍 `DW_ACCOUNT_ERROR` |

**参数层面已与健康轮 `125955` 逐字段一致**，差异不在参数。

---

## 5. 已验证（离线，可复现）

```powershell
python -X utf8 -c "
import sys, struct; sys.path.insert(0, r'CODOLServer\lobby_server')
import lobby_plain_probe as p
print(p.reply_objects(10,21,b'\x10\x00\x10MOTD.info\x00\x00')[1])   # publisher MOTD.info (29 字节)
print(p.reply_objects(8,1,b'')[1])                                    # profile public.result (33428 字节)
"
```

端到端往返（构造 10/21 任务帧 → 解密 → 分派 → 应答 → 解回）：

```
decoded: seq=7 service=10 task=21 hmac_ok=True payload=b'\x10\x00\x10MOTD.info\x00\x00'
reply_objects: publisher MOTD.info (29 字节) n=1
reply frame len 114 type 0x85
inner: len=61 marker=0x01
inner hex: 0a07...0008 00000000 0315 08 01000000 08 01000000 1308 1d000000 3b20...
```

114 字节、结构与参考实现一致。

`_mainline` / `lobby_server` 下 .py 全部 `py_compile` 通过
（唯一失败仍是既有的草稿 `_add6d4.py`）；
`capture_elevated_network.ps1` 语法解析通过；`AboProbe` 已干净 `dotnet publish`。

---

## 6. 本轮改动文件清单

| 文件 | 改动 |
|---|---|
| `CODOLServer\lobby_server\lobby_plain_probe.py` | seq 回显 + `reply_objects()` 分派表 + `DATA_DIR` |
| `CODOLServer\lobby_server\data\`（新增目录） | 从 F: 盘复制的下发数据 |
| `CODOLServer\_mainline\_e57a5c_experiment.py` | 新增 `--observer-lobby-port` |
| `run_codol_001\capture_elevated_network.ps1` | 新增 `-LobbyPort3074` 透传（两处） |
| `CODOLServer\_mainline\_shm_watch_publish.py`（新增） | SHM 等待发布器 |
| `HANDOFF_20261005_TAKEOVER_NO_ADVANCE.md` | 接手盘点（上午） |
| 本文档 | 本轮记录 |

未改动：游戏文件、`hosts`、`dwauth.ini`、ACE/TenProtect 相关任何东西。
