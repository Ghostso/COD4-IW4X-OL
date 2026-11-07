# E17 — 候选函数审计 / CANDIDATE FUNCTION AUDIT

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. `0x6B4DE0`

### 1.1 身份

| 项 | 值 |
|---|---|
| 模块 | 恢复镜像（等价客户端 .text） |
| 节区 | .text |
| RVA | 0x6B4DE0 |
| 入口字节 | 55 8B EC 83 EC 18（push ebp; mov ebp,esp; sub esp,0x18）—— 标准 prologue，非伪影 |
| 边界 | 0x6B4DE0 .. 0x6B4F4F（其后 int3 填充） |
| 大小 | 0x16F 字节 |

### 1.2 直接调用证据（PROVEN）

| 调用点 | 调用者 | 类型 |
|---|---|---|
| `0x783F5E` | `0x783F00` | 直接 call |

数据指针引用：**0**（非表驱动）。

### 1.3 函数内网络 API（PROVEN）

| 调用点 | IAT | API |
|---|---|---|
| `0x6B4E3C` | 0xBAE50C | **recvfrom** |
| `0x6B4E4C` | 0xBAE4DC | WSAGetLastError |
| `0x6B4E86` / `0x6B4F10` | 0x43A7C0（内部） | 错误上报 |
| `0x6B4E92` / `0x6B4F10` | 0xBAE4A0 | **ntohs**（端口字节序转换） |

### 1.4 参数与语义（PROVEN）

```asm
6B4DF0  mov edx,[ebp+8]      ; sock
6B4DFB  mov edi,[ebp+0xc]    ; 输出：地址结果
6B4DF7  mov ebx,[ebp+0x10]   ; 输出：端口（word）
6B4DF3  mov ecx,[ebp+0x14]   ; len
6B4E2D  mov eax,[ebp+0x18]   ; flags
6B4E25  lea eax,[ebp-0x18]   ; &fromlen (初始 0x10)
6B4E29  lea eax,[ebp-0x14]   ; &from (sockaddr_in, 栈)
6B4E3C  call recvfrom
6B4E42  mov esi,eax          ; 返回长度
6B4E46  jns 0xAB4F0C         ; >=0 成功
...
6B4F0C  mov ecx,[ebp-0x12]
6B4F10  call ntohs           ; 端口转主机序
6B4F1C  mov word [ebx],ax    ; 写输出端口
6B4F1F  mov [edi],edx        ; 写输出地址
6B4F25  add [0xD47388],eax   ; ★ socket 统计累加（低 32 位）
6B4F2E  adc [0xD4738C],edx   ; ★ 高 32 位
6B4F34  add [0xD47398],1     ; ★ 计数
6B4F3D  adc [0xD4739C],0
6B4F2D  mov eax,esi          ; 返回实际接收长度
```

**裁定（PROVEN）：`0x6B4DE0` 是 `recvfrom` 的薄封装**；输出 sockaddr/端口，返回长度，**并把字节数累加到全局统计计数器**。

### 1.5 缓冲区

缓冲区由**调用者提供**（`[ebp+0xc]`/`[ebp+0x14]`）。函数本身**不分配、不复制、不排队**数据。

---

## 2. `0x784F60`

### 2.1 身份

| 项 | 值 |
|---|---|
| RVA | 0x784F60 |
| 入口字节 | 55 8B EC 57 8B 7D 08 |
| 边界 | 0x784F60 .. 0x784FFF 附近（其后 int3） |
| 大小 | 约 0xA0 字节 |

### 2.2 直接调用证据（PROVEN）

| 调用点 | 调用者 | 类型 |
|---|---|---|
| `0x783B7E` | `0x783B70` | 直接 call |

数据指针引用：**0**。

### 2.3 函数内网络 API（PROVEN）

| 调用点 | IAT | API |
|---|---|---|
| `0x784F7D` | 0xBAE490 | **recv** |
| `0x784F8E` | 0xBAE4DC | WSAGetLastError |
| `0x784F9F` | 0x43A7C0（内部） | 错误上报 |

### 2.4 语义（PROVEN）

```asm
784F64  mov edi,[ebp+8]      ; sock
784F67  cmp edi,-1           ; 无效 socket
784F6C  lea eax,[edi-9]      ; 返回 -9（WSAENOTSOCK）
784F72  mov eax,[ebp+0x10]   ; len
784F75  mov ecx,[ebp+0xc]    ; buf
784F78  push 0               ; flags=0
784F7D  call recv
784F83  mov ecx,eax
784F87  jns 0xB8502E         ; >=0 成功
...
784FC9  mov [0xD47370],esi   ; ★ 记录 WSA 错误码
784FD0  mov [0xD47374],2     ; ★ 状态=2
...
78502E  (成功路径：返回长度)
```

**裁定（PROVEN）：`0x784F60` 是 `recv` 的薄封装**；失败时把错误码与状态码写入全局。

### 2.5 缓冲区

缓冲区由调用者提供（`[ebp+0xc]`），长度由 `[ebp+0x10]`。函数**不分配、不复制、不排队**。

---

## 3. 推测 vs 证据的区分（任务要求）

| 类型 | `0x6B4DE0` | `0x784F60` |
|---|---|---|
| 直接调用证据 | `0x783F5E`（唯一） | `0x783B7E`（唯一） |
| 间接/表驱动证据 | 无（数据指针 0） | 无（数据指针 0） |
| 仅由命名/邻近推测 | 无（不依赖命名） | 无（不依赖命名） |

## 4. 裁定

| 项 | 裁定 |
|---|---|
| 两候选的真实身份 | **PROVEN**（recv/recvfrom 薄封装） |
| 调用者数量 | **PROVEN**（各 1 个） |
| 是否应用层消费者 | **REFUTED**（均为传输层封装） |
| 是否表驱动/间接 | **REFUTED**（数据指针 0） |
