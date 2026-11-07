# 04 版本地址映射（含对 E-27 地址口径的更正）

## 1. 冻结样本

| 角色 | 路径 | SHA-256 | 结果 |
|---|---|---|---|
| 客户端（打包） | `CODOL.NET/Game/CODOL_2.6.9.7/codoMP_client_shipRetail.exe` | `35375404...d6e1` | MATCH（E-27） |
| 客户端（恢复镜像） | `CODOL_2697_Launcher/runtime/game/aplib-recovered/codol2697-static-candidate.bin` | `24b4ef25...97e4` | MATCH（E-27） |

打包客户端节区名为 `.tp3`（虚拟/加壳段），恢复镜像为 `.text/.rdata/.data/.tls/.rsrc/.tvm0/.rimp`。**两者节布局不同**，按段名或原始偏移直接套用必然错位。

## 2. 旧对端引用的客户端地址 -> 2697 恢复镜像核对

| 旧 VA | 旧标签 | 恢复镜像 RVA | 节区 | 首字节 | 判定 |
|---|---:|---|---|---|---|
| `0x9CE310` | bdLobbyConnection::getMessageToDispatch | `0x5CE310` | `.text` | `10 3B 3B 11 12 13...` | **非对应函数** |
| `0x9BAFD0` | reader memcpy | `0x5BAFD0` | `.text` | `8D 0C 89 3B CA 76...` | 非对应 |
| `0x9BA070` | readBlob | `0x5BA070` | `.text` | `C9 74 16 8B 45 E0...` | 非对应 |
| `0x703A00` | dwLogOnAccount_DecodeString | `0x303A00` | `.text` | `D9 45 FC D8 1D...` | 非对应 |
| `0x7039A0` | dwLogOnAccount_EncodeString | `0x3039A0` | `.text` | `10 E9 CA 00 DF E0...` | 非对应 |
| `0xA2E880` | bdBase64::decode | `0x62E880` | `.text` | `6A 0A E8 99 34 00...` | 非对应 |
| `0xA2E790` | base64 char->6bit | `0x62E790` | `.text` | `00 00 75 13 8B 46...` | 非对应 |
| `0x7C6DA60` | calculateInitialVector | `0x786DA60` | `.data` | — | 不可映射 |
| `0x711CD6` | chat log site | `0x311CD6` | `.text` | `8B 15 B0 5F 6F 02...` | 非对应 |
| `0x6FDAC4` | getChannelMembers completion | `0x2FDAC4` | `.text` | `00 00 D9 C0 DE EA...` | 非对应 |

在打包客户端中，这些 RVA 全部落在 `.tp3`（虚拟/加壳）段，原始字节为压缩/加壳数据，无法就地核对语义。

## 3. 更正：E-27 混淆了 RVA 与 VA（关键）

E-27 把 **`0x6AB310`** 记为“客户端阶段 1 应答状态机”，又把 `0x9CE310` 记为“对端引用但不成立”。本轮实测：

- 在恢复镜像中，`0x6AB310` 是 **RVA**，对应 **VA `0xAAB310`**，即本轮证实的**握手/KDF 函数本体**（`CLIENTCHAL`/`BDDATA` 的唯一调用者）。
- 若把 `0x6AB310` 当作 VA，则落在 RVA `0x2AB310`（无关代码）；若把 `0x9CE310` 当作 RVA，则对应 VA `0xA2E310`。
- 因此 E-27“旧对端地址在 2697 不成立”的结论**方向正确但口径错误**：它比较的是另一构建的 **VA** 与 2697 的 **RVA** 邻域，属于口径错位，而非“2697 缺少该函数”。

**修正后的表述**：`0x9CE310` 等旧 VA 在 2697 恢复镜像中**没有同址同义的代码**（构建差异 + 节重排），但这**不构成协议不兼容证据**；2697 客户端自身对应功能在 `0xAAB310` / `0xAAAE70` 等函数中**确实存在且已定位**。

## 4. 行为映射（旧功能 -> 2697 实现）

| 旧对端引用的功能 | 2697 恢复镜像中的实现 | 依据 |
|---|---|---|
| bdLobbyConnection 消息接收/分派 | `0x00AAC0C0` 会话泵分派器 | 0x81/0x83/0x84/0x85 四路分支 |
| bdLobbyConnection 读帧/字段 | `0x00A85AD0`（1B）、`0x00A878A0`（顺序读）、`0x00A85BE0`（4B） | 函数体 |
| bdLobby 密钥派生 | `0x00AAB310`（SHA-1 -> HMAC -> expandKey） | xref + 函数体 |
| 0x85 任务帧解密/校验 | `0x00AAAE70` | HMAC/seq 校验、解密分发 |
| 0x85 任务帧加密/组帧 | `0x00AAAA10` | AB/85/seq/iv/cipher 写入 |

## 5. 证据等级

| 项 | 等级 |
|---|---|
| 恢复镜像中旧 VA 处非对应代码 | PROVEN（逐地址字节） |
| `0x6AB310`=RVA <-> `0xAAB310`=VA 的口径更正 | PROVEN |
| 旧功能在 2697 中的行为映射 | INFERRED（强） |
| 打包客户端 `.tp3` 段内无法静态核对 | PROVEN（加壳段） |
