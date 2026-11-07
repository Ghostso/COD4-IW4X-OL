# CODOL 客户端绕过关服 · 现状固化（2026-10-02）

工作目录：`e:\codol tae`
对应游戏：`E:\使命召唤OL\使命召唤OL\codoMP_client_shipRetail.exe`（基址 0x400000，镜像大小 0xE659000）

---

## 0. 一句话现状

**我们让客户端成功走通了 HTTPS `/auth/`（这是此前从未做到过的），但客户端随后并不走我们分析的那段 exe 应答处理代码，也从不连接大厅端口 8446 —— 因此"无法连接大厅服务"仍未解除。**

---

## 1. 已实测通过的（有日志为证）

| 项 | 证据 |
|---|---|
| 游戏向 `127.0.0.1:8443` 发起 **TLS 1.0 + AES256-SHA**，我们能正确应答 | `auth8443.log`: `=== TLS 就绪 ... 版本=TLSv1 套件=AES256-SHA ===` |
| 游戏发出 **`POST /auth/`**（388–389 字节 JSON） | `auth8443.log` 有 `auth_task/iv_seed/title_id/identity/extra_data` 全文 |
| 我们回 **200 + 契约 JSON** | `-> 200 task=32->57`，含 `code=700 / iv_seed=0 / server_ticket / lsg_server_ticket / client_ticket`（均 Base64 解码 128B，头 4 字节 `DE AD BD EF`） |
| **TLS close-notify 正常发出** | `TLS close-notify 已发`（http.sys 做不到，见 §3） |
| 证书链通过严格校验 | 用 `_ca.pem` 作锚，OpenSSL 严格模式校验 8443/443 均 OK |
| 游戏确实连 `127.0.0.1:443` | `[net]` 里出现 `127.0.0.1:443 [ESTABLISHED]` |

---

## 2. 关键结论（改变了整体方向）

1. **客户端从不执行 exe 里那段"应答处理"代码**：
   用 nt8 的 `--direct`（会等解壳再挂）成功挂上后，实测
   ```
   === @0xBA9980 被调用 0 次 ===     # 票据逐位解析器
   === @0xBC3E10 被调用 0 次 ===     # JSON 取整数字段
   ```
   → 我们此前十几轮基于 `0xB9A470 / 0xB9A59B / 0xB9A7C7 / 0xBA9980` 的契约分析（`code==700`、`client_ticket` 长度 128、票据逐位格式…）**对这条 `/auth/` 请求并不适用**。

2. **那条 8443 的 TLS 连接不走 ws2_32 常规入口**：
   `connect` 仅 14 次（无 8443）、`WSAConnect` 0 次、winhttp 钩子只在 ACE 上报 `down.qq.com` 时命中过。
   → `/auth/` 及其应答是由**另一个网络栈/模块**处理（很可能是 TASLogin/TCLS SDK，或走 `ConnectEx`/overlapped 自有实现）。

3. **游戏从不连接 8446**（`lobby_srv.log` 里一条 `=== 大厅连接建立 ===` 都没有；`[net]` 也无 SYN_SENT 到其它可疑地址）。

4. 已排除的变量（都实测过仍报同样错误）：
   - 大厅主机/端口全局写入（`--no-poke`）
   - TAS 镜像注入（`--no-tas`）
   - 额外 hook（`connect/sendto/WinHttp*`，`--apis` 减到与 nt8 相同）
   - 我们的假服务是否在跑（`--no-services`）

---

## 3. 期间修掉的 Harness 缺陷（这些是真 bug，值得留存）

1. **`run_all.py` 里 `port_listening` 有两个定义**，后面的 socket 版覆盖了安全的版本 → 每轮 run_all 主动 `connect` 一次 8446，被 `lobby_server` 当成"真大厅连接"接收。**此前所有 `=== 大厅连接建立 ===` 都是我们自己的探测**（`[who]` 证明来访者是 `python.exe`）。现改为用 `netstat` 读 LISTENING。

2. **`powershell -File` 在 `DETACHED_PROCESS(0x08)` 下会瞬间 rc=0 退出、脚本一行都不执行** → 这就是 `auth8443.log` 长期不存在的根因。改用 `CREATE_NO_WINDOW(0x08000000)`。

3. **443 曾被 `lobby_server` 当"原始抓包"黑洞占用**，而实测游戏在 443 上 ClientHello 的 SNI 是 **`intldlgs.qq.com`** → 游戏拿不到应答。现 443 交给 `fake_ied_https.ps1`。

4. **http.sys 不发 TLS close-notify**（手册 §3.2 把它列为契约的一部分）。改用自制 `fake_auth_tls.py`（Python + ssl）后 close-notify 正常。

5. **证书不可校验**：原自签证书是"叶子当根用"且 `keyUsage` 缺 `keyCertSign` → OpenSSL 严格模式报 `unable to get local issuer certificate`。改为**两级链**（`CODOL-LOCAL-CA` + leaf），修好后游戏才第一次真的把请求发出来。

---

## 4. 一键运行

```powershell
cd "e:\codol tae"
python .\run_all.py --secs 150 --out n10xx.txt          # 起全套服务 + nt10
python .\run_all.py --secs 120 --out n8x.txt --driver nt8o   # 改用原始 nt8 的注入器
```

常用隔离/诊断开关：`--no-poke` `--no-tas` `--no-services` `--raw8443`

产物：
- `auth8443.log`（8443 `/auth/` 全量请求/应答）
- `lobby_srv.log`（8446 大厅 + 80/8081 原始抓包）
- `iedsafe_req.log`（443）
- `n10xx.txt`（注入/观测日志）
- `<out>_exe_b8b9.bin` / `_exe_ba6.bin` / `_exe_d5a.bin`（运行时解壳后的真码，反汇编用）

---

## 5. 文件清单

各文件 SHA256 见 `_frozen_manifest.txt`（发现被改动可直接比对）。

- 驱动/注入：`nt10.py`、`nt8o.py`（= 原始 nt8 副本）、`ref_nt8\nt8.py`（原始，勿改）
- 编排：`run_all.py`
- 服务：`fake_auth_tls.py`(8443)、`fake_ied_https.ps1`(443)、`lobby_server.py`(8446 + 80/8081)
- 证书：`_ca.pem`(CA)、`_leaf2.cer`/`_rsa.txt`/`_leaf2.key`/`_leaf2_chain.pem`(8443 leaf)
- 规格：`lobby_spec.txt`=`127.0.0.1:8446:8443`、`tas_spec.txt`=`127.0.0.1:3074:CODOL-LOCAL`、`late_spec.txt`=`off`、`patch_spec.txt`=空
- 其它：`patch_crossshell.py`（死 IP → 127.0.0.1）、`setup_auth8443.ps1`

---

## 6. 注意事项（踩过的坑）

- **别再跑 `setup_auth8443.ps1`**：它会把 8443 绑回那张没有 `keyCertSign` 的旧证书，前功尽弃。
- `run_all.py` 的 `free_ports()` 按命令行匹配杀进程：**不要在命令行里出现 `nt10.py`/`lobby_server.py`/`fake_auth_tls` 等字面量**（会把自己所在的 shell 杀掉）。
- exe 的 `.tp3` 段**磁盘上是加密态（全 0）**，只有运行时才是真码；早期 dump 是 0、末轮才有内容 —— 判断时要看**文件**，别只看日志那行"非零 0"。
- nt10 的 `@mod:rva` 直挂会在 30s 内等 `55 8b ec`，晚解密的函数会等不到；**nt8 的 `--direct` 没有这个短板**，挂 exe 函数优先用 `--driver nt8o`。
- 每轮前建议清残留：`Get-Process python,codoMP_client_shipRetail,IIPSHostApp,TP3Helper -ErrorAction SilentlyContinue | Stop-Process -Force`

---

## 7. 需要向开发者索取的东西（方案 B 的具体清单）

1. **`lobby_response.json`** —— 手册 §3.2 点名的 `/auth/` 应答 `extra_data` 749 字节模板；
2. **一份真实捕获的 `/auth/` 应答体原文**（200 响应全文，含所有字段与头部）；
3. **手册 §3.3 的 HTTP 队列 PUT 实际收发**（`PUT /v1.0/title/<id>/queue/0/member/<id>` 的请求头/体与应答字节）；
4. **他的探针实现**：`lobby_plain_probe.py`（尤其 `serve_handshake` / `--lobby-handshake` 那部分）与观察器 `.cs`；
5. 他那份**能走通时的完整命令行**（`capture_elevated_network.ps1` 的实际参数）。

> 目标：拿到 1–3 后，可直接与我们现有的 `fake_auth_tls.py` 对齐；拿到 4–5 后，可比对我们的编排缺了什么。

---

## 8. 待办（拿到 B 的材料后）

- [ ] 用真实响应体替换 `fake_auth_tls.py::build_response`，验证客户端是否推进
- [ ] 若推进，落地 §3.3 的 queue PUT 契约
- [ ] 回头处理 8446 明文大厅的 `0x81/0x83/0x85`（`lobby_server.py` 已备好就绪标志与原始抓包）

---

# 9. 【2026-10-02 晚 · 已达成】成功进入大厅 —— 固化配方

> 依据：`E:\codol\dist\CODOL-Portable`（第三方**能进大厅**的实现，含完整源码
> `E:\codol\dist\launcher_src\CodolLocalLobbyServer.cs` + `CodolStateReader.cs` + 真实帧日志）。
> 结论：**已成功进入大厅**（用户确认）。`lobby_srv.log` 里 50 条任务全部解密、`HMAC BAD` 仅 1 次、
> 13 次数据下发；服务集合与三方 `lsg.log` 基本一致。

## 9.1 一键命令

```powershell
cd "e:\codol tae"
python .\run_all.py --secs 200 --out n10run.txt
```
（管理员 PowerShell。**TAS 默认已关**，见 9.3。看 `n10run.txt` / `lobby_srv.log` / `auth3074.log`。）

## 9.2 必须同时成立的 8 件事（缺一即失败）

| # | 项 | 正确做法 | 曾经的错法 |
|---|---|---|---|
| 1 | hosts | **只**加 `127.0.0.1 formal-zone-auth.codol.qq.com` + `127.0.0.2 formal-zone-lsg.codol.qq.com`；**绝不劫持** `down.qq.com` / `intldlgs.qq.com`（ACE/TP3 要连真实服务器拿配置和 DLL） | 把 `intldlgs.qq.com` 指到 127.0.0.1 并让 443 回 404 → 掐断 TP3 |
| 2 | `dwauth.ini` | 三行：`formal-zone-lsg.codol.qq.com 3074` / `formal-zone-auth.codol.qq.com 3074` / `0x03EA`（CRLF） | `127.0.0.1 / 0 / 127.0.0.1 / 443 / 0 0 0` |
| 3 | 端口 | **3074**：auth(TLS) 在 `127.0.0.1:3074`，lsg(明文) 在 `127.0.0.2:3074` | 8443 / 8446（客户端根本不去连） |
| 4 | 证书 | root CA（`ca=1&pathlength=0`）进 `LocalMachine\Root` + 追加进游戏 `cacert.pem`；leaf 的 **SAN 必须含** `localhost` + `formal-zone-auth.codol.qq.com` + `formal-zone-lsg.codol.qq.com` | 自签叶子当根用、无 `keyCertSign` |
| 5 | 4 个内存补丁 | 见 9.4 | 一个都没打 → 客户端校验全都不放行 |
| 6 | **TAS 不注入** | 默认关（`tas_off.flag`） | 注入 TAS → 客户端走 DSA 签名路径（`auth_task=32` + `codo_request` 签名块）→ 卡死 |
| 7 | 会话密钥 | nt10 按 `svc=[0x8269774] → sub=[svc+0x4F4]`（要求 `[sub+0x5E8]==3`）读 `aes_out/aes_in/hmac_out/hmac_in` 写 `secrets.txt`；lobby_server 读它解密 | 服务端进程自己读游戏内存（**会被拦**，连 MZ 都读成 0） |
| 8 | 数据下发 | `publisher_files/`（10 个 .info）、`player_profiles/{public,secure}.result`、`user_files/`；对象格式 `0x13 0x08 u32len data` | 一律回空对象 → `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` |

## 9.3 TAS 为什么必须关

打 TAS 镜像时客户端的 `/auth/` 请求是 `auth_task=32` + `codo_request`（1366-bit DSA 签名块）；
关掉后与三方完全一致：`auth_task=10` + `extra_data={"version":"0","user_id":"…","extended_data":true}`。
两者后续行为完全不同（前者永远连不上大厅）。`run_all.py` 已把"不注入"设为默认，要恢复用 `--tas`。

## 9.4 4 个兼容补丁（绝对 VA，`VirtualProtectEx` 后写，写完刷 icache）

| # | 位置 | 匹配字节 | 动作 |
|---|---|---|---|
| 1 | `0x00B9A78C-16` 起 40B 内 | `84 C0 (74\|75) B2 B0 01` | 把 `74`(JE) 改成 `75`(JNE)（实测改在 `0x00B9A78E`） |
| 2 | `0x00B9A7B0` 起 64B 内 | `84 C0 (75\|EB) 2A E8` | 把 `75`(JNE) 改成 `EB`(JMP)（实测 `0x00B9A7C5`） |
| 3 | 同上区 | `call` + `8D 8D 38 FD FF FF C7 85 68 FD FF FF` | 该 call 改成 `E9` 跳 `0x00B9A7F1`（实测 `0x00B9A7C7`） |
| 4 | `0x00BA3C1A` | `85 C0 75 44` | 在 `0x00BA3C1C` 写 `90 90`（NOP 掉 LSG 的 nonce 校验） |

> ⚠️ 十进制 `12205082` = **`0xBA3C1A`**（不是 `0xBA41DA`，我一开始换算错了，导致补丁 4 长期不生效）。
> 这些字节磁盘上是加密的，**必须运行时解壳后**才匹配得到 → 补丁线程循环重试直到模式出现。
> 另外：补丁 3 会把 `0xB9A7C7` 的 `E8` 改成 `E9`，于是**补丁 2 的模式此后匹配不到** → 必须
> 照三方 `patched[$i]` 的做法，**成功即 latch，不要每轮复查**（否则计数会从 4/4 掉成 2/4）。

## 9.5 大厅帧协议（`127.0.0.2:3074`，明文）

```
① 客户端先发 28B:  C8 00 00 00 | C8 00 00 00 | D2 00 00 00 | DC 00 00 00 | 00 00 08 00 | <8B nonce>
② 服务端回 0x81:  u32 22 | 00 | 81 | u32 0xDC | 8B 随机 | 8B(=hello[20:28])
③ 客户端发 0x82:  u32 len | AB | 82 | <...>            (stage1)
④ 服务端回 0x83:  u32 10 | 00 | 83 | <8B challenge>    (challenge 读客户端内存, [sub+0x5FC])
⑤ 之后 0x85 加密任务帧:
     u32 total | AB | 85 | u32 seq | iv[16] | cipher | hmac8[8]
     hmac8 = HMAC-SHA1(hmac_out, frame[:-8])[:8]
     plain = AES-128-CBC_decrypt(aes_out, iv, cipher)
           = u32 declared | 0x86 | service | 0x03 | task | payload(declared-3)
⑥ 服务端应答(同格式):
     plain = u32 len | 0x01 | TLV
     TLV  = tag10+u64 replyId | tag8+u32 status | tag3+u8 task | tag8+u32 对象数
            [若对象数>0: tag8+u32 对象数, 随后各对象原始字节]
     ★ 应答的 seq 要**回显请求的 seq**；replyId 用独立计数器(从 1 递增)
     另: 4 个 0x00 = keepalive
```
密钥链：`svc=[0x8269774]` → `sub=[svc+0x4F4]`；`aes_out=read([sub+0x604]+156,16)`、
`aes_in=read([sub+0x608]+156,16)`、`hmac_*=XOR还原(read(sub+0x60C,40))`。

## 9.6 新增/改动的文件

| 文件 | 作用 |
|---|---|
| `codol_crypto.py` | **零依赖**纯 Python AES-128-CBC + HMAC-SHA1 + 帧编解码（`python codol_crypto.py` 跑 FIPS-197 自测） |
| `make_local_ca.ps1` | 生成 root CA + 三域名 SAN 的 leaf（纯 ASCII，避免 PS 5.1 按 GBK 读中文路径） |
| `write_dwauth.py` | 按三方格式写 `dwauth.ini`（带备份 + 回读校验） |
| `lobby_server.py` | 握手 + 帧解密 + 按任务分派下发数据 |
| `nt10.py` | 4 个兼容补丁线程 + 会话密钥快照线程 |
| `run_all.py` | 编排：清占用 → hosts → dwauth/证书 → 两个 3074 服务 → nt10 |
| `publisher_files/` `player_profiles/` `user_files/` | 从三方实现取来的数据（大小与其日志逐字节一致） |

## 9.7 已知遗留

- 50 条任务里出现过 **1 次 `HMAC BAD`**（疑似换密钥后的第一帧），无害但可查；
- `80/*`（商城）多数仍回空对象；显示设置 / 玩家档案编辑 / **战斗服务器(UDP 28960)** 未做
  （对应三方 `CodolLocalBattleServer.cs` / `DisplaySettingsForm` / `PlayerEditorForm`）。

---

# 10. 【2026-10-03】借鉴外国团队 ol-mod，补上 `21/5` 会话对象

> 素材：`E:\handoff2\`（另一团队的共享包）
> — `Understand Project Repository.md`（113 KB 技术报告）+ `ol-mod-olfinal.zip`（完整 C#/C++ 私服重写，GPL-3.0）
> — `Kernel33.dll`（客户端 TP 中和 + 自定义 `.ff` 注入器）
> 对方进度**远超我们**（已能多人对战 + 僵尸 Factory + 完整比赛结算），但**协议底层两边完全一致**。

## 10.1 两边互证的部分（可信度最高的结论）

| 层 | 结论 |
|---|---|
| `0x85` 加密封装 | **逐字节完全一致**：`u32 total | AB | 85 | u32 seq | iv[16] | cipher | hmac8[8]`；AES-128-CBC 无填充；`hmac8=HMAC-SHA1(key,frame[:-8])[:8]` |
| 应答明文 + TLV | **完全一致**：`u32 len | 01 | tag10+u64 replyId / tag8+u32 status / tag3+u8 task / tag8+u32 对象数`（对象数>0 时再写一次） |
| 客户端任务明文 | `u32 declared | 86 | service | 03 | task | payload` —— 相同 |
| 端口 | 都是 **3074**（对方的 3075/4000 只是单测 fixture） |
| 钱包对象 | `03 <type> 08 <u32 amount>` —— 与我们 `balance_object()` 一致 |
| 余额轮询 | 客户端一次轮询发**两个**请求：`Marketplace/130` 取第 1 个钱包、`93/1` 取第 2 个 —— 与我们的映射一致 |

## 10.2 本轮新增：`21/5` findSessions 会话对象

**实测**：我们客户端发的 `21/5` payload = `08 01 00 00 00 …` → **queryKind = 1 = FIND_SERVERS**，
且带 `07 AB AD 92 D6`，与 session 记录里的 query criterion 逐字段对应。

**实现**（`codol_crypto.py` + `lobby_server.py`）：
- `Buf` —— Demonware 类型化写入器，**含 `i32`(0x07)**。对方源码明确标注：matchmaking 的
  query-criterion 字段是 **SIGNED**，写成 `u32`(0x08) 会被客户端逐值类型检查拒绝。
- `bd_common_addr()` —— 37B `bdCommonAddr`：`[ipv4 4B 大端][port 2B 小端] | [00 FF 00 FF 00 00]×4 | 同 6B | [01]`
- `build_session_record()` —— 完整 258B 对象（5 个前置字段 + 记录尾）
- `lobby_server.reply_objects()`：`21/5`、`21/16` → 返回 1 条 session；
  `queryKind==1` 回"权威服务器"（max 18 / current 0），其它回本地房间（current 1）

**★ 三条"错了就崩"的门槛**（对方实测注释，必须一起满足）：
1. `MatchMakingInfo + 70` 必须 `== 67`（贴不透明描述符会填成 37 → `sub_B95C50` 把 out 指针留 0
   → `sub_8071F0` 读 `*(0+0x10)` **访问违例**）。由"逐字段构造"而非贴原始描述符来保证；
2. `roomId` 必须是**非零十进制字符串**（`MatchController.as` 用 `_strtou64(room.id)` 与未设置的
   `last_kick_room_id` 比较，非数字串也解析成 0 → `0==0` → **每次加入都被判"被踢"**）。用 `(id & 0x7FFFFFFF) | 1`；
3. host uid **不能等于玩家自己的 CODOID**（否则客户端把"加入房间"发给自己并丢弃回包 → "房间无响应"）。用常量 `1000001`。

**自测**：`python codol_crypto.py` → `session 记录(258B): 长度=258 期望=258 OK`
（逐字节对齐对方导出的 FULL A 样本，含全部锚点）。

## 10.3 商城：确认"空应答"才是对的

对方源码注释写明（`MarketplaceService.cpp:307-338`）：**格式正确的空页**能让商店保持可浏览；
而客户端**反序列化不了**的应答会让**整个 marketplace 服务死掉**（STORE/INVENTORY 变灰 + 警告三角，
本次会话不恢复）。CODOL 的 SKU 记录**不是** MW19 的 `bdMarketplaceSku`（多一个 u8 和一个 u32），
照抄兄弟作品的字段序就会触发那次失败。

→ 所以我们维持回空对象是对的；本轮把 `80/32`（getBalanceLegacy）也接上，并把
`80/{70,107,119,154,173,174,203,230,232}` 显式归为"空应答"并记日志。

## 10.4 对方给的其它可直接用的线索（尚未落地）

| 线索 | 内容 |
|---|---|
| `0x83` 的 8B challenge | 对方**不需要读内存**：由 KDF 算出 `responseId`。我们目前读 `[sub+0x5FC]`（读不到就靠补丁 4） |
| **密钥派生** `deriveSessionKeys` | 根密钥 = 客户端 `0x82` 帧 `authInfoData[0..24]`；`transcript = hello[8:28] + ServerHeaderAck(26B) + clientAuth[:-8]`；`secret = HMAC-SHA1(key=transcriptHash, data=sessionKey)`；再 `expandKey(secret,"CLIENTCHAL",16)` / `expandKey(secret,"BDDATA",72)` → responseId/requestHmac/responseHmac/decrypt/encrypt。**⚠️ 已实装但输入端对不上，见 §10.6** |
| `auth_task` 应答 | 对方统一 `+1`；我们是映射表（`10→11` 一致，`32→57` 与 `+1` 冲突）—— 只有真走签名/TAS 路径才暴露 |
| 证书 | 对方明确：CODOL 旧校验器**拒绝 X.509 v3 / SHA-256**，必须 **v1 + RSA-SHA1**（对我们的 `make_local_ca.ps1` 有直接指导价值） |
| 控制帧 marker | 真机是 `0xAB`，我们用 `0x00`（客户端只认 offset 5 的操作码，容忍 offset 4）。建议改回 `0xAB` |
| `8/2` 语义分歧 | 对方说私密档案契约是**空应答**（回 800 或非空都致命）；我们回 32983B secure profile 且能进大厅 → **需复核** |
| `11/4` 房间 ready | `setRoomData`，含 16B 常量 `0C 00 00 00 02 02 00 00 00 08 00 00 00 80 08 00` |
| `6/14` booking | `mmstart ` 本地命令，token 的 FNV-1a 必须 `== 0xDEC30B2A` |

## 10.5 合规提醒

`ol-mod-olfinal.zip` 是 **GPL-3.0**。上面所有移植都是**按协议事实重写**（常量/字段序/门槛），
未复制其源码或资产；若后续要直接用其 `assets/backend/1004` 或工具，需遵守 GPL 并保留出处。
`Kernel33.dll` 会改 TenProtect 与游戏内存 —— 与我们的既有硬边界（不关/不规避 ACE、TP）冲突，**只看不用**。

## 10.6 `deriveSessionKeys` 落地结果：算法对，**输入端对不上**（如实记录）

按对方源码实现了完整 KDF 并接进 `lobby_server.py`，然后用**真实会话复盘**验证（工具：`kdf_probe.py`）。

### 已证实的（3 条）

1. **算法本身正确**：`codol_crypto.derive_session_keys` 逐字段复现对方的已知答案向量
   （`DemonwareTests.cpp:2455-2478`，sessionKey=`"Shippo fuute, mofu-mofu!"`，transcript=0..63）
   → `python codol_crypto.py` 打印 `deriveSessionKeys KAT : OK`。
   附带确认一个**文档写反的细节**：对方 `hmacSha1(data, key)` 的形参序是 (data, key)，
   故 `secret = HMAC(key=transcriptHash, data=sessionKey)`，与报告里的写法相反。
2. **`authInfo` 位布局正确**：`session_key_from_client_auth()` 从我们真实会话的 `0x82` 帧里
   解出 `deadbdef83a2c1e0ff1e3d5c7b9ab9d8f71635547392b1d0` —— **正是我方 `/auth/` 伪造票据的前 24 字节**
   （`DE AD BD EF` + `(k*31+7)&0xFF`，逐字节吻合）。所以"跳过 83 bit、LSB-first 读 128B"是对的。
3. **这两个 label 在我们 build 里确实存在**：运行时解壳段 `n10*_exe_d5a.bin` 里
   `BDDATA`@`0xD5A4E0`、`CLIENTCHAL`@`0xD5A4E8`（同区还有 `HMAC mismatch` / `HMAC calculation`
   / `X-Checksum` / `DW-Client-Ticket` 等），说明这套 KDF 就在客户端里。

### 没对上的（否定性结论，值得后人省一轮）

用**同一轮真实会话**（已用"我们发出的 `0x83` 尾部 8B == `secrets.txt` 的 challenge"证明是同轮）做判定：

```
字段             KDF 派生                              内存快照(真值)                          判定
decrypt        bfd75476fd3e80bdf9d4f6731875d4a3     5464f933362829a3314cc8ebd832b0a5      不一致
encrypt        612a19734c68409b5363dfc526be9ec8     b8a4247a0b7fb07ae982a64292bebb5f      不一致
request_hmac   427ab570420fa6f09c76ac882d55a116607f6d88  d132e8ac818ea017fa56c58ce646f18e9b7a4321  不一致
response_hmac  125536b47d4401c8c17906ac194afa3332a5d5f2  14701b45a1585c2a6f9c69139c6656342bf1a9d1  不一致
response_id    5b670ce0ce79b012                     da24fa02fb35d6f4                      不一致
```

穷举过（全部未命中）：
- **根密钥**：票据的全部 105 个 24B 窗口（含 `[0:24]`、`[97:121]`——对方自己的 `makeTicket` 把会话密钥放 97..120）
- **transcript**：12 种组合（`hello[0/8/4:28]`、`canon` vs 我方实发 `0x81`、`auth` 全帧 / `[:-8]` / `[6:]`、含/不含 len、空、单段…）
- **KDF 变体**：HMAC 参数序 ×2、label 序 ×2 → 合计 **5,040 组**（另一轮另试过 2,160 与 33,600 组）

→ **结论：ol-mod 的 `deriveSessionKeys` 配方在我们这个 build 上输入不同**（可能 transcript 里含
我们看不到的量，或根密钥并非票据切片，或另有一层 KDF）。

### 因此当前的处理（已写进代码，可安全共存）

- `lobby_server.py` 保留 KDF 分支，但**只在派生结果与内存快照完全一致时才采信**
  （`if sec0["aes_out"] == dk["decrypt"]: derived = dk`）—— 否则一律继续用 nt10 的内存快照，
  **不会**因为密钥猜错把已经跑通的大厅弄坏。
- 每轮日志都会打 `[kdf] sessionKey=… / aes_out=… / 与内存快照不一致`，一旦哪天对上会打
  `★ 与内存快照完全一致 —— 可以脱开 nt10 了!`。
- 复盘工具：`python kdf_probe.py --brute`（三段输出：同轮一致性 / sessionKey / KDF-vs-内存对照）。

**下一步建议**：去 `0xD5A4E0/E8` 的引用点做静态定位。已知同区有指向 `0xBA13A0` / `0xBA2A30` /
`0xBA3370` 的代码指针（`_exe_lobby.bin` 覆盖 0xBA2000 起），`0xBA13A0` 落在未 dump 的
0xBA13xx 区间 —— 建议补一段 `0xB9C000..0xBA2000` 的运行时 dump，再顺着引用找 KDF 入参的组装点。

## 10.7 补 dump 定位：工具已就位，**卡在僵尸进程（需重启）**

### 已完成的准备

1. **`nt10.py` 补了缺失的 dump 区间**：新增 `0xB9C000..0xBA2000` → `<out>_exe_b9c.bin`。
   起因：`0xD5A4DC` 那个槽里存着代码指针 `0xBA13A0`，而 `0xBA13A0` 恰好落在两个既有区间
   （`b8b9` = 0xB80000+0x1C000 止于 0xB9C000、`lobby` = 0xBA2000 起）**之间的空档**里。
2. **新增分析工具 `analyze_kdf_refs.py`**（依赖已装好的 capstone 5.0.7）：
   - 解开 `0xD5A4A0` 起的指针表：发现那里其实是 **vtable 区**——
     `0xD5A4DC = [0xBA13A0]`、`0xD5A4F4 = [0xBA2A30, 0xBA3370]`，
     且 `0xD5A4F4` 被 lobby 代码用 `mov dword [esi], 0xD5A4F4`（`0xBA238D` / `0xBA2846`）
     安装进对象 —— 说明 `0xBA2A30` 那一族是**某个类的虚函数**；
   - 全量搜"引用 d5a 段地址的立即数"，并对命中处/指定 VA 反汇编前后文。
3. **已用现有 dump 做完静态排查**：在 `b8b9` / `lobby` / `ba6` / `d5a` 四段里，
   **`BDDATA`(0xD5A4E0) 与 `CLIENTCHAL`(0xD5A4E8) 一个引用者都没有**
   → KDF 的调用点不在这些段里，极可能就在新补的 `0xB9C000..0xBA2000`。

### 为什么还没跑出 dump：20 个僵尸进程

```
Get-Process codoMP_client_shipRetail → 20 个(始于 10-01~10-02)
Stop-Process -Force  → 报成功但进程仍在
taskkill /F /PID   → ERROR: Access is denied
```
与既有记录一致：被驱动挂住后**只有重启能清**；它们占住单实例互斥，新实例会秒退，
所以 dump 出不来。

### 重启后只需两步

```powershell
cd "e:\codol tae"
python .\run_all.py --secs 200 --out n10dump.txt      # 管理员; 跑完即产生 *_exe_b9c.bin
python .\analyze_kdf_refs.py                          # 自动挑最新 dump 并反汇编引用点
```

`analyze_kdf_refs.py` 会直接把 `0xBA13A0` 所在函数反汇编出来 —— 目标是在里面认出
`expandKey(secret, "CLIENTCHAL", 16)` 的调用，从而确定 `secret` 的 20 字节到底怎么来
（那才是 §10.6 里对不上的根因）。

> 另注：`.tp3` 段在磁盘上不存储该区间（`VSize 0x8A689A > RawSize 0x593000`），
> IDA 库 `codoMP_client_shipRetail.exe.i64` 是从加密态 exe 建的（里面搜不到
> `CLIENTCHAL` / `BDDATA`），所以**无法从静态文件绕过，必须运行时 dump**。

## 10.8 【2026-10-03 晚】dump 到手 —— KDF 每一环都在真实二进制里读出来了

`_exe_b9c.bin` 拿到了（21,334 非零字节）。`analyze_kdf_refs.py` 一击命中：
`BDDATA`/`CLIENTCHAL` 的引用者就藏在 **0xB9C000..0xBA2000** 这段（印证了之前的推断）。

### 客户端真实的 `deriveSessionKeys`（0xBA1E??–0xBA1FA?），与 ol-mod **逐条吻合**

```
0xBA1EDF  push 0x10            ; size = 16
0xBA1EE1  lea  ecx,[ebp-0x20]  ; 输出缓冲
0xBA1EE5  push 0x0A            ; label 长度 = 10
0xBA1EE7  push 0xD5A4E8        ; "CLIENTCHAL"
0xBA1EEC  lea  edx,[ebp-0x4C]  ; ← secret (20B)
0xBA1EEF  push 0x14            ; secret 长度 = 20
0xBA1EF2  call 0xBA13D0        ; expandKey()

0xBA1F36  mov  edx,[ebp-0x18]
0xBA1F3C  mov  [ebx+0x5FC], edx     ★ 就是 nt10 读的那个 challenge 槽!
0xBA1F42  mov  [ebx+0x600], eax

0xBA1F60  push 0x48            ; size = 72
0xBA1F69  push 6               ; label 长度 = 6
0xBA1F6B  push 0xD5A4E0        ; "BDDATA"
0xBA1F76  call 0xBA13D0        ; expandKey()
0xBA1F91  call 0xBA0420        ; data[0:20]  → (requestHmac)
0xBA1FA1  call 0xBA02A0        ; data[20:40] → (responseHmac)
0xBA1FA6  mov  ecx,[ebx+0x604] ; ★ 就是 nt10 读 aes_out 的槽
```

→ **算法、label、长度、`challenge[8:16] → [obj+0x5FC]`、四把子密钥的槽位，全部与我们的实现/读法一致。**

### `secret` 的产生：`0xBA0D20` 就是 HMAC

```
0xBA0D57 push 0x14 ; push arg1 ; call 0xC73800   → HMAC 初始化(key=arg1, 20B)
0xBA0D68 push 0x18(24) ; push arg2 ; call 0xC73760 → Update(data=arg2, 24B)
0xBA0D7F mov [ebp-0x34C],0x14 ; call 0xC737A0     → Finish(out, 20B)
```
调用点：`0xBA1E96 call 0xBA0D20(&secret, [ebp-0x60], [ebp-0x38], 0x18)`

→ **`secret = HMAC-SHA1(key = [ebp-0x60] (20B = transcript 哈希), data = [ebp-0x38] (24B = 会话密钥))`**
这**确认了 ol-mod 报告里写反的参数序**（代码是 `hmacSha1(data, key)`）。

### ★ 新发现（ol-mod 报告里没有）：24B 会话密钥是 **XOR 解码**出来的

`[ebp-0x38]` 由 `call 0xBA0750(ecx=obj, arg=&[ebp-0x38], 0)` 取得，而它是跳板 → **`0xBA05A0`**。
该函数内部：

```
0xBA05CC..  [ebp-0x1C] 写入 6 个 dword = 24B 固定密钥:
            ad 42 f5 90 | 88 a4 21 e6 | 3b c9 89 02 | 39 ff 02 dc | 11 04 77 ff | ee 88 62 0d
0xBA05F6..  [ebp-0x7C] 写入 24 项置换表(0..23 的一个排列):
            8,18,9,14,5,20,10,7,11,12,21,22,13,16,3,0,1,15,19,17,23,6,4,2
0xBA068F  add eax, 0xD9            ; 目的地 = this + 0xD8
0xBA06A2  xor bl, [ecx-1] / mov [eax-1], bl ...   ; out[i] = src[i] ^ KEY[PERM[i]]
```

→ 与 nt10 里 `_decode_key`（`out[j]=src[j]^words[indices[j]]`）是**同一套构造**。
已实测：用这 24B 密钥 + 置换去解我们从 `0x82` 取到的原始 24B（`deadbdef…`），得到
`e5da74ed274c4806fd27b53e848b2975b5caca507eb33925`。

### 目前还差的最后一块：transcript（`[ebp-0x60]`）

- `[ebp-0x60]` 是 20 字节，由 `0xBA1E59 call 0xC73D20(..., len=0x14)` 算出 —— 典型的 SHA1(20B)；
- 它的输入缓冲在 `[ebp-0x4F4]` / `[ebp-0x52C]` 一带，而这个函数里反复出现 `push 0x44A`(=1098)
  的缓冲初始化 → **transcript 是逐段拼进一个 ~1098B 缓冲再哈希的**；
- 我们此前穷举过 12 种"wire 切片拼接"，全不中 —— 说明拼接方式与 ol-mod 的
  `hello[8:28] + ServerHeaderAck + clientAuth[:-8]` 不同（我们的 build 另有组装方式）。

### 下一步（唯一剩下的拼图）—— **已实现，待跑一轮**

**运行时挂 `0xBA0D20`**（每次会话只调一次，不是每帧函数，符合我们的 hook 纪律）。
已在 nt10 落地：

| 位置 | 内容 |
|---|---|
| `build_kdf_tramp()` | 专用跳板：`pushfd/pushad` 保现场 → **入口瞬间**抄 4 个入参 + `arg1` 的 20B + `arg2` 的 24B 到数据区 → `popad/popfd` → 执行被偷指令 → 跳回 |
| `kdf_hook_thread()` | 每 1s 重试安装（等 0xB9C000.. 解壳可写），装好后轮询命中计数，落盘 `kdf_inputs.txt` |
| 启动点 | main 里紧跟"兼容补丁线程"之后，用代码洞的备用槽（`len(apis)+6`），不占用既有 hooks |
| 自检 | 把生成的 stub 用 capstone 反汇编核对过：`pushfd/pushad`→入参捕获→内容拷贝→`popad/popfd`→被偷指令→`jmp 0xBA0D25`，全部正确 |

**★ 为什么必须在入口抄**：两个入参指向的缓冲都在**调用方栈上**（`[ebp-0x60]` / `[ebp-0x38]`），
函数一返回就被覆盖 —— 和 `describe_sockaddr` 那次踩的坑一模一样。

**跑法**：

```powershell
cd "e:\codol tae"
python .\run_all.py --secs 260 --out n10kdf.txt     # 管理员
python .\kdf_probe.py --inputs                      # 验证 KDF + 反推 transcript 组装
```

`kdf_probe.py --inputs` 会做两件事：
1. 用抓到的两个入参独立复算 KDF，与 `secrets.txt` 的内存真值逐字段比对（**应当全 OK**）；
2. **拿那 20 字节哈希当靶子**，穷举 `hello/0x81/0x82 各切片`的拼接顺序 ——
   一旦 `SHA1(拼法) == 靶子`，transcript 的组装方式就被唯一确定（20B 哈希不会碰撞）。

## 10.9 【2026-10-03 深夜】★ KDF 收口 —— hook 一次就把两个入参都拿到了

### 结果：KDF **完全对上**

`kdf_inputs.txt` 抓到（第 2 次会话）：

```
transcriptHash = 5caa299738f6a4cbe08d6ea051d5c832fcf7811a   (20B, HMAC 的 key)
sessionKey     = c6e504234261809fbeddfc1b3a597897b6d5f4133251708f   (24B, HMAC 的 data)
```

用这两个入参独立复算，与 nt10 从内存读出的真值**逐字段一致**：

```
decrypt        KDF=46b1d110af78a653df1080d49135bb1a   内存=46b1d110af78a653df1080d49135bb1a   OK
encrypt        KDF=ddfc446a29e8aa4de841f2b983eaaa46   内存=ddfc446a29e8aa4de841f2b983eaaa46   OK
request_hmac   KDF=62372b2b29789ed99476292aacbc000a1068cd50  内存=…cd50  OK
response_hmac  KDF=6af57787fde2de25aa3d13ad04560aa62a6505db  内存=…05db  OK
response_id    KDF=74fa29e748cb1891                   内存=74fa29e748cb1891                    OK
```

→ **算法 + 两个入参来源全部确认，deriveSessionKeys 到此收口。**

### ★ 顺带纠正一个此前的错误假设

我原以为 24B 会话密钥是"票据前 24 字节"（`DE AD BD EF…`）。**实测不是**：

```
票据[97:121] = c6 e5 04 23 42 61 80 9f be dd fc 1b 3a 59 78 97 b6 d5 f4 13 32 51 70 8f
                    ↑ 与 hook 抓到的 sessionKey 逐字节相同
```

即 **会话密钥 = `ticket[97:121]`** —— 这**正好对上 ol-mod 自己 `makeTicket()` 的布局**
（第 781 行：会话密钥写在票据偏移 **97..120**）。`authInfoData[0:24]` 其实只是票据开头（魔数）。

### transcript 组装仍没复现（但已不阻塞）

修掉一个会话配对 bug（`lobby_rx.bin` 跨轮 append，得取**最后一次**会话；`secrets.txt` 只记最后一轮）后，
仍试了 2,639 种拼法未命中 → transcript 的组装方式与 ol-mod 的写法确实不同（可能不是简单的帧拼接）。
**但因为 hook 已经把两个入参都抓到了，这一步不再是必需** —— 直接拿入参算密钥即可。

### 已落地的"脱开内存快照"

| 改动 | 说明 |
|---|---|
| `kdf_hook_thread()` 新增 | 命中后**立刻用两个入参派生**出 4 把子密钥 + challenge，原子写入 `secrets_kdf.txt` |
| `lobby_server.read_secrets()` | **优先读 `secrets_kdf.txt`**（KDF 派生），没有才回退 `secrets.txt`（内存快照）；日志打 `[keys] 拿到会话密钥 来源=kdf/mem` |
| nt10 启动清理 | 先删掉上一轮残留的 `secrets_kdf.txt` —— 否则本轮 hook 没挂上时会误用旧密钥 |

**收益**：不再依赖"读 auth 对象内存槽 `[sub+0x604..0x60C]`"与 `[sub+0x5E8]==3` 的时序，
为将来多客户端（每个客户端一套派生密钥）铺好了路。

### 端到端验证（2026-10-03 夜，`n10kdf3.txt`）

```
-- [KDF] 抓取线程已启动 (hook 0x00BA0D20, 槽 14)
  [kdf] ★HMAC 命中#1 ret=0xBA1E9B arg1=0x19EA18 arg2=0x19EA40 arg3=24 arg4=0x19EA2C (magic=OK)
  [kdf] ★ 已按派生结果写出 secrets_kdf.txt (challenge=0d14ac7cf0c702de …)
  [kdf] ★HMAC 命中#2 … challenge=07a66e4b7a940b2e
  [kdf] ★HMAC 命中#3 … challenge=865d4d27262d0ac1
```

`lobby_srv.log`：**`[keys] 拿到会话密钥 来源=kdf`**（两次都是 kdf，不再是 mem）；
大厅正常，本轮共解出 **51 条**任务帧。

**★ 一个值得记下的现象**：三次命中的 **`sessionKey` 完全相同**（`c6e5…708f`，
因为我方 `/auth/` 伪造票据是确定性的），但 **`transcriptHash` 每次都不同** →
**每会话的派生密钥都不同**。这正好说明 KDF 是真正按会话走的，
**多客户端（每个客户端一套密钥）的路是通的** —— 而"共享一把密钥"在协议上根本不可能成立。

---

# 11. 【2026-10-03 夜】房间 ready（`11/4`）与 booking（`6/14`）

## 11.1 先补齐了「服务端主动推送」这条基建

之前只做过**任务应答**（明文 marker = `0x01`）；房间/即时消息要靠**服务端主动推送**（marker = `0x02`），
壳完全一样。新增（都照抄 ol-mod）：

| 函数 | 说明 |
|---|---|
| `codol_crypto.build_push(aes_in, hmac_in, seq, body, message_type=2)` | 同 `0x85` 壳，明文 `u32 len │ 0x02 │ body │ 补齐` |
| `codol_crypto.instant_push_body(uid, name, msg)` | `[u32 21][u64 senderId][string name][blob msg]` |
| `codol_crypto.channel_push_body(uid, name, chan, msg)` | `[u32 7/8][u64 uid][string name][u64 chan][blob msg][u32 type]` |
| `cc.ROOM_READY_BATCH` | 房间 ready 的 16B 批次常量 `0C 00 00 00 02 02 00 00 00 08 00 00 00 80 08 00` |

`reply_objects()` 现在返回 `(objects, 说明, pushes)`，调用方在应答之后把 `pushes` 逐条发出。
自检：构造的推送帧能被我方解析器正确解出（`marker=0x02`、`declared=43`、`hmac=True`、body 逐字节一致）。

## 11.2 `11/*` 房间服务（照抄 ol-mod `Unknown0BService`）

| task | 名称 | 处理 |
|---|---|---|
| 13 | `createRoom` | 对象 = `[u64 roomId][u32 memberCount=0][u32 18][u64 secondId][bool false][bool false][u32 1]`（37 B） |
| 4 | **`setRoomData`（房间 ready 走这里）** | 空应答 + 日志（payload 里命中 `ROOM_READY_BATCH` 特征会标注） |
| 2 | `leaveRoom` | 空应答 |
| 5 | `publishChannelMessage` | 空应答 |
| 1/9/11 | `consumeUserPair(u64,u64)` | 空应答 |
| 10 | — | 空应答 |
| 其它 | — | 空应答 + 记 payload 长度 |

## 11.3 `6/*` 即时消息与 booking

| task | 名称 | 处理 |
|---|---|---|
| 5 | `readQueuedMessages` | 空应答；若 payload 含 **`mmstart <token>`** → 走 booking 分支 |
| 14 | `sendGlobalInstantMessage` | 同上 |
| 18 | `sendInstantMessage` | 同上 |

**booking 分支**（照抄 ol-mod `InstantMessageService.cpp:124-146`）：
token 的 **FNV-1a 32 位 == `0xDEC30B2A`** 时，回一条**推送** `mmbook accepted`
（`instant_push_body`，marker=2）。FNV-1a 用 `_fnv1a()` 实现了（初值 `0x811C9DC5`、质数 `0x01000193`）；
token 为空时也放行（对应"客户端只发 `mmstart` 不带 token"的情形）。

> ⚠️ 注意：我们的客户端**目前还没走到房间/booking 这一步**（`lobby_tasks.bin` 里只有 `6/5`），
> 所以这些都是**按 ol-mod 的 spec 先把形状接上 + 全量记日志**，
> 等真点到「开始游戏/加入房间」时再看客户端实际发什么。

## 11.4 自检结果

```
createRoom      -> 1 对象 37 字节 (roomId=0x1122334455667788)
setRoomData     -> 空应答 (payload=20, 含 ready 批次特征)
leaveRoom       -> 空应答
consumeUserPair -> 空应答
publishChannel  -> 空应答
6/5,6/14,6/18   -> 空应答
6/5 + mmstart   -> 空应答 + 日志(fnv 值)   ← 命中 0xDEC30B2A 时改推 mmbook accepted
推送帧           -> 82 字节, marker=0x02 declared=43 hmac=True body 逐字节一致
```

---

# 12. 【2026-10-03 深夜】多客户端改造

## 12.1 难点不是"并发"，而是**密钥配对**

`lobby_server` 本来就是"每连接一线程"，天然并发。真正的问题是：
**每个客户端的会话密钥不同**（§10.9 实测：`transcriptHash` 每次会话都变），
而原来的密钥来源是**一个全局文件**（`secrets_kdf.txt` / `secrets.txt`）——
两个客户端会互相覆盖，服务端也分不清哪把密钥属于哪条连接。

## 12.2 解法：让「会话密钥」成为配对键

关键洞察：**客户端真正用的会话密钥 = 票据偏移 97..121**（§10.9 实测），
而这份票据**是我们自己的 `/auth/` 发出去的** —— 所以整条链都在我们手里：

| 环节 | 改动 |
|---|---|
| `fake_auth_tls.make_ticket(sk)` | 保持 `DE AD BD EF` 魔数与其余字节不变，只把 **97..121 换成每次唯一的随机 24B**；并记进 `auth_sessions.txt` |
| `codol_crypto.ticket_from_client_auth()` | 从 0x82 帧里取出被转发的 128B 票据（跳过 83 bit，LSB-first） |
| `codol_crypto.session_key_from_ticket()` | `= ticket[97:121]`（**纠正**：以前误以为是票据开头的 24B） |
| `nt10` | 每次 KDF 命中往 **`kdf_sessions.txt`** 追加一行：`会话密钥 + transcript哈希 + challenge + 四把子密钥` |
| `lobby_server` | 收到 0x82 → 读 `ticket[97:121]` → **查表拿到该客户端自己的密钥** → 用它解 0x85 / 签应答 |

密钥优先级：**本连接专属（配对）** > `secrets_kdf.txt`（全局 KDF） > `secrets.txt`（内存快照）。
配对失败会打 `[multi] 会话密钥 … 不在 kdf_sessions.txt（回退全局密钥）`，不影响单客户端。

## 12.3 顺带处理的两件事

| 项 | 处理 |
|---|---|
| **会话表残留** | nt10 启动时删除上一轮的 `kdf_sessions.txt`（否则可能配到上一轮的旧会话 → 用错密钥） |
| **就绪标志** | nt10 现在同时写 `lobby_ready.flag` 与 `lobby_ready_<pid>.flag`；`lobby_server.wait_ready()` 只要任一存在就放行 |

⚠️ **已知局限（如实记录）**：客户端在 0x82 之前不暴露身份（身份只在票据里），
所以"按 pid 精确放行"做不到；现在是"至少有一个客户端就绪即放行"，
尚未就绪的那条会被客户端复位后重连（实测客户端本来就会重连 2~3 次，可自愈）。
要彻底解决，得先复现 transcript 的组装方式（§10.9 那个未闭合项）。

## 12.4 跑法

```powershell
cd "e:\codol tae"
python .\run_all.py --secs 260 --clients 2 --out n10multi.txt
```

`--clients 2` 会**同时起两份 nt10**（每个 nt10 自己拉起一份游戏并注入）。
看这些文件：
- `kdf_sessions.txt` —— 应该出现**两行**（两个会话，会话密钥不同）
- `auth_sessions.txt` —— 两次 `/auth/` 的两个会话密钥
- `lobby_srv.log` —— 每条连接应打 `[multi] 配对成功: 会话密钥=… -> 用本会话密钥`
- `lobby_ready_<pid>.flag` —— 两份

**自检（已验证）**：造两张唯一票据 → 塞进 0x82 帧 → 服务端还原出的会话密钥与签发的一致
（A/B 各自正确且互不相同），`load_kdf_sessions()` 按会话密钥查表也正确。

> 注：游戏是**单实例互斥**的（`Global\{5BD75B76-…}`）。nt10 有 `--mutex` 参数；
> 若第二份起不来，先看是不是被互斥挡住 / 有没有残留僵尸进程。

### 12.5 首次 `--clients 2` 实测：配对机制 **成功**，但被"互相杀"卡住

第一轮实测（`n10multi.txt` + `n10multi_c2.txt`）结果：

| 观察 | 结论 |
|---|---|
| `lobby_srv.log` 出现 **`[multi] 配对成功: 会话密钥=187f70a7… -> 用本会话密钥 (aes_out=a1082761… challenge=f984b861…)`** | ✅ **配对机制生效** —— 服务端确实用该客户端自己的密钥解了 0x85 |
| `kdf_sessions.txt` 只有 **1 行**，而 `auth_sessions.txt` 有 **4 行** | ⚠️ 只有一份客户端真正跑到了 KDF |
| `n10multi.txt` 里两次 `game pid=… (第 N 次启动)`，且**没有任何 `[kdf] ★HMAC 命中`** | ⚠️ 第一份客户端的游戏反复被杀 |
| `解密成功` 共 **97 条** | ✅ 大厅仍正常 |

**根因**（已定位到行）：nt10 启动前会
```python
for n in ("codoMP_client_shipRetail.exe", "TP3Helper.exe"):
    subprocess.run(["taskkill", "/F", "/IM", n], ...)     # ← 杀掉**所有**实例
```
两个 nt10 **互相杀对方的游戏**，形成拉锯 → 实测永远只有一个游戏活着。

**修复**：nt10 新增 `--keep-others`（多客户端时启动前只清 `TP3Helper.exe`，不碰别的 codoMP）；
`run_all.py --clients N`（N≥2）会自动带上它。

→ 请重跑：`python .\run_all.py --secs 260 --clients 2 --out n10multi2.txt`
预期 `kdf_sessions.txt` 出现**两行**、两条连接各打一次 `[multi] 配对成功`。

### 12.6 第二轮实测：`--keep-others` 生效，但**游戏自身的单实例门**挡住第二份

`--keep-others` 之后两个游戏都能**启动**了（pid 18784 / 27568），但：

```
n10multi2_c2.txt:  game 退出 rc=0 t=4.0          ← 第二份客户端自己退出了(不是被杀)
                   [ready] [0x08269774]=00 00 00 00 -> 连接对象=0x00000000 5E8=None
```

第二份客户端**干净退出（rc=0）**、且从未初始化大厅对象 —— 也就是**游戏自身的单实例限制**把它挡掉了
（我们只是不再互相杀，但游戏自己不允许跑第二份）。

**ol-mod 怎么做到的**（查了他们仓库的 `Match_CODOL_Two_Clients.bat` / `tools/runtime/CodolGame.py`）：
他们**根本不直接跑 `codoMP_client_shipRetail.exe`**，而是走自己的 Ayria 启动链：

```
Injector32.exe <游戏目录> <角色> <client_instance> …     ← 他们自研的注入器
  + Bootstrapper32.dll / Localnetworking.Ayria32 / Platformwrapper.Ayria32 / Alwaysoffline.Localnet32
  + 环境变量 OLMOD_CLIENT_INSTANCE=1/2、OLMOD_PLATFORM_USER_ID=<账号>
```
即**多实例是由他们自研插件栈支撑的**（每个实例一套插件 + 一个 instance 序号 + 一个账号）。
我们这条"hosts 劫持 + 假服务 + 内存补丁"的路线**没有这层**，所以直接跑两份 exe 会被游戏的单实例门拦下。

**结论**：多客户端的**服务端配对已就绪并实测生效**；剩下的是**启动链层面**的问题
（游戏单实例门），与密钥/协议无关。

**可选下一步**：
1. 像找 KDF 那样，用 nt10 dump 出游戏**启动早期**的模块/命名对象调用，定位"退出前最后检查了什么"（mutex / window class / registry）；
2. 或先接受现状 —— 等以后做启动链时一并解决；配对的代码已经在了，届时自动可用。

> **2026-10-03 晚决定**：这条线**先搁置**（我们的路线不需要多实例），转去做**进房间 / 进对局**。

---

# 13. 【2026-10-03 深夜】进对局：战斗服（UDP 28960）起步

## 13.1 战斗服的协议形状（来自三方的 C# 源码）

三方源码就在我们仓库里：`success/codol/dist/launcher_src/tools/firingrange-test/src/`
——`CodolLocalBattleServer.cs`(28.9 KB) + `CodolBattleKeyExchange.cs`(5 KB)，
且 `success/codol/dist/CODOL-Portable/Data/firingrange-battle.enabled` 说明**他们确实跑通过一局**（同目录 `battle.log` 有 105 MB 实录）。

**绑定**：`UDP 127.0.0.1:28960`（与我们 `21/5` 会话对象里填的 `hostAddr` 一致）。

**握手四步**（`ReceiveLoop` 的分派顺序）：

| # | 步骤 | 形状 |
|---|---|---|
| 1 | **NAT 遍历** | 29B 固定包，首字节 `13` → 回**同一包但首字节改 `12`**；末尾 6B 是 `127.0.0.1:0x2071`（本机 127.0.0.1:29297），服务端以此确认是本机 |
| 2 | **DTLS init ack** | `TryBuildInitAck` → 交换 `clientTag`（包偏移 6 的 u16） |
| 3 | **DTLS cookie ack** | `TryBuildCookieAck` → 之后进入 `transport-ready` |
| 4 | **数据帧** | `TryReadData` → 加密快照 / GameState |

**密钥派生**（`CodolBattleKeyExchange.cs`）：
```
ECDH **P-224**（libtomcrypt DER 公钥补到 100B；头 03 02 07 00 02 01 1C）
  → NCryptSecretAgreement/TRUNCATE 得 raw 28B（CNG 小端 → **反转**成大端）
  → material = raw(28) ‖ securityKey(16) = 44B
  → **SHA1(material)** → 写入 24B 缓冲（前 20B 有效）
  → "AES 用前 16B, HMAC 用全部 24B"
```
其中 `securityKey` 就是我们写在 `21/5` 会话对象里的那 **16B**（`lobby_server.SEC_KEY`）——
所以 `lobby_server` 现在会把它的 hex 写进 `battle_security_key.txt`，供战斗服共用。

## 13.2 本轮落地：`battle_server.py`（最小骨架 + 抓包观察通道）

| 已做 | 说明 |
|---|---|
| 绑 UDP `127.0.0.1:28960` | 与 21/5 的 hostAddr 一致 |
| **全量抓包** | 每包写 `battle_srv.log`（前 40 包 + 每 50 包一次全 hex，另有首字节类型分布统计） |
| **NAT 遍历应答** | 完全照抄三方：29B、首字节 13→12、包体原样回 |
| 读 `battle_security_key.txt` | 为后续 ECDH 派生备好那 16B |
| 其余包 | 记 `(未实现: type=… len=…)` —— 先把包看全 |

**自测（已通过）**：
```
发送 29B(type=13) → 收到 29B(type=12), 与请求除首字节外完全一致 ✓
再发一个 type=0x99 的包 → 日志记为 "未实现: type=153 len=21" ✓
```

**接线**：`run_all.py` 默认拉起战斗服（`--no-battle` 可关），日志 `battle_srv.log`。

## 13.3 下一步（等真实包）

1. 跑一轮并在游戏里点到**多人/训练场**，看 `battle_srv.log` 里客户端实际发什么；
2. 按包序补齐 `TryBuildInitAck` / `TryBuildCookieAck` / `TryReadData`（C# 参考在手）；
3. ECDH P-224 在 Python 里可用 `cryptography` 或纯实现（本机只有 stdlib，需评估）；
4. 训练场（firingrange）是最小可验证目标 —— 三方就是从这里跑通的。

## 13.4 【2026-10-03 深夜】房间 ready 的"频道推送回显"实验：**格式不对，一发就断**

**动机**：`11/4 setRoomData` 在 ol-mod 里会把 ready 消息广播回频道；客户端可能在等这个回执才允许"开始游戏"。

**做法**：建 `ready_push.on` 打开（默认关），在 `11/4` 时回一条 channel push
（`channel_push_body`，marker=2）。

**结果（决定性，因果清晰）**：
```
[23:03:44] -> 0B/4 setRoomData ... 已回显频道推送
[23:03:44] -> 0x85 推送 type=2 seq=55 (226 字节 body=175)   ← 我们发出推送
[23:03:44] ★ 解密成功 #55 ...（客户端还回了一帧）
[23:03:44] 对端关闭                                          ← 客户端立刻断连
[23:03:45] 重连后 hmac=BAD（新会话，正常）
```
→ **推送体格式与客户端期望不符**。已把 `ready_push.on` 删除（恢复默认关）。

**下一步的修正假设**：ol-mod 的 `decodeChannelPush` / `decodeInstantPush` 很可能用的是
`useDataTypes(false)`（他们处理本地即时消息时明确关过标签）—— 也就是说 **push 的 body 应该是
"无 tag 的裸字段"**，而我们用 `Buf` 写了 `10/0A/13` 等标签。
下次要做这个实验时，先写一版**无 tag** 的 `channel_push_body` 再试。

**另外**：这条实验也顺带证明了推送通道本身是通的（帧能被发出、客户端能收），
差的只是 body 布局 —— 值得再试一次。

## 13.5 【2026-10-03 深夜】无 tag 版频道推送：**大幅改善，但仍不完整**

按 §13.4 的假设把 `channel_push_body` 改成**无 tag**（`Buf(use_types=False)`，
对应 ol-mod 的 `useDataTypes(false)`），再测一轮：

| 版本 | 推送帧发出后 | 结论 |
|---|---|---|
| 带 tag（§13.4） | **同一秒** `对端关闭` | 帧被判非法，立刻断 |
| **无 tag（本节）** | 存活 **6 秒**、期间解出 **57 条任务** | **格式基本对了**，但客户端随后卡死 |

```
[23:11:04] -> 0B/4 setRoomData 空应答(channel=… type=1 batch=140), 已回显频道推送
[23:11:04] -> 0x85 推送 type=2 seq=56 (226 字节 body=173)
[23:11:10] === 大厅连接结束 (解出任务 57 条) ===
```

**判定**：`use_types=False` 的方向**正确**（与带 tag 版形成明确对比），但推送体仍缺东西 ——
客户端收下后**卡在房间里**，像是在等某个后续应答，而不是把推送判为非法。

**已恢复到安全状态**：`ready_push.on` 已删除（推送默认关）。

**下一步的三条候选**（按可能性排序）：
1. **`11/4` 之后再来的 task 我们没答**（那段 6 秒里客户端还在发包）→ 对比
   `lobby_tasks.bin` 里 `11/4` 之后紧邻的 task，看有没有我们回空的；
2. **`216/217` 未知 service**（ol-mod 的 27 个注册里没有，最像"开局/会话开始"通道）；
3. 推送的**信封**（service/task 号）可能不是"裸 body"，而需要一个外层封装 —— 需按
   `CodolLocalBattleServer.cs` 的 `decodeChannelPush` 反推 encode 侧。

## 13.6 ★★ 真正的根因：推送抢走了应答的 replyId（已修）

§13.5 那轮"卡死"的原因**不在推送体格式**，而在**我们自己代码的计数器 bug** ——
离线对比 `lobby_srv.log` 的 task 序列即可看出：

```
<- #55 service=11 task=4   -> 应答 seq=55(replyId=55)  ✓
-> 推送 type=2 seq=56                                    ← 推送占用了 id 56
<- #56 service=21 task=12  -> 应答 seq=56(replyId=57)  ✗ 应为 56
<- #57 service=71 task=7   -> 应答 seq=57(replyId=58)  ✗ 应为 57
```

**根因**（`lobby_server.py` 原 588-601 行）：应答的 replyId 与推送的 seq **共用同一个全局
计数器 `srv_seq`**。推送先发、占掉一格后，**后续每一个应答的 replyId 都整体错位一格**
→ 客户端匹配不上自己的请求 → 卡死 → 抛 `ClientException`
（`service=71 task=7`，payload = `'ClientException|${TIMESTAMP}|…|Windows 10|…'`）
→ `ConnectionAborted(10053)` 本地中止。

**这正是我们自己早就踩过的坑**："应答 seq 必须回显请求 seq，回错客户端立刻断连"
（见 §7）。1:1 时 `srv_seq` 恰好等于请求 seq，所以 55 帧都没暴露问题；**推送一插进来就破功**。

**修法**：
1. 应答的 **seq 与 replyId 都回显请求的 seq**（`r["seq"]`）—— 不再依赖任何全局计数器；
2. 推送改用**独立计数器 `push_seq`**（从 1000 起），与应答的 replyId 完全隔离。

> 附带结论：§13.4/§13.5 的"带 tag 立刻断 / 无 tag 活 6 秒"这个差异**仍然成立且有效**
> （无 tag 版确实更接近正确），但真正让它"卡死"的是本节这个计数器 bug。两个问题叠加，
> 所以表现为"无 tag 版也失败"。

## 13.7 replyId 修复已验证；**但推送本身仍然有害 —— 决定停用**

修完 §13.6 的计数器 bug 后再跑一轮，**修复本身确认生效**：

```
<- #55 service=11 task=4   -> 应答 seq=55(replyId=55)  ✓
-> 推送 type=2 seq=1000                                 ← 独立计数器, 不再抢号 ✓
<- #56 service=21 task=12  -> 应答 seq=56(replyId=56)  ✓   (上一轮此处是 57 ✗)
```

**但推送一发，客户端仍然断开**（这次是干净的 reset，不再是卡死+异常上报）：

```
[23:16:45] -> 0x85 推送 type=2 seq=1000 (210 字节 body=168)
[23:16:45] recv 异常: ConnectionResetError(10054)   ← 收到推送后立刻 reset
[23:16:46] 重连: 首帧 hmac=BAD(密钥未就绪), 1 帧后对端关闭
```

**判定：channel push 是净负收益 —— 决定停用。**
- **不发推送时，房间流程完全正常**（`11/13 createRoom` → `11/4 setRoomData` → 正常应答，客户端可以自己走完）；
- 一发推送就断，说明推送体的**字段序/信封/类型**仍有一处不对（无 tag 只是"更接近"，不是"正确"）；
- `ready_push.on` 已删除，推送恢复默认关。

**要再碰推送时的正确做法**：不要靠猜字段序，而应从 `CodolLocalBattleServer.cs`
的 `decodeChannelPush`（客户端→服务端方向已实现）严格反推 encode 侧，或直接抓一份
**官方服务器当年的真实推送帧**（若队友保留有 pcap）。

**转向**：房间/对局这条线不再依赖推送，继续推进应聚焦
① `216/217` 未知 service（最像"开局/会话开始"）；
② 重连首帧 `hmac=BAD` 的健壮性问题（密钥未就绪时应**先把帧攒进 pending**，
   而不是用占位密钥硬解 —— 现有 `pending` 机制没覆盖"重连时 keys 尚未刷新"这一路）。

---

## 13.8 【2026-10-04】★★ 推送断连的**真正根因** = 出站帧 seq 必须**严格 +1**

> 本节**推翻** §13.7 的结论"推送本身有害"。推送本身是对的，错的只有两点：**seq 取法**和**推送体内容**。

### 证据链

1. **我们自己的实现**（`cc.instant_push_body`）与三方 `BuildPushFrameWithSender`
   逐字节一致 —— 实测对比：
   ```
   ours : 08 0b 00 00 00 0a 01 00 00 00 00 00 00 00 10 50 6c 61 79 65 72 00 13 08 10 00 00 00 <16B>
   C#   : 08 0b 00 00 00 0a 01 00 00 00 00 00 00 00 10 50 6c 61 79 65 72 00 13 08 10 00 00 00 <16B>
   ```
   → 信封格式**没有问题**。§13.4/13.5/13.7 的失败不是信封错（那时用的是 `channel_push_body`，现在已废弃）。

2. **三方源码 `CodolLocalLobbyServer.cs:1144`**：
   ```csharp
   uint num8 = 1u;      // 每连接一个"出站 0x85 帧序号"计数器
   ulong num9 = 0uL;    // replyId 计数器
   ```
   且**每一处出站都走它**：应答 `BuildTaskReplyObjects(..., b4, num8++, ++num9, ...)`、
   频道回显 `BuildPushFrameWithSender(..., num8++, 11u, ...)`、
   booking 推送 `BuildPushFrameWithSender(..., num8++, 21u, ...)`。
   → **出站 seq 与"客户端请求的 seq"无关**，它只保证**每帧 +1**。

3. **我们 2026-10-04 那轮的失败**：让推送"回显请求 seq"后，
   同一个 `11/4`(seq=52) 会连着发两帧 seq=52（应答 + 推送）—— **重复** →
   客户端**同秒 `ConnectionReset(10054)`**，四次复现：
   ```
   00:50:14 -> 应答 seq=52 … -> 推送 seq=52 → recv 异常 ConnectionReset(
   00:50:27 -> 应答 seq=24 … -> 推送 seq=24 → recv 异常 ConnectionReset(
   00:52:05 -> 应答 seq=51 … -> 推送 seq=51 → recv 异常 ConnectionReset(
   00:53:45 -> 应答 seq=28 … -> 推送 seq=28 → recv 异常 ConnectionAborted(
   ```
   §13.7 试过的 `push_seq=1000` 则是**跳号**（55 → 1000）→ 同样违反 +1 → 照样 reset。
   **两种取法都错，正确答案是三方的 `num8++`。**

4. **为什么"回显请求 seq"在无推送时能用**：客户端请求 seq 本身是 1,2,3… 严格 +1，
   我们逐条回显 → 出站序列恰好也是 +1。**一旦插入推送就破功**（§13.6 的 replyId 抢号是同一个病）。

### 修法（本轮已实施，`lobby_server.py`）

- 每连接一个懒初始化的出站计数器 `out_seq`：
  应答用它当 seq（首帧取请求 seq → **无推送时与旧的回显逐字节等价，零回归**），
  每发一帧（应答/推送都算）`out_seq += 1`；
- `replyId` 仍回显请求 seq（三方的 `num9` 在 1:1 时与请求 seq 同值）；
- 推送一律用 `out_seq`，**不再回显请求 seq、也不再另起号段**。

### 同时修正的推送体（`11/4`）

照抄三方 `SendChannelMessage` 分支（`CodolLocalLobbyServer.cs:1399-1412`）：
- 先回空 ACK；
- 再把**客户端这条频道消息原样回显**成频道广播：
  `BuildPushFrameWithSender(seq, 11u, pushData=客户端 payload, senderId=1, "Player")`；
- 旧代码推的是**无关的 16B `ROOM_READY_BATCH` 常量**（客户端没发过这条消息）→ 也是断连诱因之一；
- 三方的 game-start 触发条件是 `payload[11] == 0x15`：本轮**只记日志**（`sub[11]=0x??`），
  等确认不再断连后再单独加 game-start 推送（一次只改一个变量）。

### 对`6/14` booking 的连带影响

booking 推送（service=21 / senderId=1 / "localhost"，`BuildFiringRangeBookingAccepted`）
**除了 seq 之外本来就与三方逐字节一致** —— 所以 §11.3 起"客户端每 5~15s 重发 mmbook"
极可能就是同一个 seq 病。本轮修完应一并生效（前提：`firingrange-session.enabled` 也要在，
否则 `21/5` 回的不是靶场 session）。

### 13.8.1 验证结果（`n10ready2.txt` / `lobby_srv.log` 01:01~01:05）

**✅ seq 修复确认生效 —— 不再断连。** 整整 95 条任务、多次 `11/4` 推送，出站序列严格 +1：

```
01:01:39 -> 应答 seq=53 … -> 推送 seq=54(出站计数器, 242B body=192)   ← 频道回显
01:01:39 -> 应答 seq=56 … -> 推送 seq=57(出站计数器, 114B body=70)    ← 频道回显
01:04:59 -> 应答 seq=94 … -> 推送 seq=95 …  01:04:59 -> 应答 seq=96 … -> 推送 seq=97 …
```
（对比上一轮：推送 seq 与应答 seq **同值** → 同秒 `ConnectionReset`。）

**✅ ready 消息确认到达。** `0B/4 setRoomData` 的 payload[11] 序列：
```
0x8F(143B 房间数据) → 0x15 ★ready → 0x10(16B, 含 ROOM_READY_BATCH) → 0x14 → 0x15 ★ready
```
→ 三方 `payload[11]==0x15` 的判据在真实客户端上**成立**。

**❌ 但"准备无反应"** —— 因为只做了频道回显，**没推 game start**。
→ 本轮已补：`sub==0x15` 时紧跟着再推一条 `BuildPushFrame(seq, 11u, gameStartData)`
（= `cc.GAME_START_PAYLOAD`，162B，逐字节照抄 C# 1419-1430；`senderId=0, "Server"`）。

**其它现象**：
- 01:05:04 客户端报了两条 `71/7 UIException|…|ZONEID(16701785630074219790)|…`（408B）——
  与 §13.6 的 `ClientException(71/7)` **同族**，但这次**没有伴随断连**（连接又活了 27s），
  更像"点准备后 UI 没反应"的异常上报，**不是**推送格式错误。
- "剧情模式显示战斗开始然后一直转圈" —— 本轮 `--no-battle`，UDP 28960 上**没有服务端**，
  所以客户端连不上战斗服。下一轮去掉 `--no-battle`，至少让 `battle_server.py` 收包。

### 13.8.2 验证结果（`n10ready3.txt` / `lobby_srv.log` 01:08~01:13，**带 `--no-battle` 已去掉**）

**✅ game-start 推送已发出且被接受**（01:09:42 / 01:10:10 各两次）：
```
-> 应答 seq=55(replyId=54) service=11 task=4 …
-> 0x85 推送 type=2 seq=56(114B body=70)    ← 频道回显
-> 0x85 推送 type=2 seq=57(242B body=190)   ← ★game start(162B payload)
```
**全程零断连**（连接活到 01:13:30 用户手动退出）。→ seq 修复稳。

**❌ 但"准备无反应"依旧**，而且**战斗服一个包都没收到**（`battle_srv.log` 只有启动横幅）：
```
[01:08:18] [*] 已监听 UDP 127.0.0.1:28960      ← 之后 0 个 RX
```
→ 说明**客户端根本没走到"连战斗服"这一步**。三方的 `gameStartData` 是他们为
**靶场**硬编码的一份 mission 参数 blob，**从未在自定义房间场景被验证过**（其 `lsg.log` 里
压根没有 `service=11`）。所以房间 ready 这条线**不能靠抄这个 blob 打通**。

**⚠️ 更正一个假信号**：`71/7 UIException|…|ZONEID(16701785630074219790)|…` 在**点准备之前**
（01:09:13 / 01:09:24）就出现过 —— 是**例行遥测**，与推送无关，别再当成"推送格式错误"。

**靶场这轮压根没测到**：`靶场开关: session=False`，所以客户端拿到的 `21/5` 不是靶场 session，
**一条 `6/14 mmbook` 都没发**（全日志只有一条 `6/5`）→ "服务器繁忙"是必然。
要测靶场必须开 `firingrange-session.enabled`。已核对：靶场 session 对象的地址块
（67B）确实指向 `127.0.0.1:28960`（`addr[0..5] = 127.0.0.1:0x7120`，端口小端 0x7120=28960）✓。

### 13.8.3 ★ 结论：三条路（房间 / 靶场 / 剧情）的**共同卡点都是战斗服**

- 房间：准备 → game-start（已推）→ 客户端需要**可连的战斗服**才算"进对局"；
- 靶场：booking（推送已修）→ 同样要连战斗服；
- 剧情：客户端已显示"战斗开始"，也是卡在连不上战斗服。

我们的 `battle_server.py` 目前只有 **UDP 绑定 + NAT 遍历应答（type 13→12）+ 抓包**，
**ECDH / DTLS-like 握手 / netchan / 快照 / 输入回放全未实现**。
三方参考是完整的：`CodolLocalBattleServer.cs`(+`CodolBattleKeyExchange.cs`、
`CodolClientCommandReader.cs`、`CodolMotionSnapshot.cs`、`CodolRangeEquipment.cs`、`CodolStateReader.cs`)。

---

## 13.9 【2026-10-04】深挖 game-start 参数 —— 结论：**大厅本来就不负责开局**

### 1) 先更正一个判据：`payload[11]==0x15` 是**误读**

三方 `CodolLocalLobbyServer.cs:1416` 用 `pushData[11] == 0x15` 当"ready 子类型"。
但实测我们这个客户端的 `11/4` payload[11] 依次是 `0x8F / 0x15 / 0x10 / 0x14`，
**恰好等于各自 blob 的长度**（143 / 21 / 16 / 20）——
也就是说 `payload[11]` 是 **blob 长度的低字节**，不是子类型（C# 自己也把注释写成
"subtype is at pushData[13]" 与代码矛盾）。

**ol-mod（第三个独立来源）用的是逐字节比较那 16 字节批次**：
`Unknown0BService.cpp:96-105` 的 `CapturedReadyMessage` = 我们日志 01:09:54 那条 16B blob，
逐字节相同 → 已把本机判据改成 `batch == ROOM_READY_BATCH`（实测命中 ✓）。

### 2) `11/4` 的正确应答：**裸 ACK**（ol-mod 的逆向注释，权威）

> Task 4 — every room message the client sends, as `(u64 roomId, blob batch, u32)`.
> NOT a heartbeat: `FUN_007e82f0` … builds this task via `FUN_00b8ec00 = FUN_00b78bc0(buf, 0x0B, 4)`,
> so the packed batch of queued room messages — **准备 among them** — arrives HERE, inside the blob.
> **Unlike task 13 it binds no result buffer** (`FUN_00b8ec00` never calls `FUN_00b83cb0`),
> so **a bare acknowledgement is correct for this one**.

→ 我们回空 ACK 是对的。两份参考**都**额外把这条频道消息**推回**（三方 build push；ol-mod `pushSink_`）。

### 3) ★ 三方那份 `gameStartData` **不可用**

- 它是**不透明抓包常量**（C# 直接 `Convert.FromBase64String` / 内联数组照抄，没有构造过程）；
- 同文件里那份"更好"的 base64 变体 `BuildGameStartMessage`（把 ready 的 `[36..41]` 拷到
  gameStart 的 `[130..135]`）是**死代码**，**从未被调用**，而且**那份 base64 本身是坏的**：
  它声明内层 blob 长度 133（需 15+133=148 字节），**实际只有 136 字节**（被截断 12 字节）；
- 最关键：三方的 `lsg.log` 里**压根没有 `service=11`**（他们只走靶场，没建过自定义房间），
  所以这条路径**他们自己也没验证过**。
- 我们实机试了：发了 game-start 推送后客户端**不断连但也毫无反应**（`battle_srv.log` 0 个包）。

### 4) ★ ol-mod 的真架构：开局在**另一个子系统**，不在大厅

`Servers.cpp:340-365`：`RoomEvent::Ready` → `sharedRoomClient_.setReady(userId, true)`；
`submitBooking`（`mmbook/mmstart`）→ 也是 `sharedRoomClient_.setReady(...)` + `bookingDispatcher_.submit(...)`；
而 `sharedRoomClient_.connect(identity, OlMod::DedicatedControl::configuredClientBridgePort())`
走的是**另一个端口**。也就是说 ol-mod 把房间/预约/开局交给独立的
**"共享房间客户端 + DedicatedBookingDispatcher"** 子系统处理 —— **大厅只负责转发与回显**。

### 5) 意外收获：ol-mod 仓库里有**整套战斗服**

`src/game_server/`：`sv_main_mp.cpp` / `sv_gamestate_mp.cpp` / `ServerCore` /
`DedicatedProcessPatches.cpp` / `ClientProcessPatches.cpp` / `DisconnectWitness.cpp` …
另有 `.agents/research/*.md`（含 `playable_architecture.md`、`source_reconstruction_progress.md`、
`dw3_feasibility.md`）。**比三方的 `CodolLocalBattleServer.cs` 丰富得多**，
且明确写了 Matchmaking `0x15/0x8A` 的 `1,2,3,5,9,10,12,16` 任务 **8/8 已实现**。

### 6) 顺带更正一条旧结论

§13.4/13.5/13.7 说"`channel_push_body` 一发即断" —— 那几轮**同时**带着 replyId/seq 的 bug，
所以"断连"极可能全是 seq 病，**不能据此判 `channel_push_body` 死刑**。
两种信封候选：
- (A) 三方 / 我们现用：`08 service │ 0A senderId │ 10 name 00 │ 13 08 len data` —— 本轮实测**不断连**；
- (B) ol-mod `decodeChannelPush`：`u32(w=8/7) │ u64 senderId │ string name │ u64 channelId │ blob message │ u32 type`
  —— **字段序恰好等于客户端自己发 `11/4` 的顺序**（channelId → blob → type），结构上更自洽，**尚未测**。

### 7) 本轮结论

**"深挖 game-start 参数"这条路的答案是：大厅没有 game-start 参数可挖。**
两份能跑的参考里，开局都不由大厅触发。要真正"进对局"，只有两条：
① 走**靶场**那条已被三方验证的路（session + booking + 战斗服）；
② 复刻 ol-mod 的**独立房间/预约子系统**（工作量大，但 ol-mod 源码齐全）。

---

## 13.10 【2026-10-04】★ 靶场打通到战斗服 —— `battle_server.py` 按三方完整实现

### 13.10.1 本轮实测（`n10fr4.txt` / `lobby_srv.log` / `battle_srv.log`，开关 `session=True booking=True battle=True`）

**✅ booking 被接受（seq 修复的关键验证）**：
```
01:24:36 findSessions -> ★ 靶场 mission session 对象(单条, 270 字节, map=mp_shootingrange …)
01:24:36 6/14 命中 'mmbook' -> push 'mmbook accepted'(data=20)   → 0x85 推送 seq=72 (98 字节)
01:24:36 6/14 命中 'mmstart' (token='sv_resetServer;' …)          → 0x85 推送 seq=75 (98 字节)
```
客户端**不再每 5~15s 重发 mmbook**，而是直接推进到 mmstart → 进加载界面（截图确认：
"训练 靶场 … 等待连接…"）。**这是 seq 修复的实锤。**

**✅ 客户端开始连战斗服 —— `battle_srv.log` 收到 UDP 包**（此前一直是 0）：
```
RX #1..#50 peer=127.0.0.1:22011 len=16 hex=01 02 00 00 00 00 <clientTag(2)> 01 00 00 00 00 00 00 00
```
这 16B 包**就是 DTLS init** —— 与三方 `TryBuildInitAck` 的判据逐字段吻合
（`len==16 && [0]==1 && [1]==2 && u16@2==0 && u16@6!=0 && u64@8==1`）。
我们没回，所以客户端一直重试（tag 每 2~3s 换一次：`971b→bf60→aeb6→8fd7→aa28→73fa`）。

### 13.10.2 `battle_server.py` 已实现（逐条移植三方 C#，**自测全绿**）

| 环节 | 实现 | 自测 |
|---|---|---|
| NAT 遍历 | 29B type 13→12 | ✅（原有） |
| **DTLS init** | 16B → **38B cookie**（clientTag/serverTag/本机 IP:port/u64 1 + [10:14] 4B 签名） | ✅ 帧长 38 |
| **cookie+公钥** | 219B（`03 02 serverTag｜cookie(38B)｜…｜u64 1｜公钥(100B)`）→ ECDH → **114B ack** | ✅ 帧长 114 / [0:4]=`04 02 <serverTag>` / [106]=1 |
| **传输密钥** | ECDH **P-224**（纯 Python 实现，无第三方库）→ 共享 x **28B 大端** ‖ securityKey → **SHA1** → 24B | ✅ 双向推导一致 |
| 公钥编解码 | `30 <len> 03 02 07 00 02 01 1C <X> <Y>`（DER INTEGER，去前导 0/按需补 00） | ✅ 往返一致 |
| **数据帧** | `06 02 serverTag(2) seq(2) hmac(8) len(2) cipher`；AES 流（计数 = SHA1(seed)，seed=`seq,0,0,tag`）+ HMAC-SHA1 前 8B | ✅ 收发往返一致 |
| OOB 命令 | `0xFFFFFFFF + "getchallenge/connect/heartbeat/gamestateupdate/cancelConnect"` → 应答 | ✅ |
| **game state** | 读 `firingrange-gamestate.bin`(259B) → `u32 netchanSeq + state`，[8:] 按 `seq^1` 掩码 → SendData | ✅ |

**端到端联调**（起真实战斗服 + 模拟客户端走完整流程）：
```
1) init ack len=38 serverTag=7055
2) keyex ack len=114 ack[106]=1
3) 已发 gamestateupdate 6
4) 收到数据帧 seq=0 len=263 HMAC=True
   game state: netchanSeq=1 stateLen=259 前16B=00 00 00 00 03 00 00 00 00 63 6f 6f 70 5f 74 72
```
→ 解出的 state 里可读到 `coop_train_mp_firingrange` 等 cvar（与三方素材一致）。

**★ securityKey = 16 个 `0x01`**（不是 0）：C# 注释 *"Build 1649370's live security-key map
retained the 0x01 default for ID 1 despite the empty lobby blob (verified by v10 data MAC)"*。
`battle_security_key.txt` 当前是全 0 → `read_security_key()` 兜底返回 `01×16`（已实现）。

### 13.10.3 尚未实现（下一轮）

- **运动快照 / 输入回放**（`CodolMotionSnapshot` / `CodolClientCommandReader` / `CodolRangeEquipment`）
  —— 这是"能走动、能开枪"的部分；当前只推了初始 game state。
- 客户端收包后的实际表现待验（本轮尚未让真实客户端走完握手）。

---

## 13.11 【2026-10-04】★★ 踩坑: 21 个僵尸战斗服抢走了客户端的包

### 现象

`battle_server.py` 按三方实现完、自测全绿（§13.10.2）后，实机跑**还是"卡在等待连接"**，
而且 `battle_srv.log` 里新进程一直 `[stat] 收包=0`。
**但同一份日志里却出现了 `TX NAT_REPLY`** —— 而这行字符串**只存在于旧版骨架**
（新版的 NAT 分支不写日志）。→ 说明有**旧版战斗服还在跑**。

### 根因

```
netstat -ano -p UDP | Select-String ":28960"
→ 21 条, 21 个不同的 PID, 全是 python.exe
```
**`run_all.py` 的 `KILL_RE` 漏了 `battle_server.py`**：
```python
KILL_RE = r"fake_ied_https|fake_auth_https|fake_auth_tls|lobby_server\.py|fake_lobby\.py|nt10\.py|setup_auth8443"
#                                                                                          ↑ 没有 battle_server
```
于是 `free_ports()`（每轮 [1/5] 的清理）**从不杀战斗服**，而战斗服是常驻循环、永不退出。
跑了十几轮就累积出 21 个，**每个都绑在 UDP 127.0.0.1:28960**（原先设了 `SO_REUSEADDR`，
所以重复绑定不报错；Windows 把包投给最早那个 = 旧版骨架）→
**客户端的 DTLS init 全被旧版吃掉，新版永远 0 包** → 表现就是"卡在等待连接"。

> 注意：这些僵尸是**以管理员权限启动的**，非提权 shell 里 `Stop-Process` 一律
> `Access is denied`（`Get-CimInstance` 读到的 `CommandLine` 也是空串，容易误判"没有残留"）。
> **要在管理员 PowerShell 里清**——修好 KILL_RE 后，下一轮 `run_all.py` 自己就会清。

### 修法（两处）

1. `run_all.py`：`KILL_RE` 末尾加 `|battle_server\.py` → `free_ports()` 每轮自动清旧战斗服；
2. `battle_server.py`：**去掉 `SO_REUSEADDR`** → 端口被占时 `bind` 直接失败并打日志，
   不会再出现"两个战斗服都以为自己绑上了"的静默冲突。

### 教训

**"日志里出现了本不该存在的字符串"是定位脏进程的最快线索** ——
`TX_NAT_REPLY` 属于旧版本这一点，比对着 `[stat] 收包=0` 干着急有用得多。
另: `run_all.py` 的清理是**按脚本名白名单**（KILL_RE），**新增常驻服务时必须同步加进去**。

---

## 13.12 【2026-10-04】★ 真实客户端走完战斗服握手 —— 卡点变成 `stats`

### 13.12.1 实测（`n10fr6.txt` / `battle_srv.log`，清掉僵尸后的那一轮）

界面从"等待连接"变成 **"同步游戏设置"**，说明握手全过。日志逐条对上（`peer=127.0.0.1:22011`）：

```
RX #3  16B init             -> TX_DTLS_INIT_ACK 38B  (clientTag=4871 serverTag=11678)
RX #4  219B cookie+公钥     -> KEY_EXCHANGE_OK -> TX_DTLS_KEY_EXCHANGE_ACK 114B
RX #5  54B  -> RX_OOB 'getchallenge 0 "e7c8a98a6b4c2d0e"' -> TX_GAME_OOB 'challengeResponse 1'
RX #6  455B -> RX_OOB 'connect e7c8a98a6b4c2d0e "\name\QUNsaWVudA==\xuid\…\natType\3\ran…'
                              -> TX_GAME_OOB 'connectResponse'
之后: 客户端**每毫秒重发 'stats'**（44B / 1267B 交替）—— 我们没应答 -> 界面卡住 -> "服务器连接超时"
```

**★ 这条最有价值**：ECDH P-224、传输密钥派生、AES 流、HMAC-SHA1-8 **在真实客户端上全部验证通过**
（否则 `RX #5/#6` 解不出可读的 `getchallenge`/`connect`）。

### 13.12.2 从三方 `battle.log` 反推出的**完整正常顺序**（13:41/13:56/14:00 那几轮）

```
TX_GAME_OOB challengeResponse 1
TX_GAME_OOB connectResponse
TX_STAT_RESPONSE chunks=1/2 remaining=2      ← 客户端先传 index=0（1238B），再传 index=1（尾块）
TX_STAT_RESPONSE chunks=2/2 remaining=0
TX_GAME_OOB heartbeatresponse  ×N            ← 心跳保活
RX_CLIENT_GAME_HEADER messageAck=0 bytes=14  ← 客户端发首个 netchan 包（14B）
RX_GAMESTATE_PROGRESS stage=1 … stage=6      ← "同步游戏设置" 的进度就是它
（服务端在收到那个 14B 包后**只发一次** game state）
```

`stats` 的真实包形（三方日志里的明文）：
```
FF FF FF FF | "stats\0" | index(1B) | total(u16 LE) | <分块数据>
例: …73-00 | 01 | 2A-05 | B4-03-ED-40-…      (index=1, total=0x052A=1322)
```
服务端回 `statResponse <missing 位掩码>`（位 i = 第 i 块还缺；`0` = 传完）。

### 13.12.3 本轮实现（`battle_server.py`）

| 新增 | 说明 |
|---|---|
| `_handle_stats()` | 照抄三方 `stats\0` 分支：累计分块 → 回 `statResponse <missing>`；传完存 `firingrange-clientstats-last.bin`。**并打印 `len` 与三方公式期望值**，便于下轮核对 |
| `RX_GAME_OOB 'gamestateupdate'` | 按三方：`attempts>0` 时才置 `gamestate_loading`（停重试） |
| game state 触发 | 收到 **非 OOB 的 netchan 包**（len≥14）→ `ready=True` → 只发一次（`gamestate_sent`） |

**端到端自测（临时端口 28971，模拟客户端）**：
```
stats 单块 total=20        -> statResponse 0
stats 两块 total=1250      -> statResponse 2 → statResponse 0   ★ 与三方日志逐字一致
14B netchan 包             -> 收到 game state 259B，含 'firingrange' ✓
```

> ⚠️ 上轮日志里出现过一次 `[!] 绑定 127.0.0.1:28960 失败: OSError(10048)`，
> 说明清理**当时没把残留清干净**（可能是非管理员运行 → `taskkill` 被拒但静默）。
> 本轮已让 `kill_udp_owners()` **把每个 PID 的 taskkill 结果打印出来**，
> 且 `battle_server` 启动横幅加了 `pid=` —— 下次能一眼看出是谁在占端口。

### 13.12.4 下一轮判据

`battle_srv.log` 应依次出现：
`TX_STAT_RESPONSE chunks=1/2 remaining=2` → `chunks=2/2 remaining=0` →
`RX_CLIENT_GAME_HEADER … bytes=14` → `RX_GAMESTATE_PROGRESS stage=1…6` → `TX_GAMESTATE`，
客户端应从"同步游戏设置"**进入靶场**。
（再往后才是"能动/能开枪"那条线：`CodolMotionSnapshot` 快照 + `CodolClientCommandReader` 输入回放，尚未实现。）

---

## 13.13 【2026-10-04】★ stats 打通 → game state 下发 → 补上**运动快照**

### 13.13.1 实测（`n10fr7.txt` / `battle_srv.log`）—— 又前进一格

界面：`等待连接` → `同步游戏设置` → **`等待玩家数据`**。日志逐步全对：

```
01:47:03 16B init → INIT_ACK 38B ; 219B → KEY_EXCHANGE_OK → KEY_EXCHANGE_ACK 114B
01:47:04 getchallenge → challengeResponse 1
01:47:05 connect      → connectResponse
01:47:05 RX_STATS index=0 total=1252 count=2 len=1251(期望 1251) → TX_STAT_RESPONSE chunks=1/2 remaining=2
01:47:05 RX_STATS index=1 total=1252 count=2 len=27(期望 27)     → chunks=2/2 remaining=0  ★STATS_COMPLETE
01:47:05.. heartbeat → heartbeatresponse ×12
01:47:11 RX_CLIENT_GAME_HEADER messageAck=0 bytes=14 → TX_GAMESTATE seq=1 state=259B
01:47:11 RX_GAMESTATE_PROGRESS stage=1 … 6            ← "同步游戏设置"就是这个进度
01:47:13 起 RX_CLIENT_GAME_HEADER messageAck=1 bytes=44/46   ← 客户端开始发**用户命令**
之后 20 次 cancelConnect（等不到玩家数据 → 超时）
```
★ `len` 与三方公式期望值**逐条相符**（1251/27），`remaining=2 → 0` 与三方日志同形。

### 13.13.2 缺的是**运动快照**：`CodolMotionSnapshot`

"等待玩家数据"等的是每 25ms 一帧的玩家状态。已按三方源码**逐行移植**：

- `_BitWriter`：位流写入器。**反直觉的关键点**：`Bytes()` 把原始字段追加到 **Data 末尾**，
  而位指针 `bit` 不动；位流**只在字节对齐时 `bit = len(Data)*8`（跳到末尾）**。
  → 位流字节与原始字段是**交错**的，必须逐字节复刻，不能自行"补齐对齐"。
- `_build_motion_snapshot()`：空基线 + 无输入的默认玩家状态
  （`x=48, y=-572, z=-116`、默认武器 `1156/弹匣30/备弹90/弹键585`、`WeaponState=0`、事件全 0 …）。
- `pump_snapshot()`：`gamestateupdate 6` 后置 `snapshot_due=+0.5s`，此后**每 25ms** 一帧；
  载荷 = `u32 netchanSeq + state`，[8:] 按 `seq^1` 掩码（与 game state 同一套封装）。

**★ 长度校验（拿三方日志当参照物）**：
```
三方 battle.log 里 TX_SPAWN_EXPERIMENT 的 bytes 取值分布:  124×1062 / 42×795 / 138×638 …
**最后（最新）的那些全是 bytes=124 staticPosition=false**
本机 _build_motion_snapshot(0,1000,1000,first=True)  →  124 字节 ✓
```
> 注：日志早期那 29 条 `bytes=36` 是**旧版构造器**（日志里 `staticPosition=true`，而我们手上的源码写的是
> `staticPosition=false`，说明**源码比日志新**）—— 所以以 124 为准。

**端到端联调（临时端口）**：
```
game state 263B(=4+259) → 发 gamestateupdate 6 → 收到快照 seq=2/3/4 各 124B
   seq=2 第一帧: 00 00 00 00 | 00 | e8 03 00 00 | 00 08 …   (first=true)
   seq=3 起    : …              | 01 04 …                     (first=false)
★ seq 从 2 起（game state 已占用 seq=1），与三方日志 `sequence=2 … bytes=124` 完全一致
```

### 13.13.3 尚未实现

- **输入回放**（`CodolClientCommandReader.ReadInput` + `CodolRangeEquipment.Step`）：
  现在快照里位置恒为 `(48,-572,-116)`、`messageAck` 恒 0 → 玩家**能进靶场但走不动/开不了枪**。
  要"能动"需按三方的 `TryReadData` 解 netchan 体（`messageAck`/`reliableAck`/XOR 掩码/位流命令）。
- `CodolRangeEquipment` 的换背包/开火事件（`SelectBackpack` / `AddEvent`）。

### 13.13.4 下一轮判据

`battle_srv.log` 出现 `TX_SPAWN_EXPERIMENT … bytes=124`，客户端应从"等待玩家数据"**进入靶场场景**。

---

## 13.14 【2026-10-04】★★★ 进地图！靶场全链路打通

### 13.14.1 实测（`n10fr8.txt` / `battle_srv.log`）

**用户确认：进地图了。** 日志（本轮，`peer=127.0.0.1:22011`）：

```
01:53:27 TX_DTLS_INIT_ACK 38B ; KEY_EXCHANGE_OK → TX_DTLS_KEY_EXCHANGE_ACK 114B
01:53:28 STATS_COMPLETE total=1251            ← stats 全收，已存 firingrange-clientstats-last.bin
01:53:34 TX_GAMESTATE seq=1 state=259B
01:53:35 RX_GAMESTATE_PROGRESS stage=6
01:53:36 起 TX_SPAWN_EXPERIMENT seq=2/3/4/… bytes=124（日志每 40 帧一记；
          seq 到 601+ → 累计 600+ 帧，约 17 帧/秒）
→ 客户端进入靶场地图
```

**至此「登录 → 大厅 → 商城 → 靶场预订 → 战斗服握手 → stats → game state → 运动快照 → 进图」全线贯通。**

### 13.14.2 遗留：**进图了但走不动**

现象：能看、能转视角，但移动困难/像丢包。**已定位（未实现）**：

- 快照里玩家位置**恒为 `(48,-572,-116)`**、`messageAck` 恒 0 ——
  因为**没实现输入回放**：客户端发来的 44/46B netchan 包只被识别成 `RX_CLIENT_GAME_HEADER`，
  其 usercmd **没被解析、也没驱动位置**；
- 客户端本地预测往前、服务端每 25ms 又拽回原位 → 表现即"卡顿/丢包/走不动"；
- 另: 实测帧间隔 ~58ms（目标 25ms），也可能加重卡顿感。

要补（三方对应实现）：
`CodolClientCommandReader.Read/ReadInput`（120 行，含 `plain[4]^messageAck^1` 掩码）
+ `CodolRangeEquipment.Step` + 把 `ClientReliableAck/ProcessedInputTime/PlayerXYZ/PitchYawRoll`
接进 `_build_motion_snapshot()` + `InputBaselines` 基线表。

### 13.14.3 归档

- 成员面向文档：`E:\handoff\main\CODOL_FIRINGRANGE_20261004.md`（+`.zip`）
- 本文档：§13.1~§13.14 为完整流水

---

## 13.15 【2026-10-04】★ 输入回放落地 —— 靶场里能动了

### 13.15.1 移植了什么（全部逐行照抄三方）

| 模块 | 对应三方文件 | 说明 |
|---|---|---|
| `_MixedReader` / `_UserCommand` / `read_reliable` / `read_input` | `CodolClientCommandReader.cs` | netchan 体 → 可靠命令 + 用户命令；**两套游标交错**（`Bytes()` 走 cursor 不动 bit，`Bits()` 只在字节对齐时跳到 `cursor*8`） |
| `_Slot` / `_Equipment` | `CodolRangeEquipment.cs` | 默认背包 custom1（M4A1 1156/弹匣30/备弹90/弹键585）、换弹/开火/换背包/事件序列 |
| `handle_plain` 的 netchan 分支 | `CodolBattleServer.TryReadData` | 体 = `plain[13:]` 逐字节 XOR `(messageAck^1^plain[4])`；→ `Read` 可靠命令（换背包）→ `ReadInput` 用户命令 → **位置/视角/ADS/武器状态推进** |
| `pump_snapshot` | `SendPendingSnapshots` | 快照改用**实时**位置/视角/武器/事件；下发 `InputBaselines[seq]`；掩码逐字节混入 `ClientReliableCommand` |

移动公式（照抄）：`yaw = Yaw*2π/65536`；`vx=(cos·fwd+sin·right)*190*norm`、`vy=(sin·fwd-cos·right)*190*norm`；
`elapsed = min(Δtime, 200)`、`dt = elapsed/1000`；位置 **无碰撞**（三方也未实现）。

### 13.15.2 自测（全绿）

```
① 快照长度 = 124B              （回归：加了装备状态后仍是 124，与三方一致）
② read_reliable(b'\x02'+u32(7)+b'mr 1 1 custom2\0') → [(7,'mr 1 1 custom2')] ✓
③ read_input(手工 full 命令)   → count=1 time=5000 move=1 ✓
④ Equipment.step               → 不按键不开火(clip=30)；按开火键 → fired=True clip=29 state=6 event=1 ✓
⑤ 端到端（真实服务 + 手工 usercmd）:
   RX_USERCMD count=1 processedTime=5000 yaw=0 pos=86.0,-572.0,-116.0
   下一帧快照 pos=86.0          ← 48.0 + 190*0.2 = 86.0 ✓ 位置真的推进了
```

### 13.15.3 遗留

- 快照帧率实测 ~58ms（目标 25ms）；"手感卡顿"可能仍有残留。
- 无碰撞/无命中判定（三方同样如此）。
- 服务器不驱动 NPC/靶子（三方也没有）。
- 房间「准备」→ 开局、剧情模式仍待办（见 §13.9 / §13.13）。

---

## 13.16 【2026-10-04】★ 录像(demo)反推：容器格式已破，数据源确认可用

### 13.16.1 素材

`E:\使命召唤OL\使命召唤OL\main\demo\` 有 **31 个官方录像**（74 MB，2020-08 ~ 2021-08，即**关服前真机**录的）：
`*spy.demo`（观战）与 `*dm.demo`（对战）。客户端能正常播放（用户已确认）。
同目录在 `e:\codol tae\fixed_boot_chain_backup\main\demo\` 有副本。

### 13.16.2 容器格式（已用连续 seq 验证）

```
<opcode 1B> <seq u32 LE> <payload>
  opcode 1 -> payload = 以 NUL 结尾的文本命令
  opcode 2 -> payload = u16 LE 长度 + 数据
  opcode 3..6 -> 存在，格式未定（暂按 u16 长度处理）
```
实证链（同一段里连续 seq，铁证）：
```
02 | 02 00 00 00 | 06 00 | 25 d7 79 33 00 00
02 | 03 00 00 00 | 04 00 | 25 78 5b 27
02 | 04 00 00 00 | 06 00 | 25 d9 c9 29 00 00
02 | 06 00 00 00 | 12 00 | 25 db 99 2f 00 27 0b 75 5d ce 6d b7 5f f3 8b 88 a9 1a
01 | 11 00 00 00 | "d 2494 120074\0"
01 | 15 00 00 00 | "f \"MP_CONNECTED…"
01 | 16 00 00 00 | "s ui_DMKillScore \"50\""
01 | 17 00 00 00 | "S 1214"      01 | 18 00 00 00 | "9 ready 0"
```
- 首帧 = `02 | 01 00 00 00 | a3 0b | …`（seq=1，len=2979）= **初始 gamestate**（就是实体世界的起点）。
- **op=2 的载荷里还内嵌着同样的文本帧**（例：seq=17 载荷里直接出现 `f "MP_CONNECTED`、
  seq=18 里出现 `d 2535 þ…þ`）。

### 13.16.3 已确认能拿到什么

| 内容 | 证据 |
|---|---|
| **资源/实体名表** | 明文可见 `mp_killhouse_sh`、`weapon_mp_tabun_projectile`、`viewmodel_tac_knife`、`mp_trophy_system_*`、`props`、`animtrees`、`explosions`… |
| **官方下行命令流** | `d <idx> <val>`（配置串/实体字段）、`s <cvar> "<val>"`、`f "MP_CONNECTED`、`S <n>`、`9 ready 0`、`d 670 <hex…> 3 0` |
| **二进制快照流** | op=2 的 2979B 初始 gamestate + 后续每帧 100~1700B |
| 字符串编码 | **base64 的 UTF-8**（`5LiW`=世、`5L2z`=你），与实时客户端 `\name\QUNsaWVudA==` 同款 |

### 13.16.4 尚不确定（下一步要做的）

1. **op 3..6 的载荷格式**（当前靠 resync 兜底，会漏帧）—— 需要再看几种形态；
2. **块级空隙**：连续链会在某些位置断掉（首帧后就有 2 个多余字节 `ee d1`，
   且"载荷后下一字节"最常见是 `05`），说明文件是**分块**的（块头/块尾未定）；
3. op=2 载荷的**内层头**（观测到 11 字节前缀，如 `00 00 01 00 00 00 01 4d 00 00 00`）——
   疑似 netchan 头（我们的实时侧是 13B：`u32 seq | u8 serverId | u32 messageAck | u32 reliableAck`）；
4. **实体记录解码**：拿到初始 gamestate 后，用我们已写好的"字段索引 + 位流"读取器
   （`CodolMotionSnapshot` 的逆过程）逐个解实体 —— 这才是"靶子/实体名册"的来源。

### 13.16.5 工具

`demo_parse.py`（已提交到工作目录）：
```powershell
python demo_parse.py <某个.demo>              # 摘要：帧数/opcode 分布/文本命令/二进制帧
python demo_parse.py <某个.demo> --text       # 导出全部文本命令
python demo_parse.py <某个.demo> --bin 目录   # 导出 op=2 载荷，供后续按实体解码
```
实测 `C-2021-8-31[11-50-10]dm.demo`：73 帧 / seq 1..123 / opcode `{1:33, 2:39, 5:1}`。

### 13.16.6 ★ 结论（回答"能否靠录像补上碰撞/命中/靶子"）

| 想要 | 录像能给吗 | 说明 |
|---|---|---|
| **靶子/实体名册** | ✅ **能** | 初始 gamestate + 每帧快照就是官方实体流；这正是我们快照"只有本地玩家"缺的那一半 |
| **命中/伤害事件** | 🟡 **部分能** | 伤害/击杀以命令形式出现在文本流里；但**射线命中判定本身在客户端**（客户端用地图+实体包围盒做 raycast），只要实体下发正确，客户端自己就会出命中反馈 |
| **移动/惯性/武器逻辑** | ✅ 能（参考） | 每帧实体字段（速度/朝向/状态）都在 |
| **碰撞几何** | ❌ **不能** | 碰撞来自地图数据（`.ff`/BSP），不在录像里。要让"服务器位置也带碰撞"，要么移植地图碰撞，要么别让服务器覆盖客户端预测 |

---

## 13.17 【2026-10-04】碰撞侦察：地图数据在哪、以及**不要自己写 BSP**

### 13.17.1 地图数据的位置（磁盘上找不到 `*.ff`）

- `E:\使命召唤OL\使命召唤OL\main\` 下**只有** `demo/`(31 个 .demo) 与 `video/`(49 个 .bk2) —— 没有地图。
- 地图全在 **`E:\使命召唤OL\使命召唤OL\IIPS\IIPSDownload\*.ifs`**：**974 个 .ifs / 22.7 GB**。
  靶场相关：
  ```
  ff_init_asym_addon_mp_firingrange_V13.ifs        1.1 MB   ← 靶场(非对称/训练)
  ff_init_coop_survival_mp_firingrange_V15.ifs     1.6 MB
  ff_dlc19_mp_clash_killhouse_sh_V34.ifs           8.8 MB
  ff_init_common_gametype_coop_V55.ifs            31.6 MB
  …（ff_*.ifs 命名规则 = FastFile + 版本号）
  ```

### 13.17.2 `.ifs` = `nifs` 容器 + **加密的 FastFile**

```
偏移 0   : "nifs" 魔术 + 一组 u32（含各段大小/偏移）
偏移 283 : "IWff0100"  + u32 0x1CD(=461, 版本) + flags …  ← FastFile 头
其后     : 高熵数据（前 200KB 熵 = 8.00 bits/byte → 压缩或加密）
内含路径串: "client_shipRetail/chinese/asym_addon_mp_firingrange.ff"
          "ff_init_asym_addon_mp_firingrange.lst"
```
**zlib 直接解不开**（试过 wbits 15/-15/47/31 全失败）→ 是 CODOL 自己的加密/压缩。
→ 想自己解 BSP 碰撞，**前置条件是先把 FF 解出来**（member1 做过"层一 `.ff` 全量解密"，
明文在其 `number1/CODOLServer.zip` 的 `_cleanout\ff_layer1\`）。

### 13.17.3 ★ 但更好的路：**复用引擎原生碰撞**（ol-mod 就是这么干的）

ol-mod（`E:\handoff2\ol-mod-olfinal.zip`）的 `src/game_server/` 里**已经有碰撞与命中**，
而且关键是 —— 它们**不是重写 BSP，而是调用游戏引擎原生的 Pmove/trace**：

| 文件 | 作用 |
|---|---|
| `server_mp/sv_collision_mp.cpp/.hpp` | 服务器侧碰撞 |
| **`NativePmoveBindings.cpp`** | **调用引擎原生 Pmove**（玩家移动/贴墙/落地的真正实现） |
| `EngineBindings.cpp` | 引擎函数绑定（trace 等） |
| `server_mp/sv_bullet_mp.cpp` | 子弹/命中判定（101 处 trace/碰撞引用） |
| `server_mp/sv_snapshot_mp.cpp` | 快照构造（210 处 → 完整实体名册，远超我们那个"只有本地玩家"的 124B） |
| `server_mp/sv_const_baselines_mp.cpp` | 常量基线表 |

→ 结论：**碰撞与命中判定都不需要我们自己写，也不需要解 BSP** ——
   正解是**调用游戏自己已经加载好的引擎函数**（客户端里现成就有）。
   我们的 `nt10.py` 本来就在往游戏进程注入代码，具备做这件事的基础。

### 13.17.4 三条可行路线

| 路线 | 做法 | 优点 | 代价 |
|---|---|---|---|
| **A. 复用引擎（推荐）** | 在 nt10 注入里加一个 `trace/pmove` 导出；战斗服经 IPC 调用游戏引擎的原生函数 | 与官方逐字节一致；不用解 BSP | 要先定位客户端的 trace/Pmove 地址与结构体布局（ol-mod 源码里有线索） |
| B. 自己解 BSP | 先解密 FF（member1 成果）→ 解析碰撞 lump（brush/plane/node）→ 自己实现 trace | 自包含、不依赖运行时 | 工作量大（解密 + BSP 解析 + 碰撞算法） |
| C. 暂不对撞 | 保持现状（服务器位置无碰撞） | 0 成本 | 进墙/卡墙问题一直在 |

---

## 13.18 【2026-10-04】★ 路线 A 的具体规格：客户端原生 trace 的地址与调用约定（已到手）

ol-mod（同一 build **1649370**）的 `src/game_server/EngineBindings.cpp` 里把客户端关键函数
的**地址 + 字节签名 + 调用约定**都写下来了。以下全部来自其源码注释，**不是猜的**。

### 13.18.1 客户端通用 trace —— `sub_46E780`（碰撞查询的正主）

```
地址 : VA 0x0046E780        （= 模块基址 + 0x6E780）
签名 :
  void __usercall sub_46E780(
      float  *end           @<ecx>,
      Bounds *bounds        @<edx>,     // 6 个 float = {mins[3], maxs[3]}
      trace_t *results,                 // 栈参数 1
      float  *start,                    // 栈参数 2
      int     passEntityNum,            // 栈参数 3
      int     contentMask,              // 栈参数 4
      unsigned __int8,                  // 栈参数 5
      char)                             // 栈参数 6
  // 共 6 个栈参数, **caller 清 0x18**(24 字节, 类 cdecl)
★ 判分支依据(来自其反编译): `*a3`(trace_t 首 float = fraction) 与 0.0 比较 →
  a3 就是 trace_t;  `a2[3]+a2[4]+a2[5] == 0.0` 走 **point-trace** 分支 → a2 是 6 float 的 Bounds。
```
- **trace_t = 0x28 字节**，布局（`NativeTraceResult`，其源码有 static_assert）：
  | 偏移 | 类型 | 字段 |
  |---|---|---|
  | 0x00 | f32 | fraction |
  | 0x04 | f32×3 | normal[3] |
  | 0x10 | u32 | surfaceFlags |
  | 0x14 | u32 | contents |
  | 0x18 | u32 | hitType |
  | 0x1C | u16 | hitId |
  | 0x1E | u16 | modelIndex |
  | 0x20 | u16 | partName |
  | 0x22 | u16 | partGroup |
  | 0x24 | u8 | allSolid |
  | 0x25 | u8 | startSolid |
  | 0x26 | u8 | walkable |
  | 0x27 | u8 | unknownEnd |

### 13.18.2 其它已定位的客户端函数（同 build 1649370）

| 函数 | 地址/签名 | 用途 |
|---|---|---|
| `PmoveSingle` | 字节签名 `55 8B EC 81 EC 64 01 00 00`（`push ebp; mov ebp,esp; sub esp,0x164`） | 原生玩家移动（贴墙/落地/坡度） |
| 客户端 trace→实体 | VA `0x0046E6D0` | "此 build 没有服务端孪生体"（ol-mod 注释） |
| `AngleVectors` | `55 8B EC 83 EC 10 D9 EE 53` | 角度→向量 |
| `AnglesToQuaternion` | `55 8B EC 83 EC 34 D9 46 04` | |
| `MatrixMultiply` | `55 8B EC 8B 4D 08 D9 01 D8` | |
| `AxisToAngles` | `55 8B EC 83 EC 28 56 57 8B` | |
| `PMSetPitchValues` | `55 8B EC 83 EC 28 A1 40 F2` | |
| `BG_AnimParseAnimScript` | VA `0x00409040`（首指令 `0x0040905E`） | |
| `CharacterSelectionResolve` | `CODOL_CharacterCustomization_ResolveSelectionIds` VA `0x0040CA30` | |

> 关键前提已满足：**ol-mod 标注的这些地址就是 `CODDIFF(1649370)` 下核对过的**，
> 而我们的客户端 SHA256 `3699…B537` / build **1649370** 与之同款。

### 13.18.3 落地方式（路线 A 的实施步骤）

1. **注入侧（`nt10.py` 已有注入基建）**：在游戏进程里放一段桩代码 ——
   从共享缓冲读请求（start/mins/maxs/end/contentMask），按上面的 `__usercall` 调用 `0x46E780`，
   把 0x28 字节 `trace_t` 写回共享缓冲。
   ⚠️ 注意：`end@ecx / bounds@edx` 是**寄存器传参**，`results` 等 6 个走栈且 **caller 清栈**；
   Python 侧要用 `ctypes` 造一个符合该约定的调用桩（或直接写一小段机器码）。
2. **共享缓冲**：最简可用**内存映射文件**（`CreateFileMappingW`+`MapViewOfFile` —— 客户端本来就
   在跑这几个 API，`nt10.py` 的 hooks 里已有它们）。
3. **战斗服侧（`battle_server.py`）**：把现在"直接积分位置"的几行换成：
   `trace(playerPos, ±16 的 Bounds, 下一步位置, contentMask=MASK_PLAYERSOLID)` →
   按 `fraction` 截断位置（并据 `normal`/`surfaceFlags` 处理贴墙、`startSolid` 处理卡住）。
4. **验证**：先写个最小自测 —— 注入后请求一条"从 A 到 B"的 trace，拿回 fraction/normal，
   与游戏内肉眼/已知墙体位置对比。

> 备选（若注入路线受阻）：先用 ol-mod 的 `sv_collision_mp.cpp` + `NativePmoveBindings.cpp`
> 作为算法参考，自己按同样方式实现 trace（仍然依赖引擎的 BSP，不必自己解 .ifs）。

### 13.18.4 ⚠️ 关键约束：客户端被 **TenProtect 加壳**，地址只能运行时核对

用 `client_rva.py`（新工具）解析 `codoMP_client_shipRetail.exe` 的结果：

```
PE32, ImageBase = 0x400000, 大小 7.5 MB
节区: .tp3 / .tp3 / .tp3 / .tp3 / .tp3 / .tvm0 / .tp3     ← TP3(反外挂) + TVM(腾讯虚拟机)
按 ol-mod 签名核对: PmoveSingle RVA 0x19FD8 实测 0c 93 29 0f bd 00 00 00 57 (期望 55 8b ec 81 ec …) ✗
                   其余 4 个签名在 .text 里也搜不到
```
→ **磁盘上的 exe 是加壳后的镜像，真实代码不在里面**。推论（对实施很重要）：
1. ol-mod 给的 RVA 仍可用，但必须**加载到真实模块基址上**（ASLR，不能假设 0x400000）；
2. **核对/调用都必须在游戏进程内做** —— 这正是 `nt10.py`（注入侧）的职责，
   外部进程读内存会被 TP 拦（我们的历史笔记里已经踩过这条）；
3. 所以路线 A 的第一步不是静态核对，而是**在 nt10 里加一段"运行时核对"**：
   取 `GetModuleHandle(exe)` 基址 → 读 `base+0x6E780` 前 9 字节 → 与 `55 8B EC …` 之类特征比对
   （若 ol-mod 给的 trace 无签名，就用"调用后行为正确"来验证）。
4. `client_rva.py` 保留为工具（RVA↔文件偏移、签名搜索），对**未加壳**的 dll/旧版仍有价值。

---

## 13.19 【2026-10-04】路线 A 已实现：`nt10.py --trace` 探针（复用引擎原生 trace）

### 13.19.1 改了什么

| 文件 | 改动 |
|---|---|
| `nt10.py` | 新增 `get_module_base()`（Toolhelp 取真实基址）、`build_trace_stub()`（手写 x86 桩）、`trace_probe_thread()`（探针线程）、CLI `--trace` |
| `run_all.py` | 新增 `--trace`，透传给 `nt10.py` |

**桩的数据区**（放在代码洞 `page + (len(apis)+7)*SLOT + 0x800`，与 KDF 的槽/数据不重叠）：
```
0x00 req_seq   0x04 done_seq   0x08 start[3]  0x14 end[3]
0x20 mins[3]   0x2C maxs[3]    0x38 passEntityNum  0x3C contentMask
0x40 arg5(u8)  0x44 arg6(char) 0x48 trace_t[0x28]
0x70 status(-1进行中/0完成)     0x74 module_base  0x78 func_addr
```
**桩的机器码**（capstone 逐条核对通过，60 字节）：
```asm
push ebx / mov ebx,<data> / mov [ebx+0x70],-1
push [ebx+0x44]  ; char        push [ebx+0x40]  ; u8
push [ebx+0x3c]  ; contentMask push [ebx+0x38]  ; passEntityNum
lea eax,[ebx+8]  ; start  -> push eax
lea eax,[ebx+0x48] ; results -> push eax
lea ecx,[ebx+0x14] ; end      @ecx
lea edx,[ebx+0x20] ; bounds   @edx
call dword [ebx+0x78]
add esp,0x18 / mov eax,[ebx] / mov [ebx+4],eax / mov [ebx+0x70],0 / pop ebx / ret
```
→ 完全符合 ol-mod 给的 `__usercall`（ecx=end, edx=bounds, 6 个栈参数, caller 清 0x18）。

### 13.19.2 探针怎么跑

- 启动后**每 10s 一轮、共 8 轮**（覆盖"地图加载完成"那一刻）；
- 每轮从**靶场默认出生点 `(48,-572,-116)`** 向 **±X/±Y/±Z 各 500 单位**做 6 条 trace
  （玩家包围盒 ±16，`contentMask=0xFFFFFFFF`、`passEntityNum=-1`）；
- 每条打印 `fraction / normal / surfaceFlags / contents / hitType / hitId / modelIndex / allSolid / startSolid / walkable`；
- 每轮汇总 `n/6 条命中几何`。
- **首次运行还会打印**：真实模块基址、`base+0x6E780` 的**运行时前 16 字节**、
  以及磁盘上同位置的 16 字节（两者不同 = 已解壳，说明跑的确实是真实代码）。

### 13.19.3 判据 / 风险

- ✅ 成功：6 条里**部分 `fraction<1`、部分 `=1`**，且命中那几条的 normal/surfaceFlags 合理 → 路线 A 可行；
- ⚠️ 风险1：`CreateRemoteThread` 是反外挂的经典检测点（我们只是**探针**，用几次；正式版应改为
  借已有的 API hook 触发，避免反复建线程）；
- ⚠️ 风险2：`contentMask`/`passEntityNum`/后两个未知参数取值我按常规给了
  `0xFFFFFFFF/-1/0/0` —— 若 6 条全是 `fraction=1`（打不到任何东西），就先调这三个参数再判失败；
- ⚠️ 风险3：若 `base+0x6E780` 处跑的还是加壳数据，会打印"该处全 0/像乱码" —— 那说明地址对不上
  （可能 ol-mod 的 RVA 对应的是**解壳后的重建镜像**），届时改用"按行为/签名搜索"来定位。

### 13.19.4 第一次实跑的教训：`--trace` 没透传到 nt10

首轮 `n10trace.txt` 里 **一条 `[TRACE]` 都没有**（KDF 正常、槽 14 也对）。
根因：`run_all.py` 的 `run_nt10_multi()` 在 **`clients<=1`** 时直接
`return run_nt10(secs, out, apis, retries)` —— **单客户端路径转调了另一个函数**，
而我最初只给"多客户端那条分支"加了 `--trace`。

修法：
1. `run_nt10()` 加 `trace=False` 形参，并在构造 cmd 时 `cmd.append("--trace")`；
2. `run_nt10_multi()` 转调时把 `trace` 传下去；
3. **`nt10.py` 启动即打印 `-- argv: …`** —— 以后"参数到底传进来没有"一眼可见，
   不用再靠"日志里少了一行"反推。

> 通用教训：**给 nt10 加开关时，run_all 里可能有不止一条构造命令行的路径**
> （`run_nt10` / `run_nt10_multi` / `run_nt8o`），要全部照到。

---

## 13.20 【2026-10-04】探针实跑：地址没错，但**目标区当时还没解壳**

### 13.20.1 第二次实跑（`n10trace2.txt`）

`-- argv: … --trace` **到位**了，探针也起来了：
```
-- [TRACE] 探针线程已启动 (槽 15, 每轮 6 条轴向 trace, 间隔 10s)
-- [TRACE] 模块基址=0x00400000 size=0xE659000  子函数 = base+0x6E780 = 0x0046E780
-- [TRACE] 运行时 base+0x6E780 前 16B = 49 00 11 8b 86 00 20 8b 15 80 00 00 18 08 60 41
-- [TRACE] (对比)磁盘 0x6E780 前 16B = 49 00 11 8b 86 00 20 8b 15 80 00 00 18 08 60 41
-- [TRACE] 桩写入 成功 (60 字节 @0x13FC0000)
  [TRACE] +X  无结果(status 未归零)   … 6 条全部同样
```
**两条硬信息**：
1. **运行时字节 == 磁盘字节** → `base+0x6E780` 当时**仍是加壳态**，不是真实代码 → 调用必然失败；
2. 对照组：同一轮里 `[dump] KDF label 引用段 -> 0xB9C000 … ★ 已解壳` ——
   说明 TP3 是**按区/按页解密**，`0xB9C000`（KDF 所在）解了，`0x46E780` 没解。

顺带确认 ol-mod 的常量（`EngineBindings.hpp`）：
```
TraceRva = 0x06E780   PmoveSingleRva = 0x01CB40
（另有 TraceRva = 0x06EA60 / 0x268220 / 0x268470 / 0x268560 → 多版本）
```
→ **地址本身没错**，缺的是"读取时机"。

### 13.20.2 本轮修掉的两个问题

| 问题 | 根因 | 修法 |
|---|---|---|
| **我的回归**：`mods_toolhelp` 里 `CloseHandle(snap)` 抛 `OverflowError: int too long to convert` | 我在 `get_module_base` 里**改了 nt10 全局 `k32` 的原型**（`CreateToolhelp32Snapshot.restype=HANDLE`），失败时返回 `0xFFFFFFFFFFFFFFFF`，而 `CloseHandle` 默认参数是 32 位 | 改用**私有实例** `k32v = WinDLL("kernel32")` 设原型，**绝不碰全局 `k32`** |
| 探针不管解壳状态就去调 | 一拍脑袋直接调 → 打进加壳数据 | 每轮**重新判定解壳状态**（`live != disk`），只在"已解壳"时才发起调用 |

### 13.20.3 新增：活内存签名扫描（定位真实地址）

`scan_code_signatures()`：用 `VirtualQueryEx` 遍历**可执行已提交区**（上限 96 MB），
按 ol-mod 的 6 个 9 字节签名现找函数。目的有两个：
- 判断代码区**到底解壳没有**；
- 若 `PmoveSingle` 实测 RVA ≠ ol-mod 的 `0x1CB40`，就按差值**修正 `TraceRva`**
  （日志会直接给出"TraceRva 应修正为 0x…"）。

### 13.20.4 探针现状

- 每 **20s** 一轮、共 **14 轮**（覆盖到 `--secs` 之后，确保能等到地图加载完成）；
- 状态字用 **canary 0xDEAD0001**：仍是 canary = 远程线程没跑；`-1` = 桩跑了但调用没返回（炸了）；`0` = 成功；
- 只有拿到**至少一条 `fraction<1`** 才判定"路线 A 成立"并打印 `★★`。

> ⚠️ 待观察：上一轮游戏在 t=108.2 以 `rc=0xFFFFFFFF` 退出 —— 有可能是打到加壳区的那几次调用
> 把游戏带崩了（也可能只是正常退出）。新版本已加"解壳门禁"，理论上不会再撞这个。

---

## 13.21 【2026-10-04】★★ 路线 A 关键验证通过：**地址正确 + 解壳时机摸清**

### 13.21.1 第三次实跑（`n10trace3.txt`）——两条硬结论

**① ol-mod 的 `TraceRva = 0x6E780` 在我们客户端上完全正确。**
第 1 轮读到的还是磁盘加壳字节；**第 2 轮（t≈20s）起**变成真实函数序言：
```
第 1 轮 t=0s : 49 00 11 8b 86 00 20 8b 15 80 00 00 18 08 60 41   ← 加壳态
第 2 轮 t=20s: 55 8b ec 83 e4 f8 81 ec cc 00 00 00 a1 40 f2 e3   ← 真码!
               push ebp; mov ebp,esp; and esp,-8; sub esp,0xCC; mov eax,[0xE3F240]
```
→ **TP3 大约在 20s 内把该区解出来**。之前失败纯粹是"读早了"。

**② 调用能成功，但 `CreateRemoteThread` 这条路极不稳定。**
```
第7轮 t=168s: [TRACE] +X  fraction=1.0000 normal=(0,0,0) surf=0x0 …   ← 真的调通了
              [TRACE] -X/+Y/-Y/+Z/-Z  无结果 —— 桩没跑(canary 未动)
其余各轮 6/6 全部 "桩没跑(canary 未动)"
```
- 约 84 次尝试里**只有 1 次**桩真正执行 → `CreateRemoteThread` 基本被 TP3 拦掉（反向推测：
  TP 对"外部建线程"有检测）；canary 没动说明线程根本没跑到我们第一条指令；
- 唯一成功那次返回 `fraction=1.0`（该方向确实空旷），**还不足以判定碰撞可用**。

### 13.21.2 结论 / 下一步

- ✅ **地址与结构体规格都对**（`TraceRva`、`__usercall`、`trace_t=0x28`）—— 这条路值得继续；
- ❌ **执行方式要换**：不能用"外部 `CreateRemoteThread`"，改成
  **借我们已有的 API hook（游戏线程内）来触发** —— `nt10.py` 的 `build_tramp()`
  已经给 `sendto` 等装了跳板，在那个跳板里加一小段"若有请求待处理，就 pushad/pushfd →
  call trace 桩 → popfd/popad"，既不建线程、又天然跑在游戏线程里（靶场里客户端
  每秒往战斗服发 ~20 个包，触发频率足够）。
  需要在数据区加一个 `pending` 字节（请求就绪标志），跑完由桩清掉。
- ⚠️ 游戏仍在 t≈178s 以 `rc=0xFFFFFFFF` 退出 —— 与"打到加壳区"已无关（第 2 轮起就是真码了），
  更可能是**反复 `CreateRemoteThread` 触发 TP** 的结果；换触发方式后应一并消失。

---

## 13.22 【2026-10-04】改用**游戏线程内执行**（借 sendto 跳板）—— 不再建线程

### 13.22.1 改动

| 位置 | 改动 |
|---|---|
| `build_trace_stub()` | 入口**立刻清 `PENDING`**（防重入：trace 内部若再走到被 hook 的 API 不会再调一次） |
| trace 数据区 | 新增 `TR_PENDING = 0x7C`（u8），`TR_DATA_LEN` 0x7C→0x80 |
| `build_tramp()` | 新增可选参数 `trace_pending` / `trace_work`：在**恢复游戏寄存器之后**插入守卫块 |
| hook 安装处 | 只给 **`sendto`** 传这两个地址（靶场里客户端每秒往战斗服发 ~20 个包，频率足够） |
| `trace_probe_thread()` | **删掉 `CreateRemoteThread`**，改成：写请求 → 单独写 `PENDING=1`（近似原子）→ 轮询 `done_seq`（等 ~3s） |

守卫块（插在每个 API 跳板里，**跑在游戏线程**）：
```asm
pushfd / pushad
mov eax, <pending>
cmp byte [eax], 0
je  skip
call <trace_work>        ; ← 我们的桩
skip:
popad / popfd
```
> 为什么放在"恢复寄存器之后、偷来的指令之前"：`pushad/pushfd` 把游戏寄存器原样保住，
> 桩里那次 `call` 想怎么污染 eax/ecx/edx 都无所谓。

### 13.22.2 capstone 逐条核对（通过）

```
桩(64B): push ebx / mov ebx,data / mov byte [ebx+0x7c],0 / mov [ebx+0x70],-1
         push [ebx+0x44] [ebx+0x40] [ebx+0x3c] [ebx+0x38]
         lea eax,[ebx+8]→push / lea eax,[ebx+0x48]→push
         lea ecx,[ebx+0x14] / lea edx,[ebx+0x20]
         call [ebx+0x78] / add esp,0x18
         mov eax,[ebx] / mov [ebx+4],eax / mov [ebx+0x70],0 / pop ebx / ret
跳板尾部: … pop esi/edx/ecx/eax / inc [count]
         pushfd / pushal / mov eax,[pending] / cmp byte [eax],0 / je +5
         call 0x12340000   ← 目标正是桩(修掉过一次 off-by-one: rel 基址应为 E8偏移+5)
         popal / popfd / nop×5 / jmp <back>
```

### 13.22.3 判据

`battle_srv.log` 不受影响；看 **nt10 日志**（`n10trace4.txt`）：
- `-- [TRACE] 已把 trace 执行挂到 sendto 跳板 (pending=… work=…)` —— 挂载成功；
- `-- [TRACE] 第 N 轮 … 解壳判定=已解壳` → 随后应出现**成片的** `[TRACE] ±X/±Y/±Z fraction=…`
  （不再只有 1/84 的概率）；
- 若出现 `pending 一直没被取` → 说明那段时间 `sendto` 没被调用（还没进战斗服/大厅阶段）；
- 若出现 `pending 被取了但没回结果` → 桩跑了但 trace 调用炸了（参数/约定问题，下一步再调）。

> 顺带：不再建线程后，TP 的那个检测点绕开了，"游戏在 t≈178s 退出"应一并消失。

---

## 13.23 【2026-10-04】触发器挂错 API：游戏发包用的是 **WSASendTo**，不是 sendto

### 13.23.1 第四次实跑（`n10trace4.txt`）

```
-- hook sendto @0x75DB6160 偷5字节
  [t= 7.1s] sendto  累计命中 2  目标=114.222.112.81:8081
=== sendto 被调用 2 次 ===
```
**整轮 `sendto` 只被调用 2 次** → 跳板几乎不触发 → `pending 一直没被取`（14 轮 × 6 条全这样）。
所以游戏发包（含战斗服 UDP）用的是 **`WSASendTo`**，我们的默认 `--apis` 里**没有它**。

（同一轮里战斗服是正常的：`TX_DTLS_INIT_ACK` / `TX_SPAWN_EXPERIMENT` 都在 —— 说明客户端确实在发包，
只是没走 `sendto`。）

### 13.23.2 修法

1. `nt10.py`：新增 `TRACE_TRIGGER_APIS = ("WSASendTo", "sendto", "send", "WSASend")`，
   trace 挂到**这些**里先被 hook 的那个（`TRAMP_APIS` 本来就支持 `WSASendTo`/`send`）；
2. `run_all.py`：默认 `--apis` 加上 **`WSASendTo` 与 `send`**（否则连 hook 都不会装）。

### 13.23.3 关于"很严重的卡顿丢包感"

**这不是网络丢包** —— 是**缺碰撞导致的"橡皮筋"**：
服务端快照的位置是"直接积分 usercmd"（穿墙、无阻挡），客户端本地预测用的是**地图真实碰撞**；
两者每帧不一致 → 客户端被反复拉回 → 手感就是"卡顿 + 丢包"。
**这正是本轮 trace 要解决的东西**（拿到真实碰撞后，服务端位置就跟客户端预测一致了）。

> ⚠️ 附带风险：trace 现在跑在**发包线程**里（`WSASendTo` 跳板）。一次只允许一个请求（`pending` 单标志），
> 且探针是临时的；将来正式接入战斗服时，应把 trace 限频（例如每帧最多 1 次）而不是每次发包都做。

---

## 13.24 【2026-10-04】触发器再修：游戏**收发都不走** sendto/WSASendTo → 改挂**接收侧**

### 13.24.1 第五次实跑（`n10trace5.txt`）的 API 命中表

```
=== sendto     被调用 2 次 ===
=== WSASendTo  被调用 0 次 ===      ← 上一轮我刚加的那个，压根没被调用
=== send       被调用 1 次 ===
=== connect    被调用 2 次 ===
（与此同时战斗服日志里 TX_DTLS_INIT_ACK / TX_SPAWN_EXPERIMENT 都正常）
```
→ 客户端往战斗服发的 UDP，**既不是 `sendto` 也不是 `WSASendTo`**（很可能是 `WSASend` 走已连接套接字，
或走了别的封装；`TRAMP_APIS` 目前没有 `WSASend`）。

**但它一定在"收"** —— 战斗服每秒推 ~17 帧快照。而 `TRAMP_APIS` 支持接收侧：
`recv` / `recvfrom` / `WSARecv` / `WSARecvFrom`。

### 13.24.2 修法

1. `nt10.py`：`TRACE_TRIGGER_APIS` 改为
   `("recvfrom","WSARecvFrom","recv","WSARecv","WSASendTo","sendto","send")` —— **接收侧优先**，
   这是最稳的"高频游戏线程入口"；
2. `run_all.py`：默认 `--apis` 再加 `recvfrom,WSARecvFrom,recv,WSARecv`。

槽位自检（`len(apis)=14`）：KDF 槽 **20**、TRACE 槽 **21**、总槽 **22**（`page` 按 `len(apis)+8` 申请）→ 不冲突；
7 个触发器 API 全部在 `TRAMP_APIS` 里（无缺失）。

### 13.24.3 判据

`n10trace6.txt` 里应看到：
- `-- hook recvfrom @…` / `recvfrom 累计命中` 快速增长（这就是"游戏在收包"的直接证据）；
- 随后成片的 `[TRACE] ±X/±Y/±Z fraction=… normal=(…) surf=0x…`。

> ⚠️ 仍未解决的疑点：**trace 的调用约定/参数是否真对**。到目前为止一次都没真正跑过，
> 所以 `contentMask`/`passEntityNum`/后两个未知参数取值都还是"按常规猜的"，
> 等第一次真正调用返回后再看 fraction 是否合理。

---

## 13.25 【2026-10-04】⚠️ 我的一次冒进把游戏搞卡死了 —— 已回退到可用基线

### 13.25.1 第六次实跑（`n10trace6.txt`）的现象

- 游戏**起来了**（`game pid=31432`），但**卡死**：KDF hook **命中 0 次**（连 /auth/ 握手都没发生）、
  `[ready] [0x08269774]=00 00 00 00 … 5E8=None` 一直不变、日志到 t≈36s 后只剩这行在刷；
- trace 依旧没跑：`pending 一直没被取`（接收侧也基本没被调用，`WSARecv 累计命中 1`）；
- 战斗服 `bind 127.0.0.1:28960 失败: OSError(10048)`；
- 用户 Ctrl+C 中断（`KeyboardInterrupt`）。

### 13.25.2 我的错在哪

上一轮我把 **4 个接收类 API（`recvfrom`/`WSARecvFrom`/`recv`/`WSARecv`）直接加进了
`run_all.py` 的默认 `--apis`**。它们与 `MapViewOfFile` 不同 —— 是**网络热路径**，
给它们装"偷 5 字节 + 记录跳板"本身就有破坏风险（本次很可能就是它把游戏网络搞卡死）。

**修法（已改）**：
1. `run_all.py` 默认 `--apis` **回退到原样**（`OpenFileMappingW,CreateFileMappingW,MapViewOfFile,
   connect,sendto,WinHttpConnect,WinHttpOpenRequest,WinHttpSendRequest,z1,z2`）；
2. 触发器改由 **`nt10.py` 在 `--trace` 时自己追加**（`if a.trace: for nm in TRACE_TRIGGER_APIS: …`）
   —— 于是"不带 `--trace` 的日常跑"与之前**完全一致**，不再有新增风险。

### 13.25.3 顺手修掉的真 bug

- `watch_dialogs` 里 `W.LPARM` → **`W.LPARAM`**（`ctypes.wintypes` 没有 `LPARM`）——
  这个 `AttributeError` **每轮都在抛**，弹窗监听线程一直是死的。现在修好了；
- `kill_udp_owners()`：查不到占用者时**打印原始 netstat**，用来区分
  "netstat 没查到" vs "查到了没杀成"（这次就是"没查到，但 bind 仍失败"）。

### 13.25.4 下一步：先恢复基线，再决定 trace

**第一步（必须）**：跑一次**不带 `--trace`** 的，确认基线恢复正常：
```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --out n10base2.txt
```
> 这一步是为了确认"卡死"是我加的热路径 hook 造成的、而不是设备/环境的偶发。

**第二步**：查清"游戏到底用哪个 API 收发 UDP"。目前 `sendto=2 / WSASendTo=0 / send=1 /
WSARecv=1` 全都不像 —— 说明它可能走 `mswsock` / 更低层，或由 TenProxy 之类代理转发。
在没查清之前，**不要再往热路径上挂跳板**（这次已经证明代价很大）。

---

## 13.26 【2026-10-04】★ 换思路治"卡顿丢包感"：**让客户端自己说了算**（开关 `client_movement.on`）

### 13.26.1 基线恢复确认（`n10base2.txt`）+ 数据

用户确认"已恢复"，并做完整套操作（移动/射击/看录像/建房/点准备）。战斗服数据：
```
快照节奏: seq 2→41→81→121→161…  约 40 帧 / 2s ≈ 20 帧/秒（目标 25ms，实测 ~50ms）
RX_USERCMD: 位置与朝向确实在跟着变（pos=48→24.2→67.1→317.2→488.8，yaw 也在动）
```

### 13.26.2 诊断：**不是丢包，是"位置权威打架"**

- 服务端位置 = 按 usercmd **粗略积分**（速度恒定 190、对角 ×√0.5、**无碰撞**）；
- 客户端本地 = **真实 Pmove**（加速度/摩擦/坡度/真实碰撞）；
- 两者每帧不一致 → 客户端被反复拉回 → 手感就是"卡顿 + 丢包"。
要精确复刻只有引擎 Pmove/碰撞（trace 那条路），而那条路目前被"找不到触发 API"卡住。

### 13.26.3 换思路：**单人靶场不需要服务端权威**

这套实体编码是**增量语义** —— **不写某个字段 = 客户端保持原值**。
所以只要在**非首帧**里**省略位置/速度**（字段 8/10/11/13/14），客户端就会用它**自己的预测 + 真实碰撞**移动：

- 橡皮筋消失（服务端不再和它抢位置）；
- **碰撞自动就有了**（用的是地图真实碰撞，客户端本来就在跑）；
- 首帧仍照发（客户端要靠它建立基线）。

实现（`battle_server.py`）：
- `_build_motion_snapshot(..., omit_motion=False)`：为真时跳过那 5 个字段；
- 开关文件 **`client_movement.on`**（存在即生效，非首帧省略）；
- 自检：普通增量帧 **124B** → 省略后 **102B** ✓。

### 13.26.4 跑法 / 判据

```powershell
cd "e:\codol tae"; New-Item -ItemType File -Force client_movement.on
python .\run_all.py --secs 300 --out n10cm1.txt
```
判据：
- **卡顿/橡皮筋消失**，移动手感接近原生（因为就是客户端自己在动）；
- **能撞墙**（碰撞由客户端真实碰撞提供）；
- `battle_srv.log` 里 `TX_SPAWN_EXPERIMENT … bytes=102`（首帧仍是 124）。

> 取舍：服务端不再掌握玩家位置（对单人靶场无所谓）。将来若走通 trace/Pmove，删掉
> `client_movement.on` 即可切回服务端权威。

---

## 13.27 【2026-10-04】"客户端自己动"实验**失败** + 发现**出生点一直是错的**

### 13.27.1 实验结果（`n10cm1.txt`）

用户反馈：**无法移动**、可以开枪、**出生在一个正常到不了的屋顶**。

- **无法移动** → 说明客户端**需要服务端的实体位置更新才会动**（它没有free-run自己的预测，
  或者我们的 ack/时间字段让它一直等）→ "让客户端权威"这条路**走不通**，已删掉 `client_movement.on`；
- **出生在屋顶** → 暴露了一个更早的问题：**我们的出生坐标一直是错的**。

### 13.27.2 出生点为什么错

1. 三方 `Data/` 里那几个文件叫 **`firingrange-spawn-candidate.bin` / `-player-candidate.bin`** ——
   名字里就写着 **candidate（候选）**；解出来正是 `(48, -572, -116)`，
   与 `CodolLocalBattleServer.cs` 里 Association 的初值一样 → **这个值从来没被证实过**；
2. 更要紧的是**地图名不一致**：
   ```
   21/5 会话对象 : mp_shootingrange
   gamestate     : coop_train_mp_firingrange      ← 客户端实际加载的是这张
   ```
   坐标很可能属于另一张图，于是把人放到了屋顶。
3. 顺带看 `firingrange-gamestate.bin`：地图名后是 `cd cd f0 62 04 06 00 af`（`0xCDCD` 是
   MSVC 未初始化标记）—— 说明我们下发的 gamestate 里**有的字段是从内存快照里抄来的垃圾**，
   而 spawn/origin 并不在 gamestate 里（它是客户端从地图 spawn 点取的）。

### 13.27.3 新开关：`spawn_from_map.on`（连首帧也省略位置）

```
非首帧省略（client_movement.on）= 客户端仍被首帧钉在错坐标上 → 屋顶、且不能动
首帧也省略（spawn_from_map.on） = 客户端**保留地图自带 spawn**
```
自检：`omit_motion=True` 时首帧/后续帧都是 **102B**（都不含位置）✓。

**这一步只为一个问题**：验证"客户端到底会不会用地图自己的 spawn"。
- 若玩家**站在地上** → 证实"错的是我们的坐标"，而且地图里有可用 spawn；
  下一步就去**读客户端内存里的真实出生点**（`nt10` 已经在读游戏内存），
  拿到值后再照常下发（顺带也能拿客户端真实位置，一举解决"卡顿"）；
- 若仍悬空/更怪 → 说明客户端根本不认地图 spawn，坐标只能由服务端给。

### 13.27.4 跑法

```powershell
cd "e:\codol tae"; New-Item -ItemType File -Force spawn_from_map.on
python .\run_all.py --secs 300 --out n10spawn1.txt
```
判据：进靶场后**站在哪里**、能不能动；`battle_srv.log` 里 `TX_SPAWN_EXPERIMENT … bytes=102`。

---

## 13.28 【2026-10-04】★★★ 突破：`spawn_from_map.on` 一举解决**出生点 + 卡顿**

### 13.28.1 实测结果（用户确认）

> "**出生地正确，可以移动**无碰撞箱和交互，可以开枪无弹孔，移动逻辑是开局面向哪里 wasd 朝哪边，
> 动鼠标转向 wasd 还是按照开局面向走的，碰到斜坡墙壁就穿模"

且用户明确："**手感比之前好多了**"（上一版是"很严重的卡顿丢包感"）。

| 项 | 之前 | 现在 |
|---|---|---|
| 出生点 | ❌ 屋顶（`(48,-572,-116)` 这个未证实候选值） | ✅ **正确**（客户端用地图自带 spawn） |
| 移动 | 🟡 能走但**严重卡顿/橡皮筋** | ✅ **能走、不卡** |
| 碰撞 | ❌ | ❌ 仍穿墙/穿斜坡 |
| 交互/弹孔 | ❌ | ❌ |
| 移动朝向 | — | ❌ WASD 按**开局朝向**，转鼠标不改变移动基准 |

**结论：卡顿的根因就是"服务端那个错坐标每帧跟客户端抢位置"** ——
只要**不发布位置**（客户端用地图 spawn + 自己积分），橡皮筋与卡顿同时消失。

> ✅ **`spawn_from_map.on` 从此列为必开项**（见 §8 开关表）。
> 代价：服务端不再掌握玩家位置（单人靶场无妨）。

### 13.28.2 剩余两个症状（都指向"我们某个字段发错了"）

1. **WASD 按开局朝向** = 客户端跑 Pmove 时用的**视角基准被冻结**（相机在转、移动基准没更新）
   → 说明我们快照里某个**角度/状态字段**被当作权威，而我们发的是开局值；
2. **穿墙无碰撞** = 很可能 `pm_type` 一类字段被我们发成了"无碰撞"（PM_NOCLIP）。

### 13.28.3 下一步：**用录像逐字段对照**（用户已同意）

录像里是**官方服务器给真玩家的每帧字段值**。把本地玩家实体在录像里的字段
与我们 `_build_motion_snapshot` 发的**逐字段对照**，即可定位上面两个字段。
工具：`demo_parse.py`（容器已解）+ 需要一个**位流读取器**（`_BitWriter` 的逆）。

---

## 13.29 【2026-10-04】录像对照 第 1 步：**容器再下一层已破**

### 13.29.1 三个硬结果

1. **初始 gamestate 是 zlib 压缩的**（从载荷偏移 **6** 起）：
   ```
   op=2 payload(2979B) --zlib@6--> 7284 字节
   03 01 00 00 00 | "mp_killhouse_sh" 00 | "dm" 00 | 00 00 00 00 00 04 4c 01 af | "\2482\2\2485\12\…"
   ```
   解开后有 **300 个可打印串**，而且里面直接有**文本形式的数值表**，例如
   `'2130.399902 256.000000 24.000000'`（明显是**坐标三元组**）、
   `'475 9.9021e-05 95 130 130 0.209564 0 1 189 200 220 0.262241 …'`。
   → **官方 gamestate 里有大段"文本化的数值"，比二进制好解得多**。
   （已存 `e:\codol tae\_dm_init.gamestate`，7284B）
2. **只有初始那一条是 zlib**（39 条载荷里 1 条），其余是**嵌套帧容器**：
   ```
   02 <seq u32> <u16 len> [ 02 <seq2 u32> <u16 len2> <leaf…> ] …   ← op=2 的载荷里又是同样的帧
   ```
   叶子消息则形如 `00 00 01 00 | 00 00 01 38 | 00 00 00 | <payload>`，
   payload 里可能是文本命令（如 `f "MP_CONNECTED…`）或二进制。
3. **我们的 gamestate 头部与官方不一样**：
   ```
   官方: 03 01 00 00 00 <map> 00 <gametype> 00 <9B>
   我们: 00 00 00 00 03 00 00 00 00 <map> 00 <gametype> 00 <8B>   ← 三方手搓的近似, 且含 cd cd(未初始化)
   ```
   官方那份是 **7.2 KB / 300 串**，我们只有 **259 B**。

### 13.29.2 下一步（两条都可行，建议先做 a）

- **(a) 继续解"每帧实体记录"** → 直接拿到官方给本地玩家的字段值（`pm_type` / viewangles / 速度 …），
  定位"移动基准冻结"和"无碰撞"这两个字段。需要解出叶子消息的编码（下一步）。
- **(b) 换用官方的 gamestate 结构**（把 259B 近似换成"按官方结构生成"的版本，
  带上完整 configstring）—— 若"移动基准冻结/无碰撞"是某个 cvar/字段缺失导致的，这条能顺手修。

---

## 13.30 【2026-10-04】方案 (b)：gamestate 已按**官方布局**重建

### 13.30.1 官方 gamestate 的确切布局（从录像解压那份读出）

```
@0   03 01 00 00 00                       ← 5 字节头
@5   "mp_killhouse_sh" 00                 ← 地图名
@21  "dm" 00                              ← gametype
@24  00 00 00 00 00  04 4c 01 af          ← 9 字节
@33  "\2482\2\2485\12\2490\214\2491\0\3056\2\g_gametype\dm\g_hardcore\0\mapname\mp_killhouse_sh\
      scr_game_allowkillcam\1\scr_team_fftype\0"        ← configstring（只有 10 个键）
后面还有若干**文本化的数值表**（如 '2130.399902 256.000000 24.000000'），总计 7284B
```

### 13.30.2 ★ 意外但重要的发现：**我们的 configstring 与官方同构**

```
官方: \2482\2\2485\12\2490\214\2491\0\3056\2\g_gametype\dm\g_hardcore\0\mapname\mp_killhouse_sh\scr_game_allowkillcam\1\scr_team_fftype\0
我们: \2482\2\2485\1 \2490\214\2491\0\3056\2\g_gametype\coop\g_hardcore\0\mapname\coop_train_mp_firingrange\scr_game_allowkillcam\0\scr_team_fftype\0
```
只有 `2485` 的值与 `scr_game_allowkillcam` 不同 —— **三方那套本来就是从真抓包抄来的**。
所以 (b) 的"期望收益"其实很小：**差别只在头部那 14 字节**（我们是 `00000000 03000000 00`，
且夹着 `cd cd` 未初始化标记；官方是 `03 01 00 00 00`）。

### 13.30.3 已做的改动

`firingrange-gamestate.bin` 重建为**官方布局**（旧版备份为 `.bin.orig`）：
```
新(256B): 03 01 00 00 00 | "coop_train_mp_firingrange" 00 | "coop" 00
          | 00 00 00 00 00 | 04 06 00 af | <原 configstring 211B 原样>
```
（`04 06 00 af` 那 4 字节语义仍未解，保留三方那组——客户端已接受过。）

### 13.30.4 ★ 更重要的推论：两个症状**很可能不在 gamestate**

configstring 既然同构，那"移动基准冻结/无碰撞"就**不该**归因于 gamestate 缺 cvar。
结合症状（**相机在转、但 WASD 基准不动**），更合理的解释是：

> 客户端跑 Pmove 用的是**服务端权威的 viewangles**（来自我们的快照），
> 而我们写的字段 18/19（三方注释为 yaw/pitch）**很可能其实是"移动/期望角度"**，
> **真正的 viewangles 在我们从没写过的某个索引上** → 它一直保持出生值 → **基准被冻住** ✓

→ 要证实/定位**必须走 (a)**：解录像里本地玩家实体的每帧字段，看哪个索引跟着视角走。

### 13.30.5 ❌ 实测结果：**(b) 失败，已回退**

用户实测："**卡在设置游戏没进去，一会后服务器连接超时返回大厅**"。
→ 客户端**不接受**官方那套 5 字节头（`03 01 00 00 00`）的 gamestate。

**已立即回退**：`firingrange-gamestate.bin` 恢复为 **259B**（与 `.bin.orig` 逐字节一致）。
结论：三方那个"手搓头"（`00000000 03000000 00` + `cd cd f0 62 04 06 00 af`）
**虽然不真，但是客户端实际能过的形态** —— 官方的 gamestate 里应该还有我们没看懂的一层
（很可能它前面还有一层封装/长度，直接换头就对不上了）。

### 13.31 【2026-10-04】(a) 第 1 步：嵌套帧已能切

脚本实测（`demo_parse.py` + 递归切帧）：
```
顶层 73 帧 → op=2 载荷里再切出 36 个嵌套帧
  (深度1, op=2, 二进制) 22 个
  (深度1, op=2, 文本)    8 个
  op=2 载荷前有 6 字节小头(全 0), 需按偏移试切
叶子形态:
  小的 4~18B, 头字节多为 0x25: 25 d7 79 33 00 00 | 25 78 5b 27 | 25 db 99 2f 00 …
  大的为文本命令:  f "MP_CONNECTED… / d 2535 þ…þ
```
→ 下一步是把 `0x25` 开头的叶子解成"实体记录"（这才是拿到官方 viewangles/pm_type 的地方）。
**未验证**：这份录像是对战图(`mp_killhouse_sh`)，不是靶场；字段编码应通用，但取值不同。

### 13.31.1 实测规律（36 个深1叶子，`C-2021-8-31[11-50-10]dm.demo`）

```
seq=2  6B   25 d7 79 33 00 00
seq=3  4B   25 78 5b 27      ┐ 每隔一条出现，恒为 25 | u16 | 27
seq=5  4B   25 7a 63 27      │ u16 每次 **+0x802**（0x5B78→0x637A→0x6B7C→…）
seq=7  4B   25 7c 6b 27      │ → 周期性"时间/序号"，**不像实体增量**
seq=9  4B   25 7e 73 27      ┘
seq=6  18B  25 db 99 2f 00 | 27 0b | 75 5d ce 6d b7 5f f3 8b 88 a9 1a
seq=8  16B  25 dd 89 15 00 | 26 0b | 6d 69 69 64 4c 2a a2 a5 6a
seq=10 18B  25 df 89 36 00 | 47 24 b6 5d 16 1c 21 …
→ 16/18B 那批（`25 | … | u16(0x0B26/0x0B27) | 变长负载`）才是**候选实体记录**
```
- **0/36 是压缩**（raw deflate @off0/1/2 与 zlib 全试过）→ 排除压缩假设。
- 工具：`demo_parse.py --nested`（已并入正式工具，非临时脚本）。

### 13.31.2 ★ 发现的真障碍：**demo 流解析本身没走完整个文件**

对 31 个录像做普查（`parse_frames` + `parse_nested`）：

| 文件大小 | 顶层帧 | 深1叶子 | 大叶子(>40B) |
|---|---|---|---|
| 4.86 MB | 269 | 10 | 0 |
| 4.64 MB | 254 | 8 | 6 |
| 4.63 MB | 184 | **49** | 2 |
| 0.11 MB | 73 | 36 | 5 |

且小样本那份的解析备注就写着 **`无法再续 @51695`**（文件 114 KB）——
**即 `parse_frames` 只消费了文件的一部分就停了**。

→ **结论：在做任何"逐字段对照"之前，必须先把 demo 流解析补全**（跨整个文件定位帧边界，
而不是遇到一次对不上就停）。否则拿到的"叶子"只是开头一小段，统计没有意义。
这是**下一步的实际工作**，不是可选优化。

---

## 13.32 【2026-10-04】解析器补全（第 1 轮）：**找到"块"结构，但未覆盖完**

### 13.32.1 断点的真实结构（@51695）

```
51695: 00 40 45 00 40 8a 44 00 00 84 40 00 00 00 00 00     ← 含浮点(BE 3.078 / 4.32 或 LE 1106.0 / 4.125)
51743: 00 00 00 | 02 | 40 00 00 00 | 53 00 | ...             ← **op=2 seq=64 len=83：合法续帧**
52507: 01 02 ...  52531: 02 03 ...  52555: 03 04 ...          ← **seq=2,3,4 重新开始**
```
→ **录像由"块"组成，每块 seq 从 2 重新开始**，块间夹一小段头。
我们原来的判据 `last_seq < seq`（严格续帧）**永远匹配不上跨块** → 这就是 `无法再续` 的根因。

### 13.32.2 已改（`demo_parse.py`）

1. 抽出 `_frame_at()`（单帧解析）+ `_chain_ok()`（**能连走 3 帧**才算真帧头，防误判）；
2. 合法帧判据改为两种：**续帧**（`last_seq < seq <= last_seq+64`）**或新块**（`seq<=8` 且 `_chain_ok`）；
3. resync 窗口 4 KB → **256 KB**，同样要求 `_chain_ok`；
4. 返回值加 `gaps`（块间空隙），主流程打印**块数 / 空隙表 / 第一处空隙字节**。

### 13.32.3 效果与**仍未解决的部分**

```
修复前: 73 帧, 覆盖 ~20% 后 "无法再续 @51695"
修复后: 160 帧, 6 块, 5 处空隙, 但**仍只覆盖到 @48987（约 20%）**, 备注 "无法再续 @48987"
        空隙: (35786,15) (36880,589) (38672,1210) (40240,5327) (45664,2744)
        第 1 处空隙: ee d1 02 0e 00 00 00 42 06 00 00 00 00 00 00   ← 15B 块间头
```
**结论：还是没覆盖完**，而且空隙里出现了 **5.3 KB / 2.7 KB 的整段"非帧数据"** ——
说明除了"帧流"之外，demo 里还有**另一种容器**（很可能是每块的负载/索引，或实体数据）。

### 13.32.4 顺带发现的文件头（值得下一步解）

```
文件头 32B: 1d 00 00 00 | 04 00 00 00 | d6 00 00 00 | 00 00 00 00 | b9 79 f8 44 | 39 ea 02 cf | 00 00 00 00 | 05 00 00 00
             =29           =4            =214                          浮点 1980.3     ?
```
（`b9 79 f8 44` 作 LE 浮点 = **1980.3**，像时间/时长；`29/4/214/5` 像计数。）

**下一步**：解 ①15 字节块间头 ②文件头几个计数 ③大段空隙的容器格式
（CoD 类 demo 常在**文件尾部**放"关键帧索引表"，也要看一眼）。

### 13.32.5 ★ 又两条结构线索（尾部与空隙）

**① 文件尾部是"字符串表"**（不是索引表）：
```
114361: 00 15 00 | "ui_inventory_received" | f4 00 00 1d 00 00 00
114297: 98 00 01 00 30 | 99 00 01 00 31 | 9a 00 01 00 30 | 9b 00 01 00 30 | …（成对的小条目）
```
→ 尾部是**脚本/字符串表**（`ui_inventory_received` 这类），说明 demo 还存了 UI 脚本串。

**② 大段"空隙"里是与块头同款的结构**（所以它们其实也是块，只是帧布局不同）：
```
@40240 头: 00 40 1f 00 00 01 04 7f b4 48 6e a4 03 47 0e 00 00 c4 00 00 **40 45 00 00 84 40 00 40 8a 44** ae …
@45664 头: 00 04 29 00 00 01 04 47 e4 69 1a bc 3e 00 00 00 00 **40 45 b1 00 00 84 40 00 40 8a 44** …
@51695   : …                                                        **40 45 00 40 8a 44 00 00 84 40** …
```
→ 反复出现的浮点段（按 **大端**读 ≈ **2050.03 / 512.008**；按小端读 = 4.125 / 1106.0）。
**关键交叉印证**：`2050 = 0x802` —— **正是 §13.31.1 里 4 字节叶子那位 u16 的固定步长** ✓
→ 说明 demo 里存在一个 **2050 单位的时基**（很可能就是快照间隔）。

**小结**：demo = 文件头 + N 个"块"（块头含浮点时基）+ 尾部字符串表；帧只是块内的一种布局。
要 100% 覆盖还需解**块头 + 空隙内的另一种布局**。

### 13.32.6 ★ 块头已对齐（4/5 处同构）

```
@35786 (仅 15B): ee d1 02 0e 00 00 00 42 | 06 00 00 00 | 00 00 00        ← 后面直接就是帧
@36880: 00 84 1c 00 | 00 00 1c da 27 47 2e 8e 04 18 | 01 00 00 | b6 ea 51 5c 43 5f | 00 00 |
        **40 45 f7 40** | **00 00 84 40** | **00 40 8a 44** | dd 00 00
@38672: 00 b0 1d 00 | 00 00 1c da e7 47 4e 6e 03 b8 | 06 00 00 | da 5f 00 00 |
        **40 45 fb 40** | **00 00 84 40** | **00 40 8a 44** | ee …
@40240: 00 40 1f 00 | 00 01 04 7f b4 48 6e a4 03 47 | 0e 00 00 | c4 00 00 |
        **00 00 40 45** | **00 00 84 40** | **00 40 8a 44** | ae …
@45664: 00 04 29 00 | 00 01 04 47 e4 69 1a bc 3e 00 00 00 00 |
        **00 00 40 45** | **00 00 84 40** | **00 40 8a 44** | 00 00 00 00 | 0b 00 00 00
```
**核心发现**：每个块头里都有**三个连续浮点**，其中
```
第 1 个: 变(≈7.73 / 7.85 / 3072.0 / 3072.0)
第 2 个: 恒 = 4.125   (bytes 00 00 84 40, LE)
第 3 个: 恒 = 1106.0  (bytes 00 40 8a 44, LE)
```
→ 后两个是**常量**（不是坐标），更像是"尺度/默认值"。

**另一个关键点**：块头到该块首个真帧的距离**逐块不同**：
```
+15 / +589 / +1210 / +5327 / +2744
```
→ 块头与帧链之间有一段**变长区域**（这就是"空隙"），说明**每块内部还有第二种容器**
（很可能就是每块的负载/实体数据）。**这是要解的下一层。**

### 13.32.7 ★★ 第二容器已破：**"变长区域 = 长度前缀块序列 + 尾部索引"**

三个空隙的**尾部 24 字节**（结构完全一致）：
```
@36880(589B) 尾: … 00 b4 c2 00 00 00 00 00 00 00 00 02 | 0f 00 00 00 | bf 06 00 00 | 00 00 00 00
@38672(1210B)尾: … 00 b4 c2 00 00 00 00 00 00 00 00 02 | 11 00 00 00 | cf 01 00 00 | 01 00 00 00
@45664(2744B)尾: … 00 b4 c2 00 00 00 00 00 00 00 00 02 | 34 00 00 00 | b4 02 00 00 | 02 00 00 00
                                                         ↑ 02        ↑ u32 A       ↑ u32 B      ↑ u32 C
```
**决定性证据**：那两串 u32 的值
```
@36880: A=15,  B=1727
@38672: A=17,  B=463
@45664: A=52,  B=692
```
—— **`1727` 与 `463` 正是 §13.31 里那两个"大叶子"的字节数**（1727B / 463B）✓✓

→ **结论**：这段"空隙"其实是 **`<u32 长度> <数据>` 的块序列**（长度前缀块），
尾部带一个 **`02 + 各块长度` 的索引**。我们之前把这段当成"无法解析的垃圾"跳过去了。

**下一步**：按 `<u32 len><data>` 解这段区域的块（块内应就是实体/快照数据），
再把块与"帧流"的对应关系接起来。

### 13.32.8 ★ 区域内容实测：**不是长度序列，是"位打包数组 + 重复记录"**

把最小的那处（`@36880` 589B）整段倒出来后，直接看到三类结构：

```
偏移 352~447:  … 10 c0 **92 24 49** 92 24 49 92 24 49 … 49 92 24 49 10 40 92 24 49 … 
              ↑ **周期为 3 字节的重复位型**（1/3 占空比）→ 典型的**位数组**
偏移 448~511:  **f6 00 00 c0 40 17 71 54 5f ea 00 00 ea f6 00 00 c0**  (x2, c0/40 交替)
              ↑ **16 字节固定记录重复** → 定长记录数组
偏移 513~543:  fd 7f 91 f8 7f 00 05 01 00 00 00 00 00 00 |
              **40 45 00** … **8a 44** … **84 40** | 00 00 00 00 00 00 00 00
              ↑ **块头那三个浮点又出现一次**（区域尾部复现同样的指纹）
偏移 545~588: **84 1c 00 00** 00 00 00 00 00 00 **b4 c2 00 00** 00 00 00 00 00 00
              **02 | 0f 00 00 00 | bf 06 00 00 | 00 00 00 00**
              ↑ 区域尾部收尾（`02 + 两个长度 + 序号`）
```

**结论**：该区域 = **块头指纹** + **位打包数组/定长记录** + **同样的收尾指纹**；
里面的数据是**位级编码**（不是字节对齐的记录），要解必须补一个**位流读取器**
（正是我们 `_BitWriter` 的逆），再按"实体/字段索引"方案去认。

> 到这里"录像容器"还剩两层：①位打包数组的字段方案 ②尾部字符串表。
> 而这两层解完，才能拿到我们要的 **viewangles / `pm_type` 官方取值**。

---

## 13.33 【2026-10-04】★ 位流读取器完成（自测通过）+ **字段索引已解**（走参考产物，不再解容器）

### 13.33.1 位流读取器：**完成并证明是 `_BitWriter` 的严格逆**

`demo_parse.py` 新增 `_BitReader`（镜像 `battle_server._BitWriter`）。关键修正（第一版写错了）：
写侧 `bytes_()` 把原始字节**追加在数据末尾**、位游标**不动**；位流只在"字节对齐"时才
`bit = len(Data)*8` 并追加一个零字节（= 跳到末尾）。所以原始字节与位流是**按分配顺序交错**的，
读侧必须**分别跟踪两个游标**：`bit`（位游标 r）与 `n`（写侧已分配字节数 L）。
```
bits(n)  : 在 r 处读 n 位(LSB-first); 每当 r%8==0 → r = L*8; L += 1
raw(n)   : 读 D[base+L : base+L+n]（**不是**位游标处）; L += n
scalar(w): 1 位 present; 若 1 → 读 (w&7) 位低位 + (w//8) 个原始字节
index(prev): 1 位 → prev+1；否则循环读 4 位累加(遇 15 继续)
```
**证据（不依赖任何 demo 数据）**：`python demo_parse.py --selftest x.demo`
用 `battle_server._build_motion_snapshot` 真写入器建快照，再用读取器读回**逐字段比对**：
```
[selftest] omit=0 first=1 -> OK  字节=128  位=1016  读回字段=42
[selftest] omit=0 first=0 -> OK  字节=128  位=1016  读回字段=42
[selftest] omit=1 first=1 -> OK  字节=106  位=839   读回字段=37
[selftest] omit=1 first=0 -> OK  字节=106  位=839   读回字段=37
[selftest] 全部通过：读取器是 _BitWriter 的严格逆
```
> 顺带纠正：完整快照是 **128 字节**（不是以前记的 124）；省略位置/速度后 **106 字节**。
> （`--snap-at`/`--snap`/`--scan`/`--hex`/`--op2` 一并加进 `demo_parse.py`。）

### 13.33.2 ❌ demo 载荷**不是**我们这个快照格式（0 命中）

`--scan`（快照头签名 `d[o+4]==0 && d[o+11]==0x72 && d[o+12]==0x03`）在 114 KB 的
`C-2021-8-31[11-50-10]dm.demo` 上**命中 0 处**。`--op2` 也显示：op=2 载荷要么是
zlib（seq=1，2979B→7284B），要么是 **4~18 字节的小 delta**（`25 d7 79 33 00 00` /
`25 78 5b 27`…），远小于 128B 快照 → **demo 存的是"客户端已解码后的增量消息"，不是我们的
整帧快照字节**。所以"拿 demo 原字节喂读取器"这条路**不成立**，得换个数据源。

### 13.33.3 ★★ 换数据源：参考产物里**已经有解好的 demo 包**

在 `E:\handoff\success\codol\dist\launcher_src\tools\firingrange-v4-connection\` 下发现：
- **`demo-packet-1.bin` … `demo-packet-64.bin`** —— **已解码**的 demo 消息；
- `demo-initial-message.bin` / `demo-message-0.bin`（= 7284B，与 `demo-packet-1.bin` 同）；
- `demo-player-fields-trace.json`（**官方玩家字段解码 trace**）；`demo-configstrings.json`；
- `gameplay-playerstate.bin` / `viewmodel-playerstate.bin` 等 **原生结构 dump**。

**决定性验证**：`demo-packet-1.bin` 逐字节等于我们从 `.demo` 里 zlib 解出来的那份
（7284B，头 `03 01 00 00 00 "mp_killhouse_sh" 00 "dm" …`）= §13.29.1 的结果 ✓✓
→ **参考产物针对的就是同一份录像**，我们**不需要再解容器**（§13.31/13.32 那两层可以搁置）。

### 13.33.4 ★★★ 权威字段索引表（`demo-player-fields-trace.json`，真 demo 一次完整解码）

`offset` = 原生 `playerState` 偏移；`decoded` = 该次录像里的实际值：
```
idx  offset  codec   decoded       说明
 0    0x0    -97     861           commandTime            ← 我们发 ✓
 3    0x2c0  -16     591
 4    0x568  -70     3155          ← 我们**没发**
 7    0xdc   12      1526          ← 我们**没发**（= C# 注释里的 PS+0xDC field 7）
 8    0x30   -88     3072.0        x                      ← 我们发 ✓
 9    0x2bc  12      1037          ← 我们**没发**
10    0x38   -88     4.125         z                      ← 我们发 ✓
11    0x34   -88     1106.0        y                      ← 我们发 ✓
12    0x2c   8       0             ← 我们**没发**
13    0x40   -88     0.0           vy                     ← 我们发 ✓
14    0x3c   -88     0.0           vx                     ← 我们发 ✓
15    0x100  -8      0             ← 我们**没发**
16    0x44   -88     0.0           ← 我们**没发**
17    0x2cc  6       1             weapon_state           ← 我们发 ✓
18    0x164  -87     -90.0         **yaw**                ← 我们发 ✓（映射正确）
19    0x160  -87     0.0           **pitch**              ← 我们发 ✓
20    0xc    32      2048(0x800)   ADs/flags              ← 我们发 0x10（**值不同**）
29    0x168  -87     0.0           roll                   ← 我们发 ✓
30    0x298  -88     59.98×        ← 我们**没发**
34    0x170  -88     59.0          ← 我们发 60.0（**值不同**）
38    0x16c  -8      60            ← 我们发 ✓
39    0x3f8  11      1263          weapon                 ← 我们发 ✓
45    0xb8   -100    -90.0         **与 yaw 同值**         ← 我们**没发** ★头号嫌疑
47    0xc0   11      2046          ← 我们**没发**
54    0x10   -102    (value 10240=0x2800)                ← 我们发 0x1000（**值不同**）
57    0x4c   11      2047          ← 我们**没发**
58    0x2a8  0       59.98×        ← 我们**没发**
59    0x158  8       2             ← 我们**没发**
60    0xb0   16      190           移动速度                ← 我们发 ✓
61    0x1fc  16      2047          （无地面实体）           ← 我们发 ✓
63    0xa4   16      800           ← 我们发 ✓
64    0x6a8  0       —             ← 我们**没发**
```
交叉印证（`gameplay-playerstate.bin` 原生 dump，同一结构）：
`0x0=9032(commandTime)`、`0x4=0`、`0x8=0`、`0xc=0x10`、`0x30=48.0(x)`、`0x34=-572.0(y)`、
`0x38=-116.93(z)`、`0x44=-39.0`、`0xa4=800`、`0xb0=190`、`0xc0=2047` —— 与上表 offset **完全一致** ✓

**三处"值不同"+ 13 处"没发"**：
```
我们发     : 0,1,3,8,10,11,13,14,17,18,19,20,21,22,23,24,29,34,38,39,41,44,54,56,60,61,63,68,219
官方还发   : 4,7,9,12,15,16,30,45,47,57,58,59,64        ← 我们完全没有的 13 个字段
值不同     : 20(我们0x10 / 官方0x800)、34(我们60.0 / 官方59.0)、54(我们0x1000 / 官方0x2800)
```
> `0x4` 按经典 CoD 布局推断是 **`pm_type`**，官方 dump 里 = **0（PM_NORMAL）** —— 所以
> "穿墙"**不是** `pm_type` 被发成了 noclip（除非我们的 baseline 把它设成了别的值，下一步要查）。

### 13.33.5 结论 / 下一步（两个症状的头号嫌疑）

| 症状 | 最可能的字段 |
|---|---|
| **WASD 按开局朝向**（移动基准冻结） | **idx 45 @0xb8（float，值 = yaw）** —— 官方每帧都发、我们从没发过，client 一直用 baseline（出生朝向）✓ 症状完全对得上 |
| **穿墙/无碰撞** | idx 20 @0xc（flags，我们发 0x10 / 官方 0x800）、idx 54 @0x10（我们 0x1000 / 官方 0x2800）、以及没发的 12/15/16（含 `0x2c`/`0x100`/`0x44`）—— 需实测哪个是 `pm_flags` 类 |

**下一步（待用户点头再动手，属于改 `battle_server` 的实弹改动）**：
给 `_build_motion_snapshot` **补上官方多出来的 13 个字段**（先只加 idx 45 = yaw，做 A/B 最小验证：
若 WASD 立刻跟着鼠标走 → 命中），并把 20/34/54 的值改成官方实测值。改完实跑对照手感。

---

## 13.34 【2026-10-04】最小 A/B 已落盘：**只加 idx 45**，测 WASD 是否跟随鼠标

### 13.34.1 改动（`battle_server.py` `_build_motion_snapshot`）

在 idx 44 与 idx 54 之间插入（保持**升序**，否则 `index()` 的 skip 会算成负数）：
```python
_ydeg = (yaw & 0xFFFF)
if _ydeg >= 32768: _ydeg -= 65536
w.index(45, prev); w.bytes_(struct.pack("<f", _ydeg * (360.0 / 65536.0)))
```
- 值的口径取自 `camera-motion.json` 的实证：`input.angles=[52,64267,30]` → yaw 短整型
  `64267` 经 `×360/65536` = `-6.97°`，与同帧 `angles[1] = -6.9708` **完全吻合** ✓
- 编码先按**裸 f32**（与 idx 34 同款）试。若客户端**解析错位/掉线** → 说明 -100 codec 不是裸 f32，
  改成"presence 位 + f32"（同 idx 0 的 -97 口径）再试一次。

### 13.34.2 自检（已通过）

`demo_parse.py` 的读取器同步加了 idx 45 + 自测断言，自检通过：
```
[selftest] omit=0 first=1 -> OK  字节=131  位=1033  读回字段=43     ← 原 128
[selftest] omit=1 first=1 -> OK  字节=108  位=856   读回字段=38     ← 原 106
```
→ 快照长度 **128→131**（`spawn_from_map.on` 生效时 **106→108**）；`battle_srv.log` 里
`TX_SPAWN_EXPERIMENT … bytes=108` 就是"新字段已带上"的标志。

### 13.34.3 跑法 / 判据 / 回退

```powershell
cd "e:\codol tae"
# spawn_from_map.on 已在（必开项）；确认无残留游戏进程
python .\run_all.py --secs 300 --out n10idx45.txt
```
| 观察 | 结论 |
|---|---|
| **WASD 跟着鼠标走**（转身后 W 朝新朝向） | ✅ **命中** → idx 45 就是移动基准角，接着补齐其余 12 个字段 |
| 进不去/连接中断/花屏 | ❌ 编码猜错 → 换下一个候选编码 |
| 行为与之前**完全一样** | ❌ idx 45 不是移动基准 → 下一个嫌疑：idx 20/54 的 flags、或 idx 12/15/16 |

**回退**：删掉 `battle_server.py` 第 911-919 行那段插入（及 `demo_parse.py` 的 `45: "yawf"`）即可，
`git diff` 只有这一处。

### 13.34.4 ❌ 第 1 轮结果（编码=**裸 f32**）：客户端卡在"等待玩家数据"

用户反馈："**进入战斗服加载阶段，等待玩家数据**"（= 没进地图，回退到更早的阶段）。

`battle_srv.log` 的**决定性对比**（`Unknown snapshot baseline 1` 的出现密度）：
```
09:50:32 / 09:57:26 / 10:29:47   ← 各 1 次（正常加载噪声）
11:38:24 起                      ← **每秒 1 次、持续不断** → 客户端**一直没接受我们的快照**
```
→ 客户端 ack 停在 `1`（= 我们发的 gamestate 那个 seq），说明**后面的快照全被它丢弃了**
= **bit 流错位**（我们多写/少写了位数）。结论：**idx 45 的编码不是裸 f32**。

### 13.34.5 第 2 轮：编码改为 **2 字节 short 角**（本轮已落盘）

两条硬推理：
1. `playerstate-fields.json` 里 idx 34/41 的 codec = **-88**（= 裸 f32，我们一直是这么写的、
   客户端也接受）→ **idx 45 的 codec -100 ≠ -88，所以它不是裸 f32**；
2. idx 45 的原生偏移 **+0xB8**，而 **+0xB4/+0xB8/+0xBC** 是**三个连续 float**（= idx 70/45/191），
   与 viewangles 三元组 **+0x160/+0x164/+0x168**（= idx 19/18/29，codec -87）**完全同构**；
   而 viewangles 那组在线上用的就是 **2 字节 short 角**（`×360/65536`）。
→ 推断 idx 45 = **2 字节 short**：
```python
w.index(45, prev); w.bytes_(struct.pack("<H", yaw & 0xFFFF))
```
自检：快照 **131 B**（`spawn_from_map.on` 时 **108 B**）。

### 13.34.6 ❌ 第 2 轮结果（编码=**裸 short**）：**还是卡在"等待玩家数据"**

`battle_srv.log`：`TX_SPAWN_EXPERIMENT … bytes=104`（= 短整型版本确实跑了，比无 idx45 的 102 多 2），
但客户端 ack 仍恒为 `1`、`REJECT_USERCMD reason=Unknown snapshot baseline 1` 持续刷 → 仍错位。

→ **真宽度既不是 32 位、也不是 16 位**。

### 13.34.7 宽度实测：用 trace 的 per-field `cursor` 把"猜"变成"量"

`demo-player-fields-trace.json` 每个字段带 `cursor`（= 该字段读完后所在的**字节位置**）。校准：
```
已知 float 字段一律 +4:  idx 8→9, 10→11, 11→12, 13→14, 14→15   (全是 +4)
已知 1 字节:  idx 38→39 = +1
已知 2 字节:  idx 63→64 = +2  (scalar 16)
```
再看 idx 45：
```
idx 39 → idx 45 : +2
idx 45 → idx 47 : +3      ← 含 idx 47 自己的 index-skip 位
⇒ idx 45 整个字段（index-skip + 载荷）≤ 3 字节
```
**结论：idx 45 绝不可能是 4 字节 float**（无论带不带 presence 位）—— 一条很硬的排除。

### 13.34.8 第 3 轮：编码 = **1 位 presence + 2 字节 short**（本轮已落盘）

推理链：
```
真宽度 ≠ 32（第 1 轮失败）且 ≠ 16（第 2 轮失败）
+ cursor 实测 ≤ 3 字节 ⇒ 排除一切 4 字节 float（含 presence+f32 = 33 位）
⇒ 最契合"≤3 字节"且"非 16 位"的只有 **17 位** = 1 位 presence + 2 字节 short
   （17 bits ≈ 2.1 字节，正好落进 cursor 的 +2/+3 区间）
```
```python
w.index(45, prev); w.bits(1, 1); w.bytes_(struct.pack("<H", yaw & 0xFFFF))
```
自检：快照 **131 B**（`spawn_from_map.on` 时 **109 B**；battle_srv 实跑应显示 **≈105**）。
> 这一族（presence + 载荷）在我们已知的 writer 里就有：idx 0(-97: u32+presence)、
> idx 44(-16)/38(-8)（scalar = presence + 原始字节）—— 所以 idx 45(-100) 属于同一族完全说得通。

### 13.34.9 ⚠️ 第 3 轮结果（**presence + short，17 位**）：**进图了**，但状态更糟

用户反馈："**出生位置不对在屋顶上无法移动，视角也不对类似 360 度全范围转动（视角可以倾斜），
武器不在手上而是屏幕中间**"。

日志：`TX_SPAWN_EXPERIMENT … bytes=104`；**`RX_USERCMD` 有 942 条**、baseline 拒绝 2051 条
→ **客户端这次接受并解析了我们的快照**（前两轮是解析错位、卡在"等待玩家数据"，一条 usercmd 都没有）。

| 轮次 | idx 45 编码 | 客户端表现 |
|---|---|---|
| 1 | 裸 f32（32 位） | ❌ 卡"等待玩家数据"，ack 恒为 1（解析错位） |
| 2 | 裸 short（16 位） | ❌ 同上（解析错位） |
| 3 | **presence + short（17 位）** | ⚠️ **进图**，但屋顶/无法移动/**视角 360° 乱转**/武器在屏幕中间 |

**结论（三条）**：
1. **宽度确定了：17 位**（1 位 presence + 2 字节）—— 这是本轮最硬的收获；
2. 但**语义不是"移动基准角"**：把 yaw 填进去会让相机/视角整个乱掉
   （"可倾斜、360° 乱转、武器跑到屏幕中间"很像**抢了相机/自由视角一类的字段**）；
3. 因此 **WASD 按开局朝向 ≠ idx 45**，这条线**到此为止**。

### 13.34.10 处理：idx 45 改为**默认关**（开关 `idx45.on`），恢复可用基线

- `battle_server.py`：新增 `IDX45_FLAG = idx45.on`，**只在文件存在时**才发 idx 45；注释里记全三轮结论；
- 自检双态验证：
  ```
  无 idx45.on（= 基线）: 128 B / 106 B(omit)   ← 与 §13.27 可用基线一致 ✓
  有 idx45.on（实验态）: 131 B / 109 B(omit)   ✓
  ```
- **要复现实验**：`New-Item -ItemType File -Force idx45.on`；**要回基线**：删掉该文件即可。

**下一步方向（不再碰 idx 45）**：官方多出来的字段还有 **4 / 7 / 9 / 12 / 15 / 16 / 30 / 47 / 57 / 58 / 59 / 64**；
其中 idx 12(@0x2c)/15(@0x100)/16(@0x44) 有 `changeHint=3`（= 与"移动/位置"强相关），
是"移动基准/碰撞"的下一批嫌疑。要定位它们需要**离线精确解码** `demo-packet-*.bin`
（已确认是同一套索引/跳过编码，缺的就是这几项 codec）。

---

## 13.35 【2026-10-04】★ 基线复跑：**"出生点错误/无法移动"不是回归 —— 是客户端自己选的出生点踩雷了**

### 13.35.1 现象 vs 服务端证据（两者相反）

用户反馈："靶场里 **出生点错误**，但是视角恢复，能开枪**无法移动**，按 shift 有冲刺动画"。

服务端这一轮**完全健康**（`battle_srv.log` 本轮段，行 31344 起）：
```
TX_GAMESTATE            : 1        ← gamestate 正常下发
TX_SPAWN_EXPERIMENT 第1帧: bytes=102 pos=48.0,-572.0,-116.0 yaw=0   ← omit 模式正常（位置不发）
RX_USERCMD count        : 260      ← 客户端 260 条 usercmd **全被接受**
REJECT_USERCMD          : 0        ← 零拒绝
```
且代码与"出生地正确、能移动"那次**功能上完全一致**（idx 45 现在是**开关控制、默认关**，
自检 128 B/106 B 与 §13.27 基线一致）→ **不是 idx 45 的遗留影响，也不是代码回归**。

### 13.35.2 真正的原因：**这张图有几十个出生点，客户端自己挑**（可能挑到几何体里）

`loaded-map-entities.json` 里写着这就是靶场图：
```
"name": "maps/mp/coop_train_mp_firingrange.mapents"
```
把它的实体表（`loaded-map-entities-19.txt`）倒出来后：
```
info_player_start      angles "0 90 0"     origin "355 1371 0"        ← 唯一的"玩家起点"
mp_tdm_spawn_axis_start angles "0 180 0"   origin "2327.8 1400.8 -15"
mp_tdm_spawn (× 几十个)                     origin "872 996 -12" / "-300 974 -12" /
                                                    "-44 -387 -83" / "-742 -459 -84" / …
```
- 客户端在**这些 `mp_tdm_spawn` 里挑一个**当出生点。它们是为**对战图**摆的，
  在靶场这张图上**有的落在几何体/屋顶里** → 卡住；
- **卡在几何体里 = 走不动**（客户端 Pmove 被碰撞挡住），但**输入照常** → 所以
  "能开枪 / 按 shift 有冲刺动画 / 视角正常" ✓✓ 完全自洽；
- 也解释了之前"出生在屋顶"和这一次的差异：**每次挑到的点可能不同**。
- 顺带再次确认：我们那个老候选 `(48,-572,-116)` **不在**这张表的任何 spawn 里
  → §13.27 的判断（它是三方未证实的假值）**成立**。

### 13.35.3 结论与下一步：**必须由我们控制出生点**（不能再靠客户端挑）

`spawn_from_map.on`（= 完全不发位置、让客户端用地图 spawn）**不可靠** —— 它把出生点交给了一个
"在对战图 spawn 列表里随机挑"的逻辑。下一步二选一：

- **(A) 首帧发一个已知可站的坐标**（最省事）：关掉 `spawn_from_map.on`，首帧把位置填成
  `info_player_start`（`355 1371 0`）或某个 `mp_tdm_spawn`；地图表里有一整列候选可逐个试。
  坐标口径：线上 idx 8 = x、idx 10 = z、idx 11 = y（z 轴朝上，spawn 的 z 都是小数 ✓）。
- **(B) 读客户端内存里的真实出生点**：`nt10.py` 本来就能读游戏内存（§13.27.3 已提过），
  拿到后照发 —— 更准，但要动钩子。

建议先做 **(A)**（一行改动 + 一次实跑，且候选坐标现成）。

### 13.35.4 已落盘：`spawn_at.txt`（首帧指定出生点）

`battle_server.py` 新增：
```python
SPAWN_AT_FILE = spawn_at.txt      # 一行 "x y z"
def read_spawn_at(): ...          # 解析失败 / 文件不存在 → None
# pump_snapshot:
px, py, pz = assoc["pos_x"], assoc["pos_y"], assoc["pos_z"]
spawn_at = read_spawn_at()
if spawn_at is not None and not assoc["snapshot_sent"]:
    px, py, pz = spawn_at; omit = False        # 首帧发指定坐标，之后照常省略
```
- 启动日志新增两行，便于一眼确认本轮生效的是哪套：
  ```
  出生点: 首帧指定 (355.0, 1371.0, 0.0) (spawn_at.txt)   或   客户端自选（spawn_from_map.on）
  idx45 实验: 关
  ```
- `TX_SPAWN_EXPERIMENT` 行也加了 `omit=` 与首帧的 `spawn_at` 标记。
- **当前取值**：`spawn_at.txt = "355 1371 0"` = 该图唯一的 `info_player_start`（`angles "0 90 0"`）。
  坐标口径：第 1 个数 = x（idx 8）、第 2 个 = y（idx 11，水平）、第 3 个 = z（idx 10，**朝上**）。
- **换候选**：直接改 `spawn_at.txt`（地图表里还有几十个 `mp_tdm_spawn`，例如 `872 996 -12`、
  `-300 974 -12`、`-44 -387 -83`、`-742 -459 -84`…）；**回退**：删掉该文件即可。
- 语法 + 解析已验证：`py_compile` 通过；`read_spawn_at() = (355.0, 1371.0, 0.0)`。

---

## 13.36 【2026-10-04】国外团队提示："出生点也定义在地图的 `.ff` 里，让 AI 对照两边"

### 13.36.1 两边分别是什么

| 边 | 我们手上有没有 | 位置 |
|---|---|---|
| **地图 `.ff`（定义侧）** | ❌ **没有明文** | §13.17：地图只以 **加密 `.ifs`** 存在（`IIPS\IIPSDownload\ff_init_asym_addon_mp_firingrange_V13.ifs` 等 974 个 / 22.7 GB，`nifs` + `IWff0100`，zlib 解不开）；磁盘上 `**/*.ff` = **0 个** |
| **已加载实体表（运行侧）** | ✅ **有** | 参考产物 `...\firingrange-v4-connection\load-assets-21096\loaded-map-entities-19.txt`（10165 行，`"name": "maps/mp/coop_train_mp_firingrange.mapents"`）—— 这是参考工具**从运行中的游戏内存里读出来的**，等价于"`.ff` 被加载后的结果" |

→ **能做的对照**：把"运行侧"的出生点池整理出来（下面），并与**客户端实际落点**对照
（实际落点可从客户端内存读，见 §13.36.3）。

### 13.36.2 ★ 运行侧的出生点池（`loaded-map-entities-19.txt`，全量）

按 classname 统计（共 ~300 个出生点，**按游戏模式分池**）：
```
22  mp_tdm_spawn        22  mp_dm_spawn         11  mp_dd_spawn_defender
10  mp_dd_spawn_attacker 9  mp_sab_spawn_allies   9  mp_sab_spawn_axis
 9  mp_ctf_spawn_allies  9  mp_ctf_spawn_axis     9  mp_dd_spawn_*_start
 9  mp_tdm_spawn_allies_start / mp_tdm_spawn_axis_start / mp_dom_spawn ...
 6  mp_dom_spawn_flag_a  5  mp_dom_spawn_flag_c   1  worldspawn
 1  info_player_start                                                                  ← 唯一的"单人/训练起点"
```
关键坐标样本：
```
info_player_start            355 1371 0          ← 我当前放进 spawn_at.txt 的就是这个
mp_tdm_spawn (22 个)          872 996 -12 | -300 974 -12 | -44 -387 -83 | -742 -459 -84 |
                              1933 2316 -7 | 1093 919 -6.5 | 315.5 -513 -82 | 968 702 8 | …
mp_dm_spawn  (22 个)          872 996 3 | -300 974 5 | -44 -387 -75 | -739 -462 -75.5 | …
```

### 13.36.3 ★★ 池子里**混着明显非法的点**（这就是"出生点错误"的来源之一）

```
mp_tdm_spawn_allies_start   origin = 6932 5324 -867     ← 远在地图之外（正常范围 |x|,|y| < ~2700）
mp_dd_spawn_defender        origin = -3584 2448 -360    ← 同样离谱
```
而**同一 x,y 在不同模式下的 z 不一样**，说明 z 是"楼层高度"而不是随手填的：
```
(x,y)=(872,996) → mp_tdm_spawn z=-12，mp_dm_spawn z=+3
(x,y)=(-44,-387)→ mp_tdm_spawn z=-83，mp_dm_spawn z=-75
```
→ 客户端若挑到越界点/挑到别的模式池的点（比如我们的 gametype 是 `coop`、它却用了 `mp_tdm_spawn`），
就会出现在"正常到不了的地方"——与 §13.27"屋顶"、§13.35"卡住走不动"完全吻合。

> 顺带把老候选 `(48,-572,-116)` 也定位了：它落在 **z≈-83 那一层**的 spawn 群附近
> （`-44 -387 -83`、`-355 -328 -83`、`-742 -459 -84`、`315.5 -513 -82`），但 z 低了 ~33
> → **在地板下面**。三方那个 `(48,-572,-116)` 果然是错的。

### 13.36.4 结论 / 建议

1. **`.ff` 那一侧我们目前拿不到明文**（要等 member1 的 `ff_layer1` 或国外团队给地图 `.ff`）；
   现在能直接用的"定义侧"就是上面这张运行侧清单 —— 它本来就是 `.ff` 加载后的结果。
2. **真正该对照的是"清单 vs 客户端实际落点"**：客户端每局自己挑一个，我们看不到它挑了哪个。
   建议用 `nt10.py` 读客户端内存里的本地玩家 `origin`（偏移 **+0x30/+0x34/+0x38**，
   §13.34 的 `gameplay-playerstate.bin` 已确认过口径）→ 就能知道它落在哪、对应清单里哪一条。
3. 短期最省事：继续用 `spawn_at.txt` 逐个试清单里的**合法点**
   （首选 `info_player_start 355 1371 0`，因为我们的 gametype = `coop`，单人/训练起点最对症）。

---

## 13.37 【2026-10-04】已实现**读客户端本地 playerstate 的 origin**（`nt10.py --ps-probe`）

### 13.37.1 为什么能读（偏移已双重证实）

`playerstate-fields.json`（**原生内存偏移**表）+ `gameplay-playerstate.bin`（真实 dump 实证）：
```
+0x30 / +0x34 / +0x38   = origin 的 x / y / z        (float)
+0x160 / +0x164 / +0x168 = pitch / yaw / roll        (float)
+0xa4 = gravity(800)      +0xb0 = movementSpeed(190)
+0xc0 = cameraEntity(2047) +0x1fc = groundEntity(2047)
```
（`gameplay-playerstate.bin` 里 `0x30=48.0`、`0x34=-572.0`、`0xa4=800`、`0xb0=190`、`0xc0=2047` 全部对上 ✓）

### 13.37.2 实现（`nt10.py` 新增 3 个函数 + 1 个开关）

| 名称 | 作用 |
|---|---|
| `scan_playerstate_bases(h, maxtime, cap)` | 扫**私有可提交**内存：锚 = `+0xa4` 处 `800` 且 `+12` 处 `190`（备用判据 = `+0x1c` 与 `+0x158` 都是 `2047`），返回 playerstate 基址 |
| `read_playerstate(h, base)` | 按上表偏移读出 origin/角度/常量，返回 dict |
| `playerstate_probe_thread(...)` | 每 **3s** 一轮，找到就追加写 **`player_origin.txt`**，并打一行 `[PS] … origin=(x,y,z) yaw=… 距原点=…` |
| CLI `--ps-probe` | 开启上面的线程（`run_all.py` 也加了同名开关并透传到 nt10） |

落盘格式：
```
# nt10 playerstate 探针 pid=…
t=12.0 base=0x1A2B3C40 origin=872.00 996.00 -12.00 angles=0.000 66.600 0.000 commandTime=…
```
→ 拿到这行就能**和地图出生点清单逐条对**（`872 996 -12` 正是 `mp_tdm_spawn` 的一条）。

### 13.37.3 本轮实跑配置（让客户端**自己挑**，才好观察）

```
spawn_from_map.on   ← 在（客户端自选出生点 = 要观察的对象）
spawn_at.txt        ← 已停用（改名 spawn_at.txt.off），不干预
idx45.on            ← 不在（idx 45 实验关闭）
```
跑法：
```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --ps-probe --out n10ps1.txt
```
看点：nt10 日志里的 `-- [PS] playerstate 探针已启动` 与成片的 `[PS] … origin=(…)`；
以及 **`player_origin.txt`** 的内容。

---

## 13.38 【2026-10-04】★★ 对照 **v32 原启动器**（用户提示"v32 的位置是对的"）—— 找到它到底怎么做

### 13.38.1 v32 的 Data 目录（`dist\CODOL-Portable\Data\`）：答案在里面

| 文件 | 关键内容 |
|---|---|
| **`battle.log`（108 MB！）** | v32 战斗服的完整日志，**含它每帧的实际行为** |
| `firingrange-spawn-candidate.bin`（36 B） | 我解出来 = 一个真快照：`serverTime=1000`、`f0f1=00 08`(首帧)，里面就是 float **48.0 / -116.0 / -572.0** |
| `firingrange-player-candidate.bin`（42 B）/ `-posture-candidate.bin`（64 B）/ `-bootstrap.bin`（18 B） | v32 的其他实验载荷（我们没有） |
| `firingrange-battle.enabled` | 文本 = `"experimental NAT transport; battle simulation pending"` ← **它没做模拟** |
| `runtime\Run-Session.ps1`（18 KB） | v32 的会话脚本：只起 **auth(3074)+lsg(3074)**、打 4 个兼容补丁、读客户端阶段/显示状态；**战斗服不在这里** |

### 13.38.2 ★ battle.log 里的决定性证据

```
LISTEN endpoint=127.0.0.1:28960 mode=experimental-nat-only
TX_SPAWN_EXPERIMENT sequence=2 serverTime=1000 bytes=36 staticPosition=true
TX_SPAWN_EXPERIMENT sequence=3 serverTime=1263 bytes=36 staticPosition=true
…                                   （每帧都是同一份 36 字节）
RX_USERCMD count=1 processedTime=1497 yaw=0 position=48,-572,-116      ← 出生点 = 那个 candidate
RX_USERCMD count=32 processedTime=34531 yaw=65364 position=24.54,-278.73,-116
```
→ **v32 = `staticPosition=true`：每帧都发同一个固定点 `48 -572 -116`（36 字节极简快照），
且 "battle simulation pending"（不做真正的模拟）。** 而 `bytes` 分布显示它后来才演进到
`bytes=124/137/138`（带动态位置）。

**对比我们现状**：`spawn_from_map.on` 把位置**全省略**（探针实测客户端 playerstate 的
origin 真是 `0 0 0` —— 也就是说"省略"并没有让客户端去用地图 spawn，而是**留在原点**），
`spawn_at.txt` 又只发了首帧、还是我猜的 `355 1371 0` → **与 v32 恰好相反**。

### 13.38.3 已落盘：`static_spawn.on`（v32 等价模式）

```python
# pump_snapshot:
if spawn_at is not None and static_spawn:      # static_spawn.on 存在
    px, py, pz = spawn_at; omit = False        # ★ 每帧都用固定坐标（= v32 staticPosition=true）
elif spawn_at is not None and not assoc["snapshot_sent"]:
    px, py, pz = spawn_at; omit = False        # 只首帧
```
- 启动日志新增/改为可辨识的一行：
  `出生点: 每帧固定 (48.0, -572.0, -116.0) (static_spawn.on = v32 staticPosition)`
- `TX_SPAWN_EXPERIMENT` 行现在带 `staticPosition=true/false` 与 `omit=`，可直接和 v32 的日志逐行比。
- 本轮开关：`static_spawn.on` 在 + `spawn_at.txt = "48 -572 -116"`（= v32 实测值）；
  `spawn_from_map.on` 虽在，但会被 static 分支覆盖（`omit` 强制 False）。

跑法：
```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --ps-probe --out n10v32.txt
```
判据：进靶场后位置应与 v32 一致（`48 -572 -116`），且 `player_origin.txt` 里 origin
应变成 **(48, -572, -116)**（而不再是 `0 0 0`）—— 那就同时证明了偏移正确 + 位置被接纳。

---

## 13.39 【2026-10-04】★ `static_spawn` 实跑结果：**出生点确认正确**，但"钉人"导致拉回

### 13.39.1 用户反馈

> "**出生点正确**，移动还是按照初始帧，动视角不变，无法移动，有严重的卡顿丢包感，**服务器在拉回我的位置**"

### 13.39.2 三条结论（都是硬的）

1. ✅ **`48 -572 -116` 就是这张图正确的出生点** —— 之前 §13.27/§13.28 判它"错误/屋顶"是**误判**：
   当时"屋顶"其实是**服务端朴素积分漂移**（190 u/s、无碰撞）把位置带偏后客户端被拽过去造成的，
   不是坐标本身的问题。**这条要改口径。**
2. ✅ **v32 的 `staticPosition=true` 我们复现成功了** —— 出生点正确就是证明；
   但它必然带来"每帧钉在同一个点"→ 客户端一动就被拽回 → **"服务器在拉回我的位置"就来自这里**。
3. ❌ **"移动按初始帧 / 动视角不变"仍在** —— 这是独立的老问题（WASD 基准冻结），
   和钉不钉人是两件事，钉人只是把它的后果放大了（服务端用当前 yaw 算速度、客户端用冻结的基准走
   → 两者必然分叉 → 位置被拉回）。

### 13.39.3 本轮配置（修正为最优组合）：首帧给对坐标 + 其余帧省略

```
static_spawn.on  ← 已删除（不再钉人）
spawn_at.txt     ← "48 -572 -116"（第一帧发这个**正确**坐标）
spawn_from_map.on← 在（其余帧省略位置 → 客户端自己走，不和服务端抢）
```
→ 预期：**出生点正确 + 不被拉回**；此时再观察 WASD 基准问题就不会被"钉人"干扰。
`py_compile` 通过，`read_spawn_at()=(48.0,-572.0,-116.0)`、`static_spawn=False` ✓

跑法：
```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --ps-probe --out n10sp3.txt
```
判据：① 出生点仍正确；② 能自由移动、**不再有被拉回**；③ `player_origin.txt` 里 origin
应≈`(48,-572,-116)` 并随你走动而变化（这才是"偏移正确 + 位置被接纳 + 位置可读"的完整证明）。

---

## 13.40 【2026-10-04】★★ 关键结论：**客户端基本不做自主预测，它跟着服务端的位置走**

### 13.40.1 三次实跑的对照（用户反馈）

| 位置发送方式 | 出生点 | 能否移动 |
|---|---|---|
| **全省略**（`spawn_from_map.on`） | ❌ 不对（探针实测 origin=`0 0 0`） | ❌ **完全不能动** |
| **静态每帧**（`static_spawn.on` + `48 -572 -116`） | ✅ **正确** | 🟡 能动能开枪，但**被拽回**（"服务器在拉回我的位置"） |
| **只首帧 + 其余省略** | ❌ 不对 | ❌ **不能动** |

→ 三条并起来只有一个解释：**客户端的移动推进依赖服务端每帧下发的 `origin`**；
不发 → 它停在原点、动不了；发静态 → 它能动但被钉住；发动态 → 它跟着服务端走。

**所以正确模式 = v32 后期那种**：`staticPosition=false`、`bytes=124`、**每帧发动态位置**，
起点用已验证正确的 `48 -572 -116`。我们的默认模式本来就是它（`pos_*` 初值 = `48,-572,-116`）。

### 13.40.2 本轮配置 = 纯默认（还原成 v32 后期）

```
spawn_from_map.on  ← 停用（不再省略位置）
spawn_at.txt       ← 停用（不需要，pos_* 初值就是 48,-572,-116）
static_spawn.on    ← 不在
=> 每帧发服务端积分位置，omit=False
```
跑法：
```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --ps-probe --out n10sp4.txt
```
**这轮要重点看 `player_origin.txt`**（必须贴回来）：
- 若里面出现 **≈`(48,-572,-116)` 且随走动而变化** → 探针偏移证实、位置可读，
  下一步就能做 **"服务端把客户端真实 origin 原样回发"**（= 不让两者抢位置，彻底消掉拉回）；
- 若仍是 `0 0 0` → 说明我读的不是权威 playerstate（那 32 个是**每帧命令历史环**），
  需要换锚点重新定位。

---

## 13.41 【2026-10-04】★★★ 探针成功：**出生点 / 位置 / 朝向 三项全部核对通过**，剩下的是"物理"

### 13.41.1 用户反馈（纯默认模式）

> "**出生点正确了**，移动还是按照初始帧，动视角不变，**可以移动**，无碰撞等逻辑，动起来有卡顿和延迟感"

### 13.41.2 `player_origin.txt`（339 行，336 行非零）—— 探针彻底跑通

```
t=117.5 base=0x00159150 origin=48.00 -572.00 -116.00  angles=0.000 0.000 0.000    ← 出生点 ✓
t=124.8 base=0x1B4B0480 origin=154.68 -792.27 -116.00 angles=12.458 -100.607 0.000
t=161.2                 origin=-115.0 -713.7 -116.00  angles=…
t=260.9                 origin=2164.91 1067.52 -116.00
```
→ `+0x30/+0x34/+0x38` 就是 origin、`+0x160/+0x164/+0x168` 就是 pitch/yaw/roll，**偏移全对**；
位置与角度**随走动实时变化**。

### 13.41.3 服务端 vs 客户端**逐条对上**（这是本轮最硬的证据）

| 服务端 `processedTime` | 服务端解出的 yaw（换算成度） | 服务端积分的 pos | 探针读到的客户端 |
|---|---|---|---|
| 14475 | **-100.61°** | 142.2, -858.9 | **-100.607°** / 154.7, -792.3 |
| 39661 | **103.30°** | -130.5, -311.1 | **103.30°** / **-130.5, -311.1** |
| 42730 | **103.30°** | -180.1, -101.5 | **103.30°** / **-180.1, -101.5** |
| 68966 | **59.47°** | 2164.9, 1067.5 | 61.42° / **2164.9, 1067.5** |

并且把探针数据做"移动方向 vs yaw"统计后：`dir=yaw`（前进）、`dir=yaw-90`（横移）、
`dir=yaw-180`（后退）都有，**多行精确相等**（如 `dir=103.30 / yaw=103.30`）。
→ **yaw 解码正确、位置积分与客户端吻合、移动方向确实是相对"当前"视角的**。

### 13.41.4 结论：剩下的**不是**逻辑问题，是**物理保真度**

```
z 全程恒为 -116.00   ← 没有重力、没有碰撞、没有高低楼层；客户端是"纯跟随服务端位置"
```
因为客户端自己不跑 Pmove（它照着我们发的 `origin` 走），所以移动手感 = 我们的粗积分
（恒速 190、瞬时转向、无加速度/摩擦/重力）→ **卡顿 + 延迟感**；"无碰撞"也是同一原因。
**这正是 §13.17.4 那条路（复用引擎 Pmove/trace，ol-mod 的 `NativePmoveBindings`）要解决的。**

### 13.41.5 本轮新增：探针再读"是否愿意模拟"的字段（跑一次即可定性）

`read_playerstate()` 现在多读并落盘：
```
+0x04 pm_type   +0x08 pm_time   +0x0c pm_flags   +0x10 otherFlags
+0x14 linkFlags +0x2c f2c       （落盘格式：… commandTime=N pm=<type>/<flags>/<other> f2c=N）
```
判据：
- **`pm_type != 0`** → 客户端被置成了"旁观/无碰撞"一类模式 → 改这一个字段就可能让它自己跑 Pmove（**便宜**）；
- **`pm_type == 0` 但按空格跳时 z 仍恒为 -116** → 客户端**完全不模拟**，物理必须我们来做（**贵**，= §13.17.4）。

---

## 13.42 【2026-10-04】★ "移动延迟一两秒"的定位：**服务端位置是"跳着走"的**

### 13.42.1 用户的关键补充（本轮最重要的一句）

> "我视角转了，wasd 还是按照开局时那一帧的方向走，**并且按下去得过一两秒才会移动，延迟很大**"

### 13.42.2 `pm_type` / `pm_flags`：都是 0（不是旁观/无碰撞模式）

`player_origin.txt` 新格式：
```
t=120.7 base=0x00159150 origin=48.00 -572.00 -116.00 angles=18.314 -71.647 0.000 \
        commandTime=6528 pm=0/0/2771522575 f2c=0
```
- `pm_type = 0`（PM_NORMAL）、`pm_flags = 0` → **不是**被设成 spectator/noclip；
- `pm=0/0/<随机>` 里的第三个（otherFlags）读出**随机值** → 说明 `+0x10` 不是 otherFlags，
  **那个偏移我记错了**（不影响结论）。
→ 所以"让它自己跑 Pmove"不存在"改一个字段"的捷径。

### 13.42.3 ★ 真正的现象：服务端位置 7 秒一动不动（而输入一直在收）

```
13:04:09  pT=10231  pos=-804.3
13:04:10  pT=11014  pos=-804.3     ← pT 一直在推进（输入一直在收、一直在处理）
13:04:11  pT=11799  pos=-804.3
13:04:12  pT=12613  pos=-804.3
13:04:13  pT=13383  pos=-804.3
13:04:14  pT=14142  pos=-804.3
13:04:15  pT=15727  pos=-804.3
13:04:16  pT=16522  pos=-895.6     ← 7 秒里位置完全不动，然后跳 91 单位
```
而且**探针读到的客户端位置与它逐字相同**（探针 `t=124.3 origin=128.07 -804.25` ↔ 服务端 `-804.3`）
→ 客户端是**忠实跟随**我们发的 `origin` 的，所以用户感觉到的"延迟/卡顿"**就是**我们这边位置更新
"跳着走"造成的。

位置**只在解出的 `move` 位非 0 的那几条输入上才积分**（我们目前只按 4 个 `move` 位算 fwd/right）。
到底是"W 键位压根没解出来"还是"命令时间被 `elapsed` 夹到 200ms 而欠积分"，需要看**逐条输入日志**。

### 13.42.4 本轮新增：逐条输入日志（`log_inputs.on`）

`battle_server.py` 在输入循环里加了（由 `log_inputs.on` 开启，启动时判一次）：
```
IN time=<usercmd时间> dt=<毫秒> move=0x<键位位图> fwd=<±1/0> right=<±1/0> yaw=<原short> \
   pos=x,y,z vel=vx,vy
```
**跑法（这轮请严格照做，日志才好看）**：
```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --ps-probe --out n10in1.txt
```
进靶场后：**① 站住不动 3 秒 → ② 按住 W 3 秒 → ③ 松开站 3 秒 → ④ 按住 W 同时慢慢转鼠标 3 秒 → ⑤ 松开**。
然后就能从 `battle_srv.log` 直接量出"W 按下 → 位置开始动"的真实延迟，
以及"按住 W 时 `move` 位到底长什么样"。

---

## 13.43 【2026-10-04】★★★ 定位到"转 180° 只转 ~20°"：**我们回声 viewangles 把视角阻尼掉了**

### 13.43.1 逐条输入日志（17139 条）证明：**服务端方向 100% 正确**

对全部 `move != 0` 的输入算"移动方向 vs 该条的 yaw"（每 40 条取样）：
```
yaw=  4.04  move=1(前进)  dir=  4.05   dir-yaw=  0.00
yaw=-42.42  move=1        dir=-42.43   dir-yaw=  0.00
yaw=-71.25  move=1        dir=-71.25   dir-yaw=  0.00
yaw= 31.18  move=1        dir= 31.18   dir-yaw=  0.00
yaw= 44.33  move=8(右横移) dir=134.33   dir-yaw= 90.00
yaw=-77.28  move=4(左横移) dir=-167.28  dir-yaw=-90.00
yaw= 22.24  move=2(后退)   dir=-157.77  dir-yaw=180.00
```
→ **方向严格等于"当前" yaw**（横移 ±90、后退 180 全对）。而且按住 W 时位置**平滑推进**
（每 10ms 走 2.2 单位 = 220 u/s，`dt` 只有 7~21ms，没有被 200ms 夹断）。
**所以服务端这一侧没有"方向不跟手"的问题。**

### 13.43.2 那"转 180° 只转 20°"只剩一个解释：**视角本身只转了 ~20°**

机理（本轮的新假设，且与所有现象自洽）：
```
鼠标转 → 客户端算出新的 cl.viewangles → 生成 usercmd(带新 yaw)
       → 我们把它写回快照 idx 18/19 (viewangles)
       → 客户端又拿我们的值**覆盖**自己的 cl.viewangles
       → 等于每帧把鼠标增量拽回去一部分 ⇒ **阻尼** ⇒ 转 180° 只剩 ~20°
```
这同时解释了：
- 为什么"方向严格等于 yaw"——因为 yaw 就是那个被阻尼后的视角，两者自然一致；
- 为什么之前把 **idx 45** 写进去会**视角 360° 乱转**——那些字段确实在驱动相机。

### 13.43.3 本轮改动：`omit_viewangles.on`（不下发 idx 18/19/29）

增量语义下"**不写某字段 = 客户端保持原值**"，所以我们干脆**不发 viewangles**，
让客户端用它自己的（未被阻尼的）视角：
```python
if not _OMIT_VIEWANGLES:
    w.index(18, prev); …yaw…;  w.index(19, prev); …pitch…
…
if not _OMIT_VIEWANGLES:
    w.index(29, prev); …roll…
```
自检双态都通过：**关=128B / 开=122B**（omit 时 106B / 100B）。

**跑法**：
```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --ps-probe --out n10va1.txt
```
**关键判据**：这一轮"**探针读到的 yaw**"才是**真正的客户端视角**（不再是被我们覆盖的值），
所以：
1. **转 180°** → 若视角（和移动方向）**真的转 180°** → 假设成立，问题解决；
2. 若仍只转 ~20° → 说明阻尼不在我们这儿，转去查客户端自身的输入/灵敏度；
3. 顺便对比 `player_origin.txt` 里 yaw 的变化范围与服务端日志里的 yaw 范围是否一致。

---

## 13.44 【2026-10-04】"方向偏"的排查工具（`force_dir.txt` / `dir_bias.txt`）

### 13.44.1 ⚠️ 我的一次失误

§13.43 末尾我**只写了实验方案、没实现代码**（`force_dir.txt` 当时根本不存在），
用户按方案跑了那轮 → 实际跑的还是普通模式，于是反馈"还是偏"。**已补上并验证。**

### 13.44.2 用户的关键反馈

> "还是偏，**我往正右看按 W 朝左前走**，能不能读取灵敏度设置等来换算？"

"往右看、W 却往左前走" —— 说明**收到的 yaw 与实际朝向之间存在系统性的偏差**（常数偏移或比例），
而不是随机的。

### 13.44.3 关于"灵敏度换算"的说明 + 已加标定旋钮

我们收到的 `cmd.yaw` 是**整圈的 16 位绝对角**（0..65535 对应 0..360°），
**不是**被灵敏度缩放的鼠标增量 —— 所以理论上不该需要"灵敏度换算"。
但"常数偏移/比例"是可能的，于是加了一个**直接可标定**的入口：

```
dir_bias.txt  =  "<偏移度> [缩放]"     → 移动方向 = yaw × 缩放 + 偏移
force_dir.txt =  "<角度>"              → 移动方向**固定**用它（忽略 yaw，纯诊断）
```
启动日志会打印实际生效的模式：
```
viewangles: 省略(客户端自管)
方向: 固定 0.0 度 (force_dir.txt)     /  yaw x1.0 + 90.0 度 (dir_bias.txt)  /  按 yaw 原样
```
已验证：`py_compile` 通过；`force_dir = 0.0`、`dir_bias = None`（读到了）。

### 13.44.4 这一步怎么跑 / 判据

```powershell
cd "e:\codol tae"; Set-Content .\force_dir.txt "0"; python .\run_all.py --secs 300 --ps-probe --out n10dir.txt
```
进靶场后：**分别朝 北 / 东 / 南 / 西 四个方向看，每个方向都按一下 W**。

| 现象 | 结论 | 下一步 |
|---|---|---|
| **不管朝哪看，人物都往同一个世界方向走** | ✅ 我们的方向**确实**传到了画面上 | 病根 = 收到的 yaw 与真实朝向有常数/比例差 → 用 `dir_bias.txt` 标定即可（问用户一次精确观察就能算出） |
| **人物仍然跟着视线走** | ❌ 你看到的移动**不是**我们发的位置驱动的 | 要另查（客户端本地还有别的东西在动） |

### 13.44.5 用户反馈："我没有正北这些定义" → 改成**不需要参照物**的测试

原方案要求"朝北/东/南/西看"，但游戏里没有罗盘，用户无法定义方位。于是改成两种**自参照**测试：

**测试 1（固定方向，`force_dir.txt = 0`）——两次对比**
1. 站定按住 W，记住**人物在世界里往哪边跑**（例如"朝那面白墙跑"）；
2. 鼠标转大约半圈（背对刚才那个方向），再按住 W。
- 人物**还是朝同一面墙跑** ⇒ 我们的方向控制到了画面上 ✅
- 人物**改成朝你现在看的方向跑** ⇒ ❌

**测试 2（缓慢旋转，`force_dir.txt = "rot 20"`）——一眼可见**
`force_dir.txt` 现在支持 `rot [度/秒]`：方向以该速率连续旋转。
按住 W 若方向真受我们控制，人物会**走一个大圆圈**（20°/s + 190 u/s ⇒ 半径约 544 单位），
完全不需要任何参照物。

实现（`bat_serve.py` 速度计算处）：
```python
if _FORCE_DIR is not None:
    _kind, _val = _FORCE_DIR
    if _kind == "fix": yaw_r = _val * math.pi / 180.0
    else:              yaw_r = (_val * (time.time() - assoc["snapshot_epoch"])) * math.pi / 180.0
```
已验证：`rot 20` → `('rot', 20.0)`；`0` → `('fix', 0.0)`；`py_compile` 通过。

---

## 13.45 【2026-10-04】★★★ 用**实录逐帧数据**当参考：角度约定已核对 + **全部字段宽度量出来了**

### 13.45.1 用户要求

> "我还是要正常 fps 游戏的视角为前方的移动，请参考 demo 文件，里面有多个人的同一局的数据，
> 请先分析 demo 文件然后进行参考" + "根据你的判断决定 AB 先后，先归档 md 保存"

### 13.45.2 实录核对：**参考实现就是把 usercmd 的 yaw 原样写回 viewangles**（和我们一样）

参考产物 `load-assets-34680\camera-motion.json`（靶场真机 **1500 帧**，每帧含
`snapshot.origin` / `snapshot.angles` / 当帧 `input.angles`）逐条换算：
```
  #  snapshot.origin            viewangles.yaw   usercmd.angles[1]  换算成度
 336  (  62.1, -582.8, -116.0)      -32.26           59664          -32.26  ✓ 完全相等
 348  (  94.7, -607.7, -116.0)      -32.19           59676          -32.13  ✓
1428  (-108.1, -657.3, -116.0)      104.55           19032          104.55  ✓ 完全相等
1500  (-108.1, -657.3, -116.0)      133.45           24305          133.54  ✓
```
→ **`viewangles.yaw` ≡ `usercmd.angles[1] × 360/65536`** ⇒ 官方/参考实现的做法就是"把收到的
usercmd yaw 原样回声到 viewangles"，**与我们 §13.34 起的做法一致**。所以角度这一环没有偏离官方。

### 13.45.3 ★★ 量出**全部字段宽度**（解决了"缺 codec"这个卡点）

参考 trace 每个字段带 `cursor`（该字段**载荷在混合缓冲里的起始字节**）。
先用已知字段校准（全部命中）：`x/z/y/vy/vx` 各 **4 字节**、`idx 18/19/29` 各 **2 字节(角度)**、
`idx 38` **1 字节**、`idx 60/61/63` **2 字节(scalar16)**、`idx 20` **4 字节(scalar32)**。
再据此量出**我们一直缺的那些**：
```
idx 4  ≈ presence + 4 字节      idx 45 = 3 字节(含 skip 位 ⇒ **presence + 2 字节**) ✓ 与 §13.34 吻合
idx 7  = 1 字节                 idx 47 = 2 字节
idx 9  = 2 字节                 idx 54 = presence + 31 位 (=4 字节) ✓
idx 12 = 1 字节                 idx 57 = 1 字节
idx 15 = 0 字节(值为 0 ⇒ 无载荷) idx 58 = float(4 字节)
idx 16 = float(4 字节)          idx 59 = 1 字节
idx 17 = 1 字节                 idx 60/61/63 = 2 字节
idx 30 = float(4 字节)          idx 64 = 末尾
```
doc 里的"实际字段集"（该 packet）：`0,3,4,7,8,9,10,11,12,13,14,15,16,17,18,19,20,29,30,34,38,39,
45,47,54,57,58,59,60,61,63,64` —— **含 idx 18/19（viewangles）** ⇒ 官方**确实每帧下发 viewangles**，
所以"不下发"那条路（`omit_viewangles.on`）与官方不符，**可以撤掉**。

### 13.45.4 ★ 架构层面的根因（决定了 A/B 两条路）

```
真机对局:  客户端自己的 Pmove 算移动（视角为前方 + 碰撞 + 重力）→ 服务端只校验
我们的现况: 客户端**不跑 Pmove**，只是跟随我们发的 origin ⇒ 移动/碰撞/重力全是"我们算的"
```
这解释了为什么方向手感、碰撞、重力全都不对 —— **不是某个字段发错，而是"谁来算移动"这个架构不同**。

### 13.45.5 结论：**A 先 B 后**（用户授权我定序）

- **A（先做，纯离线）**：按 13.45.3 的宽度表补全 `demo_parse.py` 的解码器 →
  把 demo 里**多玩家逐帧的 `origin + viewangles`** 解出来做**权威参考**，
  用它反查"移动方向 vs 视角"的真实关系、以及官方每帧到底发哪些字段。**不需要实跑。**
- **B（A 之后）**：改架构让**客户端的移动算数**（读客户端预测态并回发/镜像），
  从根上拿到"视角为前方 + 碰撞 + 重力"（对应 §13.17.4 的"复用引擎 Pmove"）。

### 13.45.6 本轮同时确定的两件事（开关处置）

- `omit_viewangles.on`：**与官方行为不符**（官方每帧发 viewangles）→ 建议关闭；
- `static_spawn.on` / 首帧坐标：出生点 `48 -572 -116` **已确认正确**（§13.39），保留"首帧发该坐标 + 其余省略"。

---

## 13.46 【2026-10-04】A 路线实做结果：**解码器已扩展，但 demo 报文需要更多未知索引 → A 暂受阻**

### 13.46.1 已做

按 §13.45.3 的宽度表扩展 `demo_parse.py` 的读取器（新增 codec 表）：
```python
SNAP_SCALAR_W += {7:12, 9:12, 12:8, 15:8, 47:11, 57:11, 59:8}
SNAP_F32      += {16:"f16", 30:"f30", 58:"f58"}
SNAP_PRES_RAW  = {4:(4,"i4"), 45:(2,"yawf"), 64:(4,"i64")}   # presence + n 字节
```
`--selftest` 仍全绿（**122 B / 100 B**，与 `omit_viewangles` 一致）。

### 13.46.2 ❌ 但在真实 demo 报文上仍然走不完

对参考产物的 `demo-packet-*.bin` 逐个 `--snap-at` 试起始偏移：
```
p19/p20/p21 : 走到 14 个字段 → **遇未知索引 27** 停
p43         : 15 字段 → **未知索引 36**
p44         : 14 字段 → **未知索引 25**
p45         : 23 字段 → **未知索引 27**
p50/p51     : 18/20 字段 → **未知索引 36 / 46**
```
→ demo 报文里还有 **25 / 27 / 31 / 36 / 46 …** 这些索引，而参考 trace 只覆盖了**一个** packet 的
字段集（含 0..64 的一部分），**表不全**。

**结论：A 缺的是"完整字段表"**。补齐它需要：
① 更多 trace（参考工具能对每个 packet 生成一份 `demo-player-fields-trace.json`），**或**
② 客户端二进制里的那张 codec/字段表。

→ **A 以现有数据无法收敛**，不再继续瞎猜。

### 13.46.3 ★ 转向 B 的证据：客户端**确实**维护了一份"预测态"（与权威态不同）

参考产物 `camera-motion.json` 的同一条样本里**同时**有：
```
"predicted": { "origin": [48.0, -572.0, -117.14199829101562], "velocity": [0,0,-43.0], … }
"snapshot" : { "origin": [48.0, -572.0, -116.0 ],              "velocity": [0,-0.0,0.0], … }
```
**两份的 origin/velocity 不同**（z 差 1.14、velocity 一个有 -43 的重力速度）——
⇒ 客户端**自己跑了一份预测态（含重力）**，只把服务端的 `snapshot` 当权威。
这正是"视角为前方 + 碰撞 + 重力"的实现所在。

### 13.46.4 B 路线第一步（需一次实跑）

现在探针只取**第一个**命中结构，而它读出来正好 = 我们下发的值（= 权威态）。
要拿到**预测态**：让探针把**每轮命中的全部结构**的 `origin/velocity` 都落盘（现在只写 8 条，
但它们看起来全同值），然后**当位置被省略/被固定时**看哪一个结构的 origin 会"自己变"——
那个就是预测态。定位到它之后，战斗服只要**把它的 origin 回发**（镜像），
即得到"客户端自己算的移动"，方向/碰撞/重力一并解决。

---

## 13.47 【2026-10-04】★★★ B 路线突破：**找到了客户端的预测态**并已接上镜像

### 13.47.1 探针实跑：32 个结构里有一个明显不同（新判据立住了）

```
[PS] 第 21 轮: 2 个 playerstate（不同 origin 2 种）; … vel=(187.6,-30.0,0.0) pm_flags=0x0
[PS] 第 23 轮: 32 个（不同 origin 23 种）; vel=(-190.0,4.0,0.0) pm_flags=0x0     ← 回声我们快照的速度
[PS] 第 27 轮: 32 个（不同 origin 25 种）; vel=(0,0,0)
```
`player_origin.txt` 里出现了**唯一的不同结构**：
```
t=133.7 base=0x1AB5F130 origin=-101.68 -596.69 **-99.63**  vel=**-95.00 0.00 -166.00** \
        angles=6.130 -1.214 0.000 commandTime=13973 **pm=0/8224/… f2c=4**
（其余 31 个）origin=… **-116.00**  vel=我们下发的值  pm=0/0/…  f2c=0
```
- **z = -99.63**（不是我们的 -116）、**带下落速度 -166**、`pm_flags = 0x2020`、`f2c = 4`、
  commandTime 最新 ⇒ **这就是客户端自己跑的预测态**（含重力/碰撞/贴地），
  其余 31 个是"回声我们快照"的权威态。
- 判据：**`pm_flags != 0` 或 `f2c != 0`**（实测 0x2020 / 4）。

### 13.47.2 已落盘的实现

**nt10 侧（`playerstate_probe_thread`）**
- 命中里挑 `pm_flags != 0 or f2c != 0` 的那个 → 记为 `pred_base`，打日志
  `[PS] ★ 找到预测态 base=… → 开始 20ms 定点轮询`；
- 之后**定点高频轮询**（20ms，1 秒一轮）读它，写 **`predicted.bin`** =
  `<6f>x,y,z,vx,vy,vz` + `<I>seq`；读失败/标志归零就重新扫描。

**战斗服侧（`battle_server.py`）**
```python
MIRROR_PRED_FLAG = mirror_predicted.on        # 存在即启用
def read_predicted():  # 读 predicted.bin；seq 超 1s 未更新视为过期 → 回落到服务端积分
…
if _MIRROR_PRED:
    _mp = read_predicted()
    if _mp is not None:
        px, py, pz = _mp[0:3]; pvx, pvy = _mp[3:5]; omit = False
```
启动日志新增一行，一眼确认本轮生效：
```
位置: ★镜像客户端预测态 (mirror_predicted.on)
```
已验证：`py_compile` 通过；`mirror_predicted = True`、`read_predicted() = None`（尚未产生文件）。

### 13.47.3 跑法 / 判据

```powershell
cd "e:\codol tae"; python .\run_all.py --secs 300 --ps-probe --out n10mir.txt
```
进靶场后：**正常走、转视角走、跳一下、贴墙走**。

| 现象 | 结论 |
|---|---|
| 移动变成"**视角为前方**"、有**重力/落地/碰撞**、不被拽回 | ✅ **B 成功** —— 客户端自己的 Pmove 成了权威 |
| 还是卡/被拉回 | 检查 nt10 日志有没有 `[PS] ★ 找到预测态`、以及是否有 `player_origin.txt`→`predicted.bin` 在刷新 |

> ⚠️ 若走不动或位置抖动，先看是不是 `predicted.bin` 没更新（探针没找到预测态）；
> 兜底：删掉 `mirror_predicted.on` 即回到上一版可用状态（服务端积分）。

### 13.47.4 用户实测（n10mir）：**抖动证明重力/碰撞真的活了**，但本轮有两个问题

> "移动朝向还是有问题，碰撞重力也没解决，**但是人物有一个在地面上上下抖动的问题**，
> 就像碰到地面但是被拉上去然后收到重力又碰到地面这样反复，**但是没多久就会结束**"

**"上下抖动"本身就是重大好消息** —— 它说明**重力 + 地面碰撞已经在跑**：
我们每帧把 `z=-116` 回发（**比真实地面 -99.63 更低 ⇒ 在地板里**）→ 客户端把自己顶到 -99.63
→ 我们又发 -116 → 再顶 → 循环。这正是"落下去又被拉上来"的成因 ✓

但本轮有两个我们自己的问题，导致结果不算数：

1. **判据挑错了结构**（我的锅）：日志里
   ```
   [PS] ★ 找到预测态 base=0x00159150 origin=(652.6,1357.3,-116.0) vel=(0,0,0) pm_flags=0x10
   predicted.bin = z=-116.0 vel=0        ← 这是"回声我们快照"的**权威态**
   ```
   `pm_flags=0x10` 是**我们自己**开镜时下发的 idx20 值 —— 旧判据 `pm_flags != 0` 太松。
   **修正判据**（新增 `_is_predicted()`）：
   ```
   预测态 ⇔ f2c != 0  或  pm_flags ∉ {0, 0x10}
   ```
   （权威态实测恒为 `f2c = 0` 且 `pm_flags ∈ {0, 0x10}`；预测态实测 `pm_flags = 0x2020`、`f2c = 4`）

2. **本轮战斗服没起来**：`绑定 127.0.0.1:28960 失败: OSError(10048)` ——
   上一轮的旧战斗服还占着端口 ⇒ **实际服务的是旧代码**，所以抖动很可能来自旧行为。
   已确认端口现已释放；`run_all.py` 启动时的 `free_ports()` 会再清一次。

**修正已落盘**（`_is_predicted()` + 两处调用 + `predicted.bin` 已清），`py_compile` 通过。

### 13.47.5 ✅ 第二次实跑（n10mir2）：**镜像确实生效**；探针轮询被打断的问题已修

**证据 1（镜像生效）**：后段快照
```
TX_SPAWN_EXPERIMENT seq=4721 … pos=20.8,-601.0,**-123.9**  yaw=17700
```
`z = -123.9` = **客户端自己算的地面高度**（不是我们恒定的 -116）；统计 **106/123 条** 快照的 z ≠ -116 ✓
⇒ 战斗服**已经在回发客户端预测态**了。

**证据 2（预测态地址稳定）**：14 次 `★ 找到预测态` **全部是同一个地址 `0x1AD17AE8`** ✓；
`player_origin.txt` 里 **1084/1179** 行是 z ≠ -116 的预测态 ✓。

**发现的问题（我自己的）**：14 次 ★ 后面紧跟 14 次"失效→重扫" —— 因为我在**轮询期间**还用
`_is_predicted()`（`pm_flags`/`f2c`）复判，而这两个值在**预测态里也会随玩家状态变化**
（实测 0x20 / 0x4000 / 0x2；f2c 5 / 43 / 0）⇒ 稳定命中的地址被误判成失效，20ms 轮询只跑 1 秒就断。

**已修（本轮落盘）**：
1. **轮询期间不再复判 pm_flags/f2c**，只看读值有效性（非 None、非 NaN、非全 0、不越界）；
2. **选点时优先用"z 离群"**：权威副本的 z 恒等于我方下发的常量，预测态的 z 是客户端自己算的，
   取 `|z - 众数(z)| > 1` 的那个；`_is_predicted()` 退为备选。
`py_compile` 通过；`predicted.bin` 已清。

---

## 13.48 【2026-10-04】★★★ B 路线成立：**方向已"视角为前方" + 能爬箱子落地**；剩余症状 = 镜像延迟

### 13.48.1 用户实测（n10mir3）

> "移动方向：**按 W 是朝看的方向走了**，但是这是有几率和延迟的，不太能确定一直都是对的
>  抖动：上下抖动还在
>  重力：**能攀爬箱子并落地**，但是还是会穿墙
>  有很大的操作延迟丢包等感觉"

| 项 | 结果 |
|---|---|
| **移动方向 = 视角前方** | ✅ **成立**（就是你要的"正常 FPS"） |
| **重力 / 落地 / 爬箱子** | ✅ 成立 |
| 抖动 / 穿墙 / 操作延迟 | ❌ 仍在 |

### 13.48.2 数据同时证明镜像管道完全打通（n10mir3）

```
[PS] ★ 找到预测态 base=0x1B5195F0 origin=(48.0,-572.0,-121.2) vel=(0,0,-90.0)（z 离群 -121.17 vs 众数 -116.00）
★ = 1 ; 重扫 = 0                       ← 定位一次成功、20ms 持续轮询
predicted.bin seq = 6655               ← 实时刷新
TX_SPAWN pos=…z=-125.4 → -122.4 → -125.5 → -127.6 → -127.9   ← z 随地形起伏(重力/碰撞在跑)
```

### 13.48.3 三个剩余症状 = **同一个根因：镜像延迟**

服务端回发的是"20ms 前"的客户端预测值 ⇒ 客户端每帧被**往回拽**：
- 贴地时：拽高 → 再落 → **上下抖动**；
- 贴墙时：拽到上一帧（可能已进墙）→ **穿墙**；
- 移动中：方向被旧值拉偏 → **"有几率和延迟"**。

### 13.48.4 已落盘：**前导补偿**（`pred_lead_ms.txt`，默认 50ms）

```python
_lx, _ly, _lz = vx*lead, vy*lead, vz*lead          # 沿预测速度外推
if 外推距离 > 120: 等比缩到 120                     # 防瞬移
px, py, pz = pred.x + _lx, pred.y + _ly, pred.z + _lz
```
启动日志：`位置: ★镜像客户端预测态 (mirror_predicted.on), 前导补偿 50 ms`

**调参入口**（无需改代码、无需重新编译）：
- 还发飘/延迟 → `pred_lead_ms.txt` **调大**（60~80）
- 被推过头/顶进墙 → **调小**（30~40）

已验证：`mirror=True`、`lead=0.050s`、`py_compile` 通过、`predicted.bin` 已清。

---

## 13.49 【2026-10-04】全链路提到 **128 tick（≈7.8ms）** + 高速轨迹（抖动/穿墙定量分析）

用户指令："**采样 128tick**"。已把整条镜像链都提到 128 Hz，并把测量做到逐 tick：

| 环节 | 之前 | 现在 | 开关/文件 |
|---|---|---|---|
| 探针定点轮询预测态 | 20ms | **7.8ms（128 tick）** | `tick_hz.txt`（默认 128，与战斗服共用） |
| `pred_trace.txt` 高速轨迹 | 无 | **每 tick 一条**（t x y z vx vy vz） | 自动产出 |
| 战斗服快照下发间隔 | 25ms(40Hz) | **7.8ms（128 tick）** | `tick_hz.txt` |
| 镜像前导补偿 | 50ms | **25ms** | `pred_lead_ms.txt` |

> 前导补偿同步下调的原因：链路延迟从 ~50ms 降到 ~20ms（探针 7.8 + 快照 7.8 + 客户端应用），
> 50ms 会**过度外推**（把人推进墙里）。25ms 更贴合；仍可随时调。

启动日志可一眼确认：
```
位置: ★镜像客户端预测态 (mirror_predicted.on), 前导补偿 25 ms, tick 128 Hz
-- [PS] playerstate 探针已启动 (扫 3.0s 一轮; 命中预测态后按 128 tick≈7.8ms 定点轮询)
```

已验证：`tick = 128 Hz, snap_dt = 0.0078 s, lead = 25 ms`；`probe tick = 128 Hz, poll = 7.8 ms`；
`py_compile` 通过；`predicted.bin` / `pred_trace.txt` 已清。

**分析口径（下一轮拿到 `pred_trace.txt` 后）**：
- 抖动：对 `z(t)` 做一阶差分 → 统计**符号翻转次数 / 振幅谱**，量出频率与幅度；
- 落地超调：找 `vz` 由负转正的瞬间，量 `z` 相对地面的**最大下冲**（穿地深度）；
- 穿墙：找 `x/y` 在 1~2 tick 内的**瞬时大跳**（>50 单位/tick），并与前导外推量对照
  —— 若跳变量 ≈ `|v|×lead`，那就是前导补偿造成，调小 `pred_lead_ms.txt` 即可。

---

## 13.50 【2026-10-04】★★★ 128 tick 轨迹定量分析：抖动=**位置被来回拉扯**（不是手感问题）

### 13.50.1 实测（`pred_trace.txt` 15168 样本 / 168.6s，中位间隔 **10.2ms** ≈ 100~128 tick）

```
[z]       峰峰=82.66（地形起伏）
[z 抖动]  |dz|>0.05 步数=653, 符号翻转=451 → ≈2.7 次/秒
[最大单 tick 下冲] t=152.24  dz=-42.75 (10ms 内掉 42 单位!)
[x/y 单 tick 位移 >30]  61 次
    例：t=103.05 dx=+24.2 dy=+26.7 → t=103.06 dx=-26.7 dy=-29.6（10ms 内先冲后弹）
[落地事件 vz<-20 -> >=-1]  38 次（z 分别落在 -116.00 / -120.16 / -121.64 …=不同地形高度）
```

**判读**：
- 正常移动 = 190 u/s ⇒ **1.9 单位 / 10ms**；
- 实测出现 **20~33 单位 / 10ms（≈2000~3300 u/s）** 的瞬跳，且成对出现（+24 紧跟 −27）
  ⇒ 高 **三个数量级**、且是**对冲** ⇒ 这是**位置被来回拉扯**（橡皮筋），不是手感问题；
- 25 单位 ≈ 190 u/s × **0.13s**，**远大于**我加的 25ms 外推（4.75 单位）
  ⇒ 根因是 **"回发过期位置 → 客户端以它为基准重新播种预测"这个循环**；前导补偿只是又叠了一层误差。

### 13.50.2 两项修复（已落盘）

1. **`pred_lead_ms.txt = 0`** —— 去掉我人为加的外推误差（25ms 外推 ≈1.2 单位/帧的额外扰动）；
2. **镜像改为 `if _MIRROR_PRED and not omit`** —— 于是打开 `spawn_from_map.on`（省略开关）时，
   **位置完全不发**，客户端的预测就**完全自由**（不再被我们回发的过期值重新播种）。
   这是"彻底不打架"的方案；§13.40 当时"不发位置就不能动"是在**预测态还不存在**的情况下测的，
   现在客户端已经在跑预测，值得重测。

启动日志会提示：
```
位置: ★镜像客户端预测态 (mirror_predicted.on), 前导补偿 0 ms, tick 128 Hz  [⚠ 与省略开关同时开启 ⇒ 位置将完全不发，客户端预测自由]
```
已验证：`lead=0ms / tick=128Hz / mirror=True`，`py_compile` 通过，轨迹文件已清。

**分析脚本已留档**：`_an_trace.py`（读 `pred_trace.txt` 输出抖动率/瞬跳/落地/最大下冲）。

---

## 13.51 【2026-10-04】⚠️ 事故与修复：**日志里一个 `⚠` 把战斗服打死了**（客户端"卡在等待连接"）

### 13.51.1 现象

用户："**卡在战斗服加载等待连接**"。查数据：
- `battle_srv.log` 里那轮（15:04:50）**两个战斗服实例都只打了 7 行就没了**，
  既没有 `位置:`、也没有 `已监听`、也**没有 `RX #`（0 个包）**；
- 端口随后是空的 ⇒ 进程早已退出。

### 13.51.2 根因（`_battle_err.txt` 里的 traceback）

```
UnicodeEncodeError: 'gbk' codec can't encode character '\u26a0' in position 75
  battle_server.py line 1243 in main
    log("  位置: ... [⚠ 与省略开关同时开启 ...]")
```

- `run_all.start_battle_server()` 用 `subprocess.Popen(..., stdout=open(out,"w"), stderr=...)`
  启动战斗服 ⇒ 子进程 stdout 的编码是 **GBK**；
- 我上一轮在日志里加了个 **`⚠`（U+26A0，GBK 编不出）** ⇒ `print()` 抛异常
  ⇒ **战斗服在 `main()` 里启动即崩** ⇒ 客户端等不到任何回应 ⇒ "等待连接"；
- **为什么没早发现**：我手跑时 stdout 是终端（UTF-8），同一行不会报错。

### 13.51.3 修复（两处，均已验证）

1. **去掉 `⚠`**（改成 `[注意: ...]`）；
2. **加固 `log()`**：优先 `sys.stdout.buffer.write(line.encode("utf-8","replace"))`，
   再退 `ascii/replace`；并且 **`main()` 开头 `sys.stdout/stderr.reconfigure(encoding="utf-8", errors="replace")`**
   （与 nt10 同款做法）；
3. **顺手补上缺失的 `import sys`** —— 它本来就没导入，所以加固分支第一次也走了兜底（日志显示成 `?`）。

**复现验证**（用与 run_all 相同的方式：Popen + stdout 重定向到文件）：
```
进程存活 = True   无 stderr
位置: ★镜像客户端预测态 (mirror_predicted.on), 前导补偿 0 ms, tick 128 Hz
[*] 已监听 UDP 127.0.0.1:28962        ← 绑定成功
```
⇒ 现在**任何非 GBK 字符都不会再打死战斗服**。

> 教训：**凡是会被 run_all 重定向的子进程，日志里不要出现非 GBK 字符**；
> 且**改完代码不要立刻让用户跑**（这次是用户正好在我编辑的瞬间启动，两边都踩上了）。

---

## 13.52 【2026-10-04】A（去掉前导补偿）效果确认 + 新增**独立快照频率** `snap_hz.txt`

### 13.52.1 A 的效果（n10lead0，`pred_trace.txt` 9934 样本 / 206.8s）

| 指标 | 前（lead=25ms） | 本（lead=0） | 变化 |
|---|---|---|---|
| **z 峰峰** | 82.66 | **23.66** | **−71%** |
| **平均 \|dz\|** | 6.337 | **1.260** | **−80%** |
| 最大单 tick z 下冲 | −42.75 | **−18.00** | −58% |
| **x/y 单 tick 瞬跳 >30** | 61 | **90** | ✗ 反而更多 |

⇒ **z 那一维基本压住了**（前导补偿确实是我引入的额外误差）；
⇒ 但 **x/y 仍有 ±20~70 单位 / 10~20ms 的对冲跳**（`t=130.13 dy=-67.8` → `t=130.15 dy=+69.5`），
量级**远超**镜像误差（2~4 单位）⇒ 病根是「**位置纠正太频繁 → 客户端拿过期值反复重新播种预测**」。

### 13.52.2 新增旋钮：`snap_hz.txt`（快照频率，与探针 tick 解耦）

```python
_SNAP_HZ = read_snap_hz()      # snap_hz.txt；缺省 = tick_hz
_SNAP_DT = 1.0 / _SNAP_HZ      # pump_snapshot 用它
```
启动日志：`位置: ★镜像…, 前导补偿 0 ms, 探针 128 Hz, 快照 10 Hz`

**依据**：参考 launcher v32 的实测快照频率只有 **~3.3 Hz**，而用户说那时"位置是对的" ⇒
**低纠正频率**是被验证过的方向。本轮把 `snap_hz.txt = 10`（100ms 才纠正一次）。

### 13.52.3 顺带：GBK 安全静态检查

写了个一次性检查（已删）扫描 `battle_server.py`：**`log()` 里已无 GBK 编不出的字符** ✓
（剩下的 4 处 `↔/⇒/⚠` 都在**注释**里，不会被 print）；另外 `main()` 开头的
`stdout/stderr.reconfigure(encoding="utf-8", errors="replace")` 也已就位 ⇒ 双保险。

### 13.52.4 下一步（先 B1，必要时 B2）

- **B1**：本配置（mirror + lead 0 + `snap_hz.txt=10`）—— 纠正频率降 13 倍；
- **B2**：再叠 `spawn_from_map.on` ⇒ **位置完全不发**，客户端预测彻底自由（最彻底）。

---

## 13.53 【2026-10-04】事故 2：**上一轮残留的 `predicted.bin` 播种了错误出生点**

### 13.53.1 现象（用户跑 B1 后）：出生点不对 / 跳不起来 / 爬不上去 / 朝向乱 / 穿墙

第一反应是 `snap_hz=10` 的锅，查数据发现**不是**：

```
n10snap10.txt : ★=0   未找到=4        ← 探针这一轮压根没命中预测态
predicted.bin : (1371.759, 340.705, -122.231, 0,0,0, seq=9934)   ← 上一轮的残留文件
battle_srv.log: TX seq=2 pos=1371.8,340.7,-122.2   ← **出生点用了这个陈旧值**
```

⇒ **探针没命中 → 战斗服用了上一轮的文件 → 头 1 秒出生的位置就是错的**；
而客户端**不会重新出生**，于是整局都废了（跳跃/爬箱的"手感"当然也全不对）。

### 13.53.2 根因：过期判据写错了

`read_predicted()` 原来只看「**seq 有没有变化**」：
```python
if seq != _pred_state["seq"]:
    _pred_state["seq"] = seq
    _pred_state["t"] = now      # ← 第一次读到旧文件的 seq 也被当成"刚更新"
elif now - _pred_state["t"] > 1.0:
    return None
```
⇒ 残留文件的 seq 谁都没见过 ⇒ 被视为新数据 ⇒ **被用满 1 秒**。
（该判据只防"探针中途停掉"，防不住"整份文件是上一轮的"。）

### 13.53.3 修复（三处，均已编译验证）

1. **看文件自身 mtime**：`now - os.path.getmtime(PRED_FILE) > 0.5` ⇒ 直接 `return None`；
2. **启动即删除 `predicted.bin`**（`main()` 里，`_MIRROR_PRED` 时）并打日志
   `镜像: 已清空残留 predicted.bin（避免用上一轮数据播种出生点）`；
3. **拿不到数据时明确告警 + 回落**：
   `[!] mirror_predicted.on 但 predicted.bin 不可用 -> 已回落服务端积分 (连续 N 帧)`
   —— 这样以后一眼就能区分"镜像在起作用"还是"回落到老一套"。

### 13.53.4 仍待解决（风险点）

**探针的预测态判别仍不够稳**：本轮 `★=0`、`未找到=4`，说明
`_is_predicted()`（`f2c != 0` 或 `pm_flags ∉ {0,0x10}`）+ "z 离群"在这轮全部落空
（猜想：我们一直回发它的预测值，导致权威副本与预测副本**趋同、没有离群点**）。
⇒ 下一步需要更稳的判别（候选：**最新 `commandTime`** + 速度差 + `pm_flags` 的位模式学习）。

---

## 13.54 【2026-10-04】事故 3：**锚点误收了别的结构**（探针整轮 `★=0`）

### 13.54.1 现象（n10fix2）

- 战斗服告警如实工作 ✓（这正是上一轮加的告警）：
  ```
  [!] mirror_predicted.on 但 predicted.bin 不可用 -> 已回落服务端积分 (连续 1 帧)   ← 18:27:58 起
  ```
  ⇒ **镜像全程没生效**，用户那轮的手感其实是"服务端积分"；
- 探针：`★=0`、`未找到=0`（找到了候选，但**一个都不是预测态**）。

### 13.54.2 根因：锚点判据是 **OR**

```python
ok = (d[k+12:k+16] == mspd                       # +0xb0 movementSpeed == 190
      or (d[k+0x1C:k+0x20] == ent and d[k+0x158:k+0x15C] == ent))   # 或 实体索引 == 2047
```
⇒ 只要"碰巧也是 800/190"的**别的结构**就会被收进来。本轮实测误收了一批：

```
origin=(-303.90, -2471.10, 64.86)  vel=0,0,0  angles=(0, 89.072, 0)
pm_flags = 402655232 = 0x18004000   ← 真实 playerstate 的 pm_flags 只会是 0/0x10/0x20/0x2020/0x2
```
⇒ 32 份候选**全都一样** ⇒ "z 离群"判据也跟着落空 ⇒ `★=0` ⇒ 镜像无数据。

### 13.54.3 修复（两处）

1. **锚点加严**（`scan_playerstate_bases`）：`gravity==800 且 speed==190` 之外，再用 playerstate
   的其它已知字段交叉验证：
   - `+0x0c  pm_flags < 0x10000`（排除 0x18004000 这类高位假货）；
   - `+0x30/0x34/0x38 origin` 必须落在 `|x|,|y| < 8192 且 |z| < 4096`；
   - `+0xc0 cameraEntity` 或 `+0x1fc groundEntity` 至少一个是 `2047`。
2. **判别加严**（`_is_predicted`）：同样要求 `pm_flags < 0x10000 且 f2c < 0x10000`。

`py_compile` 通过；陈旧产物（`predicted.bin` / `pred_trace.txt` / `player_origin*.txt` / `pred_base.txt`）已清。


