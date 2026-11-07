# CODOL G3 帧验证差异报告（001）

> 任务：`CODOL-KEYFLOW-G3-FRAME-VALIDATION-001`
> 范围：基于冻结的 CODOL 2.6.9.7 证据，离线执行 TC-16…TC-32。
> 执行性质：仅本地参考实现、独立原语和离线测试夹具；未启动游戏/服务端，未注入，未联网，未修改正式二进制。
> 实时互通：**NOT-OBSERVED（不变）**。

## 1. 输入基线与执行环境

| 项 | 值 |
|---|---|
| 打包客户端 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` |
| 打包客户端 SHA-256 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`（复算一致） |
| 恢复镜像 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` |
| 恢复镜像 SHA-256 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`（复算一致） |
| G2 独立实现目录清单 | `CODOL-KEYFLOW-INDEPENDENT-VERIFY-001/SHA256SUMS_KEYFLOW_INDEPENDENT_001.txt`：11/11 通过 |
| 规范来源目录清单 | `CODOL-KEYFLOW-SPEC-PROVENANCE-001/SHA256SUMS_SPEC_PROVENANCE_001.txt`：6/6 通过 |
| 运行时验证方案清单 | `CODOL-DEMONWARE-RUNTIME-VALIDATION-001/SHA256SUMS_RUNTIME_VALIDATION_001.txt`：5/5 通过 |
| 本任务输入矩阵 | `CODOL_KEYFLOW_TEST_MATRIX_001.csv`，SHA-256 `1fb1528e58ed1e3de23ed68d3668556b9e8c6869924ea7020421dc6995cde630` |
| 执行环境 | Windows；Python 3.11.9；自写 SHA-1/HMAC/AES、`hashlib/hmac`、PyCryptodome 3.23.0 |

复算脚本与原始逐用例日志：

- `_tools/g3_frame_harness.py`
- `_data/g3_execution_log.json`

## 2. 用例结果总览

| 状态 | 数量 |
|---|---:|
| PASS | 16 |
| FAIL | 0 |
| BLOCKED-MISSING-ORACLE | 0 |
| BLOCKED-INSUFFICIENT-SPEC | 1 |
| NOT-EXECUTED | 0 |
| 合计 | 17 |

逐用例结果见 `CODOL_G3_FRAME_TEST_RESULTS_001.csv`。

**关键的强度限制**：16 个 PASS 不是“原始服务端兼容性”结论。其中 TC-18、TC-23、TC-28、TC-30 属于项目参考/本地夹具行为；TC-24…TC-26 是依据冻结客户端反汇编建立的严格序列号模型的内部一致性测试；TC-27 仍为规范不足阻塞。

## 3. 帧结构（TC-16…TC-18）

### 3.1 固定布局

在所有固定向量和两条抓包回放上验证：

```text
offset 0   : u32 little-endian len = total_frame_length - 4
offset 4   : 0xAB
offset 5   : 0x85
offset 6   : u32 little-endian sequence
offset 10  : IV[16]
offset 26  : AES-128-CBC ciphertext
last 8     : HMAC-SHA1(key, frame[:-8])[:8]
```

- `len` 覆盖范围：整帧长度减 4，即 `len + 4 == frame_len`。
- 密文长度：非空且为 16 字节倍数。
- 0x86 帧明文：`u32 declared | messageType(0x86) | payload | zero alignment`。
- 最小合法 0x85/0x86 帧：空 payload 时密文至少 1 个 16B 分组，总长 **50B**（而不是 34B 的纯头部长度）。

### 3.2 抓包回放

| 帧 | 长度字段 | 总长 | seq | 重编码结果 |
|---|---:|---:|---:|---|
| `DemonwareTests.cpp:2511-2515` request | `0x0000009e` = 158 | 162 | 1 | 与原始逐字节相同 |
| `DemonwareTests.cpp:2521-2523` response | `0x0000003e` = 62 | 66 | 0x16 | 与原始逐字节相同 |

项目参考 `REF_LOBBY_KIT/codol_crypto.py` 对两条抓包帧的 HMAC、序号和明文与本地夹具一致；该一致性仍属于同项目谱系，不是独立协议规范。

## 4. MAC 差异与覆盖边界（TC-19…TC-23）

### 4.1 覆盖范围

- 正确覆盖：`frame[:-8]`。
- 标签截取：HMAC-SHA1 输出的前 8 字节。
- `frame[:-9]`、完整 `frame`（包含 tag）均不匹配原帧 tag。

### 4.2 标签篡改与覆盖字段篡改

| 输入 | HMAC 结果 | 完整解码结果 | 说明 |
|---|---|---|---|
| 正确 tag | pass | accept | 正对照 |
| 翻转 tag 字节 | fail | reject | 不重算 tag |
| 翻转 frame 覆盖字段但不重算 tag | fail | reject | tag 不能覆盖篡改 |
| 重算 tag 后翻转 `0xAB` | pass | reject | 在结构检查 `marker` 处拒绝 |
| 重算 tag 后翻转 seq | pass | accept | 返回被修改的 seq，证明 seq 在 MAC 覆盖内 |
| 重算 tag 后翻转 IV | pass | accept（本固定向量） | MAC 通过，但完整帧的语义正确性不由 MAC 单独保证 |
| 重算 tag 后翻转密文 | pass | reject（`declared`） | 解密后长度语义失败 |

这一区分很重要：**MAC 验证通过不等于完整帧语义有效**；同时，本地夹具的看起来“接受”不能外推为原版客户端行为。

### 4.3 标签长度边界

| tag 长度 | 本地夹具行为 |
|---|---|
| 8B | accept |
| 9B | reject（覆盖范围随长度改变） |
| 20B（完整 HMAC-SHA1） | reject（协议字段只接受前 8B） |
| 0/1/4/7B | reject（短帧/短 tag） |

## 5. 序列号差异与模型边界（TC-24…TC-27）

冻结客户端反汇编在 `0xAAAFA4`–`0xAAAFB3` 给出：接收计数器期望值必须精确等于本帧 seq，随后回写 `expected+1`；不等时引用 `Bad recv counter`。

| 用例 | 冻结客户端语义 | 本地结果 | 判定 |
|---|---|---|---|
| TC-24 正常递增 | accept | 严格相等模型 accept，expected 前进 | PASS |
| TC-25 重复 | reject | 严格相等模型 reject，expected 不变 | PASS（模型级） |
| TC-26 跳号 | reject | 严格相等模型 reject，expected 不变 | PASS（模型级） |
| TC-27 回绕 `0xFFFFFFFF -> 0` | 未闭合 | 严格模型会 reject；模 2^32 候选会 accept | **BLOCKED-INSUFFICIENT-SPEC** |

**结构性限制**：已检查的现有服务端参考实现（`LobbyProtocol.cpp`、REF_LOBBY_KIT 路径）没有实现客户端方向的 recv counter 检查。因此 TC-25/TC-26 只能证明“严格相等模型符合冻结反汇编”，不能证明某个现有服务端参考实现已实现相同接收策略，更不能证明真实运行时会断开还是丢弃。

## 6. 长度与异常输入差异（TC-28…TC-32）

### 6.1 keepalive

- `parse_frames(b'\x00\x00\x00\x00')` 消耗 4B，分类为 keepalive，余量为 0。
- 后续正常帧可继续被拆分。该行为来自本地参考解析器，未归因于原版客户端。

### 6.2 长度上限

| 声明长度 | 本地 parser | 冻结客户端静态上限 | 备注 |
|---:|---|---|---|
| `0x00100001` | reject，恢复余量 | `< 0xFFFFFF` 内，静态上限不拒绝 | 本地参考实现的上限 **0x100000** 更小，构成实现差异 |
| `0x00FFFFFF` | reject | reject（静态使用 `cmp ...,0xffffff` / `jge`） | 与声明边界一致 |
| `0xFFFFFFFF` | reject | reject | 超界 |

因此 TC-29 对矩阵要求的 `0xFFFFFFFF` 通过，但同时记录了一个未被测试矩阵要求解决的参考实现差异：**本地参考 parser 的 1MiB 上限与冻结客户端约 16MiB 上限不同**。

### 6.3 声明长度与实际缓冲区不一致

- 声明大于实际：本地 parser 不消费，保留余量；直接解码拒绝。
- 声明小于实际：本地 parser 切出较短的候选帧，余量保留；候选帧因 `len+4 != frame_len` 被拒绝。
- 未观察到越界读写或状态污染。

### 6.4 密文对齐和短帧

- `ct_len = 0, 1, 15`：在本地夹具 `min-total-50` 阶段拒绝。
- `ct_len = 17`：在 `ct-align` 阶段拒绝。
- 总长 0…49B：直接解码全部拒绝。
- 总长 50B 的空 payload 0x86 帧：accept。

## 7. 未决/限制清单

| # | 项 | 影响 | 所需证据 |
|---|---|---|---|
| D-1 | `0xFFFFFFFF -> 0` 回绕语义未闭合 | TC-27 blocked | 同构建运行时样本或更完整的客户端执行证据 |
| D-2 | 本地参考上限 0x100000 与客户端 0xFFFFFF 不同 | 不能把本地 parser 上限当作客户端上限 | 同构建长度边界实测或进一步反汇编/调用链 |
| D-3 | 现有服务端参考无客户端 recv counter | 重复/跳号只能作模型级内部一致性 | 客户端侧接收状态机实现或运行时样本 |
| D-4 | 本地夹具拒绝异常帧，但原版客户端“断开/丢弃/幂等”未定 | 不能把异常测试结果外推为原版行为 | 运行时故障注入记录或完整控制流证据 |
| D-5 | TC-18 抓包向量与原参考同谱系 | 只能作回归一致性，不是独立协议 oracle | 独立构建/原始服务端样本 |

## 8. 结论

本地夹具在固定帧结构、HMAC 覆盖、8B tag 截取、基础长度拒绝和严格序列号模型上无逐字节差异；但 G3 仍不能无保留通过：

- 1 个必需用例因回绕语义不足而 blocked；
- 序列号重放/跳号只有模型级证据；
- 参考实现长度上限存在结构差异；
- 原版客户端失败处置没有运行时证据；
- TC-18 向量不是独立 oracle。

实时互操作仍为 **NOT-OBSERVED**；本任务不构成 G4/G5 证据。