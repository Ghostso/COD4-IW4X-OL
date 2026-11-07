# IIPS 策略服务器协议（`[100]` 的直接阻塞点）

日期：2026-09-25
证据来源：`COD OL\IIPS\iips_policymsg.dll`（腾讯签名 Valid）+ `IIPSHost.dll` 日志串

---

## 1. 为什么 `[100]` 与"没有服务器"是同一件事

`IIPSHost.dll` 内嵌日志串给出了主机启动的**严格顺序**：

```text
[ResourceLoader::Start()][connect to policy server start][policySvrAddr %s]
[ResourceLoader::Start()][connect to policy server end][policySvrAddr %s]
[ResourceLoader::Start()][connect to policy server failed][policySvrAddr %s]
[ResourceLoader::Start()][m_iipsHost.Start(),listen to pipe start]
[ResourceLoader::Start()][m_iipsHost.Start(),listen to pipe succeed]
[ResourceLoader::Start()][m_iipsHost.Start(),listen to pipe failed]
```

即：**先连策略服务器，连上之后才创建命名管道。**

而游戏侧 `iips.dll` 的失败串：

```text
[IIPSClient::Start()][failed to conncet pipe]     <- 原文拼写
```

### 实测证据

```
提权启动 COD OL\IIPS\IIPSHostApp.exe /mode iipslaunch（原版 iips.dll / IIPSHost.dll）
  -> 进程存活 (pid 18344)
  -> HostPid 未写入（保持旧值 UTF-16 "20128"）
  -> 命名管道未创建（枚举 \\.\pipe\ 无任何 IIPS 管道）
```

=> 链路断点 = `connect to policy server failed` -> 管道不建 -> 游戏 `failed to conncet pipe`
-> `WIN_IIPS_INIT_ERROR (0x8189FEC)` -> UI `[100] 无法连接大厅服务`。

**这解释了"是因为没有服务器"到底卡在哪一层**：不是大厅（GDP）层，
而是**更早的 IIPS 策略层**。大厅协议根本还没被触达。

---

## 2. 端点（写本地服务器时的劫持目标）

来源：`IIPSHostApp.ini` + `iips.dll` / `IIPSHost.dll` 字符串

```text
IIPSHostApp.ini [IIPSPolicySvrInfo]
    Address     = udp://ctrl.iips.qq.com:8000
    HeartbeatInterval = 60
    BusinessID  = 3058

iips.dll        : stat.iips.qq.com     （统计上报）
IIPSHost.dll    : http://iips.speed.qq.com （速率/上传配置）
iips_policymsg.dll : WS2_32 直连 UDP（协议本体）
```

---

## 3. 协议 schema（从 `iips_policymsg.dll` TDR 描述符提取）

该 DLL 内含完整 TDR 类型/字段描述符表（偏移 0xC664..0xEA80），
字段名逐字如下（顺序即声明顺序）：

```text
CSTransMsg      = { Head : CSTransMsgHead, Body : CSTransMsgBody }
CSTransMsgHead  = { Version, Magic, HeadLen, BodyLen }
CSTransMsgBody  = { EncryptLen, EncryptBuffer }

CSPolicyMsg     = { Head : CSPolicyMsgHead, Body : CSPolicyMsgBody }
CSPolicyMsgHead = { Version, Magic, PkgLen, CmdID }
CSPolicyMsgReq  = { BusID, LastImmDLSize, LastImmDLTime,
                    LastPreDLSize, LastPreDLTime, NeedUploadBitmap }
CSPolicyMsgRes  = { MaxPreDLSpeed, MaxConnNum, MaxDLSpeed,
                    MaxRealTimeULSpeed, MaxPreULSpeed, MaxInGamePreULSpeed,
                    NeedUploadBitmap, ReportIntervalMs,
                    ReportUploadSpeedBytePerSecond }
CSPolicyMsgBody = { Res1, Res2, Res3 }     ; 与 Req/Res 联合，保留字段
```

TDR 常量名（`cs_policy_msg` 命名空间）：

```text
CS_POLICY_MSG_MAGIC
CS_POLICY_MSG_ENCLEN
CS_POLICY_MSG_REQ
CS_POLICY_MSG_RES
```

魔数字符串（明文，位于 .rdata）：

```text
"iips#policy!@#$%"
```

导出 API（`iips_policymsg.dll`，无修饰名）：

```text
ord1  iips_policymsg_api_create    RVA 0x1000
ord2  iips_policymsg_api_destroy   RVA 0x11C0
ord3  iips_policymsg_api_recv      RVA 0x1200
ord4  iips_policymsg_api_send      RVA 0x1330
导入：KERNEL32(15) / MSVCR80(31) / WS2_32(15)   -> 自身负责 UDP 收发
```

> 待补：`CS_POLICY_MSG_MAGIC` / `CS_POLICY_MSG_ENCLEN` 的**数值**、
> 以及 Req/Res 各字段宽度（TDR 描述符里带类型码，需进一步解析）。

---

## 4. 自建本地策略服务器的最小路径

```text
1. 劫持 ctrl.iips.qq.com -> 127.0.0.1（+ stat.iips.qq.com / iips.speed.qq.com）
   * 用已有的挂起期主机名内存改写（不碰 netsh/路由/DNS）
2. 在 UDP 8000 监听，按 §3 结构解析 Req、回 CSPolicyMsgRes
   * Magic 用 "iips#policy!@#$%" 派生值
   * Res 里把限速放大（MaxDLSpeed/MaxPreDLSpeed 等给大值）、MaxConnNum>0
3. IIPSHostApp 一旦 `connect to policy server end`，
   就会进入 `m_iipsHost.Start(), listen to pipe` -> 创建 \\.\Pipe\<name>
4. 游戏 IIPSClient 连上管道 -> ResourceManagerII 初始化成功
   -> 退出 IIPS 层，进入 TCLS / TQoS / GDP 大厅层
```

现成可复用件：

```
CODOLServer\_mainline\suspend_host_redirect.py   挂起期主机名改写（已验证可用）
CODOLServer\_mainline\gdp_server.py              UDP/TCP 骨架（含 TQoS 应答）
CODOLServer\_mainline\list_pipes.py              管道枚举
CODOLServer\_mainline\_s3_iips_host_test.py      IIPS 主机层聚焦验证
```

---

## 5. 与 `[100]` 的关系一句话

```text
[100] = WIN_IIPS_INIT_ERROR
      = IIPSClient 连不上命名管道
      = IIPSHostApp 没建管道
      = IIPSHostApp 连不上策略服务器 udp://ctrl.iips.qq.com:8000
      = 那个服务器 2024 年停服关掉了
∴ 写一个会应答的本地策略服务器，就能把 [100] 这一步推进过去。
```
