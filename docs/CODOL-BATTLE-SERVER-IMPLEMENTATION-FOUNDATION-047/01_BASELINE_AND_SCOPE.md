# 01 — 源码基线与保护范围

## 1. 基线来源

| 项 | 值 |
|---|---|
| 原始工程 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1` |
| 基线快照 | `baseline\CODOL-Combat-Server-v0.1\`（047 内只读副本，43 个文件） |
| 工具链 | .NET SDK 8.0.420, runtime 8.0.26, Windows x64 |
| 新工程 | `CODOL.BattleServer.Foundation.sln`（net8.0） |
| 目标任务目录 | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047` |

## 2. 版本控制

工作区本身没有 Git 元数据（`git rev-parse` 失败），因此 047 在任务目录内初始化独立 Git 仓库，
记录 047 自身的基线 commit；**不触碰**工作区外部历史。

## 3. 保护范围（本轮未修改）

- 最终客户端原始文件与原始资源：未读写修改。
- 040–046 任务目录：只读；哈希校验见 `scripts\verify-history-immutability.ps1`。
- 原始 v0.1 工程：只读；047 使用 `baseline\` 副本。
- 未启动 CODOL 客户端；未注入/hook/读运行时内存。

## 4. 历史哈希证据

- 清单：`evidence\040_046_BASELINE_SHA256.tsv`（547 条）
- 校验结果：`checked=547 failures=0`，`HISTORY_IMMUTABLE_OK`

## 5. 047 基线 commit

| 项 | 值 |
|---|---|
| commit | `0b73aecdfda86f13d355fce3ae1bea6d2ed340db` |
| message | `047: CODOL battle server implementation foundation` |
| 库产物 SHA-256 | `50445DBF253468BA492A6CFBE56EB639BA791026F63C70343AF2AB229996BDDB` |
| 测试产物 SHA-256 | `4863FDA856AC4FD5D19D94E32A2139A73BF33B8B2D358E9AB7AF48BD42E98D41` |

> 说明：.NET 默认确定性编译。若哈希与 `build\BUILD_MANIFEST.txt` 不一致，以 manifest 为准。
