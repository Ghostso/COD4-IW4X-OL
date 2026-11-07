# COD4 / IW4X / COD OL — 逆向分析工作区

本仓库收录该项目的**文档与脚本**，不含任何游戏原始资产。

## 目录结构

| 路径 | 内容 |
|---|---|
| docs/overview/ | CODOL 总体性报告 |
| docs/experiments/ | EX0xx 系列实验记录与结论 |
| docs/battle-server/ | 自建战斗服务器相关分析 |
| docs/baseline/ | 启动基线判定与裁定 |
| docs/build/ | 构建风险与产物阻塞记录 |
| docs/reports/ | 其余分析与交接报告 |
| scripts/py/analysis/ | 分析类脚本 |
| scripts/py/build/ | 构建类脚本 |
| scripts/py/patch/ | 补丁类脚本 |
| scripts/py/oneoff/ | 一次性脚本（下划线开头） |
| scripts/py/misc/ | 其余 Python 脚本 |
| scripts/powershell/ | PowerShell 脚本 |
| scripts/lua/ | Lua 脚本 |
| src/ | C/C++ 源码 |

## 说明

- 不含游戏本体文件（.ifs / .iwd / .ff 等）、压缩包，以及任何受保护的启动基线目录。
- 单文件均小于 5 MB。
