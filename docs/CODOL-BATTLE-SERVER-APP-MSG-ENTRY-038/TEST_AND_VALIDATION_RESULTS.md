# TEST_AND_VALIDATION_RESULTS

**日期：** 2026-10-13（Asia/Shanghai）  
**性质：** 静态/离线验证。未启动游戏，未做 E2E。

---

## 1. 基线哈希复核

| 对象 | 结果 |
|---|---|
| 目标 EXE | SHA256 `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`，匹配 |
| 目标主 DLL | SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`，匹配 |
| 034 runtime image | SHA256 `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`，匹配 |
| 正式服务器源码 | 25 文件，指纹 `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`，匹配 |

---

## 2. 执行的验证

### V-01 PE 节区与模块身份

- 脚本：`scripts/pe_probe.py`
- 输出：`evidence/pe_sections.json`
- 结果：EXE/image_best 同基址、同时间戳；主 DLL 独立基址 `0x10000000`。

### V-02 调用链 DAG

- 脚本：`scripts/xrefs_and_bodies.py`
- 输出：`evidence/xrefs_and_bodies.txt`
- 结果：
  - `0x5F830` 仅有直接调用者 `0x208432`。
  - `0x208380` 仅有直接调用者 `0x1FFB88`。
  - `0x1FF820` 仅有直接调用者 `0x20059B`。
  - `0x2000A0` 直接调用者为 `0x200F10/0x200F34`。

### V-03 0x2000A0 分派表

- 脚本：`scripts/extract_opcode_dispatch.py`
- 输出：`evidence/opcode_dispatch_dump.txt`
- 结果：26 个 opcode/state 分支，索引表 RVA `0x20077C`，跳表 RVA `0x200744`；语义为客户端对象状态/动画更新。

### V-04 解析族语义

- 脚本：`scripts/dump_parser_family.py`
- 输出：`evidence/parser_family_full.txt`
- 结果：`0x6D060` 非消息解析器；`0x6D360/0x6DA30` 等属客户端状态/对象表更新。

### V-05 间接跳转表枚举

- 脚本：`scripts/enumerate_va_tables.py`
- 输出：`evidence/va_indirect_tables.txt`
- 结果：EXE 镜像中 1,279 个候选，1,187 个表可解析；未绑定 netchan 缓冲上下文。

### V-06 候选分派器语义

- 脚本：`scripts/candidate_dispatch_functions.py`
- 输出：`evidence/candidate_dispatch_functions.txt`
- 结果：`0x5D92B`（16 路）与 `0x6728C`（10 路）为字符串/本地化选择器。

### V-07 调用图质量

- 脚本：`scripts/callgraph_quality.py`
- 输出：`evidence/callgraph_quality.txt`
- 结果：
  - E8 总数 201,125；
  - 目标在文件内 158,065；
  - 入口命中 91,770；
  - 边界外 66,295（41.9%）。
- `.tvm0` 类区域 E8/E9 命中 4,414，目标在 text 中 1，比率 0.02%。

### V-08 主 DLL 归属

- 脚本：`scripts/module_identity_strings.py`、`scripts/dll_module_probe.py`、`scripts/dll_indirect_tables.py`
- 输出：`evidence/module_identity_strings.txt`、`evidence/dll_module_probe.txt`、`evidence/dll_indirect_tables.txt`
- 结果：主 DLL 是引擎模块；`netchan/gamestate/configstring` 无明文；`opcode` 仅 Lua/调试/描述符字符串；DLL `.text` 有 738 个间接跳转表候选。

---

## 3. 未执行的测试

- 未启动游戏。
- 未做真实客户端 E2E。
- 未产生抓包。
- 未动态调试、注入或 hook。
- 未验证 gamestate/configstring/snapshot 与目标客户端兼容性。

---

## 4. 结论

离线验证**支持**以下结论：

1. 037 推荐链不是应用层消息入口。
2. 目标 EXE 镜像无法闭合应用层 opcode 分派。
3. 应用层协议更可能在主 DLL 或其未解码区域。
4. 正式服务器实现仍然只有 `SERVER_ONLY` 证据支持。

离线验证**不支持**以下结论：

- 任何具体 opcode→函数映射；
- 任何 netchan 缓冲区格式；
- 任何 gamestate/configstring/snapshot 的完整格式。
