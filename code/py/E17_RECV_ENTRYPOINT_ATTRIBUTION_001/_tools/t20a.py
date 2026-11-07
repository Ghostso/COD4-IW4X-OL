# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001"
F={}
F["E17_EXECUTIVE_SUMMARY.md"]="""# E17 — 执行摘要 / EXECUTIVE SUMMARY

> 任务编号：E17_RECV_ENTRYPOINT_ATTRIBUTION_001
> 模式：只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。
> **冻结基线（开工与收工各复核一次，均一致）：**
> - 客户端 `codoMP_client_shipRetail.exe` = `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`
> - 恢复镜像 `codol2697-static-candidate.bin` = `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`
> - 服务端 `codol_dedrun.exe` = `80816711946a5396abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`
> 地址为 RVA（VA = RVA + 0x400000）。
> 工具来源：自建脚本（`_tools/`）+ E-06 恢复镜像；无 IDA/Ghidra 数据库人工标注被当作原始事实。

---

## 1. 三句话结论

1. **`0x6B4DE0` 与 `0x784F60` 都是 `recv`/`recvfrom` 的薄封装（PROVEN）**，不是应用层消费者。
2. **两者的调用者簇（`0x783xxx` / `0x6A9xxx` / `0x6ABxxx` / `0x6B3xxx`）属 Demonware 传输/会话栈（INFERRED 强）**——镜像含 `DW-Client-Ticket`、`demonware.net`、`bdSessionParams@@` 字符串。
3. **两者 7 层闭包内不接触任何游戏协议解析器（PROVEN 负）**：`0xA2660`/`0x3547D0`/`0x354100`/`0x350170`/`0x34FD80`/`0xA2E50`/`0x3524F0`/`0x352570` 全部不在闭包内。

## 2. 归属裁定

| 候选 | 真实职责 | 归属 | 等级 |
|---|---|---|---|
| `0x6B4DE0` | `recvfrom` 薄封装 + socket 统计累加 | **Demonware 传输层（非游戏应用层）** | PROVEN（职责）/ INFERRED（模块） |
| `0x784F60` | `recv` 薄封装 + socket 状态记录 | **Demonware 传输层（非游戏应用层）** | PROVEN（职责）/ INFERRED（模块） |

## 3. 是否找到游戏会话入站路径

**否（BLOCKED，限定范围）。** 本轮审计的 2 个候选均已归属到非游戏功能（Demonware 传输层）。

## 4. 最小阻塞点

**游戏协议的应用层入口仍未定位。** 当前收包原语总台账（本轮全量）：

| 原语 | 调用点数 |
|---|---|
| recv | 7 |
| recvfrom | 3 |
| send | 5 |
| sendto | 4 |

其中已归属：ICMP ping（`0x1B0BA1`/`0x1B09EF`）、HTTP 更新（`0x60522*`/`0x6104D0` 链）、Demonware 传输（`0x6B4E3C`/`0x784F7D`）、错误日志（`0x602441`/`0x6029BE`）、socket 抽象（`0x775A6C`/`0x775ADE`）。

## 5. 建议

1. 对 **`0x775A50`/`0x775AB0` 虚表** 的实例化路径做定向审计（这是最后一个有 socket 语义但未归属完整的簇）。
2. 若虚表归属后仍无游戏特征，则需转向 `.tvm0` 之外的间接分派审计（函数指针表枚举）。
3. **不**建议继续扩大 recv/recvfrom 调用点普查——边际收益已下降。

## 6. 问题库与解决率

依 E-15 权重标度：新增 Q-20（`0x6B4DE0` 归属，权重 3，PROVEN=1.0）、Q-21（`0x784F60` 归属，权重 3，PROVEN=1.0）、Q-22（Demonware 栈是否为游戏路径，权重 5，BLOCKED=0.0）。

- 旧总权重 103（E-16）-> **新总权重 114**
- 新增加权得分 = 3 + 3 + 0 = 6
- 新加权得分 = 36 + 6 = 42
- **风险加权解决率 = 42 / 114 = 36.8%**

（E-16 为 34.9%；本轮 +1.9 个百分点。）
"""
F["E17_CANDIDATE_FUNCTION_AUDIT.md"]="""# E17 — 候选函数审计 / CANDIDATE FUNCTION AUDIT

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
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
