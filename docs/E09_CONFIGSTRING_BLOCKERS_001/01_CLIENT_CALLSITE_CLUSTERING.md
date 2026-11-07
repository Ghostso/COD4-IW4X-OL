# 01 — 客户端调用点聚类 / CLIENT CALLSITE CLUSTERING

> 只读静态分析。未启动样本，未注入，未读进程内存。锁定换算：`_tools\pe_helper.py`。
> 等级：`DIRECT`（指令）/ `CROSS`（两侧印证）/ `INFERRED` / `BLOCKED`
> 原始输出：`_data\out_a01..out_a24.txt`

---

## 0. 先修正 E-08 的一处识别错误（重要）

E-08 把 **RVA 0x1A07B0** 当作"客户端共享单比特读取器"。**E-09 复核后修正：它不是网络位读取器。**

| 证据 | 内容 |
|---|---|
| 0x1A07B0 调用 0x1A0660 | 后者把 `"mp/playerdata.def"`（VA 0xCB5D58）与 `"mp/playersecuredata.def"`（VA 0xCB6CB8）**压栈**后调用 0x4CFEE0 |
| 0x1A07B0 是类型分派器 | `call 0x1A0660` → `mov eax,[..]` → `cmp eax,9` → `ja` → `jmp [eax*4 + 0x5A086C]`（**10 项跳转表**） |
| 分派表内容 | case 2 → **LSB-first 单比特读**（`and ecx,7 / shl edx,cl / shr eax,3 / test / setne`）；case 9 → 读 **2 字节**（`movzx byte [+1]`、`shl dx,8`、`or` → 大端 16 位）；case 3/4 → 报错；case 0/1/5/6/7 → 走 `0x633FE0`；case 8 → 走 `0x6340E0`/`0xB50850` |

**结论（DIRECT）：** `0x1A07B0` 是 **`.def` 脚本文件的字段读取器**（按字段类型分派：bit / word / …），**属脚本/`mp/playerdata.def` 数据加载**，**不是**网络 Msg 位流读取器。
→ 其"115 个调用点"**与网络消息分派无关**（此处修正 E-08 `_EVIDENCE_REGISTER` EV-08-03 的解读）。

---

## 1. 定位真正的客户端 Msg 模块

客户端 Msg 模块位于 **RVA 0x1AC000 附近**（与既有 E4 结论一致：`0x1AC1D0` = 字节复制核心）。

在该模块内按"读/写位"形状分类（`_data\out_a09.txt`、`out_a11.txt`、`out_a12.txt`）：

| RVA | 判定 | 依据 |
|---|---|---|
| 0x1AC190 | `MSG_InitReadOnly`（初始化） | 填 `[esi+4]/[esi+0xC]/[esi+0x18]/[esi+0x2C]`，设 `[esi+8]=buf`、`[esi+0x10]=size` |
| **0x1AC1D0** | **`MSG_ReadData(msg,dst,len)`** | `movzx byte [ecx+eax]` 逐字节复制（**无位逻辑**） |
| **0x1AC2B0** | **`MSG_WriteBits(msg,val,bits)`** | `or byte ptr [eax],cl`（**写**）、`[edi+0x20]` 为 bitpos、`and 7` / `sar 3` |
| **0x1AC670** | **`MSG_ReadBits(msg,bits)`** | `movzx byte [eax+ecx]` + `shr eax,cl`（**读**）、`lea ecx,[edx+eax*8]`、`sub edx,8`、`inc eax` |

**关键修正（DIRECT）：** 客户端 `MSG_ReadBits` = **RVA 0x1AC670**（不是 0x1A07B0）。

---

## 2. MSG_ReadBits（0x1AC670）的 126 个调用点

按 64 KB 桶分布（`_data\out_a14.txt`）：

| RVA 桶 | 调用点数 |
|---|---|
| 0x40000–0x4FFFF | 8 |
| 0x60000–0x6FFFF | 5 |
| **0xA0000–0xAFFFF** | **25** |
| 0xB0000–0xBFFFF | 5 |
| 0x1A0000–0x1AFFFF | 83 |

**含义（DIRECT）：** 位读取原语是**全体位流消息的公共原语**；其中 **25 个调用点落在消息解析簇 0xA0000–0xAFFFF** —— **与 `0xA2E50` 同一簇**。

## 3. 按"所在函数"聚类（33 个函数）

`_data\out_a21.txt` 给出全部 33 个含 MSG_ReadBits 调用的函数。重点簇：

| 函数 | 调用数 | 初步归类 |
|---|---|---|
| **0xA2660** | 6 | **Configstring body 读取器**（见 `02`） |
| **0xA2480** | 3 | **A3 定长记录读取器**（10/7/4/n×12） |
| 0xA0D40 / 0xA1290 / 0xA16B0 / 0xA1AE0 | 1–2 | 同簇其它位流消息读取器（候选） |
| 0xAA332 / 0xAAD80 | 9 / 2 | 同簇（另一族） |
| 0x6D5D0 / 0x6E060 | 3 / 2 | 网络消息相关（含 0xA2480 调用） |
| 0x1AD3A0 … 0x1AF4E0（19 个） | 1–24 | 位流读取族（多为快照/状态） |
| 0x4CBC0 / 0x4CD40 / 0xB4EC0 | 2/6/5 | 其他 |

## 4. 三分类结论（任务 A 要求）

### 4.1 已直接定位的 Configstring 消费路径 —— **PROVEN**

```
0xA2660 (configstring body reader)
   ├─ 0x1AC1D0  MSG_ReadData      : 读 count1 = 2 字节          [0xA26B2]
   ├─ 0x1AC670  MSG_ReadBits      : 13-bit 索引 / 11-bit / 10-bit
   ├─ 0xA25F0                     : 单条索引 → 字符串/条目处理    [0xA2751]
   └─ 0xA2480                     : A3 定长记录（10/7/4/n×12）   [0xA28E0]
```

**证据：** 与 2697 服务端 `_CODOL2697_WriteConfigstrings`（RVA 0xA0468）**逐字段两侧对应**（见 `02`、`05`）。
**关键旁证：** 其字符串邻域含 **`EXE_CONFIGSTRINGMISMATCH`**（VA 0xCB835C）、`"* %i"`（0xCB8344）、`"** %i %i"`（0xCB8334），紧跟 `gamestateupdate %d`（0xCB8378）。

### 4.2 仅共享底层位读取原语的候选路径

| 函数 | 依据不足的原因 | 等级 |
|---|---|---|
| 0xA0D40 / 0xA1290 / 0xA16B0 / 0xA1AE0 | 与 configstring 无字段级对应；无法确定消息类型 | **BLOCKED（候选）** |
| 0xAA332 / 0xAAD80 | 同上 | **BLOCKED（候选）** |
| 0x1AD3A0 … 0x1AF4E0（19 个） | 疑为 snapshot/状态读取；未做字段级比对 | **BLOCKED（候选）** |
| 0x6D5D0 | 含 `11-bit`/`10-bit` 双分支，且调用 0xA2480；**形态与 configstring 分支相似但作用对象是 `"* %i"` 格式化输出** | **BLOCKED（候选）** |

### 4.3 无法分类（分派缺失/混淆/证据不足）

| 对象 | 原因 | 等级 |
|---|---|---|
| **读取 `0x04` / `0x06` 外层框架的分派器** | 未定位（`0xA2660` 自身在 0xA2975 直接返回，未见 `0x06` 读取） | **BLOCKED** |
| 客户端 `0x02` reliable 分派 → `0xA2E50` | E-06/E-08 已确认全节 0 调用者 | **BLOCKED**（维持） |
| `.tvm0` 内可能的分派 | 入口对齐率 0%（E-06） | **BLOCKED** |

**纪律声明：** 未找到"读取 0x04/0x06 的框架分派器"**不等于**客户端不支持该协议。仅表示**当前已恢复的 `.text` 中未定位到它**。

## 5. 调用链记录（任务 A 第 6 项要求）

| 候选链 | 入口 | 调用边 | 关键字段操作 | 退出条件 | 等级 |
|---|---|---|---|---|---|
| Configstring body | **0xA2660** | →`0x1AC1D0`(2B) →`0x1AC670`(13b/11b/10b) →`0xA25F0` →`0xA2480`(10/7/4/12b) | `cmp edi,0x1DD7`；`cmp cl,0x14`；`cmp cl,0x12` | `[ebp-0x10c]` 计数递减为 0 → `ret` @0xA2975 | **PROVEN** |
| A3 记录 | 0xA2480 | →`0x1AC670`×3 → 内联 12-bit 读 | `cmp esi,0x3FF`? 内联位读 | 返回填充的记录串 | **PROVEN（作为 0xA2660 子过程）** |
| 0x6D5D0 | 0x6D5D0 | →`0x44C8C0`(类型判定) →`0x1AC670` →`0xA2480` | 11-bit count；10-bit count | `ret` @0x6D676 | **BLOCKED（候选）** |
| 0xAA332 | 0xAA332 | →`0x1AC670`×9 | 未解析 | — | **BLOCKED（候选）** |

## 6. 与 E-08 结论的差异（追加，不覆盖）

| 项 | E-08 | E-09 |
|---|---|---|
| "客户端共享单比特读取器" | **0x1A07B0**（115 调用点） | **修正为 0x1AC670**（126 调用点）；0x1A07B0 实为 `.def` 脚本字段读取器 |
| 客户端 configstring 消费 | `BLOCKED` | **`PROVEN`（0xA2660）** |
| 客户端 Msg 模块位置 | 仅知 0x1AC1D0 | 补全 0x1AC190/0x1AC1D0/0x1AC2B0/0x1AC670 四原语 |

## 7. 结论

| 问题 | 回答 |
|---|---|
| 是否**直接定位**到 Configstring 消费路径？ | **是**（0xA2660，两侧字段级对应） |
| 哪些只是**共享位读取原语**的候选？ | 0xA0D40 / 0xA1290 / 0xA16B0 / 0xA1AE0 / 0xAA332 / 0xAAD80 / 0x1AD* 等（均 `BLOCKED`） |
| 哪些**无法分类**？ | `0x04`/`0x06` 框架分派器；`0x02`→`0xA2E50`；`.tvm0` 内路径 |