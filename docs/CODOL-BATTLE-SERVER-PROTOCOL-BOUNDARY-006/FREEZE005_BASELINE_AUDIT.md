# FREEZE-005 基线实际内容审计

## 1. 结论

当前正式工程 `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1` 的实际源码状态与 `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005` 一致：

- `src/**/*.cs`：25 个文件
- 源码指纹：`5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`
- FREEZE-005 记录值：同一指纹
- 006 开工复核：同一指纹
- 因此本轮分析的基线不是 003 或某个中间态，而是 FREEZE-005 冻结候选。

## 2. 002 是否进入冻结版本

**是，且哈希逐项一致。**

`CODOL-BATTLE-SERVER-PROTOCOL-002\CHANGED_FILES.tsv` 列出的 9 个源码文件，其 SHA-256 与当前工程对应文件相同：

| 文件 | 当前 SHA-256 |
|---|---|
| `src/Codol/Codol2697Protocol.cs` | `bc4aaf1ee518072b0776efe29f491710002c8000ee6a131b4df9e6714e9065c6` |
| `src/Engine/ClientSession.cs` | `17b813dbf4a6881fe19b636178c8cded8d2d609f5589ca2119c923971f3aa3fe` |
| `src/Engine/ClientLogic.cs` | `0aba015da760a1c6f7ceb717895f6240060ca6bbfcfa1f41b592c39e9c2468cc` |
| `src/Engine/ServerConfig.cs` | `3767c4721eeec345c7680c390dd41edc40418181221c6f4fd407ac77e19032e2` |
| `src/Engine/GameWorld.cs` | `07fa1793671f5ff8dee84177cecdf162adc28e7956d2a216d0a8fd8b2a27cc7d` |
| `src/Engine/ServerHost.cs` | `245725fbeeb65b8c9c5bfb1310204ca43b99f58e86875cdb909a074d09382c67` |
| `src/Program.cs` | `56ce57d3848ac29fab5bd77af87ff80a08ca90d107676cf64025865bdf76ae3a` |
| `src/SelfTest.cs` | `16660b753d0e3c585f7d8043d732865acf8c536bf1602cd13c5b46512ea8c6ba` |
| `src/SelfTest.Codol2697.cs` | `98663ec8a3940f808558686ae2aa0507b7a238f325c5edf3ac7313ab5ac47f88` |

## 3. 003 是否原样进入冻结版本

**不能证明“原样”进入；只能证明相关功能语义仍存在。**

003 记录的三项源码哈希与 FREEZE-005/当前工程不同：

| 003 文件 | 003 SHA-256 | FREEZE-005 当前 SHA-256 |
|---|---|---|
| `src/Engine/ServerConfig.cs` | `1ba23b8ab24e235cc9bbb38703051024c6363c731f080a069c355e754448213e` | `3767c4721eeec345c7680c390dd41edc40418181221c6f4fd407ac77e19032e2` |
| `src/Engine/GameWorld.cs` | `4b1df7298e2c13e426a63ca080806469611d0c2a3468a38315eb7f203082ccb0` | `07fa1793671f5ff8dee84177cecdf162adc28e7956d2a216d0a8fd8b2a27cc7d` |
| `src/SelfTest.cs` | `3cbfd37a843206ae725a3668c940f6f80a607befa161f91a0ca960721af3e9df` | `16660b753d0e3c585f7d8043d732865acf8c536bf1602cd13c5b46512ea8c6ba` |

差异原因在 002 的后续修改之后被重新构建和整合。当前代码仍能找到 003 的功能标记：

- `ServerConfig.cs:63`：默认 `MovementModel = "captured"`。
- `ServerConfig.cs:68-70`：`CapturedMovement` 判定，仅 `smooth` 为实验回退。
- `ServerConfig.cs:314-320`：解析 `movement_model`、`vertical_sim`。
- `GameWorld.cs:402-468`：实录水平运动学、默认关闭的竖直模拟。
- `SelfTest.cs:56`：注册第 12 节“战斗世界”。
- `SelfTest.cs:1921` 以后：战斗世界移动/武器/生命周期测试。
- `config/combat_server.cfg`：默认 `movement_model = captured`、`vertical_sim = 0`。

## 4. 对 006 的影响

006 可以安全地引用 FREEZE-005 的 25 文件指纹作为代码基线，但不得把 003 的旧文件哈希或旧 168448 B 产物当作冻结物；003 的行为需要从当前源码重新定位，不能按旧行号或旧哈希宣称一致。