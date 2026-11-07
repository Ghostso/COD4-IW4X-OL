# `dwRoomMessageManifold::serialize` 逐指令（位流格式）

> **这是房间消息线格式的真正起点**
> 证据：`client_runtime.bin`，`0x625520` 起

---

## 1. 函数开头（`0x625520`–`0x62557B`）

```asm
0x625520  push ebp / mov ebp,esp / and esp,0xfffffff8
0x625526  sub esp, 0x24
0x625529  push ebx / push esi
0x62552b  mov esi, [ebp+8]           ; 参数：输出缓冲对象
0x62552e  mov ebx, [esi]             ; ebx = 位流写入器
0x625530  push edi
0x625531  mov edi, ecx               ; edi = this（消息对象）
0x625533  mov al, [edi+4]            ; ★ 字段 +0x4（1 字节）
0x625536  push 3
0x625538  mov ecx, ebx
0x62553e  mov [esp+0x14], al
0x625542  call 0xb77b10              ; ★ writeBits(3)
0x625547  push 8
0x625549  lea ecx, [esp+0x14]
0x62554d  push ecx
0x62554e  mov ecx, ebx
0x625550  call 0xb777c0              ; ★ writeData(&field+4, 8)
```

### 输出 1：`[edi+4]` 的 1 字节

```
writeBits(3)              ; 写 3 位（可能是类型码）
writeData(&[edi+4], 8)    ; 写 8 位（1 字节）
```

**⇒ 每个消息开头是：`3 位类型码` + `1 字节字段`。**

---

## 2. 第二段（`0x625555`–`0x625578`）

```asm
0x625555  mov ebx, [esi]
0x625557  mov edx, [edi+0x10]        ; ★ 字段 +0x10（4 字节）
0x62555a  push 8
0x62555e  mov [esp+0x1c], edx
0x625562  call 0xb77b10              ; writeBits(8)
0x625567  mov eax, [esp+0x18]
0x62556b  push 0x20
0x62556d  lea ecx, [esp+0x20]
0x625571  push ecx
0x625574  mov [esp+0x24], eax
0x625578  call 0xb777c0              ; ★ writeData(&field+0x10, 0x20)
```

### 输出 2：`[edi+0x10]` 的 4 字节

```
writeBits(8)                  ; 写 8 位
writeData(&[edi+0x10], 0x20)  ; 写 32 位（4 字节）
```

**⇒ 这是一个"8 位标签 + 32 位值"的字段。**

---

## 3. 与 `StartGame` 的对照

**`memory: codol-dwroom-protocol-reversed` 记录 `StartGame::serialize`（`0x625be0`）：**

```
writeBits(3)              ; 类型 ID
writeData(&byte, 8)       ; 1 字节
writeBits(0x13)           ; 19
writeBits(8)              ; 8
writeData(&val, 0x20)     ; 4 字节
writeData(&[eax+0x18], edx*8)  ; 变长块
...
```

**⇒ `Manifold` 与 `StartGame` 的前两句完全相同！**

```
writeBits(3)  +  writeData(8)
writeBits(8)  +  writeData(0x20)
```

**⇒ 这是所有 `dwRoomMessage` 共同的**消息头**。**

---

## 4. ★ 消息头的统一格式

```
偏移  位     内容
0     3      类型码（写死的 3）
3     8      消息版本/标志（[obj+4]）
11    8      字段标签（写死的 8？）
19    32     第一个字段值（[obj+0x10]）
```

**总长 51 位 = 6.375 字节。**

**⇒ 每个消息至少带 2 个字段：一个 1 字节、一个 4 字节。**

---

## 5. 与语料的对照

**`11/4` 的 blob 里：**

```
02 <组数> 00 00 | 00 <值> 00 00 | ...
```

**`02` 是 1 字节，`<组数>` 是 1 字节。**

**⇒ 如果按位读：**

```
0x02 = 0000 0010
0x04 = 0000 0100
```

**前 3 位 = `000` = 0（不是 3）。**

**⇒ `11/4` 不是 `Manifold` 的位流，或者起点不在 `02`。**

**⇒ `11/4` 可能是"已解包的字段序列"，不是原始位流。**

---

## 6. 这意味着什么

**`11/4` 的 blob 里那 145 个恒定字节，
可能是"某个消息序列化后的**字节对齐**结果"。**

**⇒ 位流写完后会被填充到字节边界，
所以看起来像"字节字段"。**

**⇒ 需要按位重新切分才能看到真正的结构。**

---

## 7. 下一步

1. 按位解析 `11/4` 的 blob（从 bit 0 开始，3 位类型码）
2. 如果前 3 位是 0，说明不是 `dwRoomMessage` 系列
3. 确认 `11/4` 到底是不是 `Manifold`

---

## 8. 已确定的部分

| 项 | 值 |
|---|---|
| 位流写入器 | `0xb77b10`（writeBits） |
| 位流数据写 | `0xb777c0`（writeData） |
| Manifold serialize | `0x625520` |
| 消息头格式 | `3 位 + 1 字节 + 8 位 + 4 字节` |
| 消息字段位置 | `[obj+4]`、`[obj+0x10]` |
