# TEST_AND_VALIDATION_RESULTS

**日期:** 2026-10-13 (Asia/Shanghai)
**性质:** 只读静态分析 + 离线校验

## 1. 指纹校验 (开始前重算)

| 检查项 | 实测 | 期望 | 结果 |
|---|---|---|---|
| 目标 DLL SHA256 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | PASS |
| 目标 EXE SHA256 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | PASS |
| 正式源码指纹(25 .cs) | `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf` | `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf` | PASS |
| 源码文件数 | `25` | `25` | PASS |

## 2. PE 映射与结构校验

| 检查项 | 实测 | 期望 | 结果 |
|---|---|---|---|
| ImageBase | `0x10000000` | `0x10000000` | PASS |
| 接收簇关键机器码校验 (7处) | `PASS` | `全部匹配` | PASS |
| recvfrom 槽 0xB02A48 值 | `0x80000011` | `0x80000011 (ord 17)` | PASS |
| WSASocketW 槽 0xB02A60 指向 | `0xb0692e` | `0x00B0692E` | PASS |
| 入口点首条指令 | `e90fffa901` | `e90fffa901 (jmp 0x11AA13B0 -> .tvm0)` | PASS |

## 3. 执行的验证脚本 (均只读)

| 脚本 | 作用 | 退出 |
|---|---|---|
| `scripts/analyze_netbind.py` | 解析 PE、隐藏 IAT 768 槽、FF15 调用点、LoadLibrary/GetProcAddress 调用点 | 0 |
| `scripts/_verify_bytes.py` | 逐字节核对接收链路引用的机器码 (15 处) | 0 |
| `scripts/_struct.py` | 导出节区/重定位/导出/常规导入结构 | 0 |
| `scripts/gen_*.py` | 生成交付 TSV/MD (纯文本) | 0 |

## 4. 计数复核 (与交付表一致)

| 指标 | 值 | 来源 |
|---|---:|---|
| 隐藏 IAT 槽数 | 768 | `evidence/analysis_summary.json:n_iat_slots` |
| NAME 导入 | 653 | `n_named` |
| ORDINAL 导入 | 95 | `n_ordinal` |
| Winsock 固定槽 | 72 | `evidence/winsock_slots.tsv` 行数 |
| `.text` FF15 调用点 (全部) | 4738 | `n_ff15` |
| Winsock FF15 调用点 | 248 | `evidence/winsock_callsites.tsv` 行数 |
| LoadLibraryA 调用点 | 18 | `DYNAMIC_BINDING_CALLS.tsv` (DBC API=LoadLibraryA) |
| GetProcAddress 调用点 | 42 | 同上 (API=GetProcAddress) |

## 5. 完整性校验

所有交付文件以 `SHA256SUMS.txt` + `FILE_HASH_MANIFEST.tsv` 记录; 生成后重新计算并与清单逐项核对 (见 `SHA256SUMS.txt` 自校验段)。

## 6. 明确声明

**未执行真实客户端 E2E。** 未启动游戏, 未动态调试/注入/hook, 未修改原始客户端资产、FREEZE-005、正式服务器源码。未对 `.tvm0`/`.tls` 做语义反汇编。

## 7. 结论

目标 DLL/EXE/源码指纹全部匹配 (PASS)。PE 映射、隐藏 IAT 结构、接收链路关键机器码全部通过逐字节复核。无失败项。
