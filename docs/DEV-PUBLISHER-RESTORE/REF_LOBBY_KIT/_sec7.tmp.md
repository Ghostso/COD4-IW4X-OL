
---

## 7. ★★ 快照字段语义对齐（2026-10-07，含一次自我纠错）

### 7.1 纠错：基准用错了

上一版我拿 `reference/demo-player-fields-trace.json` 当基准，得出：

> "真实快照只有 140 bit / 32 字段，我们 984 bit，序列差很多。"

**这个结论是错的。** 那份文件自己写着：

```
scope  = offline position branch trace; ... not live packet validation
error  = RuntimeError('Unclassified call 0xc42d81')     <- 解到一半就抛了
```

它**残缺**。正确基准是同一目录下的：

```
playerstate-motion-trace.json
  completed = True          <- 完整
  totalBits = 497
  reads     = 173
  带完整语义 origin / viewAngles / velocity / clips / reserve / owned /
             events / weaponTime / weaponState / weaponDelay / gravity / ...
```

### 7.2 换成正确基准后的真实结论

把 trace 的 `reads` 按 index-skip 位流解出来（`snapshot_diff.py` 的
`decode_index_sequence`），真实字段序列是：

```
[0, 1, 3, 8, 10, 11, 13, 14, 17, 18, 19, 20,
 21, 22, 23, 24, 29, 34, 38, 39, 41, 44, 54, 56, 60, 61, 63, 68, 84]
```

我方：

```
[0, 1, 3, 8, 10, 11, 13, 14, 17, 18, 19, 20,
 29, 34, 38, 39, 41, 44, 45, 54, 56, 60, 61, 63, 68, 219]
```

**24 / 29 个字段完全对上，且顺序一致。** 我们的快照结构基本是对的 ——
之前"差很多"是**基准残缺**造成的误判。

### 7.3 唯一的真缺陷：idx 21..24 语义错位（已修）

实录解码 idx 21..24 的读值：

```
idx=21  (1,1)(1,1)(11, 1157)   <- 槽0: 武器 1157
idx=22  (1,1)                  <- 槽1: 无
idx=23  (1,1)(1,1)(11, 0)
idx=24  (1,1)(1,1)(11, 0)(1,0)
```

与 metadata 完全吻合：`clips=[[1157,35,0],[1158,15,0],[0,0,0]]`、
`owned=[1157,1158,317]`、`weapon=1157`。

=> 这四个字段是**武器槽**。而旧代码往这里写的是 `eq.events[i]`（事件号），
客户端会把**事件号当成武器 id** 解释 —— 语义错位。

**已改**（`battle_server.py` `_build_motion_snapshot`）：idx 21..24 改写成
"present 位 + 有值位 + 11 bit 武器 id"，形状逐位取自实录。
回退开关：`slot_events_legacy.on`（存在时回到旧的事件数组写法）。

### 7.4 idx 84 = 武器/弹药表的完整规格

`idx=84` 解出来是一整段结构化数据，与 metadata 对得上：

```
(4,15)x8 ...                       <- 已拥有武器表尾部填充
(17, 5)                            <- clips 计数 = 5
per-slot: (4,i)(11,weapon)(1,1)(9,clip)(1,0) ...
per-slot: (4,i)(11,ammo_key)(12,reserve) ...
```

这正是我方 `_build_motion_snapshot` 末尾 `guns` 循环的对应物。

### 7.5 当前状态

* `battle_selftest.py` **12 步全绿**，新增第 ⑫ 步作为语义回归护栏
  （已用"注入回归 -> 必须报 FAIL"验证过它真的会抓）。
* `snapshot_diff.py` 基准已换成 motion-trace，并打印差异清单。

### 7.6 下一步

```
① idx 219：真实序列里没有 -> 确认是否该删
② idx 45 ：默认关，保持关（实测写进去会让视角乱转）
③ idx 84 的完整编码与本方 guns 循环逐位 diff
④ 改完后**真机验证**（大厅断连已修，现在跑得通了）
```

> **教训（第二次同类）**：素材要**先看 `completed` / `error` / `scope` 再当基准**。
> 残缺的 trace 会给出**看起来很像**但完全错误的差异清单。
