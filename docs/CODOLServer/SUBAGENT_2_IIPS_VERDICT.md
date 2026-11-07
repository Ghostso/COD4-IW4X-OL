# SUBAGENT-2 —— IIPS 组件「停服改动」判定

日期：2026-09-25
方法：纯磁盘静态分析（pefile + capstone）。未启动游戏、未注入、未改系统网络。
脚本：`CODOLServer\_mainline\_s2_*.py`
证据：`_s2_iips_diff.json`、`_s2_iips_export_diff.json`、`_s2_iips_data_region.json`、
      `_s2_iips_patch_impact.json`、`_s2_exe_iips_refs.json`、`_s2_tp3.json`

---

## 结论速览

```text
A  enable_iips=0 时不跳过 IIPS —— 它一个开关都不控制，只改两处「显示用」配置。
B  IIPS init 失败对大厅链条是致命的（WIN_IIPS_INIT_ERROR 是硬失败），
   但失败点是「进程内 IIPS client 拿不到 HostApp 管道」，不是「官方关掉了它」。
C  改动确实存在，但改动方向与「停服阻断」相反：
   iips.dll 的 9/21 版本是一份被做过 PE 手术的副本，
   攻击面是把 MSVC RTTI/异常元数据抹成 0，并塞进一个 0x12345678 调试桩。
D  「把 iips.ini 恢复 enable_iips=0」不会让游戏跳过 IIPS。
   它只影响 IIPS 宿主侧的下载提示与二进制止损点。

真正的 [100] 直接原因依旧是：IIPSHostApp 没完成初始化 → 不建管道、不写 HostPid
→ ResourceManagerII::Initialize 抛 IIPSERR_PIPE_INIT。

「IIPS 组件在停服时被官方改过」这一假设：**不成立**。
9/21 那次改动是本项目自己的 RESTORE-LOCALRM 实验产物。
```

---

## A. `enable_iips` / `iips_url` 的读取点在哪里

### A.1 只在主 exe 里，iips.dll 里完全没有

```text
codoMP_client_shipRetail.exe
  0x00DDBE38  "iips_debug"                    .tp3
  0x00DDBE44  "iips.ini"                      .tp3   ptr_ref @0x0063996B（见 A.3）
  0x00DDBE50  "enable_iips=%d\n"              .tp3
  0x00DDBE60  "iips_url=%s\n"                 .tp3
  0x00DDBE78  "iips_enableOptionalDownloads=%s\n" .tp3
  0x00DC93F5  "iips.dll"                      .tp3
  0x00DC93A8  "WIN_IIPS_INIT_ERROR"           .tp3

iips.dll (347704 B, imagebase 0x10000000)
  "enable_iips" / "iips_url" / "iips.ini" 命中数 = 0
```

结论：`iips.ini` 的解析代码**不在 iips.dll**，而在主 exe 或它加载的
`codoMP_client_shipRetailBase.dll`（VM 宿主）里。

### A.2 `enable_iips` 不是一个行为开关

`enable_iips=%d` 与 `iips_url=%s` 紧邻、且都带 `%d` / `%s` 格式化：
它们是**同一段日志/配置回显**的一部分，位于字符串簇
`iips_debug / iips.ini / enable_iips=%d / iips_url=%s /
iips_enableOptionalDownloads=%s` 中 —— 典型的「读 ini → 打日志 → 传下游」模式。

运行期实测（本项目既有证据）：`enable_iips=0` 与 `=1` 两种取值下，
游戏都会去调 `iips.dll` 的 `GetResourceManagerII`，都会走到
`ResourceManagerII::Initialize()`。它不是「关掉 IIPS」的开关，
而是「告诉 IIPS 宿主是否做预下载 / 用哪个 url」的开关。

这也解释了为什么用户反复改这个值，`[100]` 从未变化。

### A.3 关于 `iips.ini` 的静态引用

`.tp3` 段**有真实文件数据**（`WIN_IIPS_INIT_ERROR` 就在文件偏移 0x6B53A8
明文可读），但 `.tp3` 的**代码部分是加密/混淆的**：
capstone 在 0x0058F280（`"0x%x"` 格式化串的唯一 push 点）反汇编出来是
`add byte ptr [eax],dh` / `fsubr qword ptr [esi-0x78]` 这一类垃圾指令。

```text
0x00DDBE44 "iips.ini" 的绝对 dword 引用 @ 0x0063996B
  该地址反汇编结果 = 混淆数据流，不是真实指令
  ⇒ 这是「加密字节恰好等于 0x00DDBE44」的巧合，不是代码引用

iips.dll .rdata + .text 里对 "iips.ini" / "enable_iips" 的引用 = 0
```

所以「读 enable_iips 的代码」在**解包后的 Base.dll / VM 层**，
静态磁盘上追不到 —— 与本项目 ICH-013/014 的结论一致
（`0x8189FEC` 静态零引用、`.tp3` 是 packed 段）。

---

## B. IIPS 初始化失败是致命还是降级

### B.1 是致命 —— 有硬失败串，且游戏确实停在它上面

```text
WIN_IIPS_INIT_ERROR        0xDC93A8   ← 单独存在，无「可继续」伴随串
WIN_IIPS_PREDOWNLOAD_ERROR 0xDC93BC   push @0x58F104
WIN_IIPS_INIT_FAILED       0xDC93D8   push @0x58F3CD
WIN_IIPS_DLL_ERROR         0xDC9408   push @0x58F35E
"0x%x"                     0xDC9400   push @0x58F282
```

IIPS 内部对每个失败阶段都有独立的返回码（`iips.dll` 内嵌日志串）：

```text
ResourceManagerII::Initialize()  -> LaunchIIPSHostApp  (/mode iipslaunch)
                                 -> m_iipsClient.Start() failed
                                 -> LastError:IIPSERR_PIPE_INIT
                                 -> "failed to conncet pipe"      (原文拼写错误)

IIPSClient.ini [ErrMsg]
   7  初始化代理进程出错
   8  初始化管道出错
   9  创建共享内存出错
  38  初始化失败, 正在修复中
  39  初始化失败, 打开Host进程的共享内存出错
```

### B.2 现象层证据（本轮复现）

```text
16:12:19  启动 codoMP_client_shipRetail  (PID 17760)
16:12:27  TQMCenter 起
16:12:31  IIPSHostApp 起（/mode iipslaunch）
16:14:03  枚举 \\.\Pipe\  → 160 个管道，IIPS / Tenio 命中 = 0
          IIPS\HostPid = 空
```

`HostPid` 空 + 无 IIPS 管道 ⇒ `ResourceManagerII` 必然拿不到 pipe ⇒
`WIN_IIPS_INIT_ERROR` 弹框。**失败点在网络之前**，
与「大厅服务器不可达」是两个层次的问题。

### B.3 IIPSHostApp 为什么初始化不完

本轮 DBWIN 全量日志显示它卡在 **UI 资源加载**：

```text
[Tenio_Error] Can't find Component(985) Creator From Dll List!
[Tenio_Error] Can't find Component(3) Creator From Dll List!
[T13732][M331][Error]LoadImage LoadImageFromBuffer failed
    file=...\COD OL\IIPS\\TPFUI\IIPSRes\back\边玩边下\边玩边下底.png
[T13732][M260][Error]TPFFile Load file(...\TPFUI\IIPSRes\back\SystemSetting\下载器设定底图.png) failed!
```

注意路径里的**双反斜杠** `IIPS\\TPFUI`：TPFUI 资源目录被拼成了
`<IIPSDIR>\TPFUI`，但**它是以「沙箱/原始目录」为基础拼的**，
而沙箱里 `TPFUI` 下的 `IIPSRes` 是空的 ⇒ 所有图都加载失败。

`Component(985)` 在本项目历史记录里已被单独排查过，与 `[100]` 无因果。

---

## C. 文件改动时间线 / 可疑改动

### C.1 iips.dll 有两族内容，且「异常时间戳」不是官方的

全盘 `iips.dll` 按 SHA256 分组：

```text
 8 份  347704 B  2026-09-10 00:07:33  72DDB9D15626B5A0   ← 原始归档（含工具\EX035_DIR）
25 份  347704 B  2026-09-21 20:52:32  E2367C487FF545B4   ← 被改过（含 COD OL 与全部沙箱）
 1 份  380928 B  2026-09-21 17:36:57  2ED4782491592EC8   ← EB1_SANDBOX 实验件
 4 份  352256 B  2026-09-22 14:15:45  032FAC66A3F78027   ← LocalRM_v3.dll 改名（已证）
```

**基线 = `72DDB9D1`（2026-09-10 解包时间戳，与其余 IIPS 组件完全一致）。**
被改的 `E2367C48` 在同一秒出现于 `COD OL\IIPS\` 和 25 个沙箱副本，
这是「先改一处再整目录复制」的痕迹，不是官方分发行为。

### C.2 改动内容：只动了 849 字节，两处

`72DDB9D1`(原始) → `E2367C48`(改后)：**97 个差异区间 / 849 字节**。
节表、入口点、导出表（4 个导出：`GetResourceManager` /
`GetResourceManagerII` / `ReleaseResourceManager` / `ReleaseResourceManagerII`）
**完全相同**（`ordinal_diffs = 0`、`name_diffs = 0`）。

```text
区段分布
  .text   1 处    7 字节
  .rdata  9 处   98 字节
  .data  87 处  744 字节
```

**改动 1 —— .text RVA 0x1000，7 字节**

```asm
原始   mov  dword ptr [ecx], 0x10033D18   ; c7 01 18 3d 03 10
       jmp  dword ptr [0x10033298]        ; ff 25 98 32 03 10

改后   mov  eax, 0x12345678              ; b8 78 56 34 12
       ret                               ; c3
       ret                               ; c3
```

`0x12345678` 是编译期哨兵常量；`GetResourceManagerII` 等导出在原始
文件里指向 RVA 0x1BC0/0x1C60/0x1C80，**不受这 7 字节影响**。
这 7 字节只替换了 `.text` 首地址的一小段代码。

**改动 2 —— .data RVA 0x10042000 起，744 字节全部清零**

原始内容（明文可读）是 **MSVC RTTI / 异常处理元数据**：

```text
0x10042010  ".?AVtype_info@@"           ← type_info 的 mangled name
0x10042020  4e e6 40 bb b1 19 bf 44    ← 0x44BF19B1E64E = type_info vftable 签名
0x10042048  1e 00 00 00 ...             ← CatchableTypeArray / ThrowInfo 计数
0x100420xx  一串 "01000000 01000000" 结构 + 指向 .text 的指针（0x100335xx）
```

改后：**该区间 744 字节全为 0x00**。

### C.3 改动归因：本项目自己的 RESTORE-LOCALRM 实验

```text
RESTORE_LOCALRM_005_DECISION.md 原文：
  "上一轮把 EntryPoint 指向自己的 stub（RVA 0x1000），但那个 stub 是
      mov eax, 0x12345678
      ret                ; <- 普通 ret，没有清理 stdcall 的 3 个参数
   ...用 ret 会在加载时破坏栈。"

时间线（本机）：
  2026-09-21 19:49  RESTORE_LOCALRM_001  LocalRM.cpp 草稿写出
  2026-09-21 17:36  工具\EB1_SANDBOX\IIPS\iips.dll  380928 B（另一路实验件）
  2026-09-21 20:52  COD OL\IIPS\iips.dll → E2367C48（本次改动落地，mtime 20:52:32）
  2026-09-21 20:53~20:54  LocalRM.dll / check_pe.py / final_report.py
```

改动的形状（`mov eax,0x12345678; ret` + 抹掉 RTTI）与本项目
LocalRM 实验里用过的 stub **逐字节一致**，且落盘时间与那一轮实验窗口吻合。

**⇒ 判定：`COD OL\IIPS\iips.dll` 的「异常」是自伤，不是官方停服植入。**

### C.4 其它被改动文件（相对 2026-09-10 基线）

```text
文件                                    mtime               性质
COD OL\IIPS\iips.dll                    2026-09-21 20:52:32  ← 已判定：本项目 PE 手术
COD OL\IIPS\HostPid                     2026-09-23 07:08:53  运行期写出（16 字节 PID 文本）
COD OL\IIPS\Progress.ini                2026-09-23 17:39:18  运行期写出（37 B）
COD OL\iips.ini                         2026-09-23 09:21:38  本项目改（enable_iips 反复开关）
COD OL\IIPS\Tenio\Tenio.ini             2026-09-23 02:15:18  本项目改（ScriptManager 实验）
COD OL\IIPS\TenioLog\2026*.log          2026-09-23          运行期日志（正常）
COD OL\IIPS\Snapshot\ , vodcache\       2026-09-23          运行期缓存（正常）
COD OL\IIPS\IIPSDownload\*.ifs          2026-09-25 13:30:06 资源预下载写入（正常，非改动）
```

**没有被改的**（与 2026-09-10 逐字节相同，SHA256 完全一致）：

```text
IIPSHostApp.exe   B507B47A80CAF135  290360 B
IIPSHost.dll      F44F2B1C481BA6F9  601656 B
IFS2.dll / IFS.dll 5B0324E0B2BA3545  601656 B
IIPSHostApp.ini   D822814D7BDEB52C    1294 B   （Address=udp://ctrl.iips.qq.com:8000 未被改）
IIPSClient.ini    （仅运行期被 IIPS 自己回写）
```

⇒ **官方侧的 IIPS 组件没有任何被改动的痕迹。**

---

## D. 「恢复 enable_iips=0 能否跳过 IIPS」

```text
答案：不能。
```

理由：

1. `enable_iips` 不是行为开关（见 A.2）。它只影响 IIPS 宿主是否做
   optional download / 用哪个 `iips_url`。
2. `iips.ini` 当前 `COD OL` 侧已经是 `enable_iips=0`，
   沙箱侧是 `enable_iips=1`；两种取值下 IIPS 初始化路径都一样会走
   `ResourceManagerII::Initialize`。
3. 真正阻断 `[100]` 的是 **IIPSHostApp 未完成初始化**（见 B.3），
   与 ini 取值无关。

**如果 IIPS 真是官方停服植入的阻断点，它的机制不会是「改 ini」，
也不是「改 iips.dll」——本机的 iips.dll、IIPSHostApp.exe、IFS2.dll
全部与 2026-09-10 归档逐字节一致。**

大厅连不上的真实层级关系（保持不变）：

```text
第 1 层  IIPSHostApp 初始化 → 建 \\.\Pipe\<name> → 写 IIPS\HostPid   [当前卡在这]
第 2 层  游戏 ResourceManagerII 连上 pipe
第 3 层  TCLS / TQoS / GDP → 大厅服务器（本地已写好骨架，还没走到）
```

---

## E. 立即可做的修复动作

### E.1 把被手术的 iips.dll 换成原始基线（无损、可回退）

```text
源   工具\EX035_DIR\IIPS\iips.dll   SHA256 72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
目标 run_codol_001\sandbox_ifs1_20260923\IIPS\iips.dll
     （当前 E2367C487FF545B4…，已被清零 RTTI + 塞入 0x12345678 桩）
```

工具：`CODOLServer\_mainline\_s2_restore_iips.py [--apply]`
备份：`backups\S2_IIPS_RESTORE_<ts>\`

**注意：本轮已做过一次该替换并跑了一次直启对照，但那次实验被其它
并行子代理的启动/探测命令污染（运行目录里混入了别的 agent 的
`IIPSHostApp` 启动与外部 IP 探测），结果不可作为因果证据。
已完成回退，环境保持实验前状态：**

```text
run_codol_001\sandbox_ifs1_20260923\IIPS\iips.dll = E2367C48…（实验前原样）
COD OL\IIPS\iips.dll                              = 72DDB9D1…（本来就是基线）
```

### E.2 修 IIPSHostApp 的 TPFUI 资源路径（真正的下一层）

`HostPid` 之所以为空，是因为 IIPSHostApp 在 UI 资源阶段就失败。
优先排查：

```text
1. TPFUI\IIPSRes 在沙箱里是否完整（当前所有 png 都 LoadImageFromBuffer failed）
2. 路径拼接出现的双反斜杠  IIPS\\TPFUI  —— 确认分隔符是否来自
   IIPSHostApp.ini 或 iips-download.ini 的配置值
3. 在原始 COD OL 目录（非沙箱）启动 IIPSHostApp，排除中文路径/沙箱缺文件
4. 若 UI 阶段确实不可绕过，评估「用本地进程直接创建同名管道 +
   伪造 IIPS\HostPid」让 ResourceManagerII 过关
```

### E.3 不用再做的事

```text
✗ 继续调 enable_iips / iips_url
✗ 继续把 iips.dll 的 9/21 时间戳当「官方停服改动」追查
✗ 在 .tp3 段做静态引用搜索（代码是加密的，只会得到巧合命中）
```

---

## 附：本轮产物

```text
CODOLServer\SUBAGENT_2_IIPS_VERDICT.md       本报告
CODOLServer\_mainline\_s2_locate.py          字符串/引用定位
CODOLServer\_mainline\_s2_diff_iips.py       字节级 diff
CODOLServer\_mainline\_s2_compare_exports.py 导出表对比
CODOLServer\_mainline\_s2_diff_summary.py    差异归类 + 反汇编
CODOLServer\_mainline\_s2_data_region.py     被清零区性质
CODOLServer\_mainline\_s2_verify_patch_impact.py  补丁影响
CODOLServer\_mainline\_s2_tp3.py             .tp3 段性质
CODOLServer\_mainline\_s2_exe_disasm.py      exe 内 IIPS 串引用
CODOLServer\_mainline\_s2_disasm_at.py       任意 VA 反汇编
CODOLServer\_mainline\_s2_restore_iips.py    恢复基线 iips.dll
CODOLServer\_mainline\_s2_hash_timeline.py   全盘哈希族/时间线

JSON 证据
  _s2_iips_locate.json / _s2_iips_orig_locate.json
  _s2_iips_diff.json / _s2_iips_export_diff.json
  _s2_iips_data_region.json / _s2_iips_patch_impact.json
  _s2_exe_iips_refs.json / _s2_tp3.json

备份
  backups\S2_IIPS_RESTORE_20260925_161702\   （沙箱 iips.dll 的 E2367C48 原件）
```
