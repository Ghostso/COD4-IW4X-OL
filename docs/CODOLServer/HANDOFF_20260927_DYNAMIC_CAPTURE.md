# CODOL 项目交接记录：在线闸门、IIPS 启动链与大厅动态抓取

日期：2026-09-27
工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`

> **[2026-09-27 已更正] 本文件的诊断结论已被推翻，请先读
> `HANDOFF_20260927_IIPS_GATE_RESOLVED.md`。**
>
> 本文件第 3 节"阻塞点是 WeGame/TCLS 前置上下文"**错误**：`tcls_core`
> 是否存在与 IIPS 是否载入无关，三次成功复现中有两次完全没有 TCLS。
>
> 本文件第 2 节把 `E2367C48` 当作"历史成功版本"、把 `72DDB9D1` 当作
> "被改坏的版本"，**方向是反的**：`72DDB9D1` 才是出厂原件
> （`工具\EX035_DIR`、`工具\EX053_BASELINE`、`COD OL` 三处一致，
> 2026-09-10 时间戳），`E2367C48` 是本项目 09-21 自己的 PE 手术产物。
>
> 真正的闸门是 `iips.ini` 的 **`enable_iips`**：`=1` 才会启动
> `IIPSHostApp.exe`、才会载入 `iips.dll` / `ifs2.dll`、才会产生真实
> `POST /auth/`。母沙箱此前是 `=0`（2026-09-27 05:06:44 写入），
> 这就是 09-27 下午起所有运行都失败的根因。
>
> 本文件第 6 节"下一步唯一正确顺序"的第 1 步（复现 WeGame/TCLS）
> **不要再执行**。

## 一、当前硬结论

本阶段已经确认过两类不同失败，不能混为一谈：

### A. 已进入在线模式的历史运行

多次 `watch.jsonl` 证明：

```text
flag_61f = 1
uA78 = 2              DW_DNS_COMPLETE
uA50 = 2
sub_state = 6         /auth/阶段
sub_state = 7         响应处理阶段
last_err = 741/735
dw_state = 10         DW_ACCOUNT_ERROR
```

代表文件：

```text
CODOLServer\_mainline\_auto_b2\watch.jsonl
CODOLServer\_mainline\_auto_b3\watch.jsonl
CODOLServer\_mainline\_fix1_20260926_192043\watch.jsonl
CODOLServer\_mainline\_hs1_20260926_201045\watch.jsonl
```

这类运行证明：客户端在线闸门已经打开，DNS 已完成，已经进入 `/auth/` 业务阶段。

### B. 2026-09-27 最新固化链运行

运行目录：

```text
run_codol_001\runs\IFS1_ELEVATED_20260927_150015
```

通过现有提权代理运行：

```text
ADMIN=True
TAG=IFS1_ELEVATED_20260927_150015
DURATION_SECONDS=90
```

结果：

```text
codoMP_client_shipRetail.exe 创建成功
codoMP_client_shipRetailBase.dll 载入
TenRpcs.dll / GameRpcs.dll 载入
游戏存活满 90 秒
exitcode=terminated（采集结束时终止）

iips.dll 未出现在 observer 模块列表
ifs2.dll 未出现在 observer 模块列表
没有 POST /auth/
没有 lobby socket 连接
```

因此本次 `iv_seed=0` 实验**没有被客户端执行到**，不能据此判断 `/auth/` 契约。

## 二、最新定位：IIPS 文件差异

历史成功运行：

```text
run_codol_001\runs\IFS1_ELEVATED_20260923_202751
```

历史成功记录显示：

```text
t=9.023   MODULE iips.dll
t=9.262   WINDOW_NEW class=iipsinit
t=10.124  MODULE ifs2.dll
t=17.522  CoD Splash Screen
t=50.276  IIPSHostApp.exe /mode iipslaunch
exitcode=0
```

历史成功运行使用的 `iips.dll`：

```text
SHA256 E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
```

当前沙箱原来的 `iips.dll`：

```text
SHA256 72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
```

已执行恢复：

```text
run_codol_001\sandbox_ifs1_20260923\IIPS\iips.dll.s2backup
    -> IIPS\iips.dll
```

恢复前文件已备份为：

```text
IIPS\iips.dll.bak_before_success_restore_20260927_145928
```

恢复后的当前 `iips.dll` hash 已确认是：

```text
E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
```

文件差异核对显示，除 `iips.dll` 外，下列组件与历史成功副本一致：

```text
IFS.dll
IFS2.dll
IIPSHost.dll
IIPSHostApp.exe
IIPSClient.ini
IIPSHostApp.ini
IIPSVersion.ini
Tenio.ini
iips-download.ini
IIPSFilelist.ini
iips_policymsg.dll
```

对比文件：

```text
CODOLServer\_mainline\_ifs_compare_20260927.json
```

## 三、关键新判断：启动链还缺 WeGame/TCLS 上下文

历史成功 `observer.jsonl` 的进程链中出现过：

```text
wegame.exe
tcls_core.exe
AboProbe.exe
codoMP_client_shipRetail.exe
TP3Helper.exe
TQMCenter.exe
IIPSHostApp.exe
```

最新 2026-09-27 运行中实际只看到：

```text
AboProbe.exe
codoMP_client_shipRetail.exe
TP3Helper.exe
TQMCenter.exe
```

当前系统检查未发现：

```text
wegame.exe
tcls_core.exe
Client.exe
TCLSHost.exe
IIPSHostApp.exe
```

所以最新启动失败不是服务器响应失败，而是：

```text
固化 AboProbe 启动游戏
-> 游戏加载 Base/TenRpcs/GameRpcs
-> 未加载 iips.dll/ifs2.dll
-> 未建立在线模式
-> 游戏没有发 /auth/
```

下一对话应优先复现历史成功运行时的 WeGame/TCLS 前置上下文，不要先调 `/auth/`。

## 四、服务器与 `/auth/` 当前状态

### 已有服务器

```text
lobby_probe_server.py  127.0.0.1:8443
lobby_socket_server.py 127.0.0.2:8444
```

当前测试拓扑依赖已有端口转发：

```text
127.0.0.1:443 -> 127.0.0.1:8443
127.0.0.2:443 -> 127.0.0.2:8444
```

本阶段没有新增或修改 `netsh` 规则。

### 当前 `/auth/` 响应代码

文件：

```text
CODOLServer\lobby_server\lobby_probe_server.py
```

当前逻辑：

```text
stage 0  -> response auth_task 1
stage 10 -> response auth_task 11
stage 12 -> response auth_task 13
stage 24 -> response auth_task 25
stage 26 -> response auth_task 27
stage 32 -> response auth_task 57
```

ticket：

```text
client_ticket 128 bytes, starts DE AD BD EF
server_ticket 128 bytes, starts DE AD BD EF
lsg_server_ticket_size = 128
```

重要未决矛盾：

```text
客户端反汇编记录：response.iv_seed 必须为 0
旧探针行为：response.iv_seed 回显 request.iv_seed
```

单变量 `iv_seed=0` 修改曾准备过，但**最新固化链未运行到 `/auth/`，因此没有验证结果**。

相关记录：

```text
CODOLServer\AUTH_IV_SEED_CONFLICT_20260927.md
CODOLServer\AUTH_FAILURE_ROOT_CAUSE_ANALYSIS_20260927.md
```

## 五、当前禁止重复做的事情

不要重复：

```text
把问题归因于缺 dwauth.ini
把问题归因于 flag_61f 没打开
直接双击 codoMP_client_shipRetail.exe
自己写 CreateProcess 启动器绕过固化链
先写 GDP/IW4X 服务器
再次无证据修改 portproxy
重复追加 cacert.pem
```

## 六、下一步唯一正确顺序

```text
1. 恢复/启动历史成功运行中的 WeGame/TCLS 前置上下文
2. 仍使用 AboProbe --mode B 固化链
3. 只读确认 iips.dll / ifs2.dll 是否载入
4. 只读确认 flag_61f 是否为 1
5. 只读确认 uA78 是否为 2
6. 只有出现真实 /auth/ 后，才测试 iv_seed=0
7. 出现 735 时运行 frida_auth_branch.py，定位 0xB9A59B 或 0xB9A7C7
8. 出现 741 时检查 HTTP status / close-notify / httpobj+0x464
```

## 七、提权代理现状

当前本地提权代理：

```text
pid=3284
debug_privilege=true
监听 127.0.0.1
```

它是后续无人值守执行固化链和只读动态采样的入口。

## 八、本轮清理

本轮启动的本地 Python 服务已停止后重新启动用于测试；新对话开始时应先检查：

```text
Get-Process python,codoMP_client_shipRetail,AboProbe,IIPSHostApp
```

不要按进程名批量杀 `python.exe`，避免杀掉提权代理。

================================================================================
新对话第一步：读取本文件，然后检查 WeGame/TCLS 上下文，不要重新从服务器端口开始。
================================================================================
