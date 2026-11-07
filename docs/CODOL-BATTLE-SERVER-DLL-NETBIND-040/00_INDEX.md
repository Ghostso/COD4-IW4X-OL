# CODOL-BATTLE-SERVER-DLL-NETBIND-040

**目标:** CODOL 3.19.26.22 / Build 1649370 (2021-05-07)
**模块:** `codoMP_client_shipRetailBase.dll`
**日期:** 2026-10-13 (Asia/Shanghai)
**性质:** 只读静态二进制分析 + 离线验证。未启动游戏, 无动态调试/注入/hook, 未做真实客户端 E2E, 未修改 FREEZE-005 或正式服务器源码。

---

## 0. 结论摘要 (必读)

1. **目标指纹匹配**: DLL SHA256 `ef75...6a20`, EXE SHA256 `3699...b537`, 正式源码 25 文件指纹 `5655...fdf`。全部与任务给定值一致 (见 `TEST_AND_VALIDATION_RESULTS.md`)。
2. **相对 039 的重大修正**: 039 依据常规导入表目录 (Size=0x3C, 仅 3 个导入) 判定 DLL "无静态 WS2_32/WSOCK32 导入"。040 发现 PE 数据目录 1 声明的导入描述符**只是子集**; `.idata2` (RVA `0xB02000..0xB06EBA`) 实际容纳了一个完整的 **768 槽 IAT + 653 名称导入 + 95 序号导入 + 21 个 DLL 模块名** 的隐藏导入表。因此网络 API 归属**并非纯运行时 GetProcAddress 绑定**, 而是主要通过该隐藏 IAT 直接间接调用 (FF15)。
3. **已确认的动态绑定调用点**: `LoadLibraryA` 共 **18** 个 FF15 调用点; `GetProcAddress` 共 **42** 个 FF15 调用点。其中 `.text:0x430B10` 是一个**显式的 "延迟解析 WS2_32.DLL" 包装器**: `LoadLibraryA("WS2_32.DLL")` + 逐个 `GetProcAddress` 解析 WSACreateEvent/WSACloseEvent/WSAEventSelect/WSAEnumNetworkEvents 等, 返回值保存到栈槽 (`[esp+0x30]`/`[esp+0x34]`/`[esp+0x38]`) 并在同函数内立即 `call`。
4. **已确认的 Winsock 函数指针存储位置数量 = 72**: 72 个 Winsock/网络 API 槽在隐藏 IAT `.idata2` (`0xB02A40..0xB02B5C`) 中拥有固定静态位置, 槽内文件值为 `IMAGE_IMPORT_BY_NAME` 指针 (NAME, 如 WSASocketW/WSAEventSelect) 或序号 (ORDINAL, 如 recv=16/recvfrom=17/sendto=20)。全部 72 槽见 `WINSOCK_FUNCTION_POINTERS.tsv`。
5. **已确认的实际接收调用点**: `recvfrom` (WS2_32 序号 17) 在槽 `0xB02A48`/`0xB02B3C` 共 **3** 处真实间接调用 (`FF15`), 其中 `0x235F7E` (VA `0x10235F7E`) 属 socket/event 接收簇; `recv` (序号 16) 在槽 `0xB02AA8`/`0xB02B1C` 共 **12** 处 `FF15` 调用点 (多数位于 statically-linked libcurl/OpenSSL)。全 DLL 共 **248** 个 Winsock FF15 调用点。
6. **socket/event → 缓冲区写入链**: 已闭合到**数据被写入栈缓冲区**这一层 (`CONFIRMED_DATAFLOW`)。socket 创建 (`WSASocketW`)、事件注册 (`WSAEventSelect`)、事件等待 (`WSAWaitForMultipleEvents`)、事件解码 (`WSAEnumNetworkEvents`)、`recvfrom` 均在同一 socket 对象上, 缓冲区为 `[ebp-0x10C]`。
7. **缓冲区 → 解析器链路**: **UNKNOWN**。接收写入后 0x235F8x 起对数据做了头部长度/序号校验, 但未见可复核的 netchan 解析或以 opcode 驱动的分派; 应用层解析入口仍**未定位**。
8. **保护区影响**: 3 个 DLL 导出全部位于 `.tvm0` (RVA `0x1AA13B0/0x1D6582C/0x203D4F7`); `.tls` (熵 7.532) 亦不可直接线性反汇编。本报告**未**将 `.tvm0`/`.tls` 字节按普通 x86 生成调用图。
9. **反对过度声称**: 不主张已恢复 `.tvm0`/`.tls` 内任何函数; 不主张接收链路已进入消息解析器; 不主张客户端与服务器 2697/13B netchan 结构兼容。

---

## 1. 交付物

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 范围/结论/入口 |
| `DYNAMIC_BINDING_CALLS.tsv` | LoadLibraryA/GetProcAddress 动态绑定调用点 |
| `WINSOCK_FUNCTION_POINTERS.tsv` | 72 个 Winsock 函数指针存储位置 + 全部调用点 |
| `NETWORK_API_EVIDENCE.tsv` | 每个受查 API 的分阶段证据等级 |
| `SOCKET_EVENT_RECEIVE_CHAIN.md` | socket/event → 接收缓冲区链路 |
| `BUFFER_WRITE_AND_LENGTH_FLOW.tsv` | 缓冲区/长度/返回值数据流 |
| `RELOCATION_AND_SECTION_NOTES.md` | 节区/重定位/保护区说明 |
| `STATIC_ANALYSIS_BLOCKERS.md` | 阻塞点与反证范围 |
| `SERVER_IMPLEMENTATION_GAP.tsv` | 服务器侧差距矩阵 |
| `NEXT_TASK_RECOMMENDATION.md` | 唯一下一任务 |
| `TEST_AND_VALIDATION_RESULTS.md` | 实际执行的验证 |
| `FILE_HASH_MANIFEST.tsv` | 交付文件哈希清单 |
| `SHA256SUMS.txt` | SHA256 校验文件 |

原始证据: `evidence/idata2_iat_slots.tsv`, `evidence/winsock_slots.tsv`, `evidence/winsock_callsites.tsv`, `evidence/loadlib_gpa_callsites.tsv`, `evidence/analysis_summary.json`。

---

## 2. 证据等级定义

- `CONFIRMED_DIRECT`: DLL 机器码/数据表/PE 结构直接支持。
- `CONFIRMED_DATAFLOW`: 可追踪的参数/缓冲区数据流。
- `CONFIRMED_CROSSREF`: 可复核交叉引用, 语义未完全闭合。
- `CANDIDATE`: 部分证据, 仍需验证。
- `UNKNOWN`: 证据不足。

---

## 3. 最终声明

**未执行真实客户端 E2E。** 未启动游戏, 未动态调试/注入/hook, 未修改原始客户端资产、FREEZE-005 或正式服务器源码。
