# 02 — 握手协议证据(逐条,含证据等级)

**映像:** S-IMG `17cef6e0…f045`;`file_offset == RVA`;`VA = RVA + 0x400000`。
除显式标注外均为 `DIRECT_STATIC`。

---

## 1. 客户端识别的服务端→客户端命令词(证据支持)

来源:客户端分派器 `0x1C13A0..0x1C1EE0` 内的 `strcmp` 比较点。

| token | 字符串 RVA | 首个比较点 | 证据等级 |
|---|---|---|---|
| `challengeResponse` | 0x9BFEE8 | 0x1C1685 | `ClientEvidenceConfirmed` |
| `connectReject` | 0x9BFEFC | 0x1C1756 | `ClientEvidenceConfirmed` |
| `connectResponse` | 0x9BFF0C | 0x1C17B5 | `ClientEvidenceConfirmed` |
| `heartbeatresponse` | 0x9BFF1C | 0x1C18B6 | `ClientEvidenceConfirmed` |
| `statResponse` | 0x9BFF30 | 0x1C1964 | `ClientEvidenceConfirmed` |
| `disconnect_ack` | 0x9BFF40 | 0x1C1B0B | `ClientEvidenceConfirmed` |
| `echo` | 0x9BFF50 | 0x1C1B4B | `ClientEvidenceConfirmed` |
| `keyAuthorize` | 0x9BFF58 | 0x1C1BC3 | `ClientEvidenceConfirmed` |
| `loadingnewmap` | 0x9BFF70 | 0x1C1CAB | `ClientEvidenceConfirmed` |
| `fastrestart` | 0x9BFF90 | 0x1C1DF0 | `ClientEvidenceConfirmed` |

## 2. 客户端自身构造的请求格式串(证据支持)

| 格式串 | RVA | 构造点 | 说明 |
|---|---|---|---|
| `getchallenge 0 "%s"` | 0x9BFD04 | 0x1C071F | 客户端**发出**的挑战请求 |
| `connect %s "%s"` | 0x9BFE28 | 0x1C0D6F | 客户端**发出**的连接请求 |
| `heartbeat` | 0x9BFE40 | 0x1C0EBC | 心跳 |
| `stats` | 0x9BFE38 | 0x1C0E27 | 统计请求 |

**方向裁定:** 以上 4 条为 `ClientToServer`(客户端组帧发送);§1 的 10 条为 `ServerToClient`
(客户端 `strcmp` 接收比较)。方向来自 xref 站点所在函数,不是命名推断。

## 3. 证据支持的边界(能做什么)

- **能**:识别/解析连接无关文本帧的**命令边界**(token + 空格 + 参数);
- **能**:对上述 14 个 token 做**方向校验**与**未知拒绝**;
- **能**:按客户端自身格式串的**字面形状**解析 `getchallenge`/`connect` 的字段切分。

## 4. 未证实面(禁止补齐)

`UnprovenHandshakeSurface`(代码常量,8 项):

| # | 未证实项 | 为什么不能补齐 |
|---|---|---|
| 1 | challenge 算法 | 映像只证明串形状,未证明生成/校验算法 |
| 2 | nonce 长度/编码 | 无服务端样本,客户端不构造 |
| 3 | challenge 校验规则 | 比较点是 token 名比较,不是数值校验 |
| 4 | 鉴权 / `keyAuthorize` 载荷 | 只有 token 名,无载荷格式 |
| 5 | 连接序号 | `connect %s "%s"` 的两个字段语义未证 |
| 6 | OOB 前缀 / magic | 未定位未连接 socket 前缀写入点 |
| 7 | 响应封装 | 客户端只 `strcmp` token,未见封装结构 |
| 8 | connect ↔ challenge 关联字段 | 两个字段的对应关系未证 |

## 5. 048 继承与本轮差异

| 项 | 048 | 049 |
|---|---|---|
| 词表与方向 | ✅ 已定 | ✅ 继承,逐串复核一致 |
| 请求格式串 | ✅ 已定 | ✅ 继承 |
| 响应载荷 | 未证 | 仍未证;**代码层显式隔离** |
| 与 2697 关系 | 禁止混用 | 禁止混用(无回退) |

> **纪律:** 客户端存在命令字符串 ≠ 服务端响应格式已确认。本轮所有响应处理均为**接口**,
> 只有 `AcceptConnectResponse(evidenceId)` 这一条显式、带证据 id 的路径能进入 `Connected`。
