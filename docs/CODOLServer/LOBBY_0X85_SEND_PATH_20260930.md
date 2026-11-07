# 0x85 发送侧路径追加逆向（2026-09-30）

来源：可读运行期镜像
`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`。

这次读的是**发送侧**（客户端发出 0x85 的路径），不是此前的接收校验器
`0xBA3710`。两者不能混为一谈。

---

## 1. 发送函数入口

发送函数从 `0xBA1850` 开始（栈帧约 `0x520` 字节）。它先构造一系列
`0xAB` 类型业务帧：`0x81`、`0x82`，随后继续构造后续帧。

公共帧写入器是 `0xB78350`，调用形态反复出现：

```asm
push <payload/len/flags>
push 0x44A                 ; 发送缓冲上限 1098
push &frame_buffer         ; [ebp-0x4F4]
call 0xB78350
```

帧 opcode 写入栈字节 `[ebp-0x4FD]`：

```asm
0xBA18DE  mov byte [ebp-0x4F5], 0xAB
0xBA1D3F  mov byte [ebp-0x4FD], 0xAB
0xBA1D79  mov byte [ebp-0x4FD], 0x81
```

这段负责早期握手/业务帧组装；实际 0x85 的发送分支在后续状态条件内，
但其哈希辅助链已经明确出现。

---

## 2. 发送侧的 keyed-SHA1 辅助链

### 2.1 `0xBA0D20` 是通用 keyed-SHA1 helper

完整形态：

```asm
0xBA0D20  call 0xC73800       ; init，key 指针，长度 0x14
0xBA0D72  call 0xC73760       ; update，message 指针 + 长度
0xBA0D9B  call 0xC737A0       ; final，输出 20B
```

它的四个参数按调用约定是：

```
arg1 = key/message context input
arg2 = message pointer
arg3 = message length
arg4 = output buffer
```

算法 provider 为 `sha1`，输出长度固定 20 字节。

### 2.2 发送函数在 `0xBA1E96` 调用它

```asm
0xBA1E72  call 0xBA0750
          ; 写出 24 字节到 [ebp-0x38]

0xBA1E88  lea ecx,[ebp-0x4C]
0xBA1E8C  push ecx
0xBA1E8E  push 0x18
0xBA1E91  lea edx,[ebp-0x38]
0xBA1E95  push edx
0xBA1E96  lea eax,[ebp-0x60]
          push eax
          call 0xBA0D20
```

因此该调用的实参语义为：

```
key     = [ebp-0x60]       20B
message = [ebp-0x38]       24B
length  = 0x18              24
output  = [ebp-0x4C]       20B
```

⇒ 发送侧至少存在一个**20B keyed-SHA1 over 24B message**的中间结果。

### 2.3 `0xBA13D0` 继续变换该 20B 结果

紧接着：

```asm
0xBA1EDF  push 0x10
0xBA1EE1  lea ecx,[ebp-0x20]
0xBA1EE5  push 0x0A
0xBA1EE7  push 0xD5A4E8
0xBA1EEC  lea edx,[ebp-0x4C]
0xBA1EEF  push edx
0xBA1EF2  push 0x14
          call 0xBA13D0
```

`0xBA13D0` 的约束检查明确要求输入长度 `0x14`，输出长度/上限为 `0x10`，
并使用常量 `0xD5A4E8` 附近的 10 字节参数。它不是简单的 HMAC，
而是对 20B keyed-SHA1 结果再做一层自定义转换，输出 16B 中间材料。

⇒ 这解释了为什么直接把 20B HMAC 当作 0x85 末尾 tag 仍未命中：
**发送侧还存在 `BA13D0` 的二次变换**。

---

## 3. 与接收侧 `0xBA3710` 的关系

接收校验器：

```
0xBA3710 -> BA02A0 -> C73800/60/A0 -> 比对末 20B
```

发送侧：

```
0xBA1850 -> BA0D20(key20, 24B) -> BA13D0(20B -> 16B) -> 组帧
```

这两条链共享 SHA1/provider，但**不是同一个简单公式**。此前用
`HMAC-SHA1(key, frame_slice)` 直接试算真实 0x85 帧不命中，是预期结果：
发送侧还有 `BA13D0` 与自定义 24B message 构造。

---

## 4. 下一步

1. 读完整 `0xBA0750`：恢复发送侧 24B message `[ebp-0x38]`；
2. 读完整 `0xBA13D0`：恢复 20B→16B 的最终转换；
3. 追 `0xBA1E30` 分支到实际 opcode `0x85` 的组帧调用；
4. 用客户端实际发出的 386/194/468 字节帧逐字节回验。

---

## 4A. 发送 0x85 的实际组帧分支（本轮追加）

在 `0xBA2A60` 起的发送/队列函数中，状态门是：

```asm
0xBA2B5D  cmp [ebx+0xC8],2
0xBA2B6A  cmp [ebx+0x5E8],3
```

满足后进入 0x85 组帧：

```asm
0xBA2B77  mov ecx,[ebp+8]                 ; 源流对象
0xBA2B9B  call 0xB9BB90
0xBA2BA3  call 0xB9BBB0
0xBA2BB8  mov edi,eax                     ; message 指针
0xBA2BBE  call 0xB962E0                   ; 解析/准备消息
0xBA2BEF  mov byte [ebp-0x371],0xAB       ; 外层类型
0xBA2BF6  call 0xB78490
0xBA2C1A  mov byte [ebp-0x371],0x85       ; ★ opcode 0x85
0xBA2C21  call 0xB78490                   ; ★ 写出 0x85 帧
```

随后计算摘要：

```asm
0xBA2D88  call 0xBA0420(ecx=ebx, mode=0, out=&[ebp-0x24])
           ; 生成 24B 变换结果，前 20B作为 keyed-SHA1 key
0xBA2DA1  call 0xC73800(ctx, &[ebp-0x24], 0x14)
0xBA2DED  call 0xC73760(ctx, edi, [ebp-0x384]-8)
0xBA2E20  call 0xC737A0(ctx, output, len=8)
```

更精确地说，发送侧的 keyed-SHA1 输入是：

```
key     = first 20 bytes of BA0420(connection_object, mode=0)
message = [B9BBB0(source_stream)]
length  = [ebp-0x384] - 8
output  = final digest written into the frame-building area
```

这解释了为什么此前拿 `obj+0x620` / 收到的帧整体直接做 HMAC 没命中：
**发送侧 0x85 使用 `BA0420(obj+0x60D)` 生成的第二套 codec 结果作为 key，
消息长度还要减 8；不是简单的 `HMAC(key20, frame_body)`。**

## 4B. 第二套 codec `0xBA0420`

它与 `0xBA02A0` 不同：

```
source base = object + 0x60D
block count = 4
stride      = 6 bytes
output      = 24 bytes
```

常量表（由 `0xBA044C..0xBA0468` 读出）为：

```
ad42f590 88a421e6 3bc98902 39ff02dc
110477ff ee88620d
```

因此现有服务端只修正 `0xBA02A0` 仍然不够；发送侧 0x85 还必须复刻
`BA0420(obj+0x60D)`、`B9BBB0(source)` 与 `length-8` 的链。

---

## 4C. 发送 0x85 的真实入口已进一步定位到 `0xBA2A60`

`0xBA2A60` 是由多个上层状态函数调用的发送分派器。其入口条件：

```asm
0xBA2A5D  cmp [obj+0xC8],2
0xBA2A6A  cmp [obj+0x5E8],3
```

满足大厅阶段后：

```asm
0xBA2B77  ecx = [ebp+8]              ; source stream object
0xBA2B7A  esi = align16([ebp+0xC]+0x14)
0xBA2B9B  call 0xB9BB90              ; 设置 stream 的窗口上限
0xBA2BA3  call 0xB9BBB0              ; 取当前 stream offset
0xBA2BB8  edi = eax                  ; 当前消息游标/偏移
0xBA2BBE  call 0xB962E0              ; 读取/校验 0x1F 字节头
0xBA2BEF  frame_type = 0xAB
0xBA2BF6  call 0xB78490
0xBA2C1A  opcode = 0x85
0xBA2C21  call 0xB78490              ; 写 0x85 帧
```

随后：

```asm
0xBA2D8E  call 0xBA0420(obj, mode=0, out=&20B)
0xBA2DA1  call 0xC73800             ; keyed SHA1 init
0xBA2DED  call 0xC73760             ; update(edi, [ebp-0x384]-8)
0xBA2E20  call 0xC737A0             ; final
```

`B9BB90/B9BBB0` 的含义也已读出：

```asm
B9BB90: [stream+0x24] = min(requested, 0x1F)
B9BBB0: return [stream+0x1C] - [stream+0x24] + 0x1F
```

⇒ 发送侧的 message 并不是简单的"0x85 帧 body"，而是由 stream object 的
`+0x1C/+0x24` 窗口计算出的**游标/偏移**，再经 `B962E0` 取出；这解释了此前
所有按帧整体做 HMAC 的试算均不命中。

---

## 5. 边界

本报告来自离线反汇编；未注入、未下断点、未修改 `.text`、未触碰 ACE/TenProtect。
