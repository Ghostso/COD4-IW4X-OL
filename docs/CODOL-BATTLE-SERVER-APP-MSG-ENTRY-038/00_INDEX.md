# CODOL-BATTLE-SERVER-APP-MSG-ENTRY-038

**目标：** CODOL 3.19.26.22 / Build 1649370（2021-05-07）  
**日期：** 2026-10-13（Asia/Shanghai）  
**性质：** 只读静态逆向 + 离线验证。未启动游戏，未做真实客户端 E2E，未修改 FREEZE-005 或正式服务器。

---

## 0. 结论摘要

1. **目标指纹全部匹配**：EXE `3699…b537`、主 DLL `ef75…6a20`、034 运行时镜像 `17ce…f045`、正式源码指纹 `5655…fddf`。
2. **地址约定必须按模块区分**：`image_best.bin` 与 `codoMP_client_shipRetail.exe` 同基址、同时间戳、同节区，低 RVA 区域满足 `file_offset = RVA`；主 DLL 映像基址为 `0x10000000`，有独立 `.text/.rdata/.data/.tls/.tvm0`，不能用 EXE 的 RVA 约定。
3. **037 推荐的 `0x5F830 ← 0x208380 ← 0x1FF820 ← 0x20059B` 链已被复核，但不是应用层网络消息入口**：`0x2000A0` 是客户端对象状态/动画更新分派器，读取 `[ebx+0xbc]` 做 0..25 分派；其调用者遍历 `[ebx+0x120]` 数组。该链属于客户端状态更新子流程，不能作为 netchan/opcode 入口。
4. **034 的 “gamestate/configstring 解析族” 标签至少部分是误判**：`0x6D060` 读取客户端全局状态与 `+0x1d/+0x1e` 模式值、执行浮点计算并调用 `0x404340`，不是消息解析器。
5. **真实应用层 opcode 读取与分派结构未在目标 EXE 镜像闭合**：扫描 1,279 个间接跳转候选中没有可绑定 netchan 缓冲/应用层消息上下文的 0..5 或 0..6 分派；候选 `0x5D92B`（16 路）与 `0x6728C`（10 路）经反汇编确认是本地化/字符串选择器。
6. **模块边界修正**：主 DLL 是引擎模块（`.text` 7.4MB、`.tvm0` 31MB），含 `opcode` 明文但也仅见于 Lua/调试符号；`netchan/gamestate/configstring` 在主 DLL 均无明文。应用层 opcode 更可能在主 DLL 的 `.text/.tvm0` 或未恢复区域，尚不能从现有镜像线性闭合。
7. **服务器实现缺口**：现有服务器有自建 legacy/2697 分派与自建 13B/2697 netchan，但都没有目标客户端证据；不得把服务器结构外推为目标客户端协议。

---

## 1. 交付物

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 范围、结论、证据入口 |
| `TARGET_BINARY_IDENTITY.md` | 三个模块的 PE 身份、哈希、节区与地址约定 |
| `CALLCHAIN_UPWARD.tsv` | 从 `0x5F830` 向上的逐级调用链与语义 |
| `NETCHAN_BUFFER_FLOW.md` | 应用层 opcode 的真实模块边界与阻塞 |
| `APP_OPCODE_DISPATCH.tsv` | opcode 分派候选逐项判定 |
| `MESSAGE_ENTRY_SPEC.md` | 已确认/未确认的消息入口规格 |
| `PARSER_BRANCH_EVIDENCE.tsv` | `0x6D060..0x6E0A0` 解析族逐项证据与语义 |
| `SERVER_IMPLEMENTATION_GAP.tsv` | 目标证据与服务器实现差距 |
| `UNKNOWN_AND_BLOCKERS.md` | 未决问题与最小验证方法 |
| `NEXT_TASK_RECOMMENDATION.md` | 唯一下一任务建议 |
| `TEST_AND_VALIDATION_RESULTS.md` | 实际执行的验证命令与结果 |
| `FILE_HASH_MANIFEST.tsv` / `SHA256SUMS.txt` | 完整性清单 |

---

## 2. 关键证据入口

- `evidence/module_identity_strings.txt`
- `evidence/opcode_dispatch_dump.txt`
- `evidence/xrefs_and_bodies.txt`
- `evidence/parser_family_full.txt`
- `evidence/callers_of_parser.txt`
- `evidence/va_indirect_tables.txt`
- `evidence/candidate_dispatch_functions.txt`
- `evidence/callgraph_quality.txt`
- `evidence/dll_module_probe.txt`
- `evidence/dll_indirect_tables.txt`
- `scripts/*.py`

---

## 3. 状态定义

- `CONFIRMED_DIRECT`：目标机器码/数据表直接支持。
- `CONFIRMED_CROSSREF`：完整交叉引用与调用链支持，语义有限。
- `SERVER_ONLY`：仅服务器代码存在。
- `TEST_VERIFIED`：仅对应离线验证通过。
- `UNKNOWN`：证据不足。

---

## 4. 最终声明

**未执行真实客户端 E2E。** 本任务没有启动游戏、没有产生抓包、没有把合成测试当作兼容性证据。
