# 06 — 官方游戏网络接收路径（工作包 D）

## 1. 本轮方法

只读复用 046 的映像 `image_best.bin`（10,899,456 B），执行 4 轮定向分析：

| Pass | 脚本 | 产物 |
|---|---|---|
| D1 | `scripts\workpackageD_static_scan.py` | `evidence\047_workpackageD_static_scan.json` |
| D2 | `scripts\workpackageD_function_attribution.py` | `evidence\047_workpackageD_function_attribution.json` |
| D3 | `scripts\workpackageD_upstream_bfs.py` | `evidence\047_workpackageD_upstream_bfs.json` |
| D4 | `scripts\workpackageD_strict_overlap.py` | `evidence\047_workpackageD_strict_overlap.json` |

## 2. 结果

1. **P4 候选簇**（`0x865300–0x866000`）：43 个直接调用点，11 个函数，内部/外部边分离。
2. **P5 候选簇**（`0x876800–0x877000`）：45 个直接调用点，8 个函数。
3. **游戏协议串定位复核**：`gamestateupdate 0x9B4700`、`connectResponse 0x9BFF0C`、
   `EXE_CONFIGSTRINGMISMATCH 0x9B46E4`、`EXE_LOSTRELIABLECOMMANDS 0x9BB5E8`、`CA_GAMESTATE 0x9C0974`。
4. **可靠命令锚点 `0x376B14`** 有 13 个上游调用者：
   `0x7A662, 0x7EBEA, 0x7F702, 0x81338, 0x81F57, 0x1B7D11, 0x1B8882, 0x1B9516, 0x1BAE87, 0x1BC009, 0x1BC5C2, 0x1BC8F1, 0x376B7E`。
5. **严格重叠检验结果为空**：这 13 个调用者**无一**落在 P4/P5 簇内，也**没有**靠近已知游戏协议串引用点。
   （唯一例外 `0x376B7E` 与 `EXE_LOSTRELIABLECOMMANDS` 距离 1 个字节，属于同一函数内的相邻指令。）

## 3. 结论等级

- **得到:** 可复核的**负证据**与候选收敛。
- **未得到:** `游戏网络接收 → 消息解析 → opcode 分派 → 游戏状态消费者` 的完整链。
- **明确禁止:** 基于地址接近、函数名、通用 decoder 存在而宣称链已闭合。

## 4. 需要的最小额外证据

| 编号 | 证据 | 说明 |
|---|---|---|
| E-047-1 | `0x0E5C9000` 之后第 3 节区只读快照 | 046 指出的 `RSize 0x62000` 之外区域 |
| E-047-2 | P4/P5 各函数的真实入口边界（PDB 或更完整重定位信息） | 当前函数归属为启发式 |
| E-047-3 | 与预期构建 `E3823FD6..F37B` 匹配的样本 | 用于对齐 A-07 |
| E-047-4 | 一次受控的只读调用栈采样（需单独授权） | 仅在静态不可解时使用 |

## 5. 边界声明

以上分析**未**使用运行时内存读取、注入、hook；**未**启动客户端；**未**修改 040–046 产物。
