# 03 帧格式与握手状态机对照

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
| +0x1A | 密文 | 头部顺序写入 len(4)/AB/85/seq(4)/iv(16) 后，偏移自然为 26 = `0x1A` |

明文长度对齐：`lea ebx,[len+0x14]; and ebx,0xFFFFFFF0`（`0xAAAA84-0xAAAA87`），`ebx` 即 16B 对齐后的密文长度；随后 `lea edi,[ebx+0x1E]`、`lea eax,[edi+4]`（`0xAAAA9A-0xAAAA9D`）得到 `len 字段值 = ct+30`、`总帧长 = ct+34`，与 `26 头 + ct + 8 tag` 一致。参考实现 `n=(5+len(inner)+15)//16*16`。
**AES-128-CBC，无填充（PaddingMode.None），仅按 16B 对齐**。

## 2. MAC（完整性）

| 项 | 2697 客户端 | 参考对端 | 判定 |
|---|---|---|---|
| 算法 | HMAC-SHA1 | HMAC-SHA1 | 一致 |
| 覆盖范围 | 除末尾 8B tag 外的整帧：tag 取自 `base+len-8`（`0xAAAF58`-`0xAAAF6C`）；HMAC_Update 长度 = `[edi+0xAC]-4`（`0xAAB07A`），按长度字段口径即 `total-8` | `frame[:-8]` | **一致** |
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
