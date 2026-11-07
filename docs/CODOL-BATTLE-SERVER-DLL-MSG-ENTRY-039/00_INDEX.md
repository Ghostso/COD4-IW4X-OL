# CODOL-BATTLE-SERVER-DLL-MSG-ENTRY-039

**目标：** CODOL 3.19.26.22 / Build 1649370（2021-05-07）  
**模块：** `codoMP_client_shipRetailBase.dll`  
**日期：** 2026-10-13（Asia/Shanghai）  
**性质：** 只读静态逆向 + 离线验证。未启动游戏，未动态调试/注入/hook，未做真实客户端 E2E，未修改 FREEZE-005 或正式服务器。

---

## 0. 结论摘要

1. **目标指纹与 PE 映射已确认**：DLL SHA256 `ef75…6a20`、ImageBase `0x10000000`、8 个节区；EXE/DLL/034 镜像/正式源码指纹全部匹配。
2. **可分析区域已明确分离**：
   - `.text`：7.4MB，熵 6.994，5,410 个 `55 8B EC` 序言，168,714 个 `0xCC`；可作为主要静态分析区。
   - `.rdata/.data/.idata2/.rsrc2/.reloc`：数据/导入/资源/重定位。
   - `.tls`：15.5MB，熵 **7.532**，线性反汇编前 0x2000 字节仅覆盖 564 字节；**不可按正常 x86 调用图分析**。
   - `.tvm0`：31.4MB，熵 7.023，439 个疑似序言但语义不明；**不得按普通 x86 直接生成调用图**。
3. **网络 API 归属已确认**：DLL 常规导入表仅 `kernel32`（LoadLibraryA/GetProcAddress）与 `libcef`；`.rdata/.idata2` 含 `WS2_32.dll`、`WSOCK32.dll`、`WSASocketW`、`WSAIoctl`、`WSAEnumNetworkEvents`、`WSAEventSelect`、`WSAWaitForMultipleEvents`、`gethostbyname/getaddrinfo` 等字符串。由此判定网络 API 通过**动态绑定/延迟解析**使用，而非静态 IAT。
4. **网络适配层候选已定位但未闭合**：`.rdata` 存在 `WKNet_`、`w k _ i p _ c o n f i g . i n i`、`[KernelBind]`、`[KernelConnect]`、`[KernelDisconnect]`、`SendPacket` 等字符串，说明 DLL 内含独立网络内核/驱动适配层。
5. **连接内消息入口未找到**：`.text` 中未定位“读取 netchan 缓冲 → opcode → 分派”的函数。已排除 `.text` 中与字符串/本地化有关的间接跳转候选；无一项满足 buffer dataflow 证据。
6. **关键阻塞**：真实网络入口可能在 `.tls`（熵 7.53，非正常代码）或通过运行时解密/虚拟化调用，静态线性分析不可达。`.tvm0`（31MB）同样不可直接分析。
7. **服务器实现缺口**：现有 legacy 13B/2697 netchan 均为 `SERVER_ONLY`，无目标 DLL 证据；不得外推。

---

## 1. 交付物

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 范围、结论、证据入口 |
| `TARGET_DLL_PE_MAP.md` | DLL PE 结构、节区、目录、导入/导出 |
| `DLL_ANALYZABLE_REGIONS.tsv` | 各节区可分析性判定 |
| `NETWORK_API_CANDIDATES.tsv` | 网络 API 与适配层候选 |
| `NETCHAN_STATE_EVIDENCE.tsv` | netchan 状态候选（本任务未闭合） |
| `MESSAGE_BUFFER_EVIDENCE.tsv` | 消息缓冲候选（本任务未闭合） |
| `BUFFER_TO_PARSER_CALLCHAIN.md` | 缓冲区到解析器的调用链分析 |
| `APP_MESSAGE_DISPATCH_EVIDENCE.tsv` | 应用层分派判定 |
| `EXE_DLL_CROSS_REFERENCE.md` | 与 038 EXE 证据的交叉核验 |
| `SERVER_IMPLEMENTATION_GAP.tsv` | 服务器差距矩阵 |
| `UNKNOWN_AND_BLOCKERS.md` | 未决与最小验证方法 |
| `NEXT_TASK_RECOMMENDATION.md` | 唯一下一任务建议 |
| `TEST_AND_VALIDATION_RESULTS.md` | 实际执行的验证 |
| `FILE_HASH_MANIFEST.tsv` / `SHA256SUMS.txt` | 完整性清单 |

---

## 2. 关键证据入口

- `evidence/pe_map.txt`
- `evidence/net_strings.txt`
- `evidence/network_api_xrefs.txt`
- `evidence/winsock_api_xrefs.txt`
- `evidence/kernel_net_strings.txt`
- `evidence/tls_reloc_resources.txt`
- `evidence/reloc_pointer_analysis.txt`
- `evidence/tls_tvm_analysis.txt`
- `scripts/*.py`

---

## 3. 状态定义

- `CONFIRMED_DIRECT`：目标 DLL 机器码/数据表/PE 结构直接支持。
- `CONFIRMED_DATAFLOW`：可追踪的数据流/参数传递。
- `CONFIRMED_CROSSREF`：可复核交叉引用，语义未完全闭合。
- `CANDIDATE`：部分证据，仍需验证。
- `SERVER_ONLY`：仅服务器侧实现。
- `UNKNOWN`：证据不足。

---

## 4. 最终声明

**未执行真实客户端 E2E。** 未启动游戏，未动态调试/注入/hook，未修改原始资产、FREEZE-005 或正式服务器。
