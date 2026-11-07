# -*- coding: utf-8 -*-
import os
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001"
D = lambda n: os.path.join(root, n)
docs = {}

docs["01_CLIENT_CRYPTO_XREF.md"] = r"""# 01 2697 客户端密码学调用链定位（只读静态）

> 任务：CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001
> 样本（冻结，E-27 已复核）：恢复镜像 `codol2697-static-candidate.bin`
> SHA-256 `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`
> 全程只读；未启动客户端/服务端/模拟器，未连接网络，未注入/未内存读取。

## 1. 镜像与节区（本轮重新测量）

| 项 | 值 | 证据 |
|---|---|---|
| ImageBase | `0x400000` | PE OptionalHeader |
| SizeOfImage | `0x0DC14000` | PE OptionalHeader |
| `.text` | RVA `0x1000` / VS `0x7AC28B` | PE 节表 |
| `.rdata` | RVA `0x7AE000` / VS `0x142880` | PE 节表 |
| `.data` | RVA `0x8F1000` / VS `0xD05C420` | PE 节表 |

**地址口径（全篇统一）**：`VA = RVA + 0x400000`。E-27 报告混用了 RVA 与 VA（见 04 号报告）。

## 2. 两条起始字符串

| 字符串 | VA | RVA | 节区 | 终止方式 | 原始字节 |
|---|---|---|---|---|---|
| `BDDATA` | `0x00C5B13C` | `0x0085B13C` | `.rdata` | NUL 终止 | `42 44 44 41 54 41 00` |
| `CLIENTCHAL` | `0x00C5B144` | `0x0085B144` | `.rdata` | NUL 终止 | `43 4C 49 45 4E 54 43 48 41 4C 00` |

两串相邻：实际为 `...BDDATA\0\0CLIENTCHAL\0\0`，与 E-27 记录的 VA 一致（MATCH）。
**注意**：`BDDATA` 为 **6** 字节、`CLIENTCHAL` 为 **10** 字节（E-27 正文曾按 11 字节理解，本轮更正，见 02 号报告 §2）。

## 3. 全部交叉引用（绝对立即数扫描）

扫描范围：`.text` 全节（`VA 0x401000`–`0xBAE28B`），模式 = 目标 VA 的小端 4 字节立即数。

| 字符串 | xref 数量 | 引用点 VA | 所在函数 | 指令 |
|---|---:|---|---|---|
| `CLIENTCHAL` | **1** | `0x00AAB8C5` | `0x00AAB310` | `push 0x00C5B144` |
| `BDDATA` | **1** | `0x00AAB907` | `0x00AAB310` | `push 0x00C5B13C` |

同族诊断串：

| 字符串 | VA | xref | 所在函数 |
|---|---|---|---|
| `HMAC mismatch` | `0x00C5B0EC` | `0x00AAB131` | `0x00AAB310` |
| `Bad recv counter` | `0x00C5B110` | `0x00AAAFBD` | `0x00AAAE70` |

⇒ 2697 客户端的 BDDATA/CLIENTCHAL 派生链**只有一处入口**，位于 `0x00AAB310`。

## 4. 所在函数与调用图

```text
0x00AAC0C0  会话泵 / 消息分派
  |- [+0x5CC]==1 且 marker==0x81 -> 0x00AAB310   握手/KDF（调用点 0xAAC192）
  |     0x00AAB310:
  |       - 重组 transcript 缓冲（[ebp-0x170]，容量 0xC8）
  |       - call 0x00A881B0  SHA-1(transcript) -> 20B
  |       - call 0x00AA95C0  HMAC-SHA1(key=sha1, data=sessionKey24) -> 20B secret
  |       - call 0x00AA9CE0  expandKey(secret,"CLIENTCHAL",16)  [0xAAB8CF]
  |       - call 0x00AA9CE0  expandKey(secret,"BDDATA",72)      [0xAAB911]
  |       - 切分 data，安装密钥，写 [+0x5E8] = challenge[8:16]
  |- [+0x5CC]==2 且 marker==0x83 -> 0x00AAB260
  |- [+0x5CC]==2 且 marker==0x84 -> 0x00AA9690
  \\- [+0x5CC]==3 且 marker==0x85 -> 0x00AAAE70   0x85 任务帧接收（调用点 0xAAC2F0）
```

交叉验证：`0x00AA9CE0`(expandKey) 全 `.text` 仅 **2** 个调用者（`0xAAB8CF`、`0xAAB911`）；`0x00AA95C0` 仅 **1** 个调用者（`0xAAB884`）。三条均落在 `0xAAB310` 内。

## 5. 被调用函数的行为识别（按行为，不按命名）

| 函数 | 识别依据（静态） | 结论 |
|---|---|---|
| `0x00AA9CE0` | 参数 `(secret,len,label,labelLen,out,outLen)`；循环 `prev||label||counter` -> `0xDEF310E`(HMAC_Final,20B) -> 追加；counter `inc byte [ebp-0x3D5]`；累计满足 size 后截断 | **expandKey**（HMAC-SHA1 计数器模式） |
| `0x00AA95C0` | key=`[ebp+8]` -> `0xDF6216D` 构造 HMAC-SHA1 上下文 -> `0xA88400`(HMAC_Update) -> `0xDEF310E`(HMAC_Final) 输出 20B | **HMAC-SHA1(key,data)->20B** |
| `0x00A881B0` | 名表 `0x00C4461C`（`0xACC060` 逐字节比较命中 `sha1`）-> `0xACDF00` 摘要分发 -> 输出 20B | **SHA-1->20B** |
| `0x00A87830` | `lea ecx,[dst+off+len]`，边界检查后 `0xB49B40`（`rep movsd`） | 顺序**写/追加**器 |
| `0x00A878A0` | 与上对称，`memcpy(dst, src+off, len)` 并回写 off | 顺序**读**器 |
| `0x00AA8D70` / `0x00AA8BF0` | 20B 常量 + 固定置换 + 逐字节 `XOR`；输出写 `this+0x5F9` / `this+0x60D` | **客户端内部密钥 codec（混淆层）** |

`0x00A878A0` 只支持**顺序**读取（无 seek 参数），因此调用点读取顺序即线上字段顺序。

## 6. 参数与长度来源（逐调用点）

`expandKey` 签名（由 prologue 实参使用确定）：`expandKey(secret, secretLen, label, labelLen, out, outLen)`。

| 调用点 | secret | label 指针 | labelLen | outLen | 输出用途 |
|---|---|---|---|---|---|
| `0x00AAB8CF` | `[ebp-0x4C]`（len `0x14`） | `0xC5B144` | **`0x0A`** | **`0x10`** | challenge -> `[ebp-0x38]`；取 `[ebp-0x30..-0x2C]` 写 `obj+0x5E8` |
| `0x00AAB911` | 同上（len `0x14`） | `0xC5B13C` | **`0x06`** | **`0x48`** | data[72] -> `[ebp-0xA8]` |

长度全部为**立即数常量**（`6A 0A` / `6A 06` / `6A 10` / `6A 48`）。

## 7. 证据等级

| 结论 | 等级 |
|---|---|
| 两串的节区/VA/RVA/终止方式 | PROVEN |
| 两串 xref 各 1 处，同属 `0xAAB310` | PROVEN（`.text` 全节立即数扫描） |
| `0xAA9CE0`=expandKey、`0xAA95C0`=HMAC-SHA1、`0xA881B0`=SHA-1 | PROVEN（函数体级证据） |
| 参数顺序、标签长度、输出长度 | PROVEN |
| `0xAAB310` 处于握手阶段 1（`[+0x5CC]==1`、marker `0x81`） | PROVEN（分派器 `0xAAC0C0` 调用点） |
| codec 层对最终线上密钥的影响 | **未闭合**（见 05 号报告） |
"""

docs["02_CRYPTO_PARAMETER_CROSSWALK.md"] = r"""# 02 跨项目密码学参数对照表

左侧 = **2697 恢复镜像**（本轮重新测量）；右侧 = 参考对端
`ol-mod-olfinal/src/backend/Demonware/Crypto.cpp`（C++）与
`REF_LOBBY_KIT/codol_crypto.py`（Python）。

## 1. 总表

| 比较项 | 2697 客户端（本轮实测） | 参考对端 | 判定 |
|---|---|---|---|
| Transcript 组成 | 顺序追加 `clientHeader[8:28]` + `AB 81` + `clientAuth[:-8]`（`0xA87830` 为纯追加器） | `hello28[8:28] ++ serverAck26 ++ clientAuth[:-8]`（`codol_crypto.py:692-694`；`LobbyProtocol.cpp:335-338`） | **结构一致** |
| Hash | **SHA-1**（`0xA881B0`，名表项 `0x00C4461C` = `sha1`） | `sha1()` | **一致** |
| Secret | `HMAC-SHA1(key = SHA1(transcript), data = sessionKey24)`（`0xAA95C0`，`0xAAB884` push `0x18`) | `hmacSha1(sessionKey, transcriptHash)` 等价 key=transcriptHash, data=sessionKey（`Crypto.cpp:205`） | **一致** |
| Session key 长度 | 24（`push 0x18`） | 24（`!= 24` 抛错） | **一致** |
| `CLIENTCHAL` 标签 | `43 4C 49 45 4E 54 43 48 41 4C`，**len=0x0A** | `"CLIENTCHAL"`（10B） | **一致**（E-27 正文按 11B 理解处已更正） |
| `BDDATA` 标签 | `42 44 44 41 54 41`，**len=0x06** | `"BDDATA"`（6B） | **一致** |
| `CLIENTCHAL` 输出 | 16B（`push 0x10`） | 16B | **一致** |
| `BDDATA` 输出 | 72B（`push 0x48`） | 72B | **一致** |
| `expandKey` | 计数器模式 HMAC-SHA1：`prev||label||counter`，counter 自 1 递增，拼接后截断（`0xAA9CE0`） | `prev = hmacSha1(secret, prev+label+counter)`（`Crypto.cpp:153-173`） | **一致** |
| 密钥切分 | challenge[**8:16**] -> `obj+0x5E8`；`0xAA8D70(&data[0])`、`0xAA8BF0(&data[20])` -> `data[0:20]/[20:40]/[40:56]/[56:72]` | `responseId=challenge[8:16]`；`requestHmac[0:20]/responseHmac[20:40]/decrypt[40:56]/encrypt[56:72]` | **一致（20/20/16/16）** |
| 客户端附加层 | **`0xAA8D70`/`0xAA8BF0` 对 20B/16B 派生值做常量 XOR + 固定置换**，紧接在 expandKey 之后 | **无对应实现** | **差异（见 05 号报告）** |

## 2. 两处易错点的明确说明

1. **E-27 正文把 `CLIENTCHAL` 当作 11 字节**。字面实为 10 字节，2697 客户端 `push 0x0A` 与之吻合，参考 `"CLIENTCHAL"` 亦为 10 字节。此处**无差异**。
2. **同一字符串可同时被“派生输入”与“错误文本”引用，但本轮 xref 扫描显示 `CLIENTCHAL` 在 `.text` 中仅 1 处立即数引用**，即派生点 `0xAAB8C5`。历史手工分析曾据“错误消息表”否定其派生用途，本轮以调用点数据流（`push 0xC5B144` + `push 0x0A` 进入 `expandKey`）予以更正。

## 3. 证据等级

| 项 | 等级 |
|---|---|
| Hash=SHA-1、HMAC-SHA1、secret 输入/输出长度 | PROVEN |
| 标签字面与长度（6 / 10） | PROVEN |
| expandKey 计数器语义 | PROVEN（循环体级） |
| 切分 20/20/16/16 与 challenge[8:16] | PROVEN |
| transcript 字段顺序 | INFERRED（强） |
| 客户端 codec 层对线上密钥的影响 | BLOCKED |
"""

docs["03_FRAME_AND_STATE_MACHINE_COMPARISON.md"] = r"""# 03 帧格式与握手状态机对照

## 1. 帧布局

参考对端（`codol_crypto.py:697-725`、`_ref/CodolLocalLobbyServer.cs:503-535`、`LobbyProtocol.cpp:190-205`、`215-220`）：

```text
u32 len(= 整帧长度 - 4) | 0xAB | 0x85 | u32 seq | iv[16] | AES-128-CBC ciphertext | HMAC-SHA1[:8]
                                              ^10            ^26                        ^-8
```

2697 客户端出站帧头组装（`0x00AAAA10`，仅当 `[+0xC8]==2` 且 `[+0x5CC]==3`）：

| 偏移 | 写入 | 指令/位置 |
|---|---|---|
| +0x00 | `u32` | `0xA87830`（4B） |
| +0x04 | `0xAB` | `mov byte [ebp-0x1F1],0xAB` @`0xAAAB06` |
| +0x05 | `0x85` | `mov byte [ebp-0x1F1],0x85` @`0xAAAB33` |
| +0x06 | `u32 seq` | 源自 `[edi+0x5D4]`（`0xAAAB4C`） |
| +0x0A | `iv[16]` | `0xAAAB97` push `0x10` + RNG（`0x48EDA4`/`0xDF013AB`） |
| +0x1E | 密文 | `0xAAAA9A lea edi,[ebx+0x1E]`，`ebx = (len+0x14) & 0xFFFFFFF0` |

明文长度对齐：`lea ebx,[len+0x14]; and ebx,0xFFFFFFF0`（`0xAAAA84-0xAAAA87`）；参考 `n=(5+len(inner)+15)//16*16`。
**AES-128-CBC，无填充（PaddingMode.None），仅按 16B 对齐**。

## 2. MAC（完整性）

| 项 | 2697 客户端 | 参考对端 | 判定 |
|---|---|---|---|
| 算法 | HMAC-SHA1 | HMAC-SHA1 | 一致 |
| 覆盖范围 | `frame[0 : total-8]`（`0xAAAF58` 起；`0xAAAFBA` 起以 `[0:total-8]` 作 HMAC 输入） | `frame[:-8]` | **一致** |
| 截断 | **前 8 字节**（`0xAAB0E6–0xAAB12B` 对 8 字节做 XOR/OR 归并比较） | `signature[:8]` | **一致** |
| 失败路径 | `HMAC mismatch`（`0xC5B0EC` @`0xAAB131`） | 抛 `lobby frame HMAC mismatch` | 语义一致 |
| 方向键 | 入站 `[edi+0x5F4]`（`0xAAB046 call 0xAA8BF0`） | `keys_.requestHmac` | **一致** |

## 3. 序列号

- 2697 客户端：`recvCounter = [edi+0x5D0]`（`0xAAAFA4`），`lea edx,[eax+1]` 后回写（`0xAAAFAD`）；`cmp [ebp-0x224], eax` 不等 -> `0xAAAFBD` 引用 `"Bad recv counter"`。
  其中 `[ebp-0x224]` 由**帧头 seq 字段** 4B 读入（`0xAAAEE0`–`0xAAAF00`）。
- **判定一致**：接收序列号必须**精确等于**当前期望值，然后 +1（严格递增，无窗口）。

## 4. 握手消息码与阶段

2697 客户端分派器 `0x00AAC0C0`（`[+0x5CC]` 阶段 + 帧头 marker 二级分派）：

| 阶段 `[+0x5CC]` | marker | 目标函数 | 语义 |
|---:|---|---|---|
| 1 | `0x81` | `0x00AAB310` | 服务端 0x81 应答 -> 组 transcript、派生密钥 |
| 1 | 其他 | 错误路径 | 非预期 |
| 2 | `0x83` | `0x00AAB260` | 写 `[edi+0x620..0x624]`（`0xAAC21C`–`0xAAC22C`） |
| 2 | `0x84` | `0x00AA9690` | 分支 |
| 3 | `0x85` | `0x00AAAE70` | 任务帧接收 |
| 3 | `0x84` | `0x00AA9690` | 分支 |

参考对端阶段机（`LobbyProtocol.cpp`）：`clientHeader -> clientAuth -> established`，opcode `0x81`(ServerHeaderAck) / `0x82`(client auth) / `0x83`(responseId) / `0x85`(task)。
客户端阶段推进写入点：`0xAABB01 mov dword [edi+0x5CC],2`（0x83 之后）。

**判定**：消息码集合 `{0x81,0x82,0x83,0x84,0x85}` 与阶段推进顺序同构；`0x83` 携带 `challenge[8:16]` 与参考 `keys_.responseId` **一致**。

## 5. 证据等级

| 项 | 等级 |
|---|---|
| `u32 len｜AB｜85｜u32 seq｜iv16｜AES-128-CBC｜HMAC-SHA1[:8]` | PROVEN（两端独立函数体） |
| MAC 覆盖 `frame[:-8]`，取前 8B | PROVEN |
| 严格递增接收计数器 | PROVEN |
| 消息码集合与阶段顺序 | INFERRED（强）；`0x81 -> 0xAAB310`、`0x85 -> 0xAAAE70`、`[+0x5CC]=2` 为 PROVEN |
| AES provider / IV 生成细节 | PROVEN（RNG `0x48EDA4`/`0xDF013AB`，IV 16B 前置） |
"""

docs["04_VERSION_ADDRESS_MAPPING.md"] = r"""# 04 版本地址映射（含对 E-27 地址口径的更正）

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
"""

for name, text in docs.items():
    with open(D(name), "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", name, len(text))
