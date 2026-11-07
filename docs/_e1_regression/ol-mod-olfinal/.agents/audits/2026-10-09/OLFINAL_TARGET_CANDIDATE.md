# OLFINAL_TARGET_CANDIDATE — out.exe 候选评估（阶段 F，2026-10-09）

**本文件只提出候选方案，不修改正式预期哈希，不修改任何既有审计基线。**

## 0. 结论（先读）

**`NOT_FOUND`** —— 在所有已授权目录中**没有找到任何 `out.exe`**。
因此阶段 F **无法**给出“有足够证据建议切换到 OLFinal 构建”的结论；见 §4。

## 1. 搜索范围（未做全盘扫描）

| 授权根 | 深度 |
| --- | --- |
| `C:\Games` | ≤5（该目录不存在） |
| `D:\BaiduNetdiskDownload` | ≤5 |
| `E:\` | ≤4 |
| `F:\桌面` | ≤5 |
| `G:\` | ≤4 |

匹配 `out.exe` **或** `codoMP_client_shipRetail.exe` 的候选共 **40** 个，**全部**是 `codoMP_client_shipRetail.exe`；`out.exe` **0 个**。

## 2. 实际候选（40 份副本，仅 2 个不同构建）

### 候选 A —— `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`（39 份）

| 字段 | 值 |
| --- | --- |
| 代表路径 | `D:\BaiduNetdiskDownload\codoMP_client_shipRetail.exe` |
| 其他位置 | `E:\Program Files\Tencent\TGP\sandbox_codo\`、`E:\CODOL_SANDBOX\RUN001\`、`D:\...\使命召唤OL\**`（沙箱/工具/备份共 37 处） |
| 大小 | 7,841,344 字节 |
| SHA-256 | `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537` |
| PE 架构 | Machine `0x14C`（**x86**） |
| ImageBase / SizeOfImage | `0x400000` / `0xE659000` |
| TimeDateStamp | `0x6096930A`（2021-05-08T13:32:58Z） |
| 节区 | `.tp3` ×5 + **`.tvm0`** ×1（TenProtect / 腾讯 VM **加壳**特征） |
| 版本资源 | FileVersion = **1649370**（与 OLFinal 构建号相同） |

### 候选 B —— `7B31168D42A5A6BA11750D404971EE52F9FD1CAB93C56A8A85DA94AE76C41342`（1 份）

| 字段 | 值 |
| --- | --- |
| 路径 | `D:\BaiduNetdiskDownload\使命召唤OL\工具\EXPERIMENT_017_BOOT_SKIP\codoMP_client_shipRetail.exe` |
| 大小 / 架构 / ImageBase / 时间戳 / 节区 | **与候选 A 完全相同** |
| 与 A 的差异 | 仅哈希不同（同尺寸同时间戳，为局部改动版本） |

## 3. 与 OLFinal 源码绑定的构建依据 —— **核验未通过**

`src/game_server/ClientProcessPatches.cpp:207-211` 记录 build 1649370 的固定字节:
**RVA `0x8371A` 必须为 `83 7C 24 08 01 0F 94 C0`**（`cmp [esp+8],1 ; sete al`）。

`src/game_server/EngineBindings.hpp` 另记录 `Com_Frame` 等 RVA 前缀。

| 核验点 | 期望（build 1649370） | 候选 A 实测 | 候选 B 实测 | 结果 |
| --- | --- | --- | --- | --- |
| RVA `0x8371A` | `837C2408010F94C0` | `00D945108B4D088B` | `00D945108B4D088B` | **MISMATCH** |
| RVA `0x0FEA20`（Com_Frame） | OLMod 记录的 `ComFramePrefix` | `03C1E006505181C2` | `03C1E006505181C2` | **MISMATCH** |

**未确认的兼容性问题（必须保留，不得推断）**:
1. 两个候选都是**加壳镜像**（`.tp3`/`.tvm0`），而 OLMod 的 `out.exe` 是**去壳（unpacked）镜像**。文件字节**不代表**运行时解壳后的内存镜像。
2. 因此“运行时解壳后是否与 build 1649370 的 RVA 期望一致”仍为 **`UNKNOWN`**，**不能**由静态失败推断为绝对不兼容，也**不能**推断为兼容。
3. 判定该点需要**加载客户端并读取内存字节**——这属于未授权操作（需先有构建产物与合法安装），本阶段不做。
4. `FileVersion=1649370` **不是**身份依据（PE 资源可编辑；且同一构建号可对应不同镜像）。

## 4. 完成判据回答: 是否有足够证据建议正式切换到 OLFinal 构建？

**没有。** 当前证据**不足以**建议切换，理由:
- 授权的目标工件 `out.exe` **不存在**（`NOT_FOUND`）；
- 本机仅有的两个构建是**加壳镜像**，其静态字节与 build 1649370 的**两个**记录 RVA 均不匹配；
- 运行时解壳等价性为 `UNKNOWN`，且在本阶段被禁止验证；
- 没有任何构建的地图资产（见 `fastfile_inventory.json`：地图候选 0）。

### 仍缺的最小证据
1. **unpacked `out.exe` 本体**（或其明确来源说明 + 完整 SHA-256）——这是唯一能直接核验的对象。
2. 该文件 RVA `0x8371A` 实测应为 `83 7C 24 08 01 0F 94 C0`（以及 `EngineBindings.hpp` 中 `ComFramePrefix` 等其余记录前缀）——**一次比对即可给出结论**。
3. 确认**同一构建**发布地图 `.ff`（至少一个真实地图文件 + 哈希）。
4. 关于 3.3.3.3 专属工具与 fixture 的处置决定: `tools/runtime/CodolMapEntDump.py:20`、`CodolGlassAssetDump.py:20`、`CodolNetfieldDump.py:20`、`CodolWeaponHitLocationDump.py:19` 内嵌了**3.3.3.3 的强制哈希与 RVA**；若切换构建，这些工具与 `tests/game_server` 的 fixture 需要**重新标定**，属于**新的工作项**。

## 5. 只有用户明确批准后才可执行的基线切换步骤（**本阶段不执行**）

1. 用户提供 `out.exe` 并确认其 SHA-256；
2. 在该文件上核验 §3 的记录 RVA（至少 `0x8371A` 与 Com_Frame）；
3. 只有在第 2 步全部通过后，才在**新的一条审计记录**中登记新的期望哈希（**不改写**既有 `E3823FD6...` 记录）；
4. 重新标定 3.3.3.3 专属工具与 fixture；
5. 重新核验协议、结构布局、S2/S3 原生数据来源；
6. **不得**把 3.3.3.3 与 OLFinal 的证据混用。

## 6. 需要用户提供的文件清单与核验命令

```
# 需要: OLFinal unpacked 客户端，通常命名为 out.exe
Get-FileHash <path>\out.exe -Algorithm SHA256

# 核验它确实是自己声称的那个构建（RVA 0x8371A 应为 83 7C 24 08 01 0F 94 C0）
# 可用仓库自带工具或任何 PE 读取器；本阶段不执行。

# 交给 preflight 做身份与资产判定
.\codol-preflight.ps1 -RepoPath . -ClientPath <path>\out.exe `
    -ExpectedClientSha256 <你批准并记录的哈希> `
    -GamePath <完整安装目录> `
    -RequiredMapFastfiles mp_crash_tropical `
    -ExpectedAssetBuildAssociation "supplied by user: <来源说明>"
```

（`RequiredMapFastfiles` 的值需按你的实际地图集填写；`-ExpectedClientSha256` 必须由**你**提供并批准。）
