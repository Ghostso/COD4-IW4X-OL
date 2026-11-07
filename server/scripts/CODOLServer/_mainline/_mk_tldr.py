# -*- coding: utf-8 -*-
HANDBOFF = r"""# CODOL 逆向任务交接页

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

### 4.4 为什么内层流不对（已定位）

    provider 解密输出 -> [ebp-0x50]        （0xBA3A05 call [p608.vtable+0xC]）
    内层读取器 0xB783C0 的数据源参数里【没有出现 [ebp-0x50]】

=> 两者不是同一块内存，首字节当然不是 0x87。

### 4.5 下一步要验证的一件事

在 `0xBA39E7 .. 0xBA3A2C` 之间，是否存在一步
"把 provider 输出送入内层流"的拷贝。

- 若有：找出该拷贝的条件（可能就是本次卡点）
- 若无：说明 0x85 内层消息不走这次 provider 调用，
  而是走另一条更早的路径（0xBA1477 那套 + 0xC73800 摘要）

---

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
      （provider 输出写到 [ebp-0x50]，而内层读取器没读它）

    已排除：密码学、帧结构、各状态前置、arm 内部逻辑、参数残留。
    密码学部分（MAC + AES）各经 3 次独立验证，可直接复用。

    下一步只有一件事：
      确认 0xBA39E7..0xBA3A2C 之间是否存在"把 provider 输出
      送入内层流"的拷贝。有则卡点即在此；无则内层消息另走一条路径。
"""
open(r"CODOLServer\HANDOFF_20261002_TLDR.md", "w", encoding="utf-8").write(HANDBOFF)
print("written, lines =", len(HANDBOFF.split("\n")))
