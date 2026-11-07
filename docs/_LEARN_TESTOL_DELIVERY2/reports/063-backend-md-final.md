# 学习报告 063（重开）— `backend.md` 收尾（profile / 角色 / 日志）

**学习范围**：`source\.agents\modules\backend.md` 第 120–133 行（文件结束）
**性质**：全实测
**★★★ 本报告收录**两个精确的时序 bug**与**永久物品的 `UINT32_MAX` sentinel**

---

## 一、★★★★ `backend.md` 的完整规模

| 项 | 值 |
|---|---|
| 总行数 | **133** |
| 字节数 | **19,203** |
| 平均每行 | **144 字节** |

### ★★★ 完整的章节结构

```
1. 责任                              （第 3–9 行）
2. 玩家身份配置                      （第 11–21 行）
3. Ready 到 Booking                  （第 23–51 行）
4. 多客户端共享 room/session 边界    （第 53–109 行）
5. 资产和持久化                      （第 111–133 行）
```

★ **⇒ 五节，**身份/链路/多客户端/资产**三块与我们最相关。**

---

## 二、★★★★★ 永久物品的 `UINT32_MAX` sentinel（第 120 行）

```markdown
2026-08-07 的持久库存复核确认磁盘 `Inventory.json` 与 Marketplace task `203`
均可返回全部 `115` 项。归档中的永久物品以 `expireDateTime=UINT32_MAX` 表示；
其 JSON `expiryDuration` 经过十进制序列化后可能舍入到略大于 `INT64_MAX`，
handler 只对这一永久 sentinel 归一化为 `INT64_MAX`，限时物品的越界 duration 仍严格拒绝。
```

### ★★★★★ 一个精确的数值陷阱

```
永久物品：
  expireDateTime = UINT32_MAX  （0xFFFFFFFF = 4,294,967,295）
        ↓
JSON 的 expiryDuration 经十进制序列化
        ↓
★★★ 可能舍入到**略大于 `INT64_MAX`**（9,223,372,036,854,775,807）
        ↓
handler **只对这一永久 sentinel** 归一化为 `INT64_MAX`
        ↓
★ 限时物品的越界 duration 仍**严格拒绝**
```

★★★ **⇒ 这是**浮点/十进制序列化的精度陷阱**：**
```
UINT32_MAX (4.29e9) 转成某个更大的时间单位（如纳秒）
        ↓
4.29e9 × 2.1e9 ≈ 9.2e18 ⇒ 接近 INT64_MAX (9.22e18)
        ↓
★★★ **十进制舍入会超出 INT64_MAX**
```

★ **⇒ 解法：只对**这一个特定值**做归一化，其余严格拒绝。**

★★ **⇒ 这与 `nt10.py` 的 `apply_patches`"不猜"原则**一致**。**

---

## 三、★★★★★ 第一个时序 bug：profile 被清空（第 122 行）

### 3.1 ★★★ 完整的失败链（逐字）

```markdown
同日 clean launch 定位了 profile 被清空的真实时序：
task `203` response 已携带 115 个对象，
但旧 hook 在原生 `CODOL_Marketplace_OnInventoryComplete` 已消费任务后
再次读取 `bdRemoteTask +0x24`，得到清理后的 `0`，
并重复调用 `CODOL_Marketplace_FinalizeInventory(1, 0)`。
客户端下载原始 1982-byte profile 后因此按空库存 repair，
并通过 Profiles2 `8/3` 上传 1943-byte 替代文件；
上传 payload 与磁盘文件逐字节、SHA-256 完全一致。
```

### ★★★★★ 完整的因果链

```
task 203 response 携带 115 个对象  ✓
        ↓
旧 hook 在原生 `CODOL_Marketplace_OnInventoryComplete` **已消费任务后**
再次读取 `bdRemoteTask +0x24`
        ↓
★★★ 得到**清理后的 `0`**
        ↓
重复调用 `CODOL_Marketplace_FinalizeInventory(1, 0)`
        ↓
客户端按**空库存** repair
        ↓
通过 Profiles2 `8/3` 上传 **1943 字节**替代文件
        ↓
★ 原始 profile 是 **1982 字节** ⇒ **被 1943 字节覆盖**
```

### ★★★★★ 四个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | 原始 profile | **1,982 字节** |
| **2** | 上传替代文件 | **1,943 字节** |
| **3** | task 203 对象数 | **115** |
| **4** | 关键字段 | **`bdRemoteTask +0x24`** |

### 3.2 ★★★ 修复方式（第 122 行）

```markdown
当前实现不再 hook `bdMarketplace_StartGetInventory` 或重复 finalizer，
而是在原生 `CODOL_Marketplace_FinalizeInventory` 返回后
只记录 completion 并放行 profile 下载。
```

★★★ **⇒ 修复原则：**不再干预，只在原生完成后记录**。**

★★ **⇒ 且验证：**
```
clean PID 16296：task 203 原生完成 115 objects
        ↓
随后才请求 Profiles2 `8/1`
        ↓
★ 有界捕获内**没有** `8/3`
        ↓
恢复的 1,982-byte profile 保持 `DC9AAE6...D4464B`
```

★★ **⇒ 关键：**没有 `8/3` 上传 = profile 没被覆盖**。**

---

## 四、★★★★★ 第二个时序 bug：角色从 3 变 0（第 126 行）

### 4.1 ★★★ 完整的失败链（逐字）

```markdown
此前 clean restart 从 CRC 有效的 character `3` 恢复成 `0`，
不是 entitlement 或磁盘 profile repair。
启动约 `4.8s` 时 UI 在 profile 尚空时调用 `CODOL_CurrentCharacter_GetIndex 0x68A0E0`，
把 `0xCD7E3C` 的 lazy cache 从 `-1` 锁为 `0`；
约 `13.2s` 后 profile 与 inventory 已完整，后续 character init 仍复用旧 cache。
```

### ★★★★★ 完整的时序图

```
t ≈ 4.8 s   UI 在 profile 尚空时调用 `CODOL_CurrentCharacter_GetIndex 0x68A0E0`
        ↓
★★★ 把 `0xCD7E3C` 的 **lazy cache 从 `-1` 锁为 `0`**
        ↓
t ≈ 13.2 s  profile 与 inventory 已完整
        ↓
★★★ 后续 character init **仍复用旧 cache（0）**
        ↓
★ 角色从 **3** 变成 **0**
```

### ★★★ 两个精确时刻 + 两个地址

| # | 项 | 值 |
|---|---|---|
| **1** | 过早调用时刻 | **t ≈ 4.8 s** |
| **2** | profile 完整时刻 | **t ≈ 13.2 s** |
| **3** | 函数 | **`CODOL_CurrentCharacter_GetIndex 0x68A0E0`** |
| **4** | ★★★ **lazy cache 地址** | **`0xCD7E3C`** |
| **5** | cache 初值 | **`-1`** |
| **6** | 错误锁定的值 | **`0`** |

### 4.2 ★★★ 修复方式（第 126 行）

```markdown
backend 现在只在 `public + download + succeeded + errorCode 0` 的原生 profile completion
返回后把该 cache 恢复为 `-1`。
```

★★★ **⇒ 四个精确的完成条件：**
```
public + download + succeeded + errorCode 0
        ↓
把 cache **恢复为 `-1`**
```

★★ **⇒ 验证：**
```
clean PID 31148 未传角色参数
        ↓
自然读回 `current_character_index=3` ✓
        ↓
booking loadout 为 `current/prepared/registered=3`
        ↓
mask **`31/31`**
```

★ **⇒ 与报告 062 的 `mask 31`**完全吻合**。**

---

## 五、★★★ 角色选择的**两条路径**（第 124 行）

```markdown
角色选择与跨重启恢复也已在同日闭环。
`0x68C580` 的唯一 caller `0x5F01A0` 属于 onboarding，
除选择角色外还写 `onboardCharacterID` 和 telemetry；
普通 Scaleform 入口 `CL_SetDefaultCharacter/CL_SetCurrentCharacterID 0x69C850`
转入 `CODOL_CurrentCharacter_SelectItem 0x689FF0`，以 `EDI=itemId` 查找或创建 character slot、
更新 `currentCharacterIndex`、flush Publicprofile 并刷新角色表现，不写 onboarding 状态。
```

### ★★★★★ 两条路径的精确对比

| 项 | Onboarding 路径 | ★ 普通路径 |
|---|---|---|
| **入口** | **`0x68C580`**（唯一 caller `0x5F01A0`） | **`CL_SetDefaultCharacter/CL_SetCurrentCharacterID 0x69C850`** |
| **下游** | — | **`CODOL_CurrentCharacter_SelectItem 0x689FF0`** |
| **参数** | — | **`EDI = itemId`** |
| ★ **副作用** | **写 `onboardCharacterID` + telemetry** | **不写 onboarding 状态** |

★★★ **⇒ 关键区别：**
```
Onboarding 路径  ⇒  写 onboardCharacterID + telemetry  （★ 有副作用）
普通路径         ⇒  只更新 currentCharacterIndex + flush Publicprofile
```

★★ **⇒ 所以 `CodolMatchFlow.py --character-index` **改走普通路径**。**

---

## 六、★★★ 稳定 handler 的**验收标准**（第 130 行，逐字）

```markdown
稳定 handler 必须有 byte fixture、语义测试或归档 oracle 对比；
只收到 success reply 不代表 side effect 已恢复。
```

★★★ **⇒ 一句极其重要的验收原则：**
```
★ **只收到 success reply 不代表 side effect 已恢复**
        ↓
必须有：
  ① byte fixture
  ② 语义测试
  ③ 归档 oracle 对比
```

★★ **⇒ 这是**全项目最核心的验收哲学**（与报告 057 的"九项验收"一致）。**

---

## 七、★★★★ 日志规范（第 132 行）

```markdown
backend 日志统一通过 `src/shared/RuntimeLog` 写入
`Ayria/Logs/AlwaysofflineRe.Localnet32.log`；
`OLMOD_CONSOLE_LOG=1` 时同步到当前 client/combined 进程的控制台。
Storage2 下载与上传只记录文件名、owner、字节数和结果，不输出文件内容或逐 packet 数据。
```

### ★★★★★ 三个规范

| # | 规范 | 内容 |
|---|---|---|
| **1** | 统一入口 | **`src/shared/RuntimeLog`** |
| **2** | 文件路径 | **`Ayria/Logs/AlwaysofflineRe.Localnet32.log`**（★ 带 `Re`） |
| **3** | ★★ Storage2 的隐私约束 | **只记文件名/owner/字节数/结果**，**不输出文件内容或逐 packet 数据** |

★★★ **⇒ 第 3 条是**重要的隐私设计**：**
```
Storage2 下载/上传
        ↓
只记录：文件名 / owner / 字节数 / 结果
        ↓
★★★ **不输出文件内容，不输出逐 packet 数据**
```

★ **⇒ 这解释了为什么 `nt10.py` 的 timeline 只打印"新串"和"目标地址"而不打印完整包内容。**

★★ **⇒ 且日志路径**带 `Re`**（`AlwaysofflineRe.Localnet32.log`）——**
**与 `launch_chain.py:436` 的路径**完全一致**（报告 019）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★ `backend.md` 规模 | **133 行 / 19,203 B** |
| 2 | ★★★ 永久物品 sentinel | **`expireDateTime = UINT32_MAX`** |
| 3 | ★★★ 精度陷阱 | JSON `expiryDuration` **可能舍入到略大于 `INT64_MAX`** |
| 4 | ★ 归一化 | **只对永久 sentinel** ⇒ `INT64_MAX`；其余严格拒绝 |
| 5 | 库存项数 | **115** |
| 6 | ★★★★★ **bug 1：profile 被清空** | 旧 hook 在**已消费后**读 `bdRemoteTask +0x24` ⇒ **`0`** |
| 7 | bug 1 后果 | 重复 `FinalizeInventory(1, 0)` ⇒ 按**空库存** repair ⇒ 上传 **1,943** 字节 |
| 8 | bug 1 原始值 | **1,982 字节**（`DC9AAE6...D4464B`） |
| 9 | ★ 修复 | **不再 hook**，只在原生完成后记录 |
| 10 | ★★★★★ **bug 2：角色 3→0** | **t≈4.8s** 时 profile 尚空 ⇒ cache `0xCD7E3C` 从 **`-1` 锁为 `0`** |
| 11 | bug 2 后果 | **t≈13.2s** profile 完整但**仍复用旧 cache** |
| 12 | ★ 修复条件 | **`public + download + succeeded + errorCode 0`** ⇒ 恢复为 **`-1`** |
| 13 | ★★ 两条角色路径 | **onboarding `0x68C580`**（有副作用）/ **普通 `0x69C850`** |
| 14 | 普通路径下游 | **`CODOL_CurrentCharacter_SelectItem 0x689FF0`**，`EDI=itemId` |
| 15 | ★★★★ **验收原则** | **"只收到 success reply 不代表 side effect 已恢复"** |
| 16 | ★ 日志入口 | **`src/shared/RuntimeLog`** |
| 17 | 日志路径 | **`Ayria/Logs/AlwaysofflineRe.Localnet32.log`**（带 `Re`） |
| 18 | ★★ 隐私约束 | Storage2 **不输出文件内容或逐 packet 数据** |

---

## 九、结论

### 1. ★★★★★ **两个精确的时序 bug** 都源于**过早读取**

```
bug 1：在任务**已消费后**读 bdRemoteTask+0x24 ⇒ 得到 0
bug 2：在 profile **尚空时**读 GetIndex ⇒ cache 被锁为 0
        ↓
★★★ 共同模式：**读得太早/太晚 ⇒ 拿到过期状态**
```

### 2. ★★★★★ **"只收到 success reply 不代表 side effect 已恢复"** 是核心验收哲学

### 3. ★★★ **`UINT32_MAX` → `INT64_MAX` 的精度陷阱**只对 sentinel 归一化

### 4. ★★★ **两条角色路径必须区分**（onboarding 有副作用）

### 5. ★★ **Storage2 不输出文件内容和逐 packet 数据**（隐私设计）

---

## 十、`source\.agents\modules\` 的学习进度

| 文档 | 字节 | 状态 |
|---|---|---|
| `runtime.md` | 48,090 | ✓ **完成（报告 058–061）** |
| **`backend.md`** | **19,203** | ✓ **完成（报告 062–063）** |
| **`game_server.md`** | **223,587** | ★ **待学（最大）** |
| `game_server_coverage.md` | 21,180 | 待学 |
| `gsc.md` | 21,617 | 待学 |
| `reverse_engineering.md` | 89,517 | 待学 |

---

## 十一、下一步

- `source\.agents\modules\game_server.md`（**223,587 B**，最大文档）
- `source\.agents\modules\gsc.md`（21,617 B）
- `source\.agents\modules\reverse_engineering.md`（89,517 B）
- `source\docs\devlog\`（中文开发历程）
