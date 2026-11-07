# NEXT_TASK_RECOMMENDATION — 唯一下一任务

**建议编号：** `CODOL-BATTLE-SERVER-DLL-NETBIND-040`  
**目标：** CODOL 3.19.26.22 / Build 1649370  
**模块：** `codoMP_client_shipRetailBase.dll`  
**性质：** 只读静态逆向 + 离线验证；不启动游戏，不做 E2E。

---

## 1. 唯一推荐

> **解析主 DLL 的动态 Winsock 绑定表（LoadLibraryA/GetProcAddress），恢复 WS2_32/WSOCK32 函数指针，并从 socket/event 接收 API 下游追踪消息缓冲区。**

必须完成：

1. 定位 `LoadLibraryA("WS2_32.dll")` 与 `GetProcAddress` 调用点。
2. 恢复 `WSAStartup/WSASocketW/WSAEventSelect/WSAEnumNetworkEvents/WSAWaitForMultipleEvents/WSARecv/recvfrom` 等函数指针的存储位置。
3. 从函数指针使用点向上/向下追踪 socket 创建、事件注册、接收缓冲。
4. 记录缓冲区起始、长度、读游标及解析入口候选。
5. 若无法闭合，给出可复核的阻塞证据和最小解除条件。

---

## 2. 为什么是它

039 已证明：

- 网络 API 不在静态导入表，而是动态绑定。
- `.text` 中的静态 IAT 分析无法直接定位网络调用点。
- `.tls`（熵 7.53）与 `.tvm0`（31MB，含 3 个 DLL 导出）不可直接反汇编。
- 不解析动态绑定表，就无法从网络层进入消息缓冲，后续 opcode 分析无基础。

---

## 3. 输入

- DLL 固定 SHA256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`
- ImageBase `0x10000000`
- 039 的 `TARGET_DLL_PE_MAP.md`
- 039 的 `NETWORK_API_CANDIDATES.tsv`
- 039 的 `evidence/net_strings.txt`、`evidence/kernel_net_strings.txt`

---

## 4. 输出

- `00_INDEX.md`
- `DYNAMIC_BINDING_TABLE.md`
- `WINSOCK_FUNCTION_POINTERS.tsv`
- `SOCKET_RECEIVE_CALLCHAIN.md`
- `RECEIVE_BUFFER_CANDIDATES.tsv`
- `NETCHAN_VS_BUFFER_SEPARATION.md`
- `CONFIRMED_VS_UNKNOWN.tsv`
- `UNKNOWN_AND_BLOCKERS.md`
- `SERVER_IMPLEMENTATION_GAP.tsv`
- `NEXT_TASK_RECOMMENDATION.md`
- `TEST_AND_VALIDATION_RESULTS.md`
- `FILE_HASH_MANIFEST.tsv` / `SHA256SUMS.txt`

---

## 5. 验收标准

1. 至少 3 个动态 Winsock 函数指针的存储位置被定位并给出调用证据。
2. 从 socket/event API 到至少一个接收缓冲写入点形成可复核调用链，或给出系统性反证。
3. 每条链有模块、RVA、VA、文件偏移、节区、原始机器码。
4. `.tls/.tvm0` 未解码前不得生成 x86 调用图。
5. 明确区分 netchan 状态与消息缓冲状态。
6. 未修改 FREEZE-005 与正式服务器。
7. 明确声明未做真实客户端 E2E。

---

## 6. 阻塞条件

- 动态绑定表在受保护区且无静态可达路径。
- 需要运行时内存写观测或 API 调用追踪（需单独授权）。
- 只能得到 API 名称而无法得到函数指针存储位置。
