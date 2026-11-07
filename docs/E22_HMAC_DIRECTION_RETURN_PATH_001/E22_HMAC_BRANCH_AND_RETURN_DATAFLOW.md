# E22 HMAC 分支与返回数据流

## 字符串引用归因

| 字符串 | 引用点 | 实际条件 |
|---|---|---|
| Bad frame/payload size | 0x6AAF8E | 长度/对齐检查失败 |
| Bad recv counter | 0x6AAFBD | 计数器比较失败 |
| HMAC calculation | 0x6AB0C2 | 进入 HMAC 比较前的错误标签 |
| HMAC mismatch | 0x6AB131 | 16 字节比较失败 |

这证明四个字符串均由 `0x6AAE70` 直接引用，而不是泛泛的邻近字符串。

## 分支结构

```asm
; 长度/帧检查
6AAF49  test cl,cl
6AAF4B  je   0xAAAF56
6AAF4D  cmp  ebx,8
6AAF50  jbe  0xAAAF56
...
6AAF88  mov bl,1
6AAF8A  jmp 0xAAAF98
6AAF8C  xor bl,bl
6AAF8E  mov [ebp-0x218],0xC5B124   ; Bad frame/payload size
```

```asm
; 接收计数器检查
6AAFA4  mov eax,[edi+0x5D0]
6AAFAA  lea edx,[eax+1]
6AAFAD  mov [edi+0x5D0],edx
6AAFB3  cmp [ebp-0x224],eax
6AAFB9  je  0xAAAFFD
6AAFBB  xor bl,bl
6AAFBD  mov [ebp-0x218],0xC5B110   ; Bad recv counter
```

```asm
; HMAC 比较
6AB0C2  mov [ebp-0x218],0xC5B0FC   ; HMAC calculation
...
6AB12D  je  0xAAB140
6AB12F  xor bl,bl
6AB131  mov [ebp-0x218],0xC5B0EC   ; HMAC mismatch
```

## 比较语义

`0x6AB0E6..0x6AB12D` 是 16 字节的比较循环，使用 XOR/OR 聚合差异：

```asm
6AB0E9  movzx ecx, byte [ebp-0x2B]
6AB0ED  xor cl, ah
6AB0EF  mov dl, al
6AB0F1  xor dl, byte [ebp-0x2C]
...
6AB12B  or dl, cl
6AB12D  je 0xAAB140
```

匹配成功进入 `0xAAB140`；失败设置 `HMAC mismatch` 并跳转到错误路径。

## 返回路径

- 失败到 `0xAAAFCD` 调日志 `0x43A7C0`，再调 `0xAAA770` 置连接状态 4。
- 成功继续到 `0xAAB140` 之后，使用 `[edi+0x5F4]` 的虚表 +0xC 调用。
- `0x6AAE70` 最终 `0x6AAFFA ret 0x14`，返回 AL。

## 证据等级

| 主张 | 裁定 |
|---|---|
| 4 个字符串由 0x6AAE70 直接引用 | PROVEN |
| 计数器和连接状态在失败时更新 | PROVEN |
| 存在 16 字节比较 | PROVEN |
| 该比较是 HMAC | STRONG_INFERENCE（字符串 + 16 字节比较 + 状态失败路径） |
| 方向为入站 | INFERRED（强） |
| 方向为出站 | 弱支持，未排除 |
