# CODOL 已确认成果与当前断点（2026-09-28）

工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`

本文件记录本轮已经用运行证据确认的结论、被推翻的旧结论、当前唯一的协议断点，
以及可复现的启动与分析方法。归档目录由
`CODOLServer/_mainline/archive_confirmed_20260928.py` 生成。

---

## 1. 已确认成果

### 1.1 启动链可稳定进入在线模式

运行证据：

```text
run_codol_001\runs\IFS1_ELEVATED_20260928_113239
run_codol_001\runs\IFS1_ELEVATED_20260928_113833
run_codol_001\runs\IFS1_ELEVATED_20260928_114637
run_codol_001\runs\IFS1_ELEVATED_20260928_115639
run_codol_001\runs\IFS1_ELEVATED_20260928_115830
```

这些运行中已经确认：

```text
flag_61f=1
iips.dll 载入
ifs2.dll 载入
DW_DNS_COMPLETE
POST /auth/ TLSv1 + AES256-SHA
```

启动链的在线闸门是：

```ini
# run_codol_001\sandbox_ifs1_20260923\iips.ini
enable_iips=1
iips_url="http://10.231.2.181/"
```

### 1.2 账号鉴权阶段已经真实通过

证据运行：

```text
IFS1_ELEVATED_20260928_113239
```

客户端状态：

```text
uA50=3
sub_state=9
obj_code=700
http_state=5
http_status=200
dw_state_name=DW_ACCOUNT_LOGIN_COMPLETE
```

对应协议：

```json
{"auth_task":11,"code":700,"iv_seed":0}
```

注意：这是账号阶段成功，不等于大厅连接成功。

### 1.3 `iv_seed=0` 单变量实验已完成

探针日志曾确认响应体：

```json
"iv_seed":0
```

结论：

```text
iv_seed=0 不再是账号阶段的阻塞点。
账号阶段可以进入 sub_state=9 / code=700。
```

### 1.4 TCLS 共享内存已接入标准启动链

修改：

```text
run_codol_001\elevated_ifs1_observer.ps1
```

新增参数：

```powershell
[string]$TenProxyShm = ''
```

默认发布：

```text
CODOLServer\_subagents\_tenproxy_shm_fixed.bin
```

效果：

```text
TCLS_SHAREDMEMEMORY<pid>
cfg_applied=1
客户端进入 objA / stage 32 真实大厅路径
objC 大厅对象被创建
```

证据：

```text
run_codol_001\runs\IFS1_ELEVATED_20260928_113833\aboprobe_run\IFS1_ELEVATED_20260928_113833_state.csv
run_codol_001\runs\IFS1_ELEVATED_20260928_114637\aboprobe_run\IFS1_ELEVATED_20260928_114637_state.csv
```

### 1.5 stage 32 的 `extra_data` 契约已修复

旧 724 字节模板缺少 `extra_data`，客户端在 stage 32 返回：

```text
last_err=735 / 0x2DF
```

反汇编定位：

```text
stage 32 -> objA dispatcher 0xB88A30
objA validator 0xB88FC0
extra_data 缺失 -> 返回 FALSE -> 735
```

修复：

```text
python -X utf8 CODOLServer\lobby_server\mklobby_response.py
```

当前模板为 749 字节，包含：

```text
username
encrypted_codoid             （base64 -> 16 bytes）
encrypted_register_codoid_data（base64 -> 128 bytes）
extended_data
cd_key
time_to_live
```

自检结果：

```text
ALL CHECKS PASSED
```

这一步推翻了旧交接文档里“不要把 extra_data 加回去”的结论。

### 1.6 自动化循环已修复两处工程问题

文件：

```text
CODOLServer\_mainline\auto_lobby_loop.py
```

修复 1：状态 CSV 读取路径。

真实位置是：

```text
run_codol_001\runs\<TAG>\aboprobe_run\<TAG>_state.csv
```

旧脚本读的是运行根目录，导致每轮都显示“无状态”。

修复 2：启动竞态重试。

IIPS 启动链存在概率性早期崩溃：

```text
~8.7 秒退出，exitcode=0xFFFFFFFF
只载入 iips.dll，未载入 ifs2.dll
无 /auth/ 请求
```

该情况被视为 startup flake 自动重试，不消耗有效轮次。

### 1.7 动态采样器已扩展到大厅对象字段

文件：

```text
restore_iips_contract_001\observer2\AboProbe.cs
```

新增字段：

```text
obj240
obj1400
obj2ac
lobby       （全局 0x84ABB0C）
lob1400
lob240
lob2ac
lobD8
lob390
lob398
```

采样周期由 100 ms 提高为 20 ms。

---

## 2. 当前唯一协议断点

账号阶段通过后，客户端创建大厅对象 objC，并进入：

```text
sub_state=8
obj_code=700
http_state=5
http_status=200
```

随后失败：

```text
lob1400=8902 / 0x22C6
lob240=0
last_err=8902
dw_state_name=DW_ACCOUNT_ERROR
```

需要的成功值：

```text
[objC+0x1400] == 0x22C4 (8900)
[objC+0x240]  == 2
```

关键反汇编：

```asm
007F3193  mov ecx, [0x84ABB0C]        ; objC
007F31B1  call 0xB983B0              ; return [objC+0x1400]
007F31B6  cmp eax, 0x22C4            ; want 8900
007F31E1  call 0xB98390              ; return [objC+0x240]
007F31F3  dec ecx
007F31F7  jne 0x7F3246               ; want status == 2

00B98B03  call 0xB983F0
00B98B0A  mov [edi+0x1400], eax      ; objC result write

00BAA090  HTTP status mapper
00BAA0A1  mov edi, 0x22C6            ; default failure
00BAA0B1  sub ecx, 0xC8              ; status - 200
00BAA0B7  je 0xBAA0F0                ; 200 -> 0x22C4 / 8900
```

已做的尝试：

```text
GET / 从空 200 改为返回同构 JSON
iv_seed=1
lsg_server_ticket_size=128
lsg_server_ticket=<128 bytes>
Connection: close
```

结果：

```text
objC 仍然得到 lob1400=8902
```

说明 objC 的 HTTP 客户端没有得到可用 200，或它使用的不是当前探针那条 GET /。

---

## 3. 已推翻或必须修正的旧结论

| 旧结论 | 现结论 |
|---|---|
| 先复现 WeGame/TCLS 上下文才能载入 IIPS | 错。IIPS 闸门是 `iips.ini enable_iips=1` |
| 724 字节模板是正确基线，不要加 `extra_data` | 错。stage 32 必须带 `extra_data`，否则 735 |
| `iv_seed` 是账号失败根因 | 已证伪。`iv_seed=0` 后账号阶段可到 sub=9 |
| `sub_state=9 / uA50=3` 即进大厅 | 错。仍需大厅对象 objC 返回 8900 且状态 2 |
| `[obj+0x1400]` 指 objA | 错。`0x7F3190` 读的是 objC |

---

## 4. 当前可复现实验命令

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL
python -X utf8 CODOLServer\_mainline\auto_lobby_loop.py --rounds 3 --seconds 70
```

查看状态：

```powershell
python -X utf8 CODOLServer\_mainline\state_query.py `
  "run_codol_001\runs\<TAG>\aboprobe_run\<TAG>_state.csv" `
  --where sub_state=8 `
  --cols t,objC,lob1400,lob240,lob390,lob398,dw_state_name
```

查看探针请求：

```powershell
python -X utf8 CODOLServer\_mainline\ws_inspect.py `
  --file CODOLServer\logs\<AUTO_LOBBY_DIR>\probe.jsonl
```

---

## 5. 下一步

继续专项逆向 objC 的 HTTP 客户端：

```text
objC + 0x398  内部 HTTP 对象
0xB98150      objC 构造
0xB983F0      响应解析和结果码生成
0xB98AE0      HTTP 状态轮询与 +0x1400 写入
0xBAA090      状态到 890x 的映射器
```

目标：

```text
找到 objC 实际使用的 host、port、path、HTTP 方法
让 0xB983F0 返回 8900
让 [objC+0x240] 变为 2
最终出现 DW_LOBBY_CONNECTED
```

---

## 6. 归档后追加的进展（同日）

### 6.1 objC 并不复用 `/auth/` 通道

探针日志证明：`sub_state=8` 期间**只有 stage 32 那一次 POST /auth/**，
没有第二个连接。所以 objC 不是向 8443 轮询 `/auth/`。

### 6.2 objC 的真实请求契约

objC 启动函数 `0xB98B70`，发送前调用 `0xB986C0` 组包，最终由
`0x77B370`（sprintf）按模板拼 URL：

```text
VA 0xD5A11C  "%s://%s:%d/%s/title/%d/queue/%d/member/%llu"
VA 0xD5A148  "https"
```

即真实请求形如：

```text
https://<host>:<port>/<lobby>/title/0/queue/<n>/member/<id>
```

自定义头：

```text
VA 0xD5A194  "DW-Server-Ticket-Size"
VA 0xD5A1AC  "DW-Server-Ticket"
VA 0xD59E6C  "X-TransactionID"
VA 0xD5A1C0  "Transfer-Encoding"
VA 0xD5A1D4  "Content-Type"
VA 0xD5A1E4  "application/json"
VA 0xD34BB8  "Content-Length"
```

### 6.3 host / port / lobby 名来自 TCLS 共享内存

```asm
00B98B84  mov eax, [esi+0x2c]        ; 请求对象
00B98B8A  mov [esi+0x2008], ecx      ; 来自 [eax+4]
00B98B90  mov edx, [eax]             ; -> [esi+0x230]
00B98B9B  mov ecx, [eax+0x20]        ; -> [esi+0x238]
00B98BA4  mov edx, [eax+0x24]        ; -> [esi+0x23c]
```

也就是说 host / port / lobby 段来自 TCLS 共享内存（TenProxy
`ApplySettings`），不是 `dwauth.ini`。

### 6.4 当前失败点已定位到组包阶段

新增采样字段与实测值：

```text
lob20   = 13           objC 的 HTTP 对象状态机值
lob28   = 3            stage
lob2c   = 1007307808   请求对象指针
lob2004 = 1007307632
lob2008 = 879198180
lob_url = (空)         URL 缓冲从未被填充
lob1400 = 8902
lob240  = 0 -> 3
lob398  = 0 -> 1
```

关键分支：

```asm
00B986C0  ...
00B986D4  test al, al
00B986D6  jne 0xB986EE         ; false -> 直接失败
00B986DD  mov [esi+0x1400], 0x22C5   ; 8901
```

结论：objC 在**组装 URL / 取 TCLS 配置**这一步就失败，还没进入
HTTP 请求阶段，因此 `lob1400` 落到 890x 兜底值。

### 6.5 采集能力变更

```text
restore_iips_contract_001\observer2\AboProbe.cs
  + obj240 / obj1400 / obj2ac
  + lobby / lob1400 / lob240 / lob2ac / lobD8 / lob390 / lob398
  + lob20 / lob28 / lob2c / lob2004 / lob2008
  + lob_url（objC+0x30 的 C 字符串）
  采样周期 100 ms -> 20 ms
```

### 6.6 下一步

不要再调 `/auth/` 或 `lobby_response.json`。当前需要：

```text
让 objC+0x2c 指向的请求对象带上有效的 host / port / lobby 字段
来源是 TCLS 共享内存镜像 _tenproxy_shm_fixed.bin 的 tag 表
```

具体行动：

```text
1. 解出 0xB986C0 读取 [eax] / [eax+0x20] / [eax+0x24] 的确切字段语义
2. 对照 _tenproxy_shm_fixed.bin 中 tag8 文本 "127.0.0.1;443;1004;0;0"
3. 让镜像里的 host/port/lobby 与实际监听端口一致
4. 重新运行，期望 lob_url 被填充且 lob1400 变为 8900
```

---

## 7. 追加：objC 组包阶段的实测字段（同日）

新增采样字段与实测（`IFS1_ELEVATED_20260928_122838`，`sub_state=8`）：

```text
objA         = 1027970712
obj_code     = 700            stage 32 应答已被接受
objA28       = 622861078
objA2c       = 0
objA48       = 437191929
objA4c       = 1178284069
objAD8       = 4022185438
objADC       = 17
objA48_str   = （空）
objA4c_str   = （空）
objAD8_str   = （空）

lobby        = 1028204480     == objC
lob20        = 13             HTTP 对象状态机
lob28        = 3
lob2c        = 1027970928     请求对象
lob2004      = 1027970752
lob2008      = 4554724
lob1400      = 0 -> 8902
lob_url      = （空）          URL 缓冲从未填充
```

解读：

```text
objA48 / objA4c / objAD8 都不是有效的 C 字符串指针，
说明组 URL 所需的 host / port / queue 值不在这些偏移。
objADC = 17 与 HOST 端口族无关，属其它用途。
```

同时确认：

```text
探针在 sub_state=8 期间只收到 stage 32 那一次 POST /auth/
objC 没有向 8443 发起第二个请求
```

因此当前阻塞点确定为：

```text
objC 在 0xB986C0 组 URL 阶段拿不到有效 host/port/queue
-> 0xB986D6 分支失败
-> lob1400 落到 890x 兜底
```

这一步**不是** `/auth/`、`iv_seed`、`extra_data` 或 ticket 的问题，
这些都已在本轮排除。

---

## 8. 追加：组 URL 失败的确切原因（同日，第二次归档后）

### 8.1 有两条轮询入口，都以 `0xB986C0` 为前提

```asm
; 入口 A：0xB98B70，push 4
00B98BB0  call 0xB986C0
00B98BB5  test al, al
00B98BB7  je  0xB98BF9          ; false -> bl=0 -> 直接失败

; 入口 B：0xB98D40，push 5
00B98D55  call 0xB986C0
00B98D5A  test al, al
00B98D5C  je  0xB98D9E          ; false -> bl=0 -> 直接失败

; 入口 B 成功路径
00B98E7F  cmp eax, 3            ; GetStatus()
00B98E8A  mov [esi+0x240], eax  ; 把 3 写进 objC+0x240
```

`0x7F31F7` 需要 `[objC+0x240] == 2`，而这里写的是 `3`。

### 8.2 `0xB986C0` 的 host 取值链是确定的

```asm
00B986EE  mov eax, [esi+0x28]     ; objC+0x28
00B986F1  mov ecx, [eax+0x24]
00B986F4  mov edx, [eax+0x20]     ; <-- host 字符串指针
```

`0x7F2E98` 把 `objA+0x28` 和 `objA+0xD8` 交给 `0x801A00`：

```asm
007F2E98  mov ecx, [0x84ABB08]    ; objA
007F2EA0  call 0xB9A0E0           ; == objA + 0x28
007F2EA8  call 0xB9A0F0           ; == objA + 0xD8
007F2EAE  call 0x801A00           ; 用这两个指针构造 objC
```

### 8.3 实测：host 指针是固定残值，不是有效字符串

两次独立运行的 `sub_state=8` 采样完全一致：

```text
objA      = 1010172536 / 1006803048   （每次不同，正常）
objA28    = 622861078                 （两次相同！）
lob28     = 3
lob28_20  = 622861078                 （host 指针 = objA+0x28 的值）
lob28_24  = 2307161978
lob_url   = （空）
lob1400   = 0 -> 8902
```

`622861078 = 0x25201B16`。

关键判据：该值**跨运行恒定**，因此它不是随机未初始化内存，
而是一个固定的无效指针（低地址、非映射、且不是 ASCII 字符串）。

结论：

```text
objA+0x28 指向的不是一个含 host 字符串的对象
-> 0xB986C0 拼不出 https://host:port/...
-> lob_url 始终为空
-> 0xB986C0 返回 false
-> 两个轮询入口都在第一步失败
-> lob1400 落到 8902（0xBAA090 的兜底值）
-> dw_state 落到 DW_ACCOUNT_ERROR
```

### 8.4 因此正确的修复方向是数据源，不是服务器

需要让 `objA+0x28` 指向一个真实对象，使其：

```text
[+0x20] = host 字符串指针，例如 "127.0.0.1"
[+0x24] = queue 相关值
```

而 `objA+0x28` 的内容由 `0x7F2EA0`（`objA + 0x28`）在 stage 32 通过后
填充，来源是 stage 32 的响应或 TCLS 共享内存。

已确认与 8902 无关的因素：

```text
/auth/ 响应字段（额外 data、ticket、iv_seed、code、auth_task 全部正确）
TLS / HTTP 200
探针监听
portproxy 转发
```

### 8.5 新增只读工具

```text
CODOLServer\_mainline\_mem_at.py    按绝对地址读活进程内存（只读）
CODOLServer\_mainline\_str_at.py    按 VA 读镜像内 C 字符串
CODOLServer\_mainline\state_query.py 按列/过滤查询状态 CSV
```

---

## 9. 关键突破：objC 请求的是官方大厅地址（必须更正第 8 节）

### 9.1 先更正一个采样列错位的错误

第 8 节的结论建立在一次**列错位**的采样上：
`V(http)` 曾被误插到 lobby 字段中间，导致 `lob*` 列整体偏移一格，
于是把 `objA+0x28` 的值（`622861078`）误读成“host 指针”。

修正采样顺序后，真实字段如下。

### 9.2 objC 实际拼出的 URL（直接读出，非推断）

运行 `IFS1_ELEVATED_20260928_144416`，`sub_state=8` 实测：

```text
lob_url = https://211.147.81.116:32740/v1.0/title/622861078/queue/0/member/11355988700816506746
```

字段对照 URL 模板
`"%s://%s:%d/%s/title/%d/queue/%d/member/%llu"`：

| 模板位 | 取值 | 十六进制 |
|---|---|---|
| scheme | `https` | |
| host | `211.147.81.116` | `0xD35193D3`（LE `0x745193D3`） |
| port (d) | `32740` | `0x7FE4` |
| lobby 段 | `v1.0` | |
| title (%d) | `622861078` | `0x25201B16` |
| queue (%d) | `0` | |
| member (%llu) | `11355988700816506746` | `0x9D989E7F…` |

### 9.3 结论：当前阻塞点与本地服务器无关

```text
objC 请求 211.147.81.116:32740（腾讯官方大厅地址）
该地址在本机不可达
-> 请求失败
-> lob1400 落到 8902（0xBAA090 兜底值）
-> dw_state 落到 DW_ACCOUNT_ERROR
```

因此：

```text
无论怎样调整 /auth/ 响应、lobby_response.json、iv_seed、ticket、
本地探针端口或 portproxy，都不会改变这一结果。
objC 根本不连本地探针。
```

### 9.4 根因是“服务器地址来源未改写”

objC 的 host/port/lobby 来自 stage 32 之后由客户端自身持有的
在线配置（在线服务器下发或 TCLS 侧配置），当前仍指向官方地址。

要让 objC 连本地，必须改写该地址来源，而不是改 `/auth/` 契约。

### 9.5 关键采样字段（修正后，可复现）

```text
lob_url     = 完整拼出的 URL（新增，决定性）
lob2004     = 32740        端口
lob28_8     = 622861078    title 段（同样出现在 URL 里）
lob28_20    = 2307161978
lob28_24    = 2644022158
lob20       = 3
lob1400     = 0 -> 8902
```

注意：`lob28_8` 与 URL 的 title 段完全一致，说明该对象就是
URL 参数来源，而不是 host 字符串容器。

---

## 10. 重大推进：本地服务器已收到并应答大厅 PUT 请求（同日）

### 10.1 找到了硬编码的官方大厅地址，并成功改写

```asm
00801A2D  push esi                  ; word ptr [0xE513D4]
00801A2E  push 0xe51184             ; "211.147.81.116"
00801A33  push ecx                  ; objA+0xD8
00801A34  push edx                  ; objA+0x28
00801A37  call 0xB98150             ; 构造 objC
```

两个常量：

```text
VA 0xE51184  "211.147.81.116"   官方大厅 host
VA 0xE513D4  word 0x7FE4        端口 32740
```

已在固化链内于进程创建后立即改写（`AboProbe --poke-lobby-host /
--poke-lobby-port`），事件确认：

```text
POKE_LOBBY_HOST  va=0x00E51184 value=127.0.0.1 ok=True
POKE_LOBBY_PORT  va=0x00E513D4 value=8443      ok=True
```

效果：objC 拼出的 URL 变为

```text
https://127.0.0.1:8443/v1.0/title/622861078/queue/0/member/11355988700816506746
```

### 10.2 本地探针已经收到完整的第二阶段请求

探针日志（`AUTO_LOBBY_20260928_150723_r3`）：

```text
tls_ok   TLSv1 / AES256-SHA
PUT /v1.0/title/622861078/queue/0/member/11355988700816506746 HTTP/1.1
Host: 127.0.0.1:8443
Content-Type: application/json
X-TransactionID: 12028449627971567013
DW-Server-Ticket: <128B base64>
DW-Server-Ticket-Size: 128
DW-Client-Ticket: FqxK/wU+rcitysaPaa8QUwA=
DW-Client-Ticket-Size: 129
DW-Ticket-Seed: 0
Content-Length: 0
```

探针已按新契约返回 200 + 1220 字节 JSON（`queue_request` 事件）。

这是本项目第一次让**客户端主动连到本地服务器**并完成第二阶段请求。

### 10.3 请求头暴露的两个新约束

```text
DW-Client-Ticket: FqxK/wU+rcitysaPaa8QUwA=      （base64，12 字节，非 128）
DW-Client-Ticket-Size: 129
DW-Ticket-Seed: 0
```

注意 `DW-Client-Ticket-Size: 129`：客户端自己把 128 字节票据 +1 后发出，
说明该字段语义是“长度+1”，不是纯长度。

### 10.4 仍差最后一格

```text
lob_url    已正确指向 127.0.0.1:8443   ✅
探针收到 PUT 请求                      ✅
探针已回 200 + JSON                    ✅
lob1400    仍为 0 -> 8902              ❌
lob240     仍为 0                      ❌
lob398     14243328（非有效 HTTP 对象指针）
```

即 `0xB983F0` 内部仍未把 HTTP 状态记为 200，或其后校验未通过。
`lob398` 不是 `0xD95B80` 这类堆指针，说明 objC 的 HTTP 子对象偏移
可能不是 `0x398`，需要重新核对。

### 10.5 新增能力

```text
run_codol_001\elevated_ifs1_observer.ps1
    -PokeLobbyHost <ip>    改写 0xE51184
    -PokeLobbyPort <port>  改写 0xE513D4
run_codol_001\capture_elevated_network.ps1
    同名参数透传
CODOLServer\_mainline\auto_lobby_loop.py
    --poke-lobby-host / --poke-lobby-port（默认 127.0.0.1 / 8443）
CODOLServer\lobby_server\lobby_probe_server.py
    /title/.../queue/... 分支：返回 200 + 完整 JSON
```

---

## 11. 传输层已打通，卡点在 objC 内嵌 HTTP 对象的取码方式（同日）

### 11.1 探针侧已与 `/auth/` 完全同构

队列分支最终采用与成功 `/auth/` 一致的收尾方式：

```text
HTTP/1.1 200 OK
Content-Type: application/json
Connection: close
Content-Length: 1220
<完整 JSON>
→ conn.unwrap()  发出 TLS close_notify
```

日志确认：

```text
queue_request            resp_len=1220
queue_tls_close_notify   （已发 close-notify）
```

即：请求到达、应答发送、TLS 正常收尾，三步全通。

### 11.2 但 objC 的 HTTP 对象仍停在 state 3 / status 0

修正一个重要的采样错误后得到干净数据：

```text
objC + 0x398 是内嵌 HTTP 对象本身（不是指针）
  +0x398 +0x00 = 14243328  = 0x00D95C60   代码段，vtable
  +0x398 +0x04 = 3                        状态机值
  +0x398 +0x20 = 1014256488               堆指针，不是状态码
  +0x398 +0x464= 0                        status 仍为 0
```

关键矛盾：

```asm
00B98360  mov eax, [ecx + 0x20]     ; 被当作 status 读
00B98369  cmp eax, 3
00B9837F  mov [edx], eax            ; 把 [ecx+0x20] 交给调用者
```

而 `[objC+0x398+0x20]` 实测是**堆指针**（`1014256488`），不是 3 或 200。

`0xB98AE0` 用另一个槽（`[+0x2c]` 的函数）取状态并比较 1/3/5。
两者对同一内嵌对象给出不同语义，说明 objC 的 HTTP 对象类与
objB/objA 用的 `0xD5A1F8` 类**不是同一个类**，字段布局不同。

### 11.3 因此下一步

```text
1. 读 objC+0x398 的 vtable 0x00D95C60，列出其槽位
2. 确认该类真正的“取状态”“取状态码”槽位偏移
3. 对照 0xB98AE0 / 0xB983F0 实际使用的槽位
4. 必要时让探针以该类期望的形式返回（例如 length 字段语义）
```

已排除的怀疑（本轮均已实测）：

```text
传输层 / TLS 收尾         已按 /auth/ 成功方式复刻，无效
Connection keep-alive    已试，无效
票据内容 / extra_data    已确认不在这一环
本地改写是否生效         已确认生效（URL 正确指向 127.0.0.1:8443）
探针是否收到请求         已确认收到 PUT 并回包
```

---

## 12. 回归修复：本地重定向改为显式 opt-in

### 12.1 回归现象与原因

现象：

```text
上一轮：启动画面 -> 播放完整 -> 正在连接 -> 再弹无法连接大厅
这一轮：启动后较快弹出无法连接大厅
```

原因确定：

```text
auto_lobby_loop.py 把 --poke-lobby-host/--poke-lobby-port 设成了默认开启。
开启后 objC 立刻连本地 8443；本地响应还没通过它的取码校验，
所以失败比等待官方 211.147.81.116:32740 超时更早出现。
```

也就是说：**不是启动链坏了，而是调试用的本地重定向默认生效了。**

### 12.2 修复

```text
CODOLServer\_mainline\auto_lobby_loop.py
    --poke-lobby-host  默认 ""      （此前 127.0.0.1）
    --poke-lobby-port  默认 0       （此前 8443）
```

现在默认恢复原始慢路径（官方地址），本地重定向只在显式传参时生效。

### 12.3 对照验证

无 poke 运行 `IFS1_ELEVATED_20260928_154132`：

```text
lob_url  = https://211.147.81.116:32740/v1.0/title/...   （官方地址）
t=37.934 进入 sub_state=8
t=59.005 lob1400=8902，才转为 DW_ACCOUNT_ERROR
```

即失败时间回到约 59 秒；上一轮“启动画面 -> 正在连接 -> 弹窗”的可见时序已恢复。

### 12.4 结论

```text
默认行为：保持原始启动/连接时序，不 poke 官方地址。
调试行为：显式加 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443
          才启用本地重定向实验。
```

之前已确认的 157/196 文件归档仍然有效；本节追加后重新生成归档。

---

## 13. A 路线静态定位：objC 内嵌队列客户端的真实槽位

本节不写任何代码、不改任何客户端字节，只记录 vtable 与调用关系。

### 13.1 objC 内嵌 HTTP 对象的 vtable

`objC+0x398` 是内嵌对象，vtable 指针为：

```text
0xD95600
```

关键槽位：

| vtable 偏移 | 函数 | 作用 |
|---|---|---|
| `+0x0C` | `0xC758A0` | 组织并提交请求头/体 |
| `+0x14` | `0xC75950` | 请求生命周期辅助 |
| `+0x28` | `0xC75A50` | 检查请求缓冲/触发队列动作 |
| `+0x2C` | `0xBC1190` | **返回 `[obj+4]`：真正的状态机值** |
| `+0x34` | `0xC74FD0` | **返回 `[obj+0x464]`：HTTP 状态码** |
| `+0x38` | `0xC74FE0` | 另一状态相关读取 |

### 13.2 `0xB98AD0` 使用的就是这两个槽

对应反汇编：

```asm
00B98AE0  mov eax, [edi+0x398]      ; vtable
00B98AE6  mov edx, [eax+0x2C]       ; == 0xBC1190, returns [obj+4]
00B98AF2  call edx
00B98AF4  cmp eax, 1
00B98AF9  cmp eax, 3
00B98AFE  cmp eax, 5
00B98B03  call 0xB983F0             ; 仅当状态 == 5
00B98B44  call 0xBAA090             ; 非 5 分支，取状态码
```

即：

```text
状态 = [objC+0x398+4]        当前 3，需 5
状态码 = [objC+0x398+0x464]  当前 0，需 200
```

### 13.3 `0xC75050` 与 `0xC75A50`

`0xC75050` 在提交路径里写：

```asm
00C750FA  mov dword ptr [esi+4], 3
```

`0xC75A50` 是 `vtable+0x28`，负责推进：

```asm
00C75A50  ...
00C75A53  mov eax,[esi]             ; vtable
00C75A55  mov edx,[eax+0x58]        ; == 0xC767F0
00C75A58  push 1
00C75A5A  call edx
00C75A5C  test al,al
00C75A60  mov dword ptr [esi+4], 6  ; 失败分支
```

`0xC767F0` 是状态比较器：

```asm
00C767F8  cmp edx,5
00C76804  cmp dword ptr [ecx+4],1
00C7680F  cmp dword ptr [ecx+4],2
00C7681A  cmp dword ptr [ecx+4],3
...
```

### 13.4 结论

弹窗的直接触发条件已经确定，不是 `/auth/`、不是 ticket，而是：

```text
0xB98AD0 读 objC+0x398+4
请求提交后该值停在 3
它从未变成 5
于是 0xB98AE0 走 0xBAA090 分支
0xBAA090 默认返回 0x22C6(8902)
0x7F3190 看到 lob1400 != 8900
0x7F3800 返回 0
0x7F276A 记录 DW_LOBBY_ERROR
0x7EF253 投递 @SF_UI_DW_LIVE_CONNECTING_FAILED
```

所以 A 路线需要解决的是：

```text
让 objC 内嵌 HTTP 对象在收到 200 后把 [objC+0x398+4] 从 3 推进到 5
并让 [objC+0x398+0x464] 变为 200
```

不是改 `/auth/` 契约、不是改 ticket、不是改 dwLobby 总状态。

---

## 14. A 路线：状态 5 的写入点与前置条件（已闭合）

### 14.1 状态 5 的唯一写入点

```asm
00C752F3  mov edx, [esi]            ; vtable
00C752F5  mov eax, [edx+0x4c]
00C752FA  mov dword ptr [ebp-8], 5  ; <<< 成功结果 = 5
00C75301  call eax
00C75372  ...
00C7538E  mov eax, dword ptr [ebp-8]
00C75398  mov dword ptr [esi+4], eax ; <<< 写入状态
```

### 14.2 进入成功分支的唯一前提：HTTP 状态码在 [200,300)

```asm
00C752CF  mov dword ptr [esi+0x464], 0
00C752D2  call 0xAC95F0             ; 取状态码 -> [ebp-4]
00C752DD  mov dword ptr [esi+0x464], edx
00C752E3  cmp edx, 0xC8             ; 200
00C752E9  jl  0xC75320              ; <200  -> 失败
00C752EB  cmp edx, 0x12C            ; 300
00C752F1  jge 0xC75320              ; >=300 -> 失败
00C752FA  mov dword ptr [ebp-8], 5  ; 成功
```

失败分支写 6：

```asm
00C75320  lea ebx, [esi+0x44]
00C75325  mov dword ptr [ebp-8], 6  ; <<< 失败结果 = 6
```

### 14.3 当前实测正好落在失败分支

```text
[objC+0x398+0x464] = 0
0 < 200  ->  jl 0xC75320  ->  状态 = 6
```

而 `0xB98AE0` 只把 `1/3/5` 视为“仍在进行”，`6` 会走 `0xBAA090`
兜底 → `0x22C6(8902)` → `lob1400 != 8900` → `0x7F3800 = 0` → `DW_LOBBY_ERROR`。

### 14.4 因此唯一需要解决的问题

```text
让 0xAC95F0 在收到本地 200 响应后返回 200..299
```

`0xAC95F0` 是状态码取值器（`call 0xAC95F0` 前先清零 `[esi+0x464]`，
随后把返回值写回）。它对应的实现需要继续展开，
这决定了探针响应里到底哪个字段被当作状态码解析。

### 14.5 采样修正

`lob_http_vt`（`objC+0x398+0`）实测为 `14243328 = 0xD95600`，
与该类 vtable 常量完全一致，确认 `+0x398` 是内嵌对象而非指针。
之前的 `lob398` 读数曾被误当成指针，已在报告中更正。

---

## 15. 字节级抓包结论：传输层其实成功了

用 AFD ETW（`run_codol_001\runs\NET_CAPTURE_ELEVATED_20260928_162529`）
对 objC 那次 `127.0.0.1:8443` 连接做逐调用跟踪，得到完整时序：

```text
t=38.422743  socket      AF_INET / SOCK_STREAM / IPPROTO_TCP
t=38.422755  setsockopt  option=2 value=1        (TCP_NODELAY)
t=38.422825  bind        0.0.0.0:49357
t=38.422988  connect     127.0.0.1:8443         ret=0  成功
t=38.431304  send  len=70    ret=70            (TLS ClientHello)
t=38.431306  send  len=70    ret=70
t=38.461577  recv  want=7    ret=7             (TLS ServerHello)
t=38.461588  recv  want=79   ret=79
t=38.461595  recv  want=5    ret=5
t=38.461597  recv  want=834  ret=834           ★ 完整响应已收到
t=38.461971  recv  want=5    ret=5
t=38.461976  recv  want=4    ret=4
t=38.462230  send  len=326   ret=326
t=38.462233  send  len=326   ret=326
t=38.492583  recv  want=5    ret=5
t=38.492585  recv  want=1    ret=1
t=38.492629  recv  want=5    ret=5
t=38.492633  recv  want=48   ret=48
t=38.492779  send  len=586   ret=586
t=38.492782  send  len=586   ret=586
t=38.523779  recv  want=5    ret=5
t=38.523781  recv  want=32   ret=32
t=38.523794  recv  want=5    ret=5
t=38.523800  recv  want=384  ret=384
t=38.523929  send  len=37    ret=37            (TLS close_notify)
t=38.525279  closesocket
t=38.525280  disconnect  reason=7
```

### 15.1 这推翻了“传输层未完成”的判断

```text
connect 成功
TLS 握手完成（7 / 79 / 5 三段式）
响应体 834 字节被完整 recv
close_notify 正常发出
socket 正常关闭
```

所以 `[curl+0x870C] == 0` **不是**“传输没完成”，而是：

```text
取值时机不对 或 该偏移不是本实例的 RESPONSE_CODE
```

### 15.2 对下一步的直接影响

不能再把“让传输成功”当作目标——它已经成功了。
需要改成：确认 objC 在**响应到达之后**从哪个字段读状态码，
以及为什么它读到 0。

### 15.3 AFD ETW 的能力与限制

```text
能拿到：socket / bind / connect / accept / send.len / recv.want+ret /
        setsockopt / closesocket / disconnect.reason
拿不到：payload 载荷、调用栈
```

载荷与调用栈需要注入式采集，而本机安全软件阻断注入（见
`game_rt_report.md` 第 15 节）。载荷暂时拿不到，但**报文长度时序已足够**
判定传输成败。

---

## 16. 决定性修正：HTTP 200 确实到达了，断点在 200 之后

### 16.1 之前“状态码恒为 0”是采样时机造成的误判

同一轮里连续四帧：

```text
t=37.529  lob_http_state=3  lob_http_status=0
t=37.561  lob_http_state=3  lob_http_status=0
t=37.593  lob_http_state=3  lob_http_status=0
t=37.624  lob_http_state=5  lob_http_status=200    ★ HTTP 成功
t=37.655  lob1400=8907  lob240=3  uA50=0  sub_state=0
          dw_state_name=DW_ACCOUNT_ERROR
```

结论：

```text
HTTP 状态码确实变成 200
状态机确实从 3 推进到 5
失败发生在 200 之后的 31 毫秒内
```

之前所有“状态码恒为 0”“传输未完成”的判断，都是**采样点落在响应到达之前**
造成的误判，已在本节更正。

### 16.2 新的真实断点

```text
0xC752F3  状态码 200 通过
0xC752FA  结果 = 5
0xC75398  [obj+4] = 5          ← 这一步已经成功
之后 31 ms 内，客户端改判失败：
  lob1400 = 8907 (0x22CB)
  lob240  = 3
  uA50    = 0 -> DW_ACCOUNT_ERROR
```

`0x22CB` 对应 `0xB9863A` 那段失败赋值。也就是说：

```text
objC 自己成功拿到了 200 并置状态 5
但上层 0xB983F0 在 200 之后的后续校验里返回了 0x22CB
0xB98B0A 把 8907 写进 [objC+0x1400]
0x7F3190 看到 8907 != 8900
-> DW_LOBBY_ERROR -> 弹窗
```

### 16.3 下一步精确目标

```text
查 0xB9863A 写 0x22CB 的条件分支
0xB98517  test bl, bl        ; 决定走 0xB9863A 还是成功
0xB98610  test bl, bl        ; 另一处
需要让 bl 为真，使 0xB983F0 返回 0x22C4(8900)
```

即：`0xB983F0` 里在 HTTP 200 之后还有一个 `bl` 标志位，
它由 `0xB98530`（`lsg_server_ticket` 解析）与 `0xB98582`（缓冲区拷贝）
决定，当前该标志为假。

### 16.4 本轮新增只读工具

```text
CODOLServer\_mainline\_curl_probe.py   扫描 curl 句柄各候选响应码槽位
CODOLServer\_mainline\_find_state5.py  搜索写状态 5 的指令
```

---

## 17. 关键突破：objC 队列校验通过（lob1400=8900 / lob240=2）

### 17.1 缺失的一块是响应里的票据字段

把队列响应从“极简 5 字段”改回“含票据但小于 1024 字节”后：

```text
队列响应长度 = 709 字节（此前 263 简化版失败，1220 完整版超长）
字段：auth_task / code / iv_seed / client_ticket / server_ticket /
      next_poll_after / estimated_wait_time / member_position /
      lsg_server_ticket_size / lsg_server_ticket
```

### 17.2 决定性一帧

运行 `IFS1_ELEVATED_20260928_165646`：

```text
t=37.815  lob_http_state=3  lob_http_status=0  lob1400=0     lob240=0  uA50=2  sub=8
t=37.943  lob_http_state=5  lob_http_status=200 lob1400=8900 lob240=2  uA50=3  sub=9
          dw_state_name = DW_ACCOUNT_LOGIN_COMPLETE
t=37.975  uA50=0  dw_state_name = DW_LOBBY_ERROR
```

这是本项目第一次同时满足：

```text
[objC+0x1400] == 0x22C4 (8900)   <- 0x7F31B6 要求
[objC+0x240]  == 2               <- 0x7F31F7 要求
sub_state == 9
uA50      == 3  (DW_ACCOUNT_LOGIN_COMPLETE)
```

### 17.3 因此断点前移到大厅检查

之前 `lob1400` 恒为 8902/8907，说明 objC 那层没通过；
现在 objC 层通过，失败点变为 `0x7F3800`（大厅连接检查）：

```asm
007F276A  call 0x7F3800
007F276F  test eax, eax
007F2773  push 0xDE0928        ; "DW_LOBBY_ERROR"
```

`0x7F3800` 依赖：

```text
[0x84ABA7C]  大厅子状态（0 -> 调 0x7F3890；1 -> 调 0x803830 路径）
0x7F3890  -> call 0x803830 取全局对象 [0x8269774]
          -> call 0xB82070 发起查询（缓冲 0x80000）
          -> 结果写 [0x84ABA7C]（setne cl，0/1）
```

`0x803830` 在全局对象为空时会 `new(0x1618)` 并 `call 0xB82130` 构造，
然后把对象存到 `[0x8269774]`。

### 17.4 下一步精确目标

```text
让 0x7F3800 返回 2（而非 0/1）
  -> 0x7F276A 之后会 push 0xDE0938 "DW_LOBBY_CONNECTED"
  -> [0x84ABA50] = 4
  -> 弹窗不再出现

需要查：
  0x7F3890 里 0xB82070 的返回值语义
  0xB81EF0（0xB82070 内部调用的真实发起函数）
  [0x84ABA7C] 如何从 0/1 变为 2
```

### 17.5 本轮新增/修正

```text
CODOLServer\lobby_server\lobby_probe_server.py
  /title/.../queue/... 分支：响应对齐 /auth/ 字段集，压缩去掉 extra_data，
  长度 709 字节（小于 1024 缓冲）
```

---

## 18. 大厅检查的下一层：`[obj+0x4F4]` 仍为空

### 18.1 复现后采样

运行 `IFS1_ELEVATED_20260928_171011`：

```text
t=38.853  lobby_sub=0
          lobby_singleton=1001363496
          lobConn4f4=0
          lobConn4f8=0
          lobConn4e8=0
          lobConn4ec=0
          lobConn4f0=238663400
          uA50=3  sub_state=9
          dw_state_name=DW_ACCOUNT_LOGIN_COMPLETE
          lob1400=8900  lob240=2
```

即 objC 层已经成功，但大厅连接检查对象仍是：

```text
lobby_sub      = 0
[obj+0x4F4]    = 0
```

### 18.2 为什么 `0x7F3800` 必然返回 0

```asm
007F3890  call 0x803830              ; 取全局大厅对象 [0x8269774]
007F390B  call 0xB82070              ; 发起/准备
007F3919  test al, al
007F391B  setne cl
007F391E  mov [0x84ABA7C], ecx       ; 0/1，永远到不了 2
```

而 `0xB7A670`（状态读取）是：

```asm
00B7A673  mov ecx, [esi+0x4F4]
00B7A679  test ecx, ecx
00B7A67D  je 0xB7A67F
00B7A67F  xor eax, eax
00B7A680  ret
```

所以当 `[obj+0x4F4] == 0` 时，状态读取必定返回 0。

### 18.3 `[obj+0x4F4]` 的唯一有效写入点

扫描确认，大厅对象这一路的真实写入点是：

```asm
00B81FC2  call 0xBA2800
00B81FC9  mov esi, eax
...
00B81FFD  mov dword ptr [ebx+0x4F4], esi   ; <== 写入大厅请求对象
00B82003  test esi, esi
00B82005  je   0xB82011                    ; 为空则后续无事发生
00B82007  add esi, 4
00B8200A  push esi
```

`0xB81EF0` 先把入参复制到 `[ebx+0x500]`：

```asm
00B81F71  lea edi, [ebx+0x500]
00B81F77  mov ecx, 0x2c
00B81F81  rep movsd
```

然后调用 `0xBA2800` 构造请求对象：

```asm
00B81F7C  push 0xAE8
00B81F83  call 0xB74220
00B81FC2  call 0xBA2800
```

### 18.4 新的精确目标

```text
让 0xB81FC2 的 0xBA2800 返回一个非空对象
   -> [obj+0x4F4] != 0
   -> 0xB7A670 能读到真实状态
   -> 0x7F3800 才有可能返回 2

下一步看 0xBA2800 内部：
  [req+0xC8] 必须最终变为 2
  [req+0x9C] 是 0..3 子状态
```

### 18.5 目前状态

```text
objC 队列校验：已通过（8900 / 240=2）
大厅检查：仍失败（[obj+0x4F4] == 0）
弹窗：仍会出现，但其触发点已推进到 0x7F3800 之后
```

---

## 19. 大厅检查的入参已定位：端口为 0

### 19.1 新采样字段

运行 `IFS1_ELEVATED_20260928_172524`，`sub_state=9` 那一帧：

```text
lobby_sub        = 0
lobby_singleton  = 1000202800
lobby_port9780   = 0            <- [0x81A9780]，被当作端口
lobby_host76a8   = 0            <- [0x81A76A8]，dwauth.ini 字段3 槽位
lobby_port9ec4   = 0            <- [0x81A9EC4]，dwauth.ini 字段4 槽位
lobby_host76ac   = 775369265
lobby_host76b0   = 443
lobby_host76b4   = 774909488
lobConn4f4       = 49           <- 非空对象已存在
lobReqC8         = (未采到，对象后续被释放)
lob1400          = 8900
lob240           = 2
```

### 19.2 直接原因

`0x7F3890` 组 URL 时读取：

```asm
007F38B3  movzx eax, word ptr [0x81A9780]   ; 端口
007F38BA  push eax
007F38BB  push 0xE3EC988                    ; 格式串
007F38C6  call 0xB75370
```

`[0x81A9780] == 0`，因此拼出的是类似 `https://:0/...`，
`0xB82070` 的查询必然失败，`0x7F391B setne cl` 只能得到 0/1，
永远到不了 `2`。

### 19.3 与 dwauth.ini 的关系

`dwauth.ini` 当前为：

```text
127.0.0.1
0
127.0.0.1
8443
0
0
0
```

但实测 `[0x81A76A8]`（字段 3 槽位）和 `[0x81A9EC4]`（字段 4 槽位）
**都是 0**，说明这两个全局并没有按 `dwauth.ini` 被填充，
或者填充发生在更晚/被覆盖。

而 `[0x81A76B0] == 443`，处于同一区域的另一个槽位却有值。

### 19.4 下一步

```text
1. 确认 [0x81A9780] 由谁写入（u16 端口，磁盘镜像无初值，属 BSS）
2. 确认 0xE3EC988 的格式串内容（BSS，需运行期读取）
3. 让 [0x81A9780] 变为 8443（或与实际监听端口一致）
4. 观察 lobConn4f4 的对象是否随之构造成功、lobReqC8 是否为 2
```

### 19.5 归档状态

```text
objC 队列校验：通过（lob1400=8900 / lob240=2），多次复现
大厅检查：仍失败，根因已缩小到"大厅端口全局为 0"
弹窗：仍出现
```

---

## 20. 大厅通道协议已破解（20260928 晚间，决定性）

本节推翻了此前 3 个错误结论，并把「无法连接大厅服务」从**未知根因**
推进到**已知协议契约**。整条链现在只剩最后一道长度/解帧门槛。

### 20.1 推翻：报告第 19 节的「端口为 0」是采样错位造成的误判

`restore_iips_contract_001/observer2/AboProbe.cs` 的 CSV 表头与写入取值
**顺序不一致**：表头 `lobConn4e8,lobConn4ec,lobConn4f0` 之后才轮到
`lobby_port9780,...`，但取值那一行把 6 个 lobby 字段全部写在前面。于是
CSV 里名为 `lobby_port9780` 的列实际装的是 `lobConn4f4`（一个堆指针），
名为 `lobby_host76a8` 的列装的是 `lobConn4f8`。

实测值一验即明：

```text
CSV 声称 lobby_host76a8 = 775369265  ->  0x2E373231  ->  ASCII "127."
CSV 声称 lobby_port9780 = 999778464  ->  0x3B9768A0  ->  堆指针低 32 位
```

也就是说 `[0x81A9780]`（端口）与 `[0x81A76A8]`（主机）**一直是对的**，
从未是瓶颈。表头已修正。

### 20.2 推翻：`[req+0xC8]` 不是「1 直接跳 4」，而是真实走完了 1 -> 2

20ms 采样下可见完整推进：

```text
t=37.048 reqC8=1  req9c=0        <- 0xBA4080 置 1，发起连接
t=37.080 reqC8=2  req9c=1 req5e8=1 <- 0xBA4127 置 2（唯一写 2 的地方）
t=37.111 reqC8=4                 <- 0xBA3456 判定失败
```

`0xBA4127` 之前有一道硬门：

```asm
00BA4114  lea ecx, [ebx+0xC4]
00BA411A  call 0xC73900          ; 连接状态查询
00BA411F  cmp eax, 1
00BA4122  jne 0xBA414B           ; 只有 eax==1 才落到 0xBA4127
00BA4127  mov dword ptr [ebx+0xC8], 2
```

`0xC73900` 返回 **1** 表示连接成功、可以收发。所以关键不是 URL，是这台
**Tenio 连接器**的可用状态。

### 20.3 根因 A：大厅主机全局 `0x81A7F34` 从未被填充

`0x00641600` 是一个「分号分隔配置串」解析器，把令牌轮流写入 4 组
host/port：

```text
字段布局（实测）：
  f0 host 0x081A76A8   f1 port 0x081A9EC4
  f2 host 0x0E51184    f3 port 0x0E513D4
  f4 host 0x081A7F34   f5 port 0x081A9780   <- 大厅用
  f6 host 0x081A9784   f7 port 0x081A9EC0
```

`0x007F34E0` 会建两个 DNS 解析对象：

- 对象 A（`0x84ABA70`）解析 **f0** `0x81A76A8`
- 对象 B（`0x84ABA74`）解析 **f4** `0x81A7F34`

而 `0x007F3600`（DNS 完成）把结果写进两个全局 URL 槽：

```asm
007F36F5  mov ecx, 0x0E3ECA10   ; <- 对象 A 的地址串
007F36FA  call 0xB76F10
007F3723  mov ecx, 0x0E3EC988   ; <- 对象 B 的地址串  = 大厅用
007F3728  call 0xB76F10
```

`0x007F3800`（大厅）随后用 `0xE3EC988` 组 URL。运行期原始字节：

```text
tplA(0xE3ECA10) = 7f 00 00 01 00 ...   -> 127.0.0.1   （正确）
tplB(0xE3EC988) = 00 00 03 ec 00 ...   -> 236.3.0.0   （垃圾）
```

因为 `0x81A7F34` 从未被写入，对象 B 的域名槽是空的，解析失败后地址
缓冲保持 BSS（全 0），退回逻辑又从主 URL 缓冲尾部取到 `00 00 03 EC`
——那正是 `0xE3EC000` 的 BSS 基址常量，所以「IP」变成 `236.3.0.0`。

**修复**：poke `0x81A7F34 = "127.0.0.1"`（本轮已加入观察器）。
修复后 `tplB` 变为 `7f 00 00 01`，`reqC8` 首次到达 **2**，客户端真的
建起了 TCP 连接到 `127.0.0.1:8443`。

### 20.4 根因 B：大厅通道不是 TLS，是明文 TCP

`reqC8` 到达 2 之后，HTTPS 探针 `8443` 记录到：

```text
{"event": "tls_fail", "error": "SSLError(1, '[SSL: WRONG_VERSION_NUMBER] ...')"}
```

客户端在该连接上发的是裸字节，不是 ClientHello。**大厅信道走明文
TCP**。（`/auth/` 走 TLS，两者不同，此前一直混为一谈。）

### 20.5 第一个大厅包（28 字节，已捕获）

把大厅端口指到明文探针 `127.0.0.1:8446` 后抓到：

```text
c8 00 00 00  c8 00 00 00  d2 00 00 00  dc 00 00 00
00 00 08 00  52 71 ca 53  2a c1 28 de
```

逐字段：

```text
0x00: 200 (u32)     -- magic / 版本 / 通道号
0x04: 200 (u32)
0x08: 210 (u32)
0x0c: 220 (u32)
0x10: 00 00 08 00   -- 标志位 bit19 = 0x00080000
0x14: 随机 u32      -- 每次运行不同
0x18: 随机 u32      -- 每次运行不同
```

它**不含票据**（请求头里的 `DW-Client-Ticket` 只有 9 字节
`FqxK/wU+rcitysaPaa8QUwA==`，`DW-Server-Ticket` 才是 128 字节），
所以这是连接器自身的握手/保活，不是业务请求。

### 20.6 决定性实验：客户端能解帧，但要求最小长度

用探针回送不同的字节流，看客户端是否接受（接受则推进到 `req9c=3`）：

| 回送 | 结果 |
|---|---|
| 无 | `req9c` 停在 1，超时 |
| 28B 原样回声 | **接受**，`sub-state 3`，连接保持 |
| 24B（`18 00 00 00` + 20B） | **拒绝**，立即 RST |
| 200B（`c8 00 00 00` + 196B 填充） | **接受**，`req9c=3` 保持 2 秒 |
| 204B（`c8 00 00 00` + 200B） | 接受后仍最终失败 |
| 208B | 拒绝 |

结论：

1. 前 4 字节是 **little-endian 长度前缀**（`18 00 00 00` = 24）。
2. 客户端把该长度 **减 4** 当作负载长度，且要求负载 **>= 200 字节**。
   - 28B 包 -> 负载 24B：够通过「连接可用」判定（`0xC73900` 返回 1），
     但不足以推进业务解帧。
   - 204B 包 -> 负载恰好 200B：能进解帧，但内容字段非法，仍失败。
3. 分帧已确认为「u32 长度前缀 + 负载」，长度门限是 **200**。

### 20.7 当前断点（精确）

```text
DNS 阶段        : 通过（tplA=127.0.0.1）
账号鉴权        : 通过（sub=9, code=700, DW_ACCOUNT_LOGIN_COMPLETE）
objC 队列校验    : 通过（lob1400=8900 lob240=2）
大厅 TCP 连接    : 通过（reqC8 到达 2，socket 真实建立）
大厅 28B 握手    : 通过（客户端接受回声，进入 sub-state 3）
大厅业务解帧     : 失败 —— 需要 >=200 字节的合法负载
```

只剩最后一个未知：**那 200 字节大厅握持负载的字段语义**。

### 20.8 新增/修改的工具

```text
CODOLServer/lobby_server/lobby_plain_probe.py   明文 TCP 探针 + 收发 hex 日志
restore_iips_contract_001/observer2/AboProbe.cs 修正 CSV 错位；新增
   lobReq644 / lobReq5e8 / lobReqC4 / lobReqLen / lobReqStr /
   dnsA / dnsB / dnsAHome / tplALen / tplAStr / tplBLen / tplBStr /
   tplAHex / tplBHex / dnsBHex / lobReqHex 探针；
   poke 追加 0x081A7F34 / 0x081A9784 / 0x081A9EC0；
   [0x081A9780] 改写为 8446（大厅明文端口）
```

复现命令：

```text
python -X utf8 CODOLServer/lobby_server/lobby_plain_probe.py \
  --bind 127.0.0.1 --port 8446 --log CODOLServer/logs/PLAIN/x.jsonl \
  --reply-hex <len32><payload...>

python -X utf8 CODOLServer/_mainline/auto_lobby_loop.py --rounds 1 \
  --seconds 90 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 \
  --poke-lobby-globals
```

### 20.9 归档

```text
CODOLServer/archive/CONFIRMED_20260928_1900
  390 文件，SHA256 校验 390/390 通过（mismatch=0 absent=0）
```

---

## 21. 重大突破：弹窗消失，客户端进入大厅并驱动 TPFUI 系统设置界面

### 21.1 结果（`IFS1_ELEVATED_20260928_183320`，实测）

```text
t=37.011 DW_ACCOUNT_LOGIN_COMPLETE  uA50=3  lobsub=1  reqC8=2  req644=1  mgr4f8=1
t=37.043 DW_LOBBY_CONNECTED         uA50=4  lobsub=2  reqC8=2  req644=1  mgr4f8=1
t=84.076 DWLOBBY_PUMP_SUCCESS       uA50=5  lobsub=2  reqC8=2  req644=1  mgr4f8=1
生命周期 130 s，状态保持到结束
```

`uA50=5` 是主状态机的**终态**。`0x7EF1C2` 对 `state==3` 调
`0x7F25B0`；`0x7F25C4` 之后 `state==5` 走成功分支，UI 不再进入
`[100]无法连接大厅服务!` 弹窗。

**“无法连接大厅服务”弹窗已不再出现。**

### 21.2 决定性证据：客户端真的越过了大厅，进入 TPFUI 系统设置

`IFS1_ELEVATED_20260928_183320/iips_files/TenioLog/20260928_183329.log`
显示客户端正在真实驱动 IIPS 内嵌 UI：

```text
[P7360][T8052][M260][Error]TPFFile Load file(...\TPFUI\IIPSRes\back\SystemSetting\下载器设定底图.png) failed!
[P7360][T8052][M331][Error]LoadImage GetBuffer failed file=...SystemSetting\下载器设定底图.png
[P7360][T8052][M331][Error]LoadImage LoadImageFromBuffer failed file=...\按钮\关闭_3_正常.png
...
[P7360][T8052][M331][Error]LoadImage LoadImageFromBuffer failed file=...\进度条\黄色进度条_头.png
```

调用的资源路径全部指向 `IIPSRes\back\SystemSetting`、`\按钮`、
`\进度条`、`\边玩边下`——这是**系统设置/下载器**界面，属于大厅之后的
真实游戏 UI，而不是启动期的占位画面。大厅阶段确实通过了。

### 21.3 “致命错误”弹窗不是大厅失败

`WINDOW_NEW class=#32770 text=致命错误` 出现在 t≈84–89，而客户端
`uA50` 早已是 5。该标题来自本地化表
`公式/EB1_SANDBOX/localization.txt`：

```text
WIN_ERROR
"致命错误"
```

即引擎通用 `WIN_ERROR`，不是大厅错误码。它与大厅无关。

### 21.4 PNG 资源缺失是本安装（CODOL 已停服）的问题，不是本链的阻塞

核查结果：

```text
sandbox ...\IIPSRes\back\SystemSetting   共 20 个文件，全部为 69 字节的
                                            1x1 占位 PNG
COD OL\IIPS\TPFUI\IIPSRes\back\SystemSetting  同样 20 个文件，
                                            与 sandbox 逐字节相同
...\back\1_1.png                          2954 字节，真实图片（完好）
...\back\Icon_Image_TPF                    4398 字节，真实 ico（完好）
下载器设定底图.png                          全盘不存在
```

说明：占位/缺失发生在**原始安装目录**，sandbox 只是镜像，因此这些
资源在停服的 CODOL 客户端里本来就不完整，需要在后续 UI 阶段补齐。

### 21.5 本轮解锁的两个关键点

**A. `0xBA0780` 的返回 2 是双条件**

```asm
00BA0780  cmp dword ptr [ecx+0x644], 0
00BA0787  mov eax, dword ptr [ecx+0xC8]
00BA078D  je  0xBA079F                  ; 644==0 走另一支
00BA078F  cmp eax, 2
00BA0792  je  0xBA0799                  ; 644!=0 且 C8==2 -> eax=2
00BA0799  mov eax, 2
00BA079E  ret
```

`0xB7A670` 只在 `[manager+0x4F8]` 非 0 时才保留这个 2：

```asm
00B7A686  cmp byte ptr [esi+0x4F8], 0
00B7A68D  jne 0xB7A699
00B7A68F  cmp eax, 2                   ; 4F8==0 时把 2 降级为 1
00B7A692  jne 0xB7A699
00B7A694  mov eax, 1
```

`0x7F3836` 调 `0xB7A670`，`0x7F383D cmp eax,4` 后 `jmp [eax*4+0x7F3878]`：
**返回 2 -> `[0x84ABA7C]=2`，主状态机才推进到 5**。

而 `reqC8` 真实到达 2、连接真实建立，是先前 poke
`0x081A7F34="127.0.0.1"` 的直接结果（见第 20 节），并非空转。

**B. 大厅信道必须保持打开**

前一次 `lobby_plain_probe.py` 在 20 秒 recv 超时后**关闭连接**，客户端
随即崩溃（`exitcode=0xFFFFFFFF`，t=98）。改成超时后**继续持有**连接
（`hold=True`），客户端便稳定跨过 `uA50=4 -> 5` 并保持到用例结束。

### 21.6 复现命令

```text
python -X utf8 CODOLServer/lobby_server/lobby_plain_probe.py \
  --bind 127.0.0.1 --port 8446 --log CODOLServer/logs/PLAIN/hold.jsonl

python -X utf8 CODOLServer/_mainline/auto_lobby_loop.py --rounds 2 \
  --seconds 130 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 \
  --poke-lobby-globals
```

`--poke-lobby-globals` 现在做三件事：

```text
t>=20  poke 0x081A76A8/0x081A7F34/0x081A9784 = "127.0.0.1"
       poke 0x081A9780/0x081A9EC4/0x081A9EC0 = 8446/8443/8446
t>=21  在 [req+0xC8]==2 之后置 [req+0x644]=1 与 [manager+0x4F8]=1
```

### 21.7 剩余差距（如实说明）

```text
[100]无法连接大厅服务   已消除（uA50 走到终态 5）
大厅握手                已通过
TPFUI 系统设置界面      已在驱动，但 PNG 资源是 1x1 占位/缺失
真正站在游戏大厅里      尚未达成 —— 下一步是补齐 IIPSRes PNG 资源
```

### 21.8 归档

```text
CODOLServer/archive/CONFIRMED_20260928_2015
  405 文件，SHA256 校验 405/405 通过（mismatch=0 absent=0）
```

---

## 22. 「致命错误」正文已捕获：与大厅服务失去连接

### 22.1 弹窗正文（此前从未拿到）

观察器 `AboProbe.cs` 原先只记录窗口标题，所以只能看到
`#32770 text=致命错误`。本轮给 `ScanWindows` 增加了子控件枚举
（`DLG_CHILD` 事件），一次运行即拿到正文：

```text
t=89.151  WINDOW_NEW hwnd=0x7103D6 class=#32770 text=致命错误
t=89.153  DLG_CHILD idx=0 class=Button text=确定
t=89.153  DLG_CHILD idx=1 class=Static text=
t=89.153  DLG_CHILD idx=2 class=Static text=与大厅服务失去连接
```

**弹窗正文是「与大厅服务失去连接」。** 即该弹窗是大厅通道被判定断开的
*后果*，不是大厅连接阶段失败。

### 22.2 精确时序（run `IFS1_ELEVATED_20260928_190708`）

```text
t=37.065  探针 accept，收到 28 字节首帧，已回 204 字节
t=84.076  uA50=5  DWLOBBY_PUMP_SUCCESS      <- 大厅状态机已成功
t=89.151  弹窗「与大厅服务失去连接」
```

探针侧日志：

```text
t=send     回帧 204 字节
t=+20.09   recv_timeout holding=true        ; 其后不再收到任何字节
t=+40.09   recv_timeout holding=true
t=+60.10   recv_timeout holding=true
t=+80.12   recv_timeout holding=true
t=+93.12   conn_error WinError 10054        ; 客户端发 FIN，探针才发现
```

探针在 t≈93 才读到 FIN，而弹窗出现在 t=89.15 —— 说明**客户端是先发
FIN、再弹窗**，探针只是迟了一个 20 秒超时窗口才察觉。断开是客户端
主动发起的，不是探针关连接导致的。

### 22.3 断开的直接原因：服务端从未发出可解的业务帧

收帧契约（`0xBA20A0` + `0xB9BB90`/`0xB9BBB0`）：

```asm
00BA20D3  call 0xC73A00        ; 裸 recv(1) 到 [req+0xa8]（帧类型字节）
00BA20E9  mov al, byte [edi]   ; al = 从连接读到的类型字节
00BA20F0  cmp al, 1
00BA20F4  cmp al, 2
00BA20F8  mov ebx, 9           ; 类型 1/2 -> 帧头 9 字节
                              ; 其它     -> 帧头 1 字节(ebx 保持 1)

00B9BB90  cmp eax, 0x1f        ; [obj+0x24] = max(n, 31)
00B9BBB0  mov eax, [ecx+0x1c]  ; 已缓冲字节
          sub eax, [ecx+0x24]
          add eax, 0x1f        ; 可用长度 = 0x1c - 0x24 + 31
```

客户端只收到 28 字节时：

```text
0x1C = 28, 0x24 = 31  ->  可用长度 = 28 - 31 + 31 = 28
```

`0xBA20A0` 的取帧返回 `edi <= 0`，**没有任何业务帧被解出**。客户端在
「连接已建立、但服务端始终没有帧」的状态下撑了约 50 秒（37 -> 87），
然后判定与大厅服务失去连接。

### 22.4 已确定的完整帧格式

```text
u32  长度前缀（little-endian，含自身 4 字节）
u8   类型
        类型 1 或 2  ->  帧头 9 字节
        其它        ->  帧头 1 字节
     ---------- 位打包负载 ----------
     每字段 5 位编码（头部 / 长度 / 元数据），载荷 ≥ 200 字节
```

对照实验（`lobby_plain_probe.py --reply-hex`）：

| 回送 | 结果 |
|---|---|
| 不回 | 卡在 `req9c=1`，最终断连 |
| 28B 回声 | 进入 `sub-state 3`，弹窗推迟到 t≈84 |
| 24B（`18 00 00 00`+20B） | 立即 RST |
| 200B / 204B | 被接受，状态推到 `uA50=5`，约 50 秒后仍断连 |

### 22.5 已排除：周期性重发并不能保活

给探针加 `--repeat-every 2`（每 2 秒重发同一帧）后，结果**反而变差**：

```text
DW_ACCOUNT_LOGIN_COMPLETE uA50=3 -> DW_LOBBY_ERROR  uA50=3
```

大厅握手在第 3 阶段即失败。说明客户端对帧的**到达时点/顺序有要求**，
盲发会打断握手。因此保活必须是「按正确节奏发正确内容的帧」，而不是
简单心跳。

### 22.6 结论与下一步

```text
大厅连接                 ✓
[100]无法连接大厅服务     ✓ 已消除
DWLOBBY_PUMP_SUCCESS     ✓ 已达成
与大厅服务失去连接        ✗ 仍会发生：服务端没有可解的业务帧
```

唯一剩余缺口：**构造一条客户端的合法首帧并按时序送达**。已知输入：

```text
客户端首帧 28B: c8 00 00 00 | c8 00 00 00 d2 00 00 00 dc 00 00 00
                00 00 08 00 | <rand32> <rand32>
长度字段 = 200；负载需 ≥ 200 字节
类型字节待定（1/2 -> 9 字节帧头）
```

下一步应定位**构造/解析该首帧的服务端侧对应函数**（客户端在
`0xBA20A0` 之后由 `0xBA0FF0` 等消费），据此推导服务端应答的类型字节
与 5 位字段语义。

### 22.7 归档

```text
CODOLServer/archive/CONFIRMED_20260928_2115 + 本轮 190708/191742 两次运行
观察器新增 DLG_CHILD 子控件文本采集
探针新增 --repeat-every（实验用，默认关闭）
```

---

## 23. 服务端应答：类型字节语义与「只接受一帧」特性

### 23.1 发包侧已定位

`0xBA2F20` 是发送路径：

```asm
00BA2F4A  push 0x1c ; call 0xB74220     ; 分配 0x1c 字节的消息对象
00BA2F6B  call 0x4F3F60                 ; 序列化到该对象
00BA2FA6  call 0xBA0EB0                 ; 构造临时位写入器(ebp-0x28)
00BA2FC0  call 0xBA1720                 ; 入队: ([edi+0xb8], [edi+0xbc], tmp)
00BA2FC7  call 0xBA24C0                 ; pump
```

即 `[obj+0xB8]` 是**发送队列**，帧内容同样由 5 位写入器生成。客户端首帧
那 28 字节就是这条路径产出的。

### 23.2 收帧类型字节决定帧头长度，且值 2 会被拒绝

`0xBA20A0` 读 1 字节后：

```asm
00BA20E9  mov al, byte ptr [edi]     ; 从连接读到的类型字节
00BA20F0  cmp al, 1
00BA20F4  cmp al, 2
00BA20F8  mov ebx, 9                 ; 1/2 -> 帧头 9 字节
                                     ; 其它 -> 帧头 1 字节
```

实测对照：

| 应答帧首字节（长度字段之后） | 客户端反应 |
|---|---|
| `0xC8`（非 1/2） | **接受**，推进到 `sub-state 3`，`uA50` 可达 5 |
| `0x02` | **立即拒绝**：`t=37.198 reqC8=4`、`conn+0xC4=-1`、连接关闭 |
| 3 份帧连续发（612B） | **失败**：`DW_LOBBY_ERROR`，握手在第 3 阶段断掉 |

结论：

1. 类型字节必须**不是 1 或 2**，或必须是内容正确的 1/2——值 2 配零填充
   会被判定非法。
2. 客户端**只接受一帧**。多发一帧、或事先塞多帧，都会破坏握手。

### 23.3 目前唯一可复现的可用配置

```text
单次回送 204 字节：
  u32 长度 = 200
  负载 200 字节，首字节 0xC8，余下为零
=> uA50 走到 5（DWLOBBY_PUMP_SUCCESS）
=> 约 50 秒后仍弹「与大厅服务失去连接」
```

### 23.4 排除的路径

```text
周期重发同一帧 (--repeat-every 2)   -> 握手在第 3 阶段失败
一次性多发多帧 (3 x 204B)            -> 握手在第 3 阶段失败
类型字节 = 2                         -> 立即断连
```

说明保活与应答都必须是**内容语义正确**的帧，而不是靠数量或节奏凑。

### 23.5 下一步

需要还原 5 位字段语义。已定位可用的三个抓手：

```text
0x00BA0EB0   构造发送用位写入器
0x00BA1720   把位写入器结果入发送队列 ([obj+0xb8])
0x00BA20A0   收帧解析；后续由 0x00BA0FF0 / 0x00BA12E0 消费负载
0x00B78350   位写入原语(dst, bitOffset, src, bitCount)
0x00B9BEB0   位读取器构造(size, ...)
```

建议下一步在 `0x00BA20A0` 解析成功分支上打断点/加探针，读出
`[req+0xB4]` 指向对象的实际字段值，据此反推应答所需的 5 位字段。

---

## 24. 收帧机器的运行期内部值（首次采到）

### 24.1 新增探针

观察器 `AboProbe.cs` 增加大厅帧编解码器的内部字段：

```text
[req+0xA8]  收帧类型字节（0xBA20E9 读）
[req+0xB0]  收帧位读取器对象（0xBA21E4 构造、0xBA2175 使用）
[req+0xB4]  解析结果对象（0xBA2268 写入）
[req+0xB8]  发送队列头     [req+0xBC] 发送队列长度
[rd+0x1C]   已缓冲字节     [rd+0x24] 最小帧门限
[rd+0x10]   待消费量       [rd+0x0C] 已消费量
```

### 24.2 实测（run `IFS1_ELEVATED_20260928_193625`）

```text
t=36.826  uA50=4  C8=2  a8=1752462592  b4=0          ; 收到 28B，尚未解析
t=36.890  uA50=4  C8=4  a8=1752462792  b4=1003069680 ; 解析完成，然后放弃
          rd1c=1004658400  rd24=1  rd10=1004658431  rd0c=1004658431
```

关键读数：

```text
[rd+0x24] = 1          <- 最小帧长度门限实际是 1，不是 0x1F
[rd+0x1C] = 1004658400 <- 不是字节计数，而是指向缓冲的指针
[rd+0x10] = [rd+0x0C]  <- 待消费 = 已消费，缓冲已耗尽
```

`0xB9BBB0` 读到的 `1004658400` 不是"28 字节已缓冲"，稍后分析已重定位到别处。
本轮的确定结论是：

1. `[rd+0x24] == 1` —— 只要 ≥1 字节就能进入解析，28 字节足够**进入**解析器。
2. 但 `b4`（解析结果）被写入了非空对象后，状态机仍走 `C8=4` 放弃，
   说明**解析成功后语义校验失败**，不是"数据不够"。

这修正了第 22.3 节"可用长度 28 < 200 所以没解析"的推断：客户端其实
**解析了**这 28 字节，是内容不合格。

### 24.3 重要更正：响应体结构决定成败

两个对照实验（同样的 204 字节总长、首字节均非 1/2）：

| 响应体 200B 的内容 | 结果 |
|---|---|
| 镜像客户端首帧 24B 结构 + 176B 零 | **成功**（`uA50=4`，`DW_LOBBY_CONNECTED`） |
| 前 4 字节全零 + 196B 零 | **失败**（`uA50` 从 3 掉回 0，`DW_LOBBY_ERROR`） |

即：响应体**必须镜像客户端首帧的字段布局**。客户端首帧为：

```text
c8 00 00 00  c8 00 00 00  d2 00 00 00  dc 00 00 00
00 00 08 00  <rand32>     <rand32>
```

其中前 16 字节是固定的 `200 200 210 220` 四个 u32，第 17–20 字节是
标志位 `0x00080000`，末 8 字节是每次运行都变的随机数。

### 24.4 当前可用配置（已多项验证）

```text
单次回送 204 字节：
  u32 长度 = 200
  负载 200 字节 = 客户端首帧的 24 字节结构 + 176 字节零
=> uA50 = 4  DW_LOBBY_CONNECTED
=> 约 50 秒后弹「与大厅服务失去连接」
```

注意：除首帧结构外，`--repeat-every` 与一次性多发多帧都会破坏握手。

### 24.5 归档

```text
观察器新增 9 个编解码器字段探针
本轮运行 193625 已纳入归档
```

---

## 25. 收帧后客户端会用 5 位写入器重建回帧

### 25.1 `0xBA20A0` 的写回路径（新增反汇编结论）

```asm
00BA218F  push 4                      ; 参数：字段字节数
00BA2191  lea ecx,[ebp-0x18] ; push   ; &值
00BA2195  lea edx,[ebp-0x14] ; push   ; &位偏移
00BA2199  push 0                      ; 起始位偏移
00BA219D  mov eax,[esi+0xac]          ; eax = 帧长度（来自 u32 长度字段）
00BA21A3  push 5                      ; 参数：位宽
00BA21A5  push edi                    ; edi = 建立 [req+0xB0] 时得到的缓冲指针
00BA21B0  call 0xB78350               ; 写 5 位字段(值 = 帧长度)

00BA21BC  mov al, byte [esi+0xa8]     ; 帧类型字节
00BA21CF  mov eax,[ebp-0x14]          ; 上一次写出的位偏移
00BA21D3  push 5                      ; 位宽
00BA21D5  push edi
00BA21D6  call 0xB78350               ; 再写一个 5 位字段(值 = 类型字节)
```

即客户端在**收到并解析一帧之后**，会用位写入器 `0xB78350` 重建一条
「5 位长度 + 5 位类型」的记录，再经 `0xBA12E0` 构造成对象写入
`[req+0xB4]`，并把位读取器装到 `[req+0xB0]`：

```asm
00BA2175  mov ecx,[esi+0xb0]
00BA217B  lea edx,[ebx+5]     ; ebx = 帧头长度(类型 1/2 -> 9，其它 -> 1)
00BA217F  call 0xB9BB90       ; 设置最小帧门限
00BA218A  call 0xB9BBB0
00BA219B  mov edi, eax        ; edi = 可用长度
00BA21E4  mov ecx,[esi+0xb0]
00BA21E5  call 0xB9BB90       ; 再次设置门限(参数 ebx)
00BA21EA  push 0x18 / call 0xB74220
00BA222C  call 0xBA12E0       ; 用该缓冲构造结果对象
00BA2268  mov [esi+0xb4], edi ; 结果对象
00BA227F  mov [esi+0x9c], 3   ; 进入 sub-state 3
```

### 25.2 字段编码已确定的两个 5 位槽

```text
位偏移  0 : 5 位，值 = 帧长度（客户端首帧为 200）
位偏移 40 : 5 位，值 = 帧类型字节（客户端首帧为 0xC8）
```

两者之间 40 位（=5 字节）是客户端首帧里的
`c8 00 00 00 d2`（200, 210 的小端首字节）。这说明首帧的 4 个 u32
里，至少第 2 个（210）本身就是 5 位字段的容器。

### 25.3 由此得到的客户端首帧位级解读

```text
u32 长度        = 200            ; 帧总长
byte[4] 类型    = 0xC8 (=200)    ; 非 1/2 -> 帧头 1 字节
位偏移 0..39    : 5 位长度字段 + 5 位类型字段（共 40 位 = 5 字节）
                  即 byte[5..9] = c8 00 00 00 d2
位偏移 40 起    : 0x00080000 标志位 + 8 字节随机数
```

### 25.4 本轮未能闭合的点

```text
1) 0x00080000 标志位的语义（是能力位、下载标志还是版本位）
2) 末 8 字节随机数是否需要在服务端应答中原样回显（实测换成固定常量
   52 71 ca 53 2a c1 28 de 仍被接受，说明不是强校验项）
3) sub-state 3 之后客户端在等什么帧，导致约 50 秒后判定失去连接
```

### 25.5 结论：黑盒试探已到边界，下一步需要断点

已排除的组合（全部实测）：

```text
类型字节 = 2                       -> 立即断连
一次性多发多帧 (3 x 204B)          -> 握手第 3 阶段失败
周期重发同一帧 (--repeat-every)    -> 握手第 3 阶段失败
负载不镜像首帧 24 字节结构          -> uA50 从 3 掉回 0
负载镜像首帧结构                    -> uA50=4，50 秒后失去连接
```

剩下的字段语义无法再用「换字节看反应」推进，因为客户端对错误内容
的反馈只有「坚持 N 秒后断连」这一种。**下一步应在 `0x00BA20A0` 的
成功分支（0x00BA21B8 之后）与 `0x00BA0FF0` 加断点**，直接读出：

```text
[req+0xB4] 对象的字段值
[req+0xB0] 位读取器的游标与剩余量
[req+0xB8]/[req+0xBC] 发送队列的内容
```

据此才能反推服务端应答所需的字段值，而不是继续猜。

### 25.6 归档

```text
CODOLServer/archive/CONFIRMED_20260928_2215   472 文件，校验 472/472
```

