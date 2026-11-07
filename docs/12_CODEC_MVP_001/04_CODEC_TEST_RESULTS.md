# 04 - Codec 测试结果

## 1. 构建

工作副本:
D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\worktree\CODOL-Combat-Server-v0.1

命令:

    cd D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\worktree\CODOL-Combat-Server-v0.1
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build\build.ps1 -Configuration release

结果: BUILD OK

- csc: C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
- sources: 24
- source fingerprint: af48d95a3a751758d85518c191beaf73f47ddd8d2f0ffe4d96c47e85e510b744
- artifact SHA-256: 66B9AE0164F1CFBF2B79149CEBC27D565DB88EF099700E9E96AE483FB6B7E677
- build manifest: worktree\build\bin\BUILD_MANIFEST.txt

## 2. 新增 Codec 离线测试

命令:

    .\build\bin\CODOLCombatServer.exe --codec-selftest

结果: 26/26 PASS

覆盖:
- reliable 0x02 golden
- reliable 0x01 golden
- 空 payload / 最大 0x3FC payload / 超长拒绝
- 截断 / 长度不匹配 / 未知 opcode
- 有符号 sequence 边界
- configstring header/count/body/terminator
- gamestate 已确认字段完整往返
- configstring offset 不匹配
- 地图名字符集和 0x3F 长度限制
- snapshot 内层 0x06 token
- snapshot outer 0x05/0x06 selector
- unknown semantics guard

原始输出:
D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\_data\codec_selftest.txt

## 3. 原有完整离线自测

命令:

    .\build\bin\CODOLCombatServer.exe --selftest

工作副本结果: 111 通过，3 失败

失败项与原工程基线一致:
- %TEMP%\codol_sess_* UnauthorizedAccessException
- %TEMP%\codol_cfg_*.cfg UnauthorizedAccessException
- %TEMP%\codol_fp_*\sub UnauthorizedAccessException

协议相关测试均通过:
- 握手/记录层
- 真实 14B usercmd
- 快照位流
- 会话描述符
- 构建来源指纹

输出:
D:\BaiduNetdiskDownload\使命召唤OL\12_CODEC_MVP_001\_data\full_selftest_worktree.txt

## 4. 修改范围

新增:
- src\Codol\Codec2697.cs
- src\Codol\Codec2697SelfTest.cs

修改:
- src\Program.cs: 增加 --codec-selftest 入口和帮助文本。

没有修改:
- 密码学模块
- P-224/ECDH
- 现有网络传输
- 现有快照编码默认路径
- 原始工程和原始样本

## 5. 结论等级

- 已确认字段编码与边界: VERIFIED（基于 E1-E3 指令和构造向量）
- 现有协议回归: VERIFIED（离线）
- 客户端兼容: NOT-OBSERVED
- 0x02 客户端分派、0x06 客户端语义: BLOCKED
