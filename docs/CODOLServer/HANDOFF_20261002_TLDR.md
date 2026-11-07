# CODOL 逆向任务交接页

生成时间：2026-10-02
主手册：`CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md`（7074 行，55+ 小节）

本页是**精简交接**：先看这里，需要细节再回主手册对应小节。

---

## 一、任务目标

动态捕获密钥 + 静态解密，产出完整明文资料，推进《使命召唤OL》复活。
游戏已停服六年。**不存在官方应答样本，不要去找。**

---

## 二、硬性边界

**始终禁止**：关闭/停止/配置/规避 ACE、TenProtect
（历史实测会导致蓝屏 `0x01010002`）。

**用户已明确解锁（2026-10-01）**：
patch `.text` / 下断点 / 调试器。
已知后果：ACE 会告警（历史实测 `3 / 1023 / 61022`）。

**环境注意**：`--force-p608-zero-key` 曾因同时写 `p604` 导致
连续 5 次启动崩溃（`0xFFFFFFFF`，9-11 s），已修复为只写 `p608`。

---

## 三、当前状态一览

| 项 | 状态 |
|---|---|
| 层一 `.ff` 解密 | 已全线打通，明文在 `_cleanout\ff_layer1\` |
| 层二 `.ff` 解密 | 未完成（Base.dll `.tls` 受 VMProtect 保护） |
| 第一档① 0x81 握手 | 已闭合 |
| 第一档② 0x82 / +0x5FC | 已闭合 |
| 第一档③ 0x83 回显 | 已闭合 |
| 第一档④ 0x85 帧结构/方向/seq/AES-CBC/HMAC | 已闭合（多次交叉验证） |
| **第一档⑤ 状态机推进** | **未闭合 —— 卡点已精确定位** |

---

## 四、第一档⑤卡点（最重要，先看这段）

### 4.1 一句话

> 客户端收到我们发的 0x85 帧后，内层流首字节不是 `0x87`，
> 于是 0x87 arm 分支从不进入，`[obj+0x644]` 恒为 0，
> c8 停在 2，约 90 秒后弹"与大厅服务失去连接"。

### 4.2 决定性实验（已做，结论可靠）

给 `0xBA35E9`（arm 失败出口 `je`）打 `74 D6 -> 90 90`：

    PATCH_ARM  pre7=74d6  post7=9090  ok7=True

只要 `0xBA3590` 被执行到该点，下一条就是
`0xBA35EB mov [esi+0x644], 1`，必然置 1。

**但实测 644 全程 = 0**（38.6 s .. 150.5 s）。

=> 唯一解释：`0xBA3590` 从未被调用 => `cl != 0x87`。

### 4.3 卡点的位置

    0xBA3AE0  mov cl, [ebp-0x389]      ; 内层流首字节
    0xBA3AE6  cmp cl, 0x87             ; ★ 不成立
    0xBA3AE9  jne 0xBA3B0E

`[ebp-0x389]` 由 `0xBA3AA3` 从内层流读取，
内层流由 `0xBA3A91 call 0xB783C0` 提供。

### 4.4 为什么内层流不对（2026-10-02 更正为：源基址根本不是缓冲指针）

**此前的说法（provider 输出与读取器源不一致）已作废。**

逐条核准后的实参链：

    0xBA44AD  mov ecx, [esi + 0xB0]      ; esi = 连接对象
    0xBA44B3  call 0xB9BBB0              ; 返回 [ctx+0x1C]-[ctx+0x24]+0x1F
                                          ; —— 这是一个【数值】，不是指针
    0xBA44BE  mov ebx, eax               ; ebx = 该数值
    0xBA44B8  mov edi, [esi + 0xAC]      ; edi = 帧长（实测 382）
    ...
    0xBA46BF  push ebx                   ; -> 0xBA3710 的 arg1
    0xBA46C2  call 0xBA3710

而 0xBA3A91 处：

    0xBA3A90  push ebx                   ; arg1 = 源基址（= 上面那个数值）
    0xBA3A91  call 0xB783C0              ; memcpy(dst, arg1+arg3, 1)

=> **memcpy 的源 = 数值 + 游标，不是帧缓冲** => 读到的字节不是 0x87。

### 4.5 关键核对（本轮新增，证明推导可靠）

    t=39.854  obj+0xA0 = 382   obj+0xA4 = 4   obj+0xAC = 382   （收到帧）
    t=40.058  obj+0xA0 = 382   obj+0xA4 = 0   obj+0xAC = 0     （处理完）

- `obj+0xA0` = 帧内 u32 长度字段的落点（与静态推断一致）
- `obj+0xAC` = 帧长（0xBA3710 的 arg3）
- `obj+0xB0` = 每帧不同的有效堆指针（POST83_SAMPLE 实测）

并且 `0xBA44AD..0xBA46C2` 之间**只有两处写 ebx**，分属不同分支：

    0xBA44BE  mov ebx, eax          <- 0x85 路径
    0xBA465E  mov ebx, [ebp+0xC]    <- 0x84 路径（在 0xBA4682 jmp 处结束）

=> 到 0xBA46C2 时 ebx 未被改写，arg1 确实是那个数值。

### 4.6 还有一个必须记住的前提：补丁后的控制流

`--patch-85-pass` 会改 6 处站点，其中 `0xBA35BF: 74 16 -> EB 16`
把 arm 的两个前置判定**全部略过**：

    0xBA35BF  EB 16          -> 无条件跳到 0xBA35D7
    0xBA35D7  cmp [esi+0x644], 0     ; 实测满足
    0xBA35E2  call 0xBA3010          ; 唯一剩下的门槛
    0xBA35EB  mov [esi+0x644], 1

而 0xBA3010 内部（malloc / 0xB9BEB0 / 0xB76620 / 0xB75F30 / 0xB75E00）
已逐条验证恒成功。

=> 只要 0xBA3590 被调用，644 必然置 1。
   实测 644 恒 0 => 0xBA3590 确实未被调用 => cl != 0x87。

**推演这段控制流时务必按补丁后的字节来算，
否则会得出与观测矛盾的结论（这正是 2026-10-02 之前多轮误判的原因）。**


### 4.7 下一步（唯一的核对项）

    0xBA3710 的 arg1 本应是一个缓冲指针，实际却是
    0xB9BBB0([obj+0xB0]) 的返回值（一个数值）。

两种可能：

- 甲：该对象在我们的环境下未按预期初始化，`0xB9BBB0` 返回了差值；
- 乙：`0xBA44AD..0xBA46C2` 之间还有一处未识别的 ebx 改写（已扫描，只找到两处且分属不同分支，倾向排除）。

=> 这一步与"服务端发什么"无关，是客户端内部的数据流。

**若目标是进入大厅，只有两条路：**

- 改客户端代码 —— 已实测 5 次，全部导致启动崩溃（见 §六）
- 或改变该对象的构造 —— 同样需要在客户端内部写入，受限相同

**注意：不要再用"改应答内容"的思路尝试**，
该方向已被穷举并否证（零 key / 派生 key / [4:20] / 随机 IV /
arm-first / 长度字段覆盖）。


## 五、已完全解决的部分（可直接复用）

### 5.1 帧尾 MAC 公式（3 次独立验证）

    MAC key = codec_0420(obj + 0x60C 的 20 字节)     # 完整 20 字节
    tag8    = HMAC_SHA1(MAC key, frame[:len(frame)-8])[:8]

验证记录：`E57A5C_20261001_220416_a2` / `221440_a2` / `222340_a2`，
每轮 seq=1(len386) 与 seq=2(len194) 均逐字节命中。

### 5.2 接收侧 AES 密钥（3 次独立验证）

    AES key16 = codec_02A0(obj + 0x620 的 20 字节)[4:20]   # 注意是 [4:20]

验证记录：`bac75308...` / `266a380d...` / `496fc8b9...`
三组独立材料均逐字节命中 `p608+0x14`。

### 5.3 帧布局（与客户端逐字节一致）

    [0:4]   长度字段 = 382（总长 = 字段 + 4）
    [4]     类型 = 0xAB（客户端->服务端）/ 0x00（服务端->客户端）
    [5]     opcode = 0x85
    [6:10]  seq
    [10:26] 16 字节 IV
    [26:-8] 密文体
    [-8:]   tag8

### 5.4 provider 对象布局 / vtable

    +0x00 vtable = 0xD95520
    +0x04 key_len = 16
    +0x0C cipher ctx（schedule 在 +0x9C）
    +0x14 key[16]（每帧前被客户端重写，会滚动）

    vtable 0xD95520（provider 族）
      +0x04 = 0xC73AF0  set_key
      +0x08 = 0xC73BB0  get_key
      +0x0C = 0xC73C10  decrypt      <- 0xBA39FB 调用的
    vtable 0xD95514（HMAC 族）
      +0x04 = 0xC73760  update
      +0x08 = 0xC737A0  取 20 字节

### 5.5 codec 表

    TABLE_02A0 = 80 22 de aa 0b 1c 21 f4 00 ff ee 37 27 92 10 ce aa f4 3c 21
    INDEX_02A0 = 13 12 09 04 11 01 0a 08 0d 02 0f 03 0c 10 05 07 00 0e 06 0b
    TABLE_0420 = 41 13 09 ae 3f a3 bc f3 18 72 ea bc 09 32 11 cc 12 42 54 f4
    INDEX_0420 = 07 11 0e 10 09 13 0d 00 02 03 04 08 01 0a 0b 05 12 06 0c 0f

### 5.6 关键函数地址

    0xBA4430  大厅分发器入口（ecx = 连接对象）
    0xBA3710  0x85 入站校验器
    0xBA2A60  0x85 发送组帧（有两条互斥路径）
    0xBA3420  复位例程（0xBA3456 是唯一写 c8=4 的指令）
    0xBA3590  0x87 arm（成功则置 644=1）
    0xBA3600  0x89 业务（成功则置 c8=1 并置 644=2）
    0xBA0FF0  内层消息解析器
    0xC73800  HMAC 对象构造
    0xC73AF0  set_key
    0xC73C10  decrypt
    0xC781C0  cipher init（内部 0xC78212 是 key 拷贝循环）
    0xC78360  取 provider+0x14 的 16B 到调用者缓冲
    0xC78390  do_cipher
    0xB78350  带边界检查的 memcpy（len 是 arg6）
    0xB783C0  流读取器（内层分发用这个，不是 0xB78350）

### 5.7 obj 关键偏移

    +0xC8  状态（2 = 就绪；1 = 进大厅；4 = 复位）
    +0x5E8 握手步（3 = 0x83 完成）
    +0x5EC 收包计数
    +0x5F0 发包计数
    +0x5FC 0x83 回显值
    +0x604 发送侧 provider 指针
    +0x608 接收侧 provider 指针
    +0x60C 发送侧 codec 源（20B）
    +0x620 接收侧 codec 源（20B）
    +0x640 分发判据（0xDC）
    +0x644 arm 标志（0/1/2/3）
    +0xD9  24 字节材料源（会话常量）

---

## 六、已否证清单（禁止重复）

| 方法 | 结果 |
|---|---|
| 原样回显客户端 0x85 | 无效 |
| AES ECB/CBC/OFB/CFB/CTR 全矩阵扫 352B | NO_HIT |
| `u32 N + 数据[N]` TLV 记录切分 | records=0 |
| 从 p604/p608 内存扫 HMAC key 窗口 | NO_MATCH |
| 服务端 seq 从 1 开始 | 被 seq 门拒绝，必须从 0 |
| 零 key 注入可持续保持 | 否证（客户端每帧重派生） |
| patch `0xC78212` 可消除密钥竞态 | 否证（仍有第二处覆盖） |
| `HMAC(sha1(frame), conn+0xD9 派生物)` 是帧尾 MAC | 否证 |
| 随机 IV / 全零 IV 可通过应答校验 | 否证 |
| `0xBA3010`/`0xBA2A60` 收到残留栈参数导致失败 | 否证（补丁生效仍不置 644） |
| `DebugActiveProcess` 迟附加 | ERROR_ACCESS_DENIED |
| `DEBUG_ONLY_THIS_PROCESS` 创建即调试 | 4/4 在 ~2s 抛 0xC0000005 |
| 给 BreakpointProbe 加地址后迟附加 | 约 3 s 游戏崩溃（0xC0000005 -> 0xC0000409） |

**跨轮次数据比对一律无效**：`obj+0x60C` / `obj+0x620` /
`p604+0x14` / `p608+0x14` 全部逐帧变化。
必须用同批采样（`TRIO_SNAPSHOT` 事件）。

---

## 七、环境与复现

### 7.1 提权代理（必须先启动，掉线需重启）

```powershell
Start-Process -FilePath "cmd.exe" -ArgumentList '/c','"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_elevated_agent_admin.cmd"' -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping
# 期望 debug_privilege = true
```

### 7.2 运行前清理

```powershell
Get-Process | Where-Object { $_.ProcessName -match "codoMP|AboProbe|TQMCenter" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 30     # 间隔不足会导致启动期 0xFFFFFFFF 崩溃
```

### 7.3 一键实验（当前配置）

```powershell
python -X utf8 "CODOLServer\_mainline\_e57a5c_experiment.py" `
  --sandbox "D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929" `
  --attempts 3 --seconds 170 `
  --follow-85 --follow-85-rule receive --follow-85-cbc `
  --reply-85-cbc --reply-85-seqs 1,2,3,4 --reply-85-arm-first `
  --patch-85-pass `
  --plain-port 8446 --poke-port 8443
```

可选：
- `--follow-85-delay 40`  延迟发送（客户端约 T+38 s 才进入大厅状态）
- `--force-p608-zero-key` 数据级零 key（注意：只写 p608，已修）

### 7.4 编译观察器（改 AboProbe.cs 后必须执行）

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\restore_iips_contract_001\observer2"
dotnet publish -c Release -o out      # 运行用的是 out\，不是 bin\
```

### 7.5 验收判据（唯一有效）

**不要**看 c8/5e8/5ec，那套判据在多种失败情形下都"成立"。

只看：

    aboprobe.stdout 全程无 `class=#32770` 且无 `text=与大厅服务失去连接`

---

## 八、关键文件

    CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md   主手册（7074 行）
    CODOLServer\lobby_server\lobby_plain_probe.py    探针
    CODOLServer\_mainline\_e57a5c_experiment.py      实验驱动
    restore_iips_contract_001\observer2\AboProbe.cs  观察器
    run_codol_001\elevated_ifs1_observer.ps1         观察器包装

    run_codol_001\runs\<TAG>\aboprobe.stdout         观察器输出（最重要）
    CODOLServer\logs\<TAG>\plain.jsonl               探针输出
    CODOLServer\logs\<TAG>\rx.txt                    接收侧材料（实时刷新）
    CODOLServer\logs\<TAG>\tx.txt                    发送侧材料（实时刷新）

    解包镜像（静态反汇编用）：
    CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
    （完整 PE，基址 0x400000，10.9 MB）

---

## 九、重要工具陷阱

1. **RVA vs VA**：该模块 image base = 0x400000。
   观察器打印的是运行时 VA；文件里是 RVA。
   混用会导致读错位置（曾据此得出错误结论）。

2. **`Ev()` 只保留 4 个字段**：多余参数会被静默丢弃。
   需要更多字段时另开事件名。

3. **`--eip-trace` 命中率极低**：实测整轮 0 命中。
   不适合抓微秒级指令。

4. **观察器采样门槛**：曾有 `t >= 30.0` 的门槛，
   导致握手期间（t≈0）拿不到数据。已移除。

5. **探针与观察器有相位差**：探针在 T+0.17 s 就发应答，
   而观察器约 T+38 s 才进入大厅采样。
   跨这个差读文件必然拿到陈旧值。

---

## 十、一句话交接

    第一档①②③④全部闭合，⑤的卡点已精确定位到一条数据流衔接：

      客户端解我们的 0x85 后，内层流首字节不是 0x87
      ⇒ 0x87 arm 分支从不进入 ⇒ [obj+0x644] 恒为 0
      ⇒ c8 停在 2 ⇒ 约 90 s 后弹"与大厅服务失去连接"

    注意 [ebp-0x50] 的角色（§4.5 / 手册 §5.27.56）：
      它【不是】provider 的输出缓冲，而是帧内那 16 字节密钥块
      的落地位置（先由 0xBA37C2 读入，再整块交给 provider）。
      更早一版交接页把它当成输出，该表述已作废。

    决定性实验（手册 §5.27.52）：
      给 0xBA35E9（arm 失败出口）打 NOP，补丁确认生效
      （PATCH_ARM ok7=True, 74d6 -> 9090），但 [obj+0x644] 仍为 0
      ⇒ 0xBA3590（0x87 arm）根本没有被调用。

    已排除：密码学、帧结构、各状态前置、arm 内部逻辑、参数残留。
    密码学部分（MAC + AES）各经 3 次独立验证，可直接复用。

    最终定位（手册 §5.27.81 / §5.27.82 / §5.27.83）：

      0xBA3710 的 arg1 = 0xB9BBB0([obj+0xB0]) 的返回值，
      这是一个【数值】而不是缓冲指针；
      而 0xBA3A91 -> 0xB783C0 把它当作 memcpy 的源基址。

      ⇒ memcpy 源 = 数值 + 游标，落在错误地址
      ⇒ 读到的字节不是 0x87
      ⇒ cl != 0x87 ⇒ 0xBA3590 不被调用
      ⇒ [obj+0x644] 恒 0 ⇒ c8 停在 2 ⇒ ~90 s 弹窗

    性质：客户端自身的数据流问题，与服务端所发内容无关。
    已穷举否证：零 key / 派生 key / [4:20] / 随机 IV /
                arm-first / 长度字段覆盖 / 改 0xBA3A90 / 改 0xBA3A2A。

    仍在开放的唯一通道：观察器（AboProbe 正常模式）能读游戏内存，
    不受 ACE 阻挡（它采到了 c8/5e8/5ec/644/p608/p604/ac/b0 等实时值）。
    外部手段（ReadProcessMemory / ImageDump / 调试器）均已被阻断。
