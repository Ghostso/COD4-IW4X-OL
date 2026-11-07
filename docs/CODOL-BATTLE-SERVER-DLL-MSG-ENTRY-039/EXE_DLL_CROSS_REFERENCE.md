# EXE_DLL_CROSS_REFERENCE — 与 038 EXE 证据交叉核验

## 1. 已确认的模块分工

| 模块 | SHA256 | ImageBase | 主要代码区 | 038 关系 |
|---|---|---|---|---|
| `codoMP_client_shipRetail.exe` / `image_best.bin` | `3699…b537` / `17ce…f045` | `0x400000` | `.tp3` | OOB、状态、delta 字段类型分派 |
| `codoMP_client_shipRetailBase.dll` | `ef75…6a20` | `0x10000000` | `.text/.tls/.tvm0` | 引擎主体、网络适配层字符串、VM 导出 |

**判定（CONFIRMED_DIRECT）：** 两者是不同模块，地址约定不同。EXE 的 `file_offset = RVA` 不能用于 DLL。

## 2. 交叉引用可能性

| 项 | 结论 | 证据 |
|---|---|---|
| EXE 直接调用 DLL 导出 | 可能，但导出位于 `.tvm0`，未在 EXE 中找到直接对应 | `evidence/pe_map.txt` |
| DLL 导入 EXE | 未发现 | 导入仅有 kernel32/libcef |
| 共享字符串 | `gamestateupdate`、`challengeResponse` 仅在 EXE | `evidence/net_strings.txt` |
| DLL 网络关键字 | `WS2_32`、`WKNet_`、`KernelBind` 仅在 DLL | `evidence/net_strings.txt` |
| 两侧网络路径关联 | 未能建立 | 无明确接口/回调证据 |

## 3. 038 修正的继承

- EXE `0x5F830` 是 delta 字段类型分派，不是应用层入口。
- EXE `0x2000A0` 是客户端对象状态/动画更新器。
- EXE 1,279 个间接跳转候选中没有可绑定 netchan 的应用层 opcode。
- 旧版 OLFinal RVA 不适用于目标二进制。

## 4. 结论

DLL 中的网络适配层（`WKNet_`/`Kernel*`）与 EXE 中的 OOB/状态代码之间**尚未发现直接接口**。任何关联都必须等待具体导出调用或回调证据，不能仅凭都含网络相关字符串推断。
