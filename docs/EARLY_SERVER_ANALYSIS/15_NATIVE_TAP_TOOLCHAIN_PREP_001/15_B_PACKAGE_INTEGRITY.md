# 15 — B：独立暂存与完整性核验（方案，本轮未执行）

> 任务：`EARLY-NATIVE-TAP-TOOLCHAIN-PREP-001`
> 边界：**本阶段本轮未执行**。本文件仅制定“独立暂存 + 完整性核验”的方案与准入条件，**未下载、未复制、未解压、未运行任何包内程序**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。
> 前置：阶段 A 来源审查通过（见 `15_A_SOURCE_PROVENANCE.md`，裁决 GO）。

## B.0 准入条件（执行前必须全部满足）

| # | 条件 | 当前状态 |
|---|---|---|
| P1 | 阶段 A 来源审查通过 | **满足**（`15_A` 裁决 GO） |
| P2 | 目标对象与哈希已记录 | **满足**（见 B.1） |
| P3 | 独立暂存目录已定义、且不落在系统目录 | **满足**（见 B.2） |
| P4 | **获得明确的“下载/复制到暂存”授权** | **未获得** |
| P5 | 解压将使用**离线**方式，且不运行包内程序 | 计划就绪 |

**尚缺 P4，故本阶段不执行。**

## B.1 待核验对象清单

### B.1.1 MinGW-w64 工具链（主目标）

| 项 | 值 |
|---|---|
| 文件名 | `i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` |
| CI 原始 URL（短链） | `https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` |
| 规范下载 URL | `https://downloads.sourceforge.net/project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` |
| SourceForge 文件页 | `https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z/` |
| 发布者 | mingw-w64 项目 / “Personal Builds / mingw-builds”（niXman） |
| 版本标识 | GCC 8.1.0，release，i686，threads=posix，dwarf，rt_v6-rev0 |
| 源大小 | **45,050,859 字节** |
| 源 `Last-Modified` | 2018-05-24 15:31:47 UTC |
| SourceForge file id | `28215102` |
| **官方 SHA-256（SourceForge 文件页）** | `adb84b70094c0225dd30187ff995e311d19424b1eb8f60934c60e4903297f946` |
| **官方 MD5（SourceForge RSS）** | `07583a272282f71e6e8701b2bf64fafe` |
| 独立 OpenPGP 签名 | **未提供**（`.sig`/`.asc` 404） |
| 独立第二来源 | **未发现** |

### B.1.2 NASM（配套）

| 项 | 值 |
|---|---|
| CI 默认版本 | 2.16.01（经 `ilammy/setup-nasm@v1`，`action.yml` 默认值） |
| 官方 URL（2.16.01） | `https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip` |
| 官方 URL 大小 | 506,056 字节 |
| 官方 URL `Last-Modified` | 2022-12-22 02:47:17 UTC |
| NASM 官方 sidecar 校验 | **未提供**（`.sha256`/`.sha1`/`.md5`/`.sig`/`.asc` 均 404） |
| 本机已有的可核版本 | `E:\vcpkg\downloads\nasm-3.01-win64.zip`（594,502 字节） |
| NASM 3.01 已公布 pin（vcpkg 脚本内 SHA-512） | `771c238ddb17c98d5736ccaba4ade1d1601d896f09e588489cb43a4f6381bc0ae14d1869f5316fe94f847f54867e65cf12665529b1e7ad88e5e7d3e162719a4f` |
| 本机缓存实测 SHA-512 | **与上值一致（本轮已只读复算）** |
| 版本差异提醒 | CI 默认 2.16.01 ≠ 本机缓存 3.01；**版本选择须在阶段 D 明确，不得默认等同** |

## B.2 独立暂存目录（约定，尚未创建）

| 用途 | 路径 | 约束 |
|---|---|---|
| 暂存根 | `D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\15_NATIVE_TAP_TOOLCHAIN_PREP_001\_staging` | 仅限本任务输出目录内；**当前不存在** |
| 原始包 | `_staging\packages\` | **只读保留**，不覆盖、不删改 |
| 校验记录 | `_staging\integrity\` | 记录 SHA-256/MD5/SHA-512、大小、时间戳与来源 |
| 解压根（阶段 C） | `_staging\extract\` | 与 `packages\` 分离，便于只读复核 |

**硬约束：**

- **不写入**系统目录（`C:\Windows`、`C:\Program Files*`、`%ProgramFiles%` 等）。
- **不修改** PATH、注册表或任何全局/用户构建设置。
- **不覆盖**任何已存在的工具链；本机当前亦无同目标工具链（`14_A`）。
- 全程**保留原始发行包**，供后续独立复核。

## B.3 完整性核验流程（执行时）

1. **记录来源上下文**：保存两个 URL（CI 短链 + 规范路径）、文件页 URL、`Last-Modified`、file id、获取时间（Asia/Shanghai）。
2. **下载/复制到暂存**：仅落 `_staging\packages\`。若采用本机已有副本，须记录其绝对路径与产生时间。
3. **计算 SHA-256**：`Get-FileHash -Algorithm SHA256`，与 SourceForge 文件页值逐字符比对。
4. **计算 MD5**：与 SourceForge RSS 值比对（`Get-FileHash -Algorithm MD5`）。
5. **核对大小**：须等于 **45,050,859 字节**。
6. **签名核验**：**不存在可用签名** → 明确记录“无法做密码学认证”，**不得**声称已认证。
7. **落盘校验记录**：写入 `_staging\integrity\`，含上述全部字段与判定。
8. **判定**：

| 情形 | 判定 |
|---|---|
| SHA-256 与 MD5 均匹配且大小一致 | **INTEGRITY_MATCH（同源哈希校验通过）** |
| 任一不匹配 | **INTEGRITY_FAIL → 停止（NO-GO），不得解压/使用** |
| 无法取得任一哈希 | **INTEGRITY_PARTIAL → 必须显式标注局限** |

## B.4 完整性验证的局限（必须随结论一起记录）

1. **同源哈希不等于密码学认证**：SHA-256/MD5 均由 SourceForge 提供，可防传输损坏与偶发篡改，但**不能**抵御“托管方侧被攻破”的威胁模型。
2. **无独立签名**：未发现 GPG 签名，无法做签名链验证。
3. **无独立第二来源**：未发现同一 8.1.0 i686-posix-dwarf 的其它托管点，无法做跨源比对（检索结论见 `15_A A.5`）。
4. 因此任何执行结果都只能表述为“**与 SourceForge 公布值一致**”，**不得**表述为“来源已被密码学认证”或“已由官方签名背书”。

## B.5 阶段 B 裁决

- 阶段 B 方案：**CONFIRMED（已就绪）**。
- 阶段 B 执行：**NOT_EXECUTED（未获授权，未下载、未暂存）**。
- 下载/暂存需**单独授权**（`P4`）。
- 目标哈希与元数据：**已记录（B.1）**，供执行时逐字符比对。

> 本文件为**方案**，非执行记录；本轮未下载、未解压、未运行任何包内程序。