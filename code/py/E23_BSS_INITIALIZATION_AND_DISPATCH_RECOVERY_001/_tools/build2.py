# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001")
files={}

files["E23_TLS_RIMP_AND_CONSTRUCTOR_AUDIT.md"]=r'''# E23 TLS / .rimp / 构造器审计

## 1. TLS 目录

| 项 | 值 | 说明 |
|---|---|---|
| TLS 数据目录 RVA | 0x008D7E00 | Size 0x00000018，位于 `.rdata` |
| StartAddressOfRawData | 0x0DD4E000 | = `.tls` 节区起点 |
| EndAddressOfRawData | 0x0DD4E018 | 24 字节 TLS 模板 |
| AddressOfIndex | 0x01867E44 | TLS 索引槽 |
| AddressOfCallBacks | 0x00BB33E0 | RVA 0x7B33E0，位于 `.rdata` |
| SizeOfZeroFill | 0x00000000 | 无零填 |
| Characteristics | 0x00000000 | — |
| **TLS 回调数组** | **首元素 = 0x00000000（空）** | 无 TLS 回调 |

**裁定**：**不存在 TLS 回调链**。因此"五个目标是否由 TLS 回调在加载期写入"这一路径被**排除**——没有任何回调可执行写入。

## 2. .rimp 修复表

| 项 | 值 |
|---|---|
| 节区 | `.rimp` VA 0x0DC11000，VirtualSize 0x00002964，RawSize 0x00002A00 |
| 非零字节 | 8863 / 10752 |
| 首 16 dword | 0x0DC1126C, 0x0DC11168, 0x007AE000, 0x0DC112C4, 0x0DC112A4, 0x007AE038, 0x0DC11478, 0x0DC112CC, 0x007AE040, 0x0DC11530, 0x0DC114C8, 0x007AE090, 0x0DC12118, 0x0DC11548, 0x007AE0A8, 0x0DC123A8 |

- `.rimp` 中的高地址密集落在 `0x0DC11xxx..0x0DC13xxx`（即 `.rimp` 自身范围）与 IAT RVA `0x007AE000` 附近，呈现"重定位/导入修复对（目标 RVA，导入槽 RVA）"特征。
- 对五个目标地址（VA 与 RVA 两种形式）、vtable `0xC5A31C`/`0xC5B0A4`、以及 `0xA87D50`/`0xA878A0`/`0xA85AD0`/`0xAAAE70` 做 4 字节精确扫描，**`.rimp` 中命中数均为 0**。

**裁定**：`.rimp` **不包含**指向五个目标或相关 vtable 的修复记录。五个目标不依赖 `.rimp` 重定位。

## 3. 显式构造器 / 初始化函数

- 对五个目标的 RVA（`.text` 内）启动 `0xCC` 反向扫描得到函数起点，均为标准 `push ebp; mov ebp,esp` 序言；**没有任何"构造器式"的 vtable 写入**（无 `mov dword ptr [reg], <vtable>` 写入这五个地址）。
- 与 `[edi+0x5F4]` 相关的构造器为 `0xA87BA0`（RVA 0x687BA0）：

```asm
687BC9  push 0x10
687BCB  call 0xA888A0          ; 基类构造
687BD0  push 0xC5BEB0          ; 类型描述符
687BDC  mov dword ptr [esi],0xC5A31C   ; <== 写入 vtable
687BE2  call 0xACBAF0
```

其静态调用者仅两个：`0x6AB97A`、`0x6AB9DA`（均在 RVA `0x6AB9xx` 段内，即设置 `[edi+0x5F4]` 的函数）。

## 4. 三重否定结论

| 机制 | 是否存在指向五个目标的写入 | 证据 |
|---|---|---|
| TLS 回调 | 否（回调数组为空） | 数据目录 TLS，AddressOfCallBacks 数组首元素=0 |
| .rimp 修复记录 | 否（0 命中） | `.rimp` 4 字节精确扫描 |
| 显式构造器/vtable 写入 | 否 | 无对五地址的 `mov [reg],imm`；C++ 构造器不作用于代码地址 |

## 5. 真实来源

五个目标**不需要**"初始化写入者"：它们是 `.text` 中的普通被调用函数，其"来源"就是 PE 磁盘镜像本身。E-22 所设的"BSS 加载期初始化"问题在基准纠正后**自动消解**，而非"仍未找到"。
'''

files["E23_INDIRECT_DISPATCH_RECOVERY.md"]=r'''# E23 间接分派恢复

## 1. 恢复镜像中的间接调用工具（`.tvm0`）

调用点中反复出现的高地址经节区映射后确认位于 `.tvm0`（VA 0x0D958000..0x0DC11000，可执行）：

| 调用点目标（VA） | RVA | 节区 | 用途（按调用形态） |
|---|---|---|---|
| 0x0DF4A028 | 0xDB4A028 | .tvm0 | 取"帧缓冲"数据指针（`mov ecx,[esi+0xB0]; call`） |
| 0x0DF9AA45 | 0xDB9AA45 | .tvm0 | 分配器（`push size; call`） |
| 0x0DF6216D | 0xDB6216D | .tvm0 | 结构拷贝/构造（`push 0x14; lea; call`） |
| 0x0DF6F97C | 0xDB6F97C | .tvm0 | 字段存储（`push len; lea; mov ecx; call`） |

说明：`.tvm0` 是**可执行区**且有完整磁盘字节（RawSize 0x2B8C00，VirtualSize 0x2B9000），与 `.data` BSS 无关。E-21 曾把 `.tvm0` 描述为"VM 混淆、线性反汇编不可靠"，本轮不改变对该区语义的判断，只确认上述调用的**目标地址与入口形态**。

## 2. 五个目标与间接分派的关系

- 五个目标**自身**不是间接分派目标：全文件对其做 VA/RVA 4 字节指针扫描命中 0/1 次，说明它们没有被放入任何函数指针表。
- 它们由 354 个**直接** `E8` 调用点调用（1+36+96+125+96），而非通过 `FF /2` 间接调用。
- 因此"五个地址是隐藏分派表项"的假设**被证伪**。

## 3. `[edi+0x5F4]` 的间接分派

`0x6AAE70` 成功路径 `0x6AB140` 起的序列：

```asm
6AB140  mov eax,[ebp-0x220]        ; span 长度
6AB146  mov ecx,[edi+0x5F4]        ; 协商对象指针（this）
6AB14C  mov edx,[ecx]              ; vptr
6AB14E  mov edx,[edx+0xC]          ; slot 3（以对象首为 vptr[0]）
6AB151  push eax                   ; arg4: len
6AB152  mov eax,[ebp-0x210]        ; span 缓冲基址
6AB158  push eax                   ; arg3
6AB159  push eax                   ; arg2
6AB15A  lea eax,[ebp-0x50]
6AB15D  push eax                   ; arg1
6AB15E  call edx
6AB160  test al,al                 ; 返回布尔
6AB166  je 0xAAB24D                ; 失败分支
```

- vtable = `0xC5A31C`（`.rdata`，RVA 0x85A31C）。
- vptr[+0xC] 槽 = `0xA87D50`（RVA 0x687D50）。

### slot+3（0xA87D50）语义

```asm
687D50 push ebp; mov ebp,esp
687D53 mov eax,[ebp+8]        ; arg1 -> 临时缓冲
687D58 lea esi,[ecx+0xC]      ; this+0xC
687D5B push esi; push 0x10; push eax
687D61 call 0xACE180          ; 长度/哈希校验（cmp [ecx], len 形态）
687D69 test eax,eax; jne 0xA87D8E (失败->日志 0x43A7C0)
687D6D mov ecx,[ebp+0x14]     ; arg4 长度
687D70 mov edx,[ebp+0x10]     ; arg3
687D73 mov eax,[ebp+0xC]      ; arg2
687D76 push esi; push ecx; push edx; push eax
687D7A call 0xACE1B0          ; 流/缓冲递交
687D82 test eax,eax; jne 失败
687D86 mov al,1; ret 0x10
```

即：`slot+3(this, arg1, arg2, arg3, arg4)` — this 为 `[edi+0x5F4]`，对 `this+0xC`（一个 0x10 字节取数据/摘要）做校验后把 `arg2/arg3` 描述的缓冲（长 `arg4`）递交到 `0xACE1B0`，成功返回 1。

## 4. `[edi+0x5F4]` 的写入者与对象来源

| 位置 | 指令 | 含义 |
|---|---|---|
| 0x6AB9B3 | `mov dword ptr [edi+0x5F4],0` | 清空字段 |
| 0x6AB9E7 | `mov dword ptr [edi+0x5F4],eax` | 写入新对象指针 |
| 0x6AB9D8 | `mov ecx,eax; call 0xA87BA0` | 构造该对象 |

构造器 `0xA87BA0` 写入 vtable `0xC5A31C`。
`[edi+0x5F4]` 的全文件读取点：`0x6AB146`（成功路径）、`0x41DE91`、`0x41DF7A`。

## 5. 与五个目标的关系裁定

- 五个目标与 `[edi+0x5F4]` **同族但不同角色**：它们是 `.text` 低层的"缓冲区 Range/memcpy 与字段分派"辅助；`[edi+0x5F4]` 对象（vtable `0xC5A31C`）是"协商/参数"高阶对象。
- 二者通过对象构造链相邻（`0xA87BA0` 构造器紧邻 `0xA878A0`/`0xA87830` 辅助），但**没有指针边**把五个目标放进该 vtable。
- 因此：**不能**把五个目标当作 `[edi+0x5F4]` 的虚表槽位；E-22 若曾暗示此关系，本轮予以切断。
'''

files["E23_E22_SUCCESS_PATH_CROSSWALK.md"]=r'''# E23 与 E-22 成功路径交叉核对

## 1. E-22 主张 vs 本轮实测

| 编号 | E-22 主张 | 本轮实测 | 裁定 |
|---|---|---|---|
| E22-1 | `0x6AC0C0` 为 thiscall，返回 bool，两个栈输出参数，`ret 8` | 序言 `8B F1`(this=ECX)；`ret 8`；`0x6AC234 mov byte [eax],4` 证实输出状态字节 | 一致（PROVEN） |
| E22-2 | `0x6AAE70` 唯一调用点 `0x6AC2F0`，thiscall + 5 栈参，`ret 0x14` | 调用者命中仅 `0x6AC2F0`；尾声 `ret 0x14` | 一致（PROVEN） |
| E22-3 | `0x6AC3D0` 是跳板 | `push ebp; mov ebp,esp; pop ebp; jmp 0xAAC0C0` | 一致（PROVEN） |
| E22-4 | `0x6AC3D0` 调用者 `0x68EEF1`/`0x68F02C` | rel32 命中恰为 `0x68EEF1`、`0x68F02C` | 一致（PROVEN） |
| E22-5 | 接收计数器 `[edi+0x5D0]` 读/递增/比较 | `0x6AAFA4/6AAFAD` 读写，失败置 `Bad recv counter` | 一致（PROVEN） |
| E22-6 | 16 字节 XOR/OR 比较 → `HMAC mismatch` | `0x6AB0E6..0x6AB12D` 吻合 | 一致（PROVEN） |
| E22-7 | `0xA85AD0` 等位于 `.data` BSS 虚拟尾部，磁盘无字节 | 按 **VA**→`.text`（有无字节、可反汇编）；仅按 RVA 才是 `.data` BSS | **REFUTED**（基准错误） |
| E22-8 | `[edi+0x5F4]` 为虚表调用（成功路径） | 确为虚表调用，但 `[edi+0x5F4]` 是**对象指针**，vtable `0xC5A31C`，slot+3 `0xA87D50` | 部分一致（已细化） |

## 2. 成功路径完整交叉核对

```text
0x68EEF1/0x68F02C  会话循环
        call 0x6AC3D0            ; 跳板
 0x6AC3D4   jmp 0xAAC0C0         ; 0x6AC0C0 实体
 0x6AC0EA   cmp [esi+0xC8],4     ; 已失败即返回 false
 0x6AC109   call 0xAAA7B0        ; 维护
 0x6AC10E   cmp [esi+0xC8],2     ; 非 2 跳过
 0x6AC13D   mov ecx,[esi+0xB0]; call 0xDF4A028  ; 取帧缓冲
 0x6AC148   mov edi,[esi+0xAC]; dec edi         ; 有效长
 0x6AC168   call 0xA85AD0        ; 解析（本论目标 #1）
 0x6AC178   mov eax,[esi+0x5CC] ; 消息码
   ├─ ==1: 0x81 -> 0xAAB310 ; 0x04 -> 0xAAA770
   ├─ ==2: 0x83 -> 0xAAB260 ; 0x84 -> (分配对象)
   └─ ==3: 0x85 -> call 0x6AAE70
 0x6ACE70   0x6AAE70 内 HMAC/计数器校验
   ├─ 失败: 日志 0x43A7C0 -> 0xAAA770 置状态 4
   └─ 成功 0x6AB140:
         mov ecx,[edi+0x5F4]        ; 协商对象
         mov edx,[ecx]; mov edx,[edx+0xC]
         push len; push buf; push buf; push tmp
         call edx                   ; slot+3 = 0xA87D50
```

## 3. E-22 成功路径 `[edi+0x5F4]` 调用的最终解释

- E-22 若把该调用归因于"BSS 虚表（0xA85AD0 一族）"，则**不成立**：vtable 在 `.rdata`（`0xC5A31C`），目标是 `.text` 的 `0xA87D50`。
- 该调用可解释为：**HMAC/计数器校验通过后，把已解析的载荷（span 缓冲，长 `[ebp-0x220]`）经协商对象 slot+3 递交（做二次长度/摘要校验后流入 0xACE1B0）**。
- 因此 E-22 的"成功返回后缓冲区交接"在**对象层面**得到解释（交给 `[edi+0x5F4]` 对象的 slot+3），但该对象**与五个目标无指针关系**。

## 4. 修正后的方向判定

| 假设 | E-22 | 本轮修正 |
|---|---|---|
| H1 入站 HMAC 验证 | INFERRED（强） | 维持（帧码 0x85 + recv counter + HMAC 串） |
| H2 出站签名 | WEAK | 维持弱 |
| H3 收发共用会话/计数器 | INFERRED（强） | 维持 |
| "五地址为 BSS 隐藏目标" | E-22 结论 | **REFUTED**：五地址为 `.text` 辅助函数 |

方向判定本身未因基准修正而改变；改变的是"下游目标不可静态分析"的阻塞强度。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
