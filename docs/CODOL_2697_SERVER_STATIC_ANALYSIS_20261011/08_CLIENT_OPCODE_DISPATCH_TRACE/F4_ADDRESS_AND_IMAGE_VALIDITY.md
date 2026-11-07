# F4 — 地址与镜像有效性核验

> 阶段 F · 2026-10-12 · 仅静态分析。未启动、未注入、未补丁、未编译。

## 1. 样本

| 项目 | 值 | 等级 |
|---|---|---|
| 打包客户端 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | VERIFIED |
| 打包客户端 SHA-256 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | VERIFIED |
| 静态恢复镜像 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | VERIFIED |
| 恢复镜像 SHA-256 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | VERIFIED |
| ImageBase | `0x400000` | VERIFIED |
| .text | RVA `0x1000`，文件偏移 `0x400`，raw `0x7aca00` | VERIFIED |
| 本报告地址基准 | 题述 `0xA2E50`、`0xA2D90` 均为**映像 RVA**（VA = ImageBase + RVA） | VERIFIED |

## 2. 地址基准与阶段 E 工具错误

**x86 的 E8 rel32 目标永远是绝对虚拟地址（VA），不是 RVA。** 阶段 E 的部分脚本把 E8 目标直接当作 RVA 去读，导致若干读取核心函数被误判为“入口错位”。

- 题述函数在标准 PE RVA 下字节正确：
  - RVA `0xA2E50` → `55 8B EC 81 EC 44 04 00 00`（`push ebp; mov ebp,esp; sub esp,0x444`）
  - RVA `0xA2D90` → `55 8B EC 81 EC 08 04 00 00`
- `0xA2E50` 内部 `E8 rel32` 的目标是 VA：
  - `0xA2E87` 的 E8 目标 = `0x5AC1D0`（VA）；对应 RVA `0x1AC1D0`，该处字节 `55 8B EC 33 D2...`，是真实读取核心入口。
  - `0xA2EC0` 的 E8 目标同为 `0x5AC1D0`。
  - `0xA2F02` 的 E8 目标 = `0x5ACB00`（VA）；对应 RVA `0x1ACB00`，字节 `55 8B EC 51 8B 4D 0C...`。
- 若把这些 VA 直接当作 RVA 读取，会落在错误指令流（例如 `0x5AC1D0` 读作 RVA 时得到 `8A 5B 49 ...`）。

**等级：VERIFIED（字节级）。** 这不是恢复镜像混用两套基准，而是阶段 E 交叉引用扫描时缺少 `VA - ImageBase = RVA` 的转换。本阶段 F 已修正：F1/F2/F3 的调用者搜索同时核对 VA 与 RVA 两种字节形式。

## 3. 恢复镜像等价性

- 恢复镜像是 aplib 静态恢复结果，不是运行时解包观测、不是初始化后 dump。
- 镜像内部指令字节：VERIFIED。
- 运行时映射与恢复镜像完全一致：NOT-OBSERVED / BLOCKED。
- 因此：在恢复镜像中没有找到 `0xA2E50` 的调用者，不能表述为“原始客户端运行时绝对不存在该调用者”。正确表述是“在本恢复镜像的静态可解析范围内未找到”。
