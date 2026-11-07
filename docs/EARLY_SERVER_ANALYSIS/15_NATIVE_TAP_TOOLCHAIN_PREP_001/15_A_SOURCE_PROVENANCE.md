# 15 — A：来源核查（只读）

> 任务：`EARLY-NATIVE-TAP-TOOLCHAIN-PREP-001`（为 `EARLY-NATIVE-TAP-BUILD-001` 准备可追溯、可复核的独立构建工具链）
> 边界：**只读**。本阶段只做 HTTP `HEAD` / 页面元数据读取与工作区检索，**未下载发行包、未解压、未运行包内程序、未安装/升级任何软件，未修改 PATH/注册表/全局设置，未修改源码/实验副本/候选补丁/大厅基线，未编译**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。
> 依据：`14_NATIVE_TAP_TOOLCHAIN_001` 交付物 + 项目原始树 `.github\workflows\build.yml` + 在线只读元数据探查（2026-10-11）。

## A.0 结论先行

| 问题 | 结论 | 状态 |
|---|---|---|
| 项目 CI 引用的原始发行源 | **已确定**：SourceForge `mingw-w64` 项目 → `Personal Builds\mingw-builds\8.1.0\threads-posix\dwarf\i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` | **CONFIRMED** |
| 该源当前是否可用 | **是**：`HTTP 200`，`Content-Type: application/x-7z-compressed`，`Content-Length: 45050859` | **CONFIRMED（只读 HEAD）** |
| 发布者身份 | mingw-w64 项目的 SourceForge 仓库下的 **“Personal Builds / mingw-builds”（niXman）** 个人构建 | **CONFIRMED** |
| 版本标识是否可核验 | **是**：路径 + 文件名 + 线程模型（posix）+ 异常模型（dwarf）+ 运行时版本（rt_v6-rev0）均可在源路径中核对 | **CONFIRMED（路径级）** |
| 官方校验值 | **有（同源）**：SourceForge 文件页公布 **SHA-256**，RSS 公布 **MD5** 与字节数；三方数值互相自洽 | **CONFIRMED（同源）** |
| 是否有独立 OpenPGP 签名 | **未发现**（`.sig`/`.asc` 与 sidecar 校验文件均 404） | **NOT_OBSERVED** |
| 是否存在独立第二来源可交叉验证 | **未发现** 8.1.0 i686-posix-dwarf 的独立托管（niXman GitHub 镜像最早为 8.5.0；MSYS2/vcpkg 不托管 8.1.0） | **CONFIRMED（检索结论）** |
| NASM 来源 | CI 用 `ilammy/setup-nasm@v1`（默认 `2.16.01`），回退官方 `nasm.us`；本机 vcpkg 缓存另存 NASM 3.01（SHA-512 可核） | **CONFIRMED** |
| Windres / GNU Make | 随 mingw-builds 8.1.0 包提供（`windres.exe`、`mingw32-make.exe`）——**待阶段 C 开包核实，不得仅凭文件名断言** | **CANDIDATE（待静态审查）** |
| 是否可进入阶段 B（下载/暂存） | **来源审查通过**；但**下载与暂存需单独授权**，本任务未执行 | **PENDING_AUTHORIZATION** |

**一句话：** 目标发行包的**原始来源（CI 所用同一 URL）可持续访问，且 SourceForge 为该确切文件公布 SHA-256 与 MD5**，来源审查 **GO**；但**下载、完整性复核与开包审计（阶段 B/C）本轮未执行**，需单独授权。

## A.1 项目内引用（原始依据）

| 来源 | 行 | 内容 |
|---|---|---|
| `.github\workflows\build.yml`（原始树） | `:76` | `- name: Get MinGW (i686-8.1.0-release-posix-dwarf)` |
| 同上 | `:79` | `Start-BitsTransfer -Source https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z -Destination mingw32.7z` |
| 同上 | `:80` | `7z x -y mingw32.7z`（解压到 `C:\mingw32`） |
| 同上 | `:82-83` | `- name: Get NASM` / `uses: ilammy/setup-nasm@v1` |
| 同上 | `:97-100` | `$env:Path = "C:\mingw32\bin;" + $path` → `mingw32-make` |
| 同上 | `:90-93` | pexports 来自**项目内** `tools/pexports-0.47-mingw32-bin.tar.xz`（非下载） |
| `.github\workflows\build.yml` | `:14`,`:27` | Linux 作业：`ubuntu-22.04`，`nasm:i386`（与本机 Windows 路径无关） |

**原始 GitHub Actions Windows 作业的实际发行源 = `https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z`。** 这是本任务“优先查找项目原始 CI 所引用的发行源”的直接命中。

其他项目内引用（非下载源，仅证明工具链身份）：

- `docs\CODOL_PORT.md:3494-3497`：原生 Windows 使用“upstream 32-bit MinGW/NASM prerequisites”，可执行文件“was cross-compiled with MinGW-w64”。
- `docs\CODOL_PORT.md:3484-3486`：WSL 交叉构建命令使用 `i686-w64-mingw32-gcc/g++/ar`。
- `14_A`/`14_B`：既有 `bin\codol_dedrun.exe` 与 597 个 `.o` 的 GCC 注释为 `i686-posix-dwarf-rev0 … 8.1.0`，二进制内嵌 `C:\mingw810\i686-810-posix-dwarf-rt_v6-rev0` 路径。

## A.2 目标发行包的确切身份

| 项 | 值 |
|---|---|
| 发行名 | MinGW-w64 Personal Builds / **mingw-builds** |
| 版本 | **GCC 8.1.0**，release |
| 线程模型 | **posix** |
| 异常展开模型 | **dwarf** |
| 运行时修订 | **rt_v6-rev0** |
| 目标 | **i686**（32 位，Win32） |
| 文件名 | `i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` |
| 归档格式 | 7-Zip（`application/x-7z-compressed`） |
| 文件大小 | **45,050,859 字节**（HTTP `Content-Length` 与 RSS `filesize` 一致） |
| 源发布日期 | **2018-05-24 15:31:47 UTC**（HTTP `Last-Modified` 与 RSS `pubDate` 一致） |
| HTTP `ETag` | `"5b06dae3-2af6beb"` |
| SourceForge file id | `28215102` |

**CI 短链解析后的规范路径：**

```
https://downloads.sourceforge.net/project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z
```

- CI 使用的 `https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` 会 **301/302** 重定向到上述规范路径，再由镜像（本次为 `twds.dl.sourceforge.net`）以 **200** 提供文件。
- 规范路径本身即编码了 `8.1.0` / `threads-posix` / `dwarf` / `i686`，与目标规格逐项对应。

## A.3 来源与信任等级

| 维度 | 记录 | 信任评估 |
|---|---|---|
| 托管方 | **SourceForge**，项目 `mingw-w64`（项目主页 `https://sourceforge.net/projects/mingw-w64/`，HTTP 200） | 与 CI 引用的**同一托管域**；非第三方随机镜像 |
| 构建者 | **“Personal Builds / mingw-builds”**，对应 `niXman/mingw-builds`（GitHub 仓库存在，描述 “Scripts for building the 32 and 64-bit MinGW-W64 compilers for Windows”，未归档） | 该“personal builds”系列是 MinGW-w64 生态中流通最广的 Windows 发行；**mingw-w64.org 的下载页亦把 mingw-w64-builds 指向 niXman（GitHub）** |
| 信任等级 | **上游项目托管 + 已知构建者发布的官方归档路径**；但构建属于“Personal Builds”，非 MinGW-w64 项目自身的官方二进制签名发行 | **CANDIDATE-TO-TRUST / 同源可追溯**（不宣称密码学认证） |
| 是否第三方镜像 | **否**：`downloads.sourceforge.net` 为 SourceForge 官方分发入口；镜像节点（如 `twds.dl.sourceforge.net`）由 SourceForge 自动选择，仅供传输 | — |

**重要澄清（避免过度声明）：**

- 本文件**不**把“miXman 个人构建”表述为“经密码学签名的官方发行物”。它是**上游生态公认的构建者发布的归档**，且被项目 CI 直接引用。
- 也未发现该 7z 的独立 OpenPGP/GPG 签名；完整性目前**仅能依赖 SourceForge 公布的哈希**（见 A.4）。

## A.4 可验证的官方校验值与元数据（只读获取）

| 来源 | 算法 | 值 |
|---|---|---|
| SourceForge **文件页**（`.../i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z/`，页面标注 “SHA-256 checksum — use it to verify your download's integrity”） | **SHA-256** | `adb84b70094c0225dd30187ff995e311d19424b1eb8f60934c60e4903297f946` |
| SourceForge **RSS**（`/projects/mingw-w64/rss?path=.../8.1.0`，`<media:hash algo="md5">`） | **MD5** | `07583a272282f71e6e8701b2bf64fafe` |
| SourceForge RSS `<media:content filesize>` | 大小 | `45050859` |
| HTTP `HEAD`（规范 URL，跟随重定向） | 大小 | `45050859` |
| HTTP `HEAD` | `Last-Modified` | `Thu, 24 May 2018 15:31:47 GMT` |
| RSS `pubDate` | 发布时间 | `Thu, 24 May 2018 15:31:47 UT` |

**三方自洽：** 文件页 SHA-256、RSS MD5、RSS/HTTP 大小与时间戳彼此一致，且都指向同一 SourceForge file id `28215102`。

**未发现的校验物料（均为 404，只读 HEAD 探查）：**

- 发行目录内 sidecar：`*.7z.sha256`、`*.7z.sha1`、`*.7z.sha512`、`*.7z.md5`、`*.7z.sig`、`*.7z.asc`、`sha256.sum`、`SHA256SUMS`、`checksums.txt`、`README.txt` —— 全部不存在。

**完整性验证的局限（必须记录）：**

1. 上述哈希与文件**同源**（均由 SourceForge 提供），可防**传输损坏**，但**不能**防“SourceForge 侧被篡改”这一威胁模型；这**不是**密码学认证。
2. 未发现独立第二来源（见 A.5），故**无法做跨源哈希比对**。
3. 结论：**来源可追溯、哈希已记录，但未被密码学签名背书。**

## A.5 独立来源交叉验证检索（只读结论）

| 候选独立来源 | 是否含 8.1.0 i686-posix-dwarf | 证据 |
|---|---|---|
| `niXman/mingw-builds-binaries`（GitHub，mingw-w64.org 现指向的发行点） | **否**：`per_page=100` 的最新 release 列表中，9.x/10.x 之前的**最早为 `8.5.0-rt_v10-rev0`**；不存在 `8.1.0-rt_v6` | GitHub Releases API（只读） |
| MSYS2（`repo.msys2.org/mingw/mingw32/`，HTTP 200） | **否**：MSYS2 提供滚动更新的 i686 工具链，**不固定 8.1.0** | 只读探面 |
| 本机 vcpkg 下载缓存（`E:\vcpkg\downloads`） | **否**：仅含 `mingw-w64-x86_64-*` 的 MSYS2 **x86_64** 包，无 i686 8.1.0 | 只读列目录 |
| 本机全盘检索（C/D/E/F/G，深度 3–4） | **否**：无 `i686-8.1.0*`、无 `*mingw*.7z`、无 `i686-w64-mingw32-gcc.exe` | 只读检索 |

**结论：** 目标 8.1.0 i686-posix-dwarf 在本轮可检索范围内**只有 SourceForge 一个来源**。因此 A.4 的哈希无法跨源互证，属**单源完整性**。

## A.6 配套组件（NASM）的来源核查

CI 未直接下载 NASM，而是 `ilammy/setup-nasm@v1`。该 Action 的行为（只读读取其 `action.yml` + `index.js`）：

1. `action.yml`：`version` 输入 **默认 `2.16.01`**；`platform` 可选，Windows 默认选 `win64`。
2. `index.js` 的二进制下载顺序：
   ① `https://github.com/ilammy/setup-nasm/raw/mirror/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip`
   ② 官方 `https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip`
   随后仅提取 `nasm.exe` 与 `ndisasm.exe`。失败才回退源码构建。

| 项 | 记录 | 状态 |
|---|---|---|
| 官方站点 | `https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip`（HTTP 200，`Content-Length: 506056`，`Last-Modified: Thu, 22 Dec 2022 02:47:17 GMT`） | **CONFIRMED（只读 HEAD）** |
| NASM 官方 sidecar 校验 | `*.sha256`/`*.sha1`/`*.md5`/`*.sig`/`*.asc` 均 **404** | **NOT_OBSERVED** |
| 独立可核的 NASM 记录 | vcpkg 在其脚本中 **固定 NASM `3.01`** 并公布 **SHA-512**；本机 vcpkg 缓存 `E:\vcpkg\downloads\nasm-3.01-win64.zip`（594,502 字节）实测 SHA-512 **与其 pin 完全一致** | **CONFIRMED（本机只读复算）** |

- vcpkg NASM 3.01 SHA-512 pin：`771c238ddb17c98d5736ccaba4ade1d1601d896f09e588489cb43a4f6381bc0ae14d1869f5316fe94f847f54867e65cf12665529b1e7ad88e5e7d3e162719a4f`
- 本机缓存文件实测 SHA-512 与上值**逐字符一致**。
- **注意：** CI 的默认 NASM 是 **2.16.01**，本机缓存是 **3.01**；两者**不是同一版本**。项目要求的是“支持 `-f win --prefix _`”的 NASM，2.16.01 与 3.01 都支持该语法，但**版本选择需在阶段 D 明确**，不得默认等同。

## A.7 其余锁定依赖（来自项目内，非外部下载）

| 依赖 | 形态 | 依据 | 状态 |
|---|---|---|---|
| mbedTLS **2.16.6** | 项目内 vendored（`src\mbedtls`，233 文件） | `src\mbedtls\version.h` | **CONFIRMED（项目内）** |
| tomcrypt | 项目内 vendored（`src\tomcrypt`，387 文件） | `src\tomcrypt\makefile` | **CONFIRMED（项目内）** |
| zlib | 项目内 vendored（`src\zlib`，22 文件） | `makefile` 规则 | **CONFIRMED（项目内）** |
| 预置静态库 | `lib\libmbedcrypto.a`/`libmbedtls.a`/`libmbedx509.a`/`libtomcrypt.a`（i386 COFF） | `lib\libs.txt` | **CONFIRMED** |
| pexports | 项目内 `tools\pexports-0.47-mingw32-bin.tar.xz`（93,676 字节，SHA-256 `51F4D90D0DAC3BEB6FB5F8A4193EE0FAE45B60EECC2DFDB9012F89EEDCE95A7C`） | CI `:92-93`；树内文件 | **CONFIRMED（项目内）** |

**含义：** 需要外部获取的只有 **MinGW-w64 8.1.0（i686-posix-dwarf）** 与 **NASM**；**mbedTLS/tomcrypt/zlib/pexports 均已随项目锁定**，不应另行下载。

## A.8 POSIX shell / coreutils / Python 3 的取得方式（待阶段 D 决策）

目标规格还要求 POSIX shell、coreutils、Python 3。取得路径有两条，均**不代表本项目已放弃原生 Windows 前提**：

| 路径 | 说明 | 依据 | 状态 |
|---|---|---|---|
| **MSYS2**（`C:\msys64`） | 提供 `usr\bin\{make,sh,coreutils,python3}` 与 `mingw32\bin\{windres}`；`tools\BUILD-CODOL.ps1` 正是按此布局硬编码 | `tools\BUILD-CODOL.ps1`；`makefile:125-131` | **CANDIDATE（需装，未装）** |
| Git Bash | 仅提供 POSIX shell 语义与部分 coreutils，**不含** make/GCC/NASM/windres | `14_A A.2` | **不充分** |

- 官方 MSYS2 入口（只读核验）：`https://www.msys2.org/`（200）、`https://repo.msys2.org/mingw/mingw32/`（200）、`https://github.com/msys2/msys2-installer/releases/latest`（200，含 `msys2-base-x86_64-latest.tar.zst` 等资产）。
- 本机现状：`C:\msys64` **不存在**（继承 `14_A`）。

## A.9 来源核查边界声明（本轮未做）

- 未下载任何发行包（含 7z/zip/tar）；仅做 HTTP `HEAD` 与页面元数据读取。
- 未解压、未运行包内任何程序（未执行 `gcc`/`make`/`nasm`/`windres`）。
- 未安装/升级软件；未修改 PATH/注册表/全局设置。
- 未修改原始源码、现有实验副本、候选补丁或大厅基线。
- 未开始任何客户端/服务端运行实验。
- 本文件**不是**完整性验证结果，也**不是**静态包结构审查结果。

## A.10 阶段 A 裁决

- 原始发行源定位：**GO（CONFIRMED）**。
- 版本/线程/异常/目标匹配：**GO（路径级 CONFIRMED）**。
- 官方校验值获取：**GO（同源 SHA-256 + MD5 + 大小 + 时间戳，自洽）**。
- 密码学签章：**NOT_OBSERVED**（不得声称已认证）。
- 独立第二来源：**未发现**（单源完整性局限）。
- 进入阶段 B（下载/暂存）：**PENDING_AUTHORIZATION**（需明确授权）。

> 本文件为**来源核查**，非完整性验证、非静态包审查、非编译验证结果。