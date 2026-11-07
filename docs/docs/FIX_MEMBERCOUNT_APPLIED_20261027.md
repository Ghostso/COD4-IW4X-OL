# 修复落地：memberCount 0 → 1（正式 kit）

**日期**：2026-10-27 14:04
**run**：`run_codol_001/runs/ONCE_20261027_140400`
**转储**：`run_codol_001/runs/FIXMC_20261027_140146`（snap_004 完整）

## 改了什么

`CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py:884`

```diff
- ob.u64(ROOM_ID); ob.u32(0); ob.u32(18); ob.u64(ROOM_SECOND_ID)
+ ob.u64(ROOM_ID); ob.u32(1); ob.u32(18); ob.u64(ROOM_SECOND_ID)
```

只有这一个 `u32` 变化（`11/13 createRoom` 应答里的 memberCount）。
备份：`lobby_server.py.bak_before_membercount_20261027`（81143 B）。

## ★ 修复有效 —— 用正式 kit 复现成功

| 快照 | `[0x82E1518]` dwRoomMatchUber | `[0x849B61C]` 开局标志 |
|---|---|---|
| snap_001 | `0x00000000` | 0 |
| snap_002 | `0x00000000` | 0 |
| snap_003 | `0x00000000` | 0 |
| **snap_004** | **`0x3B169D98`** | **1** |

对象身份校验通过：

```
vtable = 0x00DC795C      ✓ dwRoomMatchUber
vtable+0x68 = 0x0063C5E0 ✓ 自动开局状态机
```

**即：正式 kit 上、不依赖任何实验开关，客户端现在会真正创建房间对象并置「已请求开局」。**

## 但流程仍未打通 —— 两个阻塞点都在

```
状态机 [U+0x20] = 1                    仍停在状态 1
阻塞1 闸门B = [dwRoomImp+0x10614] = 0  （由 dvar "3291" 派生）
阻塞2 计时器 [U+0x138] = 全 0           从未启动
战斗服 _battle_out.txt = 7 行           零收包
```

这两处与此前分析一致，本次修复没有触及它们（也不在本次范围内）。

## 基线完整性

- **受保护原件 `REF_LOBBY_KIT/lobby_server.py` 未被改动**
  （76410 B / sha `D7EEB456…`，与 `_golden_hashes.json` 完全一致）
- 本次改的是**工作 kit** `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`
- `run_frozen_chain_once.py --verify-only` → `protected baseline: OK`

### ⚠️ 一处既有偏差（非本次造成）

`REF_LOBBY_KIT/marketplace_store.py` 实际 50022 B，而 `_golden_hashes.json`
记录 46226 B，**哈希不符**。该文件最后修改时间 `2026-10-16 17:32:51`，
不是今天动的。按 AGENTS.md 的基线规则这属于"链被修改"，但它不影响
IIPS/Auth/Lobby 启动路径（`--verify-only` 的 launch_core 集合不含它），
所以启动校验没拦住。**需要单独处理，不要和本次修复混在一起。**

另注：`_golden_hashes.json` 里 `lobby_server.py` 期望 76410 B，
而工作 kit 那份在我改之前就已是 81143 B（playlist-resolver 那轮改过），
说明工作 kit 与受保护原件本来就不同源。

## 下一步

剩下的两段（闸门 B / 计时器）都是独立阻塞，且目前**都没有找到正规设置途径**：

- 闸门 B 来自 dvar `"3291"`（`DVAR_SCRIPT`, flags `0x2000`），
  正规途径只有 GSC 脚本或服务端 dvar 下发。
- 计时器 `+0x138` 的启动者尚未定位。

按纪律，这两处不能用改内存的方式绕过；应继续找正规途径。
