# 05 — 协议证据边界

## 1. 协议分级（必须原样保留）

| 协议 | 家族 | 状态 | 允许用途 |
|---|---|---|---|
| 最终 CODOL 游戏协议 | FinalCodolGame | **UNKNOWN** | 仅保留接口；禁止解码/编码/猜测 |
| 本地 2697 服务端语料 | Local2697 | PROJECT_IMPLEMENTATION_CONFIRMED | 离线测试与本地模拟 |
| 实机抓包 legacy 路径 | Legacy3333 | PROJECT_IMPLEMENTATION_CONFIRMED | 既有抓包链路；不等价最终 CODOL |
| 项目侧 usercmd/snapshot 宽度表 | 项目制品 | PARTIAL / CONTRADICTED | 内部模型与离线参考 |

## 2. 禁止推断项

依据 046 `05_CLIENT_PATH_MAPPING.md`：

- ❌ 不得把 TQOS/TDR 解包器（`0x87C110/0x87D5A0`）当作游戏 netfield/delta 解码器。
- ❌ 不得把 `0x87D5A0` 路径当作游戏业务入口。
- ❌ 不得用移动资料字段宽度表反推官方线格式（`N-3`）。
- ❌ 不得用项目侧实跑成功证明官方协议已复原（`N-4`）。
- ❌ 不得照搬 IW4x/CoD4x 的 opcode 或 snapshot 布局。

## 3. 代码层强制

- `FinalCodolGameDecoder` 对任何输入返回 `NotImplemented` + `UnsupportedFormat`，**不回落**。
- `ProtocolCodecRegistry` 默认不注册 2697；必须显式 `Register`。
- `ClientSession.MarkConnectedByVerifiedHandshake(false)` 直接进入 `Disconnected`。

## 4. 允许的结论等级

- `OFFICIAL_CLIENT_CONFIRMED`：本轮未新增任何此类协议结论。
- `PROJECT_IMPLEMENTATION_CONFIRMED`：本工程模块与其离线测试。
- `UNKNOWN`：最终 CODOL handshake/opcode/reliable/snapshot/gamestate。
