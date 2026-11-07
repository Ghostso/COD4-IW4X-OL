# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001")
files={}

files["E25_EXECUTIVE_SUMMARY.md"]=r'''# E25 执行摘要

## 一句话结论

阶段 1 应答数据（`0x6ABAAA`/`0x6ABABB` 写入的 `ebx` 序列化缓冲）被传给 `0x6AA230`，后者**把该缓冲按长度复制成一个 0x1C 字节的节点并压入会话对象 `[edi+0xB8]` 的侵入式链表**；该链表由 **`0x6AA7B0`（会话泵）** 在会话循环中弹出，并在 `0x6AA88D` 经 `0x783B50` → `0x784E40` 调用 **`ws2_32!send`**——即 **阶段 1 应答确实存在可静态验证的网络发送路径（数据最终到达 `send`）**。

## 关键事实

1. `0x6ABAAA`/`0x6ABABB` 的 `ebx` 不是数据块，而是**序列化器对象**（`0x6ABA50 mov ebx,eax` ← `0x6ABA4B call 0x4DAB40`）。两次 `call 0xDF6F97C` 只是往序列化器里追加字段，真正的字节缓冲是 `[ebx+0xC]`、长度是 `[ebx+0x10]`。
2. `0x6AA230`（thiscall + 2 栈参 + `ret 8`）：
   - `push 0x1c` → `0x0DF9AA45` 分配节点；
   - `call 0x320E30` 把 `(data0, len, flag)` 复制进节点（`0x320E62` 再分配 `len`，`0x320E74` `call 0xB4FF60` = `memcpy`）；
   - `lea ecx,[edi+0xB8]` + `call 0x0DF806F2`：**头插法入队**；
   - `call 0x6AA7B0`：立刻驱动一次会话泵。
3. `0x6AA7B0`（泵）从 `[esi+0xB8]` 取头节点，经 `0x6AA881`/`0x6AA88D` 把节点内容交给 `&[esi+0xC4]`（**套接字持有者**）的发送方法 `0x783B50`。
4. `0x783B50` = `send(fd, buf, len)` 包装：`mov eax,[ecx]`（取套接字句柄）→ `call 0x784E40`。
5. `0x784E40` 末尾 `call dword ptr [0xBAE4C8]`，`0xBAE4C8` 的导入名经 pefile 解析为 **`ws2_32.dll!send`**。
6. 套接字来源可验证：`0x784950` 为 `push 6; push 1; push 2; call [0xBAE508]` = `socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)`，返回句柄存入 `[esi]`；`0x784B00` 为 `closesocket`。

## 四层证据判定（任务书成功标准）

| 层级 | 结论 | 证据 |
|---|---|---|
| 1. 数据被构造 | **PROVEN** | 序列化器 `0x6AB4C3..0x6ABABB`；`[ebx+0xC]`/`[ebx+0x10]` |
| 2. 数据被传递给函数 | **PROVEN** | `0x6ABAF2/0x6ABAF9/0x6ABAFC` push 参数 + `call 0x6AA230` |
| 3. 数据被写入队列 | **PROVEN** | `0x6AA2D0 call 0xDF806F2`（入 `[edi+0xB8]`）；节点 `0x320E30` 携带副本 |
| 4. 数据被提交给发送包装器 | **PROVEN** | `0x6AA88D call 0x783B50`（send 包装，`&[esi+0xC4]`） |
| 5. 数据最终传至网络发送 API | **PROVEN** | `0x784E5D call [0xBAE4C8]` = `ws2_32!send` |

## 逐目标裁定

| 目标 | 裁定 |
|---|---|
| `0x6ABAAA`/`0x6ABABB` 的 `esi+8`/`esi+0x10`/`[ebp-0x38]` | **PROVEN**：写入 `ebx` 序列化器（`0xDF6F97C`），非直接内存块 |
| `0x6AA230` 真实语义 | **PROVEN**：把入参缓冲克隆成节点 + 头插入 `[edi+0xB8]` 队列 + 驱动泵；**不是发送函数本身** |
| `0x6AA230` 首个调用者 `0x6AA465` | **PROVEN**：`0x6AAA320`（阶段 1 建立）在同一处写 `[edi+0x5CC]=1` |
| `0x6AA230` 第二个调用者 `0x6ABAF C` | **PROVEN**：阶段 1 应答成功收尾（`0x6AB310`），并把 `[edi+0x5CC]` 置 2 |
| 队列 `[edi+0xB8]` | **PROVEN**：构造器 `0x6AA613` 清零初始化；`0x6AA7B0` 弹出；节点结构 0x1C |
| 发送包装器 `0x783B50` | **PROVEN**：`send(fd,buf,len)`；唯一上游 `0x6AA88D`（泵）等 |
| `ws2_32!send` | **PROVEN**：`0x784E5D call [0xBAE4C8]`，pefile 解析导入名 |
| 握手码 `0x81` 与发送的关系 | **INFERRED（强）**：应答生成于 0x81 分支，且该缓冲经队列进 send；但 `.data` 表内容不可静态解析，未逐字节比对线上载荷 |

## 被证伪/更正的假设

- **E-24 遗留建议「确认是否经 `0x6AA230` 入队到发送缓冲」→ 已证实**：是。但需更正一个细节——`0x6ABAAA` 的 `esi+8`/`esi+0x10` 并非内存数据块，而是**序列化器调用参数**；E-24 把 `ebx` 描述为普通对象但未说明其为序列化器。
- 「`0x6AA230` 是入队/发送函数」→ **部分更正**：它是"克隆 + 入队 + 驱动泵"，**发送发生在 `0x6AA7B0` 内的 `0x6AA88D`**，不是 `0x6AA230` 本身。

## 剩余阻塞项

1. `.data` 中队列容器/统计字段的运行时布局（`0x6A9xxx` 处 BSS 表）静态不可得。
2. `0x81` 应答字节与线上载荷的逐字节一致性未验证（只证同一缓冲链路）。
3. `[ebx+0xC]` 缓冲的实际内容（`CLIENTCHAL`/`BDDATA` 之外的字段序）未逐字段解码。
4. 反向（recv）侧同理存在 `0x784F60 → ws2_32!recv`，但本轮未展开。

## 下一步唯一建议

解析阶段 1 应答序列化器 `0x4DAB40`（`ebx` 的构造器）与 `0xDF6F97C`（字段追加）的字段序，把 `0x6AB4C3..0x6ABABB` 写成"应答报文字段布局"，与 `ws2_32!send` 的缓冲长度做静态一致性核对；这是唯一能把"数据到达 send"推进到"线上字节可预测"的边界。
'''

files["E25_RESPONSE_BLOCK_FIELD_PROVENANCE.md"]=r'''# E25 应答数据块字段来源

## 1. 更正：`0x6ABAAA` 操作的不是内存块而是序列化器

```asm
6ABA4B  call 0x4DAB40          ; 构造对象 (arg: [ebp-0x17c]+6, 0) -> eax
6ABA50  mov  ebx, eax          ; ebx = 序列化器/写入器对象
...
6ABAAA  call 0xDF6F97C         ; (ecx=ebx) 追加字段：eax=[esi+0x10], ecx=[esi+8]
6ABABB  call 0xDF6F97C         ; (ecx=ebx) 追加 8 字节：[ebp-0x38]
```

因此 `[esi+8]`、`[esi+0x10]`、`[ebp-0x38]` **不是**"被写入的数据字段"，而是**喂给序列化器 `0xDF6F97C` 的参数**。

## 2. 逐项来源

| 位置 | 来源（指令） | 类型 | 说明 | 等级 |
|---|---|---|---|---|
| `esi` | `0x6AB3DC mov esi,[ebp-0x17c]` / `0x6AB42A mov esi,eax` | 对象指针 | 由 `0x6AB3F6..0x6AB425` 构造（长度 `[ebp-0x17c]`+0） | PROVEN |
| `[esi+8]` | `0x6ABAA3 mov ecx,[esi+8]` | 指针/句柄 | 作为追加字段的载荷指针（第一参数） | PROVEN（读取） |
| `[esi+0x10]` | `0x6ABAA0 mov eax,[esi+0x10]` | 长度/计数 | 作为追加字段的第三参数（长度） | PROVEN（读取） |
| `[ebp-0x38]` | `0x6ABAB3 lea ecx,[ebp-0x38]` | 内联 8 字节 | 追加 8 字节字段（`push 8`） | PROVEN |
| `ebx` | `0x6ABA50 mov ebx,eax` ← `0x4DAB40` | 序列化器 | 字节缓冲为 `[ebx+0xC]`，长度 `[ebx+0x10]` | PROVEN |

`esi` 的构造（`0x6AB3F6..0x6AB42C`）：

```asm
6AB3F6  push 0x24
6AB3FB  mov byte ptr [ebp-0x172], 7
6AB402  call 0xDF9AA45         ; 分配
6AB41C  lea ecx,[ebp-0x172]
6AB425  call 0xDECFC0E         ; 构造（长度来自 [ebp-0x172]）
6AB42A  mov esi, eax
```

即 `esi` 是"长度取自 `[ebp-0x17c]`"的缓冲对象；`[esi+8]`/`[esi+0x10]` 是该对象的数据/长度字段。

## 3. `ebx`（序列化器）的字节缓冲

`0x320E30` 的同类对象给出节点/缓冲结构（`0x6AA230` 用它克隆）：

```asm
6A97E9  mov dword ptr [esi],0xCBBD1C     ; 基类 vtable
6A97F6  mov dword ptr [esi],0xC5B0E0     ; pair 派生 vtable
6A97FC  mov dword ptr [esi+8],eax        ; 关联对象
6A9810  mov ecx,[eax+0xC]                ; <- 数据指针复制来源
6A9816  mov dword ptr [esi+0xC],ecx
```

而 `0x320E30`（clone 0x1C 节点）：

```asm
6A… 320E48 mov dword ptr [esi],0xCBBD24  ; node vtable
     320E4E mov dword ptr [esi+8],edi     ; 长度
     320E61 push edi ; call 0xDF9AA45     ; 分配 len 字节
     320E6D mov dword ptr [esi+0xC],eax   ; 缓冲指针
     320E74 call 0xB4FF60                 ; memcpy(buf, src, len)
     320E7F mov dword ptr [esi+0x14],eax  ; 写游标
     320E82 mov dword ptr [esi+0x10],eax  ; 读游标
```

**裁定**：`[ebx+0xC]` = 序列化后的字节缓冲；`[ebx+0x10]`/`[ebx+0x14]` = 读/写游标。长度由序列化器累积。

## 4. 与 `CLIENTCHAL`/`BDDATA`/消息码的关系

| 项 | 关系 | 等级 |
|---|---|---|
| `CLIENTCHAL`（VA `0xC5B144`） | `0x6AB8C4` `push 0xC5B144` 作为 `0x6AA9CE0` 的字段值 → 进入协商输入字段区，**不在此序列化器调用点** | INFERRED（强） |
| `BDDATA`（VA `0xC5B13C`） | `0x6AB906` `push 0xC5B13C` 同上 | INFERRED（强） |
| 消息码 `0x81` | `0x6AB66D mov byte [ebp-0x171],0x81`，经 `0xA87830` 写入缓冲 | PROVEN（写入）/ 语义 BLOCKED |
| 消息码 `0x83/0x84/0x85` | 与 `0x6AB310` 应答序列化器**无直接数据流** | REFUTED（同一函数内不存在） |

## 5. 未闭合

- `[esi+8]`/`[esi+0x10]` 指向的缓冲**内容**未逐字节解码。
- `[ebp-0x38]` 的 8 字节字段语义未定。
- 序列化器 `0x4DAB40` 与 `0xDF6F97C` 的字段序未展开。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
