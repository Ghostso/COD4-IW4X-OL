# CODOL 接手交接 · 2026-10-05（只接手，不推进）

> 承接 `CODOLServer\HANDOFF_20261005_SESSION_1347.md`（最新，13:47）、
> `CODOLServer\HANDOFF_20261004_DW_PUMP_STAGE.md`（§27）
> 与 `CODOLServer\HANDOFF_20261005_KEY_AND_TASK.md`（§28/§29）。
>
> ⚠️ 与 13:47 会话文档的口径冲突，一律以 **13:47 那份**为准；
> 本文件 §3.3 已被按 13:47 文档修正（原判"启动 flake"是错的）。

---

## 0. 一句话现状

```
客户端能稳定起来、能过认证、能完成 0x81/0x82/0x83/0x85 握手（密码学已闭合），
但客户端自己把 DW 大厅判成"断开"，随后走 UI 出口弹窗，大厅 UI 不进入。
```

最新一轮真跑（13:46）之后没有再推进；工作区停在"可随时复跑"的状态。
但 13:00 之后**所有轮次的判据都是假的**——观测器不再导出密钥（见 §3.3），
下一轮的第一件事是修观测侧，不是碰客户端。

---

## 1. 当前主阻塞链（沿用于 10-04 文档，10-05 只修正了判据）

```
启动成功
  -> TCLS / IIPS / ACE 环境满足
  -> 本地认证 + 3074 明文大厅通道建立
  -> 0x81 / 0x82 / 0x83 / 0x85 握手闭合
  -> st=5，DW 泵每帧运行
  -> [0xE59D20]=5 长期等待
  -> 0x622220 返回 0
  -> 0x7EF1FF 不写 [0x849BA34]=3
  -> DW 泵停在跳转表 index 1
  -> gate / cfgobj 不建立
  -> 大厅 UI 不进入
```

已闭合：环境启动、认证、大厅连接、握手密码学、**0x85 收发密钥口径**、**DW 任务应答**。
未闭合：`Address Fail | result = -3` 指向哪个地址，以及 `[0xE59D20]` 等待态的外部推进事件。

---

## 2. 10-05 当日已确认的三件事

| 项 | 结论 | 证据 |
|---|---|---|
| 0x85 AES 密钥位置 | 真实密钥是 `[provider+0x9C]` 前 16 字节（AES-128 key schedule 首块），**不是** 此前一直用的 `[obj+0x620][4:20]` | `HANDOFF_20261005_KEY_AND_TASK.md` §1 |
| DW 任务帧 | 正确密钥下客户端 0x85 立刻解出合法任务帧：`u32 len \| 0x86 \| service=0x47 \| ver=3 \| task=N`；task 4/3/7/9 | 同上 §1 |
| 实跑应答 | KEYTASK2 轮 3 帧任务全部 `hmac_ok=true`，客户端 `5ec 1→4` 表示收下并消费 | 同上 §29.2 |

**判据已修正**：`[obj+0x644]`（0x87 arm）**不是**进大厅的必要条件，它在正确的任务应答流里根本不被驱动。
§19~§27 追的"arm 失败"整体作废。

**当前唯一有效判据**：客户端还抱不抱怨

```
71/3 UserWarning … Address Fail | result = -3
71/7 ComError    … @SF_UI_DW_LIVE_DISCONNECTED … ${ZONEID(16701785630074219790)}
```

只要这两条还在，客户端就仍把 DW 大厅判成断开。

---

## 3. 工作区即时状态（2026-10-05 13:46 后快照）

### 3.1 进程

* 无 `codoMP_client_shipRetail`、`AboProbe`、`IIPSHostApp`、python 实跑进程在跑；客户端 13:46 已退出。
* 未做任何清理动作，保持停跑时的原样。

### 3.2 环境（复跑前必须确认这几项仍在）

```
hosts     127.0.0.1 formal-zone-auth.codol.qq.com
          127.0.0.2 formal-zone-lsg.codol.qq.com
沙箱      run_codol_001\sandbox_datafix_20260929
dwauth.ini formal-zone-lsg / formal-zone-auth → 3074，0x03EA
auth      127.0.0.1:3074   fake_auth_tls.py（停跑时需手动起）
明文大厅   127.0.0.2:8446   由驱动每轮起停
```

### 3.3 最后一轮 + ★ 13:05 后的观测侧静默退化（下一轮第一件事）

* 最后一次完整实跑：`run_codol_001\runs\IFS1_ELEVATED_20261005_134626`，life=25.8 s，早退。
* 13:00~13:46 这一批 29 轮里，life 达到 80 s 门槛的只有 `130216`(88.9) 与 `132838`(72.4)，
  其余多为 24~33 s 早退。启动 flake 确实存在（客户端 9~25 s 自退、无 POST，重跑即可），
  但**本批轮次不能只用 flake 解释**。

按 13:47 会话文档 §6 复核，13:05 起观测器静默退化：

| 时段 | `SECRETS_WRITTEN` | `CODEC_KEYS` 计数 | `p604/p608` |
|---|---:|---:|---|
| 12:00–12:09 | 正常 | 140/141/142/98 | 有值 |
| 12:10–12:28 | 0 | 0 | — |
| 12:30–12:36 | 正常 | 119/137 | 有值 |
| **13:00–13:46** | **0** | **0** | `?` |

13:02 起 `CODEC_KEYS` 变成 `p604=?,p608=?`；服务端下游症状为
`keys_wait_timeout` + `hmac_ok=false, have_aes_out=false`。

**这不是客户端回归**：13:42/13:45/13:46 三轮 `/auth/` 都完整走通（请求体、200、
close-notify 全在），与 12:59 健康轮行为一致。是观测器读不到 provider 指针了。

可疑原因（按 13:47 文档给出的概率排序）：

1. 改了 `AboProbe.cs` 后没 `dotnet publish`，跑的仍是旧 `out\`
   （旧版写 `secrets.txt`、新版写 `provider_keys.txt`，路径对不上）→ **先做一次干净 publish 再跑**；

   ⚠️ 接手时已用时间戳部分否证：`AboProbe.cs` = 11:59:44，`out\AboProbe.dll/exe/pdb` = 11:59:48，
   **发布是跟上了的**。所以更可能是后两条。
   （12:54 那次改的是 `run_codol_001\elevated_ifs1_observer.ps1`，不是 `.cs`。）
   仍建议开局做一次干净 publish 排除，但不要把它当主因。

2. ASLR / 布局漂移，`0x08269774 → +0x4F4 → +0x604/0x608` 指针链失效，`ValidPtr()` 判假；
3. `post83Watch` 未置位——整段导出逻辑在 `if (post83Watch && …)` 里，
   与「`CODEC_KEYS` 也几乎为 0」的现象吻合。

修复判据（跑一轮后）：

```powershell
(Select-String -Path "<run>\aboprobe_run\*_events.csv" -Pattern "SECRETS_WRITTEN").Count   # 期望 > 0
(Select-String -Path "<run>\aboprobe_run\*_events.csv" -Pattern "CODEC_KEYS").Count        # 期望 > 50，且 p604/p608 有值
Select-String -Path "CODOLServer\logs\E57A5C_*_a1\plain.jsonl" -Pattern '"hmac_ok": true'  # 期望 > 0
```

### 3.4 代码自检

`CODOLServer\_mainline` / `lobby_server` / `lobby3074` 下 .py 全部 `py_compile` 通过，
唯一编译失败的是 `CODOLServer\_mainline\_add6d4.py`（一次性草稿脚本，不参与任何有效路径）。

---

## 4. 下次开跑：照抄这段即可

⚠️ 13:47 会话文档给出的主命令与我上一版不同，**以此处为准**：
它用 `_e57a5c_experiment.py` 直跑（不走 `_multiround.py`），且**必须带 `--no-poke`**——
`_multiround.py` 会发布 shm，把客户端按回 `auth_task=32` 的签名路径。

```powershell
# 1) 提权代理（UAC）
Start-Process -FilePath "cmd.exe" -ArgumentList '/c','"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_elevated_agent_admin.cmd"' -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping      # 期望 debug_privilege=true

# 2) 账号服务
Start-Process -FilePath "python.exe" -ArgumentList @('-X','utf8','-u','CODOLServer\lobby3074\fake_auth_tls.py') -WorkingDirectory "D:\BaiduNetdiskDownload\使命召唤OL" -WindowStyle Hidden

# 3) 主实验
python -X utf8 "CODOLServer\_mainline\_e57a5c_experiment.py" `
  --sandbox "D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929" `
  --attempts 2 --seconds 100 --plain-port 3074 --poke-port 3074 --no-poke `
  --compat4 --patch-delay 42 --serve-delay 30 --patch-85-pass --reply-85-task
```

观察器改完必须重编译：

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\restore_iips_contract_001\observer2"
dotnet publish -c Release -o out
```

跑完看什么：

1. `logs\E57A5C_*_a1\plain.jsonl` 里有没有 `rx_task` 与 `tx_task_reply`；
2. `...\a1\secrets.txt` 是否出现，且 `aes_out` 非零；
3. 71/3 `Address Fail -3` 与 71/7 `@SF_UI_DW_LIVE_DISCONNECTED` 是否仍在（这是真正的判据）；
4. **不要**看 `644`，它在本流里不该被驱动。

---

## 5. 下一刀该往哪切（优先级沿用 13:47 会话文档 §7）

**P0：先修观测侧（§3.3）**。没有密钥，后面所有实验的判据都是假的。
这一轮不要碰任何客户端侧变量。

**P1：追 `Address Fail | result = -3`**。客户端自报某个地址连不上。
71/3 在 0x83 之后 0.01 s 就上报 ⇒ 握手一完成客户端就去连了某个地址。
优先查 `0.0.0.1`（:8081/:80/:443，err 0xC000006C）与两台被 reset 的外网 IP
`101.226.156.189` / `140.206.164.16`（err 10054）指向哪个服务
（platform / QoS / publisher）。

**P2：逐条打点 `0xB9A470` 的判定顺序**（唯一未量过的一环），看哪一条先判假：

```
1. auth_task == 11
2. code == 700
3. client_ticket base64 → 128B 且 [0..3] 小端 == 0xEFBDADDE
4. server_ticket → 128B
5. extra_data 内层解析：extended_data / cd_key / time_to_live
   （objA 还额外要 username / encrypted_codoid(16B) / encrypted_register_codoid_data(≤1024)）
```

契约全文见 `CODOLServer\lobby_server\mklobby_response.py` 头部注释，
含 735 的两个写入点 `0xB9A59B` / `0xB9A7C7`。
⚠️ 但 F: 盘 `HANDOFF.md` §2.1 实测：在那条线上 `0xBA9980` / `0xBC3E10` 被调用 0 次，
即客户端可能根本不走这段 exe 代码 —— **P2 之前先用一次直挂确认 `0xB9A470` 到底有没有被调用**，否则是空转。

**P3：备选 A/B**：`auth_template749.on` 内层逐字段 A/B（用 `obj_code` 当判据），
或改用 `mklobby_response.build()` 直接产出并比字节数（成功值 2239，我们当前 1420）。

### 当前认证侧的实际卡点（13:47 文档 §4）

客户端**收到并识别我们的 200**（`http_state=5` 闪现、`http_status=200`），
随后**自己关闭连接**（应答后收到 0 字节），不推进 stage：

```
uA50=2  sub_state=6  obj_stage=10  obj_busy=1  obj_code=0
http_state 分布: 3=39, 5=1
```

成功案例要求 `uA50=3 / sub_state=9 / obj_code=700`。

---

## 6. 明确不要再试的（已否证或已作废）

| 假设 | 状态 |
|---|---|
| `[req+0x644]` 是配置链总开关 | 否证（`--poke-644-on-st5` 写成 1，gate 仍 0） |
| `[0x84ABB2F]`（g2f）是卡点 | 否证（st=5 时它本来就是 1） |
| 只要 `0xB7A670` 返回 2 就能开 gate | 否证（已返回 2，0x4A93E0 仍未调用） |
| 用 `--patch-87-gate` 修内层首字节 | 作废（不是当前阻塞点，且会污染自然观测） |
| 用 `[obj+0x620][4:20]` 当 0x85 密钥 | 作废（密钥口径已修正为 `[provider+0x9C][:16]`） |
| `--poke-644-on-st5` 作为进大厅判据 | 作废（644 不该被驱动） |

### 13:47 会话文档 §5 已排除的维度（认证侧，不要重复）

| 维度 | 结果 |
|---|---|
| 应答体形状（嵌套 / +extra_data / 749 模板） | 否证 |
| 应答体大小（1340/1418/1420/2244/3261，成功值 2239） | 否证 |
| `response.iv_seed`（回显 / 置 0） | 否证 |
| `Connection: close` → keep-alive | 否证 |
| 收尾：3s / 8s / 静默挂住 / SHUT_WR | 全否证 |
| 下一跳被丢（应答后字节） | 0 字节，否证 |
| tag8 `1004`→`1002`、不发布 shm、`TCLS\TenProtect` / `SSOPlatform.dll` / `tacc_2_1.dll` 改名 | 全否证（仅 `title_id` 受 shm 影响） |
| 443→8443 portproxy + `lobby_probe_server.py` | 链路验证通，但客户端在 443 路径下**不发连接**；`dwauth` 写 8443 时也完全不连 |

另：`AboProbe.cs` 里 `--patch-85-bufbase`（`0xBA44BE`）补丁长度写错，
实测 `ok=False`、从未生效，建议删除或重写；目前不参与任何有效路径。

---

## 7. 硬边界（不得越界）

### 用户偏好（13:47 会话文档 §9）

* 说「继续推进」= **自主连续推进**，不必每步确认；但破坏性动作、
  需要新建权限的动作**要先说**。
* 用户贴的实跑现象（如「又复现 100 无法连接大厅服务弹窗」）是真实反馈，**当证据用**。
* 沙箱/脚本实验必须**可回滚**（改名/改 ini 都留 `.bak_*`）。
* 日志里**不要出现非 GBK 字符**：`run_all` 用 GBK 重定向 stdout，会把子进程打死。

下一轮开局前先清残留（F: 盘 HANDOFF §6 经验）：

```powershell
Get-Process python,codoMP_client_shipRetail,IIPSHostApp,TP3Helper -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 开关文件现状（`CODOLServer\lobby3074\`）

```
auth_template749.on   在   ← 应答体用归档 749 模板
auth_hold.on          已删
auth_halfclose.on     已删
auth_iv0.on           已删
auth_extra_data.on    已删
```

### 硬边界

* 禁止修改本机网络配置。
* 禁止关闭 / 配置 / 规避 ACE、TenProtect。
* 允许：运行内存写入、`.text` patch、断点、调试器。
* 验收判据：无断线弹窗且 `lobReq5ec` 递增。

---

## 8. 关键文件索引

| 路径 | 用途 |
|---|---|
| `CODOLServer\HANDOFF_20261005_SESSION_1347.md` | **最新（13:47）**，含观测侧退化与 P0-P3 |
| `CODOLServer\HANDOFF_20261005_KEY_AND_TASK.md` | 密钥修正 + 任务应答实跑（§28/§29） |
| `CODOLServer\HANDOFF_20261004_DW_PUMP_STAGE.md` | DW 泵卡点全量推导 |
| `CODOLServer\lobby_server\mklobby_response.py` | 头部注释 = objB/objA 应答契约全文 |
| `CODOL_PROJECT_NODE_ANALYSIS.md` | 172 节点分层模型 |
| `REVERSE_ENGINEERING_SUMMARY.md` | 早期总览（TCLS 交接、工具链） |
| `CODOLServer\_mainline\_e57a5c_experiment.py` | 主实验驱动（`--help` 有全部开关） |
| `CODOLServer\_mainline\_multiround.py` | 多轮跑，只保留 life>=80 s 的有效轮 |
| `CODOLServer\_mainline\_dec85_tasks.py` | 离线解码 0x85 任务帧（只读） |
| `CODOLServer\lobby_server\lobby_plain_probe.py` | 明文大厅探针（含任务应答构建） |
| `restore_iips_contract_001\observer2\AboProbe.cs` | 观察器，改完需 `dotnet publish` |

### 外部参考（F: 盘，只读）

```
F:\桌面\ol\大厅\                     ← 真正进过大堂的工作实现
  CODOL_LOBBY_WORKING_20261002.md / HANDOFF.md / logs\auth3074.log（2239 字节应答那次）
F:\桌面\ol\新建文件夹\                ← 靶场那条线的完整包，含 docs\HANDOFF.md
```
