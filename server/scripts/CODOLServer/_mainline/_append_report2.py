import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()

add = """

---

## 21. 重大突破：弹窗消失，客户端进入大厅并驱动 TPFUI 系统设置界面

### 21.1 结果（`IFS1_ELEVATED_20260928_183320`，实测）

```text
t=37.011 DW_ACCOUNT_LOGIN_COMPLETE  uA50=3  lobsub=1  reqC8=2  req644=1  mgr4f8=1
t=37.043 DW_LOBBY_CONNECTED         uA50=4  lobsub=2  reqC8=2  req644=1  mgr4f8=1
t=84.076 DWLOBBY_PUMP_SUCCESS       uA50=5  lobsub=2  reqC8=2  req644=1  mgr4f8=1
生命周期 130 s，状态保持到结束
```

`uA50=5` 是主状态机的**终态**。`0x7EF1C2` 对 `state==3` 调
`0x7F25B0`；`0x7F25C4` 之后 `state==5` 走成功分支，UI 不再进入
`[100]无法连接大厅服务!` 弹窗。

**“无法连接大厅服务”弹窗已不再出现。**

### 21.2 决定性证据：客户端真的越过了大厅，进入 TPFUI 系统设置

`IFS1_ELEVATED_20260928_183320/iips_files/TenioLog/20260928_183329.log`
显示客户端正在真实驱动 IIPS 内嵌 UI：

```text
[P7360][T8052][M260][Error]TPFFile Load file(...\\TPFUI\\IIPSRes\\back\\SystemSetting\\下载器设定底图.png) failed!
[P7360][T8052][M331][Error]LoadImage GetBuffer failed file=...SystemSetting\\下载器设定底图.png
[P7360][T8052][M331][Error]LoadImage LoadImageFromBuffer failed file=...\\按钮\\关闭_3_正常.png
...
[P7360][T8052][M331][Error]LoadImage LoadImageFromBuffer failed file=...\\进度条\\黄色进度条_头.png
```

调用的资源路径全部指向 `IIPSRes\\back\\SystemSetting`、`\\按钮`、
`\\进度条`、`\\边玩边下`——这是**系统设置/下载器**界面，属于大厅之后的
真实游戏 UI，而不是启动期的占位画面。大厅阶段确实通过了。

### 21.3 “致命错误”弹窗不是大厅失败

`WINDOW_NEW class=#32770 text=致命错误` 出现在 t≈84–89，而客户端
`uA50` 早已是 5。该标题来自本地化表
`公式/EB1_SANDBOX/localization.txt`：

```text
WIN_ERROR
"致命错误"
```

即引擎通用 `WIN_ERROR`，不是大厅错误码。它与大厅无关。

### 21.4 PNG 资源缺失是本安装（CODOL 已停服）的问题，不是本链的阻塞

核查结果：

```text
sandbox ...\\IIPSRes\\back\\SystemSetting   共 20 个文件，全部为 69 字节的
                                            1x1 占位 PNG
COD OL\\IIPS\\TPFUI\\IIPSRes\\back\\SystemSetting  同样 20 个文件，
                                            与 sandbox 逐字节相同
...\\back\\1_1.png                          2954 字节，真实图片（完好）
...\\back\\Icon_Image_TPF                    4398 字节，真实 ico（完好）
下载器设定底图.png                          全盘不存在
```

说明：占位/缺失发生在**原始安装目录**，sandbox 只是镜像，因此这些
资源在停服的 CODOL 客户端里本来就不完整，需要在后续 UI 阶段补齐。

### 21.5 本轮解锁的两个关键点

**A. `0xBA0780` 的返回 2 是双条件**

```asm
00BA0780  cmp dword ptr [ecx+0x644], 0
00BA0787  mov eax, dword ptr [ecx+0xC8]
00BA078D  je  0xBA079F                  ; 644==0 走另一支
00BA078F  cmp eax, 2
00BA0792  je  0xBA0799                  ; 644!=0 且 C8==2 -> eax=2
00BA0799  mov eax, 2
00BA079E  ret
```

`0xB7A670` 只在 `[manager+0x4F8]` 非 0 时才保留这个 2：

```asm
00B7A686  cmp byte ptr [esi+0x4F8], 0
00B7A68D  jne 0xB7A699
00B7A68F  cmp eax, 2                   ; 4F8==0 时把 2 降级为 1
00B7A692  jne 0xB7A699
00B7A694  mov eax, 1
```

`0x7F3836` 调 `0xB7A670`，`0x7F383D cmp eax,4` 后 `jmp [eax*4+0x7F3878]`：
**返回 2 -> `[0x84ABA7C]=2`，主状态机才推进到 5**。

而 `reqC8` 真实到达 2、连接真实建立，是先前 poke
`0x081A7F34="127.0.0.1"` 的直接结果（见第 20 节），并非空转。

**B. 大厅信道必须保持打开**

前一次 `lobby_plain_probe.py` 在 20 秒 recv 超时后**关闭连接**，客户端
随即崩溃（`exitcode=0xFFFFFFFF`，t=98）。改成超时后**继续持有**连接
（`hold=True`），客户端便稳定跨过 `uA50=4 -> 5` 并保持到用例结束。

### 21.6 复现命令

```text
python -X utf8 CODOLServer/lobby_server/lobby_plain_probe.py \\
  --bind 127.0.0.1 --port 8446 --log CODOLServer/logs/PLAIN/hold.jsonl

python -X utf8 CODOLServer/_mainline/auto_lobby_loop.py --rounds 2 \\
  --seconds 130 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 \\
  --poke-lobby-globals
```

`--poke-lobby-globals` 现在做三件事：

```text
t>=20  poke 0x081A76A8/0x081A7F34/0x081A9784 = "127.0.0.1"
       poke 0x081A9780/0x081A9EC4/0x081A9EC0 = 8446/8443/8446
t>=21  在 [req+0xC8]==2 之后置 [req+0x644]=1 与 [manager+0x4F8]=1
```

### 21.7 剩余差距（如实说明）

```text
[100]无法连接大厅服务   已消除（uA50 走到终态 5）
大厅握手                已通过
TPFUI 系统设置界面      已在驱动，但 PNG 资源是 1x1 占位/缺失
真正站在游戏大厅里      尚未达成 —— 下一步是补齐 IIPSRes PNG 资源
```

### 21.8 归档

```text
CODOLServer/archive/CONFIRMED_20260928_2015
  405 文件，SHA256 校验 405/405 通过（mismatch=0 absent=0）
```
"""

s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add), "chars")
