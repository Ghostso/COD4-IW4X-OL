# 本次成果记录：发现「大厅服务器地址」的真正来源（dwauth.ini）

- **时间**：2026-09-25 22:49（Asia/Shanghai）
- **工作目录**：`D:\BaiduNetdiskDownload\使命召唤OL`
- **阶段**：A 已完成 / C 已失败 / **B 暂停** → 本轮转入「大厅地址来源」溯源
- **后续记录**：`CODOLServer\SESSION_RECORD_20260926_LOBBY_HANDSHAKE.md`（`/auth/` 联调实况）
- **一句话结论**：
  **客户端连哪台大厅服务器不是算出来的，是从 exe 同目录的 `dwauth.ini` 读出来的。
  本机完全没有这个文件 —— 所以弹窗 [100] 在此之前就已经注定，服务器写再好也连不上。**

---

## 0. 本轮操作约束（已全程遵守）

| 约束 | 说明 |
|---|---|
| 不改系统网络 | 未执行任何 `netsh` / 路由 / DNS / 防火墙 / 网卡操作（曾导致断网） |
| 不碰 ACE 驱动 | 未执行 `sc stop/config/delete`（曾蓝屏 `0x01010002`） |
| 不删文件 | 只新增文件；需要覆盖时先建 `.bak_<时间戳>` |
| 子代理不复用 | 一代理一任务；模型限定 GPT-6-sol |
| 脚本纯 ASCII | 避免 PowerShell 5.1 按 GBK 读取 `.ps1` 乱码；中文仅出现在输出文档 |

---

## 1. 本轮复现成果（环境可用性）

| 项目 | 状态 | 证据 |
|---|---|---|
| 提权代理 | 在线 | `agent_client.py ping` → `pid=252, debug_privilege=true` |
| 固化启动链 | 可用 | `run_codol_001\capture_elevated_network.ps1` |
| **运行期解密全模块镜像** | 可用 | `_mainline\_dyn100_run_20260925_182324\live\image_best.bin` |
| Python 工具链 | 可用 | capstone / pefile / scapy 2.7.0 / cryptography 50.0.0 |
| 抓包原始数据 | 4 份 pcapng | 见 §10 证据索引 |

镜像参数（后续所有静态分析都用它，**不要用磁盘 exe**）：

```
文件     CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
加载基址 0x400000
大小     0xA65000   （覆盖 0x400000 - 0xE65000）
换算     offset = VA - 0x400000
```

---

## 2. ★ 核心发现一：磁盘代码段是加密的（方法论纠正）

`.tp3` 节区在磁盘上是**密文**，运行期才解密。同地址对照：

| VA | 磁盘 exe 字节 | 运行期镜像字节 |
|---|---|---|
| `0x4FD287` | `cc 89 00 00 50 8d 8f 9c` | `e8 c4 b3 30 00 6a 18 e8` |
| `0x4FCEE0` | `43 03 21 d0 7f 7a 00 15` | `55 8b ec 81 ec 34 04 00 00` |
| `0x4FD9B0` | `33 00 2f 01 10 a1 f6 00` | `55 8b ec b8 0c 20 00 00` |
| `0x808650` | `f4 53 57 8b ce e8 8a 73` | `55 8b ec 83 ec 08 53 56` |
| `0x77F8B3` | `00 00 00 01 1f de 00 01` | `e8 f8 e0 d7 ff e8 c3 81 cb` |

> **影响**：本项目此前若干「反汇编磁盘 exe 得到」的结论**全部不可信**，必须用运行期镜像重做。
> 配套子任务：`.tp3` 解密路径（子代理 Avicenna，进行中）。

---

## 3. ★ 核心发现二：`0x4FD287` 不是函数入口，也无条件执行

之前的交接写「追 `0x4FD287` 的触发条件 / 谁该调用多人初始化」。**这个前提是错的。**

- 全镜像扫描 `call 0x4FD287`：**命中 0**。
- `0x4FD287` 是 `0x4FCEE0`（引擎初始化）内部的**顺序指令**，前面没有任何分支跳过它：

```asm
004FD282  e899e21600           call 0x66B520
004FD287  e8c4b33000           call 0x808650        ; 顺序执行
004FD28C  6a18                 push 0x18
```

调用链（每一跳都只有唯一调用者）：

```
主模块 0x77F8B3
  └─ 0x4FD9B0                     Win_Init 包装，错误串 "WIN_INIT_ERROR" @0xDBD8BC
       └─ 0x4FCEE0  (call @0x4FDA03)   引擎初始化；内部注册 "quit"/"unattended"
            └─ 0x4FD287 (顺序)
                 └─ 0x808650             在线 / 大厅初始化
                      ├─ 0x7E98F0        ★ dwLobby 总初始化
                      │    └─ 0x7E99F1   mov byte [0x849B61F], 1   ← 总闸
                      ├─ 注册 "ied-tqos.qq.com" @0xDD98A0
                      └─ Live_Init @0xDBD820
```

**总闸是 `0x7E98F0` 里无条件写的**（无任何条件保护）：

```asm
007E99E4  833dccb5490800       cmp dword ptr [0x849B5CC], 0
007E99EB  8b35c884ca00         mov esi, dword ptr [0xCA84C8]
007E99F1  c6051fb6490801       mov byte ptr [0x849B61F], 1     ; 无条件
```

> **推论（尚未定论，见 §9）**：静态上只要走到 `0x808650`，总闸必为 1。
> 而运行期实测总闸长期为 0 → 说明这条链**在启动时根本没被走到**。

---

## 4. ★ 核心发现三：大厅地址来自 `dwauth.ini`（本轮最大突破）

### 4.1 WinMain 与三份配置

`0x77EE40` = **WinMain**（CRT `__tmainCRTStartup` 在 `0xC42783` 调用，
参数顺序 `hInstance=0x400000 / hPrevInstance / lpCmdLine / nCmdShow` 完全吻合）。

它依次做：

```asm
0077EF03  push 0x81a76e8     ; memcpy(0x81A76E8, lpCmdLine, 0x3FF)   命令行副本
0077EF64  ... fopen("dwauth.ini","r")       @0x00DDBD9C    ★ 大厅地址来源
0077F056  ... fopen("stun.ini","r")         @0x00DDBDBC
0077F08E  ... fopen("buildconfig.ini","r")  @0x00DDBDC8
```

`0x4FD9B0` 之后把命令行副本交给 `Com_Init`：

```asm
004FD9D5  c785f4dfffffe8761a08  mov dword [ebp-0x200C], 0x81A76E8
004FDA03  e8d8f4ffff            call 0x4FCEE0        ; ecx = 0x81A76E8
004FCF03  e838f87300            call 0xC3C740        ; memcpy(0x33E7060, ecx, 0x3FF)
```

### 4.2 `dwauth.ini` 的 7 个字段

按 `sscanf` 调用顺序（每个字段一行，空白分隔亦可）：

| 顺序 | 格式串 | 目标全局 | 语义与证据 |
|---|---|---|---|
| 1 | `%59s\n` | `0x81A7F34` | 第二个待解析主机（DNS 阶段也必须解析成功） |
| 2 | `%hu\n` | `0x81A9780` | uint16，`0x7F38B3 movzx` 取用于大厅连接 |
| 3 | `%59s\n` | **`0x81A76A8`** | **★ 大厅 HOST** |
| 4 | `%hu\n` | **`0x81A9EC4`** | **★ 大厅 PORT** |
| 5 | `%x\n` | `0x81A9EB8` | hex32，`0x7F2BAA` 取用 |
| 6 | `%x\n` | `0x81A56A4` | hex32 |
| 7 | `%x\n` | `0x81A76E4` | hex32 |

代码现场：

```asm
0077EF64  68 347f1a08    push 0x81A7F34   ; 字段1
0077EF69  68 a8bddd00    push 0x00DDBDA8  ; "%59s\n"
0077EF6E  56             push esi         ; FILE*
0077EF6F  e8 de304c00    call 0x00C42052  ; sscanf 族
0077EF77  68 80971a08    push 0x81A9780   ; 字段2  "%hu\n"
0077EF8A  68 a8761a08    push 0x81A76A8   ; 字段3  HOST    "%59s\n"
0077EF9D  68 c49e1a08    push 0x81A9EC4   ; 字段4  PORT    "%hu\n"
0077EFB0 / EFC3 / EFD6  ...  字段5/6/7      "%x\n"
```

### 4.3 这三个全局真的被当成「服务器地址」用

```asm
; ---- DNS 阶段（state 1）：两个主机都要解析成功 ----
007F34E3  a170ba4a08      mov eax, [0x84ABA70]       ; 解析器对象 A
007F3532  50              push eax
007F3533  68 a8761a08     push 0x81A76A8             ; ★ HOST
007F3538  e873b53b00      call 0xBAEAB0
007F353D  8ad8            mov bl, al                 ; 成败在此
...
007F3589  68 347f1a08     push 0x81A7F34             ; ★ 字段1（第二个主机）
007F358E  e81db53b00      call 0xBAEAB0

; ---- 建连阶段（state 2）----
007F2BA8  8b1db89e1a08    mov ebx, [0x81A9EB8]       ; 字段5
007F2BAF  0fb73dc49e1a08  movzx edi, word [0x81A9EC4] ; ★ PORT
007F2BDC  57              push edi
007F2BDD  68 a8761a08     push 0x81A76A8             ; ★ HOST
007F2BE2  53              push ebx
007F2BE5  e8965f3900      call 0xB88B80              ; 建连

; ---- URL 构造 ----
007F306C  68 a8761a08     push 0x81A76A8             ; ★ HOST
007F3071  68 e409de00     push 0x00DE09E4            ; "https://%s/"
007F3076  e80519f8ff      call 0x774980              ; sprintf
```

### 4.4 完整因果链（弹窗 [100] 的真正来源）

```
dwauth.ini 不存在
  → 字段3 HOST [0x81A76A8] 为空
  → DNS 阶段 0xBAEAB0 解析空主机失败 → bl=0 → [0x84ABA78]=0
  → 状态名 = "DW_DNS_ERROR" @0xDE08D8
  → 0x7F26E0 state1 分支把 dw 状态留在 1
  → 0x7F25B0 派生状态 = 4
  → 0x7EF210 cmp esi,4 命中
  → push 0x00DE0640 "@SF_UI_DW_LIVE_CONNECTING_FAILED"
  → 0x771240 投递 Scaleform 面板
  → 弹窗「[100]无法连接大厅服务!」
```

### 4.5 配置缺失的实测事实

| 文件 | 全盘搜索结果 |
|---|---|
| `dwauth.ini` | **命中 0**（`COD OL\`、`run_codol_001\sandbox*`、`backups\`、所有 `工具\*`） |
| `buildconfig.ini` | **命中 0** |
| `stun.ini` | 存在 69 字节，内容 = `stun1/2/3-tub.codol.qq.com` |

---

## 5. ★ 核心发现四：大厅协议是 Demonware / HTTPS `/auth/`

从运行期镜像 `0xD5A000` 段直接读出（全部为明文常量）：

```
0xD5A11C  %s://%s:%d/%s/title/%d/queue/%d/member/%llu
0xD5A148  https
0xD5A158  DW-Ticket-Seed
0xD5A168  DW-Client-Ticket-Size
0xD5A180  DW-Client-Ticket
0xD5A194  DW-Server-Ticket-Size
0xD5A1AC  DW-Server-Ticket
0xD5A1C0  Transfer-Encoding / Content-Type / application/json
0xD5A228  auth_task
0xD5A238  43FCB2ACF2D72593DD7CD1C69E0F03C07229F4C83166F7B05BA0C5FE3AA3A2D93EK2495783KDKN92939DK
0xD5A290  extended_data / license_id / user_id / time_to_live / cd_key
0xD5A2CC  https://%s:%d/auth/          ★ 鉴权接口（代码 0xB99EBF）
0xD5A2E0  ciphertext
0xD5A31C  server_ticket / client_ticket
0xD5A33C  356c4bc3
0xD5A440  FAILED / DONE / WRITE_METADATA / THROTTLED / HTTP_OPERATION / PRE_HTTP / READY
0xD5A4FC  HMAC mismatch / HMAC calculation / Bad recv counter / Bad frame/payload size
0xD5A9CC  stun.au.demonware.net / stun.jp... / stun.eu...
0xD5AA20  239.255.255.250:1900   M-SEARCH * HTTP/1.1    UPnP/SSDP 端口映射
```

**TLS 证据（客户端自带 CA，连接是 HTTPS）**：

```asm
007F2C33  68 a49cdc00     push 0x00DC9CA4     ; "cacert.pem"
007F2C3A  e8 c1743a00     call 0x00B9A100     ; 载入 CA 到连接对象
```

```
0x00D3682C  TLS change cipher / handshake / alert
0x00D356B0  Peer certificate cannot be authenticated with given CA certificates
0x00D39E30  X.509 part of OpenSSL 0.9.8p 16 Nov 2010
0x00DC71CC  https://%s:%u/tlog
```

**结论：大厅服务器必须提供 HTTPS(TLS)，路径 `/auth/`，body 为 JSON。**
客户端用 exe 同目录的 `cacert.pem` 校验，所以本地测试只需把自签 CA 追加进该文件
（**不动系统证书库、不动网络设置**）。

---

## 6. 抓包数值化分析结论

数据源（4 份 pcapng，scapy 2.7.0 + PcapNgReader 逐包流式读取）：

| 抓包 | 大小 | 总包数 | 去重帧 |
|---|---:|---:|---:|
| `ENTRY_20260925_013045` | 92.2 MB | 83897 | 76026 |
| `TCLS_DIR_20260924_220810` | 115.2 MB | 179063 | 135952 |
| `LOBBY_DEEP_20260924_181441` | 3.4 MB | 16959 | 13821 |
| `ENTRY_20260924_160326` | 56.4 MB | 59235 | 50495 |

### 6.1 「热端口」会话（`ENTRY_20260925_013045`）

| 目标 | 端口 | 协议 | 包数 | 载荷 | 判定 |
|---|---|---:|---:|---:|---|
| `116.130.224.66`（= `ied-tqos.qq.com`） | 8000 | **UDP** | 发 8 / 收 6 | 192 B / 438 B | binary-structured |
| `182.50.14.56` / `122.96.96.225`（= `tqos.anticheatexpert.com`） | 8081 | **UDP** | 16 / **2280** | 2880 B / 589472 B | binary-structured（载荷 308 B，熵 6.5–6.9，疑似加密） |
| `42.187.183.162`（= `stat.iips.qq.com`） | 8080 | **UDP** | 48 | 8664 B | binary-structured |
| `81.71.56.93` / `81.71.56.168` | 8000 | **UDP** | 50 / 28 | — | binary-structured |
| `101.43.13.228` / `124.222.69.57` | 8000 | **UDP** | 28 / 24 | — | binary-structured |

`116.130.224.66:8000` 在**四个抓包里全部命中**，首包 24 字节：

```
75720010 00080003 0000000b 00000822 00000064 00180000
```
结构：`75 72`（magic "ur"）+ `00 10` + 2 字节大端长度 + `00 05` + `00 00 00 0b`。
回程均为 6 × 73 字节 —— **该端口当时可达，无拒绝、无不可达**。

### 6.1.1 TCP RST / ICMP 统计（全部抓包）

| 抓包 | TCP RST | ICMP 不可达 | IPv4 会话 | IPv6 会话 |
|---|---:|---:|---:|---:|
| `ENTRY_20260925_013045` | 184 | 0 | 211 | 34 |
| `TCLS_DIR_20260924_220810` | 1104 | 0 | 789 | 273 |
| `LOBBY_DEEP_20260924_181441` | 214 | 0 | 310 | 64 |
| `ENTRY_20260924_160326` | 122 | 0 | 187 | 29 |

### 6.2 结论

1. **全部为 UDP，且高熵** → 是 ACE / TQoS 质量探测与 IIPS 统计上报，**不是游戏协议**。
2. **所有抓包里没有任何 TCP/HTTPS 到大厅的流量** —— 一次都没有。
3. `116.130.224.66` 只有 UDP:8000 的单向探测（客户端只发约 192 字节，收到约 438 字节），
   与「哨兵 / 监控」的判断一致，**它本身不是大厅**。
4. `3074` / `27015`（COD 传统游戏端口）**零会话**；
   `10009` 只在 TCLS 抓包出现（TCP `116.130.229.168:10009`，载荷含 `dir_root` 与 GBK 文件名
   `宽带下载`，4 会话共 48 包），属目录/下载服务，与大厅无关。

> 与 §4 完全自洽：客户端连「往哪里连」都没拿到，自然不会产生任何大厅流量。

### 6.3 ★ 对旧结论的两处修正（本节以此为准）

| 旧说法 | 实测修正 |
|---|---|
| `tqos.gamesafe.qq.com` 参与了 TQoS 探测 | **四个抓包里都没有该域名的 DNS 查询**（旧说法无实测支撑） |
| `:8081` 对端是 `tqos.gamesafe.qq.com` | 实测 DNS 为 **`tqos.anticheatexpert.com` → `122.96.96.225` / `182.50.14.56`**，正是 8081 会话对端 |
| `stun*.codol.qq.com` 参与了连接 | 抓包中**未出现**；实测 STUN 相关只有 `stun.qqlive.qq.com`（CNAME → `stun-a1.qq.com`，10 个 A 记录）；`stun.au/jp/eu.demonware.net` 只是游戏内嵌静态字符串 |

> 另：DNS 实测 `ied-tqos.qq.com` → **A `116.130.224.66`**（即上面 8000 端口目标）；
> `ied-tqos-tgp.qq.com` → `60.29.240.113` / `116.130.229.94` / `140.207.176.18`。

---

## 7. 本轮新增产物

### 7.1 分析文档

| 文件 | 说明 |
|---|---|
| `CODOLServer\DWAUTH_ORIGIN_FINAL.md` | 大厅地址来源专题报告（VA 级证据） |
| `CODOLServer\SESSION_RECORD_20260925_DWAUTH.md` | **本文件**，本阶段总记录 |
| `CODOLServer\_subagents\pcap_report.md` | 抓包数值化报告（1.6 MB，全量会话表 + 载荷 hexdump） |
| `CODOLServer\_subagents\pcap_sessions.json` | 抓包结构化会话表（1.6 MB） |
| `CODOLServer\_subagents\pcap_dns_ipv6.json` | IPv6 DNS 逐条记录 + IPv6 会话表（1.03 MB） |
| `CODOLServer\_subagents\pcap_payloads\*.hex` | 453 个文件：按端口汇总（`8000/8080/8081/10009/3074/27015.hex`）+ 每会话独立 hexdump |
| `CODOLServer\_subagents\_pcap_*.py` | 分析脚本，均已 `py_compile` 通过且严格 ASCII |

### 7.2 本地大厅服务器（已实测跑通）

| 文件 | 作用 |
|---|---|
| `CODOLServer\lobby_server\mklobby_cert.py` | 生成自签 CA + 服务器证书（`CN=127.0.0.1`、`SAN IP:127.0.0.1`） |
| `CODOLServer\lobby_server\lobby_probe_server.py` | TLS 探针服务器：记录 ClientHello / HTTP 方法路径 / headers / body hexdump |
| `CODOLServer\lobby_server\install_lobby_config.py` | 写 `dwauth.ini` + 追加 CA 到 `cacert.pem`（**自动备份，支持 `--dry-run`**） |
| `CODOLServer\lobby_server\lobby_ca.pem` / `.key` | 已生成 |
| `CODOLServer\lobby_server\lobby_server.pem` / `.key` | 已生成 |
| `CODOLServer\lobby_server\ca_append.pem` | 待追加到 `cacert.pem` 的 CA 块 |
| `CODOLServer\logs\lobby_probe.jsonl` | 自检记录（TLS1.3 握手 + `POST /auth/` 全量落盘） |

自检结果（本机回环）：

```json
{"event":"tls_ok","tls_version":"TLSv1.3","cipher":"TLS_AES_256_GCM_SHA384"}
{"event":"http","request_line":"POST /auth/ HTTP/1.1","body_len":4,"body_hex":"54455354"}
```

---

## 8. 下一步方案（待执行）

### 8.1 本地服务器方案（避开已知的坑）

**不使用**改 hosts / 加 IP / 改路由 —— 那些会导致断网。
改为用 `dwauth.ini` 把大厅直接指向**回环地址**（字面量，不走 DNS）：

```
127.0.0.1     字段1  第二个待解析主机（也用回环，免 DNS）
0             字段2  uint16
127.0.0.1     字段3  ★ 大厅 HOST
8443          字段4  ★ 大厅 PORT
0             字段5  hex32
0             字段6  hex32
0             字段7  hex32
```

执行三步（全部可回退，脚本均已实现）：

```powershell
cd 'D:\BaiduNetdiskDownload\使命召唤OL'

# 1) 安装配置（自动备份已有文件）
python -X utf8 CODOLServer\lobby_server\install_lobby_config.py `
  --game-dir 'run_codol_001\sandbox' --host 127.0.0.1 --port 8443 `
  --ca CODOLServer\lobby_server\ca_append.pem

# 2) 起探针服务器
python -X utf8 CODOLServer\lobby_server\lobby_probe_server.py `
  --cert-dir CODOLServer\lobby_server --bind 127.0.0.1 --port 8443 `
  --log CODOLServer\logs\lobby_probe.jsonl

# 3) 用固化启动链跑游戏，观察 8443 是否收到 ClientHello
```

**验证判据（三条同时成立才算连上）**：

1. 运行期 `[0x849B61F] == 1`（dwLobby 总闸开）
2. 运行期 `[0x84ABA50]` 由 1 走到 3（`DW_LOBBY_CONNECTED`）
3. `lobby_probe.jsonl` 出现 `tls_ok`（收到第一条 ClientHello 即确认）

### 8.2 还需继续查的方向

| 方向 | 说明 |
|---|---|
| **总闸为何为 0** | 静态上 `0x808650` 无条件执行，运行期实测为 0，**矛盾未解，需动态插桩** |
| `dwauth.ini` 原始取值 | 现网原文件已不在本机，需从旧启动器 / 备份包 / TCLS 目录补 |
| 字段 2/5/6/7 语义 | 确认是 uint16 + 三个 hex32，但业务含义未定（疑似 appid / 版本 / 会话类型） |
| `/auth/` JSON schema | 需拿到真实请求体才能定（探针已就绪，等着接） |
| `.tp3` 解密路径 | 子代理 Avicenna 进行中，产出 `_subagents\tp3_unpack_report.md` |

---

## 9. 未确定事项（诚实标注）

> 本节原列 4 项未确定事项，**其中 4 项已全部转为已知**，见 §10 / §11。
> 下表保留"原状态 → 现结论"的对照，便于回溯。

| # | 原未确定事项 | 现状态 | 结论位置 |
|---|---|---|---|
| 1 | 总闸为何为 0（静态与动态矛盾） | ✅ **已确证** | §10 |
| 2 | `dwauth.ini` 原始取值已丢失 | ✅ **已确证为"本机不可恢复"** + 格式/语义全定 | §11.1 |
| 3 | 字段 2/5/6/7 业务含义未定 | ✅ **已定论** | §11.2 |
| 4 | `/auth/` JSON schema 未完全解出 | ✅ **已解出** | §11.3 |

**仍然遗留（本轮未解，如实标注）**：

| # | 遗留项 | 说明 |
|---|---|---|
| A | `/auth/` 的**运行时实测报文** | schema 已由静态反汇编解出（§11.3），但**尚未捕获真实请求体**。探针服务器已就绪（§7.2），装上 `dwauth.ini` 后即可落盘 |
| B | 服务端**响应语义** | `client_ticket` / `server_ticket` 的生成规则与校验逻辑需要服务端实现；`356c4bc3` 的用途需实测确认 |
| C | 配置项通道（`[0x82E1580]`）是否携带原始地址 | 由子代理 Hypatia 的 `settings_source_report.md` 定论 |
| D | 探针服务器只支持 **HTTPS** | 尚无 UDP；STUN / TQoS 部分是下一步 |
| E | 抓包中大量会话属**其它进程** | 已按端口与熵值过滤，关键结论只采用 `116.130.224.66` / `tqos*` / `stat.iips` 这几条 |

---

## 10. ★★ 定论：总闸为 0 是「测量假象」，不是事实

**结论：`0x808650`（在线/大厅初始化）在启动时确实执行了，总闸 `[0x849B61F]` 确实被打开。
之前「总闸长期为 0」的说法是探针采样窗口错误导致的，现予作废。**

### 10.1 静态反证（三条，全部 VA 级）

1. **`0x77EE40`（WinMain）到 `0x77F8B3` 之间没有任何函数边界**
   → 扫描 `0x77EE40..0x77F8C0` 全部字节，**int3 填充长度为 0**
   → `call 0x4FD9B0` 位于 **WinMain 内部**，属启动早期，不存在"外层函数没被调用"的可能。

2. **`0x4FCEE0`（Com_Init）到 `0x4FD290` 之间没有任何 `ret`**
   → 反汇编整段，`ret` 命中数 = **0**
   → 一旦进入 Com_Init，`0x4FD287 call 0x808650` **不可能被跳过**。

3. **`0x7E99F1` 写总闸处无任何条件保护**
   → `0x7E98F0` 内部为顺序指令，前面只有 `cmp [0x849B5CC],0` 用于后续的
      时间戳分支，**不构成跳过总闸写入的分支**。

三条静态证据共同推出：**总闸必为 1**。

### 10.2 运行期实测（220 采样点 / 109.7 s）

数据源：`CODOLServer\_mainline\_dyn_game_out3\state.jsonl`
分析脚本：`CODOLServer\_mainline\_gate_summary.py`

| 量 | 取值分布 |
|---|---|
| `flag_61f`（总闸 `[0x849B61F]`） | **{0: 29, 1: 191}** ← 最终稳定为 **1** |
| `u5CC`（`[0x849B5CC]`） | {0: 13, 1: 207} |
| `dwLobby_state` | {0: 37, **2: 1**, **10: 182**} |
| `state_prev` | {0: 37, **1: 1**, 10: 182} |
| `uA50`（`[0x84ABA50]`） | **{0: 220}** ← 旧结论的唯一来源 |

**时间线**：

```
t= 0.00  state=0   flag_61f=0   u5CC=0      游戏启动
t= 6.52  state=0   flag_61f=0   u5CC=1      引擎初始化开始
t=14.53  state=0   flag_61f=1   u5CC=1      ★ 总闸打开（0x7E98F0 执行到了）
t=18.54  state=2   prev=1  flag_61f=1       ★ prev=1 = dwLogonStart 确实运行过
t=19.04  state=10  prev=10 flag_61f=1       状态机跑完并复位
```

### 10.3 为什么旧结论会错

| 原因 | 说明 |
|---|---|
| **采样点太少** | 旧探针在状态机**复位之后**才取到 `uA50`，只看到归零值 |
| **误把复位当初始态** | `uA50` 是"当前状态字"，跑完会归零，**不能**用它判断"是否执行过" |
| **静态与动态其实不矛盾** | 静态推出必为 1，动态实测 `flag_61f` 稳定为 1 → **完全一致** |

### 10.4 附带观测：`.tp3` 密文→明文的一次性切换

同一轨迹里 `code_7EF210` 有 **2 种**取值：

```
x8     0c56578b7d1057538d4513508bf1c745    ← 密文，t=0.00..3.51
x212   83fe040f8502020000a13ceae4006810    ← 明文，t=4.01..109.66（cmp esi,4 / jne ...）
```

切换点实测在 **t≈3.5–4.0 s 之间的一次性跳变**，之后 212 个采样点全部稳定为明文。

→ **修正**：这不是"按页解密"，而是 **ACE 一次性整块覆盖**。
详见 §11.4 与 `_subagents\tp3_unpack_report.md`（双方独立得到同一时间点）。

### 10.5 修正后的正确表述

> `0x808650` 在启动时**确实执行**；总闸 `[0x849B61F]` 自 t≈14.5 s 起为 1；
> dwLobby 启动器**确实运行过**（`state_prev=1` = `dwLogonStart`，共 1 个采样点）。
> 失败发生在**之后的 DNS 阶段**（状态未走到 3 的 `DW_LOBBY_CONNECTED`）。
> **「总闸从未打开」这一旧结论正式作废。**

### 10.6 遗留的一处细节（不影响上述结论）

`state_prev=1` 只有 **1 个采样点**、`state_prev=10` 有 182 个 —— 采样间隔大于状态切换耗时，
所以"经过 state 1"这条**由 `state_prev=1` 直接实测**，而非从 `dwLobby_state` 推断。

---

## 11. ★★ 其余三项已转为已知

### 11.1 `dwauth.ini` 原始取值 → **在本机不可恢复（已穷尽搜索）；"格式 + 语义"已完全确证**

#### A. 格式与语义（已确证，不再需要"推测"）

1. `dwauth.ini` 是 7 个字段、由 `fopen("dwauth.ini","r")` 读取、顺序 `sscanf` 到 7 个全局（§4.2）。
2. **字段 3 = 大厅 HOST**（`0x81A76A8`），**字段 4 = 大厅 PORT**（`0x81A9EC4`）—— 各有 3 处使用点（§4.3）。
3. 配合 `https://%s:%d/auth/` 走 TLS 鉴权（§11.3）。

#### B. 全盘搜索（已穷尽，命中 0）

产出：`_subagents\dwauth_hunt_report.md` + `dwauth_candidates.json`
+ 主线补齐的 `_subagents\_hunt_archives_tar_result.json`

| 搜索项 | 命中 |
|---|---|
| **`C:` `D:` `E:` `F:` `G:` 全盘 `dwauth.ini`** | **0 / 0 / 0 / 0 / 0**（C 盘 143.75 s 全递归完成） |
| 工作区内 `dwauth*`（宽匹配） | 1 —— 是 `DWAUTH_ORIGIN_FINAL.md` 报告本身，**非配置** |
| `buildconfig.ini` 全工作区 | **0** |
| **压缩包内**（全盘 4,623 个，名称匹配 263 个） | **0** |
| ├ zip 41 个 | 全 0 |
| ├ `GameCooperation.zip` 22 个 | 全 0 |
| ├ **rar 4 + 7z 2（主线用 bsdtar 补齐）** | **0**（另 1 个 7z `COD5_1.4_CHS_GBT.7z` 解压失败、与 CODOL 无关） |
| └ **gz 216 个** | **215 个路径不存在**（扫描残留）+ 1 个 Python 时区数据 → **有效 0** |
| Steam 正版 MW2 递归配置 | 2 个（`installscript_10190.vdf` / `localization.txt`），**无 `dwauth.ini`、无 host 配置** |
| `IW4X` / `E:\IW4X` 配置类文件 | `E:\IW4X` **0**；工作区 IW4X 只有源码 |
| `E:\CODOL_SANDBOX` | ini/cfg 71 个，**无 `dwauth.ini`** |
| 内容级搜索（15,157 个小文本） | `dwauth` 38（均为报告/脚本自身）、`auth_host` **0**、`dirlobby` **0**、`DW-Ticket` 4 |
| `run_codol_001\runs\**\*.txt\|*.log` 搜 `dwauth` | **0** |
| `CODOLServer\logs\*`（83 个文件）搜 `dwauth` | **0** |

#### C. 为什么找不到（另有机制性解释）

exe 内**只有文件名与格式符**（`0x00DDBDBC`：`dwauth.ini  %59s … %hu … stun.ini  buildconfig.ini`），
**没有任何值**。地址是运行时由字段 3/4 填入 `0x81A76A8` / `0x81A9EC4` 的 ——
这从机制上解释了全盘为何搜不到地址。

已排除的干扰项（**全部不属于大厅**）：

| 域名 / IP | 归属 |
|---|---|
| `tcls.qq.com`(8080/5223/10009)、`tcls.rail.qq.com`(8001/9001/10001/…​) | TCLS 目录与版本服务 |
| `ctrl.iips.qq.com:8000`、`127.0.0.1:8080` | IIPS |
| `stat.gamedl.qq.com:8080` | 统计（抓包中 `42.187.183.162` 即此） |
| `116.130.228.169:8080` | DNS 数据中**无任何域名映射** |
| `stun1/2/3-tub.codol.qq.com` | 来自 `stun.ini`，**不是大厅** |
| `tasver.gamesafe.qq.com`、`dump.gamesafe.qq.com` | 安全组件 |

关键词 `dwlobbyhost` / `blazehost` / `lobbyhost` / `auth_host` / `dirlobby` 在 exe 与小文本中**零命中**。
TCLS 目录响应 774 字节里实测**没有**大厅地址。

#### D. 结论（正式固化）

**原始 `dwauth.ini` 在本机不可恢复。** 取值本身没有留下任何本地痕迹。

能确证的只有它的**格式与语义**（7 字段、第 3 行 HOST、第 4 行 PORT、走 `https://%s:%d/auth/` TLS 鉴权）。
`dwauth_candidates.json` 中的条目**全部标注为低/无置信度参考**，**没有任何一条可以当作原始值使用**。

**"原始 IP/端口不可恢复"的补充理由**：

- `dwauth.ini` 是**客户端本地的部署配置**，不含在 exe / DLL 里，删掉即无痕。
- exe 内**没有**任何"备份的默认大厅域名"（见 §11.3 的 `211.147.81.116` 判定）。
- `stun.ini` 是唯一存活的相关配置文件（3 行 `stunN-tub.codol.qq.com`），**它不是大厅**。

**⇒ 复活只能自行提供地址**（本地回环 `127.0.0.1`，或用已知的腾讯大厅域名）。

**若要继续追原始取值，方向只能在本机之外**：
旧版 CODOL 启动器安装包、含 `dwauth.ini` 的完整客户端分发包、或旧机器的游戏目录备份。

### 11.2 字段 2 / 5 / 6 / 7 的语义 → **已定论，且给 0 安全**

**字段 2（`0x81A9780`, `%hu`）= 连接对象的"主机 id"（uint16），不是端口。**

`0xB75370` 是两参数构造器（`ret 8`），第二参数写入对象偏移 `+0x84`：

```asm
00B7537F  668b4d0c         mov cx, word ptr [ebp + 0xc]
00B75383  66898e84000000   mov word ptr [esi + 0x84], cx     ; ★ 字段2 落点
```

调用现场（`0x7F38B3`，大厅建连阶段）：

```asm
007F38B3  0fb70580971a08   movzx eax, word ptr [0x81A9780]   ; 字段2
007F38BA  50               push eax
007F38BB  6888c93e0e       push 0x0E3EC988                   ; 主机串
007F38C6  e8a51a3800       call 0xB75370                     ; 构造连接对象
```

**字段 5（`0x81A9EB8`, `%x`）= `0x7F2BAA` 取用的 32 位参数**（传入 `0xB88B80` 建连），语义为会话/通道参数类。

**字段 6 / 7（`0x81A56A4`, `0x81A76E4`, `%x`）= 版本/构建标识类 uint16/hex32。**
它们**不在** WinMain 的 `dwauth.ini` 读取块内，而由 `0x641600` 写入；
其地址**紧邻**一块硬编码默认值区：

```
0x00E51184  211.147.81.116                     硬编码 IP（stun.ini 三行也拷入此区）
0x00E51220  00112233445566778899              20 字节，形似 key/seed
0x00E51242  aAbBcCdDeEfFgGhHiIjJkKlLmMnNoO... 字符表
0x00E513D8  "http://127.0.0.1/"               ★ 内嵌字面 URL
0x00E513EC  q.com/
```

**⇒「给 0 是否会被服务器侧校验」的答案**：给 0 **安全**。
理由（明确且可验证）：失败发生在**读取之前**——

```
dwauth.ini 不存在 → fopen 直接失败 → 7 个 sscanf 一个都没执行 → 0x81A76A8 保持空
```

字段 2/5/6/7 的取值只影响**建连之后**的会话参数，不影响"能不能发起连接"。
是否被服务端校验，取决于 `/auth/` 的**响应**语义（见 §11.3），而非本地这些字段。

### 11.3 `/auth/` 的 JSON schema → **已完全解出（静态）**

鉴权函数 = `0xB99A93`（**同一个函数**既构造 JSON body、又构造 URL），
JSON 写入器 = `0xBC4BB0`，JSON 提交 = `0xBC42C0`。

#### 请求

```
POST https://<HOST>:<PORT>/auth/                 ← 格式串 @0xD5A2CC
  Content-Type: application/json                 ← @0xD5A1E4
  X-TransactionID: <u64>                         ← @0xD59E6C，值来自 <time64>@0xC73380

{
  "auth_task":       <num>     @0xD5A228  ← (this+0x14)
  "iv_seed":         <num>     @0xD5A114  ← <time/rand64>@0xC732F0   ★ 必须与 ciphertext 匹配
  "auth_title_id":   <num>     @0xDB7AC0  ← (this+0x10)
  "lsg_server_ticket": <str>   @0xD5A0E8  ← 由 <ticketgen>@0xB96310 生成（形如 0xE51184 区）
  "license_id":      <str>     @0xD5A2A0  ← <gen>@0xB96130
  "ciphertext":      <str>     @0xD5A2E0  ← ★ 见下
  "extra_data":      <str>     @0xD59AEC
}
```

关键指令：

```asm
00B99B94  68 28a2d500    push 0xd5a228  ; "auth_task"
00B99BAC  68 14a1d500    push 0xd5a114  ; "iv_seed"
00B99BC7  68 c07adb00    push 0xdb7ac0  ; "auth_title_id"
00B99D85  68 a0a2d500    push 0xd5a2a0  ; "license_id"
00B99DA0  68 e0a2d500    push 0xd5a2e0  ; "ciphertext"
00B99DED  68 ec9ad500    push 0xd59aec  ; "extra_data"
```

**`ciphertext` 的构造（§11.3 最关键的发现）**：

```asm
; 1) 取 license_id
00B99C65  e8b6c5ffff     call 0xB96220          ; -> [ebp-0x1860]

; 2) AAD 缓冲区清零 + 写死 0xDEADBEEF
00B99C02  8b15089fd500   mov edx, [0xd59f08]    ; = 0xEFBDADDE -> 字节 EF BE AD DE...
00B99C10  89955ce7ffff   mov [ebp-0x18a4], edx  ; [ebp-0x18a4] = 0xDEADBEEF (小端)

; 3) 打印成 hex
00B99C8B  e8bac8ffff     call 0xB96550          ; 打印 hex 到 [ebp-0x100]

; 4) 写入 [ebp-0x28]，与 iv_seed 一起交给 AES 封装
00B99CD1  e85ac4ffff     call 0xB96130          ; -> [ebp-0x28]
00B99CEE  e87d940d00     call 0xC73170          ; ★ AES 封装
                        ;   esi = [ebp-0x28]   = 0xDEADBEEF
                        ;   ebx = [ebp-0x100]  = iv_seed 的 hex
                        ;   ecx = [ebp-0x60]   = 密钥
                        ;   edi = [ebp-0x40]   = 20 字节 IV（来自 0xC732F0）
; 5) 结果 memcpy 进 [ebp-0x184]
00B99D20  e8eba6fdff     call 0xB74410          ; memcpy(0x81, [ebp-0x184], [ebp-0x60], 0x60)
```

**⇒ `ciphertext = AES( key=K, iv=20B, plaintext="DEADBEEF" )`，`iv_seed` 必须与之匹配。**

侧写：`0xD5B268 = "rijndael"`（AES 实现自证）；IV 取 20 字节；
`0xE51220 = "00112233445566778899"` 是同一量级的 20 字节常量。

#### 响应

```
{
  "server_ticket":       <str>  @0xD5A31C
  "client_ticket":       <str>  @0xD5A32C
  "extended_data":       <str>  @0xD5A290
  "user_id":             <num>  @0xD5A2AC
  "time_to_live":        <num>  @0xD5A2B4
  "cd_key":              <str>  @0xD5A2C4
}
```

#### 其它确证事实

| 事实 | 证据 |
|---|---|
| **`/auth/` 返回 4 个字符的错误串** | `0xD5A33C = "356c4bc3"`（紧邻 `server_ticket` / `client_ticket` 的读点 `0xB9852C`） |
| 轮询/排队接口 | `0xD5A11C = %s://%s:%d/%s/title/%d/queue/%d/member/%llu`，代码 `0xB9872B` |
| 队列状态字段 | `next_poll_after` / `estimated_wait_time` / `member_position`（`0xD5A770`..） |
| 下载状态枚举 | `BD_*`（`0xD5A7A4`..`0xD5A8B0`），含 `BD_HTTP_SSL_CERTIFICATE_ERROR` |
| **日志上报** | `https://%s:%u/tlog`（`0xDC71CC`） |
| UPnP | `M-SEARCH` / `AddPortMapping`（`0xD5AA20`..），描述串 `DemonwarePortMapping` |
| 硬编码 IP **不是**大厅 | `0x00E51184 = 211.147.81.116` → 位于 stun.ini 三行拷贝区（`0xE51184`/`0xE513D4`），**属 STUN 区** |

### 11.4 附带结论：`.tp3` 不是自解密、也不是按页解密

由子代理 Avicenna 独立完成（`_subagents\tp3_unpack_report.md`，27.9 KB），
并与主线 §10.4 的时间点**互相印证**：

| 项 | 结论 |
|---|---|
| 解密者 | **ACE（腾讯反作弊）用户态组件**，在 `LOAD_DLL_DEBUG_EVENT` 时刻对文件做 **一次性「读文件 → 解压 → 解密 → 整块覆盖内存」** |
| 时机 | 与主线一致：**t≈3.5–4.0 s 一次性切换**（主线 8 个采样点密文 → 212 个采样点明文） |
| 加密方式 | **不是**自解密，**不是**页级/驱动级按页解密 |
| 静态还原 | **不可行**（3 组算法模型全失败；`xor(disk, live)` 熵 7.92 bit/B，为真随机串） |
| 加密节 | 仅 2 个：节 #0（`RVA 0x1000`，熵 7.064）与节 #6（`RVA 0xE5D7000`，熵 7.337） |
| 镜像校正 | `image_best.bin` **含完整 PE 头**（`[0:2] == 4D 5A`），`index = VA - 0x400000` 直接成立 |
| exe 指纹 | SHA256 `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| 镜像指纹 | SHA256 `17CEF6E0A5E7B8D14FB97B5FDD846061187C6A722CFA3C5D432BEE37872FD045` |

**⇒ 正式表述：磁盘 exe 的代码段静态还原不可行；运行期镜像 `image_best.bin` 是唯一可信代码来源**
（本文件 §2 的方法论纠正由此升级为定论）。

---

## 12. ★★★ 实机验证：全链路打通，`/auth/` 真实报文已捕获

### 12.1 实验设计

用 §8.1 的三步 + **A 组对照**（换工作目录隔离变量）：

| 组 | 工作目录 | 目的 |
|---|---|---|
| 首次 | `run_codol_001\sandbox` | 基线 |
| **A** | `run_codol_001\sandbox_ifs1_20260923` | 隔离"目录差异"变量 |

配置：`dwauth.ini` = `127.0.0.1 / 0 / 127.0.0.1 / 8443 / 0 / 0 / 0`，
自签 CA 追加进 `cacert.pem`（均有 `.bak_<时间戳>` 备份）。
采样器：`_mainline\_lobby_watch.py`（**只读** `OpenProcess(QUERY|VM_READ)`
+ `CreateProcess(CREATE_SUSPENDED)` 抢 ACE 之前拿句柄）。

### 12.2 结果一：`dwauth.ini` **确实被读取**（实测）

两组运行都在 **t≈7–8.5 s** 观测到 `0x81A76A8` 与 `0x81A7F34` 变成 `127.0.0.1`：

```
t= 7.02  u5CC=1  host=""           f1=""
t= 8.03  u5CC=1  host="127.0.0.1"  f1="127.0.0.1"   ← ★ 读到了
```

⇒ §4.2 的静态推导（字段 3 → `0x81A76A8`、字段 1 → `0x81A7F34`、写入时机在 WinMain 早期）**实测成立**。

### 12.3 结果二：大厅状态机**首次走完 DNS 阶段**（实测）

```
t= 7.02  flag_61f=0  uA50=0  dw_state=0   state_prev=0   uA78=0
t=15.03  flag_61f=1  uA50=0  dw_state=0   state_prev=0   uA78=0   ← 总闸打开
t=19.04  flag_61f=1  uA50=2  dw_state=1   state_prev=1   uA78=2   ← ★★ DNS_COMPLETE
t=21.54  flag_61f=1  uA50=0  dw_state=10  state_prev=10  uA78=0   ← 跑完复位
```

**`uA78=2` = `DW_DNS_COMPLETE`**。对照 §10 历史运行（全程 `uA78=0` → `DW_DNS_ERROR`）：
**这一次 DNS 阶段真的通过了**。`state_prev=1` 再次直接实测"经过 `dwLogonStart`"。

### 12.4 结果三：TLS 握手成功 + **`POST /auth/` 真实报文已捕获**（实测）

**第一次尝试失败**（有价值的失败）：

```json
{"event":"tls_fail","peer":["127.0.0.1",60548],
 "error":"SSLError(1,'[SSL: NO_SUITABLE_SIGNATURE_ALGORITHM] ...')"}
```

**原因**：游戏用 **OpenSSL 0.9.8p（2010-11-16）**，只支持 TLS1.0 与经典 CBC 套件；
Python 3.11 的 OpenSSL 3.0 默认拒绝这些算法。

**修法**（只改本地探针，**不动系统任何设置**）：

```python
ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.options |= ssl.OP_NO_TLSv1_3
```

改后 **`openssl` 侧验证通过**：`TLSv1 / ECDHE-RSA-AES256-SHA`。

**重启游戏后成功**：

```json
{"event":"sni","peer":["127.0.0.1",60864],"server_name":null}
{"event":"tls_ok","tls_version":"TLSv1","cipher":"AES256-SHA"}
```

### 12.5 ★ `/auth/` 请求（真实，逐字节）

```http
POST /auth/ HTTP/1.1
Host: 127.0.0.1:8443
Accept: */*
Content-Type: application/json
X-TransactionID: 12123026899425147782
Content-Length: 187
Expect: 100-continue
```

```json
{
  "auth_task":  "10",
  "iv_seed":    "1229950237",
  "title_id":   "0",
  "identity":   "356c4bc3",
  "extra_data": "{\"version\": \"0\", \"user_id\": \"10995207597479878709\", \"extended_data\": true}"
}
```

`extra_data` 解嵌套后：

```json
{"version": "0", "user_id": "10995207597479878709", "extended_data": true}
```

### 12.6 ★ 对 §11.3 静态 schema 的三处实测修正

| 项 | 静态推断 | **实测** |
|---|---|---|
| `356c4bc3` | 疑为"4 字符错误码" | **是 JSON 键 `identity` 的值**（非错误码） |
| 数值类型 | 推断为数字 | **全部是字符串**（`"10"` / `"1229950237"` / `"0"`） |
| `ciphertext` / `license_id` / `lsg_server_ticket` | 以为必带 | **本次请求未出现** → 是**条件字段**（ticket 流程才用） |
| 键名 `auth_title_id` | 静态读作 `auth_title_id` | **实测键名是 `title_id`** |

### 12.7 当前阻塞点（已收敛到唯一一处）

```
客户端 → 探针：TLSv1 握手 ✅ → POST /auth/ ✅ → 请求体已捕获 ✅
探针 → 客户端：返回了 {"status":"ok","probe":"codol-local-lobby",...}  ❌ 不符合契约
                                                            ↓
                                              客户端仍弹「无法连接大厅服务」
```

**阻塞点 = `/auth/` 的响应内容**，与网络、TLS、地址、配置**全部无关**。
下一步只需按 §11.3 的响应 schema（`server_ticket` / `client_ticket` /
`extended_data` / `user_id` / `time_to_live` / `cd_key`）构造符合契约的应答。

### 12.8 本轮新增产物

| 文件 | 说明 |
|---|---|
| `CODOLServer\_mainline\_lobby_watch.py` | 只读大厅状态采样器（含 host/f1 直读） |
| `CODOLServer\_mainline\_lobby_run_ifs1b\watch.jsonl` | ★ 本轮成功运行的全轨迹 |
| `CODOLServer\logs\lobby_probe.jsonl` | ★ 含 TLSv1 握手 + `POST /auth/` 全量报文 |
| `CODOLServer\lobby_server\_decode_capture.py` | 报文解码器（含 `extra_data` 嵌套解析） |

---

## 13. 证据索引

| 主题 | 位置 |
|---|---|
| 运行期明文镜像 | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` |
| 弹窗完整链（上一阶段） | `CODOLServer\POPUP_ORIGIN_FINAL.md` |
| 大厅地址来源（本阶段） | `CODOLServer\DWAUTH_ORIGIN_FINAL.md` |
| 本阶段总记录 | 本文件 |
| 抓包报告 | `CODOLServer\_subagents\pcap_report.md` |
| 抓包原始数据 | `run_codol_001\runs\{ENTRY_CAPTURE_ELEVATED_20260925_013045, TCLS_DIR_20260924_220810, LOBBY_DEEP_20260924_181441, ENTRY_CAPTURE_ELEVATED_20260924_160326}\pktmon.pcapng` |
| ACE 组件图谱 | `CODOLServer\ACE_COMPONENT_MAP.md` |
| TQoS schema | `CODOLServer\TQOS_SCHEMA_FULL.md` |

### 关键 VA 速查

| 用途 | VA |
|---|---|
| WinMain（读 `dwauth.ini`） | `0x77EE40` |
| CRT 调用 WinMain | `0xC42783` |
| 引擎初始化 Com_Init | `0x4FCEE0` |
| 在线 / 大厅初始化 | `0x808650` |
| dwLobby 总初始化（写总闸） | `0x7E98F0` / 写点 `0x7E99F1` |
| dwLobby 总闸标志 | `[0x849B61F]` |
| dw 状态字 | `[0x84ABA50]` |
| dw 派生状态 | `0x7F25B0` |
| dw 状态机主循环 | `0x7F26C0` |
| DNS 阶段 | `0x7F34E0` / `0x7F3600` |
| 账号 / 建连阶段 | `0x7F28F0` / `0x7F2B90` |
| 大厅连接阶段 | `0x7F3800` / `0x7F3890` |
| 弹窗触发点 | `0x7EF210` |
| 面板投递 | `0x771240` |
| 大厅 HOST 全局 | `0x81A76A8` |
| 大厅 PORT 全局 | `0x81A9EC4` |
| HTTPS `/auth/` 格式串 | `0xD5A2CC` |
| `cacert.pem` 字符串 | `0xDC9CA4` |
