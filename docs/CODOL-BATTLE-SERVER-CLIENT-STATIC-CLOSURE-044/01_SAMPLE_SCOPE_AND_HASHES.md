# 01_SAMPLE_SCOPE_AND_HASHES — 样本身份、地址换算与检查范围

**任务:** CODOL-BATTLE-SERVER-CLIENT-STATIC-CLOSURE-044
**日期:** 2026-10-13 (Asia/Shanghai)
**性质:** 只读静态分析。未启动游戏/服务器;无动态调试/注入/hook/运行期内存转储;
未修改原始样本 / 040-043 交付物 / FREEZE-005 冻结基线 / 正式服务器源码。
**044 目录:** `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-STATIC-CLOSURE-044`

---

## 1. 043 使用过的全部客户端镜像/证据(044 逐一复核)

| 编号 | 文件(实际路径) | 字节 | 完整 SHA-256 (044 重算) | 043 声明 | 复核 |
|---|---|---|---|---|---|
| S-EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | `36997674...b537` | **一致** |
| S-DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | `ef75220d...6a20` | **一致** |
| S-IMG | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` | `17cef6e0...f045` | **一致** |

> **本报告此后所有地址(RVA)只对 S-IMG `17cef6e0a5e7b8d1...` 有效。**
> 凡引用 043 的既有结论,均在 `06` 保留其原描述,不改写。

### 1.1 `image_best.bin` 多副本(身份陷阱,保持不变)

本工作区共 **12 份 `image_best.bin` / 4 个不同构建**(同尺寸,不同哈希):

| SHA-256 前缀 | 副本数 | 特征 |
|---|---|---|
| `d74f45ce5193d496...` | 7 | **无 `MZ` 头**(纯 dump,PE 结构不可解析) |
| `1b85e28e22556897...` | 2 | `MZ`,映像布局与 17ce 不同(节区 #0 va=0) |
| `17cef6e0a5e7b8d1...` | 2 | `MZ`,**本任务唯一使用** |
| `e77338e50726b135...` | 1 | `MZ`,节区 #2 与 17ce 同布局 |

证据:`evidence/a_identity_and_scope.txt`、`evidence/e01_alt_images.txt`、`evidence/e02_raw_copies.txt`。

---

## 2. 地址换算依据(独立复验,不引用 040-043)

**约定:** `ImageBase = 0x00400000`;`VA = ImageBase + RVA`;对 S-IMG(`.tp3` 族)`file_offset == RVA`。

| 探测串 | VA | file_off(=RVA) | 结果 |
|---|---|---|---|
| `gamestateupdate %d` | `0x00DB4700` | `0x009B4700` | MATCH |
| `connectResponse` | `0x00DBFF0C` | `0x009BFF0C` | MATCH |
| `CG_ServerCommand: ` | `0x00DC61AD` | `0x009C61AD` | MATCH |
| `; net-buffer NOT enough` | `0x00D9EE98` | `0x0099EE98` | MATCH |

换算依据 = PE 节区表 + 上述 4/4 逐点字节探测(非仅节区推断)。
**重要限制:** 该 PE 多数节区的 `PointerToRawData == VirtualAddress`,即节区 raw 字段并不描述"文件内位置";
`file_offset == RVA` 是实测成立的读法(043 建立,044 复验通过),仅当 `RVA < 0x00A65000`(文件长)时可读。

---

## 3. 本次检查范围(明确边界)

| 项 | 值 |
|---|---|
| 可读字节范围 | file offset `0x00000000 .. 0x00A64FFF`(10,899,456 B) |
| `SizeOfImage` | `0x0E659000` -> 镜像仅覆盖 **约 4.513 %** 映像空间 |
| 唯一可反汇编代码区 | **节区 #0**,表示 VA `0x00001000 .. 0x008A8000`,文件 `0x00001000 .. 0x008A8000` |
| 三个目标函数 | `0x87C110`、`0x87D5A0`、`0x87A890` — 均在节区 #0,FULL 覆盖 |
| 两个公共核心候选 | `0x87ED70`、`0x87EDB0` — 均在节区 #0,FULL 覆盖 |
| 直接引用扫描 | 整个节区 #0 的 `E8`/`E9` rel32 全量扫描 |
| 间接引用扫描 | 整个节区 #0 的间接 `call/jmp`;全部 present 字节的 absolute-dword 扫描 |
| **已知缺失区(不可读)** | `RVA >= 0x00A65000`:含 IAT/导入区 `0x0CAxxxx`、运行期全局 `0x0764xxxx`/`0x084ABB08`、`/GS` cookie `0x0E3F240` |

**范围复核结论:** 三个目标函数 + 两个核心 + 其 `.text` 直接引用 + 可读数据区 **已全覆盖**;
"IAT 槽值 / 运行期全局 / import name" **不可覆盖**,044 仅对其做"可否用其它静态材料替代"的判定(见 06/07)。

---

## 4. 镜像与磁盘 EXE 的对应(复验)

| 字段 | 磁盘 EXE `36997674...b537` | 恢复镜像 `17cef6e0...f045` |
|---|---|---|
| Machine | `0x14C` (x86) | `0x14C` |
| ImageBase | `0x00400000` | `0x00400000` |
| AddressOfEntryPoint | `0x0E5DC690` | `0x0E5DC690` |
| TimeDateStamp | `0x6096930A` | `0x6096930A` |

-> 同基址 / 同入口 / 同时间戳 = **同源不同态**(磁盘 `.tp3` 加壳 <-> 镜像可反汇编)。

---

## 5. 未变更声明

- 044 **只读**;未写入 `COD OL\`、040-043 目录、FREEZE-005、正式服务器源码。
- 044 全部新产物只落在 `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-STATIC-CLOSURE-044`。
- 043 中已登记的样本身份矛盾(工程预期目标哈希 `E3823FD6...F37B` 在本机不存在)**保持 `UNKNOWN/BLOCKED`**,
  044 **不**扩大、**不**消解该矛盾。
