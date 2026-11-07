# 01_SAMPLE_IDENTITY_AND_ADDRESS_MAPPING

**任务:** CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045(只读静态)。
**日期:** 2026-10-13 (Asia/Shanghai)。

---

## 1. 样本身份(本轮重新计算完整 SHA-256)

| 编号 | 文件(实际路径) | 字节 | 完整 SHA-256 |
|---|---|---|---|
| S-IMG | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` |
| S-EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |
| S-DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |

与 043/044 独立复算一致。证据:`evidence/z01_identity_and_pe.txt`(脚本 `scripts/z01_final_identity.py`)。

## 2. PE 结构(独立读取)

| 字段 | S-IMG | S-EXE(磁盘) | S-DLL |
|---|---|---|---|
| Machine | 0x014C (x86) | 0x014C | 0x014C |
| ImageBase | `0x00400000` | `0x00400000` | `0x10000000` |
| AddressOfEntryPoint | `0x0E5DC690` | `0x0E5DC690` | `0x0000149C` |
| TimeDateStamp | `0x6096930A` (2021-05-08) | `0x6096930A` | `0x5E551315` (2020-02-25) |
| SizeOfImage | `0x0E659000` | `0x0E659000` | `0x03991000` |
| FileAlignment / SectionAlignment | `0x1000 / 0x1000` | `0x1000 / 0x1000` | `0x200 / 0x1000` |
| Section count | 7 (`.tp3`×6 + `.tp3`[旧.tvm0]) | 7 (`.tp3`×6 + `.tvm0`) | 8 |
| IMPORT dir | RVA `0x0E5DC635`, size `0x0` | RVA `0x0E5DC635`, size `0x0` | RVA `0x009F67B8`, size `0x3C` |
| IAT dir | RVA `0x0`, size `0x0` | RVA `0x0`, size `0x0` | RVA `0x00B02000`, size `0xC00` |

**S-IMG 与 S-EXE 同源不同态:** 同 ImageBase、同入口、同时间戳、同节区 VA/VSize(仅 `.tvm0` 在镜像中被命名为 `.tp3`);
磁盘 `.tp3` 是加壳数据,镜像对应区段是可反汇编代码(`CONFIRMED`)。

## 3. 地址约定(本轮修正的关键)

**约定(044 建立,本轮复验):** `ImageBase = 0x00400000`;`RVA = VA - 0x400000`;对 S-IMG 的**首个可读节区**,`file_offset == RVA`。

> **本任务的核心发现:** 指令中的直接内存引用(如 `call dword ptr [0x0CA84E8]`)写的是**绝对 VA**,
> 因此**文件偏移 = VA - 0x400000**,而不是 VA 本身。

| 引用 | 绝对 VA | 正确 file_offset = VA-0x400000 | 045 结论 |
|---|---|---|---|
| `0x87BE00` 主读槽 | `0x00CA84E8` | `0x008A84E8` | **在文件内**(文件长 `0x00A65000`) |
| `0x87BE00` 降级槽 | `0x00CA84E4` | `0x008A84E4` | **在文件内** |
| last-error 槽 | `0x00CA853C` | `0x008A853C` | **在文件内** |

任务书指明的 `0x0CA8400–0x0CA8700`(VA)= RVA `0x008A8400–0x008A8700`,**同样在文件内**(属第 2 节区 `.tp3`[VA `0x8A8000`,Raw `0x8A8000`,RSize `0x16E000`])。

本任务实际核验了 **`0x00CA84B4–0x00CA8570`**(即 RVA `0x008A84B4–0x008A8570`)这一整段槽表。

## 4. 勘误:040–044 的"超出 EOF / 镜像未覆盖"结论**根因错误**

043/044/040/041 反复记载:"读 API IAT 槽 `0x0CA84E8` 值落在镜像未覆盖节区","文件长 `0xA65000` < RVA `0xCA84E8`"。

- **044 原文**(`07_RUNTIME_EVIDENCE_NECESSITY.md` §1):"`0x0CA84E8` … 该 RVA **超出 EOF 0x2434E8**"。
- **044 原文**(`06_BLOCKER_REASSESSMENT.tsv` BE-01):"IAT slots are beyond EOF (file 0xA65000 < RVA 0xCA84E8)"。
- **043 原文**(`04_IMAGE_COVERAGE_AND_BLOCKERS.md` / A-01):"读 API 槽值在镜像外"。

**这两句的前提是把绝对 VA `0x0CA84E8` 当成 RVA 与文件长比较。** 正确的 RVA 是 `0x008A84E8`,**小于**文件长,可读。

补充旁证:同任务族 2697 的 `08_CLIENT_OPCODE_DISPATCH_TRACE/F4_ADDRESS_AND_IMAGE_VALIDITY.md` **独立记录了同一类混淆**
("`0xA2E50`、`0xA2D90` 是 RVA … 函数内部 E8 目标 `0x5AC1D0` 是 VA"),说明该地址约定错误在本项目族中**是复现过的系统性风险**。

**影响:** A-01、BE-01、BE-02、BE-04 的"BLOCKED"根因消失;相关边可在**纯静态**下重新判定(见 `02`、`03`)。
本任务**不修改** 043/044 历史文件,仅在此记录勘误。

## 5. S-IMG 第 2 节区确是"导入/跳转槽表区"

第 2 节区(RVA `0x8A8000`)内容以**指针数组**为主:

- 起始 `0x8A8000` 起为指向 `0x00A1xxxx`(首节区字符串面)的名称指针数组;
- `0x8A84D4`、`0x8A8534` 等位置出现 `0x80000000 | ordinal` 形式的**序号型导入表项**;
- 运行期镜像同位置被改写为**已解析的绝对函数地址**(如 `0x751C9CC0`、`0x116CF641`),
  即"加载器已把文件内的序号表重定位/绑定为进程内地址"。

这解释了为什么 043/044 的**绝对 dword 引用扫描**找不到调用者:运行期镜像里的槽值已是解析后的地址,
而静态扫描找的是"指向槽的 dword"。

## 6. 六方身份(仅列已存在的样本,VCS 头为实际读取)

| 方 | 实际制品/证据 | 身份锚点 |
|---|---|---|
| 最终版 CODOL 客户端 | `image_best.bin` `17ce…f045`(= EXE `3699…b537` 同源镜像) | ImageBase `0x400000`,EP `0x0E5DC690`,TS `0x6096930A` |
| OLD(服务端) | `codol_dedrun.exe` SHA-256 `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a`(8,469,493 B) | 来源 `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/01`(VERIFIED) |
| 2697(服务端) | `codol_dedrun.exe` SHA-256 `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`(7,295,919 B) | 来源同上;同封包含客户端 `353754047dbb…d6e1` |
| OL-mod / ol-mod-olfinal | `_e1_regression\ol-mod-olfinal`,HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`,分支 `OLfinal-live` | `CODOL_OLMOD_AUDIT_20261009_094312` 审计(只读) |
| CoD4x | `DEV-BOOKING\_lineage021\CoD4x_Server`,HEAD `ddd65fce1a1093017bad2dbb6840d75d11c0d56f`(2026-09-18) | 源码级;`net_game_conf.h` `svc_*`,CHANGELOG `17.3` |
| IW4x | `IW4X\Client核心代码\iw4x-client`,HEAD `0699a7e5716ded53bcfa6748bcb89a535f8f39f0`(2026-09-17) | 源码级;`Structs.hpp` `svc_ops_e`;CHANGELOG `r4303` |

## 7. 未变更声明

- 本任务**只读**;未写入 `COD OL\`、040–044 目录、冻结基线、正式服务器源码。
- 全部新产物只落在 `CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045`。
- 043 登记的样本身份矛盾(工程预期 `E3823FD6…F37B` 在本机不存在)**保留**为 `UNKNOWN/BLOCKED`,本任务不消解。
