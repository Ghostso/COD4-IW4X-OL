# TARGET_IDENTITY_REPORT — 目标客户端身份判定

**任务：** CODOL-BATTLE-SERVER-CLIENT-IDENTITY-007
**日期：** 2026-10-13（Asia/Shanghai）
**结论等级：** 只读身份调查，未修改任何源码或原始文件。

---

## 1. 结论（先读）

> **本地不存在能够确认（CONFIRMED）属于 CODOL 3.9.9.7 的客户端映像，也不存在达到 PROBABLE 的 3.9.9.7 候选。**

工作区实际存在 3 个版本的客户端二进制，全部明确属于其他版本：

| 版本 | 代表 EXE SHA-256 | 判定 | 说明 |
|---|---|---|---|
| 2.6.9.7 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | `CONFIRMED` | 学习样本 |
| 3.3.3.3 族（FileVersion 1649370） | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | `PROBABLE` | 学习样本 |
| 1.1.1.13 | `904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6` | `CONFIRMED` | 学习样本 |

---

## 2. 判定标准（沿用任务要求）

| 等级 | 含义 |
|---|---|
| `CONFIRMED` | 存在可复核的直接证据，足以确认目标版本 |
| `PROBABLE` | 存在多项支持证据，但缺少决定性依据 |
| `UNKNOWN` | 只能找到文件或名称，无法确认版本 |
| `REJECTED` | 证据明确表明属于其他版本 |

**硬性纪律：** 不得仅凭目录名、文件名、文件时间戳或版本相似性认定 3.9.9.7。

---

## 3. 检索范围与结果

### 3.1 检索范围

- `D:\BaiduNetdiskDownload\使命召唤OL`（全递归，含 `COD OL`、`工具`、`backups`、`run_codol_001`、`_e1_regression`、`CODOLServer` 等）。
- `D:\BaiduNetdiskDownload\CODOL.NET\Game`（`CODOL_1.1.1.13`、`CODOL_2.6.9.7`）。
- `D:\BaiduNetdiskDownload\CODOL_2697_Launcher`。
- `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)`。
- `D:\BaiduNetdiskDownload\CODOL-201506-2.6.9.7`。
- `E:\CODOL_SANDBOX`（深度 ≤5）。

### 3.2 结果

- 命名的客户端 PE 映像共 **13 个不同 SHA-256 组**（含 `.bak` 与日志/注解等非 PE 项）。
- **`out.exe`（ol-mod 记录的去壳目标，SHA-256 `044c396c…257f9`）在本机不存在。**
- **没有任何文件的版本资源、二进制字符串或清单指向 3.9.9.7。**
- 全工作区文本资料中 `3.9.9.7` 仅出现于 10 个既有报告文件，且均在“目标版本”语境，不含任何样本证据。

---

## 4. 各候选的版本归属依据

### 4.1 2.6.9.7 —— `CONFIRMED`（学习样本）

- 路径：`D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe`
- 大小：9,964,656 B；SHA-256：`353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`
- 直接证据（三重）：
  1. PE 版本资源 `FileVersion = 2.6.9.7`。
  2. 二进制内 ASCII 与 UTF-16 均含字符串 `2.6.9.7`。
  3. `CODOL_2697_Launcher\manifest.json` 声明 `version = 2.6.9.7`，且 `original_exe_sha256` 与本文件 SHA-256 完全一致。
- 因此判为 `CONFIRMED`，但**属于 2.6.9.7，不是 3.9.9.7**。

### 4.2 3.3.3.3 族 —— `PROBABLE`（学习样本）

- 路径：`D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe`
- 大小：7,841,344 B；SHA-256：`36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`
- 支持证据：
  - FileVersion / ProductVersion 资源均为 `1649370`。
  - 外部 ol-mod 仓库（`_e1_regression\ol-mod-olfinal`）的运行分发目标为该构建。
  - 工作区 46 份逐字节相同副本。
- 反证 / 缺口：
  - 二进制内**没有** `3.3.3.3` 字符串（ASCII/UTF-16 均为 0）。
  - 镜像被 TenProtect 加壳（`.tp3`×5 + `.tvm0`），静态字节与 ol-mod 记录的 `out.exe` RVA 期望不符。
  - `3.3.3.3` 归属来自外部仓库声明，本机无官方版本资源自证。
- 因此只能判为 `PROBABLE`，**不是 3.9.9.7**。

### 4.3 1.1.1.13 —— `CONFIRMED`（学习样本）

- 路径：`D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Client\codoMP_client_shipRetail.exe`
- 大小：20,918,752 B；SHA-256：`904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6`
- 直接证据：
  1. PE 版本资源 `FileVersion = 1.1.1.13`。
  2. 二进制内 ASCII 与 UTF-16 均含字符串 `1.1.1.13`。
  3. `CODOL.NET\config\games.json` 将 `CODOL_1.1.1.13` 目录映射为 `ver = 1.1.1.13`。
- 因此判为 `CONFIRMED`，但**属于 1.1.1.13，不是 3.9.9.7**。

### 4.4 其余样本

- `codoMP_client_shipRetailBase.dll`（60,327,992 B，`ef75220d…`）：3.3.3.3 族主 DLL，`PROBABLE`。
- `codoMP_client_shipRetailBase.image.bin`（60,362,752 B，`7505132f…`）：3.3.3.3 族运行时镜像，`PROBABLE`。
- `7b31168d…` 变体 EXE：3.3.3.3 族局部改动版，`PROBABLE`。
- `codol2697-static-candidate.bin`（12,571,648 B，`24b4ef25…`）：2.6.9.7 静态恢复镜像，`CONFIRMED` 归属、运行时等价性未证。
- `codoMP_client_shipRetail.exe.bak`（`a6c213c5…`）：1.1.1.13 学习族备份，`REJECTED` 作为目标。

---

## 5. 为什么 3.9.9.7 不能被任何现有样本代表

1. **版本号不匹配**：现有样本的版本资源与二进制串分别为 `1.1.1.13`、`2.6.9.7` 与构建号 `1649370`（3.3.3.3 族），无一项为 `3.9.9.7`。
2. **无直接来源声明**：没有任何 manifest、`games.json`、启动器配置或审计文件把某个本机文件标注为 3.9.9.7。
3. **相似性不构成身份**：3.3.3.3 与 2.6.9.7 同属 CODOL 引擎家族，但大小、SHA-256、节区、版本资源与代码字节均不同，不能互相替代，更不能推导出 3.9.9.7。
4. **目录名与时间戳不可用**：工作区内含大量沙箱/备份副本，目录名（如 `CODOL_2.6.9.7`）只反映配置意图，不作为 3.9.9.7 依据。

---

## 6. 结论

- 对问题“本地是否存在能确认属于 CODOL 3.9.9.7 的客户端映像？”的回答是 **否**。
- 对问题“具体路径与 SHA-256？”的回答是 **不适用（无该样本）**。
- 对问题“版本归属由哪些直接证据支持？”的回答是：**3.9.9.7 没有任何直接证据**；其他版本的直接证据已在上文逐条列出。
- 本轮不降低确认标准，不以其他版本替代目标版本。
