# 15 — 大厅逆向发现（W1 基础图谱）

> 2026-10-29。本条只记**新做的**（053/055 已有的不重复）。
> 工具：`TOOLS/extract_image_from_dump.py`、`TOOLS/vtable_map.py`（都可复跑）。

---

## 1. 关键前置：磁盘上的 EXE 是加壳的，必须用内存镜像

| 事实 | 证据 |
|---|---|
| 磁盘 EXE 仅 7,841,344 B，但 `SizeOfImage` = **0x0E659000 ≈ 230 MB** | pefile 读 `codoMP_client_shipRetail.exe` |
| 全部 7 个节都叫 `.tp3`，虚拟尺寸巨大而 raw 很小（如 `VA=0x00A16000 vsize=0xDBB1CC0 raw=0x62000`） | 同上 |
| 内存镜像里同样 7 个节，但 raw 已等于 vsize ⇒ **代码在内存中才完整** | `client_image_20261027.bin`（241 MB，从 `EARLIEST2_20261027_132645\snap_003.bin` 提取，零字节 85.4%） |

⇒ 任何"在磁盘 EXE 上搜函数/字符串"的做法都不可靠。**本次及以后一律以内存镜像为逆向输入。**

**镜像地址换算：`文件偏移 = VA − 0x400000`**（转储本身则是 `VA − 0x10000`）。

管线已用已知真值复核：
```
0x0062FE80  cmp byte ptr [ecx + 0x10614], 0 / setne al / ret     ← 闸门B（补丁5 把它改成 B0 01 C3）
0x0063C5E0  push ebp … mov ecx,[0x82e13fc] ; call [eax+0x60] ; test al,al ; je 0x63c9cc ; call [eax+0x64]
            ⇒ 自动开局状态机的入口依次调 dwRoomImp 的 vtable+0x60（闸门A）与 +0x64（闸门B）
```

## 2. 类表（新增，机器可读）

- 全镜像 RTTI：**1446 个 TypeDescriptor**（1251 `.?AV` + 195 `.?AU`）
- 解析出 **1368 个类带 vftable、共 1708 个 vftable**（含槽位表）
- 产物：`E:\codol_re\vtables_FULL.json`；大厅子集清单：`RUNS/lobby_classes.txt`

**真值校验（全部命中已知结论）：**

| vftable VA | 类 | 与既有结论 |
|---|---|---|
| 0x00DC7274 | `.?AVdwRoomImp@@` | ✅ 与记忆一致 |
| 0x00DC795C | `.?AVdwRoomMatchUber@@` | ✅ 与 10-27 A/B 一致 |
| **0x00DC78F0** | **未映射** | ✅ 与 056/M1「MyEventHandler 从未实例化、vtable 地址全内存 0 次」互相印证 |

## 3. ★ 找到 UI→后端 的真实入口（055 判"不可达"的那条链）

`UiCppMatchSelectView` 命名空间下有一整组 Scaleform 点击处理器与查询接口，
**这就是"用户点了哪个按钮 → 客户端走哪条流程"的决策点**：

| 类 | vftable | 语义（按名字） |
|---|---|---|
| `OnRootModeClick_SF_Handler` | 0x00DD8470 | 根模式选择（PvE / PvP / 房间 …） |
| `OnPveModeClick_SF_Handler` | 0x00DD847C | **PvE 模式点击** |
| `OnPveMapClick_SF_Handler` | 0x00DD8488 | **PvE 地图点击** |
| `OnPveDifficultyClick_SF_Handler` | 0x00DD8494 | PvE 难度点击 |
| `OnRoomCreateModeClick_SF_Handler` | 0x00DD84C4 | **建房方式点击** |
| `OnRoomFindModeClick_SF_Handler` | 0x00DD84D0 | 找房方式点击 |
| `OnRoomMatchClick_SF_Handler` | 0x00DD84DC | 房间内"开始"点击 |
| `OnRoomTypeClick_SF_Handler` | 0x00DD84A0 | 房间类型点击 |
| `OnPvpMatchClick_SF_Handler` | 0x00DD84B8 | PvP 匹配点击 |
| `AS_CreateRoom` | 0x00DC8904 | UI 调后端"建房" |
| `AS_QuickMatch` | 0x00DC8904 区段 | 快速匹配 |
| `AS_IsInRoom` | 0x00DC8598 | UI 判"是否在房间" |
| `AS_GetRoomInfo` | 0x00DDD7A8 | UI 取房间信息 |
| `AS_ChangeRoomInfo` / `AS_ChangeRoomOptions` | 0x00DDD790 / 0x00DDD79C | UI 改房间设置 |

**为什么重要**：056/M1 实测"用户选剧情任务，客户端仍走 `createRoom`"。
这条链的判定逻辑就在 `OnPveMapClick` / `OnRoomCreateModeClick` / `OnRootModeClick` 的
实现里（它们设置的模式/类型字段最终决定 `mmstart` 里 `2486`/`3265`/`roomChatChannelID` 的取值）。
**这是 W3.5 的第一优先目标。**

## 4. 规模统计（供排期）

| 组 | 类/vftable 数 |
|---|---|
| UI / MatchSelect（`UiCppMatchSelectView` + `AS_*`） | 700 |
| 房间核心（`dwRoom*`） | 100 |
| 房间事件处理器（`*Handler*`） | 204 |
| Party | 34 |
| Lobby/Session/Lsg | 8 |

## 5. 第一次槽位标注（`OnPveMapClick_SF_Handler`）

工具 `TOOLS/vtable_annotate.py`（反汇编某 vftable 的每个槽）。

`OnPveMapClick_SF_Handler` 的 vftable = `0x00DD8488`，**只有 2 个槽**：

| 槽 | 函数 | 形态 |
|---|---|---|
| 0 | `0x00693DD0` | 析构：`mov [esi], 0xdc7ba4`（还原基类 vtable）→ `call 0x826DB0` → 判 `[ebp+8]&1` 决定是否 free |
| 1 | **`0x0073EB60`** | **真正的点击处理器**：`mov eax,[ebp+8]` → `mov eax,[eax+8]` → `mov ecx,[eax+0xC]` → `and ecx,0x8F` → `cmp cl,0xA` ⇒ 读一个**标志字段**并按位比较 |

⇒ 模式/类型判定的形态已现。所有 `*_SF_Handler` 都是这个 2~3 槽的小 vtable 结构，
**逐个反汇编其"处理器槽"即可得到 UI→流程的完整判定表**（这是 W3.5 的机械工作）。

## 6. 尚未做（W1 余项）

- vtable 槽位 → **函数语义**（目前只有地址）：需要逐槽反汇编 + 字符串/调用目标标注
- 交叉引用索引（谁调用/引用某 VA）
- 字符串索引（VA ↔ 协议关键字/错误串）
