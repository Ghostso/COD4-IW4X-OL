# 337 — `build_startgame_payload` vs 客户端 `0x625CE0` 逐段对账

> 结论先行：**`build_startgame_payload` 与客户端反序列化器 `0x625CE0` 逐段完全一致**
> （顺序 / 类型 / 长度 全中），包括那 1 位 ctor 头。唯一"多余"的是 `write_blob` 尾部
> 补零（4 位），客户端不读也不校验 —— 无害。**服务端不是开局失败的故障点（就本函数而言）。**

---

## 1. 服务端实际输出（机器算，不是口算）

用 `_r64_18/server_bytes.py`（逐行复制 `BitWriter` 逻辑，`python -I` 运行）算出：

| 项 | 值 |
|---|---|
| `build_bd_common_addr_67(127.0.0.1, 28960, 1)` | 67 B |
| `build_startgame_payload(addr67, 0x1122334455667788, key16)` | **109 B** |
| 位长 | 872 bit = 109*8 |

addr67 十六进制：
```
7f0000012071 00ff00ff0000 (x9) 7f0000012071 01
```

payload 逐位解码（同脚本 `--decode`）：
```
@bit0   ctor.hdr      1 bit  = 1
@bit1   tag.field1    5 bit  = 0x3
@bit6   field1.val    8 bit  = 3
@bit14  tag.blob1     5 bit  = 0x13
@bit19  subtag        5 bit  = 0x8
@bit24  len           32 bit = 67
        data 67 B
@bit592 tag.blob2     5 = 0x13 / 5 = 0x8 / 32 = 8 / 8 B
@bit698 tag.blob3     5 = 0x13 / 5 = 0x8 / 32 = 16 / 16 B
consumed = 868 / 872  ⇒ 尾部 4 位补零（write_blob 后无内容，buf 最后 1 字节高位为 0）
```

调用点：`lobby_server.py:1131-1133`（11/4 setRoomData）与 `:1270-1272`（6/x mmstart），
两处都是 `build_bd_common_addr_67(GAME_IP,GAME_PORT)` → `build_startgame_payload(_addr67, SESSION_ID, SEC_KEY)`
→ `build_room_push(1,"HostUser",ROOM_ID,_sg_payload)`。

`SEC_KEY` 来自 `battle_security_key.txt`（32 hex）或环境 `CODOL_SEC_KEY`，缺省 `00*16`
（`lobby_server.py:591-608`）。二者都是 **16 B**，长度与客户端期望一致。

---

## 2. 客户端反序列化器 `0x625CE0`（起点 → ret，完整）

调用者唯一：`0x634B2B`（在 `0x634870` 内，case 3 分支，跳转表 `0x636F3C[3]=0x634AC2`）。
`ecx` = 已构造好的 bit reader，`[ebp+8]` = 消息对象；`[ebx]` = reader 的深拷贝基址。

```
00625CE9  mov edi,[ebx]                 ; reader
00625CED  push 3   / ecx=edi  call 0xB774E0   ; readTag(3)
00625CF6  test al,al  je fail
00625CFA  push 8   lea eax,[ebp+0xB]  push  call 0xB772E0   ; readBits(8) -> [ebp+0xB]
00625D11  movzx ecx,byte [ebp+0xB]
00625D15  mov [esi+4],ecx                ; ★ 字段1 u8 -> msg+4
00625D23  eax = [esi+8];  add eax,0x18   ; 目标 &msg[8]->+0x18
00625D2B  lea edx,[ebp+8]; push edx; push eax; call 0x4F3EB0   ; readBlob(67)
00625D42  ecx=[esi+8]; mov [ecx+0x118],edx  ; ★ 长度 67 存 msg[8]+0x118
00625D56  ecx=[esi+8]; add ecx,0x10      ; 目标 &msg[8]+0x10
00625D5B  lea eax,[ebp+8]; push; push; call 0x4F3EB0   ; readBlob(8)
00625D72  mov [ebp+8],0x10
00625D7D  eax=[esi+8]; add eax,0x1CC     ; 目标 &msg[8]+0x1CC
00625D82  lea edx,[ebp+8]; push; push; call 0x4F3EB0   ; readBlob(16)
00625D95  pop edi; pop esi; mov al,1; pop ebx; pop ebp; ret 4
```

字段表（类型 / 长度 / 去向）：

| # | 客户端读 | 类型 | 长度 | 去向 |
|---|---|---|---|---|
| 0* | reader ctor 已吃掉 | 1 bit 头 | 1 bit | reader+0x21（见 §3） |
| 1 | `readTag(3)` + `readBits(8)` | u8 | 1 B | `msg_object+4` |
| 2 | `readBlob` | blob | **67 B**（长度同时写 `msg[8]+0x118`） | `msg[8]+0x18` |
| 3 | `readBlob` | blob | 8 B | `msg[8]+0x10` |
| 4 | `readBlob` | blob | 16 B | `msg[8]+0x1CC` |

`readBlob = 0x4F3EB0`：`readTag(0x13)` + `readTag(0x08)` + `readBits(32,len)` + `readBits(len*8)`，
且 `len` 被截断到调用方给的 capacity（`lea eax,[edx+esi*8]`，超长时串长仍回填真实 len）——
**即 67/8/16 是容量下限而非唯一接受值，但服务端写的正是上限值**。

`readTag = 0xB774E0`：5 bit，`+0x21` 为 0 时直接返回 true（不读）；否则 `readBits(5)` 比对。
`readBits = 0xB772E0`：LSB-first、跨字节边界、越界置 `[reader+0x20]=1` 并返回 false。

---

## 3. 1 位 ctor 头：客户端确实吃掉，位置=`reader+0x21`

- `0xB779A0`（reader 构造器）`0xB779EF lea edi,[esi+0x21]`；`0xB77A02 mov [edi],0`；
  `0xB77A04 cmp [ebp+0x10],0`（=useDataTypes 参数）；
  非零且长度非零时：`0xB77A13-0xB77A1F` 分配缓冲、`0xB77A29 mov [esi+0x14],ebx`（bit 总长）、
  `0xB77A2F call 0xB772E0`，参数 `push 1` + `push edi` ⇒ **读 1 bit 到 `+0x21`**。
- 这就是"1 位 ctor 头"：`useDataTypes=1` ⟺ `+0x21≠0`，`readTag` 据此决定是否真正读 5 位标签
  （`0xB774F0 cmp byte [ecx+0x21],0 / je 0xB7754F` 直接返回成功）。
- 服务端 `BitWriter.__init__` 也写这一位（`lobby_server.py:645`），**两侧一致**。

★ 注意：`0x625BE0`（同一消息的**写侧**）**不写**这 1 位（它只在 `0xB77B10` 写 tag）。
  这不是矛盾 —— 写侧由另一个 ctor 入口（带 `useDataTypes` 的那一个）负责写头；
  `0x625CE0` 读、`0x625BE0` 写，都属于"头已由容器另行处理"的同构对。
  **对账以读侧为准：服务端带 1 位头 = 正确。**

---

## 4. 逐项对账表

| 段 | 服务端写 | 客户端读 | 判定 |
|---|---|---|---|
| ctor 头 | 1 bit = 1 | reader ctor 读 1 bit → `+0x21` | ✅ 一致 |
| 字段1 tag | 5 bit = 3 | `readTag(3)` | ✅ |
| 字段1 值 | 8 bit = 3 | `readBits(8)` | ✅ 长度=1B |
| 字段2 tag | 0x13/0x08/u32=67 | `readBlob(67)` 同序 | ✅ |
| 字段2 内容 | 67 B addr67 | 67 B → `msg[8]+0x18`，len→`+0x118` | ✅ |
| 字段3 tag | 0x13/0x08/u32=8 | `readBlob(8)` | ✅ |
| 字段3 内容 | 8 B sessionId (LE u64) | 8 B → `msg[8]+0x10` | ✅ |
| 字段4 tag | 0x13/0x08/u32=16 | `readBlob(16)` | ✅ |
| 字段4 内容 | 16 B securityKey | 16 B → `msg[8]+0x1CC` | ✅ |
| **尾部** | **4 bit 补零** | **不读**（`0x625CE0` 读完字段4即 ret） | ⚠️ **多余但无害** |

**没有**：长度不一致 / 顺序不一致 / 缺失 / 真多余字段。

---

## 5. 唯一差异（精确）

| 差异 | 位置 | 字节 | 影响 |
|---|---|---|---|
| 尾部补零 4 bit | payload 最后一字节高 4 位 | `…0x00`（109B 末字节=0x00） | 客户端 `0x625CE0` 读完 16B blob 即刻 `ret 4`，不检查剩余位；**无影响**。若外层容器对"整消息位长"做 `==872` 校验则会暴露，但 `0x634870`/`0x6371F0` 路径无此校验。 |

---

## 6. 客户端"期望"的下游佐证（同一 67B 块）

- `0xB95C50`（该消息被 `0x634870` 收下后调）`0xB95C8C cmp dword [ebx+0x118],0x43`
  ⇒ **硬性要求 67**（0x43）。服务端写 67 ⇒ 通过。
- `0xB750B0`（addr67 → 元素列表）`0xB75170/0xB7521C push 0x43` + `call 0xB756A0`：
  按 **bit 流**（`readBits(4)` 起步，`0xB77075 push 4`）解析 67 B，10 槽 + 尾。
  服务端 10×6B 槽（`00 FF 00 FF 00 00`）+ 尾部 7B（ip4+port2+nat1）符合"67=0x43"总长；
  槽内字节序（大端 ip、小端 port）与 `0xB77060` 的 4-bit 头 + 各槽字段一致（本卷只验总长/顺序，
  槽内位级字段见 191-216 卷线索，未作独立确证）。

---

## 7. 结论 / 证据 / 推翻或确认 / 仍开

**结论**
1. `build_startgame_payload` 与服务端两份调用点（`1131`、`1270`）输出的 109 B 位流，
   与客户端 `0x625CE0` **逐段完全对齐**（4 字段 + 1 位头），无缺失、无错序、无长度错。
2. 唯一多余是 `write_blob` 尾部 4 位补零；客户端不读，**无害**。
3. 因此：**若开局仍失败，故障不在 `build_startgame_payload` 本体**，而在
   ①位流被封装进 `build_room_push` 的**外层信封**能否被客户端解到本消息，或
   ②该消息被 `0x634870`/`0x6371F0` 分派前的**外层 tag3/u8** 协商，或
   ③`SEC_KEY` 的**内容**（长度对，值是 ECDH 派生的真值见 163/272 卷）。

**证据**（地址+指令+操作数）
- 服务端输出：`_r64_18/server_bytes.py` 位解码（868/872 位）
- 客户端：`0x625CE0` 全函数；`0x4F3EB0`（blob）；`0xB774E0`（tag5）；`0xB772E0`（bits LSB）；
  `0xB779A0`（1 位头→`+0x21`）；`0xB95C50`（`cmp [ebx+0x118],0x43`）；
  跳转表 `0x636F3C[3]=0x634AC2`；调用者 `0x634B2B`。

**推翻/确认旧卷**
- **确认** 177/178 卷"LSB-first 5 位标签 TLV、blob=13/08/u32/len"模型（本卷逐位复核）。
- **确认** 245 卷"`0x21` 是编解码总开关"：`0xB774F0` 处 `+0x21==0` 则跳过标签读取。
- **线索降级**：191-216 卷"MMI+0x18 256 字节" —— 本卷测得客户端把 67B 写到 `msg[8]+0x18`、
  容量字段在 `+0x118`、16B key 在 `+0x1CC`；与"256 字节"无直接冲突但**不依赖**该推断。

**仍开（明确的函数级任务）**
- T1：`build_room_push` 的**字节级**信封（`Buf(True)`：`08 08000000 0A … 10 … 13 08 len data …`）
  与客户端外层信封 reader（`0x7E7970`/`0x7F1060`/`0x6371F0` 的 11/4 unwrap）逐段对账——本卷未做。

**T2 已闭合（本卷补做）**：`0x634870` 入口 `[ebx+0x1C]!=0` 时先 `readTag(3)+readBits(8)` 得到的 u8
  **就是字段1（opcode）本身**：`0x6348D8 mov esi,[0x82E1458+eax*4]`（专用分派器，无则落 `0x636F3C[eax]`），
  随后 `0x6348D1 mov dword [edx+0x1c],1` **把位游标复位到 bit 1**，于是 `0x625CE0` 从同一位置
  **再读一遍** `readTag(3)+readBits(8)`。即：同一个 u8 既用于分派又被成员函数重读，服务端只写一次（=3）
  即满足两侧 ⇒ **不构成额外要求，与 §4 结论一致**。

