# REQUIRED_INPUTS — 解除阻塞所需输入（2026-10-09）

## 1. 当前批准的目标客户端 SHA-256

```
E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B
```
记录位置: `.agents/AGENTS.md:174`、`.agents/modules/game_server.md:330`、`tools/runtime/CodolMapEntDump.py:20`（强制校验）、`tools/runtime/CodolGlassAssetDump.py:20`、`tools/runtime/CodolNetfieldDump.py:20`、`tools/runtime/CodolWeaponHitLocationDump.py:19`、`tools/reverse/catalogs/codol_builtin_matrix.json:8`。
**本工具不会自动更换该哈希。** 只有你明确批准切换构建基线后才会更新，且必须重新核验该构建的 RVA/协议/资产/结构。

## 2. 为什么 `FileVersion=1649370` 不能证明身份

1. `FileVersion` 是**可自由编辑的 PE 资源字段**，任何人都能改，不具备身份含义。
2. 本机实测: 客户端 `FileVersion=1649370`，但 SHA-256 是 `36997674...`，**不等于**批准目标 `E3823FD6...`。
3. 同一个构建号可以对应不同镜像: 本机镜像是**加壳**的（节区 `.tp3`×5 + `.tvm0`），而 OLMod 的目标 `out.exe` 是 **unpacked** 镜像。实测 RVA `0x8371A` 的文件字节与 build 1649370 期望不符。
4. 因此身份判定**只接受完整 SHA-256 精确匹配**；`FileVersion` 在报告中固定记为 `INFO`（`METADATA ONLY - never identity`），不参与任何令牌。

## 3. 客户端候选必须提交的字段

| 字段 | 说明 |
| --- | --- |
| 路径 | 绝对路径 |
| SHA-256 | 完整 64 位十六进制（身份的唯一依据） |
| 大小 | 字节数 |
| PE 架构 | Machine（CODOL 应为 x86 / 0x14C） |
| ImageBase / 节区 | 用于识别加壳（如 `.tp3` / `.tvm0`） |
| 版本资源 | FileVersion / ProductVersion（仅元数据） |
| 来源 | 你如何取得（合法安装目录 / 归档 / 备份），用于审计追溯 |

可直接用:
```
Get-FileHash <client.exe> -Algorithm SHA256
.\codol-preflight.ps1 -RepoPath . -ClientPath <client.exe> -ExpectedClientSha256 E3823FD6...AF37B
```
后者必须让 `client.sha256` 为 **PASS** 才算身份解除。

## 4. 同构建地图资产需要的证据

1. **文件清单**: 至少一个真实地图 `.ff`（例如 `mp_crash_tropical.ff`、`mp_nuked.ff`、`zm_factory_sh.ff`），含路径/大小/SHA-256。
2. **容器头**: 每个地图 `.ff` 必须以 `IWff0100` v461 开头且**可读**。
3. **构建关联证据**: 这些 `.ff` 来自与目标客户端**同一构建/同一安装**的说明（用于 `-ExpectedAssetBuildAssociation`）；工具只能记录该声明，不能独立验证。
4. **完整性标准**: 你要求的必需地图清单（用于 `-RequiredMapFastfiles`），工具会检查其**全部存在**。
5. 参考: 本机现有 42 个 `.ff`（`fastfile_inventory.json`）**地图候选为 0**，且属于客户端为 `36997674...` 的沙箱，构建关联为 `UNKNOWN`。

## 5. 工具链的版本与架构要求

| 组件 | 要求 | 检测方式 |
| --- | --- | --- |
| Visual Studio 2022 C++ + Windows SDK | 提供 x86 目标工具链 | `vswhere.exe` 存在；`cl` banner 解析出**版本**且 `for x86` |
| xmake | **≥ 3.0.9**（README.md:31） | `xmake --version` 解析并比较版本 |
| vcpkg | `VCPKG_ROOT` 指向有效目录 | `VCPKG_ROOT` 存在且目录有效 |
| vcpkg triplet | `x86-windows-static` | `%VCPKG_ROOT%\triplets\x86-windows-static.cmake` 存在 |
| OpenSSL | 面向该 triplet 已安装 | `%VCPKG_ROOT%\installed\x86-windows-static\include\openssl\ssl.h` 存在 |
| nlohmann_json / lua / mhook | 由 xmake `add_requires` 解析（`xmake.lua:58,62,66,67`） | 构建时判定 |
| vcpkg baseline | `aa2d37682e3318d93aef87efa7b0e88e81cd3d59`（`vcpkg.json:5`） | 记录实际解析结果 |

**注意**: 命令存在 ≠ 依赖可用 ≠ 构建成功。`TOOLCHAIN_READY` 需要上表前五项全部 PASS；`BUILD_CONFIRMED` **永远**需要一次真实构建的成功退出码与产物 SHA-256。

## 6. 需要你明确批准的选项

| # | 选项 | 影响 |
| --- | --- | --- |
| A1 | 提供 `E3823FD6...` 的客户端 | 直接解除 `CLIENT_HASH_VERIFIED`，其余工作按 3.3.3.3 基线继续 |
| A2 | **改用 OLFinal `out.exe` 构建**并给出其 SHA-256 | 需**建立新基线**并重新核验 RVA/协议/资产/结构；**不得**与 3.3.3.3 证据混用 |
| A3 | 提供含地图 `.ff` 的完整 CODOL 安装目录 | 解除 `ASSET_SET_VERIFIED` 的前置；仍需你声明构建关联 |
| A4 | 授权安装工具链 | 才能产生 `TOOLCHAIN_READY` → `BUILD_CONFIRMED` |
| A5 | 授权提权运行 pktmon | 网络取证；须接受回环流量可能漏抓 |

**在你批准 A1 或 A2 之前，本工具不会修改期望哈希，也不会开始任何构建或运行验证。**
