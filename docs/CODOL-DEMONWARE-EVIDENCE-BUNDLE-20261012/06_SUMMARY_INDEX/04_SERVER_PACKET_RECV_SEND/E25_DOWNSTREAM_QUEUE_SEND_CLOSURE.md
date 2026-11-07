# E25 下游队列与发送闭合

## 1. 会话泵 `0x6AA7B0`

调用者：`0x6AA2D7`（`0x6AA230` 入队后）、`0x6AAE13`、`0x6AC109`（会话分派器）。

```asm
6AA7B0  push ebp; mov ebp,esp; push ecx
6AA7B7  mov ecx, dword ptr [esi+0x628]   ; 传输对象（可选）
6AA7BE  test ecx,ecx
6AA7C0  je  0xAAA7C8
6AA7C2  mov eax,[ecx]; mov edx,[eax]; call edx   ; 传输对象 slot0
6AA7C8  lea ecx,[esi+0x508]
6AA7CE  call 0x7832E0                    ; 时间/速率控制
6AA7D8  cmp dword ptr [esi+0xC8],1
6AA7ED  call 0x783B30                    ; 状态机推进
6AA808  mov dword ptr [esi+0xC8],2       ; 置"进行中"
6AA812  call 0x6AA4B0                    ; 副作用/清理
6AA817  cmp dword ptr [esi+0xC8],2
6AA830  cmp dword ptr [esi+0xC0],0       ; <== 队列非空？
6AA837  je  0xAAA974                     ; 空则跳出
```

## 2. 出队 + 递交（决定性）

```asm
6AA83D  mov ebx, dword ptr [esi+0xB8]    ; 取队首节点
6AA843  mov ecx, ebx
6AA845  call 0x589230                    ; -> eax = [ebx+0x10]（读游标）
6AA84A  mov edx, eax
6AA84C  call 0x77FD10                    ; -> al = [edx+0x14]（标志）
6AA855  call 0x589230
6AA85A  add eax, 0x28
6AA85D  push eax
6AA85E  lea ecx, [esi+0x508]
6AA864  call 0x783370                    ; 环形缓冲可用空间查询
6AA869  mov edx, eax
6AA86D  jle 0xAAA9A8
6AA873  sub edx, 0x28
6AA87E  push edx                         ; 长度
6AA87F  mov ecx, ebx
6AA881  call 0x6C4070                    ; -> eax = [ebx+0xC]（缓冲指针）
6AA886  push eax                         ; 缓冲指针
6AA887  lea ecx, [esi+0xC4]              ; <== 套接字持有者对象
6AA88D  call 0x783B50                    ; <== send(fd, buf, len)
6AA892  mov edi, eax
6AA896  jle 0xAAA9AD                     ; 发送失败分支
```

## 3. 发送包装器链（到 API）

```asm
783B50  push ebp; mov ebp,esp
783B53  mov eax,[ebp+0xC]      ; len
783B56  mov edx,[ebp+8]        ; buf
783B59  push eax
783B5A  mov eax,dword ptr [ecx] ; <== 套接字句柄 fd（ecx = &[session+0xC4]）
783B5C  push edx
783B5D  push eax
783B5E  call 0x784E40          ; send wrapper
783B67  ret 8
```

```asm
784E40  push ebp; mov ebp,esp; push esi
784E44  mov esi,[ebp+8]        ; fd
784E47  cmp esi,-1             ; 无效 fd 守卫
784E52  mov eax,[ebp+0x10]     ; len
784E55  mov ecx,[ebp+0xC]      ; buf
784E58  push 0                 ; flags
784E5A  push eax
784E5B  push ecx
784E5C  push esi
784E5D  call dword ptr [0xBAE4C8]   ; <== ws2_32!send(fd,buf,len,0)
784E63  mov ecx,eax
784E65  test ecx,ecx
784E67  jns 0x784EF1
784E6D  call dword ptr [0xBAE4DC]   ; WSAGetLastError
```

导入名核对（pefile）：

```text
IAT 0xBAE4C8 = ws2_32.dll!send
IAT 0xBAE4DC = wsock32.dll!WSAGetLastError
```

## 4. 套接字来源与生命周期

| 位置 | 内容 |
|---|---|
| `0xB84950` | `push 6; push 1; push 2; call [0xBAE508]` = `socket(AF_INET=2, SOCK_STREAM=1, IPPROTO_TCP=6)`；随后 `ioctlsocket(fd, FIONBIO=0x8004667E, &mode)` |
| `0x783A50` | `call 0xB84950`，把 fd 存入 `[esi]`，`cmp eax,-1; setne al`（成功标志） |
| `0x783B90` | `mov eax,[esi]; push eax; call 0x784B00` = `closesocket(fd)`；`[esi]=-1` |
| 绑定 | 会话构造器 `0x6AA6E9..0x6AA6FB` 把 `&[esi+0xC4]` 区与 `[+0x628]` 清零；`0x68A026 mov [ecx+0x4B0],eax` → `0x68A037 call 0x6A9680` 把传输对象装入 `[session+0x628]` |

## 5. 数据流闭合表

| 层级 | 地址 | 结论 | 等级 |
|---|---|---|---|
| 构造 | `0x6AB4C3..0x6ABABB`（序列化器 `0xDAB40`） | 应答字节写入 `[ebx+0xC]` | PROVEN |
| 传递 | `0x6ABAF2/0x6ABAF9/0x6ABAFC` | (buf,len) → `0x6AA230` | PROVEN |
| 队列提交 | `0x6AA2D0 call 0x0DF806F2` | 节点入 `[edi+0xB8]` | PROVEN |
| 发送包装器 | `0x6AA88D call 0x783B50` | `send(fd,buf,len)` | PROVEN |
| 网络 API | `0x784E5D call [0xBAE4C8]` | `ws2_32!send` | PROVEN |

**裁定：应答数据到达 `ws2_32!send`，五层全部闭合。** 唯一未闭合的是"发送缓冲内容与线上字节的逐字节一致性"（需 `.data` 运行时布局）。

## 6. 反证与未覆盖

- **反证**：`0x6AA230` 内**无** send/sendto 引用（会话区间 `0x6A9000..0x6AD000` 内亦无），故"`0x6AA230` 即发送函数"被否。
- **未覆盖**：`0x783B50` 的另一调用者 `0x6A9B6E`（`0x6A9B20`，阶段 3 的空闲发送）与 `0x6B3343`（另一会话类型）未展开。
- **未覆盖**：`[esi+0x628]` 传输对象的 `slot0` 真实目标为运行时决定。
