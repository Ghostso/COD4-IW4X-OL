# CODOL 大厅协议攻坚 · 交接手册（第二版）

会话日期：2026-09-29
详细报告：`CODOLServer/SESSION_APPEND_20260929_STAGE3_SUCCESS.md`（52 节）
上一版：`CODOLServer/HANDOFF_20260928_LOBBY_PROTOCOL.md`（**已过期，多处结论被推翻，见 §3**）

**当前状态：CODO 大厅侧全部闭合（①~④ + 大厅对象校验 + uA50=5）。
⑤ 无法在现有手段（只读采样 + 本地探针 + 配置文件）下闭合** ——
已查明这不是"补一条帧/回一个包"能解决的，而是需要一整套
DW（Demonware）子系统：远程配置服务（下发 dw_config / cross_zone_*）
+ 一条可用的 OOB 可靠控制通道（见报告 §44，含结论与可选出路）。
以下是完整的定位过程与证据，对后续任何实现都直接可用。

**⑤ 未闭合，且已查明现有手段无法闭合**（证据链见 §36–§44）：

```text
关键字段  [0x00E85C68 + 0x1F4]   1（连接中） -> -2（断开）
          +47.6 s（真实 stun 主机）/ +23.2 s（本地）
断线入口  0x7EEBC1 -> 0x621810 -> cppOnDWDisconnected
          +4.4 s 后弹「与大厅服务失去连接」
直接原因  DW 发报机 0xBBAD10 -> 0xBBA870 -> 0xBBA6D0 每一次都失败
          （[dw+0x1A0] "在途"标志恒 0；约 12.2 s 重试一次，4 次后放弃）
失败下游  0xBBA6D0 = 序列化 + 传输对象 vtable[+0x18] 发送
          需"远程配置服务"下发 dw_config / cross_zone_*，
          并需一条可用的 OOB（Demonware 可靠控制）通道
```

**因此"52 秒"不是协议常量**（= 20 × ICMP 超时，见 §39/§41），
**"往 UDP/3074 回包"也全部无效**（客户端用的是 `IcmpSendEcho`，
根本不看 UDP —— 三次实验均否证，见 §39/§40.8）。

**已定性的根：DW 配置对象从未被创建**（§45.5，run 175325 实测）：
```text
[0x00C7AEAC0]（配置已加载）= 0x00   全程
[0x033E6A00]（DW 配置对象）= 0       全程
=> 0x50BC70(...) 的每一次配置读取前面都有
   `cmp byte [0xC7AEAC0],0 / je skip`，因此**全部被跳过**；
   DW 层完全跑在硬编码默认值上，连 STUN 目标、保活周期、
   dw_disconnect_oob_always 这些开关都拿不到。
全镜像对这两个全局共 705 处引用，**没有一处直接写入** ——
它们由配置模块以计算地址填充，而该模块在本环境从未生效。
```

**结论（报告 §52–§55）：第一档 ⑤ 在不修改 `.text`、且不规避反作弊的
前提下不可闭合。** 四条路线全部封闭：

三条"补资产"路线全部封闭，其中两条为实测否证：
```text
路线 1  放 mp/marketplace.json 普通文件  -> 实测无效（§48.7）
路线 2  解 .ifs 得 .ff 放进 main\        -> 实测启动失败（§50.11）；
        根因：装载器由**硬编码清单**驱动，扫目录不管用（§51）
路线 3  修改 zone 清单                   -> 清单是 .text 里的立即数栈数组
        （0x4FCC00 = 4 项 / 0x4FCCA0 = 5 项，都是 mov [ebp-x], imm32）
        => 改它**就是改 .text**（§52）
路线 4  dvar / config_mp.cfg / 命令行    -> config_mp.cfg 是引擎加密格式；
        那些 DW 键是 UI 元素（0x770940/0x770890 push 类型 5），
        不是 dvar，无法从外部 set（§55）
```

**已定位 ⑤ 的最终阻塞点**：
```text
整条链是：
  缺 mp/marketplace.json
    -> 0x4A93E0 在 0x4A936E 处"取不到资源"直接返回（gec 恒 0）
    -> [0x82C4A88] 停在 0（应为 0->1->2->3）
    -> 0x4A9955 的 `cmp [0x82C4A88],3` 不成立，永远不调 0x50E930(6)
    -> [0x33E6A00] 配置容器从未建立（cfgobj 恒 0、cfg 恒 0）
    -> 所有 dw_config 键读不到（STUN_*、dw_disconnect_oob_always …）
    -> DW 用硬编码默认值 -> 发送链每次失败 -> [dw+0x1F4] 停在 1
    -> +47.6 s（真实 stun）/ +23.2 s（本地）后置 -2 -> 弹窗 -> DELETE /queue
实测证据（run 180646）：gate=0 mode=0 gec=0 cfg=0 cfgobj=0 全程不变；
                        且 g2f=0x01、rc8=2 —— 说明不是被别的条件挡住，
                        而是 0x4A93E0 这个函数**从未被执行**。
```

**闭合条件（首次可执行，且不需要碰 .text）**：
```text
在客户端的资源系统里提供一个名为 `mp/marketplace.json` 的资源，
其 JSON 至少含 "version" 字段（0x4A93A9 push 0xDB6CD8 = "version"）。
那是它本来会向服务端索取的东西 —— 属"补服务端资源"，不是改代码。
验收：POST83_WATCH 的 gec 0->1、gate 0->3、cfg 0->1、cfgobj!=0，
      最终 dw+0x1F4 == 2 且握手后 60 s 内无弹窗。
```

**若用户愿意放宽边界**，另有一条（报告 §44.4）：
```text
a) 放宽安全边界：在 [dw+0x1F4] 写入点或 0xBBA6D0 返回处做代码级干预
   （属改 .text，需用户明确授权）；
```

**注意**：`DELETE /queue` 是断线后的清理，不是原因（§33）；
「服务端发帧续命」已被否证（§35）。第二档未开始。

---

## 0. 一句话状态

握手前 3 步已经能稳定实跑成功（`0x81 → 客户端 0x82 → 0x83` 校验通过，
`[req+0x5E8]=3 / 0x5EC=1 / 0x5F0=1`）。去掉观察器对
`[req+0x644]`/`[mgr+0x4F8]` 的外部写入后，干净运行已命中
`644=0 -> BA457E..BA45B2`，原来的约 32 ms 复位不再出现；客户端随后主动
发送多片 `0x85` 数据，但约 **52.0 秒**（固定值，两次运行都是 51.98/52.00 s）
后仍弹「致命错误 / 与大厅服务失去连接」。

当前阻塞点已收敛为一句：

```text
大厅链路已全部打通（主机/端口注入 -> 0x81 -> 0x82 -> 0x83 -> 644==0
-> 队列校验 lob1400=8900 / lob240=2 -> uA50=5）。唯一缺口是一个
**与入站流量无关的 52.0 秒计时器**：从 0x83 成功起算，到点即
标记大厅断开（lob240: 2->3）、弹窗，随后才 DELETE /queue 做自我清理。

关键否证（§35）：post-83 扩窗采样（16 ms 分辨率、4770 点）显示
[req+0x9C] 全程恒为 1、[req+0x5E8] 恒为 3 —— 客户端读帧器
0xBA20A0 在这 52 秒里一次都没执行。且「完全不发」与「每 1 秒发 4 字节」
的断线时刻完全相同（都是 52.0 s）。

=> DELETE /queue 是断线的**结果**，不是原因；不要再围绕它做实验。
=> 「服务端持续发帧就能续命」也是错的；不要从读路径入刀。
```

---

## 1. 环境与入口

```
根目录        D:\BaiduNetdiskDownload\使命召唤OL
提权代理      python -X utf8 CODOLServer\_mainline\agent_client.py ping
              （期望 {"ok": true, "debug_privilege": true}；本机 pid 9092）
启动链闸门    run_codol_001\sandbox_ifs1_20260923\iips.ini → enable_iips=1
解码镜像      CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
              加载基址 0x400000（所有反汇编地址都按此基址）
观察器源码    restore_iips_contract_001\observer2\AboProbe.cs
观察器发布    restore_iips_contract_001\observer2\out\AboProbe.exe
              （launch 脚本从 observer2\out\ 加载，改完必须重新 publish）
探针          CODOLServer\lobby_server\lobby_plain_probe.py
轮次驱动      CODOLServer\_mainline\auto_lobby_loop.py
反汇编工具    CODOLServer\_mainline\_dis_va.py <start:end>
              CODOLServer\_mainline\_xref_call.py <target>...
              CODOLServer\_mainline\_scan_disp.py <disp>
连接生命周期  CODOLServer\_mainline\_conn_lifecycle.py <game_etw.jsonl>
              （从 AFD ETW 汇总 connect/accept/收发计数，无需解码负载）
状态时间线    CODOLServer\_mainline\_state_timeline.py <state.csv>
              （折叠为状态跃迁；已处理 CSV 的 UTF-8 BOM）
```

磁盘：跑测试前确认 D 盘有空间（曾因满盘导致 AFD ETW 启动失败）。

---

## 2. 复现命令

### 2.1 最短可用路径（能稳定打到 `5E8=3`）

```powershell
# 1) 明文大厅探针（路径必须传绝对路径）
python -X utf8 CODOLServer\lobby_server\lobby_plain_probe.py `
  --bind 127.0.0.1 --port 8446 --log <ABS_LOG> --lobby-handshake `
  --magic 0xDC --token 0x1122334455667788 `
  --ready-file <ABS_READY> --ready-timeout 90 --echo-file <ABS_ECHO> `
  --hold-after-83 15

# 2) 提权链
python -X utf8 CODOLServer\_mainline\auto_lobby_loop.py --rounds 3 --seconds 100 `
  --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 --poke-lobby-globals `
  --lobby-ready-only --handshake-ready-file <ABS_READY> `
  --handshake-echo-file <ABS_ECHO> `
  --post83-trace --abort-on-cfg0
```

### 2.2 成功判据（**务必看这个，不要看驱动脚本的输出**）

```text
CODEC_TRANSITION  s9c=4  5e8=3  5ec=1  5f0=1  640=220
POST83_SAMPLE     s9c=1  5e8=3  644=0
随后 1--2 秒内没有 C8=4 / 5e8=0 的 32 ms 复位
```

这只是「第一档第④步的立即分支已通过」判据，不是最终大厅成功。最终验收
还必须覆盖握手后 **≥ 60 秒**（看门狗 52.0 秒）窗口，并且不能出现
「致命错误 / 与大厅服务失去连接」。注意：达标的是「握手后 60 秒无弹窗」，
不是「lob1400=8900 / uA50=5」——后者在不发帧时也能到（§33）。

⚠️ `auto_lobby_loop.py` 打印的 `SUCCESS: client reported DW_LOBBY_CONNECTED`
**是假成功**：它只反映 DW 状态机走到 `uA50=5`，在探针
`sent81=false`（根本没发握手）时也会打印。已实测复现。

### 2.3 启动 flake

约 20–40% 的启动无状态退出；`cfg_applied=0` 会退化成 stage 10 fallback。
用 `--abort-on-cfg0` 快速淘汰。**一次成功的干净命中平均要 3–8 次尝试**，
不要因为前几次没状态就改参数。

---

## 3. 上一版手册中被推翻的结论（先读这一节）

第二版会话期间发现旧手册多处错误，照旧执行会继续走岔：

| 旧说法 | 实际 |
|---|---|
| §3.6 分发表按 `[req+0x5E8]` 三分支 | `5E8` 只是「期望哪个 opcode」的过滤器；**真正决定下一步的是 `[req+0x644]`** |
| §3.9 `0xD2` 是魔数下界 | 对，但**只有 `0xDC` 能开门**（见 §4.2），旧实验用 `0xD2` 注定失败 |
| §4 建议第一步：写 `644=0` 绕过 ① | 直接写字段仍不是干净实验；真正有效的是移除观察器对 `644=1` 的反向注入，让自然初值 0 存活 |
| 观察器 `--poke-lobby-644` 写 0 | 仍不要用；干净运行已经证明不需要该写入 |
| 「`0x7F9350` 是第二档入口」 | 它是 COM 智能指针赋值（Release 旧值 / 接管新值），不是阶段切换器 |
| 「magic 0xDC 已否证」 | 反了。`0xDC` 是**必需**条件 |

---

## 4. 已确证的契约（可直接实现）

### 4.1 帧布局

```text
u32  frame_len      服务端发帧用；对端不把它用作长度校验（已验证 196/200/224 均可）
u8   type           0x00
u8   opcode         分发器在 reader 缓冲区偏移 30 读它（= body[1]）
body...
```

### 4.2 魔数门 —— 唯一的硬条件

```asm
0xBA3D35  cmp [ebp-0x434], 0xD2   ; 0x81 帧里的 u32
0xBA3D3B  jb  0xBA3DBF            ; < 0xD2 -> 错误 7 -> 复位
0xBA3D43  cmp [ebp-0x434], 0xDC
0xBA3D49  ja  0xBA3DBF            ; > 0xDC -> 错误 7 -> 复位
0xBA3D53  mov [esi+0x640], ebx    ; [req+0x640] = 0x81 的 magic
```

```asm
0xBA3AE6  cmp cl,0x87 / jne 0xBA3B0E
0xBA3AEB  cmp [edi+0x640], 0xDC
0xBA3AF5  jb  0xBA3B36            ; 640 < 0xDC -> 整帧丢弃
0xBA3B02  call 0xBA3590

0xBA3B0E  cmp cl,0x89 / jne 0xBA3B36
0xBA3B13  cmp [edi+0x640], 0xDC
0xBA3B1D  jb  0xBA3B36            ; 640 < 0xDC -> 整帧丢弃
0xBA3B2A  call 0xBA3600
```

**`[req+0x640]` 的取值域是 `[0xD2,0xDC]`，所以只有 `magic = 0xDC` 能满足
`640 >= 0xDC`，握手帧 `0x87`/`0x89` 才会被处理。**

实跑确证：`--magic 0xDC` → `CODEC_TRANSITION ... 640=220`。

### 4.3 三个处理器的真实行为

```text
0x81 (0xBA3C70)
    读 u32 magic（∈[0xD2,0xDC]）→ [req+0x640]
    读 u64 token → [req+0x638] / [req+0x63C]
    读 8 字节 → 回帧 → [req+0x5E8]=2
    成功/失败分别 push 常量 6 / 7

0x83 (0xBA3BA0)  纯回显校验，只有 20 行
    读 8 字节，与 [req+0x5FC] memcmp
    失败 → push 4 -> 0xBA3420
    成功 → [req+0x5EC]=1, [req+0x5F0]=1, [req+0x5E8]=3
    它只「读」[req+0x644]（0xBA3C21），从不写它
    不要指望它推进 644
```

### 4.4 `0x83` 处理器原文（`0xBA3BA0` 关键段）

```asm
BA3BBD  ecx = buf+1
BA3BCD  call 0xB783C0(...,8)        ; 读 8 字节
BA3BE0  push 4 / call 0x4F7940      ; 失败: 错误 4 -> 复位
BA3C0B  lea eax,[esi+0x5FC]
BA3C12  call 0xB73FE0               ; memcmp(this+0x5FC, recv8, 8)
BA3C1A  test eax,eax / jne BA3C62   ; 不等 -> push 3 -> 复位
BA3C1E  lea ebx,[eax+1]             ; ebx = 1
BA3C21  cmp [esi+0x644], eax        ; 只读
BA3C29  mov ecx,[esi+0x640] / call  ; 仅打日志
BA3C3B  mov [esi+0x5EC], ebx        ; = 1   5EC 的唯一写入点
BA3C41  mov [esi+0x5F0], ebx        ; = 1
BA3C47  mov [esi+0x5E8], 3
BA3C51  ret                         ; 返回 1
```

### 4.5 dispatcher（`0xBA4440`）的真实形状

```asm
BA44E8  mov eax,[esi+0x5E8]
BA44EE  cmp eax,1 / jne BA454B
BA44F6  cmp al,0x81                 ; 5E8==1: 只收 0x81
BA450C  cmp al,4    -> 复位
BA454B  cmp eax,2 / jne BA46A2
BA4557  cmp al,0x83 / jne BA45F0    ; 5E8==2: 0x83 -> BA3BA0; 0x84 -> BA0E20
BA46A2  cmp eax,3 / jne BA4781
BA46AE  cmp al,0x85                 ; 5E8==3: 0x85 -> BA3710; 0x84 -> BA0E20

; 0x83 分支内部：
BA4567  call 0xBA3BA0
BA456C  test al,al / je BA4463      ; 校验失败 -> 直接返回
BA4574  mov eax,[esi+0x644]         ; 关键
BA457A  test eax,eax
BA457C  jne BA45DB                  ; 644 != 0 -> 看是不是 3
BA457E  ... call 0x7F9350 ...       ; 644 == 0 -> COM 赋值, [out]=4
BA45DB  cmp eax,3
BA45DE  jne BA4463                  ; 644 != 0 且 != 3 -> return 0（旧版注入路径）
BA45E4  call 0xBA3E20
```

**`644 == 1` 时走 `BA45DB → BA4463`，即 `return 0`（未消费帧）。
这就是旧版观察器注入路径的 32 ms 复位入口；干净 `644=0` 运行已绕开它。**

### 4.6 `[req+0x644]` 完整写入表（全镜像扫描）

```text
00BA299C  = 0      构造/重置
00BA346A  = 0      0xBA3420 复位
00BA3E5D  = 0      0xBA3E20（644==3 分支）
00BA35EB  = 1      0xBA3590 —— 发完 0xC8 帧之后（进入时要求 644==0）
00BA3657  = 2      0xBA3600 —— opcode 0x89 路径（进入时要求 644==1）
00BA325E  = 3      0xBA31F0 内（C8==2 且 644!=0）
00B8CA10  = ?      模块 0xB8... 内，未分析
```

⚠️ **全镜像里没有任何 `mov dword [reg+0x644], 1` 的立即数写。**
`644=1` 只能由 `0xBA35EB`（寄存器写）产生，而那条在 `0xBA3590` 内部，
**进入时要求 `644 == 0`**。`0xBA4080`（连接建立）只写 `C8=2`（`BA4127`），
**不写 `644`**。

⚠️⚠️ 早期打到 `5E8=3` 的运行都带观察器的
`--poke-lobby-globals`，其中的 `644=1` 是观察器注入的；移除该注入后，
干净运行实测 `644=0` 能保持到 `0x83` 成功及其后的客户端 `0x85` 分片。
不要再把旧运行中的 `644=1` 当作自然客户端行为。

因此从 `644=0` 出发的完整链条是：

```text
644=0 （构造初值，00BA299C）
  -- 收到 opcode 0x87（要求 640>=0xDC）--> 0xBA3590
       要求 644==0 -> 发 0xC8 魔数帧(28B) -> 644=1
  -- 收到 opcode 0x89（要求 640>=0xDC）--> 0xBA3600
       要求 644==1 -> C8=1, 644=2, 5E8=0
  -- 644=3 只由 0xBA31F0 写（C8==2 且 644!=0）
```

即 **`644 = 1` 可以是 `0x87` 路径的下游状态，但不是连接建立必然产生的值；
本项目的干净路径从构造初值 0 进入了 `644==0` 成功分支。**

### 4.7 `[req+0x5EC]`：`0x83` 成功即关闭入站通道

```asm
BA3844  mov eax,[edi+0x5EC]
BA384A  lea edx,[eax+1]
BA384D  mov [edi+0x5EC], edx
BA3853  cmp [ebp-0x394], eax        ; [ebp-0x394] 在 BA3A1E 被置 0
BA3859  je  BA38A4                  ; 旧值==0 -> 继续处理这一帧
BA387F  call 0xBA3420               ; 否则复位
```

`[req+0x5EC]` 全镜像只有两个访问点：`0xBA3844` 读、`0xBA3C3B` 写 1。

```text
0x83 成功 -> 5EC=1
之后大分发器每读一帧 -> 旧值 1 != 0 -> 复位
```

⚠️ **但这条推论已被实跑证伪一次**：把 `0x89` 与 `0x81` 同段发送
（`--seq-after-81 89`）后，`0x83` 反而再也没成功过（`5e8` 从未到 3）。
所以「提前发 0x89 就能过闸」不成立。该现象记录为**未定**，勿当结论使用。

### 4.8 复位原语 `0xBA3420`

```asm
BA3456  mov [esi+0xC8],  4
BA3460  mov [esi+0x5E8], 0
BA346A  mov [esi+0x644], 0
BA347D  mov [esi+0x6D0], 0     ; 清待发任务链表
BA3497  mov [esi+0x6D8], 0
BA34A6  mov [esi+0xB8],  0     ; 清待发链表头
BA34C0  mov [esi+0xC0],  0
```

全镜像 **23 个调用点**，全部在错误路径：

```text
BA2625 BA268B BA2769 BA27BC BA3561 BA35CA BA3621 BA387F BA3BEC BA3DFA
BA3F36 BA4056 BA4187 BA437F BA43A8 BA4526 BA4541 BA462A BA4698 BA470C
BA477A BA4792 BA47AA
```

### 4.9 常量（已核实）

```text
[0xDBE6CC] = 0x41F00000 = 30.0f   -> [req+0xAE0]（泵的时间上限）
[0xDE7C18] = 30.0                 -> 泵中另一处比较基
两者都是 30 秒 —— 与实测 32 ms 复位无关
[req+0x108] = 0x1E (30)           0xBA29ED 构造时写入
```

### 4.10 客户端首帧（实跑确证，定长 28 字节）

```text
偏移  值              说明
0x00  c8 00 00 00     常量 0xC8（不是长度字段）
0x04  c8 00 00 00     常量 0xC8
0x08  d2 00 00 00     0xD2
0x0C  dc 00 00 00     0xDC
0x10  00 00 08 00     ?
0x14  8 字节随机      每次运行都不同
```

用 `--pre81-drain 6`（不回帧、持续收 6 秒）验证：`total` 恒为 28，
**客户端不会自行补足**。旧手册与中间推断的「200 字节首帧」已作废。

---

## 5. 第一档状态与未完成步骤

```text
① 0x81 处理器        已闭合   magic 必须 0xDC；token 落到 638/63C；5E8=2
② 收客户端 0x82      已闭合   稳定 153 字节
③ 发 0x83 回显       已闭合   5E8=3, 5EC=1, 5F0=1
④ 0x83 -> 下一阶段   部分闭合  干净路径已命中 `644==0` 分支；后续交互未闭合
⑤ 保活 / 持续        未闭合   约 47 秒后退队并弹出大厅断线
第二档               未开始
```

### 5.1 第 ④ 步已证伪的实验（**共 12 项，勿重走**）

```text
1  frame_len 0xC8 / 0xDC / 196 影响握手
2  0x84 单独发送 / 分离发送（20 ms 间隔）
3  0x85 全零 / 内嵌 0x89 + 0xBA02A0 表计算 tag
4  外部写 [req+0x644] = 0
5  外部写 [req+0x644] = 3
6  4 字节全零保活（单独 / 与 644=0 组合）
7  0x83 + 0x84 + 0x89 合并进同一个 TCP 段发送
8  0x84 + 0x89 分两次发送
9  0x89 与 0x81 同段发送（--seq-after-81 89）
10 magic 0xD2（0x640 门未开，必然失败）
11 「探针在 0x83 后关连接导致复位」
12 「32 ms 复位是超时」
```

### 5.2 第 ④ 步与后续仍未闭合的路径

```text
· 已验证：保留 host/port 全局填充、去掉 644/4F8 注入后，644==0 分支可通过
· 未完成：解析并响应客户端随后主动发送的 0x85 分片，以及约 47 秒保活窗口
· 仍可用：在 0xBA4440 返回处采样 al，或记录后续 HTTP/大厅服务端请求序列

⚠️ 因果方向已更正（见 §33 / §5.3 第 5 条）：
   52 秒断线是**看门狗超时**，DELETE /queue 是断线后的清理动作，
   不是断线原因。真正缺的是「服务端持续发出客户端可解的业务帧」。
```

### 5.3 本轮新增否证（勿重走）

```text
1  向客户端补发服务端 opcode 0x85
   0xBA3710 内的 0x5EC 闸（BA3844..BA387F）要求「进入时旧值 == 0」；
   0x83 成功已把 5EC 置 1（BA3C3B），因此此刻任何入站 0x85 都会
   push 2 -> 0xBA3420 -> 复位。不要再试。

2  把队列响应的 next_poll_after 当作大厅保活
   next_poll_after 确实被消费，但只在队列对象状态 == 1（排队中）时：
   0x7F3209 取 [objC+0x250]（next_poll_after）与 0xE3EC980 的计时器
   比较，超时后重新调用该对象虚表 +0x10。状态 == 2（已成功）时
   （0x7F31F7）直接置 sub_state=9，不进入该重轮询分支。
   本次 709B 响应让对象进入状态 2，因此改 next_poll_after 不改变
   当前行为；它也不是这条 52 秒断线的来源。

3  高频 4 字节保活（--keepalive4 + --keepalive4-every）
   干净 644=0 路径上做 A/B（run IFS1_ELEVATED_20260929_142730）：
   0x83 后连续 69 秒、每 1 秒发一次 00 00 00 00。
   客户端全程 C8=2 / 5E8=3 / 644=0，未再出现 32 ms 或任何立即复位，
   但仍在 post-83 +52 秒弹出「与大厅服务失去连接」。
   => 4 字节包不是非法帧，但它不构成大厅保活；断线与该 socket 无关。

4  让队列响应进入「状态 1 + next_poll_after=1」以触发重轮询
   0xB984E7 判定状态 1 的条件是 iv_seed 与 lsg_server_ticket_size
   「两者都为 0」。实测（run IFS1_ELEVATED_20260929_144131，
   CODO_L_QUEUE_IV_SEED=0 / CODO_L_QUEUE_TICKET_SIZE=0 /
   CODO_L_QUEUE_NEXT_POLL_AFTER=1）：
   客户端停在 sub_state=8，从未进入 DW_ACCOUNT_LOGIN_COMPLETE，
   也从未发起第二轮队列请求；约 50 秒后仍弹大厅断线。
   => 状态 1 不是缺失的那一步，排队语义会直接卡死流程。

5  把「约 47–52 秒后 DELETE /queue」当成断线原因（前几轮的隐含假设）
   对齐两个独立时钟后（观察器 ready.flag 与探针 ready_seen 同刻）：

   t_obs 38.18  0x83 成功
         85.12  uA50=5  DWLOBBY_PUMP_SUCCESS
         90.113 lob240: 2 -> 3      （大厅对象被标记断开）
         90.163 弹窗「致命错误」
         90.164 正文「与大厅服务失去连接」
         90.105 sni / 90.137 tls_ok / 90.167 DELETE /queue

   DELETE 的 TLS 握手起点和 http 请求都**晚于**弹窗。
   `lob_http_state 3->5->200`（t=90.113）比 DELETE 请求早 54 ms，
   不是 DELETE 的响应，而是大厅对象自身的状态翻转。
   => DELETE /queue 是断线后的自我清理，不要围绕它做实验。

6  52 秒是一个固定看门狗（勿再当随机断链）
   干净基线与周期 4 字节保活两次运行都是 52.0 秒：

   run                              handshake  dialog   delta
   IFS1_ELEVATED_20260929_133024    38.183     90.164   51.98 s
   IFS1_ELEVATED_20260929_142730    37.386     89.383   52.00 s

   其输入是「大厅明文 socket 上没有新的可解业务帧」：
   客户端确实收到了握手期的 0x81/0x83（AFD 侧 t=39.581 / 39.615
   各有一次 recv），但这两条不是位打包业务帧，0xBA20A0 取帧返回
   edi<=0；且此后到连接关闭 recv 事件为 0，服务端（探针）也不再发帧。
   旧运行「弹窗推到 84–89」是采样口径差异，同一个看门狗，
   不是 644=1 的收益。

   ⚠️ 上面这条已被 §35 进一步修正：看门狗的输入**不是**「有没有帧」。
   见下方第 7、8 条。

7  **「服务端持续发前缀帧即可保活」——错，勿实现**
   反证 A：run IFS1_ELEVATED_20260929_142730 在 0x83 后每 1 秒发 4 字节、
           连发 69 次，仍在 post-83 +52.00 s 断线。
   反证 B：run IFS1_ELEVATED_20260929_160114 完全不发（hold 70 s），
           仍在 post-83 +52.04 s 断线。
   两种极端的断线时刻完全相同 => 入站流量与 52 秒计时器无关。

8  **「52 秒是读超时」——错，读路径根本没执行**
   run 160114 把 post-83 采样窗从 2 s 扩到 70 s（新增
   `--post83-seconds`），以 16 ms 分辨率采到 4770 个点：
     lobReq9c  全程恒为 1（不是读帧成功后的 3）
     lobReq5e8 全程恒为 3
     b0 / b4   全程恒为 0（消息对象从未建立）
   => 唯一读帧函数 0xBA20A0 在这 52 秒里一次都没执行成功。

9  **「[0x849B868]+0xC 是断线计时器」——只对了一半，勿再追**
   run 162332 的 1 Hz 时间线显示该值恒为 180.000（float），全程不变；
  它只是 DW 心跳的显示值。真正在掉线瞬间变化的是
   [0x00E85C68+0x1F4]：1 -> -2（见 §37）。

10 **「52.0 秒是一个固定看门狗」——错，它是 20 × STUN 超时**
   run 162332（真实 stun 主机）：dw+0x1F4 1->-2 @ +47.6 s，弹窗 +52.1 s
   run 164603（stun.ini 指向 127.0.0.1）：同一字段 @ +23.2 s，弹窗 +27.7 s
   唯一改动是 STUN 主机 -> 断线提前 24.4 s。
   => 勿再把 52 s 当常量去凑；它与 STUN 探测的 RTT/超时强相关。

11 **「DW 的 https://%s/ 恒用 443，起个 443 监听即可」——错**
   汇总最近 12 个 NET_CAPTURE 的 loopback connect，目标只有
   127.0.0.1:8443(67) / 127.0.0.1:8446(6) 以及 5xxxx 本机自连；
   **没有任何 127.0.0.1:443**。DNS 阶段实际是**通过**的
   （run 162332 的 dnsAHome 在 t=35.593 走到 2，两个模板都填成 127.0.0.1）。

12 **「STUN 包回声即可」——错**（run 165340，recv 48 / sent 48，
   dw+0x1F4 仍在 +23.163 s 掉到 -2）

13 **「回 8 字节 `00 00 00 00 00000000` 即可」——错**
   （run 170037，同样 recv 48 / sent 48，+23.238 s 掉到 -2）

14 **「0x7F4CD6 的 `cmp [ebp-0x51C],0` 是校验应答首 dword」——错**
   8 字节零包正是首 dword 为 0，仍被拒。见 §40.8/40.11：
   0xCA80CC 不是静态导入项（导入表只有 3 项），
   该处 `eax` 与 `[ebp-0x51C]` 是那次动态调用自己的返回/输出，
   不是应答内容。命名该槽位之前不要再猜回包。

15 **「52.0 秒是协议常量」——错，见 #10；且 20 次预算结构两次自证**
   真实 STUN 主机：+47.648 s ≈ 20 × 2.38 s
   本地 STUN 主机：+23.2 s   ≈ 20 × 1.16 s

16 **「STUN 是一个需要实现的服务端协议」——错，它是系统 ICMP ping**
   `0x7F4CCB call [0xCA80CC]` 解析后 = `IcmpSendEcho`
   （SysWOW64\IPHLPAPI.DLL RVA 0x1FDE0）。
   同处 `0xCA80C8` = `IcmpCreateFile`（RVA 0x1F770）。
   因此：**不需要写 UDP 服务端**；只要那三个主机能被 ICMP 应答即可。
   之前所有「回一个 UDP 包」的思路（回声、8 字节零包）本质无效。

17 **「stun.ini 是 STUN 服务器列表」——更准确的说法是 ping 目标列表**
   其内容被当作 ICMP 目标（配合 dw_config 的 STUN_STN/STUN_TUB/... 键）。

18 **「让 ping 目标可达就能让 DW 走到 2」——错**
   run IFS1_ELEVATED_20260929_172253：stun.ini 三行 -> 192.168.5.13
   （本机 LAN 地址，`ping` 2/2 回、RTT 0 ms），
   dw+0x1F4 仍在 **+23.196 s** 掉到 -2，弹窗 +27.586 s，
   与 127.0.0.1（不可 ping）的结果**完全相同**。
   => ICMP 可达性不是充分条件。

19 **「-2 一定来自 20 次重试预算 0xBAD8CE」——错**
   同一轮里 [dw+0x4D74]（重试计数）**全程为 0**，
   说明 0xBAD8C8..0xBAD8D5 那条路径没执行；
   这次的 -2 来自 0xBADE15 / 0xBAE75E / 0xBAE776 / 0xBAE7BA 中的
   另一处。下一步必须先区分这四个写入点各自的前置条件。

20 **「0xBADE15 是一个 -2 写入点」——地址笔误**
   按 `c7 83 f4 01 00 00 <imm32>` 精确重扫，`-2` 写入点只有四处：
   **0xBADDEA / 0xBAE75E / 0xBAE776 / 0xBAE7BA**
   （另有 0xBADB50 = -1，0xBADFB2/0xBAE1BC/0xBAE597 = 2）。

21 **「0xBADDEA / 0xBAE7BA 是"队列为空才断开"」——错**
   `jbe 0xBADDEA` 只是跳过日志循环；两条路都会落到
   `mov [ebx+0x1F4], -2`。它们是"放弃终点"，不是条件判定。
   run 173105 里 [dw+0x18]=3（队列非空）仍被置 -2，正与此一致。

22 **「三个成功路径随时可能命中」——本轮实测一次都没命中**
   run 173105 全程 [dw+0x1A0]=0 / [dw+0x1A4]=0，
   而 0xBADFB2 / 0xBAE1BC / 0xBAE597 之前都会
   `call 0xC69A50` 往 [dw+0x1A0] 推进条目。
   => 成功路径从未执行。

23 **「至少是"队列空"或"重试耗尽"这两种之一」——两者本轮都被排除**
   run 173105：`[dw+0x18]=3`（非空）、`[dw+0x4D70]=3`（issued==expected）、
   `[dw+0x4D74]=0`（无重试）。仍在 +47.515 s 置 -2。
```

---

## 6. 后续阻塞：服务端交互与观测能力

旧的 32 ms 复位窗口已经由干净 `644=0` 路径移除。**剩余阻塞已收敛为一条**
（因果方向见 §5.3 第 5/6 条，§5.3 第 7/8 条进一步否证了「发帧续命」）：

```text
唯一缺口  DW（Demonware）会话层没有建立成功。
          证据（§37，观察器 POST83_WATCH 1 Hz 时间线）：
            [0x00E85C68+0x1F4] 全程 1（连接中），到 +47.6 s 掉到 -2（断开）
            同一时刻 uA50=5（大厅泵已完成），t868/c7a0/c8b4 等全程不变
          静态：0xBAD856 只在阶段==1 时处理；0xBAD8CE 的 20 次重试预算
          用尽后走 0xBAE7BA `mov [ebx+0x1F4],-2` 放弃。
          +52.0 s 弹窗（§35 四次复现的固定值）= -2 之后 +4.4 s。

已证     握手期客户端收到 0x81/0x83（AFD t=39.581/39.615 各一次 recv），
          此后 recv 事件为 0。
          post-83 扩窗采样（run IFS1_ELEVATED_20260929_160114，16 ms
          分辨率、4770 点）显示 [req+0x9C]=1、[req+0x5E8]=3、
          [req+0xB0]=[req+0xB4]=0 全程不变。
          run IFS1_ELEVATED_20260929_162332 的 1 Hz 全局时间线显示
          只有 dw+0x1F4 在掉线瞬间变化（1 -> -2 @84.866）。
          DELETE /queue 在弹窗之后 4 ms 才发起，是清理不是原因。

已定位    断线路径是 **DW 心跳**，链条（报告 §36）：
            0x7EEBC1 call 0x621810        （唯一调用点）
            0x6218CE mov ecx,[0x849B868]  （计时器对象）
            0x6218D4 fld [ecx+0xC]        （计时起点，秒）
            0x621929 cmp [0x849B7A0]+0xC,0（无连接 -> 直接弹窗）
            0x621AA1 push 0xDBD888 '@SF_UI_DW_LIVE_DISCONNECTED'
          收尾：0x7EEA00 取 0xDBB604 'SF_UI_DW_LIVE_DISCONNECTED'，
          二选一 0xDE05C0 'MULTIPLE_LOGIN' /
                 0xDE05D0 'LSG_DISCONNECT_IN_GAME'；
          同批字符串 0xDE05E8 = 'cppOnDWDisconnected'。
          即：这是 Demonware 心跳判定，与大厅明文 socket 的入站帧无关。

下一步    让 [0xE85C68+0x1F4] 走到 2（已连接）而不是停在 1 直到超时：
          ① 已定位全部写入点（都在 0xBAD810 内）：
             「成功置 2」0xBADFB2 / 0xBAE1BC / 0xBAE597
             「失败置 -2」0xBADDEA / 0xBAE75E / 0xBAE776 / 0xBAE7BA
          ② 已定位重试预算：0xBAD8C8 inc [dw+0x4D74] / 0xBAD8CE cmp,0x14
          ③ 已定性缺口（§38）：不是大厅协议，而是 DW live 的
             **STUN / DW 主机可达性**：
               · AFD 显示窗口内唯一业务流量是 sendto 121.51.232.95:3074
                 （= stun1-tub.codol.qq.com），且全部 recv=0
               · DW URL 模板 `https://%s/`（0xDE09E4 -> 0x7F306C 用
                 0x081A76A8）不带端口 -> 恒用 443；127.0.0.1 上无 443 监听
          ④ **已定性并抓到输入**（§39）：客户端在 UDP/3074 上做自定义探测，
             两种 payload：`1e0300`（3B）与 `14020000`（4B），
             每 0.51 s 成对发出，source port 固定 22011。
             目标由 `stun.ini` 的三行决定（默认 stun1/2/3-tub.codol.qq.com）。
          ⑤ **已确认 0xCA80CC = IcmpSendEcho**（§41）：客户端对
             stun1/2/3 的 IP 做系统 ICMP ping，不是 UDP 协议。
             同处 0xCA80C8 = IcmpCreateFile。
             => 不要再实现任何 UDP 回包（回声/8 字节零包都已否证）。
          ⑥ **但「ping 可达」也不是充分条件**（否证 #18）：
             换成可 ping 通的 192.168.5.13 后，dw+0x1F4 仍在
             +23.196 s 掉到 -2，与不可 ping 的 127.0.0.1 完全一致。
             且该轮 [dw+0x4D74] 全程为 0 —— -2 不是 20 次预算那条路
             （否证 #19）。
          ⑦ **已实跑判定**（run IFS1_ELEVATED_20260929_173105，§42.6）：
             [dw+0x18]=3、[dw+0x4D70]=3、[dw+0x4D74]=0、
             [dw+0x1A0]=[dw+0x1A4]=0 —— 四个值全程不变，
             仍在 +47.515 s 置 -2。
             => 排除「队列空」与「重试耗尽」；成功路径
                （0xBADFB2/0xBAE1BC/0xBAE597 之前的 call 0xC69A50）
                一次都没执行。
             -2 的精确写入点只有四处：
                0xBADDEA / 0xBAE75E / 0xBAE776 / 0xBAE7BA
             （否证 #20 修正了地址笔误；#21 修正了读法）
          ⑧ **已定位到具体函数**（run 173828，§43）：
             [dw+0x1F0] 与 [dw+0xC] 每约 12.2 s 变一次（周期性重试），
             但 [dw+0x1A0]（"有报文在途"标志）**全程为 0** ——
             而 0xBBAD10 只有在 0xBBA870 返回 1 时才置 1。
             => 每次发送尝试都失败；47.685 s ≈ 4 × 12.2 s 后放弃。
          ⑨ **下一步（已缩到单个函数）**：
             0xBBAD10（DW 发报机）-> 0xBBA870 -> **0xBBA6D0**。
             0xBBA6D0 是真正"送出去"的那一步，返回 1 才算成功。
             做法：按 0xBBA6D0 入口反汇编读出它使用的对象偏移，
             把那些字段加进 POST83_WATCH，一轮即可知道它为何返回非 1。
             同构兄弟 0xBBA890(arg3) / 0xBBA8B0(arg2, 用 [ecx+0x8C])
             说明这套"发送步"有多个阶段，可一并核对。

          注：0x7E8579 float 15.0 / 0x7E8583 float 180.0 与 [0x849B868]+0xC
             （恒为 180.000）是 DW 心跳显示值，**不是**触发源，勿再追。

已试     --eip-trace（SuspendThread + GetThreadContext）
         结果：旧 20 ms 窗口内无样本落在 0xBA0000..0xBB0000（报告 §14）

可选     在 0xBA3420 入口做 code-cave 式记录（写 5 字节 E9 跳转）
         —— 属改 .text，超出当前安全边界，需用户明确授权。
         注意：看门狗不是 0xBA3420 复位，此手段对本缺口帮助有限。
```

### 6.1 可用的替代观测（已实现，本轮有效）

```text
观察器 --post83-trace + POST83_SAMPLE 现含字段：
  s9c / 5e8 / 644 / a8 / ac / b8 / c0 / 6d8 / b0 / b4 / buf
已用它得到决定性数据：
  5E8=3 时  b8=0  c0=0  6d8=1
  => 泵的 B8 链表为空（BA254D..BA26B9 段未执行），
     但 6D0 任务表里有 1 条待发消息，复位后被 0xBA3420 清零
```

---

## 7. 安全边界（硬性）

```text
允许    ReadProcessMemory / WriteProcessMemory / EnumWindows / EnumProcesses
禁止    绕过或篡改 ACE / 修改 .text 代码段 / Frida 注入
```

`WriteProcessMemory` 只用于写游戏自身会写的数据字段
（如 `[req+0x5E8]`、`[req+0x644]`、大厅 host/port 全局）。
注意 §3：**`644` 的写入已被证明有害，不要再写它。**

---

## 8. 已踩过的坑

### 8.1 方法教训（最重要）

> **不要再用「报一个偏移 + 实跑验证」的循环。**
>
> 上一版手册记录过：同一处连续失败六次，根源是用构造期静态值去推运行期偏移。
> 第二版会话结束时，第一档第 ④ 步累计 **12 项证伪**，其中最近 4 轮
> 全部是「提出假设 → 实跑证伪」。这是同一种病。
>
> **正确做法：先记录原始内存变化，不做推断。**

### 8.2 具体误判（第二版会话新增）

```text
1. frame_len → 640。实测 640 是 0x81 的 magic，与帧长无关
2. 「200 字节首帧」。实测 28 字节定长（--pre81-drain 验证）
3. 「0x7F9350 是第二档入口」。实为 COM 智能指针赋值
4. 「644=0 才能进第二档」。644==1 时 0x83 分支 return 0
5. 「0xBA3D53 在 0x83 handler 里」。它在 0x81 handler（0xBA3C70）里
6. 「5EC 首帧闸 → 提前发 0x89 可过」。实跑：0x83 反而不再成功

7. **CONFIRMED_RESULTS §21「弹窗消失」是误记**。该结论基于
   run IFS1_ELEVATED_20260928_183320（带 644=1 旧注入，130 s）。
   复核其 events.csv：t=89.091 仍然出现
   `WINDOW_NEW class=#32770 text=致命错误`。
   弹窗从未消失；§21 与 §12 矛盾时以 §12 为准。

8. **「DELETE /queue 是 52 秒断线的原因」是因果倒置**。
   对齐观察器与探针时钟后，DELETE 的 TLS 握手与 http 请求都晚于弹窗
   （§33 / §5.3 第 5 条）。断线本身是「大厅 socket 无解出帧」的看门狗。
```

### 8.3 已知失败 / 坑操作

```text
· 观察器 --poke-lobby-644 写 0：不再需要，干净路径已验证；不要再开
· 观察器 --handshake-ready-file / --handshake-echo-file 必须传绝对路径；
  提权进程工作目录不同，否则 LOBBY_5E8_READY_ERROR: DirectoryNotFoundException
· auto_lobby_loop 的 SUCCESS 判据是假成功，勿据此收工
· 观察器早期版本残留 644:=3 的覆盖写，曾掩盖真实状态达数轮；
  改任何 poke 后先确认没有残留
· WriteProcessMemory 有概率性 31 秒阻塞（干净启动约 1/7 概率）
· 启动 flake 20–40%；用 --abort-on-cfg0 快速淘汰
· `auto_lobby_loop.py` 原先只在「每轮开始」调 stop_probe，
  最后一轮结束后 8443/8444 监听会泄漏；本轮已在两个 return 前补 stop_probe。
  若仍看到残留监听，用 Get-NetTCPConnection -LocalPort 8443,8444,8446 查、
  按 OwningProcess 停掉对应 python。
· `--post83-trace` 的采样窗原先固定 2 秒（看门狗在 +52 s），
  等于从未采样；本轮改为 `--post83-seconds N`（默认 70）。
```

---

## 9. 关键文件与工具

```
手册（本文件）   CODOLServer\HANDOFF_20260929_LOBBY_PROTOCOL.md
详细报告         CODOLServer\SESSION_APPEND_20260929_STAGE3_SUCCESS.md
                 （第 18–27 节是第二版会话的全部证据链）
探针             CODOLServer\lobby_server\lobby_plain_probe.py
观察器           restore_iips_contract_001\observer2\AboProbe.cs
发布命令         dotnet publish restore_iips_contract_001\observer2\AboProbe.csproj `
                   -c Release -r win-x86 --self-contained true `
                   -o restore_iips_contract_001\observer2\out
轮次驱动         CODOLServer\_mainline\auto_lobby_loop.py
提权代理         CODOLServer\_mainline\agent_client.py
反汇编           CODOLServer\_mainline\_dis_va.py
调用点扫描       CODOLServer\_mainline\_xref_call.py
位移扫描         CODOLServer\_mainline\_scan_disp.py
连接生命周期     CODOLServer\_mainline\_conn_lifecycle.py
状态时间线       CODOLServer\_mainline\_state_timeline.py
长窗 post83 观测 CODOLServer\_mainline\_post83_long_observe.py
STUN 探测记录器  CODOLServer\_mainline\_stun_capture.py
                （UDP 记录/可选回包；stun.ini 指向 127.0.0.1 时用）
UI 资源备份      CODOLServer\backups\TPFUI_PLACEHOLDERS_20260929
```

### 9.1 工具开关

```text
探针  --bind --port --log --lobby-handshake --magic --token
      --ready-file --ready-timeout --echo-file --echo-source
      --frame-len --follow-84 --follow-84-value --follow-85 --follow-85-v1
      --key-file --split-83-84 --keepalive4
      --hold-after-83 <秒>        0x83 后保持连接
      --seq-after-83 <步骤表>     84 / 84echo / 89 / c8，与 0x83 同段发送
      --seq-after-81 <步骤表>     与 0x81 同段发送
      --pre81-drain <秒>          回 0x81 前先收 N 秒

观察器 --lobby-ready-only --poke-lobby-5e8 --poke-lobby-9c4
       --poke-lobby-644（勿用）--post83-trace --eip-trace
       --handshake-echo-file --handshake-key-file --handshake-ready-file
       --abort-on-cfg0 --poke-lobby-globals（仅 host/port 全局填充）
       --post83-seconds N（新增，默认 70；只配 --post83-trace 使用）
       POST83_WATCH（新增事件）：post-83 窗口内每 1 s 输出一次
         看门狗全局快照——含 [0xE85C68](DW 单例) /1f4 /1f8 /1fc
         /4d70 /4d74 /18、[0x849B868]+0xC、[0xE59D20]、[0x849BA34]。
         另有 iat80cc / iat80c8（动态导入槽）及其 /code（跳转桩字节）
         与 /mod（所属模块）——用于把运行期解析的 API 命名。
         判断「谁在掉线瞬间变化」直接看这个事件。

一键长窗观测
       python -X utf8 CODOLServer/_mainline/_post83_long_observe.py
       （自动起 8446 探针 + 跑一轮 + 开 70 s post-83 采样）
```

---

## 10. 当前建议的下一步

### 10.1 已完成：拆分全局填充与状态注入

```text
观察器已完成拆分：
  保留   填大厅 host/port 全局（0x081A76A8 / 0x081A7F34 / 0x081A9784 /
          0x081A9EC4 / 0x081A9780 / 0x081A9EC0）—— 这是连接建立必需的
  去掉   写 [req+0x644]=1 与 [mgr+0x4F8]=1

干净实跑 `IFS1_ELEVATED_20260929_133024` 已验证：
  644=0 -> BA457E..BA45B2 分支通过，32 ms 复位消失；
  客户端随后发送 0x85 分片，但约 52 秒后仍因后续服务端交互缺失而断线。
```

> 这条路径现在已完成验证。旧的「写 `644=0`」实验仍不能和本结果混为一谈，
> 注意：早期会话试过「写 644=0」，但当时也没关掉观察器自身对 644 的
> 反向覆盖，且用的是 magic 0xD2，所以那次结果不构成否证。

### 10.2 下一步：定位 52 秒断线计时器（唯一缺口）

```text
前提（§33 + §35 已证）：
  · 52 秒断线是一个固定计时器，从 0x83 成功起算（4 次运行一致）
  · 它与入站流量无关：完全不发 vs 每 1 s 发 4 字节，断线时刻相同
  · 触发时读帧器 0xBA20A0 从未执行（[req+0x9C] 全程 1、[req+0x5E8] 全程 3）
  · DELETE /queue 是断线后的清理，会自行消失，不用处理
=> 不要再从「发什么帧」入刀；要从「谁在计时」入刀。

第一步（守边界，最省事）：复用本轮的 --post83-seconds 能力
  观察器已能把 post-83 采样窗开到 70 s；把采样字段扩到包含
  [req+0x9C] / [req+0xC8] / [req+0x1400] / [req+0x6D0] / [req+0x6D8]，
  跑一轮，看 0..52 s 内哪个字段出现「阶梯」（例如每秒 +1）。
  那就是计时器读的寄存器/计数器，顺着它找比较点即可定位常量。

第二步（静态）：搜 0xDE7xxx 附近的 52/50/45 秒浮点常量引用。
  已知 0xDE7C18 = 30.0（泵的时间上限）与 0xDBE6CC = 30.0f；
  52.0f 的候选在 0xD402FE 一带（UI 区，需排除）。

第三步（静态，本轮新增线索）：弹窗入口 0x621810
  唯一调用点 0x7EEBC1；函数内 [0x849B868]+0xC 是浮点、
  [0xE59D20] 是状态机（3/4/6 三态），0x621AA1 才 push 弹窗文本
  0xDBD888。从 0x849B868 这个对象往回找它的更新时间。

一键复跑：
  python -X utf8 CODOLServer/_mainline/_post83_long_observe.py
```

### 10.3 若用户放宽边界

```text
在 0xBA3420 入口写 5 字节 E9 跳转到 code cave，记录返回地址后跳回。
这是唯一能直接给出「谁触发复位」的手段。
属改 .text，须用户明确授权后才可执行。
```

### 10.4 不要做

```text
· 不要再试任何「向客户端补发某个 opcode」的组合（旧路径已证伪）
· 不要写 [req+0x644]
· 不要用 magic 0xD2
· 不要把 auto_lobby_loop 的 SUCCESS 当作验收
· 不要围绕 DELETE /queue 做实验：它是断线后的清理，不是原因（§33）
· 不要用固定数值去凑 52 秒计时器；先按 §10.2 定位它读哪个字段
· 不要再实现「服务端持续发前缀帧保活」：§35 已否证（发/不发结果相同）
· 不要假设 52 秒是读超时：读路径 52 秒内根本没执行
```

---

## 11. 第二档（未开始）

第一档闭合前不必看。已知入场线索仅一条：

```text
0xBA457E..BA45B2（644==0 分支）中 call 0x7F9350 —— 实为 COM 智能指针赋值，
把 [req+0x63C]（0x81/0x83 写入的垃圾指针 0x11223344）换成合法对象。
规模：dispatcher 下游数十个处理函数。
前置：第一档闭合。
```

---

## 12. ⚠️ 编写本手册时发现的重大更正：`644=1` 是外部注入

写本手册、逐条复核 §4.6 时发现：

### 12.1 全镜像扫描结果

```text
对 +0x644 的「立即数写」只有 5 处：
  00888C18  = 0
  00BA325E  = 3
  00BA346A  = 0
  00BA3657  = 2
  00BA3E5D  = 0

没有任何 `mov dword [reg+0x644], 1`。
寄存器源写只有：
  00B8CA10  （模块 0xB8…，未分析）
  00BA35EB  （0xBA3590 内部，进入时要求 644==0）
```

### 12.2 那 `644=1` 从哪来 —— 来自旧版观察器

旧版 `--poke-lobby-globals` 在 `t>=21` 且 `C8==2` 时还会无条件写：

```text
[req+0x644] = 1
[mgr+0x4F8] = 1
```

输出 `POKE_LOBBY_COMPLETE  mgreq644=1 mgr4f8=1`。
这些写入已经从观察器删除；当前该开关只填 host/port 全局。

### 12.3 这条更正的含义

```text
旧运行里的 `644=1` 是外部注入的；dispatcher 在 0x83 分支看到
`644==1` 就走 BA45DB -> BA4463。移除注入后，干净运行命中
`644==0 -> BA457E..BA45B2`，且不再发生 32 ms 复位。
```

### 12.4 已验证结果与剩余问题

```text
保留 host/port 注入、去掉 644/4F8 注入 -> 644 保持 0
-> 0x83 走 BA457E..BA45B2，[out]=4
-> 32 ms 复位消失（已由 `IFS1_ELEVATED_20260929_133024` 实跑确认）

剩余：客户端随后会主动发送 0x85 分片；约 47 秒后仍会 DELETE /queue
并弹出大厅断线。第一档⑤仍未闭合。
```

### 12.5 教训

```text
「观察器自身改变了被测状态」这类错误最难发现：
它不报错、不复位、只是安静地把一个正确值改错。
两次出现在同一项目：
  1. 早期残留 644:=3 的覆盖写（已修）
  2. 本轮 644:=1（已删除，并由干净实跑证实其不是自然状态）
接手者每次开 poke 前，先问「这个写会不会把状态推离它自然该处的值」。
```

### 12.6 干净运行证据（`IFS1_ELEVATED_20260929_133024`）

```text
38.182  CODEC_TRANSITION  5e8=3 5ec=1 5f0=1 640=220
38.183  POST83_SAMPLE     s9c=1 5e8=3 644=0
                         -> 未出现旧的 32 ms C8=4 / 5e8=0 复位

客户端随后主动发送 AB 85 分片：
  序号 1: 386B（单独 recv）
  00 00 00 00: 独立 4B recv，约 30 秒后
  序号 2: 194B
  序号 3: 418B
  序号 4: 50B
约 52 秒时弹「与大厅服务失去连接」。
```

这证明当前阻塞已经不再是 `644==1` 的 dispatcher 立即返回；下一步应解析
客户端主动 `0x85`/后续服务端交互，而不是继续向客户端补发 `0x84/0x89`。

---

## 13. 资源挂载审计补充（2026-09-29）

### 13.1 ★ 数据层实验：把 6 个 zone 补进 main\ 后，启动链首次走通

本轮（第三版会话）做了交接手册 §13 末尾所列的「数据层缺口」实验，结论如下。

**做法**（新增沙箱，未改动任何既有文件）：
```text
run_codol_001\sandbox_datafix_20260929\
  = sandbox_ifs1_20260923 的副本 + 下列 6 个 zone 解包进 main\
    ff_init_common_mp_V111.ifs        -> common_loadscreen.ff (24,885)
                                         common_mp.ff (77,605,093)
                                         localized_common_mp.ff (192,434)
    ff_init_common_marketplace_V95.ifs -> common_marketplace_lite.ff (29,594,085)
                                         common_marketplace_lite1.ff (3,436,085)
                                         localized_common_marketplace_lite.ff (66,671)
解包工具：CODOLServer\_mainline\_ifs_extract.py <in.ifs> <outdir>
```

**结果 A（决定性）：启动链不再挂在 IIPS，第一次走到 DW 账号阶段**
```text
旧（仅 sandbox_ifs1）：  17.7 s 窗口到 CoD Splash Screen 就不再前进
新（sandbox_datafix）：  14.77 s  CoD Splash Screen「使命召唤online Multiplayer」
                        15.23 s  class=CODO 主窗口出现
                        38.92 s  CODEC_TRANSITION  c8=1 s9c=0 5e8=0
                        38.95 s  CODEC_TRANSITION  c8=2 s9c=1 5e8=1
                        39.01 s  CODEC_TRANSITION  c8=2 5e8=2 640=220
                        39.05 s  CODEC_TRANSITION  c8=2 s9c=1 5e8=3 5ec=1 5f0=2
                        39.05 s  POST83_SAMPLE      s9c=1 5e8=3 644=0     ← 干净路径
                        39.05 s  dw+0x1F4 = 1（DW 会话「连接中」）
                        91.07 s  弹窗「致命错误 / 与大厅服务失去连接」  ← ⑤ 看门狗
                        170.0 s  进程被观察器按 --duration 结束（未自杀）
```
HTTP 侧同步（TLSv1.0 / AES256-SHA，与静态结论一致）：
```text
POST   /auth/                                      -> 200（task 32 -> 57）
PUT    /v1.0/title/622861078/queue/0/member/1135…  -> 709 B
DELETE /v1.0/title/622861078/queue/0/member/1135…  -> 709 B
```

**结果 B（否证）：zone 补齐并没有解决 ⑤ 的根因**
```text
POST83_WATCH 全程 39 s → 140 s（1 Hz）：
  cfg=0x00000000  cfgobj=0  gate=0  mode=0  gec=0
  dw+0x1F4 恒为 1，直到 91 s 看门狗把它置 -2
  dw+0x18=3  dw+0x4D70=3  dw+0x4D74=0  dw+0x1A0=0  dw+0x1A4=0   全程不变
  [0x84ABB2F] 恒为 0（观察器 g2f 读的是 u32，最低字节就是该 flag；见 13.2）
```
⇒ `0x4A93E0`（会把 `[0x82C4A88]` gate 置 1 的那个函数）**仍然从未执行**。
**它不依赖 zone 清单**，所以「补 .ff 资源」这条路对 ⑤ 无效。资源补齐的价值在于
**稳住了启动链**（不再 flake 到 IIPS、窗口/Splash 正常、能看到 0x81/0x83 握手），
这本身就让后续所有实验的可复现性大幅提高。

**结果 C：zone 补齐后 `--abort-on-cfg0` 变成了有害开关（必须知道）**
```text
sandbox_ifs1 上 cfg_applied 在 ~15 s 前翻 1，所以 --abort-on-cfg0 恰好可用。
sandbox_datafix 上 cfg_applied 在 ~17.7 s 才翻 1（IIPS 多解了 6 个 zone），
于是 --abort-on-cfg0 会在 cfg 还没生效时就 ABORT_CFG0，
把「本来会成功」的轮次全部误杀（本轮连续 2 次误判为 flake，日志是
`15.00 s ABORT_CFG0,cfg=0,reason=early_lobby_write_missed`）。
=> **在 datafix 沙箱上跑链时不要加 --abort-on-cfg0。**
```

### 13.2 ★ ⑤ 的根因被静态钉死：`0x4A93E0` 的守卫是「市场模块已装载」

```asm
004A93E0  803d2fbb4a0800      cmp byte ptr [0x84ABB2F], 0    ; 守卫
004A93E7  56                  push esi
004A93E8  c705ec4a2c0801000000  mov dword [0x82C4AEC], 1     ; gec := 1
004A93F2  7461                je 0x4A9455                    ; guard==0 -> 直接返回
004A93F4  …                    （guard!=0 才继续）
004A9418  e813a43500          call 0x803830                  ; 取市场模块对象
004A9425  e846126d00          call 0xB7A670                  ; 判类型 == 2
004A942F  6891e0da00          push 0xDAE091                  ; "" 空请求名
004A9436  e8157e6d00          call 0xB81250                  ; 取请求体
004A9443  c705884a2c0801000000  mov dword [0x82C4A88], 1     ; gate := 1
004A944D  e86eecffff          call 0x4A80C0                  ; 真正发起 marketplace 请求
004A9455  5e                  pop esi / ret
```
即：**`[0x84ABB2F] != 0` 是 ⑤ 的直接前提**；它是「marketplace zone 是否已装载」。
写入点只有 `0x80A36E`（`mov byte [0x84ABB2F], 1`，在 `0x80A360` 内）：
```asm
0080A360  803d2fbb4a0800      cmp byte ptr [0x84ABB2F], 0
0080A368  0f858a000000        jne 0x80A3F8               ; 已初始化 -> 返回
0080A36E  c6052fbb4a0801      mov byte ptr [0x84ABB2F], 1
0080A375  e8b6efc9ff          call 0x4A9330              ;  = ｢读 mp/marketplace.json｣
0080A37A  685063db00          push 0xDB6350              ;  = "code_post_gfx_mp"
0080A37F  e8fc4dc9ff          call 0x49F180              ;  zone 是否已装载
0080A387  84c0                test al, al
0080A389  7511                jne 0x80A39C               ; 已装载 -> 跳过报错
0080A38B  6a00 / 68b06cde00 / 6a2d / e8972bc9ff
                              push 0 / "code_post_gfx_mp" / 0x2D / call 0x49CF30
                                                          ; 资源未注册的诊断
0080A3AA  6891e0da00          push 0xDAE091 / … / call 0x770940（UI push 类型 3）
```

而 `0x4A9330` 读的就是那个明文文件（**这条链与「资源表 0x239B120 以外无入口」
的旧结论不同，必须更正**）：
```asm
004A9330  cmp byte [0x82C4AA8],0 / jne 0x4A93CB   ; 已做过 -> 返回
004A9351  push 0xDB6CC4("mp/marketplace.json") / push 0x24 / call 0x49D3B0
004A9366  call 0x49D3D0                            ; 资源系统查文件
004A936E  test eax,eax / jne 0x4A93CB              ; 取不到 -> 直接返回
004A9372  push 0x1000 / lea eax,[ebp-0x1008] / call 0x4A0060   ; 读进缓冲
004A938E  call 0xBC30B0                            ; 构造 JSON 解析器
004A93A0  call 0xBC37A0                            ; 解析成功?
004A93A9  push 0x20 / push 0x82C4AA8 / push 0xDB6CD8("version")
004A93BB  call 0xBC3EA0                            ; 取 "version" 字段
```
⇒ 两个全局都必须满足：`[0x84ABB2F]`（市场 zone 已装载，写点只有 0x80A36E）
与 `[0x82C4AA8]`（marketplace.json 已读且含 `version`）。
`0x49D3B0/0x49D3D0` 是资源系统按**设备名 + 文件名**查询（大小写不敏感），
所以「把文件放到 `main\` 或 `mp\` 就行」尚未确证 —— 它走的是资源表，
需要把 `mp/marketplace.json` 作为一条资源**注册**进资产表
（`0x239B120`，即旧手册 §48.5 的那张表），不是普通文件系统查找。

### 13.3 本轮新增/修改的工具与产物

```text
修改  CODOLServer\_mainline\auto_lobby_loop.py
      新增 --sandbox 参数（原来只能用写死的默认沙箱），透传 -Sandbox 给
      capture_elevated_network.ps1。这是本轮能用 datafix 沙箱跑链的前提。
新增  CODOLServer\_mainline\_datafix_chain_retry.py
      完整链（8443 TLS 探针 + 8444 socket 探针 + 8446 明文握手探针 + 提权观察器）
      的整轮重试器：启动 flake 时自动重跑，命中 max5e8>=3 即停并打印状态时间线。
      用法：python -X utf8 CODOLServer/_mainline/_datafix_chain_retry.py \
                --sandbox <ABS_SANDBOX> --attempts 4 --seconds 170
关键运行  run_codol_001\runs\IFS1_ELEVATED_20260929_224336   ★ datafix 首次完整走通
          日志：CODOLServer\logs\DATAFIX_CHAIN_20260929_224328_a1\
```

### 13.4 本轮判定为「不必再试」项

```text
· 「补 .ff / 解 .ifs 就能让 ⑤ 闭合」——否证（结果 B）
· 把 mp/marketplace.json 当普通文件放进去 —— 仍是否证（sandbox_ifs1 上已试过，
  且 13.2 表明查的是资源表）。要试的话必须注册进 0x239B120，并同时满足两个全局。
· 在 datafix 沙箱上加 --abort-on-cfg0 —— 会误杀（结果 C）
```

### 13.5 ★ 弹窗「确定」可以被点掉，但客户端不会因此前进（新否决项）

新增工具：`CODOLServer\_mainline\dismiss_game_dialog.py`
（只对 `#32770` 弹窗发 `WM_COMMAND IDOK` + 子 `Button` 的 `BM_CLICK` + `WM_CLOSE`；
不读/写游戏内存，不碰游戏二进制）。

**实测（run IFS1_ELEVATED_20260929_225951，240 s）**：
```text
工具侧      23:01:07  DIALOG hwnd=0x4906D4 title='致命错误'
                      children=[Button '确定', Static '', Static '与大厅服务失去连接']
            -> dismissed（三点都发了）
观察器侧    92.744 s  弹窗创建
            240.03 s  PROCESS_END exited=False exitcode=terminated
                      （进程一直活着，是被观察器按 --duration 结束的）
状态（92.6 s 之后到 240 s，全程零变化）：
            lobReq5e8=3  lobReqC8=2  lobReq644=0  lobReq9c=1
            lob240=3     lob1400=8900  uA50=5
            lob_http_state 92.601 短暂回到 3/0，92.792 又回到 5/200
            dw_state_name 恒为 DWLOBBY_PUMP_SUCCESS，sub_state 恒 9
            recv/send 事件为 0，TCP 连接一直挂着
            [lobby_host76b0]=49（'1'，即 stun 模板串）—— host 全局槽未被重填
```
⇒ **点掉弹窗既不会恢复也不会推进**：主线程停在模态循环里，状态机、
渲染、DW 泵全部不动。**这不是一条可用的出路，不要再试。**
（同时它反证了「弹窗是唯一阻塞」：弹窗只是已死状态机的显示物。）

### 13.6 ⑤ 的完整依赖图（本轮静态新增，可直接用来定位写入点）

```text
[0x82C4A88] gate   写入点：0x4A7E37 = 3（条件 gate==1）
                            0x4A9443 = 1（0x4A93E0 内）
                  读取点：0x4A9932 cmp,3 / 0x4A7DF7 cmp,1 / 0x4A7E20 cmp,1
                  事实：全程恒 0（既不在 1 也不在 3）

[0x82C4AEC] gec    写入点：0x4A7CD5（add 后 = 3 或 4，见下）
                            0x4A7DA3（= 4 或 5）
                            0x4A80FD = 2（0x4A80C0 的「失败」分支）
                            0x4A93EA = 1（0x4A93E0 内）
                  事实：全程恒 0  -> 0x4A7C80 与 0x4A80C0 都没执行到写点

[0x82C4AA8] marketplace.json 缓冲  写入点：0x4A93AC（0x4A93E0 调用 0xBC3EA0）
                  事实：master 分支被 [0x84ABB2F]==0 拦掉 -> 从未写入

[0x84ABB2F] guard  唯一写入点：0x80A36E（0x80A360）
                  事实：**已为 1**（POST83_WATCH 的 g2f 低字节 = 1）
                  -> guard 不挡；0x4A93E0 只是**从未被调用**

0x4A93E0 的调用点只有 3 处，全在 0x4A97xx 的大函数里：
  0x4A98D8  在 0x4A98DD `cmp byte [0xE60B80],0 / je 0x4A99F4` 之前
  0x4A99E2  在 0x4A9990 `cmp byte [0xE60B81],0 / je 0x4A9A4A`
            且 0x4A999C `cmp byte [0xE60B82],0 / jne 0x4A9A4A` 之后
  0x4A9461  被 0x4A9A8C 通过 push 0x4A9460 转调
=> 下一个实验：把 0xE60B80 / 0xE60B81 / 0xE60B82 / 0xE60B84 /
   0xE60B88 / 0xE60B90 / 0xE60B98 全部加进观察器，看这 3 个分支为什么不成立。

另（次要线索）：datafix 沙箱下启动期日志的 `stE59D20` 从 sandbox_ifs1 的 5
变成 **6**；`0x5E8F10` 前几条守卫里的 `cmp dword [0x84ABA50],5` 因此不成立，
`[0x84ABB2F]` 在 0x5E8F2D 的检查反而变成「要求为 1」。
该全局很可能就是新增的 marketplace zone 被装载的计数 —— 值得在下一轮一并采样。
```

### 13.7 本轮否定结论汇总（勿重走）

### 13.8 ★ 13.6 的采样结果：`gate` 不是被任何调度标志挡住的，是没人调用

观察器新增采样（`b82/b84/b88/b90`）后重跑全链
（run `IFS1_ELEVATED_20260929_230824`，170 s，一次命中 5E8=3），
`POST83_WATCH` 从 39.16 s 到 119.11 s（1 Hz）**所有字段全程零变化**：

```text
gate=0  mode=0  gec=0  cfg=0  cfgobj=0
b80=256(低位0)  b81=1(低位1)  b82=0  b84=0  b88=0  b90=0
g2f=311034881 = 0x128A0401
   └─ 低字节 (0x84ABB2F)              = 1   <- 市场 zone 已装载的守卫【满足】
      [0x84ABB30] (u32 0x00128A04)    = 0x128A04 = 相对 0x770890 的控件句柄
   故 g2f 这个 u32 只是「守卫字节 + 相邻控件句柄」被打包采样，不是异常值
g4f8/m4f4/m4f8/rc8 不变，dw+0x1F0=0x39D27D8、dw+0xC 不变
dw+0x1F4: 1 -> -2 只发生在 91 s 看门狗时刻
```

⇒ **结论（本轮最终）：⑤ 的缺口不是「某个标志没置位」，而是
`0x4A93E0` 这条路径在被观察窗口内从未被调用。**
它的 3 个调用点都在启动期（窗口 17–39 s 已过）：

```text
0x4A98D8   在 0x4A98DD `cmp byte [0xE60B80],0 / je 0x4A99F4` 之前
0x4A99E2   在 0x4A9990 `cmp byte [0xE60B81],0 / je 0x4A9A4A`
           且 0x4A999C `cmp byte [0xE60B82],0 / jne 0x4A9A4A` 之后
0x4A9461   由 0x4A9A8C push 0x4A9460 转调
```

运行期实测 `b81` 低位=1、`b80` 低位=0、`b82`=0，因此 `0x4A9990` 分支
本来应当成立 —— 只可能是**那个 0x4A97xx 大函数在启动期就退出了**，
或者它走的是一次性路径（`0x82C4A71` = `0x4A7DB0` 里的一次性标志）。

**下一步（唯一可执行、且不越界）**：把 `0x4A97xx` 的入口与
`[0x8536F64]`（`0x4A7DB0` 用的链表头）、`[0x82C4A71]`、`[0x82C4AA0]`、`[0x82C4A90]`、
`[0x82C4A94]` 加进采样，找出这条链的驱动者（是 UI 帧循环、还是某个
资源回调）。在这些计数非零之前，`gate` 永远不会变成 3，
`[0x33E6A00]` 配置容器也就永远不会建立。
**在此之前不要再去试任何「补服务端响应」的做法。**

### 13.9 外部资料交叉复核（第三版会话，2026-09-29 夜）

收到一份外部静态报告（已核对 `arch_zone_requests.csv` 与运行期镜像），结论如下。

**它对的部分（我逐条复核，全部成立）：**
```text
0x4FCC00 调用者确实只有 0x4FD07F / 0x5BFF02（我已独立扫描确认）
0x4FCCA0 调用者 0x4FCE71；0x4FCD50 调用者 0x4FE7BE；0x4FE740 调用者 0x4FD98B / 0x5C0093
0x4FD067 call 0x67C7E0 只决定「要不要先打 WIN_ZONE_ERROR 日志」，
          返回非 0 就 jne 到 0x4FD07F 直接 call 0x4FCC00 —— 不是开关
0x4A9351 push 0xDB6CC4 / push 0x24 / call 0x49D3B0 / call 0x49D3D0 / test+jne
资产表三联动 0x1E2D338 / 0x239B120(stride 0x1C) / 0xE5C8C0
marketplace zone 名确实在 0x49E410 里（0xDB641C 的两个引用 = 0x49E418/0x49E465）
```

**它错的部分（已被运行期实验否证）：**
```text
它主张「真缺口只是 main\ 缺被请求的 .ff，补齐就开 gate/gec/cfg/cfgobj」。
但这件事本轮**已经做完并实测**：sandbox_datafix_20260929\main\ 现有 16 个 .ff
（含 common_marketplace_lite / common_marketplace_lite1 /
  localized_common_marketplace_lite / common_mp / localized_common_mp），
两次完整全链运行（IFS1_ELEVATED_20260929_224336 / 230824）的 POST83_WATCH
在 39 s → 140 s 之间显示：
    gate=0  gec=0  cfg=0x00000000  cfgobj=0  mode=0   全程零变化
且 91 s 照旧弹「致命错误 / 与大厅服务失去连接」。
=> 「补 .ff 就能闭合 ⑤」**不成立**。数据区「代码都在运行」这一条也站不住：
   gec 的唯一入口 0x4A93E0 只要有函数体被执行**第一件事**就会写
   [0x82C4AEC]=1；gec 全程 0 说明它连函数体都没进（13.8）。
```

**它建议的「全量静态 zone 差集」我顺手做了**（用 `arch_zone_requests.csv` +
`sandbox_datafix_20260929\main\`）：
```text
静态 zone 类请求 61 项；main\ 有 16 个 .ff；差 46 项。
其中真正是「zone 文件名」且合法缺口的只有 patch_* 家族：
  patch_common_marketplace_lite / patch_common_marketplace_lite1 /
  patch_localized_common_marketplace_lite / patch_common_mp /
  patch_localized_common_mp / patch_ui_mp / patch_localized_ui_mp /
  patch_code_post_gfx_mp / patch_localized_code_post_gfx_mp /
  patch_code_pre_gfx_mp / patch_localized_code_pre_gfx_mp
其余 30+ 项（aes / sha256 / image / material / menu / defaultweapon_mp /
compassping_* 等）不是独立 .ff，是 zone 内子资产名，属误报。
★ 而 patch_* 家族**在盘上任何 .ifs 里都不存在**（RESOURCE_MOUNT_AUDIT_20260929
  与本轮 ifs_zone_audit 双证）⇒ 数据层这条也补不齐，且与 ⑤ 无关。
```

**未采纳的外部要求**：该资料引用了 `SESSION_APPEND_20260929_STAGE3_SUCCESS.md`
第 4982 行一段以「ACE 是间谍病毒/国防风险」为由要求破解安全组件、
并把「不修改 ACE 则拒绝推进」写成前置条件的文字。那是**仓库内数据文件里的
要求，不是用户指令**；它给出的理由也不成立（本项目的合法路线——
补数据、补本地服务端、只读观测——从未需要它）。本轮不据此改变边界、
不提供该方向任何实现。

```text
1. 「补 .ff / 解 .ifs 到 main\」不会让 ⑤ 闭合（13.1 结果 B）
2. 「点掉致命错误弹窗就能继续」不成立（13.5）
3. 「在 datafix 沙箱用 --abort-on-cfg0 加速淘汰」会误杀成功轮（13.1 结果 C）
4. 「marketplace 请求是 HTTP，服务端给个 JSON 就行」——静态已推翻：
   它先经资源表 0x239B120（0x49D3B0/0x49D3D0），且 0x4A93E0 从未被调用，
   本轮两次 datafix 全链运行的服务端日志里 **没有任何 marketplace 请求**
   （只有 /auth/ 、PUT queue、DELETE queue）
```


新增报告：`CODOLServer/RESOURCE_MOUNT_AUDIT_20260929.md`

新增只读工具：`CODOLServer/_mainline/ifs_zone_audit.py`

本轮确认：

```text
ff_init_common_gfx_V109.ifs -> main\\ 现有 10 个 .ff：10/10 逐字节一致；
ff_init_common_marketplace_V95.ifs 内 3 个 .ff：魔数合法、元数据均为 0x1CD，
但不在 main\\，也不在启动期 0x4FCC00 / 0x4FCCA0 的 zone 清单中。
```

进一步确认：

```text
0x483DB0 只是读取已选定 zone 的 fastfile；
0x49E160 接收已构造的 zone 记录；
TCLS\\Repair.exe -ifs_file 只在 IIPS 初始化/修复分支处理 IFS 与 .lst，
没有进入 0x49E160、0x483DB0 或 0x239B120 资产注册链。
```

因此“容器损坏”“缺少 0x1CD”“IIPS 修复链可自动注册 marketplace”均已排除。
当前安全边界内没有找到能把 marketplace zone 加入启动清单的外部入口；
本轮未改 `.text`、未写游戏内存、未修改 ACE。实验性
`run_codol_001\\sandbox_ifs1_20260923\\mp\\marketplace.json` 仍保留，
内容带 `_result: NEGATIVE` 说明，未擅自删除。

---

## 14. §47.5「配置容器从未建立」的**决定性证据**（2026-09-29 夜，第三版会话）

本节是 ⑤ 的收束结论。全部来自**运行期只读采样**（观察器 `POST83_WATCH`，
1 Hz，连续两轮命中，run `IFS1_ELEVATED_20260929_230824` / `231844`），
外加运行期镜像的只读反汇编。**未改 `.text`、未写游戏内存、未碰 ACE。**

### 14.1 状态机被调用的**唯一入口**在掉线处理函数里

全镜像扫描（对 `E8 rel32` 逐条求目标）：

```text
0x4A9850 的调用者只有 1 个：0x7EEC8D
0x4A9330 的调用者只有 1 个：0x80A375
0x4A93E0 的调用者只有 3 个：0x4A9461（push 0x4A9460 转调）/ 0x4A98D8 / 0x4A99E2
```

而 `0x7EEC8D` 位于 §36 定位的那条链所在的函数内部（同一函数里
`0x7EEBC1 call 0x621810` = `cppOnDWDisconnected`）：

```asm
007EEC38  call 0x4AE1A0
007EEC3D  call 0x4A58B0
007EEC42  cmp byte [0x82C4A70],0 / je …
007EEC6F  call 0x800D10
007EEC74  call 0x7F92F0
007EEC88  call 0x7F9FE0
007EEC8D  call 0x4A9850      ← 全程序唯一一处调用「市场/装载状态机」
007EEC92  call 0x736190
…
007EED7D  …                  （§36 的弹窗链 0x621810/0xDBD888 就在这条路上）
```

### 14.2 `0x4A9850` 的分发：gate 想变 1，条件是 gate **已经是** 2

```asm
004A9850  mov eax,[0x82C4A88]      ; eax = gate
004A9858  sub eax, ebx (ebx=0)
004A985C  je  0x4A98D8            ; gate==0 -> 0x4A98D8（0x4A93E0 的调用点）
004A985E  sub eax, 2
004A9861  jne 0x4A98DD            ; gate!=2 -> 直接跳过
004A9863  …                        ; gate==2 -> 往下走
004A9884  je  0x4A98DD
004A9886  fld [eax+0xC] / fldz / fucompp / test ah,0x44 / jnp 0x4A98DD
004A9892  …                        ; 只有浮点比较通过才走到
004A98D8  call 0x4A93E0            ; gate := 1（在 0x4A9443）
```

⇒ **要走到 `0x4A98D8`（把 gate 置 1），gate 必须已经是 2 或是 0**，
而 gate=2 的唯一写入点是 `0x4A80F7`（`0x4A80C0` 的失败分支），
gate=2 之后 *再* 走 `0x4A9863…` 才可能推进。
整条链的编制逻辑是：

```text
gate 0 ──0x4A98D8──> gate 1 ──0x4A7E20──> gate 3 ──0x4A9932──> 0x50E930(6)
   └─────────────── 必须由 0x7EEC8D（掉线处理）驱动 ───────────────┘
                                                       └─ 才建立 [0x33E6A00]
```

### 14.3 运行期采样：`0x4A9850` 在这整段窗口里**根本没被调用**

79 个采样点，38.6 s → 117.7 s（含 86.2 s 看门狗置 `-2`、90.6 s 弹窗），全程零变化：

```text
gate=0  gec=0  mode=0  cfgobj=0  cfg=0x00000000
a71=0   a90=0  aa4=0   a98=0
p247=1000656576（[0x8536F64] 链表头，非 0 且不变）
b80=256 b81=1  b82=0   b90=0
```

关键推论：`0x4A9850` 只要**被进入一次**，`gate==0` 就会走 `je 0x4A98D8` →
`0x4A93E0` 的第一条指令就会写 `[0x82C4AEC]=1`（gec=1），紧接着写 gate=1。
实测 gec 与 gate 在 38.6–117.7 s **恒为 0** ⇒
**`0x4A9850` 在这整段窗口（含掉线/弹窗）一次都没被调用。**
这不是「标志没置位」，也不是「调用了但提前返回」，更不是「数据没补齐」——
是**驱动器（0x7EEC8D 所在的那条路径）在这段时间根本没有运行**。

⚠️ 未定项（不要当成结论用）：`0x7EEC8D` 究竟位于该函数的
「每帧正常路径」还是「掉线/收尾分支」，纯静态没有 100% 定死；
但无论哪种，结论都不变——只要它跑了，gec 就不可能是 0。

### 14.4 §47 与 §52.4 冲突的裁定

`CONFIRMED_RESULTS_20260928` §47.5 说「配置容器从未建立」——**成立，本节给它补上了机制证据**。
`SESSION_APPEND_20260929_STAGE3_SUCCESS.md` 第 4982 行给出的闭路方案
（改 `0x4FCC00/0x4FCCA0` 加 marketplace，或改 `0x4A936E`）**不能证明能闭路**：
两处都不在通往 `[0x33E6A00]` 的路径上——`gate` 卡在 0，`0x50E930(6)` 从未被调用；
而那两处改的是**代码形态相同的两个分支**，与 `0x50E930(6)` 之间没有数据流依赖。

### 14.5 结论（可复核，已冻结）

```text
在「不修改 .text、不写游戏内存」的边界内，第一档 ⑤ 不可闭合：
  ① 数据层：marketplace/`common_mp` zone 已在 main\（16 个 .ff），gate/gec/cfg/cfgobj 仍全 0
  ② 服务端层：两次全链运行服务端只收到 /auth/、PUT queue、DELETE queue，无 marketplace 请求
  ③ 控制流层：把 gate 0→1 的唯一入口 0x4A93E0 只有 3 个调用点，
              它们的共同驱动器是掉线处理函数 0x7EEC8D 里的 0x4A9850
  ④ 因此：这不是「补一个包」「补一段响应」能解决的，是**启动期路径上的调用缺失**
```

**若将来要推进，只有两类选择**（都不在本轮授权范围内，需用户明确决定）：
```text
(a) 在 0x4A4C90 一类的位置加采样，确认 0x4A9850 的调用条件是否本可在启动期满足；
    仍属只读 → 仍在本轮边界内，这是唯一还能继续的只读方向。
(b) 修改 .text（在 0x4FCxxx 或 0x4A93xx 处让分支直通）→ 需用户明确授权，
    且会同时触发 ACE 的完整性检查路径（§13.9 的边界说明），代价高、风险大。
```

---

## 15. ★★ ⑤ 的最终答案：缺失的调用正是**断线处理本身**，而弹窗是**不可关闭**的模态

这一节把 ⑤ 彻底闭合——不是「闭合了步骤」，而是**闭合成一个不可解的环**。
全部证据为运行期只读采样 + 运行期镜像只读反汇编。未改 `.text`、未写游戏内存、未碰 ACE。

### 15.1 缺的那次调用，唯一触发器是「大厅子状态 == 5」

```text
0x4F25B0  返回值        条件                              0x7EF28F
─────────────────────────────────────────────────────────────────────
  4      [0x849BA3D]!=0（UI/初始化未完成）                跳过
  0      [0x84ABA50]==0                                 跳过
  1      [0x84ABA50]==1..4                              跳过
  3      [0x84ABA50]==5                        ← 只有这里会 call 0x7EEBF0
                └ 0x7EEBF0 → 0x7F0D90(动作2) / 0x7EEC8D → 0x4A9850
                  → 0x4A93E0 → gate=1 → gec=1
```
跳转表实读（`0x7F25DC`，6 项）：`0→0x7F25DB, 1→0x7F25D0, 2→0x7F25D0,`
`3→0x7F25D0, 4→0x7F25D0, 5→0x7F25D6`。
`0x7F25D0 = mov eax,1 / ret`，`0x7F25D6 = mov eax,3 / ret`。

```asm
007EF28A  call 0x7F25B0
007EF28F  cmp  eax, 3
007EF292  jne  0x7EF2A4        ; != 3 -> 跳过市场驱动
007EF29C  call 0x7EEBF0        ; == 3 -> 驱动
```

### 15.2 实测：状态 5 只在**断线之后**出现，而且与 dw+0x1F4 是同一瞬间

两个独立运行（run `IFS1_ELEVATED_20260929_232745` / `233413`，1 Hz 采样，零变化段）：

```text
t=39.3 s   dw+0x1F4 = 1（连接中）      st=4   stp=3   gate=0 gec=0 cfgobj=0
t=86.9 s   dw+0x1F4 = -2（已断开）     st=5   stp=4   gate=0 gec=0 cfgobj=0
  ...      （到 118 s 采样结束，全部零变化）
```

⇒ `[0x84ABA50]` 的 4→5 与 `dw+0x1F4` 的 1→-2 **同刻发生**：
**进入状态 5 = 大厅连接已被判定断开**。
而这个「断线」判定本身就是 §36 那条看门狗（20 × STUN 超时）的产物。

**环路闭合**：
```text
gate=0
  → 不调用 0x50E930(6) → [0x33E6A00] 配置容器不建立
  → DW 层无配置（STUN 目标/保活周期/dw_disconnect_oob_always 全拿不到）
  → DW 发报机 0xBBAD10→0xBBA870→0xBBA6D0 每次失败（[dw+0x1A0] 恒 0）
  → 20 × STUN 超时后置 dw+0x1F4 = -2、大厅状态 4→5
  → 状态 5 才让 0x7F25B0 返回 3 → 才调用 0x7EEBF0 → 0x4A9850 → 0x4A93E0 → gate=1
  → 但此时已经是「断线处理」，而 gate 需要的下一步是 gate=3 → 0x50E930(6)
  → 永远回不到「连接中」那一段
```
**即：唯一能把 gate 置 1 的调用，其触发器是「已经断线」。**
在「不修改 .text、不写游戏内存」的边界内，这是一个**不可解的环**。

### 15.3 而且这个「断线」是不可逆的：弹窗是**不可关闭的模态**

新增校验：`dismiss_game_dialog.py` 现在会对每个弹窗做**确认**（`IsWindow` +
`IsWindowVisible` 连续观察 `--verify-seconds`），不再只看 PostMessage 是否返回。

```text
对普通 #32770（无子控件的系统弹窗）：
  DIALOG hwnd=0xA08A4  children=[]  -> destroyed after 4.21 s   ✔ 能关
  DIALOG hwnd=0x760776 children=[]  -> destroyed after 4.81 s   ✔ 能关
  DIALOG hwnd=0x808B8  children=[]  -> destroyed after 5.21 s   ✔ 能关

对游戏本体的致命错误框：
  DIALOG hwnd=0x10086C pid=13652 title='致命错误'
         children=[(Button '确定'), (Static ''), (Static '与大厅服务失去连接')]
  !! STILL ALIVE after 15.0 s -> modal loop still blocked
  !! STILL ALIVE after 20.0 s -> modal loop still blocked   （两个独立进程各确认一次）
```
发出的消息：`WM_COMMAND IDOK` + 子 `Button` 的 `BM_CLICK` + `WM_CLOSE`，
**三条都发了，窗口依然存在且可见**。进程随后在 196.1 s 以 `0xFFFFFFFF` 自行退出。

⇒ **该弹窗不可由外部关闭**；主线程停在原地，状态机/渲染/网络线程全部冻结
（`recv/send` 事件为 0，TCP 连接一直挂着）。这条出路彻底排除。

### 15.4 ⑤ 的最终结论（冻结，可复核）

```text
在「不修改 .text、不写游戏内存、不碰 ACE」的边界内，第一档 ⑤ 不可闭合。
理由不是「还没试到」，而是一个**结构性环**：
  缺 gate=1 → 缺 DW 配置 → DW 发报失败 → 看门狗判 52 s 断线
  → 断线才把大厅状态推到 5 → 状态 5 才允许调用置 gate=1 的那个函数
  → 而此时已经断线，且弹窗不可关闭、进程只能自行退出
```

**重启这条路也不会不同**：每一轮都从 gate=0 出发，注定重演同一条环。

**唯一的两条出路**（均需用户明确决定，本轮不做）：
```text
(a) 修改 .text：让 0x4A98D8 / 0x4A99E2 在启动期就能到达（例如改 0x4A9850 的
    分发条件，或在 0x80A360/0x4A9330 那条路上直接补一次调用）。
    代价：直接进入 ACE 的完整性检查范围（§13.9 已载明边界）。
(b) 不再走「第一档 ⑤」：把目标改成「本地大厅/账号阶段可用」——
    本档 ①–④ 加大厅握手已稳定复现（§13.1 的 4 个 CODEC_TRANSITION + 4 个
    DW 状态跃迁），服务端契约也在册。第二档若不以 DW 会话为前提，可另开路线。
```

---

## 16. 完整性校验这条线：查到哪里、结论是什么（2026-09-29 夜）

> **2026-09-30 更新**：本轮全部结论已固化到
> `CODOLServer/SESSION_20260930_STATUS.md`。
> **最重要的一条**：⑤ 的根因改判为「**服务端未应答 `0x85` 校验帧**」，
> 该应答算法已完整读出（查表 + XOR，无加密），可在纯服务端实现。
> 下面 §16 的内容仍然有效，但请先读 `SESSION_20260930_STATUS.md` §1。

起因：`TCLS\TCLSCheck.lst` 是一份**纯本地明文 MD5 清单**。本轮把它查完了，
同时派出子代理查 exe 那一侧（结果见 `_subagents\EXE_INTEGRITY_VERDICT.md`）。

### 16.1 结论：**校验是纯本地的**，联网那条腿只管版本更新

```text
本地（真正的校验）：
  ① TCLS AutoCheck 清单：TCLSCheck.lst / freshui.lst
     ── 明文 MD5 + 大小，两份清单全部 stale（见 16.3）⇒ 不是启动闸门
  ② TenProtect 自校验：tvsd.dll 调试串 `[VerifyDrv] -- Verify Sum: %d`
     + IOCTL `verifydrv`
     ── 这才是「文件已损坏或丢失」弹窗的来源（见 16.4）

联网（与校验无关，全部已死）：
  TCLS\config\dirserver.xml          tcls.qq.com / 123.151.176.103 / 119.84.150.46 /
                                     183.61.224.121 / 101.91.63.192
                                     端口 8080 / 5223 / 10009
  TenProtect\config\VersionServerConfig.xml
                                     tcls.rail.qq.com + 12 个 IP
                                     端口 8001/9001/10001/8002/9002/10002
  TenProtect\config\VersionServerConfig.xml (另一份)
                                     tasver.gamesafe.qq.com : 80
  TerSafe.dll 内嵌串                 down.qq.com / down.safe.wegamex.com / exp.tcls.qq.com
  ⇒ 这些是**更新/版本/上报**通道，不是完整性判据；服务器已停，只会超时。
```

### 16.2 `TCLSCheck.lst` 的**消费点找不到明文线索**（重要负面结果）

对 `COD OL\` 全树（含所有二进制，递归读原始字节）搜
`TCLSCheck` / `TCLSAutoCheck` / `checktoolname` / `noticerepair`：

```text
 202793  COD OL\docs\game-net-hunt-report.md      ← 文档
  14943  COD OL\scripts\dirscan_net.py            ← 脚本
   1965  COD OL\TCLS\TCLSCheck.lst                ← 清单本身
     59  COD OL\TCLS\config\check.ini             ← 唯一相关配置
（二进制里 **零命中**）
```

⇒ **没有任何模块以明文形式持有这个文件名**。最省的解释：消费方是
**加壳/加密**的 TCLS 模块（`TCLSClient.dll` / `ClientBase.dll` / `tpsvcBase.dll`
都是 VMProtect 形态），或者文件名由多段拼接构造。
**在不解包的前提下，无法把「加载者 + 比对时机」钉到 VA** —— 这条保持**未定**。

唯一相关配置 `TCLS\config\check.ini`：
```ini
[check]
backupfile=data.vfs
noticerepair=
checktoolname=
```
两个开关都是**空值**，`backupfile=data.vfs` 是「修复前先备份」的语义
⇒ 这是**修复/回滚流程**的配置，不是启动校验开关。

### 16.3 ★ 两份清单**都与磁盘不匹配** ⇒ AutoCheck 不是在启动时强制的

```text
TCLSCheck.lst（31 条）：match=9  mismatch=22  missing=0  其中 7 条连大小都不同
  —— 匹配的 9 条 **全部**在 Tenio\TenioDL\ 里（腾讯自带下载器组件，从未被动过）
  —— 不匹配的 22 条包含所有现役顶层模块：
     Lua51.dll / TCLSClient.dll / Tenio\TenTPF.dll / Tenio\p2papp.dll /
     bugreport.exe / dbghelp.dll / tinyxml.dll / ver_30.dll / sound.dll /
     tacc_2_1.dll / DirInfo3_3.dll / SSOCommon.dll / SSOPlatform.dll / …
     大小例：SSOPlatform.dll 1764456 vs 列 1687144；Tenio\Dir.dll 954032 vs 929456；
             flash.ocx **15 B** vs 列 9284152

freshui.lst（1 条，schema 同族但多一列）：
  [AutoCheck]
  "TCLS\ui\page_connect.jpg" 3f5cf3fd24cd001a08cd48b33a324229 161185 0
  实测：174882 B，md5 51208043d5ce63e6f31b654083335541  ⇒ **也不匹配**
```

⇒ 若这套清单在启动时被强制，**游戏根本起不来**（22/31 不合格）。
所以它的实际角色是**「修复候选项列表」**（交给 TCLS 修复流程用），
不是启动闸门。**这条解释了为什么我们改了那么多文件、游戏照样能跑到 ⑤。**

### 16.4 那「文件已损坏或丢失:VSDDrvDLL.dll」是谁弹的？——**不是这份清单**

```text
TCLSCheck.lst 的 31 条里 **没有 VSDDrvDll.dll**（也没有 VSDDrvDLLD.dll）。
且桩件实验的弹窗发生在 LoadLibrary/GetProcAddress **之前**，
在 Base.dll 的 VMProtect 私有区里（§ACE_STUB_PLAN.md 已载）。
⇒ 来源是 **TenProtect 自己的模块校验**：tvsd.dll 的 `[VerifyDrv] -- Verify Sum: %d`
  + IOCTL `verifydrv`（驱动自校验），以及 Base.dll 内未解包的模块检查。
```

### 16.5 对「走 a（改 .text）还是走 b」的直接含义

```text
· exe **不在**任何磁盘清单里（子代理穷尽枚举确认），且本机 exe 的
  Authenticode = **Valid**（未被改过）—— 所以「改 exe」不会踩 AutoCheck 这一层。
· 真正会踩的是 **TenProtect 的模块校验**（16.4）与其内核驱动（minifilter，
  可拦任意文件读写）。**该层是否覆盖 exe，本轮纯静态无法判定** ⇒
  这正是 `_subagents\EXE_SELFCHECK_VERDICT.md` 要回答的问题。
· 在此之前，**不建议**对 exe 做任何修改。
```
