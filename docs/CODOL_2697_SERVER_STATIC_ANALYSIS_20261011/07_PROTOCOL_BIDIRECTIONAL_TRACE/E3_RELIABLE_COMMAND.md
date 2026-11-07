# E3 — Reliable command `0x02` / `0x01` static trace

> 阶段 E · CODOL 2697 · static-only  
> 分析日期：2026-10-12  
> 本文只依据只读 PE 解析、Capstone 反汇编、E8/E9 相对调用扫描、符号 JSON 与已有只读派生素材。未启动游戏或服务端，未注入，未修改二进制，未应用补丁，未编译。  
> 结论等级：`VERIFIED`（二进制指令直接支持）、`STATIC-INFERENCE`（有依据的语义解释）、`NOT-OBSERVED`（无运行时/互通观测）、`BLOCKED`（样本或工具不足）。

## 0. 结论速览

| 主题 | 结论 | 等级 |
| --- | --- | --- |
| 服务端样本身份 | 绝对路径样本的 SHA-256 与任务值一致，ImageBase 为 `0x400000` | `VERIFIED` |
| `_SV_WriteReliableCommand` | 函数边界 `0x8612E..0x861F8`（半开）；调用 `_SV_ProfileCommand2697` 后按返回码选择 `0x02`、`0x01` 或 `Com_Error` | `VERIFIED` |
| `_SV_ProfileCommand2697` | 函数边界 `0x860DE..0x8612C`；先检查 archive 激活，再查 `CODOL2697_PROFILE_WIRE`，`text` 强制旧格式，否则交给 `_CODOL2697_ProfileCommandBytes` | `VERIFIED` |
| 新格式 `0x02` 字段 | `02 | long(sequence/参数) | short(length) | profile_buf[length]` | `VERIFIED`（字段和写入调用指令） |
| 旧格式 `0x01` 字段 | `01 | long(sequence/参数) | NUL-terminated command string` | `VERIFIED` |
| `0x02` 的触发控制 | archive 激活、环境变量不等于 `text`、且 `_CODOL2697_ProfileCommandBytes` 返回正长度 | `VERIFIED` |
| `0x02` 是否受 E1 注册门控控制 | E3 调用链中未见对注册结构 `+0x6408` 或注册状态字段的直接检查 | `NOT-OBSERVED`（没有证据不等于证明没有间接依赖） |
| 客户端是否读取/分派 `0x02` | 不在本 E3 范围内；当前没有客户端侧的 `VERIFIED` 匹配 | `NOT-OBSERVED` / `BLOCKED` for E3-side client conclusion |
| 运行时互通 | 未运行、未抓包、未注入 | `NOT-OBSERVED` |

## 1. 样本身份与复核

| 项目 | 值 | 证据 |
| --- | --- | --- |
| 服务端样本 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 本任务只读检查 |
| SHA-256 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | `Get-FileHash` 与 PE/hash 复核一致：`VERIFIED` |
| 文件大小 | `7,295,919` 字节 | 文件系统元数据：`VERIFIED` |
| ImageBase | `0x400000` | `pefile` 读取：`VERIFIED` |
| EntryPoint RVA | `0x14E0` | `pefile` 读取，供身份记录 |
| SizeOfImage | `0x15CF0000` | `pefile` 读取，说明该 PE 的直接 RVA 空间很大；不得把文件偏移当 RVA |
| 符号来源 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json` | 仅作为函数名/边界参照，关键语义均由本样本反汇编复核 |
| 原始反汇编见证 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_data\e3_profile_bytes_full.txt` | 253 条指令，覆盖 `0x85D32..0x860D9` 的已解析尾指令 |

本文中的 RVA 均相对 `ImageBase 0x400000`。例如 `RVA 0x8612E` 的 VA 为 `0x48612E`。

## 2. 函数边界、调用约定和精确调用链

| 函数 | RVA 边界 | 本文采用的参数解释 | 等级 |
| --- | --- | --- | --- |
| `_CODOL2697_ProfileCommandBytes` | `0x85D32..0x860DE` | `EAX=input command`，`EDX=output byte buffer`，`ECX=capacity`；返回 `<0` 错误、`0` 不可转换/回退、`>0` 编码长度 | `VERIFIED`（寄存器使用和返回路径） |
| `_SV_ProfileCommand2697` | `0x860DE..0x8612E` | `EAX=command`，`EDX=output buffer`；返回 `_CODOL2697_ProfileCommandBytes` 语义或 `0` | `VERIFIED`（指令） |
| `_SV_WriteReliableCommand` | `0x8612E..0x861F8` | `EAX=MSG`，`EDX=sequence/参数`，`ECX=command string` | `VERIFIED`（保存到 `[ebp-0x40C]`、`EDI=[ECX]` 及调用点） |
| `_SV_UpdateServerCommandsToClient` | `0x861F8..0x86248` | `arg0` 客户端结构，`arg1` MSG；遍历待确认命令并调用 writer | `VERIFIED` |
| `_SV_UpdateServerCommandsToClientRecover` | `0x86248..0x86314` | 同一组参数，先预计算编码长度，再决定是否写入 | `VERIFIED` |

精确 E8 调用点：

| 调用者 RVA | 被调用者 RVA | 语义 |
| --- | --- | --- |
| `0x86150` | `0x860DE` | `_SV_WriteReliableCommand` 调用 `_SV_ProfileCommand2697` |
| `0x862DA` | `0x860DE` | recover 路径先测量 profile 编码长度 |
| `0x86127` | `0x85D32` | `_SV_ProfileCommand2697` 在未强制 text 时调用 bytes 转换器 |
| `0x8622B` | `0x8612E` | 普通更新路径写入 reliable command |
| `0x862AC` | `0x8612E` | recover 路径实际写入 reliable command |
| `0x710B7` | `0x861F8` | `_SV_SendClientGameState` 内调用普通更新 |
| `0x86DE0` | `0x861F8` | `_SV_BeginClientSnapshot` 内调用普通更新 |
| `0x873E4` | `0x86248` | `_SV_EndClientSnapshot` 内调用 recover 更新 |
| `0x86B06` | `_SV_SendMessageToClient` 入口 | 内部消息发送包装函数 |
| `0x86BCC` | `0x856B6` | `_SV_SendMessageToClient` 调用 `_SV_Netchan_Transmit` |
| `0x85716` | `0x8566A` | `_SV_Netchan_Transmit` 调用 `_SV_Netchan_Encode` |
| `0x8572C` | `0x499AEA` | `_SV_Netchan_Transmit` 调用 `_CODOL_NetchanSubmit` |

这些调用点均由 E8 相对调用扫描在本样本 `.text` 中直接命中：`VERIFIED`。

## 3. `_SV_ProfileCommand2697`：何时进入 `0x02`，何时回退 `0x01`

### 3.1 控制流

`_SV_ProfileCommand2697` 的关键指令如下（VA 显示，RVA 省略 ImageBase）：

```asm
004860EA  call 0x540133                 ; _CODOL_Target2697ArchivesActive
004860EF  test eax,eax
004860F1  jne 0x4860FA
004860F3  ...                            ; 未激活：返回 EAX=0
004860FA  mov dword [esp],0x7B98E0      ; "CODOL2697_PROFILE_WIRE"
00486101  call getenv
00486106  test eax,eax
00486108  je 0x48611E                   ; 未设置：尝试 bytes 转换
0048610A  mov dword [esp+4],0x7B98F7    ; "text"
00486112  mov dword [esp],eax
00486115  call strcmp
0048611A  test eax,eax
0048611C  je 0x4860F3                   ; 设置且等于 text：返回 0
0048611E  mov ecx,0x3FC                 ; output capacity
00486123  mov edx,esi                   ; output buffer
00486125  mov eax,ebx                   ; command
00486127  call 0x485D32                 ; _CODOL2697_ProfileCommandBytes
0048612C  jmp 0x4860F3                  ; 返回转换器返回值
```

### 3.2 返回语义

| `_CODOL2697_ProfileCommandBytes` / `_SV_ProfileCommand2697` 返回 | `_SV_WriteReliableCommand` 动作 | 线格式 | 等级 |
| --- | --- | --- | --- |
| `< 0` | `js 0x4861AF`，最终 `Com_Error(2, "Invalid target profile delta")` | 不写可靠命令；错误终止/错误路径 | `VERIFIED` |
| `== 0` | `je 0x4861C5` | 写 `0x01` 旧格式 | `VERIFIED` |
| `> 0` | `ESI=EAX` 且不跳转 | 写 `0x02` 新格式，`ESI` 同时是新格式长度 | `VERIFIED` |

直接指令：

```asm
00486155  test eax,eax
00486157  js   0x4861AF
0048615C  mov  esi,eax
0048615E  je   0x4861C5
```

因此：

- 未激活 archive：`_SV_ProfileCommand2697` 返回 `0`，走 `0x01`。
- 环境变量 `CODOL2697_PROFILE_WIRE` 值为 `text`：返回 `0`，走 `0x01`。
- 环境变量未设置或值不是 `text`：调用 bytes 转换器。
- bytes 转换器返回 `0`：走 `0x01`。
- bytes 转换器返回正长度：走 `0x02`。
- bytes 转换器返回负数：走 `Com_Error`。

### 3.3 archive 激活检查

`_CODOL_Target2697ArchivesActive` 的入口在 RVA `0x140133`：

```asm
00540133  mov edx,[0x1515872C]
00540139  mov eax,0
0054013E  test edx,edx
00540140  je 0x54014F
00540142  cmp dword [edx+0x34],0x16D
00540149  sete al
0054014C  movzx eax,al
0054014F  ret
```

- 指针为空：返回 `0`。`VERIFIED`。
- 指针非空且 `[edx+0x34] == 0x16D`：返回 `1`。`VERIFIED`。
- `0x16D` 的业务语义未在本样本符号或字符串中证明；只能说它是该指针对象的偏移 `+0x34` 字段的精确比较值。`STATIC-INFERENCE`。

### 3.4 控制因素结论

`0x02` 直接受以下条件共同控制：

1. `_CODOL_Target2697ArchivesActive` 为真（`VERIFIED`）；
2. `getenv("CODOL2697_PROFILE_WIRE")` 为空或 `strcmp(value, "text") != 0`（`VERIFIED`）；
3. `_CODOL2697_ProfileCommandBytes` 对命令返回正值（`VERIFIED`）。

未发现：

- 对客户端版本字段的直接比较；
- 对本样本 E1 注册结构 `+0x6408` 的直接引用；
- 对 command 字符串中版本号的直接检查。

这只能说明 E3 的直接调用链中没有这些检查，不能排除上层调用者或间接数据依赖。`STATIC-INFERENCE` / `NOT-OBSERVED`。


## 4. `0x02` 与 `0x01` 的精确线格式

### 4.1 `_SV_WriteReliableCommand` 的两条写路径

`_SV_WriteReliableCommand` 在 branch 判定后，两条路径共享入口参数：

- `EBX = MSG *`：入口 `EAX`，保存于 `0x8613E`；后续作为 `_MSG_Write*` 的第一个参数。
- `[ebp-0x40C]`：入口 `EDX`，保存于 `0x86140`；随后作为 `_MSG_WriteLong` 的参数。
- `EDI`：入口 `ECX`，保存于 `0x86146`；旧路径作为 `_MSG_WriteString` 的字符串指针。
- `[ebp-0x408]`：`0x86148` 交给 `_SV_ProfileCommand2697` 的局部输出缓冲区；新路径作为 `_MSG_WriteData` 的数据指针。
- `ESI`：`0x8615C` 接收 `_SV_ProfileCommand2697` 的返回正值，作为新格式 payload 长度。

以上寄存器和栈槽的搬运均由 `0x8612E..0x8619F` 的直接指令支持。`VERIFIED`。

### 4.2 新格式 `0x02`

当 `0x8615E` 的 `je` 不成立，即 `EAX > 0` 时，写出的逻辑顺序和精确调用位置为：

| 字段 | 写入 RVA | 调用目标 RVA | 实际参数/来源 | 等级 |
| --- | --- | --- | --- | --- |
| opcode `0x02` | `0x8616B` | `_MSG_WriteByte` `0x42B40A` | 立即数 `2` | `VERIFIED` |
| 32-bit `sequence/参数` | `0x8617D` | `_MSG_WriteLong` `0x42B464` | `[ebp-0x40C]`，入口 `EDX` | `VERIFIED`（字段本身）；语义名为 `STATIC-INFERENCE` |
| 16-bit `length` | `0x86189` | `_MSG_WriteShort` `0x42B434` | `ESI`，即 `_SV_ProfileCommand2697` 的正返回值 | `VERIFIED` |
| `profile_buf[length]` | `0x8619F` | `_MSG_WriteData` `0x42B4F5` | 数据指针 `[ebp-0x408]`，长度 `ESI` | `VERIFIED` |

因此，服务端侧线格式为：

```text
0x02 | long(sequence/参数) | short(length) | profile_buf[length]
```

`length` 的数值直接来自 `_CODOL2697_ProfileCommandBytes` 的返回值；该返回值在 `0x8615C` 保存到 `ESI`。最大可返回长度受容量参数 `0x3FC` 约束，见第 6 节。`VERIFIED`。

这里的 `sequence/参数` 是函数名和调用者上下文中可见的用途描述，不是从协议文档验证出的命名。32 位字段的存在、来源和写入位置是 `VERIFIED`；它究竟表示序列号、命令编号还是其他参数，仍为 `STATIC-INFERENCE`。

### 4.3 旧格式 `0x01`

当 `0x8615E` 的 `je` 成立，即返回 `EAX == 0` 时，写出的逻辑顺序和精确调用位置为：

| 字段 | 写入 RVA | 调用目标 RVA | 实际参数/来源 | 等级 |
| --- | --- | --- | --- | --- |
| opcode `0x01` | `0x861D0` | `_MSG_WriteByte` `0x42B40A` | 立即数 `1` | `VERIFIED` |
| 32-bit `sequence/参数` | `0x861E2` | `_MSG_WriteLong` `0x42B464` | `[ebp-0x40C]`，入口 `EDX` | `VERIFIED`（字段本身）；语义名为 `STATIC-INFERENCE` |
| command string | `0x861EE` | `_MSG_WriteString` `0x42B537` | `EDI`，保存的入口 `ECX` | `VERIFIED` |

因此，服务端侧线格式为：

```text
0x01 | long(sequence/参数) | NUL-terminated command string
```

`_MSG_WriteString` 的符号名直接表明这是字符串写入；具体 NUL 终止实现未在本 E3 报告中重新反汇编该 helper，因此“NUL-terminated”标为 `STATIC-INFERENCE`。0x01 与 0x02 使用同一个 32 位入口 `EDX` 字段。`VERIFIED`。

### 4.4 错误路径

`0x86157` 的 `js 0x4861AF` 处理负返回。错误路径在 `0x861BE` 调用 `_Com_Error`，参数为：

- 第一参数：`2`（`0x861B7` 附近的栈参数布局）
- 第二参数：字符串 VA `0x7B98FC`，对应 RVA `0x3B98FC`，内容 `Invalid target profile delta`

错误路径不写 `0x01` 或 `0x02` 可靠命令；调用 `Com_Error` 后跳回函数收尾。`VERIFIED`。

## 5. 调用者、recover 路径和最终发送链

### 5.1 普通更新路径 `0x861F8..0x86248`

`_SV_UpdateServerCommandsToClient` 的入口参数在代码中使用为：

- `[ebp+8]`：客户端结构指针，载入到 `ESI`，RVA `0x861FE`。
- `[ebp+0xC]`：内部 `MSG *`，载入到 `EDI`，RVA `0x86201`。

普通路径读取：

- `[ESI+0x40F88]`：上一次/待处理的命令索引；
- `[ESI+0x40F84]`：最后一条命令索引；
- `[ESI+0x40F8C]`：循环结束后写回的确认/恢复索引。

精确行为：

1. `0x86204` 取 `[ESI+0x40F88]`，`0x8620A` 计算 `EBX = value + 1`。
2. `0x8620D` 取 `[ESI+0x40F84]`；`0x86213` 若 `EBX > last`，跳到收尾。
3. 对每条命令，`0x86217` 将索引的低字节乘以 `0x408`，在 `0x86220` 计算 `ECX = ESI + EAX + 0x784`，即命令槽指针。
4. `0x86227` 将索引放入 `EDX`，`0x86229` 将 `MSG *` 放入 `EAX`，`0x8622B` 调用 `_SV_WriteReliableCommand`。
5. 循环结束后，`0x8623D` 将最后索引 `[ESI+0x40F84]` 写入 `[ESI+0x40F8C]`，然后返回。

索引间隔 `0x408`、命令数组基址 `+0x784`、索引字段 `+0x40F84/+0x40F88/+0x40F8C` 均由直接访问指令支持；把这些字段的业务名称解释为“待确认/最后命令/恢复索引”属于 `STATIC-INFERENCE`。

### 5.2 recover 路径 `0x86248..0x86314`

recover 路径在真正写命令前，先用 `_SV_ProfileCommand2697` 测量/转换命令：

- `0x862BF`：取下一命令索引低字节并计算槽指针；
- `0x862D2`：设置局部 profile 输出缓冲区 `[ebp-0x408]`；
- `0x862DA`：调用 `_SV_ProfileCommand2697`；
- `0x862DF`：`test eax,eax`；
- `0x862E1`：`js 0x48627A`，负值进入 `Com_Error`；
- `0x862E3`：`je 0x486293`，零值走旧格式长度估算；
- `0x862E5`：正值执行 `add eax,1`，即 `profile_len + 1`，走新格式长度估算。

两个长度估算分支在 `0x8629B` 合流：

- 旧格式分支 `0x86293`：`strlen(command)`，再加 `[MSG+0x14]`（当前消息长度）和 `6`。
- 新格式分支 `0x862E5`：`profile_len + 1`，再加 `[MSG+0x14]` 和 `6`。
- `0x862A1`：与 `[MSG+0x10]` 比较；`jge 0x4862F3` 为无法容纳/不写入路径。
- 可容纳时 `0x862AC` 调用 `_SV_WriteReliableCommand`。

长度公式中的 `6` 对应旧格式的 `opcode(1) + long(4) + NUL(1)`；新格式公式中的 `+1` 对应 `opcode(1)`，另行写入的 `short(2)` 包含在固定开销 `6` 中。这里的“容纳”解释为 `STATIC-INFERENCE`；`0x862A1` 的直接比较和调用位置是 `VERIFIED`。

recover 收尾在 `0x862FB` 附近：

- 计算 `[edi-1]` 为已处理索引；
- 与 `[client+0x40F8C]` 比较；
- 仅当更大时写回 `[client+0x40F8C]`；
- `0x86314` 是符号边界附近的返回指令。

### 5.3 上游调用点

| 调用点 RVA | 被调用者 | 直接上下文 | 等级 |
| --- | --- | --- | --- |
| `0x710B7` | `_SV_UpdateServerCommandsToClient` `0x861F8` | `_SV_SendClientGameState` 内，先 `_MSG_Init`，写 32 位 `[EBX+0x40FBC]`，再更新可靠命令 | `VERIFIED` |
| `0x86DE0` | `_SV_UpdateServerCommandsToClient` `0x861F8` | `_SV_BeginClientSnapshot` 内，写 `[client+0x40FBC]` 后在条件分支更新可靠命令 | `VERIFIED` |
| `0x873E4` | `_SV_UpdateServerCommandsToClientRecover` `0x86248` | `_SV_EndClientSnapshot` 内，先写 `[client+0x40FBC]` 并使用 recover 路径 | `VERIFIED` |

`_SV_SendClientGameState` 的可见序列为：

```text
_MSG_Init
-> MSG_WriteLong([client+0x40FBC])
-> _SV_UpdateServerCommandsToClient
-> _SV_WriteGameState
-> _SV_SendMessageToClient
```

其中 `0x710C3` 调用 `_SV_WriteGameState`，`0x7110C` 调用 `_SV_SendMessageToClient`。这证明可靠命令写入发生在 gamestate 写入和发送之前；不证明客户端支持 `0x02`。`VERIFIED`（服务端调用顺序）。

`_SV_BeginClientSnapshot` 的调用点在 `0x86DE0`；`_SV_EndClientSnapshot` 的 recover 调用点在 `0x873E4`。`_SV_EndClientSnapshot` 随后在 `0x873E9` 调用 `_CODOL_Target2697ArchivesActive`，并在 `0x87400` 写入 `0x05` 或 `0x06`：

```asm
004873e9  call 0x540133       ; _CODOL_Target2697ArchivesActive
004873ee  cmp eax,1
004873f1  mov eax,5
004873f6  sbb eax,-1
004873f9  mov [esp+4],eax
004873fd  mov [esp],edi
00487400  call _MSG_WriteByte
```

按 `cmp`/`sbb` 的 32 位结果：active 为 `1` 时写出 `0x06`，active 为 `0` 时写出 `0x05`。这是 E2 的相邻证据，不是 `0x02` 客户端支持证据。`VERIFIED`。

### 5.4 内部 MSG 到 netchan 的边界

`_SV_SendMessageToClient` 在 RVA `0x86B06`：

- `0x86B0F` 从 `[ebp+8]` 载入第一个参数到 `EDI`，这是内部消息结构对应的对象；
- `0x86BBB` 取 `[EDI+0x14]` 作为长度；
- `0x86BC2` 取 `[EDI+8]` 作为数据指针；
- `0x86BCC` 调用 `_SV_Netchan_Transmit` `0x856B6`。

因此，可靠命令的 `0x01`/`0x02` 首先全部写入 `_SV_*` 使用的内部 `MSG` 缓冲区，`_SV_SendMessageToClient` 再把该内部缓冲区的数据指针和长度交给 netchan。`VERIFIED`。

`_SV_Netchan_Transmit` `0x856B6..0x857AD` 的边界行为：

1. `0x856C0` 取 `[ebp+0x10]` 为长度。
2. `0x856C3` 计算 `len - 4`，`0x856C6` 与 `0x1FFFC` 比较；越界或长度小于 4 时返回失败。
3. `0x856CD` 检查 `[ebp+0xC]` 数据指针非空。
4. `0x856EA` `malloc(len)`，`0x85703` `memcpy`。
5. `0x85716` 调用 `_SV_Netchan_Encode` `0x8566A`。
6. `0x8572C` 调用 `_CODOL_NetchanSubmit` `0x499AEA`。
7. `0x85736` `free` 临时缓冲区。

这说明 `0x02` 的 profile payload 不直接调用 netchan；它先成为内部 MSG 的一部分，随后由 `_SV_Netchan_Transmit` 编码并提交。内部 MSG 边界和 netchan 外层边界已分开。`VERIFIED`。

## 6. `_CODOL2697_ProfileCommandBytes`：J/K 编码细节

函数边界：`0x85D32..0x860DE`（半开）。已有只读全量反汇编见证文件：

`D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_data\e3_profile_bytes_full.txt`

该文件记录 253 条指令，覆盖 `0x85D32..0x860D9`。以下结论来自该见证与本样本 PE 的直接指令。

### 6.1 入口和顶层命令格式

入口使用：

- `EAX`：输入 command 指针；
- `EDX`：调用者输出缓冲区指针；
- `ECX`：输出容量；`_SV_ProfileCommand2697` 在 `0x8611E` 传入 `0x3FC`。

关键控制流：

```asm
00485D47  test eax,eax
00485D49  je    0x485DF5       ; NULL -> EAX=0
00485D51  movzx ecx,byte [ebx]
00485D54  lea   edx,[ecx-0x4A]
00485D57  cmp   dl,1
00485D5A  ja    0x485DF5       ; 仅接受 0x4A ('J') 或 0x4B ('K')
00485D60  cmp   byte [ebx+1],0x20
00485D64  jne   0x485DF5       ; 第二字节必须是空格
```

因此：

- 输入指针为 NULL，或首字节不是大写 `J`/`K`，返回 `0`。`VERIFIED`。
- 首字节为 `J` 或 `K` 但第二字节不是空格，返回 `0`。`VERIFIED`。
- 首字节被复制到输出缓冲区偏移 0（`0x85D6A`）。`J` 与 `K` 的实际业务区别没有被本函数分支进一步区分；“J/K 两种命令语义不同”只能标 `STATIC-INFERENCE`，具体语义未知。
- 输入已识别为 `J ` 或 `K ` 但内容不完整/格式错误时，多数路径返回 `-1`，不是 `0`。例如空索引和最终长度 1 的检查会走 `0x86094` 的 `cmp esi,1` 拒绝路径。`VERIFIED`。

### 6.2 十进制索引和范围

在跳过前导空格后，索引必须由十进制数字组成：

- `0x85DA5..0x85DAA`：首数字范围检查 `0x30..0x39`；
- `0x85DC5..0x85DDB`：逐位 `value = value * 10 + digit`；
- `0x85DE1`：中间累加值必须 `<= 0xCCC`；
- `0x85E61`：至少要求一个数字；
- `0x85E65`：最终索引必须 `<= 0x7FFB`；
- `0x85E6C`：索引后必须出现空格；
- `0x85E76..0x85E8B`：跳过一个或多个空格，若这时已经到 NUL，则走错误路径。

`0xCCC` 是解析阶段的中间上限，`0x7FFB` 是最终绝对索引上限。`0x7FFB` 的编码单位或业务含义未由字符串/符号证明，不能写成“地图编号上限”等业务结论。数值检查本身为 `VERIFIED`，业务含义为 `STATIC-INFERENCE`。

### 6.3 5 字节分段头与 payload

解析器按段处理：

- 在写入 payload 前，`0x85E8F..0x85E9E` 计算当前输出位置 `+5`，并与 `0x3FB` 比较；超出返回 `-1`。
- 当一段达到 `0xFF` 个 payload 字节时，`0x85ED2` 和 `0x85F83` 路径写出：
  - 4 字节 little-endian base index；
  - 1 字节 payload count `0xFF`（`0x85FB3`）。
- 段结束后写出的普通头同样由 4 字节 base index 和 1 字节 count 组成；正常段 count 在 `0x86043` 写入。
- payload 字节数上限为 `0xFF`；达到上限时刷新并推进 base index。
- `0x85EE6` 和 `0x85FD6` 对 base index/累计位置做 `0x7FFB` 检查。
- `0x85EF2`、`0x85FBE` 对输出偏移做 `0x3FB` 检查，最终容量由入口 `0x3FC` 约束。

在本报告用词中，“payload count”指该 5 字节头尾部的 1 字节计数值；这是对写入位置和 `0xFF` 检查的直接描述，不将该字段扩展解释为其他协议语义。`VERIFIED`。

### 6.4 payload 文本/十六进制编码

payload 解析的直接分支：

```asm
00485F19  cmp cl,0x4F       ; 'O'
00485F1C  sete al
00485F1F  cmp cl,0x5A       ; 'Z'
00485F22  je   0x485ECC
00485F24  test al,al
00485F26  jne  0x485ECC
```

验证的编码规则：

- `O`（`0x4F`）写出字节 `0x01`。`VERIFIED`。
- `Z`（`0x5A`）写出字节 `0x00`。`VERIFIED`。
- 其他 payload 内容是两位十六进制数字，按高半字节和低半字节合成一个字节。`VERIFIED`。
- 十六进制数字接受 `0-9` 和 `A-F`；关键比较使用 `0x41` 起点，因此小写 `a-f` 不接受。`VERIFIED`。
- 该函数的输入不是裸二进制；它解析的是 `J `/`K ` 前缀的命令文本，再生成二进制 payload。这个“文本/十六进制到二进制”的总称可由指令流支持；`O`/`Z` 的业务名称（例如“1/0”）没有额外符号证明，标 `STATIC-INFERENCE`。

`CODOL2697_PROFILE_WIRE=text` 的控制发生在更上层 `_SV_ProfileCommand2697`：如果环境变量存在且与 `"text"` 相等，函数直接返回 `0`，不调用本转换器，因而回退 `0x01`。这证明该环境值是“强制旧线格式”的开关，不证明本函数内部存在独立的 text 模式。`VERIFIED`（分支）。

### 6.5 结果长度和 memcpy

最终结果检查在 `0x8608E..0x860A5`：

- `0x86094`：`cmp esi,1`；长度等于 1 时拒绝，返回 `-1`。
- `0x8609A`：比较入口容量 `[ebp-0x40C]` 与最终长度 `ESI`；容量小于长度时拒绝。
- 接受时调用 `0x860C4` 的 `memcpy` `0x765690`：
  - 目标：入口保存的输出缓冲区；
  - 源：`[ebp-0x408]` 内部缓冲区；
  - 长度：`ESI`。
- `0x860C9` 将长度 `ESI` 放入 `EAX`，作为正返回值返回。

因此：

- 返回 `0` 的已证明情形：输入 NULL，或顶层格式不是 `J`/`K`，或第二字节不是空格。
- 返回 `-1` 的已证明情形：已识别 `J`/`K` 前缀，但索引、空格、分段、字符或输出长度检查失败；最终长度等于 1 也返回 `-1`。
- 返回正值的已证明含义：成功编码的二进制长度；`_SV_WriteReliableCommand` 将其作为 `0x02` 的 `short length`。
- 输出容量传入值为 `0x3FC`；最终接受条件允许长度等于容量，拒绝长度大于容量。`VERIFIED`。
- `0x3FB` 和 `0x3FC` 的具体边界差异来自“写前偏移检查”和“最终容量检查”两个不同位置；不应把两者混为一个限制值。`VERIFIED`。

## 7. 客户端侧 0x02 的必要提示

本 E3 报告没有完成客户端二进制中 `0x02` 的读取、内部消息游标推进、opcode 分派或状态转换验证。因此：

- 服务端写 `0x02` 不能推出客户端理解 `0x02`。
- 当前客户端 `0x02` 读取/处理结论为 `NOT-OBSERVED`。
- 如果 E4 需要结论而缺少可复现客户端定位，应标记为 `BLOCKED`，而不是把“未搜索到”写成“客户端不存在”。
- 本报告不对 `_CODOL2697_ProfileCommandBytes` 的输出语义与客户端解码器做任何闭环声明；该工作属于 E4。
- `0x01` 路径同样没有在本 E3 中完成客户端读取验证；旧协议的历史资料不能替代本样本客户端指令证据。

## 8. 匹配依据、其它解释和未解决问题

### 8.1 匹配依据

- 样本绝对路径与 SHA-256 已复核；ImageBase 和入口点由 PE 解析确认。
- 函数名来自 `syms_NEW.json`，关键分支和调用目标通过本样本 Capstone 反汇编及相对调用扫描复核。
- `0x85D32` 的完整指令见证来自已有只读派生文件 `_data\e3_profile_bytes_full.txt`。
- 调用者 RVA 均为同一 PE 内相对调用目标，不是字符串猜测。
- `0x7B98E0`、`0x7B98F7`、`0x7B98FC` 的字符串按 RVA 读取为 `CODOL2697_PROFILE_WIRE`、`text`、`Invalid target profile delta`。

### 8.2 其它可能解释

- `[ebp-0x40C]` 的 32 位字段可能不是协议序列号；E3 只能证明它被原样写入 `0x01` 和 `0x02`。
- `[client+0x40F84]` 等偏移的业务含义来自访问模式和调用者上下文；偏移本身是 `VERIFIED`，名称不是。
- `_CODOL_Target2697ArchivesActive` 的 `[edx+0x34] == 0x16D` 可能是目标版本、archive 代次或其他对象字段；E3 未证明其业务含义。
- `0x01` 被本文称为“旧格式”是因为它是不经 profile 转换的字符串分支；没有独立版本证据证明所有旧客户端都必须使用它。
- `0x02` 的 `short length` 可能是 payload 长度、段长度或其他长度语义；直接数据来源证明它是转换器的正返回长度。

### 8.3 未解决问题

- `0x02` 是否受客户端版本字段、注册结构 `+0x6408` 或其他上层状态间接控制：`NOT-OBSERVED`。
- `J` 与 `K` 的业务语义差异：`STATIC-INFERENCE`/未完成。
- 5 字节段头中 count 的业务名称：`STATIC-INFERENCE`。
- 客户端是否读取 `0x02`，以及读取后如何分派：`BLOCKED/NOT-OBSERVED`，等待 E4。
- 运行时环境变量实际取值、真实命令索引和真实线数据：`NOT-OBSERVED`。
- `_MSG_WriteString` 的 NUL 终止实现是否还有额外长度/容量分支：未在 E3 中重新展开；线格式解释为 `STATIC-INFERENCE`。

## 9. 最终回答（E3 范围）

### 9.1 服务端是否确实包含更新代码

`VERIFIED`：该样本包含 `_CODOL2697_ProfileCommandBytes`、`_SV_ProfileCommand2697` 和双格式 `_SV_WriteReliableCommand`，且在 2697 archive 激活路径下可以将 `J `/`K ` 命令转换为二进制 `0x02`，否则可回退 `0x01`。这足以证明该样本包含 2697 专用可靠命令逻辑。

“相较某个更旧服务端版本具体新增/改变了什么”需要旧样本的同版本反汇编差分；本 E3 没有重新执行该通用差分，故不把“新版”结论扩展到本报告未复核的旧样本。

### 9.2 已能确认的字段/opcode 与未知项

已确认的服务端字段：

- `0x01 | long | NUL-terminated string`
- `0x02 | long | short(length) | binary profile payload`

其中 `long` 的具体业务名、`short length` 的进一步用途、`J/K` 语义仍未知。客户端对两者的读取和分派均未在 E3 中确认。

### 9.3 当前最强静态证据链

服务端侧的 `writer -> profile converter -> internal MSG -> send wrapper -> netchan transmit` 链最完整，证据等级为 `VERIFIED`（函数/调用/字段层面）。该链条止于服务端发送边界，不能替代客户端闭环。

### 9.4 当前最主要兼容性障碍

主要障碍是缺少客户端 `0x02` 读取、内部消息游标和 opcode 分派的可靠静态匹配；因此无法确认 2697 客户端是否与服务端 `0x02` 线格式一致。运行时互通也完全没有观测。

### 9.5 下一步最小任务

由 E4 对其 manifest 对应的客户端二进制做最小定位：搜索可靠命令读取入口、`0x01`/`0x02` 分派、`short` 长度读取和 profile payload 处理。E3 不再扩大扫描范围。

## 10. 证据等级汇总

| 主题 | 具体证据 | 当前等级 |
| --- | --- | --- |
| 服务端样本身份 | `codol_dedrun.exe` SHA-256 与任务值一致；ImageBase `0x400000` | `VERIFIED` |
| `0x02` 写入 | `0x8616B` byte=2、`0x8617D` long、`0x86189` short、`0x8619F` data | `VERIFIED` |
| `0x01` 写入 | `0x861D0` byte=1、`0x861E2` long、`0x861EE` string | `VERIFIED` |
| 分支语义 | `0x86157` js、`0x8615E` je；正值为新格式，零为旧格式 | `VERIFIED` |
| 新格式控制因素 | archive active + 非 `text` 环境 + profile 转换正值；未发现直接注册/版本检查 | `VERIFIED`（直接分支）；`NOT-OBSERVED`（间接控制） |
| recover 预计算 | `0x862DA` 调用转换器、`0x862A1` 长度比较、`0x862AC` 写入 | `VERIFIED` |
| 上游调用链 | `0x710B7`、`0x86DE0` 到普通更新；`0x873E4` 到 recover | `VERIFIED` |
| 最终发送链 | `_SV_SendMessageToClient 0x86B06` -> `_SV_Netchan_Transmit 0x856B6` -> encode/submit | `VERIFIED` |
| J/K 前缀 | 只接受并保留首字节；未见语义分支 | `VERIFIED`（接受/保留）；`STATIC-INFERENCE`（语义） |
| 索引/长度边界 | `0xCCC`、`0x7FFB`、`0xFF`、`0x3FB`、`0x3FC`、长度 1 拒绝 | `VERIFIED` |
| O/Z/hex payload | `O -> 0x01`、`Z -> 0x00`、大写两位 hex 合成字节、小写不接受 | `VERIFIED` |
| 客户端 `0x02` 读取/分派 | E3 未完成客户端验证 | `BLOCKED` / `NOT-OBSERVED` |
| 运行时互通 | 未启动、未抓包、未注入 | `NOT-OBSERVED` |
