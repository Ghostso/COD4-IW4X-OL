# CODOL 服务器联调手册
版本：2026-09-27
根目录：D:\BaiduNetdiskDownload\使命召唤OL

## 1. 组件
探针：CODOLServer\lobby_server\lobby_probe_server.py，监听 127.0.0.1:8443。
Socket：CODOLServer\lobby_server\lobby_socket_server.py，监听 127.0.0.2:8444。
证书：CODOLServer\lobby_server\lobby_server.pem、lobby_server.key、ca_append.pem。
客户端目录：run_codol_001\sandbox_ifs1_20260923。

## 2. 证书
```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
python -X utf8 CODOLServer\lobby_server\mklobby_cert.py
```
追加 CA 前必须先复制 cacert.pem 备份。不要重复追加同一个 CA。

## 3. dwauth.ini
固化链使用的配置文件是：
```text
run_codol_001\sandbox_ifs1_20260923\dwauth.ini
```
当前实验内容：
```text
127.0.0.1
0
127.0.0.1
443
0
0
0
```
位置由进程当前工作目录决定，不能只修改 COD OL 目录后假定沙箱使用了它。

## 4. 启动服务器
探针窗口：
```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
python -X utf8 CODOLServer\lobby_server\lobby_probe_server.py --cert-dir CODOLServer\lobby_server --bind 127.0.0.1 --port 8443 --log CODOLServer\logs\lobby_probe.jsonl
```
Socket 窗口：
```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
python -X utf8 CODOLServer\lobby_server\lobby_socket_server.py --cert-dir CODOLServer\lobby_server --bind 127.0.0.2 --port 8444 --log CODOLServer\logs\lobby_socket.jsonl
```
两个窗口必须显示 listen 并保持运行。

如果客户端目标是 443，系统必须已有 443 到 8443/8444 的转发。本手册不自动修改系统网络。

## 5. /auth/ 契约
请求是 TLS 内的 POST /auth/，常带 Content-Type、X-TransactionID 和 Expect: 100-continue。
服务器先回复 HTTP/1.1 100 Continue，再读取 body，最后回复完整 HTTP 200，并正常完成 TLS close-notify。

当前 auth_task 映射：
```text
0 -> 1
10 -> 11
12 -> 13
24 -> 25
26 -> 27
32 -> 57
```
当前 ticket 约束：client_ticket 和 server_ticket 均为 base64 解码后 128 字节，前四字节 DE AD BD EF；lsg_server_ticket 为 128 字节。
客户端反汇编记录存在 response.iv_seed == 0 检查；该字段必须单独实验，不能和 ticket/auth_task 同时改变。

## 6. 固化启动
检查管理员代理：
```powershell
Get-Content 'CODOLServer\logs\elevated_agent.json' -Raw
```
必须有 debug_privilege=true。通过代理启动：
```powershell
python -X utf8 CODOLServer\_mainline\agent_client.py run powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\capture_elevated_network.ps1' -DurationSeconds 90
```
不要直接双击游戏，也不要用自写 CreateProcess 启动器替代固化链。

## 7. 日志判定
探针日志必须出现：tls_ok、POST /auth/、auth_task_map、roundtrip、tls_close_notify。
GET /、selftest、health_check 只代表自测，不代表游戏连接。
Socket 日志至少出现 tls_wrapped 和 connect，才算进入第二阶段。

客户端状态：
```text
flag_61f=1,uA78=2,sub_state=6  已进入 /auth/
sub_state=7                    正在处理响应
last_err=741 / 0x2E5           HTTP/BD_EMPTY 候选
last_err=735 / 0x2DF           auth_task 或 ticket/tag 候选
sub_state=9                    账号鉴权完成
uA50=3                         大厅连接成功候选
```
真正成功只能是 sub_state=9 或 DW_LOBBY_CONNECTED / 主状态=3。

## 8. 故障判断
游戏 8 秒内 0xFFFFFFFF 退出：启动/IIPS 前置失败。
iips.dll 或 ifs2.dll 未加载：不要分析服务器协议。
flag_61f=0：在线闸门未打开。
flag_61f=1 但无 /auth/：查 host/port 和实际转发。
有 /auth/ 且 last_err=741：查 HTTP 状态保存和 TLS 收尾。
last_err=735：查 0xB9A59B 或 0xB9A7C7。
有 /auth/ 但无 socket：业务响应尚未推进到第二阶段。

## 9. 当前未完成
/auth/ 第 8 个业务条件未完全确证；httpobj+0x464 尚需同步采样；GDP 真实大厅帧未知；完整大厅服务器和战斗服务器均未完成。

## 10. 停止服务器
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'lobby_probe_server|lobby_socket_server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```
不要使用 taskkill /IM python.exe，因为它可能杀掉提权代理。
