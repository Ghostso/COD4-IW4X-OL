# 进度存档 —— 2026-10-27 剧情模式"战斗开始"调查

## 一、本次调查的完整因果链（已验证）

```
MyEventHandler 缺失（早期根因）
  ↓
0x63B500 建房回调永不触发
  ↓
0x63E510 不执行
  ↓
dwRoomMatchUber 从未创建
  ↓
自动开局状态机 0x63C5E0 永不运行
  ↓
停在"战斗开始"，不连 UDP 28960
```

**关键突破**：`11/13 createRoom` 应答里的 `memberCount`（u32，原值 0）就是这条链的总闸门。
改成 1 之后，`dwRoomMatchUber` 被创建、开局标志置 1。

## 二、今天做了什么（按时间）

| 时间 | 事项 | 结论 |
|---|---|---|
| 上午 | 定位本体 6 秒必崩根因 | `COD OL\iips.ini` 的 `enable_iips=0` ⇒ 改 1 后正常进大厅 |
| 上午 | 排除 ACE / `.local` / TAS | 三者均非崩溃原因 |
| 中午 | 逆向 dvar 表结构与取值 | 名字串 VA 搜指针，对象 `+0x0C` 是值 |
| 中午 | 发现闸门 B / dvar"3291" | `[dwRoomImp+0x10614]` 由 3291 派生，恒 0 |
| 下午 | 发现 `dwRoomMatchUber` 从未创建 | `[0x82E1518]=0` |
| 下午 | 追到 `MyEventHandler` 零实例 | 三条独立证据 |
| 下午 | **A/B 实验：memberCount 0→1** | **成功**：对象从无到有 |
| 傍晚 | 修复转正到正式 kit 并复跑验证 | **成功** |
| 晚间 | 查服务端 dvar 下发通道（NCS） | 3291 不在分发集合内 |

## 三、三项实证成果

### 1. 本体启动修复（已落地）

`COD OL\iips.ini`：`enable_iips=0` → `1`
备份：`iips.ini.bak_before_iips_enable_20261027`
效果：模块数 83→93，`5E8=1→3`，Auth `10→11`，31 个 service 全应答。

### 2. memberCount 修复（已落地并验证）

`CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`
`ob.u32(0)` → `ob.u32(1)`（`11/13 createRoom` 应答）
备份：`lobby_server.py.bak_before_membercount_20261027`（81143 B）

**验证**（`ONCE_20261027_140400` + 转储 `FIXMC_20261027_140146`）：

| 快照 | `[0x82E1518]` | 开局标志 |
|---|---|---|
| snap_001~003 | 0 | 0 |
| **snap_004** | **`0x3B169D98`** | **1** |

对象校验：`vtable=0x00DC795C` ✓、`vtable+0x68=0x0063C5E0` ✓

### 3. 服务端 dvar 下发通道查清（NCS）

`0x00662A50` 构建三张 NCS 表，筛选条件是 **`test byte [dvar+4], 8`**：
- `ncs_codinfo_dvar`（容量 20）
- `ncs_codinfovalue_dvar`（容量 21）
- `ncs_network_dvar`（容量 22）

**三张表均已满额**。`3291` 的 flags = `0x2000`，`& 0x8 == 0` ⇒ **不进网络分发集合**。
所有 `dw_*` 计时器 dvar flags 也是 0，同样不进。

⇒ **"服务端下发"对 3291 这条路是关闭的**，不是没找到入口，是设计上就不包含。

## 四、当前仍卡住的地方（两个独立阻塞点）

```
状态机 [dwRoomMatchUber+0x20] = 1      停在状态 1（需推进到 5 才自动开局）
阻塞1  闸门B = [dwRoomImp+0x10614] = 0  dvar"3291" 派生，恒 0
阻塞2  计时器 [dwRoomMatchUber+0x138]  = 全 0，从未启动
战斗服  _battle_out.txt = 7 行           零收包
```

### 闸门 B 的可用途径盘点

| 途径 | 可行性 |
|---|---|
| 服务端 dvar 下发 | ✗ 刚查明 flags 不含 0x8，不在 NCS 集合 |
| 命令行 `+set 3291 1` | **未验证**（`DVAR_SCRIPT` 是否吃外部赋值未知） |
| GSC 脚本 `setdvar` | 唯一确定的正规途径；官方脚本在 `.ff` 里 |
| 改内存 | ✗ 按纪律不做 |

## 五、下一步（优先级排序）

1. **最便宜、信息量最大**：命令行 `+set 3291 1` 启动一轮，
   看 `[dwRoomImp+0x10614]` 是否变 1。不改代码，一次定性。
   - 变 1 ⇒ 闸门 B 解决，可继续看计时器
   - 不变 ⇒ 确认必须走 GSC 层
2. 无论结果如何，接着要查 **计时器 `+0x138` 的启动者**（谁写它的 count/freq）。
3. 长期：确认 `.ff` 里官方 GSC 是否本来就该设 `3291`。
   若是，说明我们某个前置条件没满足导致那段脚本没跑到。

## 六、基线状态备忘

- 受保护原件 `REF_LOBBY_KIT/lobby_server.py` **完好**（76410 B / `D7EEB456…`）
- 改的是工作 kit `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`
- ⚠️ `REF_LOBBY_KIT/marketplace_store.py` 有**既有偏差**（实际 50022 vs 清单 46226，
  最后修改 2026-10-16），非本次造成，需单独处理
- ⚠️ `--verify-only` 只校验 6 个 launch_core 文件，**不覆盖清单全部 9 项**

## 七、相关产物位置

| 类型 | 路径 |
|---|---|
| 完整因果链 | `docs/GATE_B_INIT_PATH_20261027.md` |
| memberCount 实验 | `docs/AB_MEMBERCOUNT_20261027.md`、`docs/AB_MEMBERCOUNT_RESULT_20261027.md` |
| 修复落地 | `docs/FIX_MEMBERCOUNT_APPLIED_20261027.md` |
| 大厅流量缺口 | `docs/LOBBY_TRAFFIC_GAP_20261027.md` |
| 早期转储工具 | `CODOLServer/_mainline/dump_earliest.py` |
| 最优转储 | `run_codol_001/runs/FIXMC_20261027_140146/`（snap_004 完整 1613MB） |
| 实验 kit | `run_codol_001/kit_membercount1_20261027/` |
