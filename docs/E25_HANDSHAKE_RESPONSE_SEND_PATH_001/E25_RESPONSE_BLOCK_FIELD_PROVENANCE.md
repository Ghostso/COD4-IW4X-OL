# E25 应答数据块字段来源

## 1. 更正：`0x6ABAAA` 操作的不是内存块而是序列化器

```asm
6ABA25  push 0x1c
6ABA27  call 0x0DF9AA45         ; 分配 0x1C
6ABA2C  add esp,4
6ABA3D  mov ecx,[ebp-0x17c]     ; 长度来自 [ebp-0x17c]
6ABA43  add ecx,6
6ABA46  push 0                ; arg2 (flag)
6ABA48  push ecx              ; arg1 (initial size = [ebp-0x17c]+6)
6ABA49  mov ecx,eax
6ABA4B  call 0x0DAB40         ; <== 序列化器构造器 (RVA 0xDAB40)
6ABA50  mov ebx,eax           ; ebx = 序列化器
...
6ABAAA  call 0x0DF6F97C        ; (ecx=ebx) 追加字段：arg 来源 [esi+0x10]/[esi+8]
6ABABB  call 0x0DF6F97C        ; (ecx=ebx) 追加 8 字节：[ebp-0x38]
```

序列化器构造器 `0x0DAB40`（VA `0x4DAB40`）实测：

```asm
0DAB4B  mov cl,[ebp+0xC]        ; flag
0DAB4E  mov dword ptr [esi],0xCBBD1C
0DAB57  mov dword ptr [esi],0xCBBD24   ; <== node/serializer vtable
0DAB5D  mov dword ptr [esi+8],eax      ; 声明容量
0DAB63  mov byte ptr [esi+0x18],cl
0DAB70  push eax; call 0x0DF9AA45      ; 分配缓冲区
0DAB79  mov dword ptr [esi+0xC],eax    ; <== 字节缓冲
0DAB83  mov dword ptr [esi+0x14],eax   ; 写游标
0DAB86  mov dword ptr [esi+0x10],eax   ; 读游标
```

因此 `[esi+8]`、`[esi+0x10]`、`[ebp-0x38]` **不是**"被写入的数据字段"，而是**喂给序列化器 `0xDF6F97C` 的参数**。

## 2. 逐项来源

| 位置 | 来源（指令） | 类型 | 说明 | 等级 |
|---|---|---|---|---|
| `esi` | `0x6AB3DC mov esi,[ebp-0x17c]` / `0x6AB42A mov esi,eax` | 对象指针 | 由 `0x6AB3F6..0x6AB425` 构造（长度 `[ebp-0x17c]`+0） | PROVEN |
| `[esi+8]` | `0x6ABAA3 mov ecx,[esi+8]` | 指针/句柄 | 作为追加字段的载荷指针（第一参数） | PROVEN（读取） |
| `[esi+0x10]` | `0x6ABAA0 mov eax,[esi+0x10]` | 长度/计数 | 作为追加字段的第三参数（长度） | PROVEN（读取） |
| `[ebp-0x38]` | `0x6ABAB3 lea ecx,[ebp-0x38]` | 内联 8 字节 | 追加 8 字节字段（`push 8`） | PROVEN |
| `ebx` | `0x6ABA50 mov ebx,eax` ← `0x4DAB40` | 序列化器 | 字节缓冲为 `[ebx+0xC]`，长度 `[ebx+0x10]` | PROVEN |

`esi` 的构造（`0x6AB3F6..0x6AB42C`）：

```asm
6AB3F6  push 0x24
6AB3FB  mov byte ptr [ebp-0x172], 7
6AB402  call 0xDF9AA45         ; 分配
6AB41C  lea ecx,[ebp-0x172]
6AB425  call 0xDECFC0E         ; 构造（长度来自 [ebp-0x172]）
6AB42A  mov esi, eax
```

即 `esi` 是"长度取自 `[ebp-0x17c]`"的缓冲对象；`[esi+8]`/`[esi+0x10]` 是该对象的数据/长度字段。

## 3. `ebx`（序列化器）的字节缓冲

`0x320E30` 的同类对象给出节点/缓冲结构（`0x6AA230` 用它克隆）：

```asm
6A97E9  mov dword ptr [esi],0xCBBD1C     ; 基类 vtable
6A97F6  mov dword ptr [esi],0xC5B0E0     ; pair 派生 vtable
6A97FC  mov dword ptr [esi+8],eax        ; 关联对象
6A9810  mov ecx,[eax+0xC]                ; <- 数据指针复制来源
6A9816  mov dword ptr [esi+0xC],ecx
```

而 `0x320E30`（clone 0x1C 节点）：

```asm
6A… 320E48 mov dword ptr [esi],0xCBBD24  ; node vtable
     320E4E mov dword ptr [esi+8],edi     ; 长度
     320E61 push edi ; call 0xDF9AA45     ; 分配 len 字节
     320E6D mov dword ptr [esi+0xC],eax   ; 缓冲指针
     320E74 call 0xB4FF60                 ; memcpy(buf, src, len)
     320E7F mov dword ptr [esi+0x14],eax  ; 写游标
     320E82 mov dword ptr [esi+0x10],eax  ; 读游标
```

**裁定**：`[ebx+0xC]` = 序列化后的字节缓冲；`[ebx+0x10]`/`[ebx+0x14]` = 读/写游标。长度由序列化器累积。

## 4. 与 `CLIENTCHAL`/`BDDATA`/消息码的关系

| 项 | 关系 | 等级 |
|---|---|---|
| `CLIENTCHAL`（VA `0xC5B144`） | `0x6AB8C4` `push 0xC5B144` 作为 `0x6AA9CE0` 的字段值 → 进入协商输入字段区，**不在此序列化器调用点** | INFERRED（强） |
| `BDDATA`（VA `0xC5B13C`） | `0x6AB906` `push 0xC5B13C` 同上 | INFERRED（强） |
| 消息码 `0x81` | `0x6AB66D mov byte [ebp-0x171],0x81`，经 `0xA87830` 写入缓冲 | PROVEN（写入）/ 语义 BLOCKED |
| 消息码 `0x83/0x84/0x85` | 与 `0x6AB310` 应答序列化器**无直接数据流** | REFUTED（同一函数内不存在） |

## 5. 未闭合

- `[esi+8]`/`[esi+0x10]` 指向的缓冲**内容**未逐字节解码。
- `[ebp-0x38]` 的 8 字节字段语义未定。
- 序列化器 `0x4DAB40` 与 `0xDF6F97C` 的字段序未展开。

## 6. 实际传给 `0x6AA230` 的两个参数（决定性）

```asm
6ABAD2  mov ecx, ebx
6ABAD4  call 0xDF16878          ; 取序列化状态（返回值用于成功判定）
6ABAD9  cmp byte ptr [ebp-0x172],0
6ABAE0  je  0xAABB0D
6ABAE2  mov edx, dword ptr [ebx+0xC]   ; data0 = 序列化字节缓冲指针
6ABAE7  mov dword ptr [ebp-0x18C], edx
6ABAED  call 0xDF16878                 ; data1 = 序列化字节数（返回值）
6ABAF2  push eax                       ; arg2 = data1（长度）
6ABAF3  mov eax, dword ptr [ebp-0x18C]
6ABAF9  push eax                       ; arg1 = data0（缓冲指针）
6ABAFA  mov ecx, edi                   ; this = 会话对象
6ABAFC  call 0x6AA230
```

在 `0x6AA230` 内：

```asm
6AA267  mov ebx, dword ptr [ebp+0xC]   ; ebx = data1 = 长度
6AA273  mov ecx, dword ptr [ebp+8]     ; ecx = data0 = 缓冲指针
6AA276  push esi                       ; arg3 = 0
6AA277  push ebx                       ; arg2 = 长度
6AA278  push ecx                       ; arg1 = 缓冲指针
6AA27B  call 0x320E30                  ; clone(node, buf, len, 0)
```

→ `data0` = **缓冲指针**，`data1` = **字节长度**。两者一起被 `0x320E30` 复制进新节点（`memcpy(node+0xC, data0, data1)`）。**等级：PROVEN。**
