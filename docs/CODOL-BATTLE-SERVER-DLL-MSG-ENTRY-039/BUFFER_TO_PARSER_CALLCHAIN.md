# BUFFER_TO_PARSER_CALLCHAIN — 缓冲区到解析器调用链

## 1. 目标链路

```text
网络接收/传输处理
  → netchan 相关状态（序列号/分片/可靠消息/会话）
  → 消息缓冲区（起始指针/有效长度）
  → 读取操作（字节/位/整数/字符串）
  → 应用层分派（opcode/消息类型）
  → 具体处理函数
```

## 2. 已确认部分

### 2.1 可分析区

`.text` 是唯一可靠的主分析区：

- VA `0x1000`，VSize `0x742000`
- 熵 6.994
- 5,410 个 `55 8B EC` 序言
- 168,714 个 `0xCC` 填充
- `FF15 [absolute IAT slot]` 调用普遍存在

### 2.2 网络 API 归属

常规导入表中没有 WS2_32/WSOCK32。相关字符串出现在 `.rdata/.idata2`：

- `WS2_32.dll`
- `WSOCK32.dll`
- `WSAIoctl`
- `WSASocketW`
- `WSAEnumNetworkEvents`
- `WSAEventSelect`
- `WSAWaitForMultipleEvents`
- `gethostbyname`、`getaddrinfo`

**判定（CONFIRMED_DIRECT）：** 网络 API 是动态解析或延迟绑定，不能通过静态 IAT 直接定位调用点。

### 2.3 网络适配层字符串

- `WKNet_`
- `w k _ i p _ c o n f i g . i n i`（UTF-16）
- `[KernelBind]--Packet is NULL`
- `[KernelConnect]--success.`
- `[KernelDisconnect]--Packet is NULL`
- `SendPacket Failed`
- `wkconfig_exper`

**判定（CANDIDATE）：** DLL 内含独立的 Kernel/WKNet 网络适配层，但未找到从它到应用层消息缓冲的直接数据流。

## 3. 未闭合部分

| 环节 | 状态 | 原因 |
|---|---|---|
| 网络接收函数 | `UNKNOWN` | 无静态 IAT；可能运行时绑定 |
| netchan 序列/分片状态 | `UNKNOWN` | 未定位状态写入点 |
| 消息缓冲区起始指针 | `UNKNOWN` | 未定位分配/传入点 |
| 有效长度生成/检查 | `UNKNOWN` | 未定位长度字段 |
| 读游标初始化/推进 | `UNKNOWN` | 未定位读函数 |
| 应用层 opcode 读取 | `UNKNOWN` | 未定位读取指令 |
| 分派表/分支 | `UNKNOWN` | 未定位 |
| 处理函数 | `UNKNOWN` | 未定位 |

## 4. 保护区域限制

### 4.1 `.tls`

- VA `0xB0A000`，VSize `0xED3000`
- 熵 7.532
- 前 `0x2000` 字节线性反汇编仅覆盖 564 字节
- 在 `.tls` 中出现的 `E8/E9` 字节不能作为正常调用证据

**判定：** `.tls` 为加密/保护数据，静态线性分析不可达。

### 4.2 `.tvm0`

- VA `0x19DD000`，VSize `0x1F5E000`
- 熵 7.023
- 未解码前不得按 x86 解释

**判定：** 三个导出全部位于 `.tvm0`，因此外部调用入口可能被 VM 层包裹；这是应用层消息入口无法从 `.text` 线性闭合的结构性原因之一。

## 5. 结论

本任务确认了网络适配层和动态 API 绑定的存在，但未能建立“缓冲区 → 解析器”调用链。所有关键环节保持 `UNKNOWN`，不得用服务器自有 netchan 结构补齐。
