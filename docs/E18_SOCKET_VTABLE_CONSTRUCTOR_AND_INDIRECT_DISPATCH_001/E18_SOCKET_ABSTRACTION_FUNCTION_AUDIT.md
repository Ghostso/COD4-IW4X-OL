# E18 — socket 抽象函数审计 / FUNCTION AUDIT

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
