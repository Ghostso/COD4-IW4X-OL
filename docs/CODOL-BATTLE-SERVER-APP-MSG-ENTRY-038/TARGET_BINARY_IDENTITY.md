# TARGET_BINARY_IDENTITY — 目标模块身份与地址约定

## 1. 指纹

| 对象 | 路径 | 大小 | SHA256 | 判定 |
|---|---|---:|---|---|
| 目标 EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | 与固定基线一致 |
| 目标主 DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | 与固定基线一致 |
| 034 运行时镜像 | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 10,899,456 | `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045` | 与 034 一致 |
| 正式源码 | `CODOL-Combat-Server-v0.1\src\**\*.cs` | 25 文件 | `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf` | 与 FREEZE-005 一致 |

**判定：** 指纹全部匹配，可以继续使用旧地址作为“调查起点”，但每条地址都必须重新归属模块。

---

## 2. PE 与节区

### 2.1 `codoMP_client_shipRetail.exe` 与 `image_best.bin`

两者完全同源：

| 项 | EXE | image_best.bin |
|---|---|---|
| ImageBase | `0x400000` | `0x400000` |
| TimeDateStamp | `0x6096930A` | `0x6096930A` |
| SizeOfImage | `0x0E659000` | `0x0E659000` |
| EntryPoint | `0xE5DC690` | `0xE5DC690` |
| 节区 | `.tp3`×6 + `.tvm0` | `.tp3`×7（运行时视图） |

`image_best.bin` 的第 3 节区起 `.tp3` 的原始数据被扩展填充，因此：
- 低 RVA（如 `0x5F830`、`0x1FF820`、`0x208380`、`0x6D060`）可以直接用 `file_offset = RVA`。
- 该等式**不能**外推到整个映像；高 RVA 区域需要按节区映射。
- `0xE5D3000` 在 EXE 中是 `.tvm0`，在 `image_best.bin` 中被标为 `.tp3` 且出现重复/扩展原始数据。

### 2.2 `codoMP_client_shipRetailBase.dll`

| 项 | 值 |
|---|---|
| ImageBase | `0x10000000` |
| TimeDateStamp | `0x5E551315` |
| SizeOfImage | `0x3991000` |
| 节区 | `.text .rdata .data .idata2 .rsrc2 .tls .tvm0 .reloc` |
| `.text` | VA `0x1000`，VSize `0x742000` |
| `.tls` | VA `0xB0A000`，VSize `0xED3000` |
| `.tvm0` | VA `0x19DD000`，VSize `0x1F5E000` |

**关键判定：** 主 DLL 不是 EXE 的附属数据，而是独立引擎模块。EXE 镜像中的 RVA 不能映射到 DLL；DLL 的地址必须使用 `ImageBase=0x10000000` 换算。

---

## 3. 字符串归属

在 EXE 镜像中：

| 字符串 | 存在 | 图像偏移 |
|---|---|---|
| `gamestateupdate` | 是 | `0x9B4700` |
| `challengeResponse` | 是 | `0x9B762E`、`0x9BFEE8` |
| `connectResponse` | 是 | `0x9BFF0C` |
| `configstring` | 是 | `0x9B46CC`、`0x9B46E8` |
| `heartbeat` | 是 | `0x9BFE40` |
| `getchallenge` | 是 | `0x9BFD04` |
| `cancelConnect` | 是 | `0x9BFC8C` |

在主 DLL 中：

| 字符串 | 存在 |
|---|---|
| `opcode` | 是，但属于 Lua/调试/描述符字符串，不是协议 opcode 表 |
| `netchan` | 否 |
| `gamestate` | 否 |
| `configstring` | 否 |
| `parseServerMessage` | 否 |

**判定：** 明文关键字不能用来判定协议入口归属；EXE 中的 OOB 字面量只证明该模块包含 OOB 相关代码，不能把同区所有函数都称为消息解析器。
