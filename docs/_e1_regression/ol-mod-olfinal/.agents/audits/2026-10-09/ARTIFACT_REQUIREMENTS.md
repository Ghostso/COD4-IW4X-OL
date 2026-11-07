# ARTIFACT_REQUIREMENTS — 工件需求与交付清单（阶段 H，2026-10-09）

本文件可直接交给你执行。**未安装任何工具；未修改任何正式配置、fixture 或期望哈希。**

---

## A. 目标客户端

**需要**：OLFinal **unpacked** `out.exe`（或其明确来源 + 完整 SHA-256）。

### 必须提供的字段
| 字段 | 说明 | 必需 |
| --- | --- | --- |
| 来源 | 你如何取得（合法安装目录 / 可信归档 / 备份） | **是** |
| 获取日期 | 你取得该文件的日期 | **是** |
| 文件大小 | 字节数 | **是** |
| **完整 SHA-256** | 64 位十六进制，**身份的唯一依据** | **是** |
| PE Machine | 期望 `0x014C`（x86） | **是** |
| ImageBase | 例如 `0x00400000` | 是 |
| 节区表 | 名称/VirtualSize/RawSize；用于识别加壳（`.tp3`/`.tvm0`） | **是** |
| FileVersion | 仅作**辅助元数据**，**不得**用于身份或构建判定 | 是（辅助） |

### 三个必须分开的主张
| # | 主张 | 判定方式 | 现状 |
| --- | --- | --- | --- |
| 1 | **文件身份** | SHA-256 精确比对 | 现有候选全部 `REJECTED`（不匹配 `E3823FD6...`） |
| 2 | **构建身份** | 记录的守卫/RVA 是否吻合 | 现有候选 `UNKNOWN`（加壳，文件字节不可判定） |
| 3 | **与 OLMod 源码的兼容性** | 加载后内存核验 + 结构/协议核验 | `NOT_RUN`（未授权） |

**不得**仅凭文件名或 `FileVersion` 确认构建身份。`FileVersion=1649370` 已实测存在于一个**不匹配**批准哈希的加壳镜像上。

---

## B. 地图资产

**需要**：至少一个**真实 CODOL 地图** `.ff`。

### 必须提供的字段
| 字段 | 说明 |
| --- | --- |
| 文件名 | 例如 `mp_crash_tropical.ff` / `mp_nuked.ff` / `zm_factory_sh.ff` |
| 来源安装 | 它来自哪个安装目录（必须与目标客户端**同一安装**） |
| 获取日期 | 取得日期 |
| 文件大小 | 字节数 |
| 完整 SHA-256 | 64 位十六进制 |
| FF 头部解析结果 | 期望 `magic=IWff0100`、`version=461` |

### 明确排除（不接受）
`playlist`、`UI`、`localized`、`common`、`code`、`development`、`marketplace`、`loadscreen`，以及**任何其他 COD 系列**的 `.ff`（IW4X / Infinite Warfare / MWII 等）。
**`mp_playlists.ff` 不是地图**，它分类为 `playlists`。

### 构建关联证据
必须提供它与目标客户端**属于同一构建**的关联依据。仅“同目录/文件名相似/版本资源相同”**不足以**单独证明。

---

## C. 来源关联的标注规则

| 标注 | 含义 |
| --- | --- |
| `CONFIRMED` | 有用户提供的原始文件 + 来源说明 + 可复核哈希记录，三者一致 |
| `PARTIAL` | 有部分证据（例如本机存在该文件），但缺用户来源说明或哈希记录 |
| `UNKNOWN` | 证据不足，无法判断 |
| `REJECTED` | 已被更可靠的证据否定（例如 SHA-256 不匹配） |

**优先顺序**：用户明确提供的原始文件与来源说明 > 同一安装中的文件清单 > 可信归档元数据 > 可复核哈希记录。
**同目录、文件名相似、版本资源相同，均不足以单独证明属于同一构建。**

---

## D. 可复现的只读核验命令（H2）

仓库内已提供 `inspect-artifact.ps1`（**只读**，仅用 PowerShell/.NET，**无需安装任何东西**）：

```powershell
# 核验你指定的文件（可一次多个），不启动程序、不修改文件、不遍历其他目录
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .agents\audits\2026-10-09\inspect-artifact.ps1 `
  -Path "D:\your\path\out.exe,D:\install\main\mp_crash_tropical.ff" `
  -OutFile "$env:TEMP\inspect.json"
```

输出内容: 路径、是否存在、字节数、**完整 SHA-256**、PE Machine 与架构名、ImageBase、SizeOfImage、节区表、FileVersion（标注 `METADATA ONLY - never identity`）；对 `.ff` 则输出 `IWff0100` magic 与 version。

等价的最小内建命令（无需任何脚本）：
```powershell
Get-FileHash -LiteralPath "D:\your\path\out.exe" -Algorithm SHA256
Get-Item -LiteralPath "D:\your\path\out.exe" | Select-Object Length, @{n='FileVersion';e={$_.VersionInfo.FileVersion}}
# FF 头部（前 12 字节）
$b=[byte[]](Get-Content -LiteralPath "D:\install\main\mp_crash_tropical.ff" -Encoding Byte -TotalCount 12);
[System.Text.Encoding]::ASCII.GetString($b,0,8); [System.BitConverter]::ToUInt32($b,8)
```

### 这些命令的保证
- 只处理你**明确指定**的路径；
- **不启动**目标程序；
- **不修改**文件或配置；
- **不遍历**其他目录；
- **不会**把实测哈希写入任何正式期望哈希配置。

若你的环境无法运行上述命令，把文件路径与来源说明交给我，由我在已授权范围内只读核验（**不安装依赖**）。

---

## E. 交付清单（最小集）

| # | 交付物 | 形式 |
| --- | --- | --- |
| 1 | OLFinal unpacked `out.exe` **或其来源 + 完整 SHA-256** | 文件或说明 |
| 2 | 该客户端的**来源说明**（从哪来、何时取得） | 说明 |
| 3 | **≥1 个真实 CODOL 地图 `.ff`** | 文件 |
| 4 | 该地图的**来源安装路径**与「与客户端同一安装」的声明 | 说明 |
| 5 | （可选）两者的 `inspect-artifact.ps1` 输出 JSON | 文件 |

拿到 1-4 后我会：核验身份与哈希 → 静态比对守卫/RVA → 输出切换审查报告。**仍然不会自行更改正式基线。**
