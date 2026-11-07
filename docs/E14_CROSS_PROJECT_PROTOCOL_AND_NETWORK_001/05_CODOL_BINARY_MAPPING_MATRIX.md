# 05 — 开源 ↔ CODOL 二进制映射矩阵

> 映射裁定：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`
> 纪律：源码映射只提假设，不自动证明客户端同实现。

---

## 1. 已证实映射（常量级 / 字面证据）

| 机制 | 开源来源 | CODOL 二进制证据 | 裁定 |
|---|---|---|---|
| 分片尺寸 1161 | OLD `codol_wire.h` `CODOL_FRAGMENT_SIZE−1` | 2697 `0x999B6 cmp eax,0x489` | **PROVEN** |
| 分片缓冲 148736 | OLD `1162×128` | 2697 `0x24500` | **PROVEN** |
| 分片步进 | OLD `ceil(2^37/1162)` | 2697 `0x998D8` `0x70CC729` | **PROVEN** |
| 序列掩码 29 位 | OLD netchan | 2697 `0x1fffffff` | **PROVEN** |
| OLD 是 CoD4x fork | 字面 `q_shared.h:6` | — | **PROVEN** |

**本轮反证：** 上述 4 个常量在**客户端镜像 `.text` 中命中 0 次** → 属**服务端侧**机制。

## 2. 引擎级映射（符号名 + 控制流形状）

| 2697 符号 | RVA | 开源对应 | 裁定 |
|---|---|---|---|
| `_Com_Init` | `0x9B04` | CoD4x `Com_Init` | **PROVEN**（同族） |
| `_MSG_WriteByte` | `0x2B40A` | CoD4x `MSG_WriteByte` | **PROVEN**（同族） |
| `_Netchan_Transmit` | `0x30D58` | CoD4x `Netchan_Transmit` | **PROVEN**（同族） |
| `_Huffman_InitMain` | `0x24F8D` | CoD4x `Huffman_InitMain` | **PROVEN**（Jaccard 99.7%） |
| `_SV_WriteReliableCommand` | `0x8612E` | **无对应** | 项目专属 |

## 3. 客户端映射（本轮新增）

| 客户端机制 | 候选开源对应 | 证据 | 裁定 |
|---|---|---|---|
| `MSG_ReadBits` `0x1AC670` | CoD4x/IW4X `MSG_ReadBits` | 位序 LSB-first、`and 7`/`sar 3` 形状一致 | **实现高度相似** |
| `MSG_ReadData` `0x1AC1D0` | CoD4x `MSG_ReadData` | 逐字节复制，无位逻辑 | **实现高度相似** |
| socket 虚表 `0x898588/0x898590` | IW4X/CoD4x `netchan_t` | **架构不同**：IW4X/CoD4x 为结构体直接调用，非虚表分派 | **机制相同、实现不同** |
| `0x60E5B0` | `vsnprintf`/`_vsnprintf` | `'%'` 判定 + 7 项转换符跳转表 + putc 回调 | **机制相同、实现不同**（通用 C 运行时） |
| TLS 路径 `0x605220`→`0x6104D0`→`0x672460` | **无** | 内联 OpenSSL 0.9.8p | **无法对应**（IW4X/CoD4x 无 TLS） |

## 4. 无法对应 / 项目专属

| 项 | 说明 |
|---|---|
| CODOL 握手（cookie + ECDH） | CoD4x/IW4x 无；属 CODOL 自研 |
| CODOL `0x01`/`0x02` reliable command 2697 形态 | 服务端专属 |
| `_CODOL_NetchanTransmit*` 分片族 | 服务端专属（客户端无同类常量） |
| CODOL 客户端 TLS 传输 | 项目专属（内联 OpenSSL） |
| 客户端 9 收包函数虚表族 | 与 IW4X/CoD4x 架构不同 |

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 服务端引擎函数可在 CoD4x 源码中定位 | **PROVEN** |
| 服务端常量可在 OLD 源码中定位 | **PROVEN** |
| 客户端网络栈可直接映射到 IW4X/CoD4x | **REFUTED**（架构 + TLS 差异） |
| 客户端 MSG 原语与 CoD4x 形状一致 | **实现高度相似**（INFERRED） |
