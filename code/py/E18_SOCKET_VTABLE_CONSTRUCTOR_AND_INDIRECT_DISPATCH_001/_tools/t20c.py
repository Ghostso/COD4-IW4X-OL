# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001"
F={}
F["E18_CONSTRUCTOR_REGISTRATION_AND_OBJECT_LIFECYCLE.md"]="""# E18 — 构造者、注册与对象生命周期 / CONSTRUCTOR & LIFECYCLE

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 直接交叉引用（PROVEN）

.text 中对 vtable 基址（VA 0x00C98568）的立即数写入：仅 2 处。

| 站点 RVA | 指令 | 语义 |
|---|---|---|
| 0x776139 | mov dword [esi], 0xC98568 | 就地构造：写 vptr |
| 0x776188 | mov dword [eax], 0xC98568 | 堆分配后构造：写 vptr |

## 2. 构造函数（PROVEN）

    776130  push ebp / mov ebp,esp / push esi
    776134  mov esi,ecx
    776136  lea ecx,[esi+0x1C]
    776139  mov dword [esi],0xC98568      ; vptr = 基类 vtable
    77613F  call 0xB757E0
    776148  mov dword [esi],0xC98500      ; 再改为清理 vptr
    77614E  je 0xB7615E
    776150  mov ecx,[0xD3A588]            ; 全局分配器
    776158  mov edx,[eax+0x30]
    77615B  push esi / call edx           ; 归还对象
    77615E  ret 4

    776170  mov ecx,[0xD3A588]
    776178  mov edx,[eax+0x28]           ; 分配方法
    77617B  push 0 / push 0x24           ; 0x24 = 36 字节
    77617F  call edx
    776188  mov dword [eax],0xC98568      ; 构造：写 vptr
    77618E  mov [eax+0x14],-1
    776191  mov [eax+0x18],-1
    776194  mov [eax+0x1C],0
    77619B  mov [eax+0x20],0

裁定（PROVEN）：0x776130 析构/清理；0x776170 堆分配 + 构造；对象大小 0x24；分配经全局分配器 vtable [0xD3A588]+0x28。
0x776170 无直接调用者（数据指针 0），经表/延迟注册（INFERRED）。

## 3. 派生类构造（PROVEN）

| 站点 | 写入 vptr |
|---|---|
| 0x7763A6 | 0xC985CC |
| 0x7767D2 | 0xC985EC |
| 0x776B64 | 0xC98620 |
| 0x776BE6 | 0xC985FC |
| 0x776C1A | 0xC985CC |
| 0x776F15 | 0xC985FC |
| 0x473F1C | 0xC985CC |

裁定（PROVEN）：同一 libcurl 传输对象族有 5 个 vptr 值，对应 5 个继承层级。

## 4. 生命周期（PROVEN）

| 阶段 | 证据 |
|---|---|
| 分配 | 0x776170 push 0x24 + 分配器 vtable |
| 构造 | 写 vptr（9 处） |
| 使用 | 52 个方法经 vtable 分派 |
| 销毁 | 0x776130（flag 归还）、0x7767E6（释放成员 + 改 vptr） |

## 5. 未闭合（BLOCKED）

| 项 | 说明 |
|---|---|
| 0x776170 的调用者 | 无直接交叉引用（BLK-18-1） |
| 对象实例化时机 | 需运行时或更深表枚举 |
| 0xD3A588 单例初始化 | 未追溯 |

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 构造函数 | PROVEN（0x776130 / 0x776170） |
| vptr 写入点 | PROVEN（9 处） |
| 对象大小 | PROVEN（0x24） |
| 注册者 | 部分（构造已定位，注册路径 BLOCKED） |
| 生命周期 | PROVEN（四段均有证据） |
"""
F["E18_SOCKET_ABSTRACTION_FUNCTION_AUDIT.md"]="""# E18 — socket 抽象函数审计 / FUNCTION AUDIT

> 类别（不得混同）：A=socket 操作；B=对象的接口方法；C=事件调度/回调；D=仅管连接状态；E=消费游戏应用层消息。

---

## 1. 0x775A50

| 项 | 值 |
|---|---|
| RVA | 0x775A50 |
| 边界 | 0x775A50..0x775A5E |
| 调用约定 | thiscall（ECX=this）+ ret 8 |
| 槽位 | vtable 0x898588（基类 0xC98568 第 8 槽） |

    775A53  mov eax,[ecx+0x14]        ; this->sock
    775A56  cmp eax,-1 / jne
    775A61  mov ecx,[ebp+0xC]        ; len
    775A64  mov edx,[ebp+8]          ; buf
    775A67  push 0                    ; flags
    775A6C  call dword [0xBAE490]     ; recv(sock,buf,len,0)
    775A72  ret 8

类别判定：socket 操作=是；对象接口方法=是；事件回调=否；仅管状态=否；消费游戏消息=否。
裁定：类别 B（socket 对象的接口方法），PROVEN。

## 2. 0x775AB0

| 项 | 值 |
|---|---|
| RVA | 0x775AB0 |
| 边界 | 0x775AB0..0x775AE7 |
| 槽位 | vtable 0x898590（基类第 10 槽） |

    775AB4  mov eax,[ecx+0x14]        ; this->sock
    775AC4  lea edx,[ebp-4]
    775ACB  add ecx,4                 ; &this->addr
    775AD6  mov dword [ebp-4],0x10    ; fromlen=16
    775ADE  call dword [0xBAE50C]     ; recvfrom(sock,buf,len,0,&this[4],16)
    775AE7  ret 8

裁定：类别 B，PROVEN。对端地址写入对象字段 this+0x04。

## 3. 两者对比

| 项 | 0x775A50 | 0x775AB0 |
|---|---|---|
| API | recv | recvfrom |
| 额外输出 | 无 | 对端地址 -> this+0x04 |
| 是否解析载荷 | 否 | 否 |

## 4. 是否含加密/分帧/重组/解析（REFUTED）

| 检查 | 结果 |
|---|---|
| 加密/解密 | 无 |
| 分帧/重组 | 无 |
| 消息解析 | 无 |
| 状态更新 | 仅 sock==-1 判定 |

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 0x775A50 类别 | 类别 B — PROVEN |
| 0x775AB0 类别 | 类别 B — PROVEN |
| 是否游戏消息消费者 | REFUTED |
| 是否有下游消费者 | 无（返回调用者） |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
