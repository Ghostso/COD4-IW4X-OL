# TEST_AND_VALIDATION_RESULTS — 独立校验

**性质:** 只读校验。脚本 `scripts/verify_045.py`(可独立运行,全部断言从原始字节重新推导)。
**运行命令:** `python scripts/verify_045.py`  → **exit=0**。

## 1. 自校验断言(从原始字节重新推导,非引用本报告结论)

| # | 断言 | 结果 |
|---|---|---|
| 1 | S-IMG sha256 17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045 | PASS |
| 2 | S-EXE sha256 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537 | PASS |
| 3 | 0x0CA84E8 -> RVA 0x8A84E8 is in file filesize=0xA65000 | PASS |
| 4 | disk 0x8A84E8 == ordinal 18 0x80000012 | PASS |
| 5 | disk 0x8A84E4 == ordinal 16 0x80000010 | PASS |
| 6 | disk 0x8A853C == ordinal 111 0x8000006f | PASS |
| 7 | runtime 0x8A8534 == 0x751C0000+0x9CC0 0x751c9cc0 | PASS |
| 8 | runtime 0x8A853C == 0x751C0000+0x5D50 0x751c5d50 | PASS |
| 9 | 0x87BA50 E8 callers == {0x85D96E,0x85E71A} 0x85d96e,0x85e71a | PASS |
| 10 | 0x87BE00 E8 callers == 0 | PASS |
| 11 | 0x87D5A0 callers include 0x85D9B5,0x85D9F7 | PASS |
| 12 | 0x87BA50 is E9 -> 0x87BE00 | PASS |
| 13 | path cmp 0x2733 (WSAEWOULDBLOCK) | PASS |
| 14 | path sub 0x2714 (WSAEINTR) | PASS |
| 15 | all 12 deliverables exist missing: | PASS |

**结果: 15/15 断言通过(exit=0)。**

## 2. 决定性断言的原始证据(可手工复算)

| 断言 | 复算方法 |
|---|---|
| `0x0CA84E8` 在文件内 | `0xCA84E8 - 0x400000 = 0x8A84E8 < 0xA65000`(文件长) |
| 槽 = `select` | 磁盘 EXE `raw = 0x594000 + (0x8A84E8 - 0x8A8000)` 处 dword = `0x80000012`(序号 18);`ws2_32.dll` 导出序号 18 = `select` |
| 槽 = `recv` | 同上 `0x8A84E4` → `0x80000010`(序号 16)= `recv` |
| 槽 = `WSAGetLastError` | 同上 `0x8A853C` → `0x8000006F`(序号 111)= `WSAGetLastError` |
| 运行期绑定=ws2_32 | 镜像 `0x8A853C` = `0x751C5D50`;`0x751C5D50 - 0x5D50 = 0x751C0000`(=ws2_32 基址) |
| `0x87BE00` E8 调用者=0 | 节区 #1 全量 E8 扫描,E8 目标 VA 无一等于 `0x400000+0x87BE00` |
| `0x87BA50` = thunk | `E9 rel32`,目标 = `0x87BE00` |
| `0x87BA50` 调用者 | E8 目标 VA = `0x400000+0x87BA50` 的站点 = `{0x85D96E, 0x85E71A}` |
| 接收→解码 | `0x85D96E` 调 thunk(返回长度 `esi`),`0x85D9B5`/`0x85D9F7` 把该长度传入 `0x87D5A0` |
| WSA 错误域 | 路径含 `cmp eax,0x2733`(10035 `WSAEWOULDBLOCK`)与 `sub eax,0x2714`(10004 `WSAEINTR`) |

## 3. 完整性校验

- `SHA256SUMS.txt`:对本目录产物(除自身与清单)计算 SHA-256,共登记文件见该文件行数。
- `FILE_HASH_MANIFEST.tsv`:登记**输入样本**(S-IMG/S-EXE/S-DLL)与**六方证据引用**(OLD/2697/OL-mod/CoD4x/IW4x + 040–044)的完整 SHA-256,以及全部**输出产物**哈希。
- 独立复算:用 `sha256(文件)` 与 `SHA256SUMS.txt` 逐行比对,全部一致(除已删除的临时脚本,已重新生成清单)。

## 4. 未执行的验证(明确声明,避免过度声称)

- 未启动游戏或服务器;未做动态调试/注入/hook/内存转储。
- 未运行六方任一实现;互通状态一律 `NOT-OBSERVED`。
- 未裁决 `1154` vs `1162`;未裁决 `0x85Dxxx` 的层次归属。
- **哈希通过 / 脚本通过 / 函数数量 / 边数量 均不代表协议还原完成度**(见 `08` §2)。
