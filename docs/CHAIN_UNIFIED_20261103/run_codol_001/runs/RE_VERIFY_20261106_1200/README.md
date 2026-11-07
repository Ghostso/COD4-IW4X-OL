# RE_VERIFY — 以原版行为为对照的回归校验机制

> 大型游戏复原可拆成大量独立函数任务，再通过依赖图组织关系、并以原版行为为对照建立
> 严格的自动化回归验证机制持续推进。（GPT-6A）

本目录就是这条原则的**可执行落地**：把 3.19 客户端逆向出来的每条结论，变成一条
**函数级、可机械复核**的断言，对照物只有一个 —— 原版二进制。

## 对照物

```
run_codol_001/runs/UNPACKED_146/codoMP_unpacked_146.exe
  PE TimeDateStamp = 1620480778 (2021-05-08)，与实跑客户端同源
  sha256 记在 _baseline.json 的 bin_sha256 字段
```
**二进制一旦变化，`check` 立刻报 `!! 二进制已变`** —— 防止"换了反汇编件却以为结论仍成立"。

## 三条命令

```powershell
python -I verify.py baseline   # ① 首次：采集全部观测值 → _baseline.json
python -I verify.py check      # ② 之后每次：绝对断言 + baseline 比对，任何变化都算回归
python -I verify.py graph      # ③ 打印依赖图与未闭项（同时校验：已闭任务不得依赖未闭、不得成环）
```
退出码：`0` 全通过 / `1` 有断言失败或回归 / `2` 依赖图不合法。
人读报告写在 `out/<mode>.txt`（UTF-8；控制台输出已转 ASCII 安全，避免 GBK 报错）。

## 断言种类

| kind | 含义 | 用途 |
|---|---|---|
| `insn` / `seq` | 在 VA 处**反汇编**并与期望文本比对（语义，非字节） | 指令级结论 |
| `bytes` / `str` | VA 处原始字节 / NUL 结尾字符串 | 常量、字面量 |
| `u32` / `ptru32` | VA 处 dword / 解引用后的 dword | vtable 槽、全局指针 |
| `calls` | 目标函数的全部 `E8` 调用点（可 `"subset": true` 只要求包含） | "唯一调用点""无调用点" |
| `callcount` | 调用点数量 | 结构回归（如 TaskBuilder 88 个调用点） |
| `xrefs` | 可执行段内逐字节出现该 4 字节值的位置 | "全客户端只此一处读取" |
| `vtslot` | 函数指针落在哪些数据段位置 | vtable 归属 |
| `noxref` | 断言无 `E8` 调用点 | 纯回调（经 vtable） |

## 为什么用 `discover.py` 而不是手抄

第一版任务表是我手抄地址/编码的，`baseline` 一次就抓出 **30+ 处转写错误**
（地址偏 1–8 字节、`ret` 写成 `ret n`、十六进制里多余空格、把四个不同全局的
四处 xref 误当成同一个值的四处……）。
因此加了 `discover.py`：给定 (近似地址, 期望指令文本)，在 ±32 字节窗口内反汇编并
定位**真实**指令，输出 `found.json`；任务表由它生成，不再靠人眼。

```powershell
python -I discover.py claims.json found.json
```

## 结构

```
verify.py        校验器（自带 PE 解析，不依赖外部工具目录）
discover.py      指令定位器（生成任务表用）
tasks.json       任务表 + 依赖图（42 条：39 已闭 / 3 未闭）
claims.json      第一批定位输入
claims2/3.json   第二、三批定位输入
_baseline.json   观测基线（含二进制 sha256）
out/             人读报告
```

## 依赖图的组织方式

任务按组串成链，闭环才可对外使用：

```
envelope   E1 → E2 → E3
                 └ E4, E5
svc-table  S1 → S2/S3/S4/S5/S6
security   K1 → K2(S4)
injection  I1 → I2 → {I3 → I4 → I5, A5}
                    └ J1 → J2 → J3 → J4 → (0xBBDE10 ACK 闸门)
mmrsv      A1 → A2 → A3 → A4
S-object   M1 → {M2, M3, M4}
task-fw    P1 → P3 ; P2
room       R1, R2 → R3, R4
open       O1, O2, O3        ← 未闭；已闭任务**不得**依赖它们（图校验强制）
```

## 当前状态

```
任务 51 条：断言全过 51，失败 0
baseline 比对：0 处差异
依赖图：合法
=> 全部通过

==== 未闭清单 (12 条) ====      ← check/baseline 每次都打印，Running 报告亦写入 out/<mode>.txt
```

### 未闭 12 条（含缺口）

| ID | 内容 | 缺口 |
|---|---|---|
| O1 | 谁触发 `S` 的入站反序列化 | 经 vtable 派发；需定位派发器（候选 `0xB838A0→0xB7B300→slot[6]→0x7E7C90`） |
| O2 | `0x47` 其余任务的 builder 与应答体 | svc=0x47 共 12 任务，已定 1/2/4 |
| O3 | `0x622A80` 逐字段读序 | 读原语语义已知，字段顺序未写死 |
| O4 | `0xB79360` 传输对象类与 `vt[+4]` 本体 | `this=[srpc+4]` 已定；`[this+0x44]` 的类未定 |
| O5 | `21/1` 应答目标 `singleton+0x258` 期待形状 | 该类已知，schema 未定 |
| O6 | `0x47/4` 的 16 字节服务端侧去向 | 上行源已证；消费侧在源码不在二进制 |
| O7 | 谁把 RPC poll 从 1 推到 4 | 完成派发路径未定位 |
| O8 | `[+0x105FD]`/`[+0x105FE]` 语义 | 来源已证，含义未定 |
| O9 | `0x770940` 参数语义 | 注册器已识别，arg2/arg4 未定 |
| O10 | **服务端**：`0x47/2` 应回 true | 结构已对、极性错，未改未验 |
| O11 | **服务端**：`21/1` 应答体形状 | 现 8B blob vs 客户端发的整个 `S` |
| O12 | `0xDB6B68` 是否即战斗服 securityKey | 未与 `battle.c` KDF 对账、未实机 |

### 防"做了一个忘了一个"的机制

1. **未闭项只住在 `tasks.json`**，散文里不留唯一副本；每条带 `blocked_on`（缺什么证据）。
2. `check`/`baseline` **每次都打印未闭清单**。
3. `check` 与上次未闭集合对比：闭掉的标 `本次闭掉`，新增的标
   `⚠ 本次新增未闭（必须确认不是把旧项丢了）`。
4. `graph` 强制：**已闭任务不得依赖未闭任务**、不得成环。
5. ★ **重复 id 检查**（`verify.py` 内置）：`tasks` 是 dict，重复 id 会**静默覆盖**前者
   ⇒ 等于把旧项弄丢。一旦出现，`check`/`graph` 直接失败并报 `重复 id: Ox 出现 N 次`。
   （2026-11-06 审计时真的抓到过一对重复的 `O4`，已修。）
6. ★ **`OPEN_INVENTORY.md`**：把 `memory\*.md` 里**每一处** 未闭/缺口/待办/尚未/未定
   的原文按 `文件:行号` 抓成清单（生成器 `inv.py`）。用途：`tasks.json` 只覆盖已重新推导
   并建成断言的条目，**其余仍有 176 处散落在 72 个 memory 文件里** —— 转成正式任务时
   在 `tasks.json` 增条目并在清单那一行标注 `[已转 Gx/Oxx]`。

### 审计记录（2026-11-06）

- `O4` 曾重复（旧的开着的 + 新的已闭的），dict 静默覆盖；已删除旧副本
  （它还带着一句被推翻的"实机 6/14 发得出去"）。现已加自动检查。
- 从 memory 回收旧开项：**279 卷 §54 的 4 条**已入表 —— 1/2 闭为 `G10`，3/4 闭为 `O15`；
  **279 卷的 0x6F37E0/0x6F381B** 闭为 `G11`。

### ★ backlog：把散文项变成可推进的账本（2026-11-06）

```powershell
python -I backlog.py                 # 重扫 memory + 统计 + 本次新增/消失
python -I backlog.py list --open     # 列出待处理项（带 key）
python -I backlog.py close <key> 备注   # 标记已处理
python -I backlog.py reopen <key>
python -I sweep_backlog.py           # 把被 tasks.json 已闭任务覆盖的批量标掉
```

- `key = sha1(文件名|原文)[:12]`，**与行号无关** ⇒ 文件加几行不会让状态错位。
- 关键告警：`⚠ 本次消失 N 条（原文被改写/删除 —— 确认不是把旧项丢了）`。
- 现状：**176 条散文项 / 已处理 20 / 待处理 156**。
- 两套账并行的分工：
  - `tasks.json`（70 条）= **已重新推导并建成可机械复核断言**的结论；
  - `backlog.json` = **尚未推导成断言的散文线索**，按文件分批推进。



