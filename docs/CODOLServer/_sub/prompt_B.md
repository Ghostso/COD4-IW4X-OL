你是 CODOL 复活项目的子代理 B。工作目录 D:\BaiduNetdiskDownload\使命召唤OL。

## 硬约束
- 禁止改系统网络（netsh / route / DNS / firewall / 网卡）。
- 允许启动游戏、读进程内存、附加调试、提权。提权代理在线：python -X utf8 CODOLServer\_mainline\agent_client.py ping
- 一次只跑一个游戏实例；跑完 taskkill /F /IM codoMP_client_shipRetail.exe /T 清理。
- 命令与脚本必须 ASCII 纯文本。脚本前缀 _subB_，只写 CODOLServer\_sub\ 与 CODOLServer\_mainline\。

## 背景（已确认，直接使用）
- 游戏把启动期"疑似服务端"的外连发往 116.130.224.66:8000（UDP，magic 'ur'，24 字节请求）。
- 该地址 = DNS 解析 ied-tqos.qq.com 的结果（TQoS）。ctrl.iips.qq.com 现在解析到 81.71.56.27/168，与它无关。
- 已有 73 字节 / 48 字节等假应答模板，见 CODOLServer\_mainline\gdp_server.py 与 run_codol_001\runs\AUTO_TQOS_V1_A1\server\fake_tqos.jsonl。
- 固化启动链：powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\run_codol_001\capture_elevated_network.ps1' -DurationSeconds 120
- 弹窗是游戏内渲染，只有桌面 BitBlt 截图能看到，工具 CODOLServer\_mainline\_pop_desktop_shot.py。
- 已有工具：CODOLServer\_mainline\suspend_host_redirect.py（挂起期等长改写主机名字符串，已验证可用）、_popup_watch.py、gdp_server.py。

## 任务
把 116.130.224.66:8000 这条路做成受控 A/B 实验，判定它到底是不是 [100] 的成因。

1. 用 suspend_host_redirect.py 把 ied-tqos.qq.com 等长改写成 127.0.0.1（不改 hosts、不改 netsh），本地在 8000/UDP 起应答服务。
2. 起游戏 -> 桌面截图 -> 记录：是否仍出现 [100]？出现的时刻？本地服务收到了什么？
3. 对照实验，各跑一次：本地服务"故意不应答" / "按模板应答" / "发送不同变体应答"，观察 [100] 是否变化。
4. 如果 [100] 与这条 UDP 无关，就明确给出反证（例如：不应答时也照样 N 秒后画 [100]；或画 [100] 时根本没有再次连接过这个地址）。
5. 顺便记录：画 [100] 前后，游戏进程有没有发起任何新的 connect（用 AFD ETW 或已有抓包脚本），特别是 TCP。

## 产出
报告 CODOLServer\_sub\SUBAGENT_B_DISCOVERY.md（中文，UTF-8），含：
- 三组 A/B 对照的原始输出与截图路径
- 明确结论：[100] 是否由 116.130.224.66:8000 触发（是 / 否 / 证据不足）
- 未解决项标 UNKNOWN

最后把结论摘要写进 CODOLServer\_sub\B_out.md。
