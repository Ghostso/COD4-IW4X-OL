# Phase 3 收口：Snapshot Codec（2026-10-23）

状态：`DONE`（首帧黄金向量字节级一致）

## 1. 验收基线

基线文件：

`CODOL-Combat-Server-v0.1/tests/golden_first_snapshot.hex`

基线参数：

```text
ack=0
serverTime=1000
commandTime=1000
first=true
x=48 y=-572 z=-116
pitch=yaw=roll=0
vx=vy=0
aimFraction=0
aiming=false
默认装备：M4A1 1156
```

## 2. 已实现

Python codec：

`tools/codol_snapshot_codec.py`

实现了：

- split bit/raw cursor 写入器
- `index-skip` 字段索引编码
- `Scalar` 位域编码
- float raw-byte 编码
- commandTime 编码
- 首帧快照头
- playerState 运动字段顺序
- 武器事件、ViewHeight、current weapon、ammo/clip/reserve 段
- 尾部 owned slots 和 ammo pools

## 3. 验证结果

```text
golden=141 bytes
built =141 bytes
byte_exact=True
```

这证明当前实现与已知黄金首帧逐字节一致。

## 4. 关键 codec 语义

本阶段验证到的核心语义：

- 位流 LSB-first
- `Bytes()` 是 append-only，不移动 bit cursor
- `Bit` 只在字节边界重新基准到 `Data.Length*8`
- index-skip：0 表示紧跟，非 0 用 4-bit 连续段
- scalar：1-bit presence + 低位 + 逐字节高位
- float/raw 字段按 little-endian 原样追加
- 角度和短整数字段按 16-bit 原始值写入
- clip/ammo 段使用 11-bit weapon key、9-bit clip、12-bit reserve

## 5. 产物

- Codec：`tools/codol_snapshot_codec.py`
- 黄金向量：`CODOL-Combat-Server-v0.1/tests/golden_first_snapshot.hex`
- 路线状态：Phase 3 `DONE`

## 6. 边界

本阶段闭环的是首帧 playerState/运动快照黄金路径。
数组元素 18 种实体布局和大型结构的全部 codec 分支，仍由 Phase 4
的字段语义和实体状态工作继续覆盖。
