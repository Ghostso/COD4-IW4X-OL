# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001"
F={}
F["E18_RECEIVE_BUFFER_TO_APPLICATION_DATAFLOW.md"]="""# E18 — 接收缓冲区到应用层数据流 / RECEIVE BUFFER TO APPLICATION

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED
> 纪律：严格区分 找到网络对象 / 找到数据交接 / 找到游戏协议消费者。

---

## 1. libcurl socket 方法的数据流（PROVEN）

    libcurl 传输对象 (this)
       this+0x04 : 对端 sockaddr（0x775AB0 写入）
       this+0x14 : socket 句柄（0x775A50/0x775AB0 读取）
       this+0x1C..0x20 : 计数/状态（0x776170 初始化为 0）

    0x775A50(recv)     0x775AB0(recvfrom)
       buf=[ebp+8]        buf=[ebp+8]
       len=[ebp+0xC]      len=[ebp+0xC]
           到 recv/recvfrom
             返回长度 eax -> 调用者

关键（PROVEN）：两方法只把 buf/len 透传给 socket API 并返回长度；不解析、不复制、不排队。

## 2. Demonware 接收入口数据流（E-17 已证，本轮复核）

    0x783F00
       栈缓冲 [ebp-0x118]
       call 0x6B4DE0 -> recvfrom -> buf
       复制 0x84 字节（rep movsd, ecx=0x21）
       call 0xA84CE0

## 3. 0xA84CE0 的真实语义（PROVEN，本轮更正 E-17 表述）

地址口径更正：E-17 引用的是 VA 0xA84CE0；其 RVA = 0x684CE0。

    684CE0  push ebp / mov ebp,esp
    684CE3  mov eax,[ebp+8]        ; 源指针
    684CE8  mov esi,ecx            ; this
    684CEA  call 0xA86280
    684CEF  mov cx,[ebp+0xC]       ; 第二参数（word）
    684CF3  mov [esi+0x84],cx      ; 写 this+0x84
    684CFC  ret 8

而 0xA86220（RVA 0x686220）:

    686220  push ebp / mov ebp,esp / push esi / push edi
    686225  mov eax,ecx
    686227  mov ecx,0x21           ; 33 dwords = 0x84 字节
    68622C  lea esi,[ebp+8]
    686231  rep movsd              ; 定长内存拷贝
    686236  ret 0x84

裁定（PROVEN）：0xA84CE0 是定长 0x84 字节结构体拷贝 + 写一个 word 字段的构造/赋值函数。它不是消息分帧器、不是队列、不是游戏协议消费者。
这修正了 E-17 对它的描述（Demonware 对象交付点）：更准确的说法是定长结构体赋值函数。

## 4. 是否存在环形缓冲/异步队列/回调/跨线程交接

| 检查 | libcurl 方法 | Demonware 入口（0x783F00） |
|---|---|---|
| 环形缓冲 (0x3524F0/0x352570) | 否 | 否 |
| 消息队列 | 否 | 否 |
| 回调注册 | 否 | 否（同步 call） |
| 跨线程交接 | 否（直接返回） | 否 |
| 数据复制 | 无 | 是（0x84 定长） |

裁定（PROVEN）：两条路径都没有异步队列或跨线程交接。

## 5. 是否与已知解析候选建立连接

| 候选 | libcurl 簇 | Demonware 簇 |
|---|---|---|
| 0xA2660 | 否 | 否 |
| 0xA2E50 | 否 | 否 |
| 0x350170 | 否 | 否 |
| 0x3547D0 | 否 | 否 |
| 0x354100 | 否 | 否 |
| 0x3524F0 | 否 | 否 |
| 0x352570 | 否 | 否 |

裁定（REFUTED，限定范围）：未建立任何连接。

## 6. 首个应用层消费者

| 路径 | 首个下游 | 是否读 opcode/长度/序列号 |
|---|---|---|
| libcurl 方法 | 调用者（未展开） | 未观察到 |
| Demonware 入口 | 0xA84CE0（定长拷贝） | 否（仅拷贝 + 写 word） |

裁定（BLOCKED）：未找到读取协议字段的应用层消费者。

## 7. 裁定

| 项 | 裁定 |
|---|---|
| 接收缓冲区 | PROVEN（调用者提供 / 栈） |
| 长度传递 | PROVEN（返回值） |
| 是否复制 | libcurl 否 / Demonware 是（0x84 定长） |
| 异步/队列/回调 | REFUTED |
| 0xA84CE0 语义 | PROVEN（定长结构体赋值） |
| 与解析候选连接 | REFUTED（限定范围） |
| 首个应用层消费者 | BLOCKED |
"""
F["E18_INDIRECT_DISPATCH_INVENTORY.md"]="""# E18 — 间接分派表清单 / INDIRECT DISPATCH INVENTORY

> 范围：仅与已证网络对象/表相关的分派结构。

---

## 1. 表 T1：libcurl 传输对象基类 vtable

| 项 | 值 |
|---|---|
| 表地址 | .rdata 0x898568（VA 0xC98568） |
| 大小 | 52 槽 |
| 初始化 | 0x776139（就地）、0x776188（堆） |
| 调用位置 | 经对象首字段 [obj] + slot*4 |
| 数据流 | thiscall；方法读 this+0x14(sock)、this+0x04(addr) |
| 归属 | libcurl 传输层（PROVEN 库身份） |
| 成员示例 | 0x775A50(recv)、0x775AB0(recvfrom) |

## 2. 表 T2：派生类 vtable 0xC985CC

| 项 | 值 |
|---|---|
| 地址 | .rdata 0x8985CC |
| 初始化 | 0x7763A6、0x776C1A、0x473F1C |
| 归属 | libcurl 传输层派生类 A |

## 3. T3/T4/T5：其余派生 vtable

| 表 | 地址 | 初始化 |
|---|---|---|
| T3 | 0xC985EC | 0x7767D2 |
| T4 | 0xC985FC | 0x776BE6、0x776F15 |
| T5 | 0xC98620 | 0x776B64 |

## 4. T6：全局分配器 vtable

| 项 | 值 |
|---|---|
| 全局 | [0xD3A588] |
| 方法 | +0x28（分配）、+0x30（释放） |
| 使用者 | 0x776170（分配）、0x776130（释放） |
| 归属 | 内存分配器接口（INFERRED） |

## 5. 其他间接分派（历史已证）

| 站点 | 形式 | 说明 |
|---|---|---|
| 0x60E5B0 | 20+ call [ebp-0xd2c] | vsnprintf putc 回调（E-15 已证；非协议表） |
| 0x60264A | jmp [edx*4+0xA026D0] | 状态机跳转表（E-13） |
| 0x783F00 | 无直接 call | 经虚表/表分派（BLOCKED） |

## 6. 未闭合（BLOCKED）

| 项 | 说明 |
|---|---|
| 0x776170 的注册者 | 无直接交叉引用（BLK-18-1） |
| Demonware 0x783F00 的调用者 | 未定位（BLK-18-2） |

## 7. 裁定

| 项 | 裁定 |
|---|---|
| 与网络对象相关的表枚举 | PROVEN（T1..T6） |
| 是否发现游戏协议分派表 | 未发现（限定范围） |
| 是否有表通向游戏解析器 | REFUTED（限定范围） |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
