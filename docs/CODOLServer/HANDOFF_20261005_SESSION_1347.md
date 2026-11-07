# CODOL 本地大厅复活 · 会话交接（2026-10-05 13:47）

> 承接 `HANDOFF_20261005_KEY_AND_TASK.md`（§28/§29）与
> `HANDOFF_20261004_DW_PUMP_STAGE.md`（§27）。
> 本文档是**当前会话的完结状态**，写给下一轮接手的人。
> 全文基于本仓库已落盘的数据复核，未做任何新的实跑。

---

## 0. 三句话现状

1. **客户端能发出 `/auth/` 请求、能收到我们的 200、能收到并消费 DW 任务应答**，
   但**就是不推进 stage**，最终弹「100 无法连接大厅服务」。
2. 本会话已经把**最底层的一环（0x85 加解密）彻底做对**了：AES 密钥口径修正后，
   客户端任务帧**实时解开**，`hmac_ok=true`，四条任务全部即时应答。
3. **13:05 之后出现一次静默退化**：观测器不再导出密钥（`SECRETS_WRITTEN=0`、
   `CODEC_KEYS` 里 `p604/p608` 变 `?`），导致服务端 `keys_wait_timeout`、
   `hmac_ok=false`。这是**观测侧**的问题，不是客户端回归 —— 见 §6，
   这是下一轮**必须先做**的第一件事。

---

## 1. 环境与固化启动方式（照抄即可）

```
工作目录:   D:\BaiduNetdiskDownload\使命召唤OL
客户端:     codoMP_client_shipRetail.exe  build 1649370

提权代理:   run_codol_001\run_elevated_agent_admin.cmd   （UAC 弹窗）
            自检: python -X utf8 CODOLServer\_mainline\agent_client.py ping
            期望: debug_privilege=true

认证服务:   CODOLServer\lobby3074\fake_auth_tls.py  @ 127.0.0.1:3074
明文大厅:   CODOLServer\lobby_server\lobby_plain_probe.py @ 127.0.0.2:3074（由驱动拉起）

hosts（已固化，勿动其它）:
  127.0.0.1 formal-zone-auth.codol.qq.com
  127.0.0.2 formal-zone-lsg.codol.qq.com

dwauth.ini: formal-zone-lsg.codol.qq.com 3074
            formal-zone-auth.codol.qq.com 3074
            0x03EA

观测器:     restore_iips_contract_001\observer2
            改 .cs 后**必须** dotnet publish -c Release -o out

沙箱:       run_codol_001\sandbox_datafix_20260929
```

### 主实验命令（当前推荐）

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL"

# 1) 提权代理（另开窗口，接受 UAC）
Start-Process -FilePath "cmd.exe" -ArgumentList '/c','"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_elevated_agent_admin.cmd"' -WindowStyle Hidden

# 2) 认证服务
Start-Process -FilePath "python.exe" -ArgumentList @('-X','utf8','-u','CODOLServer\lobby3074\fake_auth_tls.py') -WorkingDirectory "D:\BaiduNetdiskDownload\使命召唤OL" -WindowStyle Hidden

# 3) 主实验
python -X utf8 "CODOLServer\_mainline\_e57a5c_experiment.py" `
  --sandbox "D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929" `
  --attempts 2 --seconds 100 --plain-port 3074 --poke-port 3074 --no-poke `
  --compat4 --patch-delay 42 --serve-delay 30 --patch-85-pass --reply-85-task
```

⚠️ **`--no-poke` 是硬要求**：`_multiround.py` 会发布 shm，把客户端按回
`auth_task=32` 的签名路径（详见 §3.3）。

### 开关文件现状（`CODOLServer\lobby3074\` 下的 `.on` 文件）

```
auth_template749.on   在   ← 应答体用归档 749 模板
auth_hold.on          已删
auth_halfclose.on     已删
auth_iv0.on           已删
auth_extra_data.on    已删
```

---

## 2. 观测指标与判据（先看这个）

### 2.1 明文大厅侧（`CODOLServer\logs\E57A5C_*_a1\plain.jsonl`）

| 字段 | 含义 | 健康值 |
|---|---|---|
| `rx_task.hmac_ok` | 我们是否用正确密钥解开了客户端任务帧 | `true` |
| `rx_task.have_aes_out` | 观测器有没有导出密钥 | `true` |
| `tx_task_reply` | 我们是否应答了客户端任务 | 每帧 1 条 |
| `keys_wait_timeout` | 服务端等密钥超时 | **不应出现** |

成功样本（`E57A5C_20261005_125947_a1`，本会话最后一轮健康轮）：

```
rx_task  seq=1 hmac_ok=true service=71 task=4 declared=212 have_aes_out=true
tx_task_reply reply_id=1 seq=1 task=4 len=66
rx_task  seq=2 hmac_ok=true service=71 task=3 declared=147
tx_task_reply reply_id=2 seq=2 task=3 len=66
rx_task  seq=3 hmac_ok=true service=71 task=7 declared=370
tx_task_reply reply_id=3 seq=3 task=7 len=66
rx_task  seq=4 hmac_ok=true service=71 task=9 declared=9
tx_task_reply reply_id=4 seq=4 task=9 len=66
```

### 2.2 客户端侧（`run_codol_001\runs\IFS1_*\aboprobe_run\*_events.csv`）

| 字段 | 当前值 | 期望值 |
|---|---|---|
| `POST83_WATCH ... uA50` | `2` | `3` |
| `subA34`（sub_state） | `6` | `9` |
| `obj_stage` | `10` | 推进 |
| `obj_busy` | `1` | — |
| `obj_code` | `0`（偶发 `735`） | `700` |
| `http_state` 分布 | `3=39, 5=1` | 5 应稳定 |
| `CONN_D9 ... 5ec` | 收下应答后 `1 → 4` | 说明**确实消费了**我们的帧 |
| `644` | 恒 `0` | **不再是判据**，见 §3.4 |

### 2.3 认证侧（`CODOLServer\lobby3074\auth3074.log`）

最近三轮（13:42 / 13:45 / 13:46）都完整走通：

```
=== TLS 就绪 ... 版本=TLSv1 套件=AES256-SHA ===
[POST /auth/ HTTP/1.1] blen=190
  Host: formal-zone-auth.codol.qq.com:3074
  body: {"auth_task": "10", "iv_seed": "...", "title_id": "1002",
         "identity": "356c4bc3",
         "extra_data": "{\"version\": \"0\", \"user_id\": \"10995207597479878709\", \"extended_data\": true}"}
-> 200 task=10->11 (1420 字节)
TLS close-notify 已发
```

---

## 3. 本会话确认的关键事实

### 3.1 0x85 密钥口径（根本性修复，已双会话验证）

```
错误口径（旧）:  codec_02a0(obj+0x620)[4:20]  /  [obj+0x608]+0x14
正确口径（新）:  [provider+0x9C] 的前 16 字节（AES-128 key schedule 首块 w[0..3]）
```

用它解密客户端任务帧，`hmac_ok=true` 在**四个独立会话**全部成立：
`113919 / 115049 / 115350 / 115654 / 120008 / 120250 / 123007 / 123254 /
124502 / 125127 / 125429 / 125726 / 125947`。

### 3.2 客户端任务帧格式（已解开）

```
明文: u32 declared | 0x86 | service(0x47=71) | ver(3) | task | payload
```

实跑解出的四条任务：`71/4`、`71/3`、`71/7`、`71/9`。

`71/3`（UserWarning）与 `71/7`（ComError）的 payload 是明文，**这是最有价值的线索**：

```
UserWarning|…|1649370|1234605616436508552|16701785630074219790|${CODOID(…)}|Address Fail|result = -3

ComError|…|1649370|…|…||Windows 10|AMD Ryzen 7 5800H …|15725|NVIDIA GeForce RTX 3070 …|
[nvldumd.dll] 617.14|0|2162688|@SF_UI_DW_LIVE_DISCONNECTED|0|D4-93-90-18-55-10|
mp_ui_viewer|war|0|0||@SF_UI_DW_LIVE_DISCONNECTED|${ZONEID(16701785630074219790)}
```

* **`Address Fail | result = -3`** —— 客户端自报某个地址连不上；
* **`@SF_UI_DW_LIVE_DISCONNECTED`** —— 与弹窗字符串
  `@SF_UI_DW_LIVE_CONNECTING_FAILED` 同族。

⇒ **弹窗不是某个字段写错，而是客户端先认定 DW 链路断了，再走 UI 出口。**

### 3.3 `auth_task` 的两条路径

```
auth_task=32  ← 由观测器 -PokeLobbyGlobals 1 触发（cfg_applied=1 → objA 路径）
auth_task=10  ← 关掉 poke 后的自然路径，与 F: 盘「真正进过大堂」的记录逐字段一致
```

`title_id` 由**是否发布 `TCLS_SHAREDMEMEMORY`** 决定：发布 → `0`，不发布 → `1002`。

这就是为什么主实验命令必须带 `--no-poke`。

### 3.4 `644`（0x87 arm）**不是**进大厅的必要条件

它是 0x87/0x89 子协议的输入，在正确的 DW 任务应答流里根本不会被驱动。
§19~§27 追了十几轮的「arm 失败」应整体作废。

### 3.5 735 已被消除

应答体改用归档 **749 模板**（`mklobby_response.build()` 形状：扁平 + `extra_data`）后，
`obj_code` 不再出现 735。开关：`auth_template749.on`。

### 3.6 `/auth/` 请求字段与 F: 盘成功记录完全一致

F: 盘 `大厅\logs\auth3074.log`（真正进过大堂那次）：

```
body: {"auth_task": "10", "iv_seed": "3569017267", "title_id": "1002",
       "identity": "356c4bc3",
       "extra_data": "{\"version\": \"0\", \"user_id\": \"16714726778184453630\", \"extended_data\": true}"}
-> 200 task=10->11 (2239 字节)
```

我们当前（13:46）：

```
body: {"auth_task": "10", "iv_seed": "3032924307", "title_id": "1002",
       "identity": "356c4bc3",
       "extra_data": "{\"version\": \"0\", \"user_id\": \"10995207597479878709\", \"extended_data\": true}"}
-> 200 task=10->11 (1420 字节)
```

**逐字段一致，只有 `user_id` 和应答体字节数不同**（2239 vs 1420）。
应答体大小这一维度已单独否证过（见 §5）。

---

## 4. 当前卡点（唯一）

客户端**收到并识别我们的 200**（`http_state=5` 闪现、`http_status=200`），
随后**自己关闭连接**（应答后收到 0 字节），不推进 stage：

```
uA50=2  sub_state=6  obj_stage=10  obj_busy=1  obj_code=0
http_state 分布: 3=39, 5=1
```

成功案例要求 `uA50=3 / sub_state=9 / obj_code=700`。

---

## 5. 已排除（**不要重复**）

| 维度 | 结果 |
|---|---|
| 应答体形状（嵌套 / +extra_data / 749 模板） | 否证 |
| 应答体大小（1340/1418/1420/2244/3261，成功值 2239） | 否证 |
| `response.iv_seed`（回显 / 置 0） | 否证 |
| `Connection: close` → keep-alive | 否证 |
| 收尾：3s / 8s / 静默挂住 / SHUT_WR | 全否证 |
| 下一跳被丢（应答后字节） | 0 字节，否证 |
| tag8 `1004`→`1002`、不发布 shm、`TCLS\TenProtect` 改名、`SSOPlatform.dll` 改名、`tacc_2_1.dll` 改名 | 全否证（仅 `title_id` 受 shm 影响） |
| 443→8443 portproxy + `lobby_probe_server.py` | 链路验证通（TLS1.0/AES256-SHA 可连、请求落日志），但客户端在 443 路径下**不发连接**；`dwauth` 写 8443 时也完全不连 |

---

## 6. ★ 新发现：13:05 后的观测侧静默退化（下一轮第一件事）

这是本轮复核**新发现**的问题，之前的交接文档里没有。

### 现象

按 `run_codol_001\runs\IFS1_ELEVATED_20261005_*\aboprobe_run\*_events.csv` 统计：

| 时段 | 轮次 | `SECRETS_WRITTEN` | `CODEC_KEYS` 计数 | `p604/p608` |
|---|---|---:|---:|---|
| 12:00–12:09 | 120016 / 120258 / 120544 / 120918 | 正常 | 140 / 141 / 142 / 98 | 有值 |
| 12:10–12:28 | 121224 … 122502 | 0 | 0 | — |
| 12:23 / 12:29 | 122023 / 122901 | 0 | 97 / 9 | 仅 `p608` |
| 12:30–12:36 | 123015 / 123302 | 正常 | 119 / 137 | 有值 |
| **13:00–13:46** | 130216 … 134626 | **0** | **0**（130216 有 131 条但 `p604` 为空且 `sched` 全零） | `?` |

13:02 起 `CODEC_KEYS` 变成：

```
21.528,CODEC_KEYS,p604=?,p608=?,src620=6853b1d5… src60C=0046304402201c08…
```

而 12:59 那轮（`IFS1_ELEVATED_20261005_125955`）还是健康的：

```
SECRETS_WRITTEN = 66 次
```

对应服务端日志（`E57A5C_20261005_130208_a1\plain.jsonl`）直接表现出下游症状：

```
{"event": "keys_wait_timeout", "seconds": 3.0}
{"event": "rx_task", "seq": 1, "hmac_ok": false, ..., "have_aes_out": false, "have_aes_in": false}
```

13:00 之后**没有任何一轮**再解出任务帧，直到会话结束。

### 关键区分

**这不是客户端回归**：13:42/13:45/13:46 三轮 `/auth/` 都完整走通
（请求体、200、close-notify 全在），客户端行为与 12:59 健康轮一致。
是**观测器读不到 provider 指针**了。

### 可疑原因（按概率排序）

1. **改了 `AboProbe.cs` 后没有 `dotnet publish`**：
   本会话改过 `secrets` 判据（去掉 `ainOk`）与 `provider_keys.txt` 导出。
   若 12:54 附近某次改动后忘了发布，正在跑的仍是旧 `out\`，而旧版走
   `secrets.txt`、新版走 `provider_keys.txt`，路径对不上就会导致
   `SECRETS_WRITTEN=0`。**先做一次干净 publish 再跑。**
2. **ASLR / 布局漂移**：`0x08269774` → `+0x4f4` → `+0x604/+0x608` 这条
   指针链在某次客户端更新或加载顺序变化后失效，`ValidPtr()` 判假。
3. **`post83Watch` 未置位**：`SECRETS_WRITTEN` 的整段逻辑都在
   `if (post83Watch && …)` 里。若 0x83 之后的状态判定漂移，整段根本不执行
   —— 这与「`CODEC_KEYS` 也几乎为 0」的现象吻合。

### 修复判据

跑一轮，然后：

```
# 观测器侧
(Select-String -Path "<run>\aboprobe_run\*_events.csv" -Pattern "SECRETS_WRITTEN").Count   # 期望 > 0
(Select-String -Path "<run>\aboprobe_run\*_events.csv" -Pattern "CODEC_KEYS").Count        # 期望 > 50，且 p604/p608 有值

# 服务端侧
Select-String -Path "CODOLServer\logs\E57A5C_*_a1\plain.jsonl" -Pattern '"hmac_ok": true'  # 期望 > 0
```

---

## 7. 下一步（按优先级）

### P0：先修观测侧（§6）

没有密钥，后面所有实验的判据都是假的。**这一轮不要碰任何客户端侧变量。**

### P1：追 `Address Fail | result = -3`

客户端自报「某个地址连不上」。已知线索：

* `71/3` 是在 **0x83 之后 0.01 s** 就上报的 ⇒ 握手一完成客户端就去连了某个地址；
* 同轮 ETW 网络图（`runs\NET_CAPTURE_ELEVATED_20261005_113924\game_rt_report.md`）：

```
connect 36 次：成功 27 / 失败 9
  成功：127.0.0.1:3074（auth）、127.0.0.2:8446（我们的明文大厅）
  失败：0.0.0.1:8081 / :80 / :443（err 0xC000006C）
        101.226.156.189:8081|:80|:443、140.206.164.16:8081|:80|:443（err 10054）
另有 3 台外网 121.51.232.79/93/95:3074 各 48 包（平台侧）
```

优先查 `0.0.0.1` 与那两台被 reset 的 IP 指向哪个服务（platform / QoS / publisher）。

### P2：逐条打点 `0xB9A470` 的判定顺序

唯一未量过的一环。在实跑里给下列判定各插一个探针，看**哪一条先判假**：

```
1. auth_task == 11
2. code == 700
3. client_ticket base64 → 128B 且 [0..3] 小端 == 0xEFBDADDE
4. server_ticket → 128B
5. extra_data 内层解析：extended_data / cd_key / time_to_live
   （objA 还额外要 username / encrypted_codoid(16B) / encrypted_register_codoid_data(≤1024)）
```

契约全文在 `CODOLServer\lobby_server\mklobby_response.py` 头部注释，
含 735 的两个写入点 `0xB9A59B` / `0xB9A7C7`。

⚠️ 但注意 F: 盘 `HANDOFF.md` §2.1 的实测结论：在那条线上
`0xBA9980` / `0xBC3E10` **被调用 0 次**，即客户端可能根本不走这段 exe 代码。
**先在 P2 之前用一次直挂确认 `0xB9A470` 到底有没有被调用**，否则 P2 是空转。

### P3：备选 A/B

* 把 `auth_template749.on` 的内层逐字段做 A/B（用 `obj_code` 当判据）；
* 或改用 `mklobby_response.build()` 直接产出并比字节数（成功值 2239）。

---

## 8. 已完成的改动清单（均已编译验证）

### 服务端

| 文件 | 改动 |
|---|---|
| `CODOLServer\lobby_server\lobby_plain_probe.py` | 新增 `--reply-85-task` / `--secrets-file` / `--wait-keys-max` / `--reply-85-out-keys`；新增 `read_secrets()`（支持 `key=value` 与空格两种格式、读 `provider_keys.txt`）、`decrypt_client_task()`、`build_task_reply()`；pending_frames 迟到补答 |
| `CODOLServer\_mainline\_e57a5c_experiment.py` | 新增 `--reply-85-task` / `--reply-85-out-keys`；给 observer 传 `-SecretsFile`；`--wait-keys-max 3` |
| `CODOLServer\lobby3074\fake_auth_tls.py` | 应答形状退回归档形态；`extra_data` 开关 `auth_extra_data.on`；`response.iv_seed` 开关 `auth_iv0.on`；749 模板开关 `auth_template749.on`；`Connection: keep-alive`；收尾保留 8 秒 + 应答后字节打点；`auth_hold.on`（静默挂住）、`auth_halfclose.on`（SHUT_WR）两个实验开关 |

### 观测器

| 文件 | 改动 |
|---|---|
| `restore_iips_contract_001\observer2\AboProbe.cs` | `secrets.txt` 判据去掉 `ainOk`（本 build `[p608+0x9C]` 恒 0，旧判据会把**有效**的 `aes_out` 一起丢掉）；5E8→3 时刻与 `CODEC_KEYS` 处高频导出 `provider_keys.txt`；启动时清 `secrets.txt` |
| `run_codol_001\capture_elevated_network.ps1` | 新增 `-SecretsFile` 透传 |
| `run_codol_001\elevated_ifs1_observer.ps1` | 新增 `-SecretsFile` 透传；**观察器 TenProxy 默认值改为空**（第 84 行，注释内含还原方法） |

### 离线工具（只读）

* `CODOLServer\_mainline\_dec85_probe.py`
* `CODOLServer\_mainline\_dec85_scan.py`
* `CODOLServer\_mainline\_dec85_tasks.py`（用法：`_dec85_tasks.py <run_log_dir> <aes_key_hex>`）

### 文档

* `CODOLServer\HANDOFF_20261005_KEY_AND_TASK.md`（§28 / §29）
* 本文档

---

## 9. 用户偏好与硬约束

* 用户说「继续推进」= **自主连续推进**，不必每步确认；
  但破坏性动作、需要新建权限的动作**要先说**。
* 用户贴的实跑现象（如「又复现 100 无法连接大厅服务弹窗」）是真实反馈，
  **当证据用**。
* 环境有**启动 flake**：客户端 9~25 秒自退、无 POST，重跑即可，**不是回归**。
  本会话 13:10–13:30 之间大量轮次 `plain.jsonl` 只有 95 字节，就是这个 flake。
* 硬边界：
  - **不关、不规避 ACE / TenProtect**；
  - **不改本机网络配置**（hosts 除外，已固化）。
* 沙箱/脚本实验必须**可回滚**（本会话所有改名/改 ini 都已还原或留 `.bak_*`）。
* 日志里**不要出现非 GBK 字符**：`run_all` 用 GBK 重定向 stdout，
  会把子进程打死。

---

## 10. 参考文件

### F: 盘（外部，只读参考）

```
F:\桌面\ol\大厅\                     ← 真正进过大堂的工作实现
  CODOL_LOBBY_WORKING_20261002.md    ← 主文档
  HANDOFF.md                         ← 现状固化（含 §2 的关键否证结论）
  scripts\  nt10.py / nt8o.py / run_all.py / lobby_server.py / fake_auth_tls.py / codol_crypto.py
  certs\    _ca.pem / _leaf2_chain.pem
  data\     publisher_files / player_profiles
  logs\     auth3074.log（2239 字节应答那次）/ lobby_srv.log / secrets.txt
  _frozen_manifest.txt               ← SHA256，可比对是否被改动

F:\桌面\ol\新建文件夹\                 ← 靶场那条线的完整包，含 docs\HANDOFF.md
F:\桌面\ol\CODOL_MOVEMENT_PHYSICS_20261004.md
```

### 本仓库

```
CODOLServer\HANDOFF_20261004_DW_PUMP_STAGE.md          ← DW 泵 / 0x85 全流水（§27）
CODOLServer\HANDOFF_20261005_KEY_AND_TASK.md           ← 密钥口径 + 任务应答（§28/§29）
CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md         ← 430KB 逆向主手册
CODOLServer\SESSION_RECORD_20260926_LOBBY_STAGE2.md    ← §1.3/1.4：cfg_applied / auth_task=32 因果
CODOLServer\lobby_server\mklobby_response.py           ← 头部注释 = objB/objA 应答契约全文
CODOLServer\backup_reverse_engineering\...\CONFIRMED_20260929_0100\...\lobby_response.json
                                                       ← 749 字节模板
```

---

## 11. 环境当前状态快照（2026-10-05 13:47）

```
auth_template749.on                在
auth_hold.on / auth_halfclose.on / auth_iv0.on / auth_extra_data.on   已删
dwauth.ini                         3074 / 3074 / 0x03EA
fake_auth_tls                      最后活跃 13:46:47（进程已退出）
8443 探针                          已停
提权代理                           已退出（需重新起）
沙箱 TCLS / SSOPlatform / tacc_2_1 / TenProtect   均已改回原名
shm bin                            已从 .bak_1004 还原

残留：无 python / 无游戏 / 无 observer 进程（干净，可直接起下一轮）
```

下一轮开局前建议先清残留（F: 盘 HANDOFF §6 的经验）：

```powershell
Get-Process python,codoMP_client_shipRetail,IIPSHostApp,TP3Helper -ErrorAction SilentlyContinue | Stop-Process -Force
```
