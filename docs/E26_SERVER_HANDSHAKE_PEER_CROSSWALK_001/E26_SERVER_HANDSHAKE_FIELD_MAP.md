# E26 服务端握手字段与标签

## 1. `CLIENTCHAL` / `BDDATA` 定向检查结论

对三个服务端侧样本做精确字节扫描：

| 样本 | `CLIENTCHAL` | `BDDATA` | `HMAC mismatch` | `Bad recv counter` | `Bad frame/payload size` |
|---|---|---|---|---|---|
| `codol_dedrun.exe` | **0** | **0** | **0** | **0** | **0** |
| `client_room2697.dll` | **0** | **0** | **0** | **0** | **0** |
| `client_native_loopback.dll` | **0** | **0** | **0** | **0** | **0** |

对照客户端恢复镜像：`CLIENTCHAL`=1、`BDDATA`=1（均存在）。

**裁定**：服务端侧**不存在** `CLIENTCHAL`/`BDDATA` 字样（在所述样本范围内）。按任务书 §B，这**不直接等于协议不兼容**——须继续检查等价字节结构（见 §4）。**PROVEN（缺席）／语义 BLOCKED。**

## 2. 服务端实际存在的握手族：iD-Tech challenge/response

| 函数 | RVA | 关键指令与常量 |
|---|---|---|
| `_CODOL_HandshakeInit` | `0x0982A3` | `cmp byte [arg],1`；`cmp byte [arg+1],2`；`[+2..3]==0`；`[+4..5]==0`；`[+6..7]!=0`；`[+8..15]` 与 cookie 做 XOR 比较 |
| `_CODOL_HandshakeCookie` | `0x09857B` | `cmp [ebp+0x14],0xBD`（长度必须 = 0xBD）；与 `[obj+0x106]` 做 `memcmp`；成功则从 `[obj+0x1C3]` 起拷出 0x40 字节 |
| `_CODOL_WriteChallengeResponse` | `0x097592` | `push "challengeResponse %d"(VA 0x7BCCCA)`；`push 0x40`；`call 0x757270`；再 `call 0x4971C5` |
| `0x4971C5` | `0x4971C5` | 后续响应包装（供 `0x6DD83 call 0x430E80` 发送） |
| `_CODOL_HandshakeClear` | `0x09828D` | 清零 0x240 字节 |

`_CODOL_HandshakeInit` 的 16 字节输入布局（PROVEN，指令级）：

| 偏移 | 期望 | 指令 |
|---|---|---|
| +0 | `0x01` | `0x9830D cmp byte [eax],1` |
| +1 | `0x02` | `0x98316 cmp byte [eax+1],2` |
| +2..+3 | `0x0000` | `0x98320..0x98331` |
| +4..+5 | `0x0000` | `0x98337..0x98345` |
| +6..+7 | `≠ 0` | `0x9834B..0x98359`（16 位非零） |
| +8..+15 | 8 字节 cookie，与 `[arg3]` XOR 后须为 0 | `0x9835F..0x98377` |

## 3. `challengeResponse` 两侧共享（PROVEN）

| 侧 | 字符串 VA | 代码引用 | 说明 |
|---|---|---|---|
| 服务端 | `0x7BCCCA` | `0x975A4`（`push imm32`） | `_CODOL_WriteChallengeResponse` |
| 客户端 | `0xCB7AE4` | `0x9BFB9`（`mov edx,imm32`） | 客户端 challenge 处理 |
| 客户端 | `0xCC5EF0` | `0x1EC4FE` | 另一处引用 |

**裁定**：`challengeResponse` 是**两侧共有的 iD-Tech 握手标识**（PROVEN）。这是本轮唯一在握手语义层可交叉验证的共享点。

## 4. 等价字节结构检查

| 候选 | 服务端 | 客户端 | 结论 |
|---|---|---|---|
| `7F 00 00 01` 会话就绪签名 | 6 处（`.text` 内 `0x9A454..0x9A46A` 等） | 2 处 | **共享**（PROVEN 存在；语义对应 INFERRED 强） |
| 16 字节 `[1,2,0,0,0,0,≠0,cookie8]` | `_CODOL_HandshakeInit` 校验 | 未找到同构校验（客户端为 Demonware 对象握手） | 服务端特有 |
| 长度 `0xBD` 字段 | `_CODOL_HandshakeCookie` | 未找到 | 服务端特有 |

## 5. 字段编码/终止/边界检查（服务端 iD-Tech）

- 长度常量 `0xBD`（189）为 challenge 数据长度（`0x98611`）。
- `0x40`（64）为响应缓冲区长度（`0x975A8`/`0x975BB`）。
- `_CODOL_HandshakeInit` 对 cookie 做 **16 字节 XOR 全等比较**（`or eax,edx; setne`）。
- 无 Demonware 风格的 `recv counter`/HMAC 32 字节比较。

## 6. 与握手状态的关系

| 服务端字段 | 含义 | 证据 |
|---|---|---|
| `[obj+0x238]`/`[obj+0x23C]` | challenge 有效标志 | `0x98380/0x98389` |
| `[obj+0x50]`/`[obj+0x54]` | 期望 cookie（8 字节） | `0x98398/0x983A3` |
| `[obj+0x78]` | 关联标识 | `0x983BC` |
| `[obj+0x25C]` | 会话已建立标志 | `_CODOL_NetworkAdmission` `0x9A367` |
| `[obj+0x64]`/`[obj+0x68]` | admission/authenticated 标志 | `0x9A370`/`0x9A3EE` |
| `[obj+0x10..0x13]` | 会话四字节签名须为 `7F 00 00 01` | `_CODOL_NetworkSessionReady` `0x9A454..0x9A46A` |
| `[obj+0x264]` | 发送窗口 | `0x9A4CF/0x9A4E3` |

## 7. 结论

服务端的握手是**iD-Tech challenge/cookie/response**（`challengeResponse %d`、长度 `0xBD`、16 字节结构 `[1,2,...]`、会话签名 `7F000001`），**不是**客户端 E-21..E-25 追踪的 Demonware 协商对象（`CLIENTCHAL`/`BDDATA`/HMAC/recv counter）。两者**无字段级对应**。
