# E25 执行摘要

## 一句话结论

阶段 1 应答数据（`0x6ABAAA`/`0x6ABABB` 写入的 `ebx` 序列化缓冲）被传给 `0x6AA230`，后者**把该缓冲按长度复制成一个 0x1C 字节的节点并压入会话对象 `[edi+0xB8]` 的侵入式链表**；该链表由 **`0x6AA7B0`（会话泵）** 在会话循环中弹出，并在 `0x6AA88D` 经 `0x783B50` → `0x784E40` 调用 **`ws2_32!send`**——即 **阶段 1 应答确实存在可静态验证的网络发送路径（数据最终到达 `send`）**。

## 关键事实

1. `0x6ABAAA`/`0x6ABABB` 的 `ebx` 不是数据块，而是**序列化器对象**（`0x6ABA50 mov ebx,eax` ← `0x6ABA4B call 0xDAB40`，容量取 `[ebp-0x17c]+6`）。两次 `call 0xDF6F97C` 只是往序列化器里追加字段；真正传给 `0x6AA230` 的是 **`0x6ABAE2 mov edx,[ebx+0xC]`（字节缓冲指针 = data0）** 与 **`0x6ABAED call 0xDF16878`（返回序列化字节数 = data1）**。
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
| 1. 数据被构造 | **PROVEN** | 序列化器 `0xDAB40` vtable `0xCBBD24`；缓冲 `[ebx+0xC]`、写游标 `[ebx+0x10]` |
| 2. 数据被传递给函数 | **PROVEN** | `0x6ABAF2`(len) `0x6ABAF9`(buf=`[ebx+0xC]`) + `0x6ABAFC call 0x6AA230` |
| 3. 数据被写入队列 | **PROVEN** | `0x6AA2D0 call 0xDF806F2`（入 `[edi+0xB8]`）；节点 `0x320E30` 携带副本 |
| 4. 数据被提交给发送包装器 | **PROVEN** | `0x6AA88D call 0x783B50`（send 包装，`&[esi+0xC4]`） |
| 5. 数据最终传至网络发送 API | **PROVEN** | `0x784E5D call [0xBAE4C8]` = `ws2_32!send` |

## 逐目标裁定

| 目标 | 裁定 |
|---|---|
| `0x6ABAAA`/`0x6ABABB` 的 `esi+8`/`esi+0x10`/`[ebp-0x38]` | **PROVEN**：写入 `ebx` 序列化器（`0xDF6F97C`），非直接内存块 |
| `0x6AA230` 真实语义 | **PROVEN**：把入参缓冲克隆成节点 + 头插入 `[edi+0xB8]` 队列 + 驱动泵；**不是发送函数本身** |
| `0x6AA230` 首个调用者 `0x6AA465` | **PROVEN**：`0x6AAA320`（阶段 1 建立）在同一处写 `[edi+0x5CC]=1` |
| `0x6AA230` 第二个调用者 `0x6ABAFC` | **PROVEN**：阶段 1 应答成功收尾（`0x6AB310`），并把 `[edi+0x5CC]` 置 2 |
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
