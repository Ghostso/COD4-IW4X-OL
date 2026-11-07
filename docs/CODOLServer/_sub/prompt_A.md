你是 CODOL 复活项目的子代理 A。工作目录 D:\BaiduNetdiskDownload\使命召唤OL。

## 硬约束
- 禁止改系统网络（netsh / route / DNS / firewall / 网卡）。上次改 netsh 导致用户断网，绝对禁止。
- 允许启动游戏、读进程内存、提权。提权代理在线：python -X utf8 CODOLServer\_mainline\agent_client.py ping
- 一次只跑一个游戏实例；跑完 taskkill /F /IM codoMP_client_shipRetail.exe /T 清理。
- 命令与脚本内容必须 ASCII 纯文本（PowerShell 5.1 按 GBK 读 .ps1）。
- 脚本前缀 _subA_，只写 CODOLServer\_sub\ 与 CODOLServer\_mainline\。

## 背景（已确认，不要重复验证）
- 游戏内渲染面板 [100]无法连接大厅服务 来自 key @SF_UI_DW_LIVE_CONNECTING_FAILED。
- 先读这几份报告：CODOLServer\IIPS_PIPELINE_FULL_REVERSE.md、CODOLServer\IIPS_POLICY_PROTOCOL.md、CODOLServer\IIPS_TAMPER_FORENSIC.md、CODOLServer\SUBAGENT_2_IIPS_VERDICT.md
- 已发现：COD OL\IIPS\TPFUI\IIPSRes 下的 UI png 全部被替换成 69 字节 1x1 透明 PNG，导致 IIPSHostApp 的 LoadImageFromBuffer 全失败。备份在 backups\ 下。
- 固化可复现启动链：powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\run_codol_001\capture_elevated_network.ps1' -DurationSeconds 75

## 任务
把 IIPSHostApp 的初始化链从"卡在 UI 资源"推进到"写出 IIPS\HostPid 并创建命名管道"。

1. 查 TPFUI 资源体系的真实布局：读 COD OL\IIPS\TPFUI\TPFUI.tprj、Style\IIPS.xml、Layout 目录，搞清楚 IIPSHostApp 到底从哪里加载 UI 资源、是否真的需要磁盘 PNG、还是应该从 IFS/vfs 归档取。判断 69 字节占位符是不是根本原因。
2. 提权做受控实验：
   a. 在 sandbox_ifs1_20260923 下把 IIPSRes 结构还原（用 工具\EX035_DIR 与 backups 里的真件替换占位符，或按 tprj 结构推断正确路径），再启 IIPSHostApp /mode iipslaunch，看 HostPid 是否被写入、\\.\Pipe\ 下是否出现 IIPS 管道。
   b. 如果 UI 不是根因，就提权读内存 + capstone 反汇编 IIPSHostApp.exe / IIPSHost.dll，定位它在什么条件下才写 HostPid、才 CreateNamedPipeA。
   c. 需要时用 Procmon 类手段（如果本机已有）或 ETW 观察它读了哪些路径、返回什么错误。
3. 关键产出：一份能复现的"让 IIPSHostApp 成功写出 HostPid 且创建管道"的最小步骤；或者反证说明它不可能在本地成立（附证据）。

## 产出
报告 CODOLServer\_sub\SUBAGENT_A_IIPS_HOST.md（中文，UTF-8），包含：
- 每条结论带 文件:偏移 / 反汇编片段 / 日志原文 证据
- 实验命令与原始输出摘要
- 未解决项明确标 UNKNOWN 并说明缺什么

最后把结论摘要写进 CODOLServer\_sub\A_out.md。
