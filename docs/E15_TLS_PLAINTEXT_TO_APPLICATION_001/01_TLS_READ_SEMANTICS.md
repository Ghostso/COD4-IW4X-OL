# 01 — TLS 读取语义 / TLS READ SEMANTICS

> 只读静态分析。冻结基线（本轮开始前复核，全部一致）：
> 客户端 353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1
> 恢复镜像 24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4
> 服务端 80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1
> 地址为 RVA（VA = RVA + 0x400000）。等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 0x672460 的函数边界与语义（PROVEN）

边界：0x672460..0x6724A0（其后 0x6724A1 为 int3，0x6724B0 起为同类函数）。

    672460  mov eax,[esp+4]            ; 参数1 = SSL 对象
    672464  cmp dword [eax+0x20],0     ; OpenSSL SSL 对象字段
    672468  jne 0xA7248C
    67246A  push 0x38B                 ; 行号
    67246F  push 0xC5650C              ; 指向 ".\\ssl\\ssl_lib.c"
    672474  push 0x114 / push 0x10E / push 0x14
    672480  call 0xA27F20              ; ERR_put_error
    672488  or eax,-1 / ret
    67248C  test byte [eax+0x30],2 / je 0xA72495
    672492  xor eax,eax / ret
    672495  mov ecx,[eax+8]
    67249C  mov eax,[ecx+0x1c]
    67249F  jmp eax                    ; 对象方法虚分派

字符串证据（PROVEN）：0xC5650C = ".\\ssl\\ssl_lib.c" —— OpenSSL ssl_lib.c 的源码路径常量。

裁定：0x672460(ssl, buf, len) 是 OpenSSL 读方法的薄包装（检查 SSL 对象有效性 → 转发到对象方法）。

## 2. 0x672460 的全部调用点（PROVEN）

| 调用点 | 调用者 | 传递参数 | 语义 |
|---|---|---|---|
| 0x6104E3 | 0x6104D0 | (ecx=[obj+0x188], &local_byte, 1) | 只读 1 字节到栈局部 |
| 0x67F5F0 | 0x631E10 区段（边界不可靠） | (esi, buf, len) | 通用读（buf/len 来自调用者） |

只有 2 处（DIRECT）。无第三处。

## 3. 0x6104D0 的输入输出（PROVEN）

    6104D0  mov ecx,[ebp+8]            ; 参数 = 连接对象
    6104D6  mov edx,[ecx+0x188]        ; TLS/SSL 子对象
    6104DC  push 1                     ; len = 1
    6104DE  lea eax,[ebp+0xb]          ; 输出缓冲 = 栈上 1 字节
    6104E1  push eax
    6104E2  push edx
    6104E3  call 0x672460
    6104E8  add esp,0xC
    6104EB  test eax,eax
    6104ED  jle 0xA104F6               ; <=0 → 失败
    6104EF  mov eax,1 / ret            ; 成功返回 1
    6104F6  neg eax / sbb eax,eax / ret ; 返回 0/-1

关键（PROVEN）：

| 项 | 值 |
|---|---|
| 输出缓冲区 | [ebp+0xb]（栈上 1 字节） |
| 容量 | 1 字节 |
| 返回值 | >0 → 返回 1；<=0 → 返回 0 或 -1 |
| 字节数据是否外传 | 否 —— [ebp+0xb] 是局部变量，函数返回后即失效 |

裁定：0x6104D0 不是"读取明文数据"的函数；它是"探测是否有 1 字节可读"的布尔探测（peek 语义）。读取的 1 字节被丢弃。

## 4. 0x5FB510 到 0x6104D0 的角色（PROVEN）

0x5FB510 只是 0x6104D0 的跳转别名（thunk）。其在 0x605220 中的用法：

    60527D  cmp dword [esi+0x17C],0
    60528D  call 0x5FB510              ; 到 0x6104D0（探测 1 字节）
    605295  test eax,eax
    605297  jne 0xA052B5               ; 有数据 → 返回
    60529A  or eax,-1 / ret            ; 无数据 → -1

## 5. 0x605220 的真实语义（PROVEN）

    60522B  mov esi,[edi+0x5B8]        ; 连接/SSL 对象
    60523C  push 0xA05200              ; 超时比较回调
    605253  call 0xA06650              ; 就绪/超时检查
    60525B  cmp [ebp-4],0 / jne 0xA05274
    605261  mov [edi+0x5B8],0          ; 对象失效
    60526B  or eax,-1 / ret
    605274  mov eax,[ebp+0xC] / mov [eax],esi   ; 输出：对象指针
    60527D  cmp [esi+0x17C],0
    60528D  call 0x9FB510              ; 到 0x6104D0（探测）
    6052A2  push 2 / push 1 / lea eax,[ebp+0xB]
    6052AB  call [0xBae490]            ; ws2_32!recv（2 字节探测）

裁定（PROVEN）：0x605220 = 连接就绪探测：① 超时检查；② 若连接层（含 TLS）有 1 字节可读则返回；③ 否则直接 recv 2 字节探测。它不是"读取完整协议消息"的函数。

## 6. 对 E-14 的修订

| E-14 表述 | E-15 修订 | 依据 |
|---|---|---|
| "0x605220到0x6104D0到0x672460 是 TLS 读取路径" | 部分更正：是 1 字节就绪探测（peek），不是明文数据读取 | §3 |
| "TLS 解密后的明文" | REFUTED：无明文外传；1 字节被丢弃 | §3 |
| "0x605220 是应用层入口候选" | REFUTED（见 02/04） | §5 + 02 |

## 7. 裁定

| 项 | 裁定 |
|---|---|
| 0x672460 边界与语义 | PROVEN（OpenSSL ssl_lib.c 包装） |
| 0x672460 调用点数 | PROVEN（2 处） |
| 0x6104D0 输出缓冲区 | PROVEN（栈上 1 字节） |
| 0x6104D0 语义 | PROVEN（探测/peek，丢弃数据） |
| 0x605220 语义 | PROVEN（就绪探测 + recv 2 字节探测） |
| 明文数据流存在 | REFUTED（无外传） |