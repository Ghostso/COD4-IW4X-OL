# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001")
files={}

files["E26_SERVER_RECEIVE_DISPATCH_CLOSURE.md"]=r'''# E26 服务端接收与分派闭合

## 1. 映像身份复核

| 项 | 值 |
|---|---|
| 路径 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` |
| SHA-256 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`（复核一致） |
| ImageBase | `0x400000` |
| SizeOfImage | `0x15CF0000` |
| EntryPoint RVA | `0x14E0` |
| 节区 | `.text`(VA `0x1000`,VS `0x382BF8`) `.rodata` `.data` `.rdata` `.eh_fram` `.bss`(VS `0x15800000`, RawSize 0) `.edata` `.idata` `.tls` `.rsrc` `.reloc` |
| 符号 | **45,792 个 COFF 符号**（MinGW/GCC 16.2，保留 `.symtab` 名） |
| 导入 | ADVAPI32 CRYPT32 GDI32 KERNEL32 msvcrt SHELL32 USER32 WINMM **WS2_32**（28 项，含 `recv`/`recvfrom`/`send`/`sendto`） |

> 说明：服务端为 MinGW 构建，符号表可用——这使接收/分派链可**按名闭合**，与客户端（无符号、TenProtect 恢复镜像）形成鲜明对比。

## 2. 接收入口链（PROVEN）

```text
WS2_32.dll!recvfrom            (IAT, .idata)
  └─ _guard_recvfrom@24         RVA 0x98C4E  (符号)
_SV_ReadPackets                 RVA 0x06E2D5
  ├─ caller 0x6E53A             (_SV_FrameUsec 区域)
  ├─ caller 0x84833
  └─ caller 0x84DBB             (_SV_PacketEvent 内)
_SV_PacketEvent                 RVA 0x084CA2
  ├─ 0x84CC7 call 0x42B38B      (_MSG_BeginReading)
  ├─ 0x84CD2 call 0x42BCE1      (_MSG_ReadLong)
  ├─ 0x84CDA cmp eax,-1 ; je 0x84D13 -> _SV_ConnectionlessPacket
  ├─ 0x84CDF cmp eax,-2 ; je 0x84D22 -> 0x47CF41
  └─ 0x84DA9 call 0x42BCA2 (_MSG_ReadShort) ; 0x84DBB _SV_ReadPackets(...,ax)
_SV_ConnectionlessPacket        RVA 0x08487F
  ├─ 0x84E... 读取首字节；分派 'getinfo'/'getchallenge'/'connect' 等
  └─ _SV_DirectConnect          RVA 0x06F2C0  (收到 'connect' 后)
```

`_SV_Netchan_Decode` RVA `0x0855C0`（对 `int` 帧做 XOR 流变换）：

```asm
0855C8  mov ebx,[ebp+8]
0855CB  movzx eax,byte [ebx+0x40F88]
0855D2  imul eax,eax,0x408
0855DF  call 0x540133            ; 帧类型/长度检查
0855F5  ... 读取 CODOL2697_PROFILE_WIRE 配置（VA 0x7B9812）
085619  movzx eax,byte [esi]     ; 首字节
08561C  sub eax,0x4A             ; 'J' = 0x4A
08561F  cmp al,1                 ; 允许 0x4A/0x4B
085623  cmp byte [esi+1],0x20    ; 次字节 ' '
08564F  movzx eax,al             ; XOR 密钥字节
085663  call 0x49C4FE            ; XOR 变换
```

**裁定**：服务端有明确、可符号闭合的接收与顶层分派路径。**PROVEN。**

## 3. 客户端消息分派（`clc`）——3 位 opcode 0..4（PROVEN）

`_SV_ExecuteClientMessage` RVA `0x072DBB`：

```asm
072DE7  call 0x42B277            ; _MSG_Init(本地 0x801 缓冲)
072E1A  call 0x42B4F5            ; _MSG_WriteData(装载已解码载荷)
072E7D  call 0x42BF2D            ; _MSG_ReadBits(msg, 3) -> edi   [0x42BF2D 带 'push 3']
072E8E  cmp eax,0xFF
072EA7  cmp edi,4
072EAA  ja 0x47315E              ; >4 => 越界(日志)
072EB0  jmp dword ptr [edi*4+0x7B37A0]   ; <== 5 项跳表
```

跳表（VA `0x7B37A0`，5 项）：

| index | 目标 RVA | 行为 |
|---|---|---|
| 0 | `0x473104` | `mov ecx,1; call 0x4725F1`（`_SV_UserMove(...,1)`） |
| 1 | `0x47311B` | `mov ecx,0; call 0x4725F1`（`_SV_UserMove(...,0)`） |
| 2 | `0x473132` | `call 0x471701`（`_SV_ClientCommand`） |
| 3 | `0x47319A` | 直接 `jmp 0x472E01`（无操作返回） |
| 4 | `0x472E6F` | 回到读循环（拒绝/重读） |

**裁定**：服务端**客户端消息 opcode 宽度 = 3 位，取值范围 0..4**（PROVEN）。

## 4. 服务端（下行）servercommand 编码

`_SV_WriteReliableCommand` RVA `0x08612E`（据本目录 04/E3 报告并复核）：

- 命中 2697 profile 时写 **`0x02` + long + short(length) + data[length]`**；
- 未命中回退写 **`0x01` + long + string`**；
- `_SV_ProfileCommand2697` RVA `0x0860DE` 受 `CODOL2697_PROFILE_WIRE` 配置控制。

## 5. 分派形式排查

| 形式 | 结果 |
|---|---|
| 直接调用 | 全链为直接 `call rel32`（可符号闭合） |
| 跳表 | `_SV_ExecuteClientMessage` 的 5 项跳表（唯一 3 位 clc 分派） |
| 函数指针 / vtable | `_SV_PacketEvent` 中 `0x48E622` 遍历连接数组；`_SV_ReadPackets` 遍历 socket 数组 |
| 回调 / 注册表 | `_SV_ResolveEntityClassFields`/`_netFieldList`（网络字段），与握手无关 |
| 服务端多个 writer | **存在**：legacy (`0x01/0x03/0x05`) 与 2697 (`0x02/0x03/0x04/0x06`) 两套，须分别标记（见 E-26 冲突报告） |

## 6. 闭包边界

- 已闭合：socket → 帧解码 → 顶层（connectionless/reliable）→ `clc` 3 位分派 → `_SV_UserMove`/`_SV_ClientCommand`。
- 未闭合：`0x48E622`（连接匹配）内部、`_SV_ConnectionlessPacket` 的完整命令表、`_Netchan_Process` 的分片重组内部。
'''

files["E26_SERVER_HANDSHAKE_FIELD_MAP.md"]=r'''# E26 服务端握手字段与标签

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
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
