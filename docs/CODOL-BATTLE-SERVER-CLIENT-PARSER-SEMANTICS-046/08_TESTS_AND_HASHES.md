# 08_TESTS_AND_HASHES

**任务:** CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046(只读静态)。
**日期:** 2026-10-13 (Asia/Shanghai)。

---

## 1. 自检脚本

| 脚本 | 作用 | 结果 |
|---|---|---|
| `scripts\verify_046.py` | 从原始字节**重新推导**每条决定性结论(身份、TQOS 归属、TDR 归属、调用者集合、ordinal 槽、游戏串 xref 分离、ZIP 计数、交付物存在) | **24/24 PASS** |
| `scripts\gen_hashes_046.py` | 生成 `SHA256SUMS.txt` + `FILE_HASH_MANIFEST.tsv` | 160 文件 |

`verify_046.py` 判定项(全部 PASS):

```
S-IMG / S-EXE / S-DLL sha256
'udp://%s:%d' @ RVA 0x985AB0
QOSCSPkg @ 0x985AA4 ; QOSSSPkg @ 0x985A78 ; 'tqos_create_protohandle err' @ 0x985B1C
0x85D870 E8 callers == {0x85EC01}
0x85D2E0 E8 callers == {0x85EBBB}
0x87D5A0 E8 callers == {0x85D3DB,0x85D418,0x85D9B5,0x85D9F7}
0x87C110 E8 callers == {0x85D49D}
0x87BA50 == E9 -> 0x87BE00
'lib_src\tdr\tdr_net.c' @ RVA 0x99F060 ; 'net-buffer NOT enough' @ 0x99EE98
0x87ED70 E8 callers == 43
0x87EDB0 E8 callers == {0x87C9B7}
0x879AC0 E8 callers == {0x8799BC,0x879D60,0x879F44,0x87A1F7}
'gamestateupdate %d' refs == {0x54B7B,0x73214}
'EXE_CONFIGSTRINGMISMATCH' refs == {0x731E1,0xF2833}
'EXE_LOSTRELIABLECOMMANDS' refs == {0xF2737,0x376B14}
无游戏串 xref 落在 0x85D000..0x88F000
[0xCA84E8] -> ord18(select) ; [0xCA84E4] -> ord16(recv)
_extracted\SHA256SUMS.txt 列出 79 条
10 份交付物全部存在
```

---

## 2. 只读性声明(未修改基线)

| 对象 | 动作 |
|---|---|
| `COD OL\codoMP_client_shipRetail.exe` | **仅读取**(sha256 重算) |
| `COD OL\codoMP_client_shipRetailBase.dll` | **仅读取** |
| `CODOLServer\...\live\image_best.bin` | **仅读取** |
| `CODOL-BATTLE-SERVER-*040..045` 目录 | **仅读取**;未写入;其 `SHA256SUMS.txt` 未改动 |
| 冻结基线 / 进入大厅基线 / 正式服务器源码 | **未触碰** |
| 游戏 / 客户端 / 战斗服 | **未启动** |
| 动态调试 / 注入 / hook / 运行时内存读取 | **未执行** |

全部新产物只写入 `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\`。

---

## 3. 输入哈希(关键)

| 文件 | 字节 | SHA-256 |
|---|---|---|
| `image_best.bin` (S-IMG) | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` |
| `codoMP_client_shipRetail.exe` (S-EXE) | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` |
| `codoMP_client_shipRetailBase.dll` (S-DLL) | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |
| `CODOL_MOVEMENT_PHYSICS_20261004(1).zip` | 393,674 | `18ca339a563469883a369781f713db6077493dccb046f15c47ada39c69cc8466` |
| `CODOL_MOVEMENT_PHYSICS_20261004(1).md` | 16,275 | `093b30412c7eacc6156d58c7f1e4cd1f707d8438906269739cb675b2499b51d0` |

ZIP 内部:`SHA256SUMS.txt` 79 条 → **OK=79 BAD=0 MISSING=0**。

---

## 4. 输出哈希清单

- `SHA256SUMS.txt` —— 160 行(`<sha256>  <relative/path>`,含交付物、evidence、scripts、_input、_extracted)。
- `FILE_HASH_MANIFEST.tsv` —— 160 行 + 表头(`relative_path\tbytes\tsha256\tcategory`)。
- `category` 取值:`deliverable` / `evidence` / `script` / `input` / `extracted` / `other`。

> 本文件(`08_TESTS_AND_HASHES.md`)在生成哈希清单**之后**写入,
> 故其自身哈希需在最终一轮 `gen_hashes_046.py` 重跑后确定。见 `SHA256SUMS.txt` 中的最终值。

---

## 5. 证据转储对照

| 文件 | 支撑结论 |
|---|---|
| `evidence/00_identity.txt` | 三个样本身份 |
| `evidence/a10_chain_function.txt` | 045 链所在函数完整反汇编 |
| `evidence/a11_tqos_strings.txt` | TQOS 字符串与 `udp://` xref |
| `evidence/a12_tqos_factory.txt` | `QOSCSPkg/QOSSSPkg` 工厂 |
| `evidence/a13_callgraph.txt` | E8 调用图 |
| `evidence/a14_tdr_strings.txt` | TDR `tdr_net.c` 与 net-buffer 诊断 |
| `evidence/a15_ws2_iat_usage.txt` | 全部 socket 原语调用点 |
| `evidence/a16_game_strings.txt` | 游戏协议串 xref(低地址区) |
| `evidence/a17_decoder_prologue.txt` | decoder 参数捕获序言 |
| `evidence/c01_usercmd_vectors.txt` | usercmd 测试向量摘要 |
| `evidence/c02_snapshot_field_widths.tsv` | snapshot 字段/宽度矩阵原始导出 |
| `evidence/c03_playerstate_trace.txt` | PlayerState 轨迹标量 |

---

## 6. 已知局限

1. `demo-player-fields-trace.json` 为**未完成**离线跟踪(`RuntimeError('Unclassified call 0xc42d81')`, `scope` 自述非实包验证)。
2. 移动文档引用的 `camera-motion.json` / `gameplay-playerstate.bin` / `pred_trace.txt` / `n10*.txt`
   **不在 ZIP 内** → 相关结论降为 `REPORT_ONLY`。
3. 本任务**未**对 040–045 的报告逐字复核(仅在需要处引用);其结论按 045 基线继承并显式标注改判点。


