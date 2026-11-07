# PVE-CONNECTION-TEARDOWN-027
# Lobby transport teardown 静态控制流：transport+0x4F4 与 0x84ABA7C 的生命周期

```
TEARDOWN_MECHANISM_CHAIN     = **CONFIRMED**（从 vt[0] 一路到 reconnect 全链已恢复）
CONNECTION_TEARDOWN_PATH     = **PARTIAL**（链完整；**外部触发源未枚举**，见 §7）
H_A_STATUS                   = **STRONG_CANDIDATE**（机制已证，runtime 未证）

4F4_ZERO_WRITER              = **0xB8255A**（位于 transport 析构 0xB824F0 内）
84ABA7C_STATE_VALUES         = {0, 1, 2}（tick 只在 ==1 时跑消息泵）

B82034_ROLE                  = socket 对象方法调用点（传 [transport+0x1610] -> 0xBA0DE0）
BA0DE0_ROLE                  = 写 socket 对象 +0xAE4 的方法
AE4_TEARDOWN_ROLE            = **REFUTED**（+0xAE4 与 transport+0x4F4 无写入关系）

MESSAGE_PUMP_ORDER           = **CONFIRMED A**（同一 tick 内：lock -> pump -> unlock -> 状态判定）
TEARDOWN_ORDER               = **B 适用**（析构由虚槽在 tick 之外触发时，下一 tick 的泵被门跳过）

RUNTIME_632680 = UNKNOWN ; RUNTIME_G6 = UNKNOWN ; RUNTIME_G7 = UNKNOWN
BATTLE_28960   = NOT_OBSERVED
MODIFIED_FILES = NONE（本轮纯静态；新增的 DEV-BOOKING\scripts\_027_iat.py 为只读分析脚本）
```

冻结基线（未改动）：codol_crypto.py = E836C63A... / lobby_server.py = 7BBDC4F2... /
battle_server.py = 71BB7BEB... / nt10.py = DEAA33E8...
未 hook / 未 breakpoint / 未 debugger / 未注入 / 未写内存 / 未 patch / 未启动游戏。

---

## §1 TRANSPORT_OBJECT / TRANSPORT_CONSTRUCTOR

```
0x803830  mov eax,[0x8269774]        <- 单例指针
0x803835  test eax,eax ; jne 0x8038A7
0x803839  push 0x1618 ; call 0xB74220      <- operator new(0x1618)
0x80384A  mov ecx,eax ; call 0xB82130      <- ★ 构造函数
0x803851  mov [0x8269774], eax             <- 存单例
0x80385A  push 0xE39B6E8 ; ...             <- 注册 manager（与 020 的 0x80385A -> 0xB7A400 一致）

TRANSPORT_OBJECT      = singleton [0x8269774]，size 0x1618，vtable **0xD599DC**
TRANSPORT_CONSTRUCTOR = **0xB82130**（由 getter 0x803830 在首次访问时构造）
```

## §2 transport+0x4F4 的全部写入者（网络模块内）

```
| 地址      | 写法                      | 所属函数     | 语义        |
|-----------|---------------------------|--------------|-------------|
| 0xB81EA3  | mov [esi+0x4F4], ebx      | 0xB815E0     | 初始化/基类 |
| 0xB81FFD  | mov [ebx+0x4F4], esi      | 0xB81EF0     | 初始化      |
| 0xB82404  | mov [esi+0x4F4], ebx      | **0xB82130** | **构造函数** |
| 0xB8255A  | **mov [esi+0x4F4], 0**    | **0xB824F0** | ★ **teardown 清零** |

（镜像 0x847155 / 0x8B3F89 / 0xBA92C6 / 0xBA9339 的 +0x4F4 写入属于其它类，与 transport 无关）

4F4_ZERO_WRITER    = **0xB8255A**（唯一把该字段清零的点）
4F4_NONZERO_WRITERS= 0xB81EA3 / 0xB81FFD / 0xB82404（均为构造/初始化）
4F4_INITIAL_VALUE  = **UNKNOWN** —— ctor 里 0xB82404 用寄存器 ebx 写入，本轮未回溯 ebx 的取值
```

## §3 ★ teardown 本体：0xB824F0（transport vtable[0] 的被调目标）

```
0xB82850  = transport vtable **0xD599DC 的槽 0**（refs 0xD599DC 命中该值）
0xB824F0  = 真正的析构/拆除体，唯一调用者 = 0xB82856（在 0xB82850 内）

0x00B824F0  55                 push ebp
0xB8251A  c706dc99d500       mov dword ptr [esi], 0xd599dc        <- 装回自身 vtable（析构特征）
0xB82520  mov [ebp-4], 0x12
0xB82527  e8b4f0ffff         call 0xb815e0                        <- 基类/子对象清理
0xB8252C  8b86f4040000       mov eax,[esi+0x4f4]
0xB82536  test eax,eax ; je 0xB82564
0xB8253A  add eax,4 ; push eax
0xB8253E  ff151481ca00       call dword ptr [0xca8114]            <- socket+4 上的释放/计数调用
0xB82548  8b8ef4040000       mov ecx,[esi+0x4f4]
0xB8254E  test ecx,ecx ; je 0xB8255A
0xB82552  8b01 / 8b10 / 6a01 / ffd2   mov eax,[ecx] ; mov edx,[eax] ; push 1 ; call edx
                                                       <- ★ socket 对象 vtable[0](1) = 释放
0xB8255A  c786f404000000000000 mov dword ptr [esi+0x4f4], 0   <- ★★★ 清零点
0xB82564  lea ecx,[esi+0x460] ; call 0xB76E50
0xB82573  lea ecx,[esi+0x220] ; call 0xBAEA50
0xB82582  lea ecx,[esi+0x204] ; ...
```

即：**先释放 socket 对象，再把 transport+0x4F4 清 0** —— 与"连接被拆除"语义完全一致。

## §4 消息泵的两道门与循环退出

```
0x00B838A0（泵）：
  0xB8392C  cmp dword ptr [esi+0x4f4], 0
  0xB83933  je  0xB83ADE                     <- ★ 门 1：socket 不在 -> 整轮跳过队列
  0xB83939  ... 处理消息 ...
  0xB83A88  mov byte ptr [esi+0x4f8], 1      <- 记录"曾做过清理"（探针里的 net4F8）
  0xB83A9A  cmp dword ptr [esi+0x4f4], 0
  0xB83AA1  jne 0xB83951                     <- ★ 门 2：socket 还在 -> **循环继续处理**
  0xB83AA7  mov ecx,[esi+4] ; call 0xB7A240  <- socket 消失 -> 通知并退出
```

**关键**：泵是一个 **以 transport+0x4F4 非 0 为循环条件** 的循环。因此只要该字段在处理队列的过程中变成 0，
泵会**立即停止继续处理剩余消息**；若在下一 tick 之前就已经是 0，则整轮队列被跳过。

## §5 ★ tick 状态机（0x84ABA7C 的语义）—— 本轮完整恢复

```
0x7F3800  mov eax,[0x84ABA7C]
0x7F3805  sub eax,0 ; je 0x7F386B              <- state 0 -> 0x7F3890 连接/重连
0x7F380B  dec eax ; jne 0x7F3870              <- 只有 state == 1 才继续；其余直接 ret
0x7F380E  call 0x803830                       <- 取 transport
0x7F3819  push 0x81A5570 ; call [0xCA819C]    <- 临界区加锁
0x7F3826  call 0xB838A0                       <- 消息泵
0x7F382B  push 0x81A5570 ; call [0xCA8190]    <- 解锁
0x7F3836  mov ecx,esi ; call 0xB7A670         <- ★ 泵后状态判定（返回 0..4）
0x7F383D  cmp eax,4 ; ja 0x7F3870
0x7F3842  jmp [eax*4 + 0x7F3878]              <- ★ 跳转表
  表项（0x7F3878 起，dword）：
    0x7F3878 -> 0x7F3849  **state = 0**       (index 0)
    0x7F387C -> 0x7F3870  ret（状态不变）      (index 1)
    0x7F3880 -> 0x7F385A  **state = 2**       (index 2)
    0x7F3884 -> 0x7F3849  **state = 0**       (index 3)
    0x7F3888 -> 0x7F3849  **state = 0**       (index 4)

state 0 分支 -> 0x7F3890（连接/重连）：
  0x7F38A4  call 0x803830                     <- 取 transport
  0x7F38AB  test esi,esi ; je 0x7F393E -> 0x7F3943 **state = 0**
  0x7F38B3  movzx eax,word [0x81A9780] ; push 0xE3EC988
  0x7F38C6  call 0xB75370                     <- 组本机大厅地址
  0x7F38DD/0x7F38EE/0x7F38F0 call 0xB983C0 / 0xB9A0E0
  0x7F38F9  push 1 ; push eax ; call 0xB75340 <- 组装 sockaddr
  0x7F3912  call 0xB82070                     <- ★ connect
  0x7F3919  test al,al ; setne cl
  0x7F391E  mov [0x84ABA7C], ecx              <- ★ state = (连接成功 ? 1 : 0)
```

## §6 泵后状态判定 0xB7A670 与连接状态查询 0xBA0780

```
0xB7A670(transport):
  0xB7A673  ecx = [esi+0x4F4]
  0xB7A679  test ecx,ecx ; jne 0xB7A681
  0xB7A67D  **eax = 0 ; ret**                 <- ★ socket 不在 -> 返回 0 -> 跳表 index0 -> state = 0
  0xB7A681  call 0xBA0780                     <- socket 在 -> 查询连接状态
  0xB7A686  cmp byte [esi+0x4F8], 0 ; jne 0xB7A699
  0xB7A68F  cmp eax,2 ; jne 0xB7A699
  0xB7A694  **eax = 1**                       <- transport+0x4F8 == 0 且状态 == 2 -> 强制"保持连接"
  0xB7A699  ret                               <- 否则原样返回 0..4

0xBA0780(socket):
  cmp [ecx+0x644],0 ; eax = [ecx+0xC8]
  ... 返回 1 或 2（其中 [ecx+0x5E8]==3 会 +1）
```

**与运行期探针的交叉验证**：025 探针采样的 t_644 / t_C8 / t_5E8 正是这里的
[ecx+0x644] / [ecx+0xC8] / [ecx+0x5E8]，且实测 t_5E8 出现过 3、t_C8 出现过 1/2/4
-> 说明 0xBA0780 在实际运行中确实在改变返回值，进而改变 tick 的状态判定。

## §7 控制流图（实际地址填充）

```
Lobby state = 1
      |
      v
0x7F3800 tick
      |
      +-- lock 0x81A5570 --> 0xB838A0 泵 --> unlock
      |        |
      |        +-- transport+0x4F4 != 0 -> 处理队列（循环 0xB83A9A 复核）
      |        +-- transport+0x4F4 == 0 -> 0xB83ADE 跳过；并置 [transport+0x4F8]=1
      |
      +-- 0xB7A670
      |        +-- [4F4]==0            -> 返回 0 -> 跳表 -> **state = 0**
      |        +-- status==2 且 4F8==0 -> 返回 1 -> state 保持 1
      |        +-- 其它               -> 原样 0/2/3/4 -> state = 0 或 2
      |
      v
state = 0 的下一 tick -> 0x7F3890 -> 0xB82070 = connect -> 0x7F391E state = 1/0（重连）

拆除侧（**外部触发**，见下）：
  transport vtable[0] = 0xB82850
        -> call 0xB824F0
             0xB8253E call [0xCA8114]（socket+4）
             0xB82552 socket->vt[0](1) 释放
             0xB8255A **[transport+0x4F4] = 0**        <-- ★ 唯一清零点
        -> 下一 tick 的泵命中 0xB8392C 门 -> 跳过队列
        -> 0xB7A670 返回 0 -> state = 0 -> 重连
```

**未闭合的一环（诚实标注）**：0xB82850 是 **虚函数槽（vtable[0]）**，
其调用者是**间接调用**，无法用 rel32 引用枚举 -> **外部触发源 = UNKNOWN**。
因此按任务书 §16，CONNECTION_TEARDOWN_PATH = PARTIAL（机制链 CONFIRMED，触发源未枚举）。

## §8 顺序关系（任务书 §12 的 A/B/C）

```
A（同一 tick 内 pump 先于状态判定）：**CONFIRMED**
  0x7F3826 pump -> 0x7F382B unlock -> 0x7F3836 0xB7A670 -> 跳表改 state
  => 一次 tick 内，泵总是先跑完，其后才可能把 state 置 0。

B（拆除先于下一 tick 的泵）：**适用**（H-A 的机制）
  如果拆除（0xB824F0，可由虚槽在 tick 之外触发）把 transport+0x4F4 清 0，
  那么下一 tick（若 state 仍为 1）的泵会在 0xB8392C 直接 je 跳过整轮队列；
  若同一 tick 内就清 0，泵的循环条件 0xB83A9A 会立即退出（剩余消息不处理）。

C（同一临界区内 teardown -> pump）：**未发现**（拆除体不在 0x7F3800 的临界区内被调用）
```

## §9 B82034 / BA0DE0 / +0xAE4

```
0xB82034（在 0xB82030 所在的连接相关函数内）：
  0xB82034  mov eax,[ebx+0x1610]        <- transport 的 +0x1610 字段
  0xB8203A  mov ecx,[ebx+0x4F4]         <- socket 对象
  0xB82041  call 0xBA0DE0               <- 以 (socket, transport+0x1610) 调用
0xBA0DE0 的调用者：0xB7A657 与 0xB82041（共 2 处）
0xBA0DE0 入口即 mov [ecx+0xAE4], eax（0xBA0DE6）-> **它写的是 socket 对象的 +0xAE4**
+0xAE4 的读写点全部落在 0xBA0DE0 / 0xBA24C9 / 0xBA3396 / 0xBA29E0 这一族（socket 对象）
=> **+0xAE4 与 transport+0x4F4 之间没有任何写入/清零关系**
=> AE4_TEARDOWN_ROLE = **REFUTED**（不再扩大）
```

## §10 closesocket / shutdown 的定位限制（INSTRUMENTATION_BLOCKED）

```
本镜像的 IAT 槽（0xCA8114 / 0xCA8128 / 0xCA8364 / 0xCA8548）在文件里已经是**运行期解析后的地址**
（0x116D0190 等），无法从镜像还原导入名。
并且按名扫描：closesocket / WSASocketW / WSAConnect / sendto **在镜像中完全不存在**
（字符串表里没有这些名字）。
=> CLOSESOCKET_CALLERS_RELEVANT_TO_TRANSPORT = **INSTRUMENTATION_BLOCKED**
=> SHUTDOWN_CALLERS_RELEVANT_TO_TRANSPORT    = **INSTRUMENTATION_BLOCKED**
（机制不需要它：0xB824F0 已明确"释放 socket 对象 -> 清 0x4F4"）
```

## §11 0x84ABA7C 的写入者与状态取值

```
[W] 0x7EEAEE  mov [0x84ABA7C], 0
[W] 0x7EF30E  mov [0x84ABA7C], esi
[W] 0x7F28A9  mov [0x84ABA7C], esi        （DW_LOBBY_CONNECTED 附近）
[W] 0x7F3849  mov [0x84ABA7C], 0          （tick 判定的 index 0/3/4 -> teardown）
[W] 0x7F385A  mov [0x84ABA7C], 2          （index 2 -> 停用态）
[W] 0x7F391E  mov [0x84ABA7C], ecx        （连接结果 -> 1/0）
[W] 0x7F3943  mov [0x84ABA7C], 0          （无 transport -> 0）
[R] 0x5C2D62 / 0x5C2DAE / 0x5D3526 / 0x617334 / 0x67CAD1 / 0x7F37B0 : cmp [0x84ABA7C], 2

84ABA7C_WRITERS     = 上述 7 个真实存储
84ABA7C_STATE_VALUES= {0, 1, 2}（读侧只比较 2；tick 侧 0=重连、1=跑泵、2=不动作）
```

## §12 结论

```
TEARDOWN_MECHANISM_CHAIN = CONFIRMED
  transport vt[0]=0xB82850 -> 0xB824F0 -> 释放 socket -> **0xB8255A transport+0x4F4 = 0**
  -> 下一 tick 泵 0xB8392C 跳过（或同 tick 内 0xB83A9A 退出循环）
  -> 0xB7A670 返回 0 -> tick 跳表 -> state=0 -> 0x7F3890 重连

CONNECTION_TEARDOWN_PATH = PARTIAL（唯一缺口 = 虚槽 vt[0] 的**外部调用者**，间接调用无法静态枚举）

H_A_STATUS = STRONG_CANDIDATE（机制已静态证实；仍**没有** runtime 证据表明这一次 accepted push 确实走了该路径）
H_B_STATUS = REFUTED（来自 025）
RUNTIME_632680 / G6 / G7 = UNKNOWN
BATTLE_28960 = NOT_OBSERVED
MODIFIED_FILES = NONE
```

（全文完 · 纯静态 · 未修改任何被禁止的文件）
