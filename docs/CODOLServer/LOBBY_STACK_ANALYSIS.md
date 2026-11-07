# CODOL 大厅服务识别（方案 A 阶段结论）

日期：2026-09-24
依据：`LOBBY_DEEP_20260924_181441` 抓包 + `codoMP_client_shipRetail.exe` 静态分析

---

## 1. 核心发现：大厅是 Demonware，不是腾讯自研

`codoMP_client_shipRetail.exe` 内部存在完整的 **Demonware (dw) / Blaze (BD)** 协议栈。
这是 IW4 世代 CoD 的标准网络层，CODOL 继承了下来。

### 1.1 事件/状态字符串（确认属于 dw 状态机）

```
DW_DNS_ERROR / DW_DNS_COMPLETE
DW_ACCOUNT_ERROR / DW_ACCOUNT_LOGIN_COMPLETE
DWLOGON_REGISTERCODOID_ERROR / DWLOGON_REGISTERCODOID_COMPLETE
DW_LOBBY_ERROR / DW_LOBBY_CONNECTED
DWLOBBY_DELETED / DWLOBBY_PUMP_DISCONNECTED / DWLOBBY_PUMP_SUCCESS
DW_DUPLICATE_LOGIN
```

调用点符号：

```
cppOnDWConnected
cppOnDWDisconnected
dwLogonStart
```

### 1.2 Blaze (BD) 错误码族

```
BD_LOBBY_PROTOCOL_VERSION_FAILURE
BD_LOBBY_INTERNAL_FAILURE
BD_LOBBY_PROTOCOL_ERROR
BD_LOBBY_FAILED_TO_DECODE_UTF8
BD_LOBBY_ASCII_EXPECTED
BD_LOBBY_METHOD_DISABLED
BD_LOBBY_MIGRATION_FAILURE
BD_NOT_CONNECTED / BD_SEND_FAILED / BD_CONNECTION_RESET
BD_LOGIN_QUEUE_DNS_RESOLUTION_ERROR
... (数百条 BD_* )
```

### 1.3 错误码格式化点（关键）

```
BD_MAX_ERROR_CODE
Unknown bdLobbyErrorCode
```

**这就是 `[100]` 的来源。** 客户端把 `bdLobbyErrorCode` 直接拼进了
`无法连接大厅服务` 的提示里，所以 `100` 是 **Blaze 大厅错误码**，
不是"网络错误编号"，也不是我们之前以为的 IIPS 端口号。

---

## 2. 这修正了什么

| 之前的假设 | 现在的事实 |
|---|---|
| 大厅是腾讯自研服务 | 大厅是 **Demonware Blaze Lobby** |
| `116.130.224.66` 可能与大厅有关 | 它是 `ied-tqos.qq.com`，纯 QoS，**无关** |
| `[100]` 是本地判定 | `[100]` 是 **Blaze 返回/映射的错误码** |
| 需要伪造 8000 端口 | 需要伪造的是 **Blaze 大厅连接** |

---

## 3. 未在抓包中出现 Blaze 连接的含义

整个 240 秒采集里，游戏**从未建立任何 Blaze 大厅连接**。
结合 `BD_LOGIN_QUEUE_*` / `DWLOGON_*` / `DW_ACCOUNT_*` 的存在，
启动链应该是：

```
TCLS(账号/目录)  ->  IIPS/TQoS(网络质量)  ->  DW_LOGON(登录)
     ->  DW_ACCOUNT_LOGIN_COMPLETE  ->  DW_LOBBY_CONNECT(连大厅)
```

`[100]` 出现在 **DW_LOGON 之后、DW_LOBBY_CONNECT 之前或之中**。
由于抓包里没有 Blaze TCP 连接，说明失败发生在**更早的一步**：
客户端还没拿到"该连哪个 Blaze 主机"的下发，就已经报错了。

---

## 4. 下一步（优先级排序）

### 4.1 找到 Blaze 主机名从哪来

CoD 系列用 dvar 配置 Blaze 地址，常见形式：

```
onlinegame  /  dwlobbyhost  /  lobbyhost  /  blazehost  /  title_id
```

需要：

1. 在 EXE 中定位 `dwLogonStart` 被调用前的 dvar 读取点；
2. 找到默认值或配置文件来源（`mp/*.cfg`、`players/config_mp.cfg`）；
3. 确认被谁覆盖（TCLS 下发？注册表？命令行？）。

### 4.2 确认 `[100]` 对应的 BD 常量

`bdLobbyErrorCode` 是枚举。需要确认 `100` 落在哪个
`BD_LOBBY_*` / `BD_*` 常量上，才能知道"客户端到底在抱怨什么"。

### 4.3 战术提醒

即使伪造出 Blaze 大厅，它也需要：

- `${CODOID}` / `${CODO_JUMP_SIGNATURE}` / `${CODO_OPENID}` 等身份字段
- `BD_LOBBY_PROTOCOL_VERSION_FAILURE` 暗示存在**协议版本协商**
- `title_id` / `zone` 等由 TCLS 下发的常量

也就是说，**Blaze 大厅的伪造难度远高于 IIPS/TQoS**，
这解释了为什么社区里 IW4X 能重写多人战局，却没人重写过 CODOL 大厅。

---

## 5. 本轮交付物

| 文件 | 用途 |
|---|---|
| `_probe_100_dll.py` | 扫描 EXE/DLL 中 `[100]`、`lobby`、中文文案 |
| `_dw_lobby.py` | 提取 `DW_*` / `BD_*` 字符串族 |
| `_qos_payload.py` | 重组 `182.50.14.56:8081` QoS 载荷（确认单向、加密） |
| `_find_error_strings.py` | 全盘扫描错误文案 |
| `_lobby_round2.py` | 第二轮抓包的 AFD/PktMon 汇总 |
| `_dns_map.py` | 从 PktMon 提取 DNS 域名到 IP 映射 |
