p = r"CODOLServer\HANDOFF_20261002_TLDR.md"
s = open(p, encoding="utf-8").read()
old = """### 4.5 下一步要验证的一件事

在 `0xBA39E7 .. 0xBA3A2C` 之间，是否存在一步
"把 provider 输出送入内层流"的拷贝。

- 若有：找出该拷贝的条件（可能就是本次卡点）
- 若无：说明 0x85 内层消息不走这次 provider 调用，
  而是走另一条更早的路径（0xBA1477 那套 + 0xC73800 摘要）"""
new = """### 4.5 [ebp-0x50] 的真实角色（2026-10-02 已查明）

    0xBA37A6  push 0x10
    0xBA37A8  lea eax, [ebp-0x50]      ; dst
    0xBA37AB  push eax                 ; arg5
    0xBA37AC  lea ecx, [ebp-0x3A0]
    0xBA37B2  push ecx                 ; arg4
    0xBA37B9  mov edx, [ebp-0x3A0]
    0xBA37BF  push edx                 ; arg3
    0xBA37C0  push ebx                 ; arg2
    0xBA37C1  push esi                 ; arg1
    0xBA37C2  call 0xB783C0            ; 从帧里读 16 字节 -> [ebp-0x50]

    0xBA39FE  push esi
    0xBA39FF  push eax
    0xBA3A00  push eax
    0xBA3A01  lea eax, [ebp-0x50]
    0xBA3A04  push eax                 ; 同一块缓冲传给 provider
    0xBA3A05  call [p608.vtable+0xC]

=> **[ebp-0x50] 不是 provider 的输出缓冲，而是帧内那个 16 字节
   密钥块的落地位置**，先由 0xBA37C2 读入，再交给 provider。

（全函数内 [ebp-0x50] 只有两处 lea，没有任何"读其内容"的指令，
  说明它只作为指针被传递，不在这里被直接消费。）

### 4.6 下一步要验证的（更新）

既然 [ebp-0x50] 是输入而非输出，那么：

  provider 解密后的明文去了哪里？
  内层读取器 0xB783C0 的数据源（[ebp-0x39C]/[ebp-0x390] 那一套）
  究竟指向什么？

建议先确认 `0xB783C0` 在 0x85 路径上被调用的两处实参分别是什么：
  0xBA37C2  （读帧内 16B 密钥块）
  0xBA3794  / 0xBA3A45  （内层流读取）
三者用同一套读取器，但源不同。"""
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("TLDR updated")
