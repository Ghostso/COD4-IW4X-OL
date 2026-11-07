# ★ A/B 实验结果：memberCount 0 → 1 生效（2026-10-27 13:27）

**run**：`run_codol_001/runs/ONCE_20261027_132700`
**转储**：`run_codol_001/runs/EARLIEST2_20261027_132645`（snap_003/#4 各 1630MB、0 失败块）
**实验 kit**：`run_codol_001/kit_membercount1_20261027`（唯一改动：`11/13` 应答 `ob.u32(0)` → `ob.u32(1)`）

## 实验成立条件全部满足

1. ✅ 转储器拿到**早期句柄**（t+15.39s，handle=0x280），首读 `0x00400000 = 4d5a9000`
2. ✅ 全量快照干净：snap_003 读到 **1630.2 MB、失败块 0**
3. ✅ 日志里确实出现 `11/13 createRoom`（13:27:57）
4. ✅ 工作 kit 确认是实验版：`ob.u32(1)`

## ★ 结果：假设成立，memberCount 就是闸门

**跨快照时间线（同一进程，snap 间隔约 30 秒）**：

| 快照 | 时刻 | `[0x82E1518]` dwRoomMatchUber | `[0x849B61C]` 已请求开局 |
|---|---|---|---|
| snap_001 | t=29s | `0x00000000` | 0 |
| snap_002 | t=61s | `0x00000000` | 0 |
| **snap_003** | **t=89s** | **`0x3ACA0CD8`** | **1** |
| snap_004 | t=118s | `0x3ACA0CD8` | 1 |

同一轮里对象**从无到有**，且「已请求开局」标志从 0 变 1。

### 对象身份已验证

```
[0x82E1518] = 0x3ACA0CD8
  该对象 vtable        = 0x00DC795C   ✓ (dwRoomMatchUber)
  vtable+0x68          = 0x0063C5E0   ✓ (自动开局状态机)
```

⇒ 这确实是 `dwRoomMatchUber` 实例，不是别的类。

### 与上一轮（未改 memberCount）对比

| | 上一轮 `122904`（memberCount=0） | 本轮 `132700`（memberCount=1） |
|---|---|---|
| `[0x82E1518]` | `0`（且全程无建房尝试） | **`0x3ACA0CD8`** |
| `[0x849B61C]` | `0` | **`1`** |
| `11/13 createRoom` | 有（但下游没动） | 有 |
| 自动开局状态机 | 不运行 | **运行，但停在状态 1** |

## 但还没进图：状态机停在状态 1

```
[U+0x20] = 1     ← 状态机的状态字段，停在状态 1
跳表: 1->0x63C7F8  2->0x63C85F  3->0x63C89B  4->0x63C8B8  5->0x63C970(自动开局)
```

**状态 1 的逻辑（`0x0063C7F8`）**：

```asm
0063C7F8  mov  eax, [ebp-4]
0063C7FB  push eax
0063C7FC  mov  eax, esi
0063C7FE  call 0x63C550        ; 判据 A
0063C803  test al, al
0063C805  jne  0x63C86E        ; A 为真 -> 走另一支
0063C807  mov  ecx, [ebp-8]
0063C80A  push ecx
0063C80B  call 0x63C350        ; 判据 B
0063C810  test al, al
0063C812  je   0x63C9CA        ; B 为假 -> 直接返回（当前就是这条）
```

⇒ 当前卡在 `0x63C350` 返回假。

**该对象实测字段**：

```
+0x020 = 1          状态
+0x024 = 0x7852B855
+0x028 = 0x38 (56)
+0x02C = 0x80 (128)
+0x030..0x038 = 0
+0x108 = 0x3B03DBF8  （不是 timer 对象；+0x100..0x10C 看着像别的东西）
+0x120 = 0            （timer，0xB75DA0/0xB75D90 操作的那个）
```

## 结论

**`11/13 createRoom` 应答里的 `memberCount`（u32，原为 0）确实是客户端"是否建房"的判据。**
改成 1 后，客户端从「从未尝试建房」变成「建房成功、状态机启动」。

这是本项目第一次让 `dwRoomMatchUber` 真正出现。

**剩下的一步**：状态机停在状态 1 的 `0x63C350` 判据上。这条已不再是"对象不存在"级别的问题，
而是状态机内部的推进条件——下一轮该解 `0x63C350` 和 `0x63C550` 两个判据。

## 复现方式

```bash
python -I run_codol_001/run_frozen_chain_once.py --authorize-next-launch
python -I run_codol_001/run_frozen_chain_once.py \
        --kit run_codol_001/kit_membercount1_20261027 \
        --seconds 200 --out chain_mc2.txt
```

转储用 `CODOLServer/_mainline/dump_earliest.py <outdir> 200 6`，经提权 agent 运行。

相关：[[codol-myhandler-never-created-root-cause]]、[[codol-dwroommatchuber-never-created]]
