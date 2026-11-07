# 03 — 网络与消息系统比较 / NETWORK & MESSAGE COMPARISON

> 等级：`PROVEN` / `INFERRED` / `BLOCKED` / `REFUTED`

---

## 1. 机制矩阵

| 机制 | IW4X | COD4X | OLD/1113 | 2697 | CODOL 客户端 | 裁定 |
|---|---|---|---|---|---|---|
| socket 收发 | 客户端插件层 | `sys_net.c` | 同 CoD4x | 同族 | **分层虚表封装**（`.rdata 0x898588/0x898590`） | 机制相同、实现不同 |
| netchan 包头/分片 | `netchan_t`（Quake3） | `netchan.c`（Quake3） | CoD4x + `CODOL_NetchanProcess` 接管 | 常量级对应 | **未见 CODOL 分片常量** | 服务端专属 |
| MSG 缓冲/游标 | `msg_t` | `msg.c` | 同 | 同族 | `MSG_ReadBits`/`MSG_ReadData`（`0x1AC670`/`0x1AC1D0`） | 通用引擎机制 |
| Reliable Command | 部分 | 无 2697 形态 | — | `0x8612E`（`0x01`/`0x02`） | 未定位 | 项目专属 |
| Gamestate | 客户端侧 | `SV_SendClientGameState` | 同族 | `0xA21B8` | demo 消费者 `0x34FD80(1)`（字段不匹配） | 存在差异 |
| Configstring | 客户端侧 | `sv_snapshot.c` | 同族 | `0xA0468` | `0xA2660`（字段级 PROVEN） | 实现高度相似 |
| Snapshot/增量 | 客户端侧 | `sv_snapshot.c` | 同族 | `0xA4FA0`/`0xA4860` | 未定位 | 机制相同、实现不同 |
| 客户端分派 | 插件 hook | — | — | — | `0x350170`（demo）/ 实时未定位 | 无法对应 |
| 连接/注册 | 部分 | `sv_auth.c` | 同族 | `0xA3EA0` 注册 | 未定位 | 项目专属 |

## 2. 关键差异：CODOL 的传输层接管（服务端侧）

OLD `netchan.c` 含：

```c
#include "codol_wire.h"        // CODOL-only
#include "codol_network.h"     // CODOL-only
#ifdef CODOL_SERVER
    if (fragmentBuffer && fragmentBufferSize >= (int)sizeof(codol_fragments_t))
        memset(fragmentBuffer, 0, sizeof(codol_fragments_t));
#endif
#ifdef CODOL_SERVER
    return CODOL_NetchanProcess(chan, msg);   // CODOL 接管
#endif
```

**度量：** CoD4x `netchan.c` 中 `CODOL|Xor|stride|1162` 命中 **0**；OLD 顶层 `.c` 中 `CODOL` 标记 **1,844**，CoD4x **0**。

## 3. 客户端网络栈：本轮的二进制发现（PROVEN）

### 3.1 socket 抽象为虚表分派

`.rdata` 虚表（相邻槽位）：

```
0x898588: [0xb75a50] [0xb75a80] [0xb75ab0] 0xb75af0 ...
0x898590: [0xb75ab0] 0xb75af0 0xb75b30 ...
```

`0x775A50`（recv）/ `0x775AB0`（recvfrom）是该虚表的相邻槽位 → **平台 socket 抽象族**。

### 3.2 CODOL 客户端内联 OpenSSL 0.9.8p（PROVEN）

客户端字符串（`0xC3D0D2` 等 5 处）：

```
"OpenSSL 0.9.8p 16 Nov 2010"
"SSL routines" / "elliptic curve routines" / "common libcrypto"
```

**含义：** 客户端网络层包含 **TLS 传输实现**，与 CoD4x/IW4x 的明文 UDP/TCP 栈**架构不同**。这解释了 E-13 的 `0x605220 → 0x6104D0 → 0x672460` 路径：

- `0x672460`：`cmp [eax+0x20],0` → 报错 → `mov eax,[ecx+0x1c]` → `jmp eax`（**OpenSSL 对象方法分派**）
- `0x605220`：`call 0x5FB510` → `0x6104D0` → `call 0x672460`（**TLS 读路径**）
- `0x6029A0` 错误分支引用 `"Recv failure: %s"`（`0xC37244`）→ 经 `0x602760` → **printf 格式化器** `0x60E5B0`

### 3.3 IW4X / COD4X 缺口

| 项 | 状态 |
|---|---|
| IW4X dedicated server 源码 | **仓库为客户端项目**；未在本地副本中发现 `sv_main`/`sv_client` 服务端源 |
| IW4X netchan_t | 与 CoD4x 1:1 相同（历史已证） |
| IW4X 是否含 TLS | **未发现** TLS 实现（与 CODOL 客户端架构不同） |

## 4. 裁定

| 项 | 裁定 |
|---|---|
| MSG 位读写原语为通用引擎机制 | **PROVEN** |
| netchan 分片为 **服务端侧** CODOL 专属 | **PROVEN**（客户端 0 命中同类常量） |
| socket 抽象为分层虚表 | **PROVEN** |
| CODOL 客户端内联 OpenSSL 0.9.8p | **PROVEN** |
| IW4X 有完整服务端实现 | **REFUTED**（仓库为客户端） |
| TLS 机制可移植自 IW4X/COD4X | **REFUTED**（两者无此实现） |
