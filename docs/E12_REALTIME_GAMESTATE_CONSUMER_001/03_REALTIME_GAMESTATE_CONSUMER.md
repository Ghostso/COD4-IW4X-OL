# 03 — 实时 Gamestate `0x03` 消费者 / REALTIME GAMESTATE CONSUMER

> 等级：`PROVEN` / `INFERRED` / `BLOCKED`。

---

## 1. 结论

**实时 Gamestate `0x03` 消费者：未定位（BLOCKED）。**

已定位的 `0x03` 处理点属于 **demo/回放路径**（见 `01`），其字段序与服务端 `0xA21B8` 不匹配（见 `04`）。

## 2. 已定位的 `0x03` 处理点（DIRECT）

顶层分派器 `0x350170`（E-11 已证）：

```asm
350150  movzx eax, byte [ebp+0xc]
3501EF  dec eax
3501F5  cmp eax, 3
3501FA  jmp dword [eax*4 + 0x75025C]
```

| wire 值 | 目标 |
|---|---|
| 1 | `0x350040` |
| 2 | `0x34FD80(0)` |
| **3** | **`0x34FD80(1)`** |
| 4 | `0x3547D0` |

**`0x03` → `0x34FD80(arg=1)`（DIRECT）。**

## 3. `0x34FD80` 读取序列（DIRECT）

```asm
34FDB0  call [edi+0x89244]  len=4        ; f0 = dword
34FDC4  cmp byte [ebp+0xc],0
34FDD0  call [edi+0x89244]  len=4        ; f4 = dword（仅 arg=1 分支）
34FE3F  call [edi+0x89244]  len=4        ; f8 = length
34FE81  cmp eax,0x20000                  ; 上限检查
34FE8D  push 0xCD637C                    ; 超限报错
34FEAC  call [edi+0x89244]  len=f8       ; 载荷
34FEB7  cmp [ebp-0x20034],4
34FED4  call 0x1AC1D0       len=4        ; 内嵌 dword
34FF39  ... 写入 [esi+0x4231F8] ...
350024  call 0x751D00
```

**字段序（DIRECT）：** `{i32 f0, i32 f4, u32 len, len bytes}`。

## 4. 与服务端 `0x03` 体的冲突（DIRECT，REFUTED 匹配）

服务端 `_CODOL2697_WriteGamestate` `0xA21B8`：

```asm
0A224C  WriteByte(3)
0A225A  WriteInt32(version)          ; i32
0A2269  WriteLenStr(map)             ; cstring
0A2279  WriteLenStr("mp")            ; cstring
0A2288  WriteInt32(field4)           ; i32
0A22C1  call WriteConfigstrings      ; 0x04 ... 0x06
0A22D9  WriteInt32(fieldC)
0A22E8  WriteInt32(field8)
0A22F8  WriteByte(6)
```

| 位置 | 服务端 | 客户端 `0x34FD80(1)` | 匹配 |
|---|---|---|---|
| 1 | `i32` | `i32` | 宽度同，语义未证 |
| 2 | `cstring` | `i32` | **冲突** |
| 3 | `cstring` | `u32 len` | **冲突** |
| 4 | `i32` | `payload` | **冲突** |

**结论（REFUTED）：** `0x34FD80(1)` **不是** `0xA21B8` 的消费者。两者字段序直接冲突。

## 5. 上游路径归属（DIRECT）

`0x34FD80` 的唯一调用者是 `0x350170`（`0x350204`/`0x350217`），而 `0x350170` 的归属为 demo（`01` §3–§6）。

**因此 `0x03` → `0x34FD80(1)` 属 demo 路径。**

## 6. 实时消费者候选（INFERRED，未证实）

| 候选 | 依据 | 状态 |
|---|---|---|
| 收包函数（§`02`）的下游 | 底锚 PROVEN，但下游边 BLOCKED | BLOCKED |
| `0xA2E50`（reliable payload） | 直接调用者 **0**；数据指针引用 **0** | BLOCKED（历史已记） |
| `0x6D340`/`0x6D5D0` | 读位 + 调 `0xA2480`；上游 `0x6F2F0` | 未证属实时 |
| `0x6E060` | 多次 `MSG_ReadData` | 未证属实时 |

**纪律：** 不使用“用了 `MSG_ReadBits`/`MSG_ReadData`”作为消费者判据。

## 7. 裁定

| 项 | 裁定 |
|---|---|
| 顶层分派器与 `0x03` → `0x34FD80(1)` | **PROVEN** |
| `0x34FD80(1)` 归属 demo | **INFERRED（强）**（经 `0x350170`） |
| 实时 `0x03` 消费者 | **BLOCKED** |
| 实时消费者与服务端字段匹配 | **BLOCKED**（无候选可比） |
