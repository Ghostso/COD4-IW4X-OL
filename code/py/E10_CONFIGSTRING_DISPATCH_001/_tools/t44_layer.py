# -*- coding: utf-8 -*-
import os, hashlib
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001"
add03 = r"""

## 7. 层归属补正（新增，重要）

本轮复核出一条会改变解释的层级事实：

```
0xA21B8 _CODOL2697_WriteGamestate
  |- 0xA224C WriteByte(3)                     ; 顶层 opcode = 0x03
  |- 0xA225A WriteInt32(version)
  |- 0xA2269/0xA2279 WriteLenStr(map) / WriteLenStr(mode)
  |- 0xA2288 WriteInt32(field4)
  |- 0xA22C1 call 0xA0468 _CODOL2697_WriteConfigstrings   <- 内层帧
  |       |- 0xA07F8 WriteByte(4)              ; * 0x04 是 Gamestate 内部帧头
  |       |- 0xA0807 WriteShort(count1)
  |       |- ... A1/A2/A3 ...
  |       |- 0xA0997 WriteByte(6)
  |- 0xA22D9 WriteInt32(fieldC)
  |- 0xA22E8 WriteInt32(field8)
  `- 0xA22F8 WriteByte(6)                      ; 顶层 Gamestate 尾
```

**结论（DIRECT）：** 任务书所称的“外层 `0x04`”是**相对于 Configstring body 的外层**，即 **Gamestate 内部子帧的帧头**；它**不是**顶层 wire opcode（顶层是 `0x03`）。

| 层 | 标识 | 证据 |
|---|---|---|
| 顶层 wire opcode | `0x03`（Gamestate） | 服务端 `0xA224C`；客户端 `0x354100` 键域 0..8 |
| Configstring 内层帧头 | `0x04` | 服务端 `0xA07F8`（位于 `0xA22C1` 调用内） |
| Configstring 内层尾 | `0x06` | 服务端 `0xA0997` |
| Gamestate 顶层尾 | `0x06` | 服务端 `0xA22F8`（**与上行不同层，禁止合并**） |

**因此：** 客户端 `0x354100` 的 9 项跳转表是**顶层**消息分派器，**不是**内层 `0x04` 的分派器。内层 `0x04` 的客户端处理仍为 **BLOCKED**（`0x352F80` 的 +1 字节为强 INFERRED）。
"""
p=os.path.join(wd,"03_OPCODE_04_DISPATCH_VERDICT.md")
s=open(p,encoding="utf-8").read()
if "层归属补正" not in s:
    open(p,"w",encoding="utf-8",newline="\n").write(s+add03)
    print("appended to 03")

add02 = r"""

## 8. 层级补正（见 03 §7）

`0x04` 是 **Gamestate 内部子帧帧头**（服务端 `0xA22C1` 调用 `0xA0468` 后由 `0xA07F8` 写入），顶层 opcode 为 `0x03`。

因此：
- `0x3547D0` + `0x354100`（9 项）是**顶层**分派器，键域 0..8；
- 它**不**负责内层 `0x04` 的判定；
- 内层 `0x04` 的客户端判定仍为 **BLOCKED**，仅由 `0x352F80` 的 +1 字节行为给出强 INFERRED。
"""
p=os.path.join(wd,"02_OUTER_DISPATCH_CALLGRAPH.md")
s=open(p,encoding="utf-8").read()
if "层级补正" not in s:
    open(p,"w",encoding="utf-8",newline="\n").write(s+add02)
    print("appended to 02")
print("ok")
