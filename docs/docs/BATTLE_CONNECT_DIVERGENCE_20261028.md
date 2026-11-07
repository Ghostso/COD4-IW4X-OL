# 战斗服连不上的真正分水岭：102/7 回包（2026-10-28 第十九轮）

## 一、数据：只有一种 mmstart 形态能连上

对全部 57 轮 run 做相关性统计（`tools/correlate_mmstart_battle.py`）：

| mmstart 形态 | 轮数 | 战斗服有事件 |
|---|---|---|
| **A：带 `g_gametype`** | 25 | **8** |
| B：带 `playlist 37` | 8 | 0 |
| none | 24 | 0 |

**8 轮成功全部在 2026-10-26。** 10-27 之后即使有 A 形态也全灭。

## 二、10-26 成功轮 vs 10-27 失败轮的 kit 差异

`tools/diff_ok_vs_bad_kit.py`：

```
只在成功轮: _authobj_*.bin, keymap_cal.csv
只在失败轮: _authobj_*.bin, task_params.txt
lobby_server.py: 78206 B -> 82089 B   ← 关键
```

`lobby_server.py` 的实际代码差异只有两处（非注释）：

### 差异 1：`11/13` 的 memberCount

```python
# 成功轮
ob.u64(ROOM_ID); ob.u32(0); ob.u32(18); ob.u64(ROOM_SECOND_ID)
# 失败轮（10-27 改动）
ob.u64(ROOM_ID); ob.u32(1); ob.u32(18); ob.u64(ROOM_SECOND_ID)
```

### 差异 2：新增 `102/7` 处理（★ 关键）

```python
# 成功轮：没有这段 —— 102/7 落入 UNMAPPED，回空 ACK
# 失败轮：新增
if service == 0x66:
    if task == 7:
        ...
        return 回显 50 个字段，值全填 0
```

日志对照：

```
ONCE_20261026_220815 : （无 102/7 记录，走 UNMAPPED）
ONCE_20261027_140400 : -> storage 102/7 ★ 回显 50/50 个字段(值=0) 555B
```

## 三、判断

`102/7` 是 **playerdata 字段批量读**。字段表注释写明索引 `[44..49]` 是：

```
currentMatchSelectPVEDifficulty / PVEMap / PVEMode /
PVPMatch / PVPMode / RootIndex
```

**把 50 个字段全部回 0，等于告诉客户端"你什么都没选"** ——
PvE 关卡、PvP 模式、根索引全被清零。

⇒ 这很可能就是 10-27 之后客户端不再连战斗服的原因。

## 四、`mmstart` 推 StartGame 是 10-28 才加的

对比 10-27 失败版与当前版：

- 10-27 失败版：`mmstart` 分支只记日志，**只回空应答**（第 1018 行同文案）
- 10-28 当前版：额外推 109 B 的 `dwRoomMessageStartGame`

⇒ 这条不是 10-27 失败的原因，但**可能**是 10-28 各轮仍失败的原因之一
（成功版从不在这一步推任何东西）。

## 五、下一步实验（最小改动）

回到 10-26 成功配置，只做一件事：

1. **`mmstart` 不推 StartGame**（恢复"仅空应答"）
2. **`102/7` 恢复为不处理**（回空 ACK，与成功轮一致）
3. `memberCount` 保留 1（这是 10-27 的成果，与连服无关）

然后跑一轮，看战斗服是否收包。

若成功 ⇒ 确认是 102/7 或 StartGame 打断；
再单独放开其中一个做二分。

## 六、工具

```
tools/correlate_mmstart_battle.py    mmstart 形态 × 战斗服事件相关性（★ 本轮关键）
tools/diff_ok_vs_bad_kit.py          成功/失败 kit 逐文件对比
tools/analyze_service6.py            service=6 各 task payload
tools/dump_all_mm_commands.py        mmstart/mmbook 命令全文
```
