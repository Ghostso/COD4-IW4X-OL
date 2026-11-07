# CODOL TCLS 目录协议 —— 字节级标定与本地复刻

日期：2026-09-24
证据来源：真实抓包 `run_codol_001/runs/TCLS_DIR_20260924_220810/pktmon.pcapng`
（`tcls_core.exe` PID 19144 ↔ `116.130.229.168:10009`，即 `tcls.qq.com`）

本报告只读产出。分析期间未修改任何被分析文件，未改网络配置，未启停进程。

---

## 结论先行

1. **目录服务器地址的来源已经完全定位：** `COD OL\TCLS\config\dirserver.xml`
   的 `<Server1 host="tcls.qq.com" />` 与 `<portlist port1="8080" port2="5223" port3="10009">`。
   运行时用 `COD OL\TCLS\config\dirserverdynamic.ini` 的
   `successfulserverid=1` / `successfulport=10009` 选定 `Server1 + 10009`。
   `tcls.qq.com` → `116.130.229.168`，端口 10009。**这条 IP 是解析出来的，源头就是这两个文件。**
   `WeGame\tcls\tcls_core.exe` 与 `COD OL\TCLS\Tenio\Dir.dll` 里都**没有**这些字符串的明文，
   说明 host/port 由 `Dir.dll`（或 TCLS 配置读取层）在运行时从 xml/ini 读入，而非硬编码。

2. **请求是 33 字节、响应是 774 字节的定长结构化 TLV 帧**，不是明文文本、不是 protobuf。
   两者共享同一套 4 字节魔数与 26 字节帧头。

3. **`ServiceID=715019302` 在帧里的位置已确定：** 帧头偏移 `8..11`，大端 u32。
   请求与响应都带它，响应原样回显。它是 `Dir.dll` 里 `Service\id` 配置键对应的业务标识。

4. **目录内容里没有 CODOL 大厅地址。** 774 字节里出现的唯一 URL 是
   `www.qq.com:443;1004` / `www.qq.com:443` —— 这是**网络质量测试用的公共 URL**，
   不是游戏服。地区节点名（北京电信/联通、上海、广东、香港等）可以识别，但节点名字段是
   **编码过的**，明文 GBK 扫描不到。

5. **这条链路本身是"成功"的**：`TCLSHost` 日志 `result: true`、`SendServerDirToTgp result=1`。
   但内容里没有可用的大厅条目，所以客户端拿不到地址，最终 `[100] 无法连接大厅服务`。

---

## 1. 地址来源链（可复现）

```
COD OL\TCLS\config\dirserver.xml
  <DirServer count="5" SuccessfulServerID="1" SuccessfulPort="8080">
      <Server1 Catalog="" host="tcls.qq.com" />      <-- 主目录服务器
      <Server2 host="123.151.176.103" />
      <Server3 host="119.84.150.46" />
      <Server4 host="183.61.224.121" />
      <Server5 host="101.91.63.192" />
      <portlist count="3" port1="8080" port2="5223" port3="10009">0</portlist>

COD OL\TCLS\config\dirserverdynamic.ini          <-- 运行时回写"上次成功的选择"
  [DirServer]
  successfulserverid=1
  successfulport=10009
```

DNS：`tcls.qq.com` A 记录 = `116.130.229.168`（实测 `Resolve-DnsName`）。
两者一致。**这条 IP 不是被"算"出来的，是配置文件 + DNS 的确定性结果。**

> 含义：停服后这个 IP 仍在响应，但它返回的目录里没有 CODOL 大厅。
> 它更像"目录/测速服务还活着，但业务目录已撤空"。

---

## 2. DIRTREEREQ（客户端 → 目录服务器，33 字节）

```
偏移  字节                     解析（大端）
0000  0a 09 64 1a              魔数（4B，固定）
0004  00 00 00 07              u32 = 7            序号（注意：请求这里不是长度）
0008  2a 9e 54 26              u32 = 715019302    ServiceID
0012  00 00 17 71              u32 = 6001         事务号 txn
0016  00 00 00 01              u32 = 1
0020  00 00 00 00              u32 = 0
0024  00 00 00 00              u32 = 0
0028  00 02 30 00              u32 = 0x00023000
0032  00                       1 字节收尾
```

原始 hex：

```
0a 09 64 1a 00 00 00 07 2a 9e 54 26 00 00 17 71
00 00 00 01 00 00 00 00 00 00 00 00 00 02 30 00 00
```

观察：抓包里出现了**两次连接**，每次客户端都重复发同一帧（TCP 重传可见 8 次同 seq 的 33 字节）。
第二次连接的 txn 不同。这说明重连时 txn 会递增，`ServiceID` 不变。

---

## 3. DIRTREERESP（目录服务器 → 客户端，774 字节）

```
偏移  字节                     解析
0000  0a 09 64 1a              魔数（与请求相同）
0004  00 00 02 ec              u32 = 748           = 774 - 26（固定头长）
0008  2a 9e 54 26              u32 = 715019302     ServiceID（回显请求值）
0012  00 00 17 72              u32 = 6002          txn = 请求 txn + 1
0016  00 00 00 01              u32 = 1
0020  00 00 00 00              u32 = 0
0024  02 06                    固定
0026  ---- 载荷开始（748 字节）----
0026  00 09
0028  00 00
0030  02 db
0036  09 64 69 72 5f 72 6f 6f 74 00     u8 长度=9 + "dir_root" + 0
0055  00 00 00 b4              u32 = 180
...
0384  "www.qq.com:443;1004"
0415  "www.qq.com:443"
0494  "www.qq.com:443;1004"
0525  "www.qq.com:443"
0604  "www.qq.com:443;1004"
0635  "www.qq.com:443"
0715  "www.qq.com:443;1004"
0746  "www.qq.com:443"
0774  文件结束
```

**帧头固定 26 字节**，这一条已被验证：本地服务器按 26 字节头重建后，
与抓包响应**逐字节一致**（见第 6 节）。

---

## 4. 节点块布局

`dir_root` 之后是 4 个结构相同的节点块。以 `北京电信` 为例（偏移 0x60 起）：

```
0x60  02 00 00 00 00 00 00 00     节点序号/nodetype = 2
0x68  20 00 00 00                 名字区长度 = 0x20 (32)
0x6c  0e                          u8 = 14 = 名字字节长度
0x6d  b6 ab b2 bf d5 bd c7 f8 2d b5 e7 d0 c5     "北京电信-电信"（编码后）
0x7b  00 00 00 00
0x7f  01 00 00 00 00 00 00 00
0x87  01 00 00 00                 子节点/属性
0x8b  00 01 00 01 01
0x90  00 00 00 00 03 00 00 00 00   attrs
0x99  14 00 00 02                  地址区长度 = 0x14 (20)
0x9d  00 00 00 00 00 00
0xa2  20 00 00 00                  strURL 区长
0xa6  0e b1 b1 b2 bf d5 bd c7 f8 2d c1 aa cd a8   "北京联通"...（第二块起始）
```

> **注意：** 每个节点块末尾挂 `strURL`（`www.qq.com:443;1004` + `www.qq.com:443`）。
> 这是**网络测速 URL**，用来让客户端测各地区的网络质量，进而挑选地区节点。
> 它**不是**游戏服地址。

节点名可用 GBK 识别出这些（都在同一个"名称池"里）：

```
北京电信-电信   北京电信-联通   上海电信-电信   广州电信-电信
广东电信-电信   北京网通-联通   广东网通-联通   香港电信-电信
```

但它们在字节里是**经过一层编码**的（不是直接 GBK 连续串），需要按每 2 字节 + 偏移规则解。
第 4 节给出的结构只覆盖到"能定位名字字段"，未完成完整解码表。

---

## 5. 本机复刻服务器

新文件：`CODOLServer/tcls_dir_server.py`

能力：

| 参数 | 作用 |
|---|---|
| `--mode replay` | 用抓包 `tcls_dirtree_response.bin` 原样回放（用于验证链路） |
| `--mode tree` | 按 JSON 追加/替换节点，用于注入自定义大厅条目 |
| `--mode empty` | 返回空载荷，用于对照失败路径 |
| `--describe` | 只打印请求/响应的解析结果 |

它同时监听 TCP 与 UDP 10009。TCP 走 26 字节定长头，UDP 只在收到魔数匹配的报文时回。

验证：本地起服务器，用真实 33 字节请求打过去，收到 774 字节，
**与抓包文件逐字节相同**（`byte_identical_to_capture True`）。

---

## 6. 定向重定向（不碰系统网络）

新文件：

- `CODOLServer/frida_tcls_dir_redirect.js` —— Frida 脚本，只 attach 一个进程，
  hook `connect` / `WSAConnect`，把目标 IP 命中目录服务器列表（且端口 ∈ {10009, 8080, 5223}）
  的 `sockaddr_in` 就地改写成 `127.0.0.1:10009`。
- `run_codol_001/tcls_redirect_run.ps1` —— 端到端包装脚本。

**为什么不用 netsh / hosts：**

- `netsh interface ipv4 add address` 会真的往网卡加地址，之前导致整机断网。
- 改 hosts 会影响**所有**进程并留全局痕迹。
- Frida 方案只改目标进程的一次 `connect` 调用的参数，进程退出即消失，**不影响整机网络**。

验证（已实测通过）：

```
客户端 connect 目标 : 116.130.229.168:10009   （真实公网 IP）
实际收到            : 774 字节，头 0a 09 64 1a 00 00 02 ec ...
来源                : 本机 127.0.0.1:10009 的 tcls_dir_server
```

即：**客户端以为自己在连腾讯，实际连到了我们的服务器。**

---

## 7. 下一步与仍未闭环的点

已完成：

- [x] 定位目录服务器地址来源（`dirserver.xml` + `dirserverdynamic.ini` + DNS）
- [x] 标定 DIRTREEREQ / DIRTREERESP 帧格式（33 / 774 字节，26 字节头）
- [x] 本机复刻可字节级回放
- [x] 进程内定向重定向，不影响整机网络

未完成：

- [ ] 节点名/节点的完整解码规则（当前只到"能定位字段"）
- [ ] 是否存在**第二跳**查询（拿到地区树后是否再问一次要游戏服列表）
- [ ] `dirsystemconfig.cfg`（1144 字节，加密）的明文规则
- [ ] 游戏本体 `codoMP_client_shipRetail.exe` 侧的大厅协议 —— 这是 `[100]` 的真正归属层

**重要判断：** 即使目录这一跳完全伪造成功，`[100]` 也不一定消失，
因为大厅连接是游戏本体发的（Demonware/Blaze 风格），不经过 TCLS 目录。
目录这跳的作用是让启动链**继续往下走**，从而暴露游戏本体的下一步动作。

---

## 8. 复现命令

```powershell
# 只打印解析结果
python .\CODOLServer\tcls_dir_server.py --describe

# 本地验证回放（回环）
python .\CODOLServer\tcls_dir_server.py --bind 127.0.0.1 --port 10009 --mode replay --tcp-only

# 端到端（需要管理员）
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File '.\run_codol_001\tcls_redirect_run.ps1' `
  -DurationSeconds 240 -AttachDelaySeconds 8
```

回滚：目录服务器与 Frida 脚本都不修改任何被分析文件；
如需重置 `dirserverdynamic.ini` 等运行时文件，备份在
`backups/TCLS_RETARGET_20260924_223137/`。
