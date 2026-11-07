# 01 - M0 基线冻结

> 本任务只推进 M0-M2 离线 Codec；未启动客户端/服务端网络会话，未注入、补丁或修改原始样本。

## 1. 工程位置

- 原工程: D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1
- 独立工作副本: D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\worktree\CODOL-Combat-Server-v0.1
- 原工程未修改；所有新增/修改仅发生在工作副本。

## 2. 基线哈希

| 项目 | SHA-256 |
|---|---|
| 2.6.9.7 客户端 EXE | 353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1 |
| 2697 服务端 EXE | 80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1 |
| 原工程 Program.cs | 9c34b50c1f2cf1e6edb618f1721667975635297e6a6641fedea61e38ed5d2e94 |
| 原工程 CodolProtocol.cs | fa06d0543b621216dc57c05a581ec1dcb8f00d18a9bf1368942213c75cf4a046 |
| 原工程 ClientLogic.cs | 8e864b4b254f5ec5708c7e5256c94191f94f87dff073bf57658de617a42b24c2 |
| 原工程 MotionSnapshot.cs | 272bb62147a81d108108da0439da6a080206c0f62c73f19c0b49395403af1d66 |
| 原工程 SelfTest.cs | dfebeb06905ded52b4e4ba74a021da68deba8d8250a357c38baffae05ddcc9664 |

完整 22 个原始 .cs 文件的路径、大小和 SHA-256 见:
D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\_data\source_hashes_baseline.json

## 3. 编译器与构建

- C# 编译器: C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
- 构建脚本: build\build.ps1
- 原工程 source fingerprint: 61982c961396249f9f5cc9ebef9b11308e990ecd528527ef0d5412910e16bbdd (22 sources)
- 工作副本 source fingerprint: af48d95a3a751758d85518c191beaf73f47ddd8d2f0ffe4d96c47e85e510b744 (24 sources)
- 工作副本构建产物 SHA-256: 66B9AE0164F1CFBF2B79149CEBC27D565DB88EF099700E9E96AE483FB6B7E677

## 4. 现有离线入口与基线

命令:

    cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1
    .\build\bin\CODOLCombatServer.exe --selftest

基线结果:

- 通过 111 项，失败 3 项。
- 3 项均为 %TEMP%\codol_* 路径 UnauthorizedAccessException:
  1. 描述符落盘导出
  2. 配置行内注释
  3. 指纹语义（合成目录）
- 密码学、P-224/ECDH、握手阶段、可靠命令解析、快照位流、会话描述符和源码指纹断言均通过。
- 结论: 协议基线可用；失败项是测试环境临时目录权限问题。

原始输出:
D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\_data\baseline_selftest_original.txt

## 5. 2697 已知规格与未决项

已知:
- Reliable command 0x01/0x02 及字段顺序。
- Gamestate 0x03 头部字段、configstring 嵌套位置、0x06 尾标记。
- Configstring 0x04、count、0x06 终止符。
- Snapshot 内层 0x06 和 outer 0x05/0x06 选择器。

未决:
- 客户端 opcode 0x02 分派到 RVA 0xA2E50。
- 客户端 0x06 语义。
- Gamestate 长字段业务名称。
- Configstring body 的完整位编码。
- Snapshot 完整字段/分段边界。

## 6. 工作副本修改

新增:
- src\Codol\Codec2697.cs
- src\Codol\Codec2697SelfTest.cs

最小修改:
- src\Program.cs
  - 增加 --codec-selftest 模式。
  - 帮助文本增加一行。
  - 不改变原 --selftest 行为。

修改摘要:
D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\_data\worktree_diff_summary.txt
