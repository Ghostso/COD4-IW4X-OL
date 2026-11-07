# E24 协商对象生命周期

## 1. 对象标识

| 项 | 值 |
|---|---|
| 字段 | `[edi+0x5F4]`（`edi` = 会话 this） |
| 构造器 | `0xA87BA0`（RVA `0x687BA0`，`.text`） |
| vtable | `0xC5A31C`（`.rdata`，RVA `0x85A31C`） |
| 对象大小（构造时分配） | `0x394`（`0x6AB9C2 push 0x394` → `0x0DF9AA45` 分配器） |
| 首次使用点 | `0x6AB146`（`0x6AAE70` 成功路径） |

## 2. 构造器 `0xA87BA0`

```asm
687BA0  push ebp; mov ebp,esp
687BC9  push 0x10
687BCB  call 0xA888A0          ; 基类/子对象构造
687BD0  push 0xC5BEB0          ; 类型描述符（含函数指针表）
687BDC  mov  dword ptr [esi], 0xC5A31C    ; <== 写入本对象 vtable
687BE2  call 0xACBAF0
687C07  mov eax, esi; ret
```

- 静态调用者仅两处：`0x6AB97A`、`0x6AB9DA`（均在被调用函数 `0x6AB310` 内）。
- 构造器自身是 thiscall（ECX=this，无栈参数），返回 this。

## 3. 字段写入点（全量）

`[edi+0x5F4]` 的确定写入点：

| 写点 | 指令 | 语义 |
|---|---|---|
| `0x6AB9B3` | `mov dword ptr [edi+0x5F4], 0` | 旧对象经 slot0 释放后清零 |
| `0x6AB9E7` | `mov dword ptr [edi+0x5F4], eax` | 换入 `0x6AB9DA` 构造的新对象 |

紧邻的 `[edi+0x5F0]`（另一对象字段，同构造器）：写 `0x6AB953`(清 0)、`0x6AB983`(换新)，构造调用 `0x6AB97A`。

释放序列（析构路径 `0x6AA100` 起）：

```asm
6AA14D  mov  ecx,[esi+0x5F0]
6AA155  je   skip
6AA157  mov  eax,[ecx]; mov edx,[eax]; push 1; call edx   ; slot0(1) = 删除
6AA15F  mov  dword ptr [esi+0x5F0], 0
6AA165  mov  ecx,[esi+0x5F4]
6AA16D  je   skip
6AA16F  mov  eax,[ecx]; mov edx,[eax]; push 1; call edx   ; slot0(1) = 删除
6AA177  mov  dword ptr [esi+0x5F4], 0
```

**裁定**：对象生命周期为"构造 → 赋字段 → 首次使用（slot+3）→ 析构删除并清零 → 可再次构造替换（USE-REPLACE 模式）"。可写为 PROVEN。

## 4. 读取点（全量）

| 读点 | 函数 | 用途 |
|---|---|---|
| `0x6AB146` | `0x6AAE70` | 成功路径取对象，调用 slot+3 |
| `0x6AB99C` | `0x6AB310` | 换入新对象前取旧对象做删除 |
| `0x6AA165` | 析构 | 删除并清零 |
| `0x41DE91` / `0x41DF7A` | 渲染/相机路径 | 与 `[+0x5F0]` 二选一（同型对象，非本协议对象） |

## 5. 与连接/帧字段的关系

| 字段 | 含义（据 E-22/E-23 与实测） | 与本对象关系 |
|---|---|---|
| `[+0xC8]` | 连接状态（1/2/4） | 分派器要求 ==2 才可能到达 `0x6AB310`；失败置 4 |
| `[+0xAC]` | 帧长 | `0x6AB5D1` 读入应答；`0x6AC148` 读入解析 |
| `[+0xB0]` | 载荷对象 | `0x6AC13D` 取数据指针 |
| `[+0x5D0]` | 接收计数器 | 由 `0x6AB2ED` 写 3（与阶段 3 同步） |
| `[+0x5CC]` | **握手阶段** | `0x6ABB01` 由本函数从 1 推进到 2 |
| `[+0x5E0]`/`[+0x620]`/`[+0x624]` | 协商输入（server nonce/长度等） | `0x6AB3A9`/`0x6AB3C6`/`0x6AB5C1` 写入 |
| `[+0x5D8]` | 协商输出 | `0x6AB5A6` 写入 |
| `[+0x52C]`/`[+0x530]` | 32 位能力/NAT 标志 | `0x6AB479`/`0x6AB49E` 读入应答 |

**裁定**：本对象的创建与"握手阶段 1 → 2 的推进"直接耦合；创建发生在 `0x6AB310` 的应答组装完成之后（`0x6ABB01` 置阶段 2 之前）。

## 6. 状态推进与失败

```text
[+0x5CC]==1 且 msgcode==0x81
  └─ 0x6AB310
       ├─ 解析 arg1/arg2/arg3 (0xA878A0)
       ├─ 写 [+0x620]/[+0x624]/[+0x5E0] 协商输入
       ├─ arg1 首 dword == 0xD2 ? 否则 0x6ABB91 失败
       ├─ 构造应答 (0x6AB4C3.., 含 0x400 字节、CLIENTCHAL/BDDATA)
       ├─ 填 [ebx+8]/[ebx+0x10]/[ebp-0x38] 到应答 (0xDF6F97C)
       ├─ 成功 (0x6ABAC0 置 1)
       │    ├─ 构造新 [+0x5F0] 对象 (0x6AB97A)
       │    ├─ 构造新 [+0x5F4] 对象 (0x6AB9DA)
       │    ├─ 调用 slot+1 (0x6AB9FE, vtable+4 = 0xA87C30) 取 0x10 字节
       │    ├─ 0x6AA230(this, data0, data1) 入队/提交
       │    └─ [+0x5CC] = 2   (0x6ABB01)
       └─ 失败 (0x6ABACB 置 0) → 日志 0x43A7C0 → 0x6AAA770 置 [+0xC8]=4
```

**裁定**：成功即推进阶段并换入新对象；失败即终止连接状态。可写为 PROVEN（结构层面）。
