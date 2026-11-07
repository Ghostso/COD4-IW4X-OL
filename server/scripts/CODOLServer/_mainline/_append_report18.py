"""Append section 18 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 18. 复位机制定位：`0xBA34D0` 的超时分支（2026-09-29，静态反汇编）

本轮放弃了「再加一个偏移 - 实跑」的循环，改为先把复位真正读透。
结论是**此前对复位点的判断错了两处**。

### 18.1 `0x7F9350` 不是「第二档入口」

```
7F9350  push ebp / mov ebp,esp
7F9356  mov eax,[esi]            ; esi = ecx = [req+0x63C]
7F935C  add eax,4 / push / call [0xCA8114]   ; COM AddRef
7F9378  mov eax,[ebp+8] / mov [esi],eax      ; 赋新值
7F9386  call [0xCA8128]                      ; 新对象 AddRef
7F938D  ret 4
```

这是一个 **COM 智能指针赋值函数**（Release 旧值 / 接管新值），
`ecx = [req+0x63C]`，参 8 = 新对象指针。它把 `[req+0x63C]` 从
「0x83 处理器写入的 0x11223344（非法指针）」改成合法对象。
**它不是阶段切换器，也不写 `0x644`。**

### 18.2 `644==0 / 644==1 / 644==3` 的真实含义

`0xBA4080` 的真实出口序列（`0xBA4114` 起）：

```asm
BA411A  call 0xC73900            ; 连接/读状态
BA411F  cmp  eax,1
BA4127  mov  [ebx+0xC8],2        ; ★ 传输up -> C8=2
BA412D  mov  [ebx+0x644],1       ; ★ 644=1   （由 C8=2 决定，非由任何入站帧）
BA4131  call 0xBA32A0            ; 通知
BA414B  cmp  eax,-2              ; 无数据 -> 继续等（成功）
BA417B  push 0x12 / call 0xBA3420  ; 其它负值 -> 复位
```

`0xBA32A0` 内部（`0xBA3315` 起）最关键的守卫：

```asm
BA3315  cmp byte [esi+0x90],0
BA331C  je  BA335C               ; 0x90==0 -> 什么都不做（安全）
BA3320  call 0xBA3100
BA3325  test al,al / jne BA335C
BA3331  ret 4                   ; ★ 0x90!=0 且 0xBA3100 失败 -> 直接返回，
                                ;   不触发 [esi+0x644]!=0 分支的虚调用
```

即：

```
[req+0x644]  == 0   只能由外部写入
[req+0x644]  == 1   传输已建立（C8=2），等待/处理入站帧 —— 正常态
[req+0x644]  == 3   0xBA4080 已把 {0x638,0x63C} 换出（0xBA417B/0xBA404E 之后）
```

**因此 `644=1` 不是错误、不是待清除的标记，而是「连接已就绪」的正值。**
观察器长期在 `C8==2` 时把 `644` 覆盖成 `0`，是在**持续性破坏一个正确的运行期值**。

### 18.3 31 ms 复位 = `0xBA34D0` 的「读结果 <= 0」分支

`0x7F9350` 被调用时 `esi=[req+0x644]`，而 `[req+0x644]` 是 `0`
（被覆盖），于是 `[esi+0x63C] = 0`。`0xBA34D0` 的判定：

```asm
BA3517  push 4 / push &val(0)
BA3522  lea ecx,[esi+0xC4]       ; ★ 读游标（不是「设备就绪」）
BA3539  call 0xC739E0           ; 读 4 字节
BA3539  -> edi = read result
BA3547  test edi,edi
BA3549  jns  BA356F              ; edi >= 0  -> 成功
BA354B  cmp  edi,-2
BA354E  je   BA356F              ; edi == -2 -> 成功（暂无数据）
BA3561  call 0xBA3420            ; ★ 其它负值（-1/-7 等）-> 复位
```

结合 §18.2 的返回值枚举：

```
edi == -2   无数据，继续等        -> OK
edi >= 0    读到 N 字节           -> OK
edi == -1   「无数据」           -> 复位（-1 的语义是失败，不是暂空）
edi == -7   「连接关闭」         -> 复位
```

**`[req+0xC4]` 是读游标。** `0x83` 帧被消费后游标停在帧尾，
随后 `0xC739E0` 在空读游标上返回 **`-1`**（不是 `-2`），
遂在约 1–2 个泵周期（实测 31 ms）后复位。这解释了复位时刻与
「是否再发 4 字节包」无关的既有实测。

### 18.4 已否证的既有推测

```
1. 0xDE7C18 是 30.0（不是 31ms）。该分支是 30 秒上限，本轮 31ms 复位无关。
2. 0x83 handler 写的 0x638=0x11223344 / 0x63C=0x11223344 是垃圾指针；
   但 [req+0x644] 是 0 时 0xBA32A0 走 je 0xBA335C 早退，
   不会对该垃圾指针解引用 —— 故不是崩溃源，也不能解释复位。
3. 「探针在 0x83 后关闭连接导致 31ms 复位」——探针本来就在 recv 中阻塞，
   并未关闭；且 §18.3 的复位与 socket 状态无关。
```

### 18.5 尚未闭合的可能归因（未验证，勿当结论）

```
a) 0x83 handler 同时写了 [req+0x5EC]=1 / [req+0x5F0]=1。
   0xBA2A60 在 [ebx+0x644]==0 分支（BA2AC0..BA2B58）里直接 ack 并把
   入站对象 push 进 [ebx+0x6D0] 队列。
   -> [0x5EC]/[0x5F0] 这对「抑制 ack」标志可能就是抑制 0xAB ack 的原因，
      从而让对端（本探针）不再收到任何 0x86/0xAB 交互。
b) 0xBA4080 在 [ebx+0x644]!=0 时对 {[ebx+0x638],[ebx+0x63C]} 所持对象
   做虚调用（BA40E0 区域）。0x83 handler 写入的 0x11223344 在 644!=0
   时会被真的解引用。这需要单独一轮静态确认。
```

### 18.6 第一档状态（本轮更正）

```
① 0x81                已闭合
② 0x82                已闭合
③ 0x83 校验           已闭合（5E8=3, 5EC=1, 5F0=1）
④ 644=0 -> 7F9350     ★ 更正：644=0 是错误状态，7F9350 只是 COM 赋值，
                        不是第二档入口。此前「入口条件已满足」的判断作废。
⑤ 保活/持续           未闭合：复位点已定位到 0xBA34D0 的 edi==-1 分支
```

### 18.7 下一轮的第一个动作（已定，尚未执行）

```
移除观察器在 C8==2 时对 [req+0x644] 的覆盖（--poke-lobby-644 不再使用），
让客户端自行保持在 644=1；同时用 POST83_SAMPLE 记录
[req+0xC0]（待处理出站事件数）与 [req+0xB0/rb+0x10C]（读游标），
以判定 edi==-1 是否在 0x83 被消费后必然出现。
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
