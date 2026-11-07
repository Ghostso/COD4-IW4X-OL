# 02 — 源码血统与分叉矩阵 / SOURCE LINEAGE & FORK MATRIX

> 分类：`同源已证实` / `实现高度相似` / `机制相同、实现不同` / `存在差异` / `无法对应`
> 纪律：不凭函数名、片段相似或 RVA 相同认定对应关系。

---

## 1. 血统总图

```
        Quake3 引擎（COD 通用网络栈）
                 │
        ┌────────┴────────┐
        │                 │
   CoD4x_Server        IW4x-client
     (AGPL)             (仅客户端)
        │  netchan_t 1:1 相同（共享 Quake3 祖先）
        │
        │  fork（字面证据：q_shared.h "IW4OL, a fork of CoD4x"）
        ▼
    OLD / 1113 服务端（+ CODOL 专用层 codol\*）
        │
        │  PORTED_CODE（同族延续 + 2697 层）
        ▼
      2697 服务端

   独立：ol-mod（自述不基于 IW4x）；C# codec（自研）
```

## 2. 逐对照裁定

| 对照对 | 裁定 | 依据 |
|---|---|---|
| OLD ↔ 1113 | **同源已证实**（`IDENTICAL_SOURCE`） | 82/83 顶层 `.c` 字节相同；唯一差异 `g_sv_main.c` |
| OLD/1113 ↔ CoD4x | **同源已证实**（`PORTED_CODE`，fork） | `q_shared.h:6` 字面；`netchan.c` Jaccard 95.0%，`msg.c` 81.9% |
| OLD/1113 ↔ CoD4x（`codol\` 层） | **存在差异** | CoD4x 无 `codol\` 子树；OLD 有 1,844 处 `CODOL` 标记，CoD4x 0 处 |
| OLD/1113 ↔ 2697 | **同源已证实**（同族延续 + 常量级） | 同 EntryPoint/节区/工具链；传输常量 `0x489`/`0x24500`/`0x70cc729` 对应 |
| CoD4x ↔ IW4X（netchan） | **同源已证实**（共享 Quake3 祖先） | `netchan_t` 1:1 相同 |
| IW4X ↔ CODOL 客户端 | **无法对应** | 无源码血统证据；仅架构类比 |
| ol-mod ↔ IW4X | **机制相同、实现不同** | `AUDIT.md` 明示不基于 IW4x |
| CODOL 握手/加密 ↔ CoD4x/IW4x | **存在差异** | CoD4x/IW4x 无 cookie+ECDH |

## 3. 分叉差异矩阵（网络/消息相关文件）

| 文件 | OLD/1113 | CoD4x | 差异性质 |
|---|---|---|---|
| `netchan.c` | 有 | 有 | Jaccard 95.0%；OLD 含 `#ifdef CODOL_SERVER` + `CODOL_NetchanProcess` |
| `msg.c` | 有 | 有 | Jaccard 81.9%；OLD 多 192 行 |
| `sv_main.c` | 有 | 有 | Jaccard 74.7%；OLD 多 830 行（CODOL 定制） |
| `sv_client.c` | 有 | 有 | Jaccard 70.2% |
| `sv_snapshot.c` | 有 | 有 | Jaccard 67.0% |
| `huffman.c` | 有 | 有 | Jaccard 99.7%（几乎未改） |
| `cvar.c` | 有 | 有 | Jaccard 97.9% |
| `cmd.c` | 有 | 有 | Jaccard 97.6% |
| `sv_init_mp.cpp` | 有 | 有 | **100.0%** |

## 4. 常量级血统证据（2697 ↔ OLD）

| 2697 二进制常量 | 值 | OLD 源码常量 |
|---|---|---|
| `0x489`（1161） | CODOL_FRAGMENT_SIZE−1 | `codol_wire.h` |
| `0x24500` | 1162×128 | `CODOL_FRAGMENT_SIZE×CODOL_MAX_FRAGMENTS` |
| `0x70cc729` | `ceil(2^37/1162)` | 分片步进 |
| `0x1fffffff` | 29 位序列掩码 | netchan 掩码 |

**读取位置：** `_CODOL_NetchanTransmit` RVA `0x999B6`；`_CODOL_NetchanTransmitNextFragment` RVA `0x998D8`。

**本轮新增反证（重要）：** 相同常量在**客户端恢复镜像 `.text` 中命中 0 次**（`0x489`/`0x70CC729` 均无）。→ **CODOL 分片传输是服务端侧机制**；客户端未显示同一分片常量。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| OLD/1113 是 CoD4x 的 fork | **同源已证实** |
| OLD ≡ 1113 | **同源已证实** |
| 2697 = Old/1113 同族 + 2697 层 | **同源已证实** |
| CoD4x/IW4X 共享 Quake3 netchan | **同源已证实** |
| ol-mod 独立于 IW4x | **同源已证实（否定关系）** |
| IW4X ↔ CODOL 客户端血统 | **无法对应** |
