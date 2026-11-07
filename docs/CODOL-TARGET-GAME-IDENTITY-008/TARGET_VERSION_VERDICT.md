# TARGET_VERSION_VERDICT — 目标游戏版本判定

**任务：** CODOL-TARGET-GAME-IDENTITY-008
**日期：** 2026-10-13（Asia/Shanghai）
**目标目录：** `D:\BaiduNetdiskDownload\使命召唤OL\COD OL`（用户指定）

---

## 1. 一句话结论

> **目标游戏实例的版本可以确认：它是 CODOL `3.19.26.22`（构建号 `1649370`，构建日期 `2021-05-07`）。**
> **它不是 3.9.9.7。** 目标目录中没有任何 3.9.9.7 证据。

---

## 2. 判定等级

| 结论 | 等级 | 说明 |
|---|---|---|
| 目标实例 = CODOL 3.19.26.22 / 构建 1649370 | **CONFIRMED** | 四类独立直接证据互相一致（见 §3） |
| 目标实例 = CODOL 3.9.9.7 | **REJECTED** | 无任何支持证据；`3.9.9.7` 字符串在全部 2,973 个文件中命中 0 次 |
| 目标实例 = 2015-06-15 的 3.3.3.3 QA 构建 | **REJECTED** | 二者的 PE 时间戳、SizeOfImage、发布标签与版本资源均不同（见 §5） |
| 目标实例 = 2.6.9.7 / 1.1.1.13 | **REJECTED** | 属其他独立安装目录，不在目标目录内 |

---

## 3. 直接证据（四类，逐条可复核）

### 证据 1 — PE 版本资源（VS_FIXEDFILEINFO，二进制自证）

对象：`COD OL\codoMP_client_shipRetail.exe`

| 字段 | 实测值 |
|---|---|
| `VS_FIXEDFILEINFO.FileVersion` | **3.19.26.22** |
| `VS_FIXEDFILEINFO.ProductVersion` | 0.0.0.0 |
| `StringFileInfo.FileVersion` | **1649370** |
| `StringFileInfo.ProductVersion` | 1649370 |
| `FileDescription` / `ProductName` | Call of Duty Online |
| `CompanyName` | Activision Blizzard |
| `FileHeader.TimeDateStamp` | `0x6096930A`（2021-05-08T13:32:58Z） |
| `OptionalHeader.SizeOfImage` | `0x0E659000` |

> 说明：该 PE 同时携带“机器可读版本 3.19.26.22（VS_FIXEDFILEINFO）”与“构建号 1649370（字符串资源）”，二者不矛盾——前者是游戏版本，后者是构建号。

### 证据 2 — TCLS 客户端版本配置（明文 XML）

对象：`COD OL\TCLS\mmog_data.xml`

```xml
<VersionUpdateData>
  <VersionConf>16:16:16:16</VersionConf>
  <ClientConf>
      <VersionData>
           <Version>3.19.26.22</Version>
           <Uin>0</Uin>
           <WorldID>0.0.0.0</WorldID>
       </VersionData>
       <VersionDemoStr>3.19.26.22</VersionDemoStr>
       <resv1>3.19.26.22</resv1>
  </ClientConf>
</VersionUpdateData>
```

**一致性佐证（跨安装对照）：** 该文件在各安装中恰好等于游戏版本标签：

| 安装目录 | `TCLS\mmog_data.xml` 的 `<Version>` | 安装标签 |
|---|---|---|
| `CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Client` | `1.1.1.13` | 1.1.1.13 |
| `CODOL.NET\Game\CODOL_2.6.9.7` | `2.6.9.7` | 2.6.9.7 |
| **`COD OL`（目标）** | **`3.19.26.22`** | **本轮目标** |

即：TCLS 版本字段是可靠的安装级版本标识，而目标实例的该字段为 `3.19.26.22`。

### 证据 3 — Windows 错误报告（操作系统级）

对象：`run_codol_001\runs\*\application_events.json`（WER 崩溃事件，进程为 `codoMP_client_shipRetail.exe`）

```
Faulting application name: codoMP_client_shipRetail.exe, version: 3.19.26.22, time stamp: 0x6096930a
```

- 全部 70 条记录中，`version: 3.19.26.22` 与 `time stamp: 0x6096930a` **完全一致**。
- `0x6096930a` 精确等于目标 EXE 的 PE `TimeDateStamp`（`0x6096930A`）。
- 这是操作系统按 PE 版本资源记录的版本，独立于项目文档，构成强直接证据。

### 证据 4 — IIPS 资源清单构建标签

对象：`COD OL\IIPS\IIPSFilelist.ini`

- `FileCount = 974`，全部 974 条 `FileUrl` 均形如：
  `http://rshlinux01/Release2/1649370.2021-05-07.14-11-50/pc/Client/IIPS/IIPSDownload/...`
- 构建标签唯一值：`1649370.2021-05-07.14-11-50`
- 与 PE 字符串版本 `1649370`、PE 时间戳 `2021-05-08` 相互印证（构建 2021-05-07/08）。

---

## 4. 反证：`3.9.9.7` 在目标目录中不存在

| 核验动作 | 结果 |
|---|---|
| 全目录文本检索（659 个文本 + 其余小文件）`3.9.9.7` | **0 命中** |
| 全部 EXE/DLL 的 ASCII + UTF-16 子串扫描 `3.9.9.7` | **0 命中** |
| 全部 2,973 个文件前 4MB 的 ASCII 扫描 `3.9.9.7` | **0 命中** |
| 目标目录中任何清单 / 配置 / 日志的 `3.9.9.7` | **0 命中** |

> 注：`3.9.1` / `3.9.2.1` / `3.9.2.2` 等命中均来自 `Cross\Apps\CQS\QTalk\QTLicense.txt` 的条款编号，与游戏版本无关，已排除。

**结论：** 目标目录内不存在任何支持 3.9.9.7 的证据。

---

## 5. 与“3.3.3.3 QA 构建”的差异（推翻 007 的隐含归属）

007 依据外部 ol-mod 仓库，将 `36997674…`（本目标 EXE）标注为“3.3.3.3 族”。本轮以目标目录自身证据推翻该归属：

| 维度 | 目标实例（本轮实测） | 旧记录的 3.3.3.3 QA 构建 |
|---|---|---|
| 游戏版本 | **3.19.26.22** | 3.3.3.3 |
| PE `TimeDateStamp` | **`0x6096930A`（2021-05-08）** | `0x57611E31`（2015-06-15） |
| `SizeOfImage` | **`0x0E659000`** | `0x0C72A000` |
| 构建号 | 1649370 | — |
| 发布标签 | `1649370.2021-05-07` | 2015-06-15 |

`0x57611E31` / `0x0C72A000` 在 ol-mod 源码中被明确记为 **3.3.3.3 QA 客户端**（`CodolClientPatches.cpp:45-46`），且该项目在 2026-08-18（`55fcdbf`）已把门禁整体翻转到 `0x6096930A` / `0x0E5D6000`（即本目标实例所属的 1649370 构建）。

**因此：** 本目标客户端属于 **1649370 / 3.19.26.22** 构建；将其称为“3.3.3.3”是不准确的。

---

## 6. 目标客户端 SHA-256 清单

| 对象 | 路径 | 大小 (B) | SHA-256 | 判定 |
|---|---|---:|---|---|
| 入口 EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | CONFIRMED（目标实例；3.19.26.22 / 1649370） |
| 主引擎 DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | CONFIRMED（目标实例主模块） |
| DLL 重定向变体 | `COD OL\codoMP_client_shipRetail.exe.local\codoMP_client_shipRetailBase.dll`（及 `...Base.dll.local\...`） | 60,327,992 | `3d2b338da69f2544fe29db8d3da3b3c2de92f5de9e8b5a9fb085a4c4ecc20dfd` | CONFIRMED（同版本，6 字节改动的本地覆盖副本） |

---

## 7. 对项目目标的影响（事实陈述，不改变目标）

1. 用户既定目标版本为 **3.9.9.7**；用户指定目标目录 `COD OL` 的实际实例为 **3.19.26.22 / 1649370（2021）**。**二者不一致。**
2. 本机**同时**存在其他独立版本实例：`CODOL.NET\Game\CODOL_1.1.1.13`、`CODOL.NET\Game\CODOL_2.6.9.7`。这些是独立安装，不属于目标目录。
3. 本机**不存在**任何 3.9.9.7 客户端样本（延续 007 的结论）。
4. 现有证据能够确定：**目标实例应兼容 3.19.26.22 / 1649370**；但它**不能**证明这是用户想要的 3.9.9.7 实例。
5. 依任务要求（§E），**本轮仅报告差异与影响，不擅自把项目目标改为任何其他版本。**

### 待用户裁定

- 目标版本究竟应为 **3.9.9.7**（则本机缺失该样本，需另行取得），还是应为**目标目录实际所示 3.19.26.22 / 1649370**（则现有目标目录即为正确样本）？
- 在裁定之前，任何协议字段都不得跨版本套用。
