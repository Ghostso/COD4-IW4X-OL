# 08 — 实时消息入口与 Gamestate 消费者裁定

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 分层定位表

| 层 | 本轮定位 | 裁定 |
|---|---|---|
| **socket API** | IAT：`recv` `0xBae490`、`recvfrom` `0xBae50C`、`send` `0xBae4C8`、`sendto` `0xBae504` | **PROVEN** |
| **网络抽象层** | 虚表 `.rdata 0x898588`/`0x898590`；槽位 `0x775A50`(recv)/`0x775AB0`(recvfrom)；另 `0x1B0430`/`0x6029A0`/`0x605220` 等 | **INFERRED**（构造者 BLOCKED） |
| **传输加密层** | OpenSSL 0.9.8p（`0xC3D0D2`）；TLS 读 `0x605220`→`0x6104D0`→`0x672460` | **PROVEN** |
| **应用层消息分派** | **未定位** | **BLOCKED** |
| **Gamestate `0x03` 消费者** | **未定位**（已定位的 `0x34FD80(1)` 属 demo 且字段不匹配） | **BLOCKED** |
| **内部 Configstring 子帧处理器** | `0x354100` case 6（属 demo 链） | INFERRED（demo） |
| **Configstring body reader** | `0xA2660`（字段级 PROVEN） | 实时归属 **BLOCKED** |

## 2. E-13 断点的本轮进展

| E-13 断点 | E-14 结果 |
|---|---|
| `0x60E5B0` 是"协议状态机"候选 | **REFUTED**（实为 vsnprintf） |
| `[ebp-0xd2c]` 是协议处理器指针 | **REFUTED**（实为 putc 回调） |
| `0x6029A0` 是协议处理 | **REFUTED**（实为 recv 错误日志路径） |
| `0x605220` 是"独立协议路径"候选 | **REFUTED**（实为 TLS 读路径） |
| 网络虚表构造者 | **仍 BLOCKED** |
| 实时 `0x03` 消费者 | **仍 BLOCKED** |

**净效果：** E-13 的 4 条候选路径中有 **3 条被排除**（`0x6029A0`/`0x605220`/`0x60E5B0`），剩余候选为 **`0x1B0430`** 与 **`0x78772D`**（含 `.tvm0`）。

## 3. `0xA2660` 的实时归属

| 判据 | 结果 |
|---|---|
| 字段级行为（count1/索引/A1/A2/A3） | **PROVEN** |
| 3 个调用点（`0x3512A0`/`0x352F80`） | 均属 demo 链 |
| 实时上游 | **未定位** |

**裁定：`0xA2660` 是 Configstring body reader（PROVEN）；"实时"归属 BLOCKED。**

## 4. 本轮新增的结构性认识

**CODOL 客户端网络栈与 IW4X/CoD4x 架构不同：**

| 项 | IW4X/CoD4x | CODOL 客户端 |
|---|---|---|
| socket 抽象 | `netchan_t` 结构体直接调用 | **虚表分派**（`.rdata 0x898588`） |
| 传输加密 | 无 | **内联 OpenSSL 0.9.8p（TLS）** |
| 分片常量（1161 等） | 服务端侧 | **客户端 0 命中** |
| 错误输出 | 直接格式化 | `0x60E5B0` vsnprintf + putc 回调 |

**含义：** 不能用 IW4X/CoD4x 的客户端网络代码直接推断 CODOL 客户端行为；**必须**依赖 CODOL 二进制直接证据。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| socket API 层 | **PROVEN** |
| TLS 加密层 | **PROVEN** |
| 网络抽象层 | **INFERRED** |
| 应用层消息分派 | **BLOCKED** |
| 实时 `0x03` 消费者 | **BLOCKED** |
| `0xA2660` 实时归属 | **BLOCKED** |
