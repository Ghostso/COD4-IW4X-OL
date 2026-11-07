# NEXT_TASK_RECOMMENDATION — 唯一下一任务

**建议编号：** `CODOL-BATTLE-SERVER-DLL-MSG-ENTRY-039`  
**目标：** CODOL 3.19.26.22 / Build 1649370  
**性质：** 主 DLL 静态逆向 + 离线验证；不启动游戏，不做 E2E，不修改正式服务器。

---

## 1. 唯一推荐

> **在主 DLL `codoMP_client_shipRetailBase.dll` 中定位连接内消息读取/分派入口，并把缓冲读取与 netchan 状态分离确认。**

必须完成：

1. 使用 DLL 自身 ImageBase `0x10000000`、节区映射和 738 个间接跳转表的清单。
2. 在 DLL 中定位读取网络缓冲、检查消息长度/opcode、进入解析分支的函数。
3. 把主 DLL 的 `.text` 候选与 `.tvm0` 未解码区域区分；不得对 `.tvm0` 直接做 x86 调用图推断。
4. 对每个候选记录：模块、RVA→VA→file offset、原始指令、调用者、参数/返回值、消息边界。
5. 若无法闭合，必须给出量化反证与最小解除证据。

---

## 2. 为什么是它

038 已证明：

- 037 推荐的 EXE 链是客户端对象状态更新，不是网络消息入口。
- EXE 镜像中没有可绑定的应用层 opcode。
- 主 DLL 才是引擎模块，包含 `.text` 7.4MB 与 `.tvm0` 31MB。
- 当前 60MB DLL 尚未按协议上下文系统分析。

因此继续在 EXE 的非网络分派器或旧 Atlas 地址上投入，收益很低。唯一有明确证据支撑的下一步是**主 DLL 的消息入口定位**。

---

## 3. 前置条件

| 条件 | 要求 |
|---|---|
| 目标 DLL | 必须使用固定 SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` |
| 镜像基址 | `0x10000000` |
| 节区映射 | 按 DLL 自身节区表计算 file offset |
| 基线 | 只读；不得修改 FREEZE-005、正式服务器、原始资产 |
| 任务目录 | 新建独立目录 `CODOL-BATTLE-SERVER-DLL-MSG-ENTRY-039` |
| 动态操作 | 默认静态；插桩/调试需单独授权并记录影响 |

---

## 4. 范围

### 必须做

- DLL 节区/ImageBase/重定位复核。
- 枚举从网络缓冲读取的函数候选。
- 定位 opcode/消息类型比较、跳转表、间接调用表或分支链。
- 将候选与 OOB 命令分派、snapshot 字段类型分派区分。
- 记录每个候选中已确认的读取宽度、偏移、长度检查与失败路径。
- 验证候选表目标是否落在 DLL 函数入口。
- 输出可复现的脚本与原始输出。

### 明确不做

- 不启动游戏。
- 不做真实客户端 E2E。
- 不实现 gamestate/configstring/snapshot 编码。
- 不修改正式服务器。
- 不把 EXE 的 RVA/VA 约定套用到 DLL。
- 不把 `.tvm0` 的原始 E8/E9 当作调用者证据。

---

## 5. 输出文件

建议与 038 相同的稳定证据编号体系：

- `00_INDEX.md`
- `DLL_IDENTITY_AND_MAPPING.md`
- `MSG_READER_CANDIDATES.tsv`
- `OPCODE_DISPATCH_EVIDENCE.tsv`
- `NETCHAN_STATE_SEPARATION.md`
- `MESSAGE_BOUNDARY_SPEC.md`
- `CONFIRMED_VS_UNKNOWN.tsv`
- `UNKNOWN_AND_BLOCKERS.md`
- `SERVER_IMPLEMENTATION_GAP.tsv`
- `NEXT_TASK_RECOMMENDATION.md`
- `TEST_AND_VALIDATION_RESULTS.md`
- `FILE_HASH_MANIFEST.tsv`
- `SHA256SUMS.txt`

---

## 6. 验收标准

1. DLL 指纹与 `0x10000000` 基址/节区映射复核通过。
2. 至少定位一个“读取缓冲并基于 opcode/消息类型分派”的候选，或给出系统性反证。
3. 每个候选有原始机器码、RVA/VA/file offset、调用者与参数关系。
4. 已确认的 opcode 映射与 `UNKNOWN` 数量明确。
5. OOB 分派、应用层 opcode、snapshot 字段类型分派三者分开记录。
6. 缓冲长度、读指针、边界检查与错误路径逐项标明确认或 unknown。
7. 未修改冻结基线与正式工程；测试与构建结果真实。
8. 明确声明未做真实客户端 E2E。
9. 若命中 `.tvm0`，必须先解码或明确阻塞，不得把原始字节当 x86。

---

## 7. 阻塞条件

出现以下任一情况应停在该结论，不得猜测：

- DLL 候选需要运行时内存或未解码 VM 才能继续。
- 只能通过其他游戏版本惯例推断 opcode。
- 需要启动游戏或抓包。
- 无法区分 OOB 文本分派、应用层 opcode 与 delta 字段类型分派。
