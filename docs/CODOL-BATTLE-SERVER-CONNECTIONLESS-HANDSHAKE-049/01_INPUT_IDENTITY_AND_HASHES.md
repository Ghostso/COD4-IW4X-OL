# 01 — 输入身份、哈希与版本

## 1. 基础口径

| 项 | 值 |
|---|---|
| 049 工作目录 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CONNECTIONLESS-HANDSHAKE-049` |
| 服务器工程 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047` |
| 分析方式 | 只读静态(pefile + capstone);无运行时访问、无注入、无 hook、无内存读取 |
| 地址口径 | 恢复映像 `file_offset == RVA`;`VA = RVA + 0x400000` |
| 反汇编工具 | capstone `base = ImageBase` → **分支目标在 op_str 中是 VA**;`RVA = VA - 0x400000` |

> **本任务最重要的口径纪律:** 同一映像里,`push imm32` 与 `call rel32` 的操作数是 **VA**,
> 而文件偏移/RVA 是 **VA - 0x400000**。048 在一处把两者混用(见 `07` §D0),本轮已修正。

## 2. 样本身份(SHA-256,本轮实测)

| 代码 | 文件 | 大小 | SHA-256 |
|---|---|---|---|
| S-IMG | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` |
| S-EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |
| S-DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |

三者与 046 `evidence\00_identity.txt`、048 `01` §3 **完全一致** → 同一构建,无新身份差异。

## 3. 恢复映像 PE 结构(S-IMG)

| 节 | VA | VSize | Raw(=VA) | RSize |
|---|---|---|---|---|
| .tp3 | 0x00001000 | 0x8A689A | 0x00001000 | 0x8A7000 |
| .tp3 | 0x008A8000 | 0x16DA70 | 0x008A8000 | 0x16E000 |
| .tp3 | **0x00A16000** | **0x0DBB1CC0** | 0x00A16000 | **0x00062000** |
| .tp3 | 0x0E5C8000 | 0x31 | 0x00A78000 | 0x1000 |
| .tp3 | 0x0E5C9000 | 0x9228 | 0x00A79000 | 0xA000 |
| .tp3 | 0x0E5D3000 | 0x4000 | 0x00A83000 | 0x4000 |
| .tp3 | 0x0E5D7000 | 0x82000 | 0x00771000 | 0x6000 |

- `ImageBase = 0x00400000`;`EntryPoint = 0x0E5DC690`。
- 映像实际长度 `0x0A65000` = 10,899,456 字节,**恰好覆盖到第 3 节 Raw 起点 `0xA16000` 之后
  0x4F000 字节**;第 3 节声明 VSize `0xDBB1CC0`,磁盘 RawSize 仅 `0x62000`(壳压缩)。
- 结论:映像在第 3 节只含前 `0x4F000` 字节(见 `08`)。

## 4. 工作区内的全部候选映像(本轮新查)

| 路径 | 大小 | SHA-256(前 16) | MZ | 非零字节 | 可用性 |
|---|---|---|---|---|---|
| `_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d1` | ✅ | 9,354,801 | **S-IMG 基准** |
| `_mainline\_pop3_rpm_20260925_174041\live\image_best.bin` | 10,899,456 | `d74f45ce5193d496` | ❌ | **0** | 全零,不可用 |
| `_mainline\_pop3_run_20260925_173843\live\image_best.bin` | 10,899,456 | `d74f45ce5193d496` | ❌ | **0** | 全零,不可用 |
| `_mainline\_pop3_smoke\image_best.bin` | 10,899,456 | `d74f45ce5193d496` | ❌ | **0** | 全零,不可用 |
| `_fullimage\run1\fullimage\image_best.bin` | 10,899,456 | `d74f45ce5193d496` | ❌ | **0** | 全零,不可用 |
| `_fullimage\run2\fullimage\image_best.bin` | 10,899,456 | `1b85e28e22556897` | ✅ | 6,439,332 | 见 §5,与基准不同构建态 |

> `_fullimage` 的目录名有误导性:run1 是**全零**文件,run2 是另一个哈希,二者都**没有**超出
> 基准映像的长度,因此都**没有**补齐第 3 节区。

## 5. run2 与基准的差异(不可替代基准)

| 对比项 | 结果 |
|---|---|
| 大小 | 两者均 10,899,456 |
| `connectResponse` @ 0x9BFF0C | **相同**(两映像都有该串) |
| 泵 `0xF8FB0` 首 16 字节 | **不同** |
| 出队 `0x221E50` 首 16 字节 | **不同** |
| P5 循环 `0x7A41D0` 首 16 字节 | **不同**(run2 此处为 0) |
| 连接无关分派 `0x1C13A0` 首 16 字节 | **不同** |
| 16 字节块相等数 | 113,572 / 681,216 |
| 全文件差异字节 | 8,671,354 |

- run2 与基准**不是**同一字节镜像,其代码区内容与基准不一致(疑似不同运行时/不同解密阶段),
  且第 3 节 present 窗口与基准**不相等**(3,167 字节差异)。
- **裁定:run2 不可作为基准映像的替代或补丁来源。** 理由:代码段不一致且同样未覆盖第 3 节区,
  用它替换基准会改变所有地址证据的语义。仅保留其哈希与差异记录作为身份证据。

## 6. 与 046/047/048 的一致性

| 046/048 断言 | 本轮结果 |
|---|---|
| S-IMG SHA-256 `17cef6e0…f045` | ✅ 一致 |
| S-EXE / S-DLL SHA-256 | ✅ 一致 |
| 连接无关词表 RVA 0x9BFCE8..0x9BFFA0 | ✅ 逐串复核一致 |
| 请求格式串 0x9BFD04 / 0x9BFE28 | ✅ 一致 |
| 第 3 节 RSize `0x62000` 缺口 | ✅ 复核,并量化 present 窗口为 `0x4F000` |
| 048 `0x621E50` = 泵队列消费者 | ❌ **地址口径错误**,见 `07` §D0 |
