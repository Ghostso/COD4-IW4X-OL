# 09 — 可复用组件与协议差异 / REUSABLE COMPONENTS & DELTAS

> 可复用性裁定：`可直接复用` / `改造后复用` / `不能复用` / `未知`

---

## 1. 可直接复用

| 组件 | 来源 | 依据 |
|---|---|---|
| Huffman 表与初始化 | CoD4x `huffman.c` | Jaccard 99.7% 与 OLD/2697 一致 |
| cvar 子系统 | CoD4x `cvar.c` | Jaccard 97.9% |
| 命令解析 | CoD4x `cmd.c` | Jaccard 97.6% |
| `sv_init_mp.cpp` 骨架 | CoD4x | **100.0%** |
| MSG 位读写原语（服务端侧） | CoD4x `msg.c` | Jaccard 81.9%；2697 有对应符号 |
| netchan 基础结构 | CoD4x `netchan.c` | Jaccard 95.0%（引擎部分） |

## 2. 改造后复用

| 组件 | 需要的改造 | 依据 |
|---|---|---|
| netchan 传输 | 需加 CODOL 分片层 | OLD 用 `#ifdef CODOL_SERVER` + `CODOL_NetchanProcess` 接管 |
| Gamestate 写入 | 需替换为 2697 字段序 + Configstring 子帧 | `0xA21B8` vs CoD4x `SV_SendClientGameState` 差异 |
| Snapshot | 需对齐 2697 `0xA4FA0`/`0xA4860` | `sv_snapshot.c` Jaccard 67.0% |
| 可靠命令 | 需实现 2697 `0x01`/`0x02` | 服务端专属，CoD4x 无对应 |
| 客户端分派逻辑 | **不可复用**（需 CODOL 证据重写） | 见 §3 |

## 3. 不能复用

| 组件 | 原因 |
|---|---|
| IW4X/CoD4x 客户端网络栈 | CODOL 客户端为虚表分派 + 内联 TLS，架构不同 |
| IW4X/CoD4x 明文 UDP 传输 | CODOL 客户端含 OpenSSL 0.9.8p（TLS） |
| CODOL 握手（cookie + ECDH） | 自研，无开源对应 |
| CODOL 客户端 Gamestate 消费 | 实时消费者未定位，无法复用任何实现 |
| `.tvm0` 保护层 | 无开源对应 |

## 4. 仍未知

| 项 | 缺失 |
|---|---|
| 网络虚表构造者 | 对象实例化路径未定位 |
| 应用层消息分派器 | 未定位 |
| 实时 `0x03` 消费者 | 未定位 |
| `0x04`/`0x06` 客户端值级识别 | 未定位 |
| TLS 与 netchan 的衔接 | TLS 解密后的数据去向未定位 |

## 5. 服务器实现建议（基于证据）

| 模块 | 建议 |
|---|---|
| 传输层 | 复用 CoD4x netchan 骨架 + 实现 CODOL 分片层（常量已证） |
| Huffman/压缩 | 直接复用 CoD4x |
| 可靠命令 | 依 2697 二进制证据重新实现（`0x8612E` 字段序已 PROVEN） |
| Gamestate 编码 | 依 `0xA21B8` 字段序实现；**但客户端验证 BLOCKED** |
| Configstring 编码 | 依 `0xA0468` 字段序实现（含本轮修订的 A2=11 bit） |
| 客户端互操作验证 | **不可**在实时消费者定位前声称 |

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 服务端引擎层可复用 CoD4x | **可直接复用** |
| 服务端传输层 | **改造后复用** |
| 客户端网络栈 | **不能复用** |
| 协议互操作 | **未知**（依赖实时消费者定位） |
