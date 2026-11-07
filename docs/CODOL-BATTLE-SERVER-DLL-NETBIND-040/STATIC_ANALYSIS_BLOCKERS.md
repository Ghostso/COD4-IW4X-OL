# STATIC_ANALYSIS_BLOCKERS — 阻塞点与反证范围

**证据等级: 本文件为 040 的实际阻塞清单。**

## 1. 阻塞清单

| 编号 | 层 | 阻塞 | 等级 | 本任务已排除范围 | 最小解除方法 |
|---|---|---|---|---|---|
| BLK-040-01 | BUFFER→PARSE | 接收后的 netchan/opcode 解析入口未定位 | P0 | 已确认 `recvfrom`(0x235F7E) 写栈缓冲 `[ebp-0x10C]` 后只做 `buf[0]&0xF` + 源校验 + 写 out 结构; 未见 handler 表索引、未见拷贝到持久缓冲区 | 追踪 out 结构 (调用方 `0x2310E5` 的 `[esp+0x14]`) 的下游消费者 |
| BLK-040-02 | 归因 | `0x235xxx` socket/event 对象的协议归属 (游戏 netchan vs 网卡/ICMP 诊断) 未能静态判定 | P0 | `WSASocketW(af=2,type=3,proto=1)` = SOCK_RAW/ICMP; 全 DLL 唯一 WSASocketW 点 | 需运行时观测该 socket 的流量或调用栈 (需单独授权) |
| BLK-040-03 | 归因 | 显式 WS2_32 延迟解析器 (`0x430B10`) 邻接字符串为 libcurl FTP/TELNET, 无法确认它是游戏层还是 libcurl 层 | P1 | 已见 `failed to load WS2_32.DLL`/`FreeLibrary(wsock2)`/`WSAEnumNetworkEvents failed` 等以 libcurl 语境出现 | 交叉核对 libcurl 公开源码字符串集合 |
| BLK-040-04 | 保护区 | 3 个导出与入口点均在 `.tvm0`; VM 未解码 | P0 | 不生成 `.tvm0` 调用图; 仅引用 PE 结构 | VM 解码或去保护 (需单独授权) |
| BLK-040-05 | 保护区 | `.tls` 熵 7.532, 非正常 x86 | P0 | 不线性反汇编 | 解密/去保护 (需单独授权) |
| BLK-040-06 | 导入语义 | 隐藏导入表所属模块的严格归因未完成 (导入描述符数组未在文件内显式锚定) | P1 | 已确认 `.idata2` 含 21 个 DLL 名 + 768 槽 IAT + 653 NAME + 95 ORDINAL; 但未找到指向该描述符数组的显式数据指针 | 需要复现链接器布局或参考同源构建 |
| BLK-040-07 | CROSSREF | EXE 的 OOB/状态链与 DLL 接收路径无接口证据 | P1 | 038/039 已确认二者是不同模块 | 导出/回调共享对象定位 |
| BLK-040-08 | TEST | 无真实客户端 E2E | P0 | 本任务明令禁止 | 需单独授权 |

## 2. 反证范围 (本任务已尝试但未闭合的路径)

1. **无常规 WS2_32/WSOCK32 导入描述符**: PE 数据目录 1 的 3 个描述符 (kernel32/libcef) 之外, 未在 `.data` 中再找到 `TimeDateStamp=0 && Name->*dll` 形态的标准 `IMAGE_IMPORT_DESCRIPTOR`。故隐藏表**不是**标准导入目录的一部分, 其装载机制未完全还原。
2. **栈缓冲区未拷贝到持久缓冲**: `0x235F8F..0x23607C` 全程未出现对 `[ebp-0x10C]` 的 `memcpy`/`rep movs` 到堆。
3. **应用层解析器不在 `.text` 可达处**: 对 0x235xxx 簇的 99 处字符串引用做归属检查, 命中项为 STL 异常串与反汇编器格式串, **无** netchan/opcode/gamestate 语义串。
4. **`.tvm0`/`.tls` 未用于任何结论**: 已在 `RELOCATION_AND_SECTION_NOTES.md` 明确。

## 3. 结论

接收 API 已解析 (recv/recvfrom 等), 函数指针存储位置已定位 (72 个 Winsock 槽), 接收调用点已定位 (recv 12 处, recvfrom 3 处), 且已连成"socket/event → 栈缓冲区写入"的可复核链。但 **缓冲区 → 消息解析器** 一段静态证据不足, 结论为 **UNKNOWN**, 不做推测性闭合。
