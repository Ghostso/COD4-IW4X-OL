# TEST_AND_VALIDATION_RESULTS

**日期：** 2026-10-13（Asia/Shanghai）  
**性质：** 离线静态验证。未启动游戏，未做 E2E。

## 1. 基线哈希

| 对象 | 结果 |
|---|---|
| 目标 EXE | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`，匹配 |
| 目标 DLL | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`，匹配 |
| 034 镜像 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`，匹配 |
| 正式源码 | 25 文件，`5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`，匹配 |

## 2. 已执行验证

### V-01 PE 映射

- 脚本：`scripts/pe_map.py`
- 输出：`evidence/pe_map.txt`
- 结果：ImageBase `0x10000000`；8 节区；常规导入仅 kernel32 + libcef；3 个导出均在 `.tvm0`。

### V-02 网络字符串归属

- 脚本：`scripts/net_strings.py`
- 输出：`evidence/net_strings.txt`
- 结果：WS2_32/WSOCK32/WSA* 字符串存在；常规导入表无这些 DLL。

### V-03 网络适配层字符串

- 脚本：`scripts/kernel_net_strings.py`
- 输出：`evidence/kernel_net_strings.txt`
- 结果：`WKNet_`、`wk_ip_config.ini`、`[KernelBind]/[KernelConnect]/[KernelDisconnect]`、`SendPacket` 存在。

### V-04 重定位

- 脚本：`scripts/tls_reloc_resources.py`
- 输出：`evidence/tls_reloc_resources.txt`
- 结果：4819 块 / 156,506 条目，类型 3 为主；优先 VA 数据指针需重定位处理。

### V-05 `.tls/.tvm0` 可分析性

- 脚本：`scripts/tls_tvm_analysis.py`
- 输出：`evidence/tls_tvm_analysis.txt`
- 结果：
  - `.text` 熵 6.994，54,10 个序言；
  - `.tls` 熵 7.532，线性反汇编前 0x2000 仅覆盖 564 字节；
  - `.tvm0` 熵 7.023，不可按普通 x86 生成调用图。

## 3. 未执行

- 未启动游戏。
- 未动态调试/注入/hook。
- 未做真实客户端 E2E。
- 未修改 FREEZE-005 或正式服务器。

## 4. 结论

离线验证支持：

- DLL 网络 API 为动态绑定；
- DLL 存在 WKNet/Kernel 网络适配层字符串；
- `.tls/.tvm0` 静态不可直接分析；
- 连接内消息入口未闭合。

离线验证不支持：

- 任何具体 netchan 格式；
- 任何具体 opcode 映射；
- 任何 gamestate/configstring/snapshot 兼容性。
