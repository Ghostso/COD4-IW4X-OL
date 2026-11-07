# CODOL-ISSUE-0066 — 武器定义运行时布局未验证，WeaponAttach 545 条字符串记录不可消费

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

旧候选 +0xBB4/+0xBCC/+0xBF0 已被 zone 对拍否定；+0x810..+0x824/+0xAC0 未验证。WeaponAttach 545 条 string/resource 记录被跳过，168 个资产共享槽无法解析。标量覆盖率有两套数字（172/879 vs 94 记录/44 资产）。

## 2. 历史首次发现过程

- **首次发现**：2026-10-23（`docs/PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md`）
- **最近验证**：2026-10-23
- **所属系统**：`combat`　**优先级**：P2　**登记状态**：`UNVERIFIED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-23 | PHASE7 记录否定与未验证项 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0066-01 | source | `battle/weapondefs.c` | 11-55 | 武器表查找 | — |
| EV-0066-02 | source | `battle/weaponattach.c` | 74-78 | 附件应用（只处理标量） | — |
| EV-0066-03 | location | `CODOL_SERVER_319_20261021/docs/PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md` | — |  | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/weapondefs.c` | 11-55 | 武器表查找 |
| `battle/weaponattach.c` | 74-78 | 附件应用（只处理标量） |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `CODOL_SERVER_319_20261021/docs/PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md` | — |  |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0066，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0066，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
zone 武器表 → weapondefs.c → 运行时结构
```

## 10. 第一条未闭合调用边

**运行时 WeaponDef 布局证据。**

## 11. 已确认事实

- 旧候选被否定
- 标量可用

## 12. 尚未确认的假设

- 运行时布局
- 545 条字符串记录

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

只处理标量。

## 16. 最小复现条件

用 probe 读一份真实 WeaponDef。

## 17. 最小验证实验

**实验 B66**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 对照 zone 里的武器表与运行时结构<br>2. 定位 +0x810..+0x824 |
| 通过判据 | 字段与值能对上 |
| 失败判据 | 仍对不上 |
| 成本 | 离线数小时 |

## 18. 条件式修复方案

**方案A：先定布局，再谈附件。**

**方案B：只用已验证的标量。**

## 19. 修改影响分析

配件效果不完整。

## 20. 可测量的验收标准

1. WeaponDef 关键字段有 3.19 实测值。

## 21. 回归测试方案

test_weapondefs 增加布局断言。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B66：运行时 WeaponDef 读取。
- **上游依赖**：`CODOL-ISSUE-0029`

---