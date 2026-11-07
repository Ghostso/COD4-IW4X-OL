# G1 — 客户端恢复镜像有效性审计

> 2026-10-12 · 仅静态分析。未启动游戏/服务端，未注入、补丁、编译或修改样本。
> 样本哈希：
> - 原始客户端 `codoMP_client_shipRetail.exe`：`353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`
> - 静态恢复镜像 `codol2697-static-candidate.bin`：`24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`

## 1. 身份与生成链

| 项目 | 结果 | 等级 |
|---|---|---|
| manifest 版本 | `2.6.9.7`；`original_exe_sha256` 与原始客户端一致 | VERIFIED |
| 原始客户端路径 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | VERIFIED |
| 原始客户端 SHA-256 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | VERIFIED |
| 恢复镜像路径 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | VERIFIED |
| 恢复镜像 SHA-256 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | VERIFIED |
| 生成脚本/构建元数据 | 未在 Launcher、分析目录或恢复目录中找到独立的 aplib 解包/重建脚本；恢复目录只有候选 bin 本身 | BLOCKED |

恢复目录内没有 README、日志、映射表或原始解包器；消费端脚本（`restricted_candidate_probe.py`、`server2697/local_candidate_probe.py`、`run_native_connection.py`）只读取候选 bin。因此“如何生成”不能由现有文件证明，只能审计产物结构。

## 2. 地址基准

- 恢复镜像 ImageBase：`0x400000`。
- `0xA2E50`、`0xA2D90` 是**映像 RVA**，对应 VA `0x4A2E50`、`0x4A2D90`。
- E8/E9 rel32 的目标是**绝对 VA**；从目标还原 RVA 必须减去 ImageBase，例如：
  - `0xA2E87` 的调用目标 `0x5AC1D0` 是 VA，对应 RVA `0x1AC1D0`。
  - `0xA2F02` 的调用目标 `0x5ACB00` 是 VA，对应 RVA `0x1ACB00`。
- 该基准在 G1/G2 全部分析中固定使用：VERIFIED。

## 3. 节区结构与覆盖

原始 EXE 与恢复镜像具有相同的 ImageBase 和 7 个虚拟地址区间，但节名与内容来源不同：

| VA | 原始节 | 原始 VSZ/RAW | 恢复节 | 恢复 VSZ/RAW | 字节一致性 | 等级 |
|---|---|---|---|---|---|---|
| `0x1000` | `.tp3` | `0x7AC90B / 0x394400` | `.text` | `0x7AC90B / 0x7ACA00` | 等长重叠区仅 0.448% 相同；恢复侧已展开到完整 VSZ | VERIFIED |
| `0x7AE000` | `.tp3` | `0x142880 / 0x142A00` | `.rdata` | `0x142880 / 0x142A00` | 99.884% 相同；1536 字节不同，集中为指针/表项改写 | VERIFIED |
| `0x8F1000` | `.tp3` | `0xD05C420 / 0x49600` | `.data` | `0xD05C420 / 0x49600` | 100% 相同 | VERIFIED |
| `0xD94E000` | `.tp3` | `0x19 / 0x200` | `.tls` | `0x19 / 0x200` | 100% 相同 | VERIFIED |
| `0xD94F000` | `.tp3` | `0x8DF8 / 0x8E00` | `.rsrc` | `0x8DF8 / 0x8E00` | 100% 相同 | VERIFIED |
| `0xD958000` | `.tvm0` | `0x2B9000 / 0x110600` | `.tvm0` | `0x2B9000 / 0x2B8C00` | 重叠区仅 0.420% 相同；恢复侧已展开 | VERIFIED |
| `0xDC11000` | `.tp3` | `0x3214000 / 0x336800` | `.rimp` | `0x2964 / 0x2A00` | 仅 0.884%；恢复侧极小 | VERIFIED |

### 3.1 明确的覆盖缺口

原始最后一段 `.tp3`：

- VA `0xDC11000`
- VSZ `0x3214000`
- RAW `0x336800`
- 熵约 `7.8837`
- 首字节不是 MZ/PE，高熵且无可读协议字符串

恢复镜像同址只有 `.rimp`（VSZ `0x2964`）。它与原始最后段相差约 `0x321169C` 虚拟字节，且整个恢复镜像 `SizeOfImage=0xDC14000`，比原始 `0x10E25000` 小 `0x3211000`。

**结论：恢复镜像没有覆盖原始 EXE 的最后大量高熵保护区域。该区域是否包含运行时分派、VM 状态或其他代码，当前无法确定。** 等级：覆盖差异 VERIFIED；内容语义 BLOCKED。

## 4. `.rimp` 是恢复伪影，不是原始游戏代码

`.rimp` 的原始字节缺少正常函数序言，也没有 `FF25`、`E9`、`C3` 形式的跳板/返回模式。解析为 dword 后呈记录/指针表结构，例如：

```text
0DC1126C 00000000 00000000 0DC11168
007AE000 0DC112C4 00000000 00000000
0DC112A4 007AE038 0DC11478 ...
```

大量值落在：

- 原始/恢复 `.rdata` 区间 `0x7AE000–0x8F1000`
- `.rimp` 自身区间 `0xDC11000–0xDC13964`
- 其他恢复镜像地址区间

同时，原始与恢复 `.rdata` 的 1536 字节差异正是连续指针数组/表项被改写，恢复后指向 `0xDC11xxx–0xDC13xxx`。

**最合理解释：恢复工具在 `.rdata` 中把一批指针/表项改写为指向 `.rimp`，用 `.rimp` 保存旧的指针/修复记录。** 该解释为 STATIC-INFERENCE；指针改写和表结构为 VERIFIED。

这直接限制负面搜索：
- 针对 `0xA2E50` 的“全镜像无 xref”可能受指针表被改写影响；
- vtable/函数指针表不再等同于原始运行时布局；
- 不能把恢复镜像中的 xref 缺失直接升级为原始客户端不存在。

## 5. 代码可解码性

- `.text` RAW `0x7ACA00`、VSZ `0x7AC90B`，已覆盖完整虚拟空间及文件对齐 padding。
- `.text` 中零字节约 9.16%，`0xCC` 约 3.61%；有最长 `0xF5` 的零填充和 `0xDD` 的 int3 填充，但未发现大段全零占位整个函数区。
- `.tvm0` RAW `0x2B8C00`、VSZ `0x2B9000`，也覆盖完整虚拟空间。
- 但正常代码会直接调用非正常序言目标，例如：
  - `0x61ADA0` 调用 `0xA04860`
  - `0x61B597` 调用 `0x9FA070`
  - 这两个目标在 `.text` 内，字节流无法按普通 x86 函数线性解释。

**结论：文件尺寸覆盖并不等于可追踪覆盖。存在未解释的非线性/受保护代码岛。** 字节与直接调用：VERIFIED；虚拟化/保护解释：STATIC-INFERENCE。

## 6. 与原始样本的函数字节对应

- `0xA2E50`、`0xA2D90`、读取核心字节序列在原始 EXE 原始节区中找不到，符合“恢复侧是解包/展开后的代码”。
- `.rdata` 99.884% 相同、`.data/.tls/.rsrc` 100% 相同，说明恢复不是任意伪造文件。
- 但 `.text/.tvm0` 是重写/展开后的内容，且 `.rdata` 指针被修复；不能仅凭高一致率证明其与运行时映射逐字节等价。

## 7. G1 判定

**当前恢复镜像可以支持“候选镜像内部未找到”的表述，但不能支持“原始客户端运行时绝对不存在”的结论。**

主要限制：
1. 缺少原始最后的 `.tp3` 高熵保护区。
2. `.rdata` 指针/表项被 `.rimp` 修复，可能与运行时布局不同。
3. 存在非线性代码岛。
4. 没有生成脚本、dump 日志或运行时映射对照。
