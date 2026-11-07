# 01_SAMPLE_IDENTITY_AUDIT — 样本身份核验

**性质:** 只读审计。未启动游戏/服务器;无动态调试/注入/hook/转储。
**日期:** 2026-10-13 (Asia/Shanghai)

---

## 1. 被审计对象(实际文件重新计算,非复用摘要)

| 编号 | 文件 | 字节 | 完整 SHA-256 | 报告前缀/后缀 | 结论 |
|---|---|---|---|---|---|
| S-DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | `ef75…6a20` | **一致** |
| S-EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | `3699…b537` | **一致** |
| S-IMG | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` | `17ce…f045` | **一致** |

> 三份哈希均由 043 从原始字节**重新计算**,不是引用 040/041/042 的截断摘要。

---

## 2. 地址换算约定(独立复验)

| 模块 | ImageBase | 约定 | 复验方式 | 结果 |
|---|---|---|---|---|
| S-DLL | `0x10000000` | 按节区表:`file_off = raw + (RVA - sec.va)` | 节区表读取 | **确认** |
| S-EXE(磁盘) | `0x400000` | `file_off = RVA`(低区) | 节区表:`raw==va` 于首个 `.tp3` | **确认** |
| S-IMG(恢复镜像) | `0x400000` | `file_off = RVA = VA - 0x400000` | **ASCII 串逐点探测**(见下) | **确认** |

### 2.1 镜像 `file_offset = RVA` 探测(4/4 MATCH)

| VA | file_off | 期望串 | 结果 |
|---|---|---|---|
| `0x00DB4700` | `0x009B4700` | `gamestateupdate %d` | MATCH |
| `0x00DBFF0C` | `0x009BFF0C` | `connectResponse` | MATCH |
| `0x00DC61AD` | `0x009C61AD` | `CG_ServerCommand: ` | MATCH |
| `0x00D9EE98` | `0x0099EE98` | `; net-buffer NOT enough` | MATCH |

(脚本 `scripts/a03_convention.py`;输出 `evidence/image_convention_and_correspondence.txt`。)

---

## 3. EXE ↔ 镜像 对应关系

| 字段 | 磁盘 EXE `3699…b537` | 恢复镜像 `17ce…f045` | 判定 |
|---|---|---|---|
| Machine | `0x14C` (x86) | `0x14C` | 同 |
| ImageBase | `0x400000` | `0x400000` | **同** |
| AddressOfEntryPoint | `0x0E5DC690` | `0x0E5DC690` | **同** |
| TimeDateStamp | `0x6096930A` | `0x6096930A` | **同** |
| 节区名/VA/VSize | `.tp3`×6 + `.tvm0`(与镜像同,仅镜像 `.tvm0`→`.tp3`) | 同 | 同源 |

**结论:** `image_best.bin` 是**同一 PE 的运行时/解壳镜像**(同基址、同入口、同时间戳、同节区布局);
磁盘 EXE 的 `.tp3` 为加壳数据,镜像对应区段为**可反汇编代码**。二者**同源不同态**(`CONFIRMED`)。

---

## 4. 镜像覆盖范围(对 042 结论的硬边界)

| 节区 | VA | VSize | 镜像内 | 覆盖 |
|---|---|---|---|---|
| `.tp3` #1 | `0x00001000` | `0x008A689A` | 全 | **FULL** |
| `.tp3` #2 | `0x008A8000` | `0x0016DA70` | 全 | **FULL** |
| `.tp3` #3 | `0x00A16000` | `0x0DBB1CC0` | 仅 `0x62000` | **PARTIAL** |
| `.tp3` #4 | `0x0E5C8000` | `0x00000031` | 部分 | **PARTIAL** |
| `.tp3` #5 | `0x0E5C9000` | `0x00009228` | 部分 | **PARTIAL** |
| `.tp3` 旧 `.tvm0` | `0x0E5D3000` | `0x00004000` | 部分 | **PARTIAL** |
| `.tp3` #7 | `0x0E5D7000` | `0x00082000` | 全 | **FULL** |

- 镜像文件 `0xA65000`,而 `SizeOfImage = 0x0E659000` → 镜像仅覆盖约 **4.5%** 的映像空间。
- **可分析代码区** = 节区 #1(含 042 的 net-buffer 解码器 `0x87xxxx` 与 TQOS `0x85xxxx`)。
- 运行时全局(如 `0x76446B0`、`0x84ABB08`、`0xE3F240` 安全 cookie 值)与 IAT 槽(`0xCA84E8`)落在
  #3/#4/#5,**不可解析** → 见 `04_IMAGE_COVERAGE_AND_BLOCKERS.md`。

---

## 5. `image_best.bin` 多副本问题(必须登记)

`image_best.bin` 在本工作区共 **12 份、4 个不同构建**(同尺寸 10,899,456,不同哈希):

| SHA-256 前缀 | 副本数 | 首个路径 |
|---|---|---|
| `17cef6e0…` | 2 | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\` |
| `d74f45ce…` | 7 | `CODOLServer\_fullimage\run1\fullimage\` |
| `1b85e28e…` | 2 | `CODOLServer\_fullimage\run2\fullimage\` |
| `e77338e5…` | 1 | `run_codol_001\runs\mem_vsd_20260929\` |

- 042 使用的是 **`17ce…f045`**(唯一),其身份与约定**已复验**。
- 其余 3 个构建的**差异未审计**(本任务不扩大范围);**警告**:任何以"image_best.bin"泛称的引用
  必须绑定精确 SHA-256,否则不可复核。
- 清单:`evidence/image_best_copies.tsv`。

---

## 6. 040/041/042 材料完整性(独立重算)

| 项目 | `SHA256SUMS.txt` 行 | 复核 | 结论 |
|---|---|---|---|
| 040 | 32 | 32/32 MATCH | **通过** |
| 041 | 79 | 79/79 MATCH | **通过** |
| 042 | 72 | 72/72 MATCH | **通过** |

- 三项目清单**仅验证文件完整性**,不代表其结论正确性(结论审计见 02/03/04)。
- 盘点共 186 个文件 → `evidence/inventory_040_041_042.tsv`。

---

## 7. 历史样本身份矛盾(保留,不消除)

| 项 | 记录 | 本机实际 | 状态 |
|---|---|---|---|
| 目标宿主 `out.exe`(build 1649370) | 工程审计要求 SHA-256 `E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B` | **本机不存在任何 `out.exe`** | **UNKNOWN / BLOCKED** |
| 实际客户端制品 | — | `3699…b537`(加壳 `.tp3/.tvm0`) | 与 `E3823FD6…` **MISMATCH** |
| 加壳 vs 去壳 | OLMod 记录 `out.exe` 为**去壳**镜像 | 本机制品为**加壳** | 运行时解壳一致性 **UNKNOWN** |

**结论(不得推断):**
1. 本机**无**与 `E3823FD6…F37B` 匹配的客户端;`3699…b537` ≠ 该哈希。
2. 因此 042 的镜像 `17ce…f045` 与 `E3823FD6…` 目标客户端**是否同一构建,无法证实** →
   `UNKNOWN`。上游把 `E3823FD6…` 归为 "3.3.3.3 QA 客户端" 而非 OLfinal 目标的说法,本任务**沿用并保留**,
   不据此断言 042 镜像错误(镜像身份 = 与磁盘 EXE 同源,已确认;与工程预期目标的**版本**关系另论)。
3. OL-mod 工作树存在未提交修改与不同构建哈希(见 `CODOL_OLMOD_AUDIT_20261009_094312`),同样登记。

> 该矛盾**实质影响**"服务器实现对象"的确定 → 列入服务器开工问题账本 A 类。

---

## 8. 041 结论适用边界(重申)

041 的 ICMP/ping 结论**仅适用于**其分析过的接收簇(`codoMP_client_shipRetailBase.dll` 唯一
`WSASocketW` 站点及其 `recvfrom 0x235F7E`)。**不得**扩大为"客户端没有其他网络接收路径"——
042 已在**另一模块(EXE 镜像)**发现 net-buffer 解码原语,即反例。
