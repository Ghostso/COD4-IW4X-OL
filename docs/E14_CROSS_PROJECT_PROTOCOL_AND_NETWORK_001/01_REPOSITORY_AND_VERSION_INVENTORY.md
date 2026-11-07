# 01 — 仓库与版本清单 / REPOSITORY & VERSION INVENTORY

> 只读静态分析 + 公开源码研究。原始样本未修改。
> 地址约定：RVA（VA = RVA + ImageBase）。客户端恢复镜像 ImageBase = `0x400000`；服务端 ImageBase = `0x400000`。

---

## 1. 冻结样本（本轮再次复核哈希）

| 样本 | 路径 | SHA-256 | 实测 |
|---|---|---|---|
| 客户端 EXE | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | ✔ 一致 |
| 恢复镜像 | `CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | ✔ 一致 |
| 2697 服务端 | `CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | ✔ 一致 |

**映射依据：** 恢复镜像 `.text` 与冻结客户端逐字节一致（E-06：8,047,104/8,047,104）。

## 2. 开源仓库（本地 git 副本，含提交 SHA）

| 项目 | 仓库 URL | 本地路径 | 分支 | 提交 SHA | 提交日期 |
|---|---|---|---|---|---|
| IW4X | `https://github.com/Iw4x/iw4x-client` | `IW4X\Client核心代码\iw4x-client` | — | `d1b175da1a25d31043246de103a702b206269e5a` | 2026-09-20 |
| COD4X | `https://github.com/callofduty4x/CoD4x_Server` | `DEV-BOOKING\_lineage021\CoD4x_Server` | — | `ddd65fce1a1093017bad2dbb6840d75d11c0d56f` | — |
| COD4X（第二副本） | 同上 | `DEV-BOOKING\_lineage021\iw4x-client` | — | `d1b175da…`（同 IW4X） | — |
| IW4X rawfiles | `https://github.com/Iw4x/iw4x-rawfiles` | `DEV-BOOKING\_lineage021\iw4x-rawfiles` | — | （未取） | — |

**线上核对（本轮实测）：** `api.github.com` 返回 HTTP 200；
- `iw4x/iw4x-client` 默认分支 `main`，`pushed_at` 2026-10-07
- `callofduty4x/CoD4x_Server` 默认分支 `master`，`pushed_at` 2026-09-18

**说明：** 本地副本 SHA 与线上 HEAD 不必一致；本报告全部比较以**本地副本 SHA** 为准，避免混版本。

## 3. 其他研究对象

| 对象 | 位置 | 形态 | 备注 |
|---|---|---|---|
| OLD 服务端源码 | 仅见 `EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy\src` | 源码（含 `codol\` 子树） | 标 `IW4OL, a fork of CoD4x` |
| 1113 服务端源码 | 同族（历史报告：82/83 `.c` 与 OLD 字节相同） | 源码 | 冻结记录见 `14_SERVER_KNOWLEDGE_ATLAS_001\13_...` |
| 2697 服务端 | `...\bin2697\codol_dedrun.exe` | 二进制 | 无源码 |
| OL-mod / ol-final | `_e1_regression\ol-mod-olfinal`（含 `.git`）；审计 `CODOL_OLMOD_AUDIT_20261009_094312\AUDIT.md` | 源码 + 审计 | 自述**不基于 IW4x** |
| 最终版 CODOL 客户端 | 见 §1 | 二进制 | E-01..E-13 证据 |

## 4. 本轮未取到的对象

| 对象 | 状态 |
|---|---|
| OLD/1113 独立源码树的完整副本 | **未在本地定位**（仅 experiment_copy 变体）；血统结论沿用 `14_SERVER_KNOWLEDGE_ATLAS_001\13_...` 的实测 Jaccard 与字面证据 |
| COD4X 提交历史 / blame | **未取**（无线上 git clone） |
| IW4X dedicated server 源码 | **未取**（仓库为客户端项目；见 `03` §IW4X 缺口） |
