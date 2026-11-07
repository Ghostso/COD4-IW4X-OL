# G2 — 客户端消息接收与分派独立追踪

> 样本哈希：原始客户端 `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`  
> 恢复镜像 `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`  
> ImageBase `0x400000`；本文 RVA 均为映像 RVA，E8 目标为 VA。

## 1. 搜索原则

不以 `0xA2E50` 为唯一中心，而是从：
1. IAT 中的 socket 接收函数；
2. socket 包装器及 vtable；
3. 网络对象调用者；
4. 字符串引用的协议路标；
5. 辅助 DLL 的桥接层

逐层追踪。仅把 Capstone 能确认为实际 `call/jmp dword ptr [IAT]` 的指令算作网络调用点；字节搜索命中的立即数/数据不算。

## 2. IAT 与网络调用点

恢复镜像真实网络导入包括：
- `ws2_32.dll`: `recv` IAT `0xBAE490`、`recvfrom` `0xBAE50C`、`send`、`sendto`、`connect`、`socket`
- `wsock32.dll`: `select`、`closesocket`、`WSAGetLastError`、`htons` 等

经验证为真实 IAT call/jmp 的地址：
- `0x602441`：`call [recv]`
- `0x6029BE`：`call [recv]`
- `0x6052AD`：`call [recv]`
- `0x76D65E`：`jmp [recv]`
- `0x775A6E`：`call [recv]`
- `0x784F7F`：`call [recv]`
- `0x788135`：`call [recv]`
- `0x775AA2`：`call [sendto]`
- `0x775ADE`：`call [recvfrom]`
- `0x77592C`：`call [connect]`
- `0x77587E`：`call [socket]`

这些地址和指令：VERIFIED。

## 3. 已排除的非协议路径

### 3.1 libcurl / SOCKS

- `0x602430` 是 `recv` 薄包装。
- 0x61ADA0 是接收循环，调用 `0x602430`。
- 0x61ADA0 的调用者在 0x61Bxxx，该区字符串为：
  - `SOCKS4...`
  - `SOCKS5...`
  - `Proxy CONNECT...`
  - `TUNNEL_STATE...`
- 因此 0x61Bxxx/0x61ADA0 属 libcurl 代理/连接代码，不是游戏协议分派：STATIC-INFERENCE；字符串和调用链为 VERIFIED。

### 3.2 QoS 库

- `.rdata RVA 0x89856C` 有一张 vtable，方法依次指向 `0x775870`–`0x775BB0`。
- 这些函数包装 `socket/connect/send/sendto/recv/recvfrom/ioctlsocket`。
- vtable 邻域和同区字符串包含：
  - `QOSSSPkgBody`
  - `QOSSSPkgHead`
  - `QOSCSPkg`
  - `udp://%s:%d`
  - `tqos_find_connd_by_ip fail`
  - `tqos_get_qosconnd_iplist fail`
- 因此该 vtable 属 QoS/网络质量组件，不是游戏 server-message parser：STATIC-INFERENCE；vtable 表项和字符串为 VERIFIED。

### 3.3 其他真实 recv 调用

- `0x76D65E` 是 `jmp [recv]`，但所属函数包含大量位运算/ASCII 转换，未见消息类型分派。
- `0x784F7F`、`0x788135` 是真实 recv 调用，但当前未定位其所属消息对象和上层解包循环；没有证据到 `0xA2E50`。
- 这些路径标记为 BLOCKED，不当作已排除。

## 4. 平台组件边界

主 EXE 动态引用：
- `TenProxy` 字符串 RVA `0x8BBE8C`，引用点 `0xDE295/0xDE2CB`。
- `IIPS` 字符串 RVA `0x8C0DB4`，引用点 `0x18C5E6`。
- `IIPS/iips` 另有 `.data` 指针表和 `0x246xxx` 引用。

最小审计：
- `TenProxy.dll` 仅导出 `Invoke`，导入 `PostMessageW`，是进程/窗口代理，不是包解析器。
- IIPS 目录包含 `iips.dll`、`IFS2.dll`、`Download.dll` 等下载/更新组件；其字符串与导出未显示游戏 server-message 分派。
- 因此它们是启动/平台/下载边界，不是当前 0x02 消息分派的直接证据：STATIC-INFERENCE。

## 5. 辅助 DLL

- `client_room2697.dll` SHA-256 `120c4cfdd79a9a38d992598c30af3c5cabe754e7b3d17614074b4b8026ffc3a7`，导出 `LocalRoomPump`。
- `client_native_loopback.dll` SHA-256 `53c6fbe264defc06629fef06f43a1ddd82fda716439432c354b5eb2ee4074829`，导出 `LocalMatchBegin`。
- 两者直接导入 `WS2_32` 的 `socket/connect/send/recv`，字符串显示本地 `udp:127.0.0.1:28969`、房间/挑战/重连桥接。
- 两者中未找到 `0xA2E50`、`0xA2D90` 的 VA 或 RVA 引用（`0x4A2E50`、`0xA2E50` 等均 0 命中）。

因此：
- 它们是本项目的自定义 loopback/房间桥接组件：VERIFIED。
- 它们不是原版客户端 `0xA2E50` 分派器的直接调用者：当前范围未命中，不能写成不存在。

## 6. 到 0xA2E50 的分派结论

既有多轮搜索（阶段 F 与 G2）：
1. `.text` 内无 E8/E9 目标为 VA `0x4A2E50`；
2. 全镜像无 dword VA `0x4A2E50`；
3. 无 dword 裸 RVA `0xA2E50`；
4. 未见跳转表项指向 `0x4A2E50`；
5. libcurl、QoS、平台 DLL、辅助 DLL 均未引用 `0xA2E50`；
6. 只有一条 `.tvm0` 未对齐 E8 字节命中，不能作为调用者。

**未找到内部消息类型 byte → 条件/跳转表 → RVA 0xA2E50 的完整静态控制流。** 等级：分派链 BLOCKED；已执行的搜索范围为 VERIFIED。

剩余盲区：
- 原始最后的 `.tp3` 未恢复；
- `.rdata` 指针被 `.rimp` 改写；
- 非线性代码岛（如 `0xA04860`、`0x9FA070`）不可线性追踪；
- 运行时解包/初始化的内存映射未观测；
- 可能有平台回调或运行时生成的函数指针表。
