# UNKNOWN_AND_BLOCKERS — 未决问题与最小验证方法

**原则：** 证据不足即 `UNKNOWN`；不以 `.tls/.tvm0` 原始字节猜测 x86 调用链。

## 1. 阻塞清单

| 编号 | 层 | 阻塞 | 等级 | 最小验证方法 |
|---|---|---|---|---|
| BLK-039-01 | NET | WS2_32/WSOCK32 调用点未解析 | P0 | 还原动态 GetProcAddress 绑定表 |
| BLK-039-02 | NET | WKNet_/Kernel* 适配层未绑定到函数 | P0 | 重定位后数据指针分析或运行时 dump |
| BLK-039-03 | PROTECTED | `.tls` 熵 7.532、线性反汇编覆盖 564/8192 | P0 | 解密/去保护或运行时 dump |
| BLK-039-04 | PROTECTED | `.tvm0` 31.4MB 未解码，3 个导出全在其中 | P0 | VM 解码或运行时 dump |
| BLK-039-05 | BUFFER | 未定位缓冲起始/长度/读游标 | P0 | 从网络适配层下游追踪 |
| BLK-039-06 | DISPATCH | 未定位应用层 opcode 读取/分派 | P0 | 需先有 buffer dataflow |
| BLK-039-07 | CROSSREF | EXE OOB/状态链与 DLL 网络层无接口证据 | P1 | 导出/回调/共享对象定位 |
| BLK-039-08 | TEST | 无真实客户端 E2E | P0 | 需单独授权 |

## 2. 已确认结论

1. DLL 指纹与 PE 映射匹配；ImageBase `0x10000000`。
2. 8 个节区中 `.text` 是可分析主区域；`.tls`、`.tvm0` 不可直接反汇编。
3. 网络 API 通过动态绑定使用（常规导入表无 WS2_32/WSOCK32）。
4. DLL 内含 `WKNet_` 与 `[Kernel*]` 网络适配层字符串。
5. 三个 DLL 导出全部位于 `.tvm0`。
6. 连接内消息 buffer、netchan 状态和应用层 opcode 均未闭合。

## 3. 明确不主张

- 不主张已找到网络接收函数。
- 不主张 `WKNet_`/`Kernel*` 是游戏 netchan。
- 不主张服务器 legacy 13B 或 2697 结构适用于目标 DLL。
- 不主张任何 opcode 映射。
- 不主张真实客户端兼容性。

## 4. 最小解除路径

1. 先解析 `LoadLibraryA/GetProcAddress` 的动态绑定表，恢复 WS2_32 函数指针。
2. 从 `WSASocketW/WSAEventSelect/WSAEnumNetworkEvents` 下游追踪接收缓冲。
3. 用重定位修正后的数据指针解析 `WKNet_`/`Kernel*` 适配层对象。
4. 若静态仍不可达，取得运行时 dump 或去保护后的 `.tls/.tvm0`（需单独授权）。
