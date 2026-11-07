# ★ 突破：queue 恢复 + 认证通过 + 握手闭合 + st 4→5（2026-10-05 14:59）

> 承接 `HANDOFF_20261005_PUSH_TO_LOBBY.md`。
> **本轮把主阻塞链从「认证后不推进」推进到了「st=5 / DWLOBBY_PUMP_SUCCESS」**。
> 弹窗仍复现（`Address Fail | result = -3` 仍在）。
> 剩余差异已用参考实现逐帧对照**精确定位**，见 §4。

> ⚠️ **更正**：本文档早期草稿曾据 48 字节截断判断「Address Fail 已消失」，
> **该判断是错的**。放大到 512 字节后确认它仍在。以 §4 为准。

---

## 0. 一句话

```
根因是 `auth_template749.on`。它自 13:28 启用后, 客户端再也没发过 /queue/。
关掉它 -> queue 立刻回来 -> DW_ACCOUNT_LOGIN_COMPLETE -> 0x81/0x82/0x83 全闭合
-> uA50=5 / sub_state=9 / obj_code=700 / st 4->5 / DWLOBBY_PUMP_SUCCESS
```

---

## 1. 复现命令（有效配方，照抄）

```powershell
# 0) 前提: 关闭 749 模板(见 §2)

# 1) 提权代理
Start-Process -FilePath "cmd.exe" -ArgumentList '/c','"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_elevated_agent_admin.cmd"' -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py ping"      # 期望 debug_privilege=true

# 2) 认证服务
Start-Process -FilePath "python.exe" -ArgumentList @('-X','utf8','-u','CODOLServer\lobby3074\fake_auth_tls.py') -WorkingDirectory "D:\BaiduNetdiskDownload\使命召唤OL" -WindowStyle Hidden

# 3) 主实验
python -X utf8 "CODOLServer\_mainline\_e57a5c_experiment.py" `
  --sandbox "D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929" `
  --attempts 1 --seconds 150 `
  --poke-port 3074 --plain-port 3074 --observer-lobby-port 3074 `
  --compat4 --patch-delay 42 --serve-delay 30 --patch-85-pass --reply-85-task
```

⚠️ 三个端口**必须都是 3074**，与 `dwauth.ini` 一致。
（`--plain-port 8446` 时客户端按 dwauth 去连 `127.0.0.2:3074`，没人接 → `DW_LOBBY_ERROR`。）

---

## 2. 根因：`auth_template749.on`

| 时刻 | 事件 |
|---|---|
| 13:03 | 最后一次 `/queue/` 请求 |
| 13:28 | `auth_template749.on` 创建（应答改用 749 模板，1420 字节） |
| 13:28 之后 | **queue 再也没出现过**，直到本轮 |
| 14:47 | 本轮把它改名禁用 |
| 14:54 | queue 立刻回来（#1 #2 #3） |

**为什么之前的「应答形状已否证」结论是错的**：13:47 会话文档 §5 记录「应答体形状/大小已否证」，
但那时 queue 早已消失 —— 那次否证是在**错误的判据**上做的：
既然客户端连 queue 都不发，改应答形状当然看不出差别。

**当前状态**：`auth_template749.on` 已改名为
`auth_template749.on.disabled_20261005_1447`（可回滚）。
启用 749 时 `/auth/` 应答 1420 字节；禁用后 2244 字节 —— 后者才是能走通的形状。

---

## 3. 本轮实测证据

### 3.1 queue 全链路（`CODOLServer\lobby3074\auth3074.log`，14:54）

```
[POST  /auth/]                                -> 200 task=32->57 (2244 字节)
[PUT   /v1.0/title/-2047582/queue/0/member/16701785630074219790]
       DW-Server-Ticket: 3q2974OiweD/Hj1ce5q52PcWNVRzkrHQ7w4tTGuKqcjn...
       DW-Server-Ticket-Size: 128
       DW-Client-Ticket: OHVr8pIn014uDL7Y3/SlngA=
       DW-Client-Ticket-Size: 129
       DW-Ticket-Seed: 3379735364
                                              -> 200 queue reply (236 字节)
[GET   ...queue...]  -> 200 (236 字节)
[GET   ...queue...]  -> 200 (433 字节)   ← 含 lsg_server_ticket
```

### 3.2 明文大厅握手（`logs\E57A5C_20261005_145650_a1\plain.jsonl`）

```
listen  127.0.0.2:3074
recv    28B hello: c8 00 00 00 c8 00 00 00 d2 00 00 00 dc 00 00 00 00 00 08 00 a9 9c 98 ca cb d5 04 d7
sent_81 len=204 magic=220
recv    153B: 95 00 00 00 ab 82 ...        (0x82 stage1)
echo_from_observer  echo8=ec f4 0e 0a a1 3b 4f bf
keys_ready_before_83  aes_out=71208e390205945f670bc9aee9d62e83
sent_83 len=204
```

### 3.3 任务应答（4 条，全部 hmac_ok=true，seq 回显已生效）

```
rx_task  seq=1 hmac_ok=true service=71 task=4  -> tx_task_reply reply_id=1 seq=1 task=4
rx_task  seq=2 hmac_ok=true service=71 task=3  -> tx_task_reply reply_id=2 seq=2 task=3
rx_task  seq=3 hmac_ok=true service=71 task=7  -> tx_task_reply reply_id=3 seq=3 task=7
rx_task  seq=4 hmac_ok=true service=71 task=9  -> tx_task_reply reply_id=4 seq=4 task=9
```

### 3.4 客户端终态（两轮一致：`145658` 90 s 与 `145954` 150 s）

```
uA50=5  sub_state=9  obj_code=700  http=5/200  lobReq5e8=3  lobReq5ec=5
st 4 -> 5        dw_state_name=DWLOBBY_PUMP_SUCCESS
```

**这已经达到 13:47 会话文档 §2.2 定义的期望值**（uA50=3→实测 5，sub_state=9，obj_code=700）。

---

## 4. ★ 新卡点：弹窗在 st=5 之后仍然出现

```
73.774  WINDOW_NEW class=#32770 text=致命错误
73.775  DLG_CHILD text=与大厅服务失去连接
```

两轮都在 **73.7~73.9 s** 弹（连接约在 41 s 建立 → 弹窗在连接后约 33 s）。

**这推翻了 10-04 文档的弹窗路径假设**。那份文档说：

```
约 +52 s 后 0x8037E4 把 st 清零并标记 DWLOBBY_PUMP_DISCONNECTED
-> 0x7F25B0 返回 4 -> 0x7EF254 弹窗
```

但实测 **st 一直是 5、dw_state_name 一直是 DWLOBBY_PUMP_SUCCESS**，
弹窗照样出现。所以弹窗**不是**由 st 清零触发的，另有路径。

## 4. ★★ 剩余差异：参考实现逐帧对照（决定性）

把参考实现（**用户确认进过大厅**）的成功轮
`F:\桌面\ol\大厅\logs\lobby_srv.log` 与本轮
`logs\E57A5C_20261005_151128_a2\plain.jsonl` 并排：

```
参考: 71/4 -> 71/10 -> 10/12 -> 80/70 -> 12/6 -> 6/5 -> 8/1 -> 8/2 -> 10/21 x10 -> ...
                 ^^^^^ 正常流程
我们: 71/4 -> 71/3  -> 71/7  -> 71/9  -> (断流)
              ^^^^^^^^^^^^^^^^ 这两条是**错误上报**, 不是业务请求
```

### 4.1 同一 task 的载荷长度不同 —— 客户端初始状态就不同

```
71/4:  参考 declared=84      我们 declared=212
```

同一个 task，客户端构造的内容完全不同。

### 4.2 `Address Fail` 仍在（完整 payload，512 字节采样）

```
seq=2 svc=71 task=3 declared=147
  "UserWarning|${TIMESTAMP_OFFSET(0)}|1649370|1234605616436508552|
   16701785630074219790|${CODOID(16701785630074219790)}|
   Address Fail|result = -3"

seq=3 svc=71 task=7 declared=370
  "ComError|${TIMESTAMP}|...|@SF_UI_DW_LIVE_DISCONNECTED|
   ${ZONEID(16701785630074219790)}"
```

### 4.3 ★ 参考实现的成功日志里**完全没有**这些错误

```
grep "Address Fail|UserWarning|ComError|DISCONNECT" F:\桌面\ol\大厅\logs\lobby_srv.log
→ 0 命中
```

⇒ **`Address Fail -3` 不是"无害遥测"，它是失败标志**：
只要客户端还在报它，就说明 seq=1 之后它就走了失败分支，
于是 seq=2 发的是 `71/3`(UserWarning) 而不是参考的 `71/10`(正常流程)。

### 4.4 ★ 0x87 / 0x89 arm 那条路可以整条作废

**裁决依据**：参考实现（进过大厅）里**根本没有 0x87/0x89 帧** ——
`lobby_server.py` / `codol_crypto.py` 里搜 `0x87|0x89|inner|arm` 只命中
任务应答的 TLV 构造，没有任何 arm 帧。它只做 `u32 len | 0x01 | TLV`。

所以主手册 §5.27.5 那套「构造合法内层 0x89 满足 0xBA0FF0」的方向，
以及 §19~§27 的「arm 失败」追查，都是**历史误判**。
这与 13:47 会话文档 §3.4 的结论一致（`644` 不是必要条件）。

### 4.5 已排除：`Address Fail` 不是 TCP connect 失败

本轮 ETW（`runs\NET_CAPTURE_ELEVATED_20261005_151133\game_rt_report.md`）：

```
共 26 次 connect；成功 26，失败 0
```

早期那些 `0.0.0.1:8081/:80/:443`（err 0xC000006C）的失败连接**已经没有了**。
所以 `-3` 是**应用层判定**，不是网络层。

### 4.6 ★ 服务端侧已全部对齐并排除（2026-10-05 15:40 追加）

逐项与参考实现（`F:\桌面\ol\大厅\`）对齐后**全部一致**，仍报 `Address Fail`：

| 维度 | 参考 | 我们 | 结论 |
|---|---|---|---|
| `/auth/` 请求 `blen` | 190 | 190 | 一致 |
| `auth_task` | 10 | 10 | 一致 |
| `title_id` | **1002** | **1002** | 一致（此前"参考是 0"的判断是错的） |
| 应答 `auth_task` | 10→11 | 10→11 | 一致 |
| 应答字节数 | 2239 | 2244 | 差 5 字节（字段顺序/空白），非结构性 |
| 应答字段集 | ret/code/auth_task/status/success + data + profile + 三个 ticket | 同 | 一致 |
| 票据公式 | `DE AD BD EF + (k*31+7)&0xFF` | 同 | 一致 |
| 端口 | 3074/3074 | 3074/3074 | 一致 |
| 任务应答结构 | `u32 len \| 0x01 \| TLV` | 同 | 一致 |
| 数据分派表 | 10/21、10/12、8/1、8/2、80/130、93/1 | 同（已搬） | 一致 |

**唯一剩余的结构性差异**是客户端发出的 `71/4` 载荷本身：

```
参考 field1 = "nQloP0oCVWR6RDJS" (16B ASCII)   field2 = "++++++++++++++++"
我们 field1 = 全零 (16B)                        field2 = 全零
参考 declared=84                                我们 declared=212
```

`71/4` 是**客户端自报**的机器/会话标识。两边字段布局相同、内容不同 ——
这正是"客户端初始状态不同"的直接体现，而它是**客户端侧**的，服务端改不了。

### 4.7 已试并否证（2026-10-05 15:40）

| 尝试 | 结果 |
|---|---|
| 延后 20 s 发布 TAS SHM（发布成功，524288 B） | `title_id` 仍 1002，`71/4` 仍 declared=212，`Address Fail` 仍在 |
| `auth_iv0.on`（`response.iv_seed=0`，代码注释称 0xB984E7 要求） | **无变化**，已禁用（`.disabled_20261005_1540`） |
| 0x87/0x89 arm 真纳 | 参考实现根本没有这两个帧 —— 整条路作废（§4.4） |

### 4.8 参考实现是在另一台机器上跑通的

F: 盘 `HANDOFF.md` 记录其工作目录是 `e:\codol tae`、游戏在 `E:\使命召唤OL\` ——
**不是本机**。所以「参考能进、我们不能」的剩余差异，可能落在
客户端侧环境（ACE/TP3 前置、会话标识生成、zone 数据），而不是服务端协议。

### 下一步（按此顺序）

1. **`title_id`**：参考成功轮 `title_id=0`，我们恒 `1002`。
   13:47 文档 §3.3：是否发布 `TCLS_SHAREDMEMEMORY<pid>` 决定它。
   本轮试过延后 20 s 发布，但发布器没触发（日志停在 `waiting 20s`，
   游戏在 20 s 内就结束/未被识别），`title_id` 仍是 1002。
   → **下一轮先把这个发布真正做成**，看 `title_id` 转 0 后
   `71/4` 的 declared 是否从 212 变成参考的 84。
   这是目前唯一能对上的结构性差异。
   ⚠️ 更正：§4.6 已实测参考成功轮**也是 `title_id=1002`**，
   "参考是 0"来自文档另一条记录，不是这条成功链路。此方向**优先级降低**。
2. **`71/4` 的 field1/field2**（参考 `"nQloP0oCVWR6RDJS"` / `"+++..."`，我们全零）：
   这是客户端自报的会话标识。值得查它由哪个内存/配置生成，
   能否在观察器里定位写入点。
3. **不要**再走 0x87/0x89（§4.4）；**不要**再用 `644` 当判据；
   **不要**再改应答形状（§4.6 已逐项对齐）。

---

## 5. 本轮改动

| 文件 | 改动 |
|---|---|
| `CODOLServer\lobby3074\auth_template749.on` | **禁用**（改名 `auth_template749.on.disabled_20261005_1447`，可回滚） |

（其余沿用 `HANDOFF_20261005_PUSH_TO_LOBBY.md` §6：
seq 回显、数据分派表、`--observer-lobby-port` 透传。）

---

## 6. 已否证（不要再试）

| 项 | 结果 |
|---|---|
| `--plain-port 8446` + `--observer-lobby-port 3074` | 客户端按 dwauth 连 `127.0.0.2:3074` → `DW_LOBBY_ERROR` |
| `--no-poke` | 会连 `PokeLobbyGlobals` 一起关掉 → 客户端走 `auth_task=32` 卡死路径 |
| 过早发布 TAS SHM（游戏刚起来就注入） | 客户端 10 s 内早退 |
| 「应答形状/大小已否证」 | **结论作废** —— 那次否证时 queue 已消失，判据是假的。形状确实重要（§2） |
| 「`auth_task=32` 必然卡死」 | **需修正** —— 突破轮 `/auth/` 走 `task=32`（2244 B），照样到 st=5；失败轮多为 `task=10`（2241 B）。二者由 `PokeLobbyGlobals`(t≥20) 竞态决定，不是"32 必死" |
| 「Address Fail 已消失」 | **错**（48 字节截断造成的误判）。放大到 512 字节后确认仍在 |
| 「Address Fail 是网络问题」 | 否证：本轮 26 次 connect 全成功，0 失败 |

---

## 7. 当前环境状态（15:20）

```
hosts       127.0.0.1 formal-zone-auth.codol.qq.com
            127.0.0.2 formal-zone-lsg.codol.qq.com
dwauth.ini  3074 / 3074 / 0x03EA
auth 服务   127.0.0.1:3074
明文大厅     127.0.0.2:3074（由驱动每轮拉起）
749 模板     已禁用（.disabled 备份在）
残留         无游戏/无 observer 进程（提权代理 5160 + 认证服务 20340 保留）

### 有效配方命中率

`--plain-port/--observer-lobby-port/--poke-port` 全 3074 这组中，
约 **1/3 轮**能跑到 `DWLOBBY_PUMP_SUCCESS`（151136、151633 成功；
151040、150756、150914、150613 为 flake）。**必须多轮重试**。
```
