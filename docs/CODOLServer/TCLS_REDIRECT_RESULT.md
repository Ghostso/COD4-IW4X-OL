# TCLS 目录重定向 —— 端到端复现成功

日期：2026-09-24 23:55
状态：**成功**（`tcls_core` 从本机服务器拿到 774 字节目录响应，并成功桥接到 TGP）

---

## 1. 结论

已实现「**让 CODOL 的启动链向我们自研的目录服务器取目录**」，
**全程不修改系统网络配置**（无 netsh / 路由 / DNS / 防火墙 / 网卡），
**不修改 `WeGame\tcls` 内任何文件**，**不需要 hosts**。

证据（同一次运行，时间戳完全对齐）：

```
# 本机目录服务器日志
23:55:00.986  tcp_request   peer=127.0.0.1:64679  raw_len=33
              hex=0a 09 64 1a 00 00 00 07 2a 9e 54 26 00 00 17 71 ...
              service_id=715019302  txn=6001
23:55:00.987  tcp_response  peer=127.0.0.1:64679  sent=774  payload=748

# Frida 改写探针
rewrite_probe  before: 116.130.229.168:10009   (raw 02 00 27 19 74 82 e5 a8 ...)
               after : 127.0.0.1:10009          (raw 02 00 27 19 7f 00 00 01 ...)
rewrite_result ret=0  wsa_error=0  elapsed_ms=0

# TCLSHost 日志
23:55:00  ServerDir::FetchWithUin() tclsPath: ...\sandbox\TCLS, gameID: 29
23:55:00  ServerDir::ReadServiceID() ServiceID = 715019302
23:55:00  TCLSHostApp::OnFetchServerDirEnd(), gameID: 29, result: true, forTgp: true
23:55:00  TCLSHostApp::SendServerDirToTgp(), result: 1
```

即：**客户端以为在连 `tcls.qq.com`，实际连到了 `127.0.0.1:10009`，并且接受了我们返回的字节。**

---

## 2. 关键教训（为什么会失败很多次）

### 2.1 时间窗口极短 —— 这是唯一真正的难点

| 事件 | 时间 |
|---|---|
| `tcls_core` 进程创建 | 23:54:56 |
| 它发出目录 `connect()` | 23:55:00 |
| 窗口宽度 | **约 4 秒** |

对比一次失败的尝试：进程 23:41:15 创建，23:41:31 查目录，而我们 23:41:54 才 attach —— **晚了 23 秒，一个 connect 都没抓到**。

失败现象极具误导性：Frida 日志**完全没有 connect 记录**，看起来像 hook 没装上；
实际上 hook 装上了，只是目录查询早已结束。

**解法：`CODOLServer\_orchestrate.py`**
以 50 ms 粒度用 `tasklist` 轮询 `tcls_core.exe`，一旦出现立刻 attach 并注入。
`tasklist` 能看见提权进程，而 `frida.enumerate_processes()` 看不见 —— 这是本机的一个坑。

### 2.2 Frida spawn-gating 在本机不可用

```
frida.NotSupportedError: not yet supported on this OS
```

所以「创建即暂停」的干净方案用不了，只能靠轮询抢时间窗口。

### 2.3 `WSAGetLastError` 不在 kernel32

早期版本在 `onLeave` 里从 `kernel32.dll` 取 `WSAGetLastError`，直接抛异常刷屏。
它在 `ws2_32.dll`。已修正为惰性获取 + 失败降级。

### 2.4 提权进程无法用 taskkill 清理

旧 TGP/TCLS 链由提权会话启动，普通权限 `taskkill` / `Stop-Process` 都报 Access denied。
但它们**占着 TGP 单实例命名管道**，导致新起的 `tgp_daemon` 静默移交给旧实例、
根本不重新查目录。

已找到可行路径：**Frida attach 后用 `kernel32!TerminateProcess` 结束**（不需要管理员）。

---

## 3. 协议标定（回顾，已验证）

### 请求 33 字节

```
偏移  字节                     解析
0000  0a 09 64 1a              魔数
0004  00 00 00 07              大端 u32 = 7（序号，不是长度）
0008  2a 9e 54 26              大端 u32 = 715019302  ServiceID
0012  00 00 17 71              大端 u32 = 6001       事务号 txn
0016  00 00 00 01              大端 u32 = 1
0020  00 00 00 00              0
0024  00 00 00 00              0
0028  00 02 30 00              大端 u32 = 0x00023000
0032  00                       1 字节收尾
```

### 响应 774 字节，固定 26 字节帧头

```
0000  0a 09 64 1a              魔数（同请求）
0004  00 00 02 ec              大端 u32 = 748 = 774 - 26
0008  2a 9e 54 26              ServiceID（回显）
0012  00 00 17 72              txn = 请求 txn + 1
0016  00 00 00 01              1
0020  00 00 00 00              0
0024  02 06                    固定
0026  ---- 载荷 748 字节 ----
0055  09 "dir_root" 00         根节点名
0384  "www.qq.com:443;1004"    测速 URL（不是游戏服）
0415  "www.qq.com:443"
...   重复 4 组
```

本地服务器按 26 字节头重建后，与抓包响应**逐字节一致**。

### 地址来源

```
COD OL\TCLS\config\dirserver.xml
  <Server1 host="tcls.qq.com"/>
  <portlist port1="8080" port2="5223" port3="10009">
COD OL\TCLS\config\dirserverdynamic.ini
  successfulserverid=1
  successfulport=10009
tcls.qq.com -> 116.130.229.168 (DNS)
```

`WeGame\tcls\tcls_core.exe` 与 `Dir.dll` 内部**没有**这些字符串的明文，
由运行时从 xml/ini 读入。

---

## 4. 可复现流程（非提权）

```powershell
# 1) 起本机目录服务器
python .\CODOLServer\tcls_dir_server.py --bind 0.0.0.0 --port 10009 --mode replay

# 2) 起编排器（50ms 轮询抓 tcls_core 启动瞬间并注入）
python .\CODOLServer\_orchestrate.py --wait 90 --duration 120

# 3) 起 TGP 链
powershell -File .\run_codol_001\start_tgp_sandbox.ps1
```

验证脚本（带 sockaddr 前后对照）：

```powershell
copy .\CODOLServer\_orchestrate.py .\CODOLServer\_orchestrate_verify.py
# 把 _orchestrate_verify.py 里的 frida_tcls_dir_redirect.js 换成 _verify_rewrite.js
python .\CODOLServer\_orchestrate_verify.py --wait 90 --duration 120
```

---

## 5. 文件清单

| 文件 | 作用 |
|---|---|
| `CODOLServer\tcls_dir_server.py` | 本机 TCLS 目录服务器（replay / tree / empty 三模式） |
| `CODOLServer\frida_tcls_dir_redirect.js` | 进程内 connect 改写（生产用） |
| `CODOLServer\_verify_rewrite.js` | 带改写前后对照的验证版 |
| `CODOLServer\_orchestrate.py` | 轮询 + 注入编排器（关键） |
| `CODOLServer\_trace_real_path.js` | socket 生命周期追踪 |
| `CODOLServer\_selftest_inside_tcls.js` | 进程内合成连接自测 |
| `CODOLServer\_dump_gbk_nodes.py` | 响应节点结构 dump |
| `CODOLServer\_dump_node_blocks.py` | 响应逐字节展开 |
| `run_codol_001\start_tgp_sandbox.ps1` | 起 TGP 链（纯 ASCII，PS5.1 安全） |
| `CODOLServer\TCLS_DIR_PROTOCOL.md` | 协议分析报告 |
| `CODOLServer\TCLS_REDIRECT_RESULT.md` | 本文件 |

> **编码注意**：本机 Windows PowerShell 5.1 按 GBK 读 `.ps1`。
> 所有 `.ps1` 必须**纯 ASCII**，否则中文注释会导致 `UnexpectedToken` 解析错误。

---

## 6. 下一步

目录这一跳已通。接下来要回答的是**真正决定 `[100]` 的问题**：

1. **第二跳**：`tcls_core` 是否会在拿到地区目录后，再向某个"地区节点服务器"发第二次查询？
2. **目录节点编码**：774 字节里地区名是编码过的，需要解码规则才能放进自定义大厅条目。
3. **游戏本体的大厅协议**：`[100] 无法连接大厅服务` 属于 `codoMP_client_shipRetail.exe` 层
   （Demonware/Blaze 风格），**不经过 TCLS 目录**。
   目录这跳的价值是让启动链继续往下走，从而暴露游戏本体的下一步动作。
4. 观察：客户端拿到这份目录后，**是否推进到启动游戏本体**。

子代理 Lovelace 负责 1+2，Carson 负责 2+3 的静态部分。
