# 06 — D1:P5 消费循环启动者与缓冲追踪

**目标:** 围绕 `0x7A41D0` 确认函数边界、调用者/启动者、输入来源、以及它处理的是 socket 数据还是已解析数据。
**映像:** S-IMG `17cef6e0…f045`;`RVA = VA - 0x400000`。
**证据:** `evidence\d40..d45`、`evidence\049_analysis.json` → `d1_p5_consumer`。

---

## 1. 函数边界(确认)

| 项 | 值 |
|---|---|
| 入口 | `0x7A41D0`(`55 8B EC`,标准 prologue) |
| 直接调用者 | `0x7A4491`(`call`) |
| dword 指针引用 | **0** |
| 门控字段 | `[esi+0xC8] == 2` |
| 状态字段 | `[esi+0x9C]` 0..3,跳转表 VA `0x00BA4400` |
| 返回 | `ret`(无参) |

## 2. 启动者/调用链(本轮新闭合)

```
0x7A41D0  P5 消费循环
  ▲ call 0x7A4491
0x7A4430  消息驱动/分派(含 recv 分支与 opcode-ish 字节分支)
  ▲ jmp  0x7A47E4
0x7A47E0  thunk: push ebp; mov ebp,esp; pop ebp; jmp 0x7A4430
  ▲ call 0x78395F
0x7838A0  P5 per-tick driver
  ▲ callers: 0x0A648C, 0x3F3826, 0x4037B8
```

**结论:**
- `0x7A47E0` 是纯 thunk(5 字节后即 `jmp 0x7A4430`),不是新逻辑。
- `0x7838A0` 是 **P5 per-tick driver**:它按 tick 调用 thunk → 分派 → 消费循环,
  并在 `0x78392C` 检查 `[esi+0x4F4]`,再于 `0x78395F` 调用。
- **无 dword 指针引用** → 该循环**不是**经 vtable/函数指针表注册启动的,而是被 `0x7838A0`
  **直接 `call`**。这回答了 048 `04` §6 的"启动者不明":启动者 = `0x7838A0` 的调用者
  `0x0A648C / 0x3F3826 / 0x4037B8` 所在的上层 tick 系统。

## 3. 输入队列/缓冲区如何初始化

- `0x7A41D0` 的 `[esi+0xB0]`、`[esi+0xB4]` 是被管理的缓冲区/对象指针
  (`0x7A4236`/`0x7A4266` 处释放、`0x7A421E`/`0x7A424E` 处检查);
- 状态 `[esi+0x9C]` 的 4 分支分别调用 `0x7A3FB0` / `0x7A0AF0` / `0x7A0A20` / `0x7A20A0`;
- **`0x7A20A0` 直接调用 P5 `recv` 包装 `0x873A00`**:
  ```
  007A20C8  mov esi, ecx
  007A20CC  lea edi, [esi+0xA8]        ; 缓冲
  007A20D2  push edi
  007A20D3  lea ecx, [esi+0xC4]        ; this(对象首字段= socket)
  007A20D9  call 0x873A00              ; Recv(buf=[esi+0xA8], len)
  ```

## 4. 它处理的是 socket 数据还是已解析数据?

- **输入侧**:`0x7A20A0` 直接调 `recv`,故 **P5 循环的输入是 socket 原始字节**。
- **解析侧**:`0x7A4430` 内:
  ```
  007A44D8  call 0x7765A0            ; 读 1 字节 → [ebp-0xE]
  007A44F3  mov al, [ebp-0xE]
  007A44F6  cmp al, 0x81             ; → handler 0x7A3C70
  007A4557  cmp al, 0x83             ; → handler 0x7A3BA0
  007A45F0  cmp al, 0x84             ; → handler 0x7A0E20
  007A46AE  cmp al, 0x85             ; → handler 0x7A3710
  ```
  并由 `[esi+0x5E8]`(值 1/2/3)门控。
- **判定:** P5 循环处理的是**socket 原始字节**,且存在"**读 1 字节 → 按字节值分支**"的指令点。
  **但**:该字节经 `0x7765A0` 读取,`0x7765A0` 的 `arg1`(缓冲)来源**尚未**与 §3 的
  `recv` 缓冲建立指令级连接。

## 5. `0x7765A0` 读字节器

```
007765A0  push ebp; mov ebp,esp; push ecx
007765A4  mov ecx, [ebp+0x14]
007765A7  mov edx, [ebp+0x10]
007765AA  push 1
007765AC  lea eax, [ebp-1]
007765AF  push eax
007765B0  mov eax, [ebp+0xC]
007765B3  push ecx
007765B4  mov ecx, [ebp+8]
007765B7  push edx
007765B8  push eax
007765B9  push ecx
007765BA  call 0x7783C0                             ; 通用 1 字节读取(缓冲游标读)
007765C2  test al,al
007765C6  mov edx, [ebp+0x18]
007765C9  mov cl, [ebp-1]
007765CC  mov [edx], cl                            ; 写出读取到的字节
```
- `0x7765A0` 是**薄包装**:委托给 RVA `0x7783C0`(VA `0x00B783C0`),
  读取长度=1,并把结果写到 `arg6`。`0x7783C0` 有 10+ 个调用者,是通用缓冲游标读原语(带边界检查)。
- 这是**读取原语**,不是协议分派器;因此 §4 的字节分支属于**读之后**的消费者。

## 6. 最后已证实节点 / 第一个未证实节点

| 链 | 最后已证实节点 | 第一个未证实节点 |
|---|---|---|
| P5 启动 | `0x7A41D0` ← `0x7A4430` ← thunk `0x7A47E0` ← **driver `0x7838A0`** | driver 之上(`0x0A648C/0x3F3826/0x4037B8`)所属 tick 系统未定性 |
| P5 收包 | `0x7A20A0` 内 `call 0x873A00`(`recv(sock,buf,len)`) | `recv` 缓冲 `[esi+0xA8]` 与 `0x7765A0` 的 `arg1` 是否同一缓冲 —— **未证** |
| 字节分支 | `0x7A44F6/0x7A4557/0x7A45F0/0x7A46AE` 的 `cmp al,0x81/0x83/0x84/0x85` | 这些字节值的**线上语义**(opcode 名/字段布局)—— **未证** |

**最小未闭环边:** `recv` 缓冲 → `0x7765A0` 输入缓冲。这是 `10` 的 050 唯一优先目标。

## 7. 口径纪律

- 未把"存在 `cmp al,0x81`"写成"opcode 0x81 已确认"。字节值的**分支存在**是直接的;
  其**协议语义**是未证的。
- 未把 driver 之上未定性的 tick 系统当作 P5 的协议入口。
- 未把 `0x7765A0` 的调用当作"分派点";它是读取原语。


## 8. 新增:调用点实参与会话字段(为 050 铺路)

`0x7A44D8` 调用 `0x7765A0` 前的实参装配(逐条直接指令):

```
007A44AD  mov ecx, [esi+0xB0]     ; 缓冲对象指针
007A44B3  call 0xB9BBB0           ; 取数据指针 → eax
007A44B8  mov edi, [esi+0xAC]     ; 长度字段
007A44BE  mov ebx, eax
007A44C0  lea eax, [ebp-0xE]      ; &byte
007A44C3  push eax
007A44C4  lea ecx, [ebp-0x14]     ; &count
007A44C7  push ecx
007A44C8  push 0
007A44CA  dec edi                 ; len-1
007A44CB  push edi
007A44CC  push ebx                ; data ptr
007A44CD  mov byte [ebp-0xE], 0
007A44D1  mov dword [ebp-0x14], 0
007A44D8  call 0x7765A0
```

- **`0x7765A0` 的输入缓冲 = `[esi+0xB0]` 经 `0xB9BBB0` 取得的数据指针,长度 = `[esi+0xAC]-1`。**
- `0x7A41D0` 内对同一会话对象字段的读写集中在 `0x7A4211..0x7A4278`:
  `[esi+0xA8]`(字节标志)、`[esi+0xAC]`(长度)、`[esi+0xB0]`/`[esi+0xB4]`(两个缓冲对象指针)。
- **重要限制:** `0xB9BBB0` 与调用 `0x7765A0` 的 `[esi+0xB0]` 数据来源,以及 `0x7A20A0`
  里 `recv` 用的 `[esi+0xA8]` 缓冲,是否**同一**字段/同一底层缓冲,**本轮未证**。
- **映像缺口:** `0xB9BBB0` 的 RVA `0xB9BBB0` **超出**恢复映像(0xA65000)→ 该函数体不可读,
  只能记录调用关系,不能解码其实现。这与 `08` 的第 3 节区缺口同源(第 3 节起始 `0xA16000`,
  映像只到 `0xA65000`;`0xB9BBB0` 落在第 3 节未展开部分)。

**给 050 的直接线索:** 检查 `0x7A20A0` 的 `recv` 缓冲 `[esi+0xA8]` 与
`0x7A44AD` 的 `[esi+0xB0]` 是否指向同一会话对象的同一缓冲(注意两者偏移不同:`0xA8` vs `0xB0`,
且 `0xAC` 是长度字段)——这是最小未闭环边的**具体候选**。
