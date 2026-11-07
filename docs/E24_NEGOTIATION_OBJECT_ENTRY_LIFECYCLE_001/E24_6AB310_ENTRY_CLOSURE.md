# E24 `0x6AB310` 入口闭合

## 1. 映像与地址口径

- 冻结恢复镜像 SHA-256 = `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`（复核一致）。
- ImageBase = `0x400000`。本文地址默认 RVA；等价 VA = RVA + `0x400000`。
- `0x6AB310` RVA ↔ VA `0xAAB310`，属 `.text`（VA `0x001000..0x7AD90B`）。

## 2. 函数边界与序言

`0x6AB310` 起点由反向 `0xCC` 填充确定（前一条指令为 `ret 0xc`，`0x6AB306..0x6AB30F` 为 `0xCC`）：

```asm
6AB310  push ebp
6AB311  mov  ebp, esp
6AB313  push -1
6AB315  push 0xB98749          ; SEH scope table
6AB31A  mov  eax, fs:[0]
6AB321  sub  esp, 0x194
6AB331  push ebx / esi / edi
6AB33E  mov eax,[ebp+0xC]      ; arg2
6AB341  mov ebx,[ebp+0x10]     ; arg3
6AB344  mov esi,[ebp+8]        ; arg1
6AB349  mov edi, ecx           ; this
...
6ABB8E  ret 0xC
```

**调用约定：thiscall（ECX=this）+ 3 个栈参数，`ret 0xC`。**

对应 `0x6AC192` 处调用形态（`0x6AC18A..0x6AC192`）：

```asm
6AC18A  mov  edx,[ebp-0x14]    ; 解析出的负载缓冲指针
6AC18D  push edi               ; arg3 = 有效长（[esi+0xAC]-1）
6AC18E  push edx               ; arg2 = 负载指针
6AC18F  push ebx               ; arg1 = 帧缓冲基址
6AC190  mov  ecx, esi          ; this = 会话对象
6AC192  call 0xAAB310          ; == RVA 0x6AB310
```

## 3. 入口闭合（三种入口形式逐一排查）

| 入口形式 | 方法 | 结果 |
|---|---|---|
| 直接 `E8` | 全 `.text` rel32 扫描，`target = insn_VA+5+rel` | **1 处**：`0x6AC192` |
| `E9` 跳板 | 同上扫描 opcode `0xE9` | **0 处** |
| 函数指针表 / vtable | 全文件 4 字节扫描 VA 形式 `00AAB310` 与 RVA 形式 `006AB310` | **均 0 命中** |
| `.rimp` 修复 | `.rimp` 全量字节扫描（VA/RVA 形式） | **0 命中** |
| TLS 回调 | 数据目录 TLS `AddressOfCallBacks` 数组首元素 | `0x00000000`（空） |

**裁定**：`0x6AB310` 的入口是**唯一直接调用**，不存在跳板、函数指针或间接注册路径。可写为 PROVEN。

## 4. 上游触发条件

调用链（自外向内）：

```text
0x68EEF1 / 0x68F02C   会话循环
   call 0x6AC3D0      跳板: push ebp; mov ebp,esp; pop ebp; jmp 0x6AC0C0
0x6AC0C0   会话分派器 (thiscall, 2 栈输出参数, ret 8)
  6AC0EA  cmp [esi+0xC8], 4      ; 已失败 -> 返回 false
  6AC10E  cmp [esi+0xC8], 2      ; 必须处于"进行中"
  6AC121  call 0x6AABE60         ; 维护/推进
  6AC130  call 0x6A9570          ; 准备
  6AC13D  mov  ecx,[esi+0xB0]    ; 载荷对象
  6AC143  call 0xDF4A028         ; .tvm0: 取数据指针
  6AC148  mov  edi,[esi+0xAC]    ; 帧长
  6AC168  call 0xA85AD0          ; 解析出 msgcode(= [ebp-0xE]) 与 offset(= [ebp-0x14])
  6AC178  mov  eax,[esi+0x5CC]   ; 握手阶段
  6AC17E  cmp  eax, 1
  6AC183  mov  al,[ebp-0xE]      ; msgcode
  6AC186  cmp  al, 0x81          ; 阶段1 + 0x81 -> 0x6AB310
  6AC192  call 0xAAB310
```

判定逻辑（`0x6AC178..0x6AC2F7`）可整理为：

| 阶段 `[esi+0x5CC]` | msgcode | 目标函数 |
|---|---|---|
| 1 | `0x81` | `0x6AB310`（**本论**） |
| 1 | `0x04` | 失败路径 `0x6AAA770` |
| 2 | `0x83` | `0x6AB260` |
| 2 | `0x84` | `0x6A9690`（分配私有对象 0x1C） |
| 3 | `0x85` | `0x6AAE70`（HMAC/计数器校验） |
| 3 | `0x84` | `0x6A9690` |
| 其他 | — | `0x6AC38C` 日志 + `0x6AAA770` |

**裁定**：`0x6AB310` 受"连接状态 `[+0xC8]==2`"与"握手阶段 `[+0x5CC]==1` + 报文码 `0x81`"双重控制。可写为 PROVEN。

## 5. 与 E-23 的差异

E-23 `E23_NEXT_GATE_DECISION.md` 记录："`0x6AB9D8` 所在函数（起点 `0x6AB310`）……当前 rel32 搜索得 0 —— 说明它可能经跳板/间接调用"。

实测：E-23 自带工具 `_tools/t21_callers2.py` 运行即输出 `RVA 0x6AB310 VA 00AAB310 : 1 ['0x6ac192']`，与报告结论矛盾。这是**报告与自有工具不一致**，非证据冲突。裁定为 REFUTED 并记入负向证据。
