# CODOL 主线逆向：运行时引擎区固化方案

> 约束更正（2026-09-25，用户明确）：**不存在“不要碰 ACE”这条约束。**
> 用户原话是“干掉 ACE”。ACE 是待处理目标，不是分析边界。
> 本文档及后续所有方案不再以此作为限制条件。

时间：2026-09-25
范围：`codoMP_client_shipRetail.exe` 副本的静态结构与已确认的运行时解密区
状态：工具链完成并通过自检；等待一次提权启动以生成全量运行时 dump

## 1. 已独立复核的静态事实

- EXE SHA-256：
  `36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`
- PE32/I386，ImageBase `0x00400000`，Entry RVA `0x0E5DC690`。
- 导入表只有 1 项：
  `codoMP_client_shipRetailBase.dll!ordinal_1`，IAT `0x0E9DC665`。
- 但 EXE 内部存在 1528 处 `FF 15` 间接调用，指向 1083 个不同槽位；
  其中 651 处指向 `0x00CA8xxx` 哨兵表。
- `config_mp.cfg` 字符串位于 RVA `0x009BCFE0`（VA `0x00DBCFE0`）。
  全文件只有 1 处 32 位立即数引用，位于文件偏移 `0x000AF56D`；
  该处属于不可执行的 `.tp3` 数据区，不是代码引用。
- `dwlobbyhost` / `blazehost` / `lobbyhost` 在 EXE 中零命中。

结论：磁盘上的 EXE 不是可线性反汇编的完整程序；大量代码和字符串在
VM 解密后的运行时内存里。继续在磁盘文件里搜索大厅地址没有收益。

## 2. 已确认的运行时事实（来自既有 ICH 证据）

- 引擎 gap：`0x00994000..0x00CA789A`，磁盘为零，运行时由 Base.dll
  `.tvm0` 在约 `t=5.075s` 一次性填充为有效 x86。
- 首个被证明执行的引擎函数：`0x00CA0000`，在 IIPS 加载前执行。
- 运行时哨兵表：`0x00CA8000`，把 EXE 原生 `FF 15` 槽位连接到解密后的
  引擎函数。
- `RESTORE001_FUNCTION_DUMPS.csv` 已保存 14 个真实运行时函数的 hex。
  这些函数不是壳代码，包含标准 prologue、`ret imm16`、`int3` padding、
  虚调用和绝对字符串引用。
- 既有 RESTORE-ENGINE-BRIDGE-001 证明：Gate 之后引擎不读文件、不读注册表、
  不发网络请求，处于 Base VM dispatch continuation 的 standby。

## 3. 已定位的运行时字符串引用点

从已有 14 个运行时函数中提取出的绝对立即数引用：

```text
0x00CD2550  C4_resource_ops
0x00CD3468  C3_resource_a
0x00CD34B0  C3_resource_a
0x00CD34F8  C3_resource_a / C3_resource_b
0x00CD3538  C3_resource_a / C3_resource_b
0x00CD35F4  C3_resource_b
0x00CD3618  C3_resource_a / C3_resource_b
0x00CD3950  C4_resource_ops
0x00CD8340  C6_config_fs
0x00CD8388  C6_config_fs
0x00CD9490  C10_major_sub
```

这些地址落在静态文件未落盘的运行时数据区，只有内存 dump 才能还原字符串。
其中 `C6_config_fs` 的两个引用最接近配置/文件系统层，是下一轮优先分析点。

## 3A. cfg 子代理结论（Base.dll）

子代理对 `codoMP_client_shipRetailBase.dll`
（SHA-256 `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`）
完成了可见原生代码的机械穷举：

- `.text`（RVA `0x1000`，size `0x742000`）和 `.tls`（RVA `0xB0A000`，
  size `0xED3000`）中，对 `LoadLibraryA`/`GetProcAddress` IAT 槽的
  `FF15`、`FF25`、`8B05`、`A3`、`push`、`mov`、`mov [mem],reg` 等
  13 种编码全部零命中。
- `.idata2` 中有 660 条自定义 hint+name API 条目，覆盖 KERNEL32/
  ADVAPI32/WS2_32 等；但 `CreateFileW`、`ReadFile`、`WriteFile`、
  `CryptDecrypt` 等名称只有 2 个 32 位 RVA 指针引用，且都落在
  `.tls` 的非指令 blob 中。
- `CryptImportKey` 全文件零命中，因此“标准 CryptoAPI 导入会话密钥再
  `CryptDecrypt`”这条路径在名称表层面被否定。
- 结论：cfg 的读取/解密逻辑不在可见 `.text` 的普通 IAT 调用链中；
  只能在 `.tls` 自解码区或 `.tvm0`。可见证据无法进一步裁决，
  报告明确标为 `UNKNOWN`。

详细报告：

```text
CODOLServer\_subagent_cfg_crypto.md
CODOLServer\_subagent_cfg_crypto_xref.csv
```

## 4. 主线工具链

新增文件：

```text
CODOLServer\_mainline\engine_dump.py
CODOLServer\_mainline\engine_analyze.py
run_codol_001\run_engine_dump_admin.ps1
run_codol_001\run_engine_dump_admin.cmd
```

`engine_dump.py`：

- 只使用 `OpenProcess` + `ReadProcessMemory`。
- 不注入、不 hook、不 patch、不改系统网络。
- 默认转储 `0x00994000..0x00D34000`，覆盖引擎代码、哨兵表和运行时字符串区。
- 额外转储 `0x00CA8000` 哨兵表、`0x00CD0000` 字符串区、
  `0x00E83A00` dispatch table、`0x00E83C00` global state。
- 每 4 秒采样，保存变化样本和最优样本。

`engine_analyze.py`：

- 提取 ASCII/UTF-16 字符串。
- 匹配 config/cfg/lobby/blaze/demonware/dvar/server/host/http/iips 等关键词。
- 扫描 `push imm32`、`lea`、`mov reg, imm32` 等绝对引用。
- 对命中点用 Capstone 反汇编上下文。

自检结果：合成样本可正确识别 `dwlobbyhost=...`、`blaze...qq.com`、
`config_mp.cfg`，并给出 `push` / `mov` 引用与反汇编窗口。

## 5. 下一次提权运行

在管理员 PowerShell 中执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_engine_dump_admin.ps1' `
  -DurationSeconds 75 -DumpSeconds 40 -DumpDelaySeconds 9
```

或双击/运行：

```text
D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_engine_dump_admin.cmd
```

它会在 `run_codol_001\runs\ENGINE_DUMP_<timestamp>\engine\` 生成：

```text
engine_best.bin
engine_*.bin
sentinel_table.bin
runtime_strings.bin
dispatch_table.bin
global_state.bin
engine_dump.jsonl
engine_analysis.md
```

运行结束后回报 `DONE=` 路径；下一步直接对 `engine_analysis.md` 和
`C6_config_fs` 附近引用做真实引擎代码逆向。

## 6. 第一次提权转储的结果（2026-09-25 11:15）

运行目录：

```text
run_codol_001\runs\ENGINE_DUMP_20260925_111537
```

### 6.1 关键时序发现

```text
t= 0.12s  engine gap 0x994000..0xD34000  nonzero=3261702  928/928 pages
t= 4.25s  same
t= 8.30s  entire region reads back as ZERO  (pages=0/928)
```

即：引擎区在约 5-8 秒之间被整块释放/清零。首次采样已抓到解密后的
真实代码，最终样本却是零。这说明后续采样必须提前，且附加窗口要在
“最佳样本”时刻同步抓取，而不是等到结束。

已据此修正：`DumpDelaySeconds=4`、`DumpStepSeconds=2`、转储范围扩到
`0x00E65000`，附加窗口在最佳样本点同步抓取，并新增 `vm_code`。

### 6.2 engine_best.bin 的实际内容

- 大小 3,801,088 字节（0x3A0000），非零 3,261,702（85.8%）。
- 含 3,749 处 `FF 15`，指向 1,277 个不同槽位。
- 字符串主体是 Scaleform/Flash 运行时（`URLRequest`、`NetConnection`、
  `Socket`、`ContextMenu`、`Capabilities`、XML/Expat）与 libcurl
  （`Failed to connect to %s port %ld`、`Hostname in DNS cache`）。
- 未出现 `config_mp.cfg`、`dwlobbyhost`、`blaze`、`demonware`等
  CODOL 业务层符号。

结论：该窗口主要执行 UI/Scaleform 与 libcurl 初始化，还不是大厅层。
之前把 `C6_config_fs` 当作配置层的判断需要修正：它引用的
`0x00CD8340` / `0x00CD8388` 实际是 Scaleform
`DisplayObject`/`DisplayObjectContainer` 的 not-implemented 串。

### 6.3 决定性发现：运行时哨兵表是真实函数指针表

`engine_best.bin` 中 `0x00CA8000` 处有 995 个非零槽位，绝大多数是
形如 `0x116A9xxx` / `0x116ABxxx` 的真实代码指针：

```text
0x00CA8000 -> 0x116AB4FE
0x00CA8004 -> 0x116ABE48
0x00CA8008 -> 0x116AAB9A
...
0x00CA8114 -> 0x116AC863
```

分布：

```text
0x116A0000 区段   397 个指针
0x00C95DA0 起连续表  ~196 个指针（每 0x10 递增）
系统 DLL          少量（0x748C/0x752C/0x7555/0x76FE/0x7700 等）
```

⇒ `0x116A0000` 是一个**PE 头未声明、运行时才映射进来的可执行区**，
承载 VM 解密后的游戏/引擎真函数。EXE 里那些指向 `0x00CA8xxx` 的
`FF 15` 槽位，正是通过这张表间接调到 `0x116Axxxx`。

已落盘映射表：

```text
CODOLServer\sentinel_runtime_map_20260925.csv   (995 行 slot_va,target_va)
```

这是目前第一个把“静态 EXE 槽位”与“运行时真函数”连起来的结构，
也是下一轮逆向大厅/网络的正确入口。

## 7. 第二次转储（建议）

用升级后的脚本再跑一次，重点取：

```text
vm_code.bin        0x116A0000, 0x20000     <- 运行时真函数区
sentinel_table.bin 0x00CA8000, 0x1000      <- 函数指针表
engine_best.bin    0x994000..0xE65000      <- 完整运行时窗口
```

命令不变：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_engine_dump_admin.ps1' `
  -DurationSeconds 75 -DumpSeconds 18 -DumpDelaySeconds 4 -DumpStepSeconds 2
```
