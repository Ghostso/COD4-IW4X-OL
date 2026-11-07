# 01 2697 客户端密码学调用链定位（只读静态）

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
