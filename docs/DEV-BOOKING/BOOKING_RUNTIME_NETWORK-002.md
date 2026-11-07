# BOOKING_RUNTIME_NETWORK-002

> 运行期观测阶段 002：非侵入式网络层观测
> 目标：6/14 之后客户端是否收到网络响应，来自哪条连接
>
> 结论：
>
> ```
> NETWORK_OBSERVATION_CHANNEL = AVAILABLE (NDIS, payload-capable)
> 6/14 REQUEST                 = NOT_SENT
> BOOKING_RESPONSE_NETWORK     = NOT_OBSERVED
> RESPONSE_CHANNEL             = NOT_ESTABLISHED
> BLOCKING_ERROR               = EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE
> ```
>
> 客户端在**发出 6/14 之前**就弹“致命错误”并终止，
> 因此本轮不存在可观测的 Booking 请求，更无响应可谈。

---

## 0. 纪律核对

```
Server 修改              = 无
Golden 修改              = 无
4 个 Lobby patch 修改    = 无
KDF hook 修改            = 无
6/14 request 修改        = 无
client 内存修改/patch    = 无
Frida attach / 注入      = 无
DebugActiveProcess       = 无
Booking response 发送    = 无
ACE 关闭/配置/规避       = 无
```

本轮唯一动作是：用提权代理执行系统自带的
`netsh trace start capture=yes`（NDIS 报文捕获），
以及读取客户端自己的窗口文字。两者都不触碰目标进程。

---

## 1. 观测通道能力确认

上一阶段（001）因没有断点能力而被阻塞。本阶段改用系统网络层：

```
pktmon                 = 驱动缺失（无法通信）
tshark/dumpcap/windump = 未安装
netsh trace capture=yes = 可用（NDIS，携带 payload）
tracerpt               = 可用（ETL -> XML）
```

### 能力验证

```
> netsh trace start capture=yes tracefile=...\probe.etl maxsize=8
状态: 已启动
> netsh trace stop
正在合并数据... 完成
> tracerpt probe.etl -o probe.xml -of XML
转换成功
```

结论：

```
NETWORK_OBSERVATION_CHANNEL = AVAILABLE
（系统级、带载荷、不注入目标进程、不触碰 ACE）
```

这是相对上一阶段的实质进展：**观测通道不再是瓶颈**。

---

## 2. 正式观测运行

```
启动方式   Golden 手册（run_all.py，只读，未修改）
抓包目标   C:\Windows\Temp\booking_net.etl（netsh trace capture=yes）
抓包范围   全网络接口，含回环与本机
轮询       lobby_srv.log 中 mmbook / 6/14
```

### 时间线

| 时间 | 事件 |
|---|---|
| 20:01:54 | 客户端进程启动 (PID 20356) |
| 20:02:08 | IIPSHostApp 启动 |
| 20:02:22 | 大厅握手完成，`hmac=OK`，3074 双监听建立 |
| 20:02:22 | 最后一条业务解密 `#40 service=71 task=9` |
| 20:03:05 ~ 20:06:35 | 仅 keepalive（每 30s） |
| 20:02 ~ 20:07 | 用户操作进入剧情/靶场 |
| 20:07:28 | 对端关闭，大厅连接结束 |

### 证据：6/14 从未到达服务器

lobby_srv.log 全文搜索 `mmbook`：

```
mmbook 命中 = 0
```

最后一个业务事件是 `#40`，之后只有 keepalive，最后连接被客户端关闭：

```
[20:07:28]   对端关闭
[20:07:28] === 大厅连接结束 ('127.0.0.1', 59418) (解出任务 40 条) ===
```

因此：

```
6/14 REQUEST = NOT_SENT
```

---

## 3. 客户端真实错误（弹窗抓取）

用客户端自己的窗口文本接口（`WM_GETTEXT`，只读）抓取：

```
hwnd 0x3070A  pid 20356  class #32770
进程: codoMP_client_shipRetail.exe
文字: ["致命错误", "确定", "EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE"]
```

即：

```
致命错误
EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE
```

### 语义

客户端在进入剧情/靶场流程时，需要下载/读取发布方（publisher）文件，
该步骤失败，于是弹出致命错误并终止。

这不是：

```
✗ 6/14 mmbook 被拒
✗ "mmbook accepted" 解析失败
✗ Booking 超时
✗ 网络连接中断
```

而是它**尚未走到预约阶段**。

---

## 4. 网络层统计（崩溃窗口内）

ETL 转 XML 后统计端口出现次数：

```
PORT_3074  = 1875
PORT_28960 = 33
PORT_8443  = 525
PORT_8444  = 569
PORT_8446  = 508
```

对 Booking 相关字符串搜索：

```
mmbook                  = 0
MM_RESERVE_CMD_REQUEST  = 0
booking                 = 0
```

### 解释

- 3074：本地 auth/lobby（Golden）。
- 28960：出现 33 次，但**不是 Booking 握手**——6/14 从未发生，
  因此不构成 Battle endpoint 证据，保持 `UNKNOWN`。
- 8443/8444/8446：客户端自身安全/统计通道，与本阶段目标无关。

**注意**：二进制协议不一定含 ASCII，所以 0 命中不能单独推出
“没有响应”。但本轮有更强证据——**服务器侧根本没有收到 6/14**，
因此无论二进制与否，都不存在对应的 Booking 响应。

---

## 5. 结论判定

| 检查项 | 结果 |
|---|---|
| 网络观测通道 | AVAILABLE (NDIS payload-capable) |
| 6/14 是否发送 | NOT_SENT（lobby 0 命中 + 连接在预约前关闭） |
| 6/14 endpoint | NOT_OBSERVED |
| inbound response | NOT_OBSERVED |
| retry / timeout | NOT_OBSERVED（未进入预约阶段） |
| 3074 关系 | 稳定大厅连接，仅 keepalive |
| 28960 关系 | 出现报文，但非 Booking（UNKNOWN 语义） |
| RESPONSE_CHANNEL | NOT_ESTABLISHED |
| 阻塞原因 | `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` |

按阶段 002 的 P6 情形归类：

```
当前问题 = 既不是 A(Server 不回应)
           也不是 B(回应了但不接受)
           也不是 C(通道建立错误)
           也不是 D(endpoint 错误)

而是 0. 客户端在发出预约请求之前就崩溃
       → EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE
```

---

## 6. 为什么这不是 Booking 的失败

现有 9/9 断连实验、booking-push OFF、retry 5s 等现象，
都发生在“客户端已经发出 6/14”的前提下。
本轮不同：客户端连 6/14 都没发。

因此本轮**不能**用来评价任何 Booking response 方案，
也不改变静态阶段的结论：

```
RESPONSE_CHANNEL         = NOT_ESTABLISHED
ACCEPTED_HANDLER_CALLER  = UNKNOWN
```

---

## 7. 下一阶段的正确入口

先解决 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`，让客户端能真正
走到发出 6/14，再做网络观测。否则网络通道再强也观测不到。

```
前置任务（必须先完成）：
  定位 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 触发的文件/URL，
  并让本地服务/资源满足该步骤（只读定位 + 由用户决定修复方式）。

完成后的观测计划（不注入，仍用 netsh trace）：
  1. 记录 6/14 的 T0 与 endpoint
  2. 记录 T0 后新出现的 TCP/UDP 连接（含动态端口）
  3. 记录首个 inbound payload 的 时间/长度/前 64B
  4. 对照 retry 间隔与连接存活
  5. 只在拿到上述证据后才判定 RESPONSE_CHANNEL
```

不要在本轮基础上继续猜 response。

---

## 8. 产物清单

```
DEV-BOOKING\runtime_net_001\booking_net.xml   ETL -> XML（81 MB）
DEV-BOOKING\runtime_net_001\popup\windows.jsonl  弹窗文字记录
GOLDEN-LOBBY-001\REF_LOBBY_KIT\lobby_srv.log  运行日志（含 0 命中 mmbook）
```

（ETL 本体位于系统 Temp，已清理。）

---

## 9. 环境状态

```
codoMP 进程     = 0
IIPSHostApp     = 0
3074 / 28960    = 无监听
提权代理        = 仍在（pid 11012）
Golden 哈希     = 未变
```

