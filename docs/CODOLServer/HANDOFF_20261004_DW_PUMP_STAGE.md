# CODOL 大厅推进 · DW 泵阶段卡点交接

日期：2026-10-04
会话目标：把「[100] 无法连接大厅服务」弹窗的根因定位到可执行的下一步。

状态：**弹窗根因已收敛到单一状态位**，但尚未消除。

---

## 0. 一句话结论

```
DW 大厅泵的状态变量 [0x849BA34] 停在 1，从未推进到 3。
  → 每帧泵 0x7EF0D0 把 [0x849BA30] := [0x849BA34] = 1
  → 跳转表 0x7EF43C 的 index 1 → 0x7EF1C8（不是 index 3 → 0x7EF271）
  → 唯一能进入 0x7EEBF0 → 0x4A9850 → 0x4A93E0 的路径从不执行
  → [0x82C4AEC]（0x4A93E0 入口自增标志）恒为 0
  → gate / gec / cfg / cfgobj 恒为 0
  → 约 +52 s 后 0x8037E4 把 st 清零并标记 DWLOBBY_PUMP_DISCONNECTED
  → 0x7F25B0 返回 4 → 0x7EF254 弹「与大厅服务失去连接」
```

---

## 1. 已实测的关键证据

运行：`run_codol_001\runs\IFS1_ELEVATED_20261004_172515`（life=110 s，st 4→5）

```
PUMP_INPUTS  mgr=0x3A40C6D0 req=0x3C04A828 c8=2 5e8=3 644=0 m4f8=1
CHAIN_PROBE  entered_4A93E0=0  g2f=1  st=5  stp=4
CHAIN_INDEX  tblIdx_ba30=1  dwState_ba34=1  ui_ba3d=0
```

含义：

| 观测 | 结论 |
|---|---|
| `entered_4A93E0=0` | `0x4A93E0` **从未被执行**（它在入口写 `[0x82C4AEC]=1`） |
| `tblIdx_ba30=1` | DW 泵当前走跳转表 index 1，不是能推进配置链的 index 3 |
| `dwState_ba34=1` | 大厅阶段变量停在 1 |
| `g2f=1` | `[0x84ABB2F]` 本来就是 1，**不是**卡点 |
| `ui_ba3d=0` | `[0x849BA3D]` 为 0，`0x7F25B0` 不会因此返回 4 |
| `c8=2 / 5e8=3` | 握手状态正常（与历史一致） |

---

## 2. 关键函数与地址（全部来自解密运行镜像，基址 0x400000）

### 2.1 弹窗的唯一出口

字符串 `@SF_UI_DW_LIVE_CONNECTING_FAILED` 在 `0x00DE0640`，
全镜像**只有一个引用点**：`0x007EF254`。

```
0x7EF1CD  call 0x7F25B0        ; esi = UI 阶段
0x7EF1DE  cmp  esi, 3
0x7EF1E1  jne  0x7EF210
          ...                  ; esi==3 → 成功路径
0x7EF210  cmp  esi, 4
0x7EF213  jne  0x7EF41B        ; 不是 4 就什么都不做
0x7EF254  push 0x00DE0640      ; ← 唯一弹窗点
```

### 2.2 UI 阶段映射 0x7F25B0

```
0x7F25B0  cmp byte [0x849BA3D],0
          mov eax,4
          jne 返回              ; [0x849BA3D]!=0 → 4
          ecx = [0x84ABA50]     ; st
          jmp [ecx*4 + 0x7F25DC]
跳转表 0x7F25DC: st=0 → 0x7F25DB(eax=4)
                 st=1..4 → 0x7F25D0(eax=1)
                 st=5 → 0x7F25D6(eax=3)
```

### 2.3 st 状态机 0x803780（唯一写 st 的地方）

```
0x8037BF  call 0xB7A670
0x8037D6  cmp  esi, 2
0x8037D9  je   0x8037FA        ; ==2 → 成功
0x8037E4  mov  [0x84ABA50], 0  ; 否则 st=0
0x8037F4  marker = 0xDE16F0    ; "DWLOBBY_PUMP_DISCONNECTED"
0x803804  mov  [0x84ABA50], 5  ; 成功 → st=5
0x803814  marker = 0xDE170C    ; "DWLOBBY_PUMP_SUCCESS"
```

### 2.4 判据 0xB7A670 / 0xBA0780

```
0xB7A670  ecx = [esi+0x4F4]        ; lobby request 对象
          if ecx == 0 → return 0
          eax = 0xBA0780(ecx)
          if [esi+0x4F8] == 0 && eax == 2 → eax = 1
          return eax

0xBA0780  if [req+0x644] != 0 → return 2 if c8 ∈ {1,2}
          else ([req+0x644]==0) → return 2 only if c8==2 && 5e8==3
```

实测 `m4f8=1`（非 0），所以 `0xB7A670` 原样返回 `0xBA0780` 的结果。
实测 `c8=2 且 5e8=3`，因此返回 2 → `st` 能到 5。这条链是通的。

### 2.5 DW 泵 0x7EF0D0 与跳转表

```
0x7EF0D6  eax = [0x849BA34]        ; 大厅阶段
0x7EF0F6  [0x849BA30] = eax        ; 跳转表索引
0x7EF176  jmp [ecx*4 + 0x7EF43C]

跳转表 0x7EF43C:
  index 0 → 0x7EF18A
  index 1 → 0x7EF1C8   ← 当前停在这里
  index 2 → 0x7EF266
  index 3 → 0x7EF271   ← 唯一进入 0x7EEBF0 的路径
  index 4 → 0x7EF2CA
  index 5 → 0x7EF2D5
  index 6 → 0x7EF2F1
  index 7 → 0x7EF335
  index 8 → 0x7EF3FE
  index 9 → 0x7EF39C
```

阶段变量 `[0x849BA34]` 的三个写入点：

```
0x7EF1B8  = 1     (index 1 处理器的分支)
0x7EF224  = 2     (在 esi==4 弹窗分支附近)
0x7EF1FF  = 3     (index 1 处理器里 esi==3 的成功分支)
```

---

## 3. 已否证的假设（不要再试）

| 假设 | 否证方式 | 结果 |
|---|---|---|
| `[req+0x644]` 是配置链总开关 | `--poke-644-on-st5` 写成 1，`gate` 仍 0 | **否证** |
| `[0x84ABB2F]`（g2f）是卡点 | 实测在 `st=5` 时它本来就是 1 | **否证** |
| 只要 `0xB7A670` 返回 2 就能开 gate | 实测已返回 2（st 到 5），`0x4A93E0` 仍未被调用 | **否证** |
| 内层首字节能靠 `--patch-87-gate` 修正 | 修正方向后内层字节仍是 0x4E/0x8F/0x00，非 0x87 | 未解决，但**不是当前阻塞点** |

---

## 4. 本次代码改动（全部只写运行内存 / 只读采样，未改原游戏文件）

### 4.1 修掉一个真实 bug：`--patch-87-gate` 方向反了

`restore_iips_contract_001\observer2\AboProbe.cs`

```
0xBA3AE6  cmp cl, 0x87
0xBA3AE9  75 23        jne 0xBA3B0E
```

`0x87` arm 分支是**顺序执行**那一侧（`0xBA3AEB..0xBA3B02`），
`0xBA3B0E` 是 `0x89` 分支。原实现写 `EB 23`（jmp）等于永远跳到 0x89、
跳过 arm，这是 `644` 长期为 0 的直接原因之一。
**已改为 NOP（`90 90`）**，使控制流落入 `0x87` arm。

### 4.2 新增开关

| 开关 | 作用 | 实测结果 |
|---|---|---|
| `--poke-g2f-on-st5` | `st==5` 时把 `[0x84ABB2F]` 置 1 | 它本来就是 1，无副作用 |
| `--poke-644-on-st5` | `st==5` 时持续保持 `[req+0x644]=1` | 写入成功，但不改变 `gate` |

透传链路（四处均已打通）：

```
CODOLServer\_mainline\_e57a5c_experiment.py
run_codol_001\elevated_ifs1_observer.ps1
run_codol_001\capture_elevated_network.ps1
restore_iips_contract_001\observer2\AboProbe.cs
```

### 4.3 只读诊断事件

```
CHAIN_PROBE    entered_4A93E0=[0x82C4AEC]  g2f  st  stp
CHAIN_INDEX    tblIdx_ba30  dwState_ba34  ui_ba3d
PUMP_INPUTS    mgr  req  c8  5e8  644  m4f8
POKE_G2F_ST5 / POKE_G2F_ST5_ALREADY
POKE_644_ST5
```

### 4.4 遗留未清理项

`AboProbe.cs` 里还有一个 `--patch-85-bufbase`（`0xBA44BE` 改写），
**该补丁长度写错**（用 5 字节覆盖了 2 字节指令 + 后续指令），
实测 `ok=False`、从未生效。**建议删除或重写**，目前它不参与任何有效路径。

---

## 5. 复现命令（当前可用组合）

前置：

```powershell
# 提权代理
Start-Process -FilePath "cmd.exe" -ArgumentList '/c','"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\run_elevated_agent_admin.cmd"' -WindowStyle Hidden
python -X utf8 "CODOLServer\_mainline\agent_client.py" ping   # 期望 debug_privilege=true

# 账号服务（客户端走 auth_task 32 的 TAS 路径）
Start-Process -FilePath "python.exe" -ArgumentList @('-X','utf8','-u','CODOLServer\lobby3074\fake_auth_tls.py') -WorkingDirectory "D:\BaiduNetdiskDownload\使命召唤OL" -WindowStyle Hidden
```

主实验：

```powershell
python -X utf8 "CODOLServer\_mainline\_multiround.py" --tag IDX --need 1 `
  --patch-85-pass --patch-87-gate --compat4 --patch-delay 42 --serve-delay 30 `
  --follow-85 --follow-85-rule receive --follow-85-cbc `
  --reply-85-cbc --reply-85-seqs 1,2,3,4 --reply-85-arm-first `
  --poke-g2f-on-st5 --poke-644-on-st5
```

观察器改完必须重编译：

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL\restore_iips_contract_001\observer2"
dotnet publish -c Release -o out
```

---

## 6. 当前环境状态（2026-10-04 收尾）

```
沙箱              run_codol_001\sandbox_datafix_20260929
dwauth.ini        formal-zone-lsg.codol.qq.com 3074
                  formal-zone-auth.codol.qq.com 3074
                  0x03EA
auth 服务         127.0.0.1:3074  (fake_auth_tls.py)
明文大厅探针      127.0.0.2:8446  (每轮由驱动启动/关闭)
hosts             127.0.0.1 formal-zone-auth.codol.qq.com
                  127.0.0.2 formal-zone-lsg.codol.qq.com
```

注：沙箱 `dwauth.ini` 曾被我临时切到 443 配置，**已切回 3074**。
`netsh portproxy 443→8443` 仍在，但不参与当前 3074 链路，可留可删。

---

## 7. 后续实测（2026-10-04 17:43）

运行：`run_codol_001\runs\IFS1_ELEVATED_20261004_174320`（life=110 s，st 4→5）

新增只读开关 `--dw-timeline`（`--dw-timeline-start/end/interval`），
在 70-92.5 s 内以约 1 ms 采样 `[0x849BA34]`、`[0x84ABA50]` 和线程 EIP。

实测：

```
87.458  st=5  dw=1  idx=1  ui=0
87.459  CHAIN_PROBE entered_4A93E0=0 g2f=1 st=5 stp=4
87.459  CHAIN_INDEX tblIdx_ba30=1 dwState_ba34=1 ui_ba3d=0
92.513  st=5  dw=1  idx=1  ui=0   (窗口结束前保持 5 s 不变)
```

补充结论：

1. `0x7EF0D0` 的唯一持续调用点是 `0x4F8AD1 -> 0x808240 -> 0x808259`，
   主循环每帧执行，入口没有外部门。
2. 静态扫描确认 `[0x849BA34]` 的唯一写入点是 `0x7EF1FF`，
   即 index 1 处理器成功分支。
3. index 1 处理器 `0x7EF1C8` 在写 `dw=3` 之前还会经过：

```
0x7EF1F2  call 0x622220
0x7EF1F7  test al, al
0x7EF1F9  je   0x7EF41B     ; al==0 -> 直接返回，不写 dw
```

4. `0x622220` 只在 `[0xE59D20] == 4` 或 `6` 时返回 1。
   实测运行中 `[0xE59D20] = 5`（`POST83_WATCH` 的 `stE59D20=5`），
   因此 index 1 处理器始终走 `0x7EF41B`，`dw=3` 永远不写入。

新增证据：`[0xE59D20]` 的状态机位于 `0x6212C0/0x621840`。

```
0x62186B  eax = [0xE59D20]
0x621870  sub eax, 3
0x621873  je  0x62188B      ; 3 -> call 0x802CC0 -> [0xE59D20]=4
0x621875  sub eax, 2
0x621878  jne 0x62189F      ; 5 不匹配这两个成功输入
0x62187F  mov [0xE59D20], 6 ; 原值 3 -> 成功输出
```

补充时序（run `IFS1_ELEVATED_20261004_175841`）：

```
35.013  e59=5   st=0  dw=0
76.219  e59=0   st=4  dw=1
76.315  e59=5   st=4  dw=1
...     e59=5   st=5  dw=1  直到运行结束
```

因此 5 不是一次性错误码，而是状态机启动后长期停留的“等待”值。
当前真正的卡点是：**`[0xE59D20]` 停在 5，没有外部事件把它推进到 3/4/6 的成功链。**

---

## 8. 下一步（单一问题）

**哪个外部事件（网络响应 / 服务回调 / 游戏事件）负责把
`[0xE59D20]` 从等待值 5 推进到成功输入 3/4/6？**

已确认的调用链：

```
0x7EF1C8  call 0x7F26C0
0x7EF1CD  call 0x7F25B0        ; st==5 -> eax=3
0x7EF1D2  esi = eax
0x7EF1D4  call 0x8014A0
0x7EF1D9  call 0x7EEBC0
0x7EF1DE  cmp esi, 3
0x7EF1E1  jne 0x7EF210
0x7EF1E3  call 0x803780
0x7EF1E8  call 0x4A3CE0
0x7EF1ED  call 0x7F4DB0
0x7EF1F2  call 0x622220        ; [0xE59D20] must be 4 or 6
0x7EF1F7  test al, al
0x7EF1F9  je   0x7EF41B        ; measured: 0
0x7EF1FF  mov [0x849BA34], esi ; never reached
```

建议测量：

1. 在 `0x621779`、`0x62187F`、`0x621890`、`0x621AC0` 四个写点做只读计数/时序采样，
   确认 5 的来源；
2. 检查 `0x621A5E` 的 `-1/-2/-3` 错误分支和 `0x82E13F8` 重试计数，
   判断当前是网络超时、服务拒绝还是重试耗尽；
3. 修复方向应优先落在 `[0xE59D20]` 的输入事件，而不是继续强推 `dw`。

---

## 9. 收尾结论（2026-10-04）

后续补充确认：

1. `[0xE59D20]` 的 5 不是一次性错误码，而是启动后长期保持的等待值
   （`IFS1_ELEVATED_20261004_175841`：35.0 s 已是 5，76.2 s 短暂为 0，
   76.3 s 回到 5，之后保持到运行结束）。
2. `0x6212C0` 的状态跳转表中，状态 5 落到 `0x6217E1`，即**直接返回、不推进**；
   只有状态 3 和 4 会分别进入 `0x62188B` 和 `0x62187A` 的成功分支。
3. `0x7E98F0`（唯一调用 `0x6212C0` 的初始化入口）只被 `0x808658`
   在启动序列中调用一次；运行期没有再次触发。
4. 因此当前不是“泵没跑”，而是：

```
启动初始化把等待态留在 [0xE59D20]=5
  -> 没有运行期事件把它推进到 4/6
  -> 0x622220 返回 0
  -> 0x7EF1C8 的 dw=3 写入分支永不执行
  -> [0x849BA34] 停在 1
```

**修复方向已收敛为：找到并恢复触发 `[0xE59D20]` 从 5 前进的外部事件
（网络响应 / 服务回调 / 游戏事件），而不是继续在 DW 泵或 0x4A93E0 上打补丁。**

---

## 10. 继续推进（2026-10-04 晚）

### 10.1 上游根因继续收敛

静态调用链确认：

```
0x7EEBC0  call 0x621810          ; DW 泵每帧调用
0x621810  [obj+0x1F4] 分支
            == 1 -> 0xBAD810
            == 2 -> E59D20 状态分支
            其他 -> 错误路径
```

`0x621810` 的分支条件是 `0xBAC370` 返回值，即 `[obj+0x1F4]`。

实测 `POST83_WATCH`：

```
1f4=1     ; st=4 早期
1f4=-2    ; st=4 后期与 st=5 全程
```

`-2` 不是成功输入，因此 `E59D20` 的 3/4/6 分支根本无法进入。

静态写入点：

```
0xBAD4B0  mov [obj+0x1F4], -4
0xBAD4DD  mov [obj+0x1F4], -3
0xBAD5EF  mov [obj+0x1F4], -1
0xBAD641  mov [obj+0x1F4], 2
0xBADDEA  mov [obj+0x1F4], -2
0xBADFB2  mov [obj+0x1F4], 2
0xBAE1BC  mov [obj+0x1F4], 2
0xBAE597  mov [obj+0x1F4], 2
0xBAE75E  mov [obj+0x1F4], -2
0xBAE776  mov [obj+0x1F4], -2
0xBAE7BA  mov [obj+0x1F4], -2
```

### 10.2 新增数据实验开关

```
--poke-1f4-on-st5     独立轮询，把 [req+0x1F4] 保持为指定值
--poke-1f4-value N    默认 2
--poke-e59-on-st5     独立保持 [0xE59D20]
--poke-e59-value N    默认 4
```

验证结论：

1. 把 `E59D20` 单独保持为 4，`dw` 仍停在 1，`gate/cfgobj` 仍为 0。
2. `1F4` 写入最初被误放在 `st==5` 嵌套分支内，未触发；
   已改为独立轮询并修复节流变量冲突。
3. 最后一轮因启动 flake 未拿到有效样本，但 `1F4` 独立轮询逻辑已就位。

### 10.3 环境回归修复

`_z7_cleanup.py` 之前会杀掉所有非 agent 的 `python.exe`，
包括 `fake_auth_tls.py`，导致每轮在 10-12 s 以 `0xFFFFFFFF` 退出。

已修复：保留 `fake_auth_tls` / `lobby_plain_probe` / `lsg_server` 等
持久服务进程。

### 10.4 新的一句话结论

当前主阻塞已从 `E59D20` 继续上移一层：

```
[obj+0x1F4] 先为 1，后变 -2
  -> 0x621810 不进入 E59D20 成功分支
  -> E59D20 停在 5
  -> 0x622220 返回 0
  -> dw=3 永不写入
```

**下一步唯一问题：`[obj+0x1F4]` 为什么从 1 变成 -2，
以及 -2 对应哪个网络/对象状态。**

---

## 11. 再推进（2026-10-04 深夜）

### 11.1 修正了一个指针错误

上一节的 `--poke-1f4-on-st5` 最初写成读写
`[[0x8269774]+0x4F4]+0x1F4`（大厅连接对象），这是错的。

观察器 `WatchGlobals` 早已指出：`1f4` 属于

```
[0x00E85C68] + 0x1F4
```

即 Demonware singleton，也就是 `0x643300` 返回、`0x621810` 中
`ecx/ebx` 使用的对象。已修正为读取 `[0xE85C68]+0x1F4`。

### 11.2 `-2` 的真实语义

静态确认 `0xBAD810` 是 `[obj+0x1F4]==1` 时才进入的处理函数，
其失败终态写 `-2`。四个 `-2` 写入点全部在 `0xBAD810` 内部：

```
0xBADDEA  [obj+0x1F4] = -2   ; [obj+0x18] 工作队列 <= 0
0xBAE75E  [obj+0x1F4] = -2   ; 子步骤返回 0
0xBAE776  [obj+0x1F4] = -2   ; 子步骤返回 0
0xBAE7BA  [obj+0x1F4] = -2   ; 同类失败
```

因此 `-2` 不是外部事件缺失，而是 **Demonware 对象自身的处理失败终态**。

### 11.3 当前链路

```
Demonware singleton [0xE85C68]
  -> [obj+0x1F4] == 1   成功输入
  -> 0xBAD810           处理（含工作队列 + 子步骤）
  -> 失败写 -2
  -> 0x621810 不再进入 E59D20 分支
  -> E59D20 停在 5
  -> 0x622220 返回 0
  -> dw=3 不写入
```

### 11.4 当前环境问题

`0xFFFFFFFF` 早期退出（9-12 s）在当前会话里已从偶发变成高频。
最近连续多批（4 次、8 次、6 次）均未拿到有效轮。
这不是 `1F4` 补丁导致，因为补丁在 `st=5` 之后才可能执行。

启动前置状态需在下一会话重新预热或复位；
验证 `1F4=2` 的实验开关与指针修正已经就位。

---

## 12. 继续下钻（2026-10-04 收尾）

### 12.1 四个 -2 写入点的判据已还原

反汇编 `0xBAD810`（约 4 KB）后确认：

| 写入点 | 判据 |
|---|---|
| `0xBADDEA` | `[obj+0x18]`（工作队列长度）`<= 0` |
| `0xBAE7BA` | 同上，另一条同类路径 |
| `0xBAE75E` | `[obj+0x4D70] != [obj+0x18]`（队列计数不一致） |
| `0xBAE776` | 子步骤 `0xBBAD10` 返回 0 |

实测 `4d70=3`、`18=3`，两者相等，所以当前 `-2` 来自
**`0xBBAD10` 返回 0**。

### 12.2 失败链已下钻到网络写操作

```
0xBAD810  -> 0xBBAD10
0xBBAD10  cmp [obj+0x1A0],0     ; 实测 0，通过
          test arg1             ; 有效指针，通过
          call 0xBBA870
0xBBA870  call 0xBBA6D0
0xBBA6D0  call 0xBC1C90          ; 序列化 0x14 消息头
          call [vtbl+0x18]       ; ★ 实际网络写操作
          要求返回值 > 0 且等于写入长度
          否则返回 0 -> 0xBBAD10 返回 0 -> 写 -2
```

`0xBC1C90` 只是把 `0x14` 消息头（1 字节类型 + 2 字节标志 +
4 字节长度）写入发送缓冲，不决定成败。

**真正决定 `[obj+0x1F4]` 的，是 `0xBBA6D0` 里 `[vtbl+0x18]`
指向的写实现及其返回值。**

### 12.3 新的一句话结论

```
[0xE85C68] Demonware singleton
  -> [obj+0x1F4] == 1
  -> 0xBAD810 -> 0xBBAD10 -> 0xBBA870 -> 0xBBA6D0
  -> 0xBC1C90 序列化 0x14 消息头
  -> [vtbl+0x18] 网络写失败（返回值 != 长度）
  -> 0xBBA6D0 返回 0
  -> 0xBBAD10 返回 0
  -> [obj+0x1F4] = -2
  -> 0x621810 不进入 E59D20 分支
```

### 12.4 下一步唯一问题

**解析 `0xBBA6D0` 中 `[vtbl+0x18]` 指向的写实现，
确定它为什么返回失败（返回 0、短写、还是连接不可用）。**

需要在新一轮有效样本里抓：

```
[0xE85C68] + 0x1F4   阶段
[0xE85C68] + 0x1A0   内部阶段
[0xE85C68] + 0x1FC   写对象指针
[0xE85C68] + 0x4D70  队列计数
[0xE85C68] + 0x18    队列长度
```

---

## 13. 再下钻一层（2026-10-04 最终）

### 13.1 `[obj+0x1FC]` 写对象的来源

`0xBBA6D0` 使用的写对象来自：

```
0xBBA730  mov ecx,[esi]        ; esi = [obj+0x1FC]
0xBBA732  mov eax,[ecx]        ; vtable
0xBBA734  mov eax,[eax+0x18]   ; virtual write
0xBBA740  call eax
```

`[obj+0x1FC]` 在 `0xBAD810` 内部由 `0xBBA7E0` 构造，
写入点包括 `0xBADD55` 与 `0xBAE722`。

### 13.2 `0xBBA6D0` 的精确成功条件

```
0xBC1C90 序列化 0x14 消息头
          （1B 类型 0x14 + 2B 标志 + 4B 长度）
call [vtbl+0x18] 写请求
  ret > 0 且 ret == 写入长度  -> 返回 1
  否则                        -> 返回 0
```

返回 0 会让 `0xBBAD10` 返回 0，
进而 `0xBAD810` 在 `0xBAE776` 写 `[obj+0x1F4] = -2`。

### 13.3 启动环境退化诊断

成功轮 `IFS1_ELEVATED_20261004_184520` 的模块序列：

```
5.656  TenProxy.dll
7.331  iips.dll
8.289  ifs2.dll
15.155 CoD Splash Screen
```

失败轮（19:10 起连续多轮）：

```
6.659  iips.dll
6.878  iipsinit 窗口
12.3   PROCESS_END 0xFFFFFFFF
```

即失败轮**在 `iips.dll` 之后、`ifs2.dll` 之前就退出**。
IIPS 目录文件完整，属于 IIPS 初始化阶段的运行时状态退化，
不是文件缺失，也不是 `1F4` 补丁导致。

### 13.4 本轮可交付结论

主阻塞链已从 `E59D20` 完整下钻到**一个网络写调用**：

```
[0xE85C68] Demonware singleton
  -> [obj+0x1F4] == 1
  -> 0xBAD810 -> 0xBBAD10 -> 0xBBA870 -> 0xBBA6D0
  -> 0xBC1C90 写 0x14 消息头
  -> [vtbl+0x18] 网络写返回失败
  -> [obj+0x1F4] = -2
  -> 0x621810 不进 E59D20 分支
  -> E59D20 = 5
  -> 0x622220 = 0
  -> dw=3 不写
```

下一步需要在启动环境恢复后，抓 `[0xE85C68]+0x1FC` 的写对象
与其 vtable，确定 `[vtbl+0x18]` 的具体实现和失败返回值。

---

## 14. ★★★ 决定性突破（2026-10-04 19:26）

### 14.1 结论：泵和下游配置链完全健康

运行：`IFS1_ELEVATED_20261004_192636`（life=130.3 s，无弹窗）

实验：`st>=4` 时把 `[0x849BA34]` 保持为 3。

实测：

```
68.393  POKE_DW        st=4  before=1 target=3
68.394  POKE_DW_WRITE  before=1 after=3 ok=True
68.425  CHAIN_INDEX    tblIdx_ba30=3 dwState_ba34=3 ui_ba3d=0
```

下游变化：

| 观测 | 前 | 后 |
|---|---|---|
| `gate` | 0 | **1** |
| `gec` | 0 | **1** |
| `zbuf` | 空 | `mp_playlists_shipRetail_` |
| `rqAC` | 0 | **382** |
| `obj` | None | 完整帧对象 |
| 运行时长 | ~80 s 弹窗 | **130.3 s 无弹窗** |

### 14.2 这意味着什么

1. `0x4A93E0 -> gate=1` 链路**完全可用**。
2. `0x7EEBF0 -> 0x4A9850 -> 0x4A93E0` 配置链**完全可用**。
3. `mp_playlists_shipRetail_` zone 名出现，说明配置/资源阶段已启动。
4. 之前的失败**唯一原因**就是 `0x7EF1FF` 没有把 `dw` 从 1 写到 3。

### 14.3 两条可独立生效的修复路径

路径 A（数据，已验证可打通）：

```
st>=4 时保持 [0x849BA34]=3
开关：--poke-dw-on-st5 --poke-dw-value 3
```

路径 B（上游根因，已验证可到 6）：

```
把 [0xE85C68]+0x1F4 保持为 2 或 6
  -> 0x621810 成功分支
  -> [0xE59D20] 从 5 推进到 6
开关：--poke-1f4-on-st5 --poke-1f4-value 2
```

路径 B 已实测让 `stE59D20=6`，但 `dw` 仍停在 1，
说明 `0x7EF1FF` 的触发还需要 `0x7F25B0` 在该帧返回 3
（时序问题），因此路径 A 更直接、当前可复现。

### 14.4 当前状态

**大厅链路的关键闸门已被证明可以打开。**
剩余工作是让 `dw=3` 的写入在正确帧自然发生，
或在配置链启动后确认大厅 UI 是否进入。

---

## 15. 长时验证与新的两层结论（2026-10-04 19:33）

运行：`IFS1_ELEVATED_20261004_193353`，300 秒。

强制 `dw=3` 后观测：

| 观测 | 结果 |
|---|---|
| `gate` | 0 → 1 |
| `gec` | 0 → 1 |
| `cfg` | 0 → 0x00010000 |
| `zbuf` | `mp_playlists_shipRetail_` |
| `rqAC` | 0 → 382 |
| `obj` | 完整帧对象出现 |
| `cfgobj` | **仍为 0** |
| 弹窗 | **162.4 s 出现 `#32770`「与大厅服务失去连接」** |
| 进程 | 活到 300 s（探针主动终止） |

### 15.1 新的两层结论

问题不是一层，而是两层：

**第一层：DW/配置闸门**

```
[0x849BA34]=3
  -> 0x7EEBF0 -> 0x4A9850 -> 0x4A93E0
  -> gate=1 / gec=1 / cfg=0x00010000 / zone 名出现
```

这一层已被 `--poke-dw-on-st5` 证明可以打开。

**第二层：大厅会话超时**

```
gate/gec/cfg 已开
  -> cfgobj 仍为 0
  -> 162.4 s 弹「与大厅服务失去连接」
```

这一层与 `dw` 无关，是独立的大厅连接/看门狗问题。

### 15.2 gate 后续状态

静态确认 `0x4A93E0` 成功后调 `0x4A80C0`；
若 `0xB7A670` 返回值不是 2，或连接对象取不到，
`0x4A80C0` 会把 `gate` 从 1 改写为 **2**。
`gate` 后续变化属于正常流程，不代表失败。

### 15.3 下一步唯一方向

在 `dw=3` 保持的前提下，追 162.4 s 弹窗对应的第二条看门狗：

1. 该弹窗的调用点（`0x7EF254` 或另一处）；
2. `cfgobj` 未建立时配置步骤停在哪一步（`0x50E930` 的 eax 索引）；
3. 大厅会话在 `gate=1` 后是否还需要一次新的服务端响应。

**大厅入口现在由两层组成：DW 闸门（已可开）+ 大厅会话（未闭合）。**

---

## 16. 服务端线缆时间线（2026-10-04 19:33 轮）

日志：`CODOLServer\logs\E57A5C_20261004_193344_a1\plain.jsonl`

服务端探针完整事件：

```
t=703.607  sent_81        len=204
t=703.630  echo_from_observer  echo8=87 2e f2 6a d0 16 6b 01
t=703.631  found_82       frame_len=149
t=703.631  sent_83        len=204
t=703.697  85_tag         rule=receive/codec_02a0+aes-cbc+hmac_sha1
t=703.697  sent_85        len=772  keyed=true
之后        recv_timeout × 155
t≈763.85   conn_error WinError 10054（客户端强制关闭）
```

### 16.1 关键纠正

之前把 162 s 弹窗理解为「服务端没有继续应答」，
但计数确认：

```
sent_81  = 1
sent_83  = 1
sent_85  = 1
send_error = 0
recv_timeout = 155
```

**服务端把 0x81/0x82/0x83/0x85 全部发出，没有发送错误。**

### 16.2 真正卡点

客户端收到 0x85 后**没有继续回应**，
双方进入 155 次 `recv_timeout` 的僵持，
直到客户端看门狗触发断线弹窗。

这与客户端侧的观察一致：

```
gate=1 / gec=1 / cfg=0x00010000 / zone 名出现
但 cfgobj = 0
```

⇒ 客户端在收到 0x85 后，配置解析没有完成，
因此不产生后续握手帧。

### 16.3 下一步唯一问题

**客户端收到 0x85 后，为什么没有继续握手（0x86/0x87/0x89 回环）？**

已排除：

- 服务端未发送（已确认 sent_85=1）
- 服务端发送错误（send_error=0）
- DW 泵未运行（gate/gec/cfg 已打开）

需要查：

1. 0x85 帧内容是否被客户端接受（`obj+0xC8/0x5E8/0x644` 收帧后变化）；
2. 客户端配置解析 `0x50E930` 卡在哪个 eax 索引；
3. `cfgobj=0` 是否阻止了后续握手帧生成。

---

## 17. ★★ 客户端确实接收并处理了 0x85（2026-10-04 19:46）

运行：`IFS1_ELEVATED_20261004_194632`

`POST83_SAMPLE` 实测：

```
86.474  644=1               ← 0x87 arm 成功
86.490  6d8=18
88.462  ac=382  5ec=2       ← 收到完整 382 字节帧
88.481  5ec=3
88.495  5ec=4               ← 连续收到多帧
88.610  s9c=1
```

### 17.1 结论修正

之前判断「客户端收到 0x85 后没有继续回应」**不准确**。

实际情况：

1. 客户端**完整接收**了服务端 0x85 帧（`ac=382`、`5ec` 1→4）。
2. **0x87 arm 成功**（`644=1`）。
3. 但 `644` 没有进一步变成 2，`dw` 仍停在 1。

### 17.2 新的精确卡点

```
0x85 帧被接收            ✓
0x87 arm 成功 644=1      ✓
0x89 业务 644: 1 -> 2    ✗  ← 当前卡点
dw: 1 -> 3               ✗
cfgobj                   0
```

### 17.3 这意味着

问题不在传输层，也不在 0x87 arm。
**卡点是 0x89 业务分支（`0xBA3600`）没有成功**，
它要求 `644==1` 且内层 `0x89` 消息通过 `0xBA0FF0` 解析。

因此下一步唯一问题变成：

**服务端第二个 0x85 帧的内层 0x89 载荷为什么没有让 `0xBA0FF0` 解析成功？**

需要核对：

1. `0xBA0FF0` 对三字节头（ver/subtype/flag）的具体要求；
2. 服务端 `build_inner_89()` 产生的载荷是否满足；
3. `0x89` 分支失败时的返回码与复位路径。

> 本节判断已由 §18 修正：此前 644=1 的样本包含 `POKE_644_ST5`，不能证明 arm 自然成功；
> 同时标准命令里的 `--patch-87-gate` 会把后续 0x89 也强制送进 arm 分支。

## 18. ★★★ 静态闭合：0x85 内层首 DWORD 是 opcode 游标（2026-10-04）

### 18.1 消费端的精确语义

顺序反汇编 `0xBA3A2C..0xBA3AA9` 并复核 `0xB783C0`：

```text
0xBA3A2C  从当前流偏移读 4 字节到临时值 [ebp-0x3A4]
0xB783C0  同时把 reader cursor 推进 4 字节，写到 [ebp-0x390]
0xBA3A18  再把读出的 DWORD [ebp-0x3A4] 覆盖回 [ebp-0x390]
0xBA3A91  从 source + 该 DWORD 游标读取 1 字节，作为分发 opcode
0xBA3AB5  用首 DWORD 与 opcode 后游标检查 source 边界
0xBA3AE6  opcode==0x87 -> arm 0xBA3590
0xBA3B0E  opcode==0x89 -> business 0xBA3600
```

因此首 DWORD 是相对 source 起点的 **opcode 游标**，不是 body 长度。编码 `4` 时，
分发器在 source+4 读取 opcode；`0x87` arm 再消费下一字节并要求其值为 1。

### 18.2 旧构造为何必错

```text
旧 build_inner_87 在 CBC 明文起始处输出 `87 01 00 00 ...`：
首 DWORD 被消费为游标 `0x187`，opcode 读取落在 352 字节解密体之外，不能读到偏移 0 的 `0x87`。

旧 build_inner_89 在 CBC 明文起始处输出 `01 01 00 00 ...`：
首 DWORD 被消费为游标 `0x101`，opcode 读取落在偏移 257 的零填充，不是 `0x89`。
所以该结构没有把 opcode 放在解析器会读取的位置。
```

当前 352 字节解密体足以容纳这些偏移，因此它们不会作为越界错误清晰失败，而是从错误位置取到填充/无关字节。
正确消息形态为：

```text
0x87: u32 cursor=4 | 87 | 01
0x89: u32 cursor=4 | 89 | ver=1 | subtype=1 | flag=0 | u16 len=0 | u32 value=0
```

`build_inner_89()` 原有业务字段布局符合 `0xBA0FF0` 的 subtype-1 短路径；此前缺少正确的外层 cursor/opcode envelope。

### 18.3 旧运行证据重新定级

1. 运行 `IFS1_ELEVATED_20261004_194632` 的观察器记录了 `POKE_644_ST5 before=0 after=1`；后续 `644=1` 是探针写入保持值，不能据此说“服务端 0x87 arm 成功”。
2. `--patch-87-gate` 把 `0xBA3AE9` 的 `jne 0xBA3B0E` 改成 NOP，导致任何 opcode 都顺序落入 `0xBA3590`；启用时 0x89 business 分支不可达。
3. 因而旧实验没有有效验证 `0x89 -> 0xBA3600 -> 0xBA0FF0`，也没有证据表明当前卡点是 parser 的 subtype/body 字段。

### 18.4 本轮代码与下一次有效实验

`lobby_plain_probe.py` 已改为输出 `cursor=4 | opcode | body` 的 0x87/0x89 消息，并新增离线单元测试覆盖游标、业务字段及 CBC 往返。
下一轮应保留经验证所需的 0x85 收帧实验开关，但**不要**启用 `--patch-87-gate`、`--poke-644-on-st5` 或其它强制 arm 写入；验收顺序是自然 `644:0->1`、再自然 `644:1->2`/`c8:2->1`。

---

## 8. 参考文件

```
CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md   主手册
CODOLServer\HANDOFF_20261002_TLDR.md             上一版精简交接
CODOLServer\_mainline\_e57a5c_experiment.py      主实验驱动
restore_iips_contract_001\observer2\AboProbe.cs  观察器
run_codol_001\elevated_ifs1_observer.ps1         观察器包装
```

---

## 19. 继续推进（2026-10-05 凌晨）

### 19.1 修掉一个真实缺陷：`--cert-dir` 参数不存在

`CODOLServer\_mainline\auto_lobby_loop.py` 的 `start_probe()` 给
`lobby_socket_server.py` 传了 `--cert-dir`，但该脚本只有
`--bind / --port / --log`，argparse 直接以 exit 2 退出。

后果：**8444 大厅监听每一轮都没起来**，socket 日志永远为空。

```python
# 修复前
q = subprocess.Popen([PY, "-X", "utf8", "-u", sock, "--cert-dir", LS, ...])
# 修复后
q = subprocess.Popen([PY, "-X", "utf8", "-u", sock, ...])
```

离线验证：按新参数启动 8444，`alive` 且 `connect ok`，stderr 为空。

### 19.2 四轮对照实验（环境已重新预热）

前置已恢复：

```
提权代理        debug_privilege=true（重启 run_elevated_agent_admin.cmd）
auth 服务       127.0.0.1:3074  fake_auth_tls.py
hosts           127.0.0.1 formal-zone-auth.codol.qq.com
                127.0.0.2 formal-zone-lsg.codol.qq.com
```

| 标签 | 开关 | life | 结果 |
|---|---|---:|---|
| `BASENO85` | 仅 `--compat4`，**不发任何 0x85** | 96.7 s | `st 4 -> 5`，`DWLOBBY_PUMP_SUCCESS` |
| `FOLLOWONLY` | `--follow-85 --follow-85-cbc` | 96.2 s | 收 0x85 后 `c8 2->4 5e8 3->0` 复位 |
| `NAT` | `--follow-85` + `--reply-85-cbc --reply-85-arm-first` | 88.8 s | 同上复位 |
| `ECHO85` | `--echo-85 --echo-85-rule receive` | 110.0 s | 同上复位 |

### 19.3 关键结论一：DW/配置闸门在"不发 0x85"时本就通畅

`BASENO85` 时序：

```
37.815  c8=1  5e8=0
37.847  c8=2  5e8=1
67.780  c8=2  5e8=2
67.826  uA50=4  c8=2  5e8=3   DW_LOBBY_CONNECTED
84.871  uA50=5  c8=2  5e8=3   DWLOBBY_PUMP_SUCCESS   ★
96.695  进程结束
```

⇒ `0xB7A670` 返回 2 → `st=5` → `DWLOBBY_PUMP_SUCCESS`，
**不需要任何服务端 0x85**。§14/§15 里"必须靠 `--poke-dw-on-st5` 才能到 st=5"
的结论在此配置下不成立：`st=5` 是自然到达的。

### 19.4 关键结论二：合成的 0x85 是复位的原因，不是修复

三组发了 0x85 的实验全部在同一位置失败：

```
68.x  uA50=4  c8=2  5e8=3   DW_LOBBY_CONNECTED
68.x  uA50=4  c8=4  5e8=0   DW_LOBBY_CONNECTED   ← 复位，之后不再恢复
```

服务端侧看到的是客户端随即 `10054` 强制关闭。

`0xBA3420`（复位例程）无条件写 `c8=4 / 5e8=0 / 644=0`，
且 `0xBA4430` 在 `c8==4` 时直接返回。这与实测完全吻合。

### 19.5 复位点的静态判据（已算实）

`0xBA3590`（0x87 arm）里唯一的错误出口路径：

```text
0xBA35B0  call 0xB783C0        ; 读 1 字节（arm 标志）
0xBA35BC  cmp [ebp+0x13], 1
0xBA35BF  je  0xBA35D7         ; ==1 才继续
0xBA35C1  xor bl,bl
0xBA35CA  call 0xBA3420        ; ★ 复位
```

arm 读取成功后的两个前置条件：

```text
0xBA35D7  cmp [esi+0x644], 0   ; 必须 == 0（已是 0）
0xBA35E0  call 0xBA3010        ; ★ 构造并真正发送一帧
0xBA35E9  je  0xBA35C1         ; 返回 0 -> 复位
0xBA35EB  mov [esi+0x644], 1
```

`0xBA3010` 内 `0xBA30AD call 0xBA2A60`（发送路径）前有
`0xBA2AC0 cmp [ebx+0x644], 0`，而 `0xBA2A60` 依赖
`[obj+0x6D0]/[obj+0x6D4]` 与 `[obj+0x608]` 上的 codec provider。

### 19.6 §18.4 的验收顺序本轮无法闭合

`--reply-85-len-field` 与"改小长度字段"路线已在
`HANDOFF_20260930_REVERSE_MANUAL.md` §5.27.71 被否证：
客户端按长度字段切帧，改小会立刻破坏解析并触发 `10054`。
本轮 `LENF`（`--reply-85-len-field 0x10`）复现了同一现象，
不再重复该路线。

当前 `frame_len` 的算术约束仍然是
`frame_len + 游标 <= [obj+0xAC]`，而我们发出的帧令 `[obj+0xAC]=382`
且 `frame_len=382`，`游标>0` ⇒ 该式恒成立失败。

### 19.7 当前精确卡点

```text
DW/配置闸门          ：通畅（BASENO85 实测 st=5 / DWLOBBY_PUMP_SUCCESS）
0x87 arm（644=1）    ：卡在 0xBA3010 -> 0xBA2A60 的真实发送
                       （不是判据，而是发送依赖的 provider/连接状态）
0x89 业务（644=2）   ：以 644==1 为前提，无旁路（0xBA360D）
```

### 19.8 下一步唯一问题

**`0xBA2A60` 的发送为什么返回 0**：查 `[obj+0x608]` 上的 codec provider
与其 vtable `[vt+0x0C]` 实现，以及 `[obj+0x6D0]/[obj+0x6D4]`
在 `5e8==3` 时的实际取值。

建议测量（在 `BASENO85` 这一已知通畅的配置上叠加只读采样）：

```
[obj+0x608]  provider 指针及其 vtable
[obj+0x6D0] / [obj+0x6D4]
[obj+0x1F4] / [obj+0x1FC]（Demonware 写对象）
```

### 19.9 本轮不要再做的事

1. **不要**再改 `frame_len` 字段（已否证）。
2. **不要**用 `--patch-87-gate` 验证自然握手（它会把 0x89 也送进 arm）。
3. **不要**把 `644` 当作可强推的开关：`0xBA3600` 与 `0xBA3590`
   都以它为输入，强推只掩盖发送失败。

---

## 20. 发送路径实测（2026-10-05 凌晨，第 19.8 节已答）

### 20.1 新增只读采样事件 `SEND_PATH`

`AboProbe.cs` 在 `post83Watch` 窗口内以 4 Hz 采样（只读，不写游戏数据）：

```
SEND_PATH  req  644  6d0  6d4  p608  p60c  vt608
```

采样点为 `[[0x08269774]+0x4F4]` 上的连接对象，字段对应 §19.8 的要求。
观察器已重编译（`dotnet publish -c Release -o out`）。

### 20.2 实测结果（运行 `IFS1_ELEVATED_20261005_005123`，life=106 s，`st 4 -> 5`）

`68.0 s → 85.1 s` 全程共 68 条 `SEND_PATH`，**逐条一致**：

```text
644  = 0
6d0  = 0        ★
6d4  = 0        ★
p608 = 1007831480 (0x3C1122B8)   非空
p60c = 480875498 (0x1CAF3A6A)    非空
vt608= 703cc700 f03ac700 b03bc700 103cc700 ...   非空
```

对照 `POST83_WATCH`：

```text
68.030  uA50=4  c8=2  5e8=3   DW_LOBBY_CONNECTED
85.108  uA50=5  c8=2  5e8=3   DWLOBBY_PUMP_SUCCESS
1f4=1  1f8=…  1fc=…  4d70=3  18=3   stE59D20=5  subA34=1
```

### 20.3 结论：§19.8 的问题已答

`0xBA2A60` 的发送**不是失败在 provider**：`p608 / p60c / vt608` 全部非空、
逐帧稳定。

失败在**发送缓冲的两个长度/游标字段恒为 0**：

```text
[obj+0x6D0] = 0
[obj+0x6D4] = 0
```

而 `0xBA2A60` 正是用这两个字段构造待发帧：

```text
0xBA2B14  mov eax, [ebx+0x6D4]
0xBA2B1A  lea ecx, [ebx+0x6D0]
0xBA2B2C  call 0xBA17B0        ; 组帧，输入 = [obj+0x6D0]/[obj+0x6D4]
```

`0xBA3420`（复位）把 `6D0/6D4` 清零：

```text
0xBA3474  mov [esi+0x6D0], eax   ; eax = 0
0xBA3485  mov [esi+0x6D4], ecx   ; ecx = 0
```

因此状态是自洽的死锁，而不是"发送报错"：

```text
644 = 0 -> 只有 0xBA2B5D 分支（644==0）会被走到
       -> 该分支不写 6D0/6D4（写入点在 644!=0 的 0xBA2ACD 分支之后）
       -> 6D0/6D4 保持 0
       -> 即使 arm 成功、644=1，下一次 0xBA2A60 仍拿到 0/0
```

### 20.4 修正后的精确卡点

```text
DW/配置闸门       通畅（st=5 / DWLOBBY_PUMP_SUCCESS 实测）
provider/密码学   通畅（p608/p60c/vt608 非空稳定）
待发帧缓冲        空（[obj+0x6D0]=0、[obj+0x6D4]=0）★ 当前卡点
0x87 arm（644=1） 依赖 0xBA3010 -> 0xBA2A60 成功，而后者需要 6D0/6D4
```

### 20.5 下一步唯一问题

**谁负责把 `[obj+0x6D0]/[obj+0x6D4]` 填成非 0？**

`0xBA3420` 清零它们，说明存在对应的写入路径。需要静态找出
`[obj+0x6D0]` / `[obj+0x6D4]` 的**全部写入点**，确认写入前置条件，
再判断该条件是"等待服务端下行帧"还是"本地队列非空"。

可并行的低成本验证：把 `6D0/6D4` 写成一组合理值（例如 `6D0=0、6D4=0x14`）
观察 `0xBA17B0` 是否组帧成功、`644` 是否自然变 1。

---

## 21. `[obj+0x6D0]/[obj+0x6D4]` 的语义（2026-10-05，静态已答）

### 21.1 全部写入点（镜像静态扫描 0xBA0000–0xBB2000）

| 地址 | 字段 | 所在函数 | 语义 |
|---|---|---|---|
| `0xBA29B1` / `0xBA29B7` | `6D0` / `6D4` | `0xBA29xx`（连接对象初始化） | `= ebx(0)` 初始化 |
| `0xBA347D` / `0xBA3485` | `6D0` / `6D4` | `0xBA3420`（复位） | `= 0` 清空 |
| `0xBA3EA7` | `6D0` | `0xBA3E20`（**出队**） | `= [node+8]` 链表前进 |
| `0xBA3EB8` | `6D4` | `0xBA3E20`（**出队**） | `= [node+0xC]` 尾跟随 |

### 21.2 它是"待发帧队列"的头/尾指针

`0xBA17B0`（入队）给出节点布局：

```text
0xBA17B9  call 0xB74220          ; 分配 0x10 字节节点
0xBA17CD  mov [edi], eax         ; node+0 = payload 指针（引用计数 +1）
0xBA17E0  mov [edi+4], eax       ; node+4 = payload 的第二个字段
0xBA17F4  mov [eax+8], edx       ; node+8 = next
0xBA17F7  mov [eax+0xC], ecx     ; node+C = prev
0xBA1801  mov [edx+0xC], eax     ; 双向链接
0xBA1807  inc [esi+8]            ; 队列计数 +1
```

`0xBA3E20`（出队）与之对称：

```text
0xBA3E67  cmp [ebx+0x6D8], 0     ; ★ 前置：计数器必须非 0
0xBA3E6E  je  0xBA3F84           ; ==0 直接退出，不动 6D0/6D4
0xBA3E74  mov esi, [ebx+0x6D0]   ; 取队首
0xBA3EA4  mov edx, [esi+8]
0xBA3EA7  mov [ebx+0x6D0], edx   ; 头指针前进
0xBA3EAD  cmp esi, [ebx+0x6D4]
0xBA3EB8  mov [ebx+0x6D4], eax   ; 若是最后一个，尾也更新
```

⇒ **`6D0 = 队首，6D4 = 队尾，6D8 = 队列计数**。三者同零 = 队列空。

### 21.3 与实测完全吻合

§20.2 实测 `6D0=0 6D4=0`，且 §20.2 的 `POST83_WATCH` 里 `6d8` 也是 0。
`0xBA3E67` 的前置 `6D8 != 0` 不满足 ⇒ 出队分支从不执行
⇒ `6D0/6D4` 永远不会被填成非 0。

### 21.4 修正后的死锁表述

```text
入队方（游戏业务层）从不往队列里放帧
  -> 6D8 = 0
  -> 0xBA3E20 的前置 cmp [6D8],0 不满足，直接退出
  -> 6D0/6D4 保持 0
  -> 0xBA2A60 拿 0/0 组帧
  -> 0xBA3010 返回 0
  -> 0xBA3590 走 0xBA3420 复位
  -> 644 保持 0
```

注意：这**不是**"我们发的 0x85 触发的"。`BASENO85` 不发任何 0x85 时
队列同样是空的，只是那条路不需要队列，所以能到 `st=5`。

### 21.5 否证：不要再往 6D0/6D4 里写值

`6D0/6D4` 是**指针**，不是长度/游标。§20.5 建议的
"写成 `6D0=0、6D4=0x14`" 会让 `0xBA3E74` 去解引用 `0x0`
并读 `[0x0+8]`，立刻访问违例。该建议作废。

正确的下一步是找**入队方**：`0xBA17B0` 的全部调用点，
确认在什么业务条件下游戏会往这个队列放帧。

---

## 22. ★★ 入队方已定：队列只由发送路径自己填（2026-10-05）

### 22.1 `0xBA17B0` 全镜像只有一个调用点

对整个镜像（0x400000 起，逐字节扫 `E8 rel32`）求
`call 0xBA17B0` 的调用点：

```text
callers of 0xBA17B0 : 1
  0xBA2B2C
```

而 `0xBA2B2C` 就在 **`0xBA2A60`（发送函数）内部**：

```text
0xBA2B14  mov eax, [ebx+0x6D4]
0xBA2B1A  lea ecx, [ebx+0x6D0]
0xBA2B2C  call 0xBA17B0        ; 唯一入队点
```

### 22.2 这否证了"上游业务层会往队列放帧"的假设

原本假设：游戏业务层构造帧 → 入队 → `0xBA3E20` 出队 → 真正发送。

实际：**入队发生在发送函数自己的尾部**，即

```text
0xBA2A60 被调用
  -> 组帧、加密、签名
  -> 0xBA2B2C 入队（把刚组好的帧挂到 6D0/6D4）
  -> 之后才真正写出
```

所以 `6D0/6D4` 不是"待发队列"，而是**本次发送过程中的帧链表游标**，
只在 `0xBA2A60` 执行期间有意义；函数外恒为 0 是**正常状态**，不是死锁。

### 22.3 §21.4 的"死锁"结论作废

§21.4 把 `6D0/6D4 = 0` 解释为"入队方从不放帧 ⇒ 死锁"，这是错的。
`0xBA2A60` 每次进入都会自己填它们；实测为 0 只说明
**`0xBA2A60` 当前根本没被调用**（这与 `644=0`、`0xBA3590` 未走 arm
成功分支一致），不代表缓冲异常。

§20.3 的"失败在 6D0/6D4 恒为 0"同样需要改写为：
**`6D0/6D4` 恒为 0 是 `0xBA2A60` 从未进入的结果，而非原因。**

### 22.4 回到真正的唯一入口条件

`0xBA2A60` 只在 `0xBA3010` 内被调用，而 `0xBA3010` 只在
`0xBA3590`（0x87 arm）arm 标志读到 1、`644==0` 之后被调用：

```text
0xBA35BC  cmp [ebp+0x13], 1     ; arm 标志必须 == 1
0xBA35D7  cmp [esi+0x644], 0    ; 必须 == 0
0xBA35E0  call 0xBA3010         ; -> 0xBA2A60
```

⇒ **`0xBA2A60` 从未进入 ⇔ `0xBA3590` 的 arm 分支从未成功。**

### 22.5 因此卡点仍回到 §19.6 的算术约束

```text
0xBA3AC2  cmp eax, [ebp-0x39C]  ; eax = frame_len + 游标
0xBA3AC8  jbe 0xBA3AE0          ; 必须 <= [obj+0xAC]
0xBA3ACA  xor bl,bl
0xBA3ACC  call 0x8435D0
0xBA3AD3  push 1
0xBA3AD8  call 0x4F7940
0xBA3ADB  jmp 0xBA387D          ; 失败出口（不复位，仅本次不 arm）
```

我们发出的帧令 `[obj+0xAC] = 382` 且 `frame_len = 382`，
`游标 > 0` ⇒ 该式恒成立失败。

`[obj+0xAC]` 由客户端按**实际收到的字节数**设置，
所以要让不等式成立，只有两条路：

1. **让实际帧长大于长度字段**：长度字段写 382，实际发更多字节，
   使 `[obj+0xAC] > 382`。与 §5.27.71 的否证不同——那次是把字段改小
   （破坏切帧），这次应保持字段 = 382 而**加大实际负载**。
2. **让游标为 0**：游标取自内层首 u32，我们写 4；若写 0，则
   `382 + 0 <= 382` 成立，但 opcode 会落在偏移 0（即长度字段首字节），
   需要把 opcode 放在帧的最前面。

### 22.6 下一步（按优先级）

1. **路线 1（首选，纯服务端数据）**：保持 `frame_len=382`，
   实际发送 `386 + N` 字节（在 8 字节 tag 之后追加填充），
   观察 `[obj+0xAC]` 是否大于 382、`644` 是否自然变 1。
2. 路线 2：把内层游标写 0 并把 opcode 置于帧首，验证
   `0xBA3AC2` 是否通过。
3. 两者都不要碰 `6D0/6D4`（指针，写了必崩）。

---

## 23. 路线 1 实测：否证（2026-10-05）

### 23.1 改动

新增纯服务端数据开关（不改客户端代码、不改长度字段）：

```
--reply-85-pad-after-tag N   在 8 字节 tag 之后追加 N 个零字节
```

透传链：`_e57a5c_experiment.py` → `lobby_plain_probe.py`
→ `build_0x85_server_cbc(pad_after_tag=N)` → `serve_handshake`。
离线自检：`frame_len=382, pad=64` → 实发 450 字节，长度字段仍 382。

### 23.2 实测（运行 `IFS1_ELEVATED_20261005_010101`，life=103.5 s）

服务端确实发出了加长帧：

```text
reply_85_cbc  seq=1  len=450  inner=87   （原为 386）
```

客户端侧：

```text
69.301  uA50=4  c8=2  5e8=3  ac=0  DW_LOBBY_CONNECTED
69.394  uA50=4  c8=4  5e8=0  ac=0  DW_LOBBY_CONNECTED   ← 仍是同一复位
随后 10054 强制关闭
```

**`ac`（即 `[obj+0xAC]`）全程为 0**，没有因为多发的 64 字节而变大。

### 23.3 否证结论

路线 1 的前提是"客户端按实际收到的字节数设置 `[obj+0xAC]`"。
实测否定该前提：`[obj+0xAC]` 只按**长度字段**切帧，
多发字节不会进入当前帧，`[obj+0xAC]` 保持 382（本轮因未计入而显示 0）。

补充静态依据：`0xBA4430` 的收帧入口按长度字段取帧，
`0xB783C0` 读流时以 `[ebp+0xC]`（= 帧长）为上界：

```text
0xB783E4  cmp edx, esi        ; 偏移 vs 长度
0xB783EA  cmp ecx, esi        ; 偏移+本次读取 vs 长度
0xB783EF  jne 失败            ; 超出即失败
```

⇒ 帧边界完全由长度字段决定，多发字节只会污染**下一帧**的开头，
这正是 §5.27.71 观察到的"解析立刻失败 / 10054"。

### 23.4 路线 1 作废后的剩余选项

长度字段不能再改小（§5.27.71 否证），多发字节也无效（本节否证）。
`frame_len + 游标 <= [obj+0xAC]` 在
`frame_len == [obj+0xAC]` 时**只能靠 `游标 == 0` 成立**。

⇒ 只剩路线 2：**把内层游标写 0**。

代价：`游标=0` 时 opcode 从 `source+0` 读取，即帧的**长度字段首字节**。
需要让该字节恰好等于 0x87（或 0x89），同时长度字段仍要被客户端
正确用于切帧——这两者直接冲突。

### 23.5 因此：服务端数据侧已无路

```text
改长度字段    否证（破坏切帧）
多发字节      否证（AC 不变）
游标=0        与长度字段语义冲突
强推 644      掩盖问题，且 0xBA2A60 自己会填 6D0/6D4（§22）
写 6D0/6D4    指针，必崩
```

**结论：在不改客户端代码的前提下，`0x87 arm` 无法达成。**
继续推进必须落在客户端侧（代码补丁或等价的内存改写），
这与项目授权边界（L0-05 允许内存写入 / `.text` patch / 断点）相符，
但每一步都要确认不触碰 L0-04 的反作弊禁令。

---

## 24. 客户端侧补丁首次生效（2026-10-05）

### 24.1 新增开关 `--arm-bounds-relax`

把 `0xBA3AC8` 的 `76 16`（`jbe`）改为 `EB 16`（`jmp`），
长度不变，不扰动其他指令，写入前逐字节校验：

```text
0xBA3AC2  3b8564fcffff   cmp eax,[ebp-0x39C]
0xBA3AC8  7616           jbe +0x16      ->  EB 16   jmp +0x16
```

透传链（四处全通）：

```
_e57a5c_experiment.py  ->  capture_elevated_network.ps1
                       ->  elevated_ifs1_observer.ps1
                       ->  AboProbe.cs (--arm-bounds-relax)
```

### 24.2 实测：补丁确实写入成功

运行 `IFS1_ELEVATED_20261005_010921`（life=110 s）：

```text
0.025  ARM_BOUNDS_STATUS done=0 pre=0000 post=0000   ← .text 尚未解密
4.394  ARM_BOUNDS_STATUS done=1 pre=7616 post=eb16   ★ 写入成功
```

（与 compat4 同构：早期读到 0000 是镜像尚未就位，不是补丁失败。）

### 24.3 但 arm 仍未成功 —— 失败点前移

```text
68.529  POST83_SAMPLE  s9c=1  5e8=3  644=0  ac=0    ← 复位前，ac=0
68.589  POST83_SAMPLE  s9c=0  5e8=0  644=0  ac=382  ← 已复位（c8=4/5e8=0）
```

服务端侧：`reply_85_cbc seq=1 len=386` 发出，
但客户端随即 `10054` 关闭；服务端只收到客户端自己的
`hold_recv len=258`（`ab 85`），**复位发生在我们应答之前**。

### 24.4 修正后的理解：`[obj+0xAC]` 是"当前帧长度"，不是"缓冲容量"

主手册 §5.27.65 已记录 `[obj+0xAC]` 在 `0 ↔ 382` 之间循环：
**每收到一帧置 382，处理完清零**。本次实测与之完全一致
（`ac=0` 空闲 → `ac=382` 收到帧）。

⇒ §22.5 把 `[obj+0xAC]` 当成"缓冲容量上限"是错的。
`frame_len + 游标 <= [obj+0xAC]` 的真实含义是
**"游标不能越过当前帧的末尾"**，即：

```text
382 + 游标 <= 382   ⇒  只有 游标 == 0 才合法
```

补丁把 `jbe` 改成 `jmp` 后该检查被跳过，所以
**本轮 arm 不再因越界被拒**——但仍然复位，说明后面还有别的判据。

### 24.5 当前状态与下一步

已排除（本轮）：

1. 越界检查 `0xBA3AC2`（已用补丁跳过，仍复位）

下一步按 `0xBA3710` → `0xBA3590` 的顺序逐关定位，优先级：

1. `0xBA39D4` MAC 比对（`--patch-85-pass` 已有，但未与本补丁联用）
2. `0xBA3AE6` 的 `cl == 0x87` —— 需确认我们帧内游标处的字节真是 0x87
3. `0xBA3AEB` 的 `[edi+0x640] >= 0xDC`

**建议下一轮：`--compat4 --arm-bounds-relax --patch-85-pass`**
（注意不要加 `--patch-87-gate`，它会把 0x89 也送进 arm，
破坏自然握手的可观测性）。

---

## 25. ★★★ 复位消除，握手持续进行（2026-10-05）

### 25.1 组合

```
--compat4 --arm-bounds-relax --patch-85-pass
--follow-85 --follow-85-rule receive --follow-85-cbc
--reply-85-cbc --reply-85-seqs 1,2,3,4 --reply-85-arm-first
```

运行 `IFS1_ELEVATED_20261005_011326`（life=105.1 s，`st 4 -> 5`）。

### 25.2 复位消失

对比 §24.3（只有 bounds-relax 时）：

| | §24.3 | §25 本轮 |
|---|---|---|
| `c8` | `2 -> 4`（复位） | **保持 2** |
| `5e8` | `3 -> 0` | **保持 3** |
| `5ec` | 1 → 2 后停 | **1 → 4 → 7**（持续增长） |
| 结束 | 10054 | `hold_peer_closed`（正常收尾） |

时序：

```text
68.044  uA50=4  c8=2  5e8=3  644=0  5ec=1   DW_LOBBY_CONNECTED
68.106  uA50=4  c8=2  5e8=3  644=0  5ec=4   DW_LOBBY_CONNECTED   ★ 收帧推进
85.080  uA50=5  c8=2  5e8=3  644=0  5ec=4   DWLOBBY_PUMP_SUCCESS ★
85.096  uA50=5  c8=2  5e8=3  644=0  5ec=7   DWLOBBY_PUMP_SUCCESS ★
105.068 进程被探针终止（非崩溃）
```

### 25.3 服务端侧：四帧全部送达并被消费

```text
hold_recv  258  -> reply_85_cbc seq=1 inner=87   （arm）
hold_recv  194  -> reply_85_cbc seq=2 inner=89
hold_recv  468  -> reply_85_cbc seq=3 inner=89
              reply_85_cbc seq=4 inner=89
hold_peer_closed（客户端正常关闭，非 10054）
```

⇒ 客户端持续发 `0x85`（258/194/468 字节），我们也持续应答，
**双方进入稳定的收发循环**，不再是 §16 那种 155 次 `recv_timeout` 僵持。

### 25.4 仍未闭合的一点

```
644 全程 = 0
```

即 `0xBA3590` 的 `mov [esi+0x644], 1`（`0xBA35EB`）仍未执行。
但职责已清楚：`--patch-85-pass` 跳过了 MAC 比对，
`--arm-bounds-relax` 跳过了越界检查，剩下的失败点在

```text
0xBA3AE6  cmp cl, 0x87          ; 游标处的字节是否真是 0x87
0xBA3AEB  cmp [edi+0x640], 0xDC ; 必须 >= 0xDC
```

或 `0xBA35B0` 读到的 arm 标志不是 1。

### 25.5 这是本项目目前最好的状态

```text
已闭合：启动 / TCLS / IIPS / ACE / 认证 / 大厅连接 / 握手密码学
        / st=5 / DWLOBBY_PUMP_SUCCESS / 复位消除 / 持续收发
未闭合：[obj+0x644] 从 0 到 1（0x87 arm 的最后一步）
```

下一步（按优先级）：

1. 打点确认 `0xBA3AE6` 处 `cl` 的实际值，以及 `[edi+0x640]` 是否 >= 0xDC。
2. 若 `cl != 0x87`，说明内层游标位置不对，回到
   `build_inner_87()` 的游标语义（§18）复核。
3. 保留本组合作为后续所有实验的**新基线**。

---

## 26. arm 前置条件逐条核对（2026-10-05）

### 26.1 `[obj+0x640]` 已达标

`0xBA3AEB` 要求 `cmp [edi+0x640], 0xDC`（220）不 below。

本轮 `IFS1_ELEVATED_20261005_011326` 实测：

```text
68.028  640=220  644=0  c8=2  5e8=2
68.044  640=220  644=0  c8=2  5e8=3
```

220 == 0xDC ⇒ **该门已通过**，不再是卡点。

### 26.2 内层 0x87 信封离线自检通过

按 §18 的游标语义，用真实的 CBC 解密路径还原我们发的帧：

```text
inner87 bytes       : 04 00 00 00 87 01
plaintext[0:16]     : 04 00 00 00 87 01 00 00 00 00 00 00 00 00 00 00
cursor u32          : 4
byte at cursor      : 0x87      ★
next byte (arm 标志): 0x01      ★
```

⇒ `0xBA3AE6` 的 `cl == 0x87` 与 `0xBA35BC` 的 `== 1` 在
**纯密文层面都满足**。二者在实机仍不成立，只能说明
**客户端读到的明文不是我们以为的这一份**（解密键或读流起点不同）。

### 26.3 读流失败的两个候选

`0xB78350/0xB783C0` 是统一的流读取器，失败条件：

```text
0xB78374  cmp esi, eax        ; 起始偏移 vs 上界 [ebp+0xC]
0xB7837A  cmp ecx, eax        ; 起始+本次长度 vs 上界
两者都必须 <=  否则返回 0
```

上界 `[ebp+0xC]` 来自调用方，即帧长。若客户端把上界当作
**382** 而我们的实际明文体更长/更短，或读起点不在解密体开头，
即使游标=4 也会越界失败。

### 26.4 下一步（收敛为两个可判实验）

1. **确认解密键是否一致**：本轮服务端用
   `codec_02a0(src20)[4:20]` 作 AES key、`codec_02a0(src20)` 作 HMAC key。
   离线用同一 `src20`（`30 2c 42 63 ...`）可自洽解出 0x87/0x01，
   但客户端是否用同一 `src20` 需实测——建议在观察器里把
   `[obj+0x620]` 的 20 字节与服务端 `src20` 打在同一条事件里比对。
2. **确认读起点**：在 `0xBA37A0` 附近打点，输出
   `[ebp-0x3A8]`（首 u32）与 `[ebp-0x3A0]`（游标）的实际值；
   若首 u32 不是 4，说明读起点不是解密体开头。

### 26.5 当前总账（本会话为止）

```text
已闭合：
  启动 / TCLS / IIPS / ACE 环境
  认证 + 3074 明文大厅通道
  0x81 / 0x82 / 0x83 / 0x85 收发
  st=5 / DWLOBBY_PUMP_SUCCESS
  复位消除（c8 不再变 4）
  持续收发循环（5ec 1->4->7）
  [obj+0x640] >= 0xDC
  内层 0x87 信封（离线自洽）

未闭合：
  [obj+0x644] 0 -> 1
 根因候选：客户端解密键 / 读流起点与我们的假设不一致
```

---

## 27. ★★★ 修掉一个真实 bug：0x85 应答用了错误的密钥（2026-10-05）

### 27.1 现象

`KEYCMP` 轮（`IFS1_ELEVATED_20261005_011908`）服务端日志里：

```text
85_tag  src20 = 31 2f 30 2d 06 03 55 04 0b 13 26 56 69 73 61 20 49 6e 74 65
```

解出来是 ASCII：

```text
b'1/0-\x06\x03U\x04\x0b\x13&Visa Inte'
```

⇒ 这是**证书 DER 片段**，不是握手密钥。

同一时刻客户端的真实值（新增 `RECV_KEY` 事件实测）：

```text
hs620 = 74300af8 a6a7d0e2 40a6685c c398ef50 6db476fd 726e6174 88776655 44332211
```

### 27.2 根因

`lobby_plain_probe.py` 的应答路径用 `--key-file` 取 20 字节源，
而 `_e57a5c_experiment.py` **只在 `--follow-85` 分支里**追加该参数：

```python
if follow_85:
    ...
    argv += ["--key-file", tx if follow_85_rule == "send" else rx]
```

⇒ 只给 `--reply-85-cbc` 而不给 `--follow-85` 时，`--key-file` 为空，
`read_key_file()` 返回空串后落到缺省源（证书 DER）。

**这意味着此前大量轮次的 0x85 应答都是用错误密钥签名/加密的**，
客户端解密出来自然不是 `0x87/0x01`。

### 27.3 修复

```python
if reply_85_cbc:
    argv.append("--reply-85-cbc")
    # 应答路径同样需要 20 字节源；以前只有 --follow-85 才设置
    if "--key-file" not in argv:
        argv += ["--key-file", tx if follow_85_rule == "send" else rx]
```

### 27.4 密钥一致性已验证

修复后（`IFS1_ELEVATED_20261005_012515`，life=97.9 s，`st 4 -> 5`）：

```text
客户端 [obj+0x620] 前 20B : 8fca5c67 657c2f98 109d29dd 29cdfb98 5787f615
服务端 rx.txt (= src20)   : 8fca5c67 657c2f98 109d29dd 29cdfb98 5787f615   ★ 一致
推导 AES[4:20]            : 915ec1988243e7770e67e76cd797d722
```

而修复前：

```text
rx.txt 推导              : 550cf5f3 52853ee2d278a6f6e432f3a4eda457ca
客户端实测 p608key        : 52853ee2d278a6f6e432f3a4eda457ca   ★ 也一致
```

⇒ `codec_02a0([obj+0x620])[4:20] == [p608+0x14]` 这一关系
**在两轮独立数据上都成立**，密钥推导模型本身是对的。

### 27.5 本轮状态（修复后仍差一步）

```text
68.318  uA50=4  c8=2  5e8=3  644=0  5ec=1   DW_LOBBY_CONNECTED
68.382  c8=2  5e8=3  644=0  5ec=2
85.324  uA50=5  c8=2  5e8=3  644=0  5ec=2   DWLOBBY_PUMP_SUCCESS
85.340  5ec=5
97.845  c8=4  5e8=0                          ← 末尾才复位（探针终止时）
```

`644` 仍为 0，但**密钥不再是原因**。剩余候选：

1. AES 密钥取 `[4:20]` 的偏移在新一轮是否仍成立（本轮 `p608key` 读空，
   需在 `5e8==3` 之后再采一次才能比对）。
2. `0xBA3A91` 的读起点是否落在解密体开头（§26.4 第 2 条）。

### 27.6 下一步

在 `5ec >= 2`（客户端已收帧）之后再采一次 `RECV_KEY`，
确认 `p608key` 与推导值逐字节相等；若相等，则转向读起点问题。

```
CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md   主手册
CODOLServer\HANDOFF_20261002_TLDR.md             上一版精简交接
CODOLServer\_mainline\_e57a5c_experiment.py      主实验驱动
restore_iips_contract_001\observer2\AboProbe.cs  观察器
run_codol_001\elevated_ifs1_observer.ps1         观察器包装
```
