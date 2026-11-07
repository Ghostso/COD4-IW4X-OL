# CODOL 游戏内 `[100]` 弹窗动态来源报告

日期：2026-09-25
执行目录：`D:\BaiduNetdiskDownload\使命召唤OL`
证据类型：动态运行 + 挂起期预授权只读内存 + 桌面像素截图 + 静态反汇编核对

---

## 一、结论先行

`[100]无法连接大厅服务!` **不是 Win32 MessageBox**，而是游戏自己的 GFx / Scaleform UI。

本次动态运行第一次拿到了**覆盖整个主模块的解密内存**（`0x00400000..0x00E65000`，read_fail_pages=0），因此找到了此前静态分析看不到的代码路径。最关键的两条直接证据是：

1. `@SF_UI_DW_LIVE_CONNECTING_FAILED` 在内存中**被真实代码直接引用**：

```text
007EF253  684006DE00        push 0xDE0640
007EF258  E8E31FF8FF        call 0x771240
```

   这个字符串就是 `localization.txt` 里的 `@SF_UI_DW_LIVE_CONNECTING_FAILED`，
   对应正文「无法连接大厅服务!」。

2. `0x771240` 是这套游戏内面板的**错误/提示投递函数**。它在内部根据 `esi` 指向的
   UI 对象状态决定如何组装并渲染面板，面板左上角的 `[100]` 是这套 UI 通道使用的
   **面板/错误标识号**，不是 TQoS 或 Blaze 的返回值。

因此，`[100]` 的直接来源是：

```text
dwLobby 状态机
   -> 007EF0D0  (每帧调用，读 DW 状态)
   -> 状态枚举值 == 4
   -> 检查 DW_DUPLICATE_LOGIN
   -> 决定显示 @XBOXLIVE_DUPLICATE_LOGIN 或 @SF_UI_DW_LIVE_CONNECTING_FAILED
   -> 007EF258  push @SF_UI_DW_LIVE_CONNECTING_FAILED
   -> call 00771240  (GFx 面板投递)
   -> 屏幕出现 [100]无法连接大厅服务!
```

## 二、动态证据

### 2.1 运行实例

```text
run dir:
  CODOLServer\_mainline\_dyn100_run_20260925_182324

game:
  run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe

pid:
  4448

memory window:
  0x00400000 .. 0x00E65000

read failures:
  0
```

关键用途：本次读取是在 `CREATE_SUSPENDED` 阶段先取得 `PROCESS_QUERY_INFORMATION |
PROCESS_VM_READ` 句柄，等 ACE 武装后继续使用同一句柄只读采样；没有写内存、没有注入、
没有修改系统网络、没有碰 ACE 驱动。

### 2.2 内存变化

```text
t=0.01s  nonzero=6439402
t=2.47s  nonzero=6439402
t=4.76s  nonzero=9352689   (第一批 100-dword 出现)
t=7.17s  nonzero=9354757
t=9.53s  nonzero=9354781
t=99.16s nonzero=9354801
```

运行后期内存稳定在 9,354,801 个非零字节，和早先只覆盖
`RVA >= 0x594000` 的旧 dump 相比，本次多了完整的低地址解密代码区。

## 三、真实调用链

### 3.1 每帧入口

```text
00808246  681069DE00   push 0x00DE6910      ; "Live_Frame"
0080824B  6AFF         push -1
0080824D  E8DE56E6FF   call 0x0066D930
00808252  E8E9D40000   call 0x00815740
00808257  6A00         push 0
00808259  E8726EFEFF   call 0x007EF0D0      ; 每帧进入 DW lobby 状态机
```

`Live_Frame` 字符串和后面的字符串 ID 表位于同一段只读数据：

```text
00DE68CC  @PLATFORM_POPUP_CONNECTION
00DE68E8  <during startup>
00DE6900  popup_connecting
00DE6910  Live_Frame
00DE691C  "1750"
00DE6924  "1751"
...
```

### 3.2 状态机取状态

```text
007EF0D0  55            push ebp
007EF0D1  8BEC          mov ebp, esp
007EF0D3  83EC14        sub esp, 14
...
007EF1C8  E8F3340000    call 0x007F26C0
007EF1CD  E8DE330000    call 0x007F25B0
007EF1D2  8BF0          mov esi, eax       ; <-- 当前 DW/lobby 状态
...
007EF1DE  83FE03        cmp esi, 3
007EF1E1  752D          jne 0x007EF210
...
007EF210  83FE04        cmp esi, 4          ; <-- 失败分支
007EF213  0F8502020000  jne 0x007EF41B
```

### 3.3 `[100]` 分支

```text
007EF219  A13CEAE400    mov eax, [0x00E4EA3C]
007EF21E  681006DE00    push 0x00DE0610     ; "DW_DUPLICATE_LOGIN"
007EF223  50            push eax
007EF224  C70534BA490802000000  mov [0x0849BA34], 2
007EF22E  E8DD54F8FF    call 0x00774710     ; 比较/查询 DW_DUPLICATE_LOGIN
007EF233  8B35ACB84908  mov esi, [0x0849B8AC]
007EF239  83C408        add esp, 8
007EF23C  85C0          test eax, eax
007EF23E  7513          jne 0x007EF253     ; 非零 -> 走「无法连接大厅服务」

007EF240  682406DE00    push 0x00DE0624     ; "@XBOXLIVE_DUPLICATE_LOGIN"
007EF245  E8F61FF8FF    call 0x00771240
007EF24A  83C404        add esp, 4
007EF24D  5E            pop esi
...
007EF253  684006DE00    push 0x00DE0640     ; "@SF_UI_DW_LIVE_CONNECTING_FAILED"
007EF258  E8E31FF8FF    call 0x00771240     ; 投递并渲染错误面板
007EF25D  83C404        add esp, 4
007EF260  5E            pop esi
```

### 3.4 为什么此前静态分析找不到

主 exe 的 `.tp3` 在磁盘上是加密/保护的；旧运行时 dump 只覆盖
`RVA >= 0x594000`。本次证明了真正的状态机代码在：

```text
0x007EF0D0..0x007EF2EF
```

即 `RVA = 0x3EF0D0`，**低于旧 dump 的起始 RVA 0x594000**。因此所有基于旧 dump 的
xref 结论都会漏掉这条路径。

## 四、`[100]` 的数字是什么

`100` 不是 `BD_LOBBY_PROTOCOL_VERSION_FAILURE`（该枚举值为 17），也不是
TQoS 请求里的 `BusinessID=100`。

证据：

- 这条代码路径没有把 TQoS 的 100 传给 `0x771240`。
- `0x771240` 的调用点只压入字符串 key：

```text
007EF253  push 0x00DE0640
007EF258  call 0x00771240
```

- `0x771240` 读取 `esi+8` 的 UI 对象类型，并把字符串和 UI 上下文交给
  `0x76EDF0` 的 GFx/面板投递层。

因此 `[100]` 是这套游戏内错误面板的**固定 UI 标识/面板编号**。它和同一个
`@PLATFORM_POPUP_CONNECTION` / `popup_connecting` 注册表一起使用，不能被当成
网络协议里的错误码去反推服务端应答。

## 五、深层原因

`[100]` 面板的深层触发条件是：

1. dwLobby 状态机处于状态 `4`；
2. 在这个状态下，`DW_DUPLICATE_LOGIN` 检查结果使分支跳到 `007EF253`；
3. 于是调用 `@SF_UI_DW_LIVE_CONNECTING_FAILED` 的面板投递路径；
4. `0x771240` / `0x76EDF0` 把它渲染成 `[100]无法连接大厅服务!`。

所以它不是单纯的“UDP 8000 没有回包”。单答 TQoS 8000 之所以仍会看到 `[100]`，
是因为这条分支处在 **dwLobby / duplicate-login 状态机**，而不是 TQoS 应答层。

## 六、可复用的产物

本次新增工具（都在 `CODOLServer\_mainline\`）：

```text
_dyn100_mem.py        挂起期预授权只读内存采样器
_dyn100_run.ps1       单实例编排 + 窗口/桌面/内存采样
_dyn100_site.py       任意 VA 的十六进制 + capstone 反汇编窗口
_dyn100_fn.py         lobby key 真实调用点反汇编
_dyn100_lit.py        字符串/格式字面量扫描
_dyn100_ptr.py        字符串指针槽扫描
_dyn100_popup_tbl.py  popup 注册表 / 字符串 ID 表解码
```

一次运行产物：

```text
CODOLServer\_mainline\_dyn100_run_20260925_182324\
  mem_stdout.txt
  live\live.jsonl
  live\image_best.bin
  shots\desktop_*.png
  windows\windows.jsonl
```

