# UNKNOWN_AND_BLOCKERS — 未决问题与最小验证方法

**原则：** 证据不足即 UNKNOWN；不得以相似名称或服务器实现替代目标机器码。

## 1. 阻塞清单

| BLK_ID | LAYER | BLOCKER | SEVERITY | EVIDENCE | MINIMAL_VERIFICATION | IMPACT |
|---|---|---|---|---|---|---|
| BLK-038-01 | APP | Application opcode read/dispatch not located in target EXE image | P0 | evidence/va_indirect_tables.txt | Locate buffer-reader in main DLL or runtime dump | Cannot define message entry |
| BLK-038-02 | APP | netchan reassembly buffer never linked to a parser | P0 | evidence/refs_indirect_calls.txt | Find sequence/fragment state writes | Cannot bind opcode source |
| BLK-038-03 | APP | 037 chain is client object-state update, not network parser | P0 | evidence/opcode_dispatch_dump.txt | Treat 038 as correction; choose new module target | Prevents implementing wrong protocol |
| BLK-038-04 | PARSER | 0x6D060 semantics are not message parsing | P0 | evidence/parser_family_full.txt | Reclassify 034 family labels | Prevents false gamestate implementation |
| BLK-038-05 | MODULE | Application protocol may reside in main DLL or .tvm0 | P0 | evidence/module_identity_strings.txt; evidence/dll_indirect_tables.txt | Analyze DLL with correct imagebase 0x10000000 | Current EXE-only analysis insufficient |
| BLK-038-06 | CALLGRAPH | 41.9% of in-file E8 targets outside heuristic entries | P1 | evidence/callgraph_quality.txt | Recover function boundaries or runtime symbols | Cannot assert absence of callers |
| BLK-038-07 | VM | DLL .tvm0 31MB undecoded | P0 | evidence/dll_module_probe.txt | Decode VM or obtain runtime dump | Potential dispatcher may be hidden |
| BLK-038-08 | OOB | OOB inbound envelope and length rules unknown | P1 | 037/035 evidence | Trace 0x1C13A0 branch bodies | Cannot emit target-valid OOB |
| BLK-038-09 | TEST | No real target capture or E2E | P0 | Task rules | Requires separate authorization | No compatibility claim possible |

## 2. 已证结论

1. 目标 EXE/image_best.bin 与主 DLL 是两个模块；DLL ImageBase=0x10000000。
2. 037 链 0x5F830 ← 0x208380 ← 0x1FF820 ← 0x20059B 是客户端对象状态更新链，不是应用层网络消息入口。
3. 0x2000A0 的 26 路分派读取 [ebx+0xBC]，调用者遍历 [ebx+0x120] 数组。
4. 0x6D060 是客户端模式/进度浮点辅助函数，不是 gamestate/configstring 解析器。
5. EXE 镜像 1,279 个间接跳转候选中没有可绑定 netchan 缓冲上下文的应用层 opcode 表。
6. 主 DLL 才是引擎模块；netchan/gamestate/configstring 无明文，opcode 字符串仅 Lua/调试用途。

## 3. 明确不主张

- 不主张已经找到应用层 opcode 映射。
- 不主张 0x5D92B/0x6728C/0x39634 是消息分派器；前两者已证为字符串选择器，后者上下文不足。
- 不主张 034 解析族 0x6D060..0x6E0A0 是 gamestate/configstring 解析器。
- 不主张服务器 legacy 13B 或 2697 netchan 与目标客户端一致。
- 不主张真实客户端兼容性。

## 4. 最小解除方法

1. 用 DLL ImageBase=0x10000000 和节区表重新建立候选地址。
2. 在 DLL 中定位网络缓冲读取、长度检查与 opcode 比较。
3. 将候选与 OOB 文本分派、snapshot 字段类型分派分开。
4. 对 .tvm0 先解码；未解码前不得按 x86 推断。
5. 若仍无法闭合，取得目标运行时内存 dump 或完整重定位/符号信息（需单独授权）。
