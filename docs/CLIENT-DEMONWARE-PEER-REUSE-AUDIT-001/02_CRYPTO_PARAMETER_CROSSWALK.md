# 02 跨项目密码学参数对照表

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
