# CODOL 全量动态扫描保存报告

日期：2026-09-27
状态：**本轮真实启动与动态采集已完成，原始证据已保存。**

本报告只把本轮时间线一致的文件作为当前事实。旧运行日志仅作为背景线索，
不能与本轮数据混用。

## 1. 本轮运行

标准固化链运行目录：

```text
D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\IFS1_ELEVATED_20260927_223423
```

专用服务日志目录：

```text
D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\logs\FULL_DYNAMIC_20260927_2238
```

启动参数与身份：

```text
ADMIN=True
PROBE_PID=764
DURATION_SECONDS=120
SANDBOX=D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_ifs1_20260923
ARGS=--mode B --tag IFS1_ELEVATED_20260927_223423 --duration 120
```

本轮确认的进程：

```text
AboProbe.exe
codoMP_client_shipRetail.exe
IIPSHostApp.exe
TenProxy.dll（游戏模块）
TQMCenter.exe
```

## 2. 模块与窗口时间线

来源：

```text
run_codol_001\runs\IFS1_ELEVATED_20260927_223423\aboprobe_run\IFS1_ELEVATED_20260927_223423_events.csv
```

关键事件：

```text
t=6.747    TenProxy.dll 载入
t=8.094    iips.dll 载入
t=9.160    ifs2.dll 载入
t=15.245   CoD Splash Screen / 使命召唤online Multiplayer
t=120.024  采集结束，游戏被采集器终止
```

本轮不是 8 秒退出，也不是 IIPS 缺失。IIPS 启动链在本轮真实运行中完整出现。

## 3. 服务端与 TLS 证据

本轮专用探针日志：

```text
CODOLServer\logs\FULL_DYNAMIC_20260927_2238\probe.jsonl
CODOLServer\logs\FULL_DYNAMIC_20260927_2238\probe.20260927_223335.jsonl
```

本轮服务端观测到：

```text
TLS 版本：TLSv1
密码套件：AES256-SHA
请求：POST /auth/
请求头：Expect: 100-continue
响应：HTTP 200
收尾：TLS close-notify
```

真实请求字段：

```json
{
  "auth_task": "10",
  "iv_seed": "2034743188",
  "title_id": "0",
  "identity": "356c4bc3",
  "extra_data": "{\"version\": \"0\", \"user_id\": \"10995207597479878709\", \"extended_data\": true}"
}
```

本轮响应：

```text
auth_task=11
code=700
iv_seed=2034743188（回显请求值）
client_ticket=128 字节，DE AD BD EF 开头
server_ticket=128 字节，DE AD BD EF 开头
lsg_server_ticket=128 字节
```

## 4. socket 证据

本轮专用 socket 日志：

```text
CODOLServer\logs\FULL_DYNAMIC_20260927_2238\socket.jsonl
```

本轮仅确认：

```text
127.0.0.2:8444 listen
```

没有观测到：

```text
tls_wrapped
connect
游戏到 127.0.0.2:8444 的大厅 socket
```

因此本轮真实状态仍是：

```text
IIPS 成功
stage 10 /auth/ 成功
stage 32 未出现
大厅 socket 未建立
```

## 5. AFD/ETW 网络证据

来源：

```text
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260927_223157\afd.etl
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260927_223157\afd.xml
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260927_223157\game_etw.jsonl
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260927_223157\game_rt_report.md
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260927_223157\rt_etw_console.txt
run_codol_001\runs\NET_CAPTURE_ELEVATED_20260927_223157\rt_summary_console.txt
```

这些文件保存了本轮 AFD ETW 原始数据、解析结果和报告。分析时以 `game_etw.jsonl`
和 `game_rt_report.md` 为入口，必要时回到 `afd.etl`/`afd.xml` 复核。

## 6. 客户端原始证据

```text
observer.jsonl
aboprobe.stdout
aboprobe.stderr
aboprobe_run\*_events.csv
aboprobe_run\*_summary.txt
processes_before.json
processes_final.json
launch.txt
identity.txt
token_privileges.txt
token_groups.txt
original_hashes_before.json
original_hashes_after.json
iips_files\
```

这些文件均位于：

```text
run_codol_001\runs\IFS1_ELEVATED_20260927_223423\
```

其中 `observer.jsonl` 保存进程、窗口、模块对应的时间采样；事件 CSV 保存模块、
线程、窗口与退出时间线；`iips_files` 保存运行末尾的 IIPS 文件状态。

## 7. 本轮事实结论

```text
游戏确实启动
固化链确实执行
TenProxy.dll 确实载入
iips.dll / ifs2.dll 确实载入
IIPSHostApp.exe 确实出现
在线版 Splash 窗口确实出现
dwauth.ini 实际配置为 127.0.0.1:443
真实 POST /auth/ 确实到达本地探针
HTTP 200 与 TLS close-notify 确实完成
client/server/lsg ticket 已返回
本轮没有 stage 32 请求
本轮没有大厅 socket
```

## 8. 当前不能下的结论

本轮不能证明：

```text
stage 32 -> 33 或 32 -> 57 哪个正确
ticket 内容是否能通过 stage 32 校验
历史 watcher 的 sub_state=9 是否对应真实大厅连接
TCLS 共享内存是否能恢复完整业务登录上下文
游戏是否已经真正进入 DW_LOBBY_CONNECTED
```

旧 `_auto2/_auto3/_auto5/_auto6` 记录含有状态值，但没有本轮级别的完整服务端、
socket、启动快照和界面证据，只作为待核对线索保存。

## 9. 静态分析入口

下一轮静态分析优先使用以下动态锚点：

```text
TenProxy.dll 载入时间：t=6.747
iips.dll 载入时间：t=8.094
ifs2.dll 载入时间：t=9.160
/auth/ 请求时间：服务端专用日志中的 ts=1790519684.*
stage 10 响应：auth_task 11 / code 700
stage 32：本轮未出现，不应从本轮推导
```

对应静态函数重点：

```text
0x641600        TenProxy ApplySettings
0x7F2E7F        cfg_applied 门控
0x801A00        objC 创建路径
0x7F2BA0        主连接路径
0xB88CC0        objA 连接调用
0xB9A470        /auth/ 响应解析
0xB983F0        响应结果取值器
0x7F3190        objC/结果推进判定
```

## 10. 说明

本报告保存的是一次真实启动、真实服务端请求、真实 TLS/AFD 事件和真实模块时间线。
它不是“完整复活游戏”的证明，也不包含绕过安全组件或伪造在线凭据的结论。
后续工作应以本报告列出的原始文件为证据入口，逐项验证，避免把旧 watcher 状态
或累计日志误当成当前运行事实。
