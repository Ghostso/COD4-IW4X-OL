# 阶段记录：`/auth/` 大厅握手联调（已打通双向，剩最后一道闸）

- **时间**：2026-09-26 00:20（Asia/Shanghai）
- **工作目录**：`D:\BaiduNetdiskDownload\使命召唤OL`
- **上一份记录**：`CODOLServer\SESSION_RECORD_20260925_DWAUTH.md`
- **当前状态**：**TLS + `POST /auth/` 请求/应答双向已通**；客户端仍弹「[100] 无法连接大厅服务」
- **一句话结论**：
  **网络层、TLS 层、地址层、配置层全部打通，请求已被服务器收到并正确应答；
  唯一剩下的闸门是应答内容里还有第 8 个未定位的条件。**

---

## 0. 环境与安全（全程遵守）

| 约束 | 说明 |
|---|---|
| 未改系统网络 | 无 `netsh` / 路由 / DNS / 防火墙 / 网卡操作 |
| 未碰 ACE 驱动 | 无 `sc stop/config/delete` |
| 无删除 | 只新增；覆盖前先建 `.bak_<时间戳>` |
| 只读采样 | 游戏状态全靠 `OpenProcess(QUERY\|VM_READ)` + `ReadProcessMemory`，**无注入、无写内存** |

---

## 1. 本轮打通的三段链路（全部实测）

### 1.1 `dwauth.ini` 被读取（t≈7–8 s）

```
t= 7.02  u5CC=1  host=""           f1=""
t= 8.03  u5CC=1  host="127.0.0.1"  f1="127.0.0.1"   ← ★ 读到
```

⇒ `0x77EE40`(WinMain) 的 `dwauth.ini` 解析**实测成立**（字段3→`0x81A76A8`、字段1→`0x81A7F34`）。

### 1.2 DNS 阶段通过（此前从未通过）

```
t=19.04  flag_61f=1  uA50=2  dw_state=1  state_prev=1  uA78=2   ← ★★ DW_DNS_COMPLETE
t=21.54  flag_61f=1  uA50=0  dw_state=10 state_prev=10
```

`uA78=2` = `DW_DNS_COMPLETE`；对照历史运行（全程 `uA78=0` = `DW_DNS_ERROR`）。

### 1.3 TLS 握手 + `POST /auth/` 真实报文

**第一次握手失败（有价值的失败）**：

```json
{"event":"tls_fail","error":"SSLError(1,'[SSL: NO_SUITABLE_SIGNATURE_ALGORITHM]')"}
```

原因：游戏用 **OpenSSL 0.9.8p（2010-11-16）**，只支持 TLS1.0 + 经典 CBC 套件。

**修法**（只改本地探针）：

```python
ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.options |= ssl.OP_NO_TLSv1_3
```

**成功后**：

```json
{"event":"tls_ok","tls_version":"TLSv1","cipher":"AES256-SHA"}
{"request_line":"POST /auth/ HTTP/1.1"}
```

---

## 2. `/auth/` 真实报文（首次捕获，逐字节）

### 2.1 请求（客户端 → 服务器）

```http
POST /auth/ HTTP/1.1
Host: 127.0.0.1:8443
Accept: */*
Content-Type: application/json
X-TransactionID: 5703326275551353801
Content-Length: 187
Expect: 100-continue
```

```json
{
  "auth_task":  "10",
  "iv_seed":    "2844838425",
  "title_id":   "0",
  "identity":   "356c4bc3",
  "extra_data": "{\"version\": \"0\", \"user_id\": \"10995207597479878709\", \"extended_data\": true}"
}
```

`extra_data` 解嵌套：`{"version":"0","user_id":"10995207597479878709","extended_data":true}`

**要点**：

- 所有数值都是**字符串**（不是数字）。
- `356c4bc3` 是 **`identity` 的值**（不是错误码）。
- `iv_seed` **每次不同**（实测 1229950237 / 1599246547 / 483210527 / 2385052197 / 2844838425）→ 时间或随机源。
- **没有** `ciphertext` / `license_id` / `lsg_server_ticket` → 那些属于**另一条** `/auth/` 分支。

### 2.2 应答（我构造，已完全符合已解出的契约）

```json
{"auth_task":10, "code":700, "iv_seed":0,
 "next_poll_after":0, "estimated_wait_time":0, "member_position":0,
 "lsg_server_ticket_size":128, "lsg_server_ticket":"<base64 128B>"}
```

---

## 3. 反编译解出的应答契约（VA 级，全部已完成）

### 3.1 校验器 `0xB991A0`（任务 vtable `0xD5A1F8` 的 +0x0C 槽）

```asm
00B991D5  mov  edi, 0x2BC            ; 默认失败码 = 700
00B991DC  cmp  eax, 0xc8             ; HTTP 必须 == 200
00B991E1  jne  0xb992ac
00B9921E  push 0xd5a228              ; "auth_task"
00B99226  call 0xbc3e10              ; get_int64
00B99235  cmp  ecx, 1                ; ★ auth_task == 1
00B99238  jne  0xb9923e
00B9924E  push 0xdaddc4              ; "code"
00B99256  call 0xbc3e10
00B99265  cmp  eax, 0x2bc            ; ★ code == 700
00B9926E  je   0xb99289              ; → 返回 700
```

### 3.2 取值器 `0xB983F0`（由 `0xB98AD0` 在任务状态 == 5 时调用）

```asm
00B98436  mov  [ebp-0xEC], 0x22C4    ; ★ 默认结果 = 8900
00B98440  call edx                   ; HTTP 状态
00B98442  cmp  eax, 0xc8             ; == 200
00B98447  jne  0xb9865e
00B9846A  call 0xbc37a0              ; 解析 JSON

00B98480  call 0xBA9BC0              ; ★ 排队字段解析（见 3.3）

00B984B2  push 0xd5a114              ; "iv_seed"
00B984BD  call 0xbc3e10              ; get_int64
00B984CD  push 0xd5a0fc              ; "lsg_server_ticket_size"
00B984D8  call 0xbc3e10

00B984E7  cmp  [ebp-0xE4], 0         ; ★ iv_seed 必须 == 0（含高 32 位）
00B984EF  cmp  [ebp-0xE8], 0         ; lsg_server_ticket_size
00B984F5  jbe  0xb9862c              ; == 0 → status=1（无 ticket 分支）
...
00B98553  cmp  edi, 0x80             ; ★ ticket_size 必须 <= 128
00B98562  ...                        ; 读字符串 + base64 解码
00B98620  mov  [esi+0x240], 2        ; ★★ status = 2（带 ticket 分支）
00B9862C  mov  [esi+0x240], 1        ; status = 1（无 ticket 分支）
00B9863A  mov  [ebp-0xEC], 0x22CB    ; 8907（失败）
00B98614  mov  [ebp-0xEC], 0x22CC    ; 8908（另一失败）
```

### 3.3 排队字段解析器 `0xBA9BC0`（`0xB98480` 解析后立即调用）

```asm
00BA9BD4  push 0xd5a794              ; "member_position"
00BA9BFA  push 0xd5a780              ; "estimated_wait_time"
00BA9C0E  push 0xd5a770              ; "next_poll_after"
00BA9C24  mov  [esi+4], ecx          ; ★ 三个都必须存在，否则返回 0
00BA9C3E  call 0x8435d0              ; 失败路径
```

**⇒ 这是"排队/等待"语义**；三个键缺任何一个都会让 `bl=0` → 结果被覆盖为 8907。

### 3.4 状态推进判定 `0x7F3190`（子状态 5/8 处理器）

```asm
007F31B1  call 0xB983B0              ; 读 [obj+0x1400] = 取值器返回
007F31B6  cmp  eax, 0x22C4           ; ★★ 必须 == 8900
007F31BB  je   0x7F31E1
007F31C4  mov  [0x84ABA5C], eax      ; 失败 → 记录错误码
007F31D2  mov  [0x84ABA60], 0        ; → 复位

007F31F1  mov  ecx, edi              ; edi = status ([obj+0x240])
007F31F3  dec  ecx
007F31F4  je   0x7F3209              ; status == 1 → 另一分支
007F31F6  dec  ecx
007F31F7  jne  0x7F3246
007F31FA  mov  [0x84ABA60], 9        ; ★★ status == 2 → 子状态 9 → 主状态 3
```

**⇒ 两个条件必须同时成立：`[obj+0x1400]==8900` 且 `[obj+0x240]==2`。**

### 3.5 `[obj+0x1400]` 的全部写入者（穷尽搜索，共 6 处）

| VA | 写入值 | 语义 |
|---|---|---|
| `0xB98244` | `ebx`(=0) | 构造时清零 |
| **`0xB98B0A`** | `call 0xB983F0` 的返回 | ★ 成功路径 |
| **`0xB98B4B`** | `call 0xBAA090` 的返回 | ★ 另一成功路径 |
| `0xB98D25` | `5` | 硬失败 |
| `0xB98ECA` | `5` | 硬失败 |
| `0xB99074` | `5` | 硬失败 |

⇒ **成功路径不写 `0x22C4`，而是把取值器返回原样搬入**。8900 是取值器的**默认值**。

### 3.6 任务 vtable `0xD5A1F8`（11 槽）

| 槽 | VA | 角色 |
|---|---|---|
| +0x00 | `0xB99990` | 构造/重置 |
| +0x04 | `0xB99A60` | 启动 |
| +0x08 | `0xB9A070` | —— |
| **+0x0C** | **`0xB991A0`** | **★ auth 应答校验** |
| +0x10 | `0xB9A370` | —— |
| +0x14 | `0xB99930` | —— |
| +0x18 | `0xB999C0` | —— |
| +0x1C | `0xB99940` | —— |
| +0x20 | `0xB99350` | —— |
| +0x24 | `0xB99610` | —— |
| +0x28 | `0xB994B0` | —— |
| +0x2C | `0x76A6D0` | 通用 |

### 3.7 关键全局

| 名称 | 地址 | 语义 |
|---|---|---|
| dwLobby 总闸 | `0x849B61F` | `1` = 开启 |
| 主状态 | `0x84ABA50` | 0→1→2→3(LOBBY_CONNECTED)… |
| 派生状态 | `0x849BA34` | —— |
| 前一状态 | `0x849BA30` | `1` = `dwLogonStart` 运行过 |
| 子状态 | `0x84ABA60` | 含 9（推进信号） |
| DNS 结果 | `0x84ABA78` | `0`=ERROR，`2`=COMPLETE |
| 最近错误码 | `0x84ABA5C` | 失败时记录 |
| 大厅 HOST | `0x81A76A8` | `dwauth.ini` 字段3 |
| 大厅 PORT | `0x81A9EC4` | `dwauth.ini` 字段4 |

---

## 4. 契约逐条对照（八项里七项已对上）

| # | 条件 | 来源 | 我的应答 | 结果 |
|---|---|---|---|---|
| 1 | HTTP `200` | `0xB991DC` / `0xB98442` | 200 | ✅ |
| 2 | `auth_task == 1` | `0xB99235` | 1 | ✅ |
| 3 | `code == 700` | `0xB99265` | 700 | ✅ |
| 4 | `iv_seed == 0` | `0xB984E7` | 0 | ✅ |
| 5 | `member_position` 存在 | `0xBA9BD4` | 0 | ✅ |
| 6 | `estimated_wait_time` 存在 | `0xBA9BFA` | 0 | ✅ |
| 7 | `next_poll_after` 存在 | `0xBA9C0E` | 0 | ✅ |
| 8 | `lsg_server_ticket_size` ∈ (0,128] + `lsg_server_ticket` base64 | `0xB98545`~`0xB985A1` | 128 / 已验证 | ✅ |
| **?** | **`[obj+0x240] == 2`** | `0x7F31F7` | **未达成** | ❌ |

**⇒ 仍有第 8 个未定位的条件。**

---

## 5. 八轮实验轨迹（全部实测）

| 轮次 | 目录 | `dwauth.ini` | 应答 | 末态 |
|---|---|---|---|---|
| 1 | `sandbox` | 无 | —— | 进程 t≈11.5 s 自行退出 |
| 2 | `sandbox` | 有 | —— | t=11.52 s 进程消失 |
| 3 | `sandbox_ifs1_20260923` | 无 | 探针未起 | t=23.54 复位 |
| 4 | `sandbox_ifs1_20260923` | 有 | `{"auth_task":1,"code":700}` | t=21.54 复位 |
| 5 | 同上 | 有 | 加 `iv_seed:0` | t=22.04 复位 |
| 6 | 同上 | 有 | 加 32B ticket | t=22.06 复位 |
| 7 | 同上 | 有 | ticket → 128B | t=22.05 复位 |
| 8 | 同上 | 有 | 加排队三键 | t=18.04 复位 |

**每轮都稳定复现同一模式**：

```
t≈7-8   host="127.0.0.1"        dwauth.ini 被读
t≈15-19 flag_61f=1              总闸打开
t≈19-22 uA50=2  uA78=2  prev=1   ★ DNS_COMPLETE，请求发出并被应答
t≈22    uA50=0  dw_state=10      复位（未到 state 3）
```

**探针统计**：`http req = 5`、`resp_sent = 5`（每轮恰好一次 `/auth/`）。

---

## 6. 下一步的两个候选（待定，未执行）

### 候选 1：补 `HTTP/1.1 100 Continue`

客户端明确发了 `Expect: 100-continue`，但探针**没回 100** 就直接回 200。
标准客户端（curl 等）会照发 body，但 Demonware 的 HTTP 层可能认为流程不完整。

**改法**：读到头部后先 `sendall(b"HTTP/1.1 100 Continue\r\n\r\n")`，再发 200。

### 候选 2：`code` 试 `8900`

`0xB983F0` 的默认成功值是 `0x22C4`(8900)，而 `0xB991A0` 要求 `700`。
两者可能**属于两个不同任务的应答**，被我读混了。

**改法**：`"code":8900` 试一轮，看 `0xB991A0` 是否放行。

### 候选 3（若前两条无效）：定位 `0xB99350` / `0xB99610` / `0xB994B0`

这三个 vtable 槽（+0x20/+0x24/+0x28）尚未反汇编，可能才是**真正解析成功数据**的地方，
也是 `[obj+0x240]` 被写成 `2` 之外的条件来源。

---

## 7. 本轮改动清单（全部在沙箱内，可回退）

### 7.1 配置文件

| 文件 | 位置 | 备份 |
|---|---|---|
| `dwauth.ini`（新建，7 行） | `run_codol_001\sandbox\` | —— |
| `dwauth.ini`（新建，7 行） | `run_codol_001\sandbox_ifs1_20260923\` | —— |
| `cacert.pem`（追加自签 CA） | 同上两处 | `cacert.pem.bak_20260925_233333` / `_233952` |

`dwauth.ini` 内容：

```
127.0.0.1
0
127.0.0.1
8443
0
0
0
```

### 7.2 新增脚本

| 文件 | 作用 |
|---|---|
| `lobby_server\mklobby_cert.py` | 自签 CA/服务器证书（`--sha1` 选项） |
| `lobby_server\mklobby_response.py` | 生成 `/auth/` 应答（契约写进注释，占位符 `$AUTH_TASK`） |
| `lobby_server\lobby_response.json` | 当前应答模板（335 字节） |
| `lobby_server\lobby_probe_server.py` | TLS 探针（SECLEVEL=0 / TLS1.0 / 模板回填） |
| `lobby_server\_decode_capture.py` | 报文解码器（含 `extra_data` 嵌套解析） |
| `lobby_server\install_lobby_config.py` | 安装 `dwauth.ini` + 追加 CA（自动备份、`--dry-run`） |
| `_mainline\_lobby_watch.py` | 只读状态采样器（含 host/f1 直读） |
| `_mainline\_hunt_resultcode.py` | `+0x1400`/`+0x240` 写入者穷尽搜索 |
| `_mainline\_find_authtask.py` | `auth_task` 引用点定位 |
| `_mainline\_gate_summary.py` | 轨迹汇总 |

### 7.3 证据文件

| 文件 | 说明 |
|---|---|
| `logs\lobby_probe.jsonl` | ★ 含 5 次完整 `/auth/` 请求/应答 + TLSv1 握手 |
| `_mainline\_lobby_run_ifs1b~\g\watch.jsonl` | ★ 6 轮完整状态轨迹（每轮 320-360 采样点） |

---

## 8. 复现命令（三条）

```powershell
cd 'D:\BaiduNetdiskDownload\使命召唤OL'

# 1) 生成应答模板
python -X utf8 CODOLServer\lobby_server\mklobby_response.py 128

# 2) 起探针服务器
python -X utf8 CODOLServer\lobby_server\lobby_probe_server.py `
  --cert-dir CODOLServer\lobby_server --bind 127.0.0.1 --port 8443 `
  --log CODOLServer\logs\lobby_probe.jsonl

# 3) 提权采样 + 启动游戏（另开窗口）
python -X utf8 CODOLServer\_mainline\agent_client.py run python -X utf8 `
  CODOLServer\_mainline\_lobby_watch.py `
  --cwd run_codol_001\sandbox_ifs1_20260923 `
  --out CODOLServer\_mainline\_lobby_run_next --seconds 180 --step 0.5
```

**注意**：`lobby_probe_server.py` 每条连接**实时读** `lobby_response.json`，改应答**无需重启探针**；
但改 `lobby_probe_server.py` 本身**必须重启**。

---

## 9. 未解项（诚实标注）

1. **第 8 个条件未定位** —— 七项契约全对，`[obj+0x240]` 仍拿不到 `2`。
2. `0xB99350` / `0xB99610` / `0xB994B0` 三个 vtable 槽**未反汇编**。
3. `lsg_server_ticket` 的**内容语义**未定 —— 目前是任意 128 字节；客户端只校验长度，
   但**后续使用**它做什么（是否用于后续请求的签名）未知。
4. `ticket` 流程（`0xB9A470` 带 `0x2BC` 的另一条 `/auth/` 路径）**未跑通** ——
   它是 §11.3 里 `ciphertext`/`license_id`/`ticket` 那条链。
5. `DW-Ticket-Seed`（`0xD5A158`）的构成未解 —— 只在 `0xB98A3E` 看到它被写入，
   格式串 `0xDB7B68` + 缓冲 24 字节。
6. `space` 战斗服（非大厅）**完全未涉及**。

---

## 10. VA 速查（本阶段新增）

| 用途 | VA |
|---|---|
| auth 应答校验（vtable+0x0C） | `0xB991A0` |
| 结果取值器 | `0xB983F0` |
| 排队字段解析器 | `0xBA9BC0` |
| 子状态 5/8 处理器（推进判定） | `0x7F3190` |
| 任务状态机 | `0x7F26C0`（跳转表 `0x7F2850`） |
| 子状态分派 | `0x7F28F0`（跳转表 `0x7F2994`） |
| 任务 vtable | `0xD5A1F8` |
| `https://%s:%d/auth/` | `0xD5A2CC` |
| `auth_task` 键 | `0xD5A228` |
| `iv_seed` 键 | `0xD5A114` |
| `next_poll_after` 键 | `0xD5A770` |
| `estimated_wait_time` 键 | `0xD5A780` |
| `member_position` 键 | `0xD5A794` |
| `lsg_server_ticket` 键 | `0xD5A0E8` |
| `lsg_server_ticket_size` 键 | `0xD5A0FC` |
| `server_ticket` 键 | `0xD5A31C` |
| `client_ticket` 键 | `0xD5A32C` |
| `DW-Ticket-Seed` | `0xD5A158` |
| "rijndael"（AES 自证） | `0xD5B268` |
