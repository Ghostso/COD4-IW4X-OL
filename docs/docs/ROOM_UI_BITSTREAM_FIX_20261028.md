# 房间 UI 全死 / 进不了 BOT 对局 —— 位流层根因（2026-10-28）

证据来源优先级：本地内存转储 `MEMDUMP_20261027_v4`（运行时 EXE 镜像，
VA 直接可读）> 客户端真实上行字节（`lobby_srv.log` 的 `11/4 setRoomData` 批次）。

---

## 一、已确认的字段级缺陷（我们编的房间消息，客户端必然解析失败）

客户端的位流写器 `0xB77B10` = `writeBits(v)`，内部调
`0xB77A70(value, 0, 0x1f, 0)` —— 即**固定写 5 位常量**。
真正的数据宽度来自 `writeData(ptr, nbits)`（`0xB777C0`）。

旧实现把两者都读错了，于是每一条房间消息从**第一个字段**起就与客户端的
反序列化器错位。逐条对照（客户端 `serialize` 实测 vs 我们的 `build_*`）：

| 消息 | 客户端 serialize | 旧实现 | 现在 |
|---|---|---|---|
| 消息头 | `writeBits(3)` + `writeData(type,8)` | **多写 1 位 `m_useDataTypes`** | 已删除前导位 |
| RoomStateUpdated | `0x15`+**32 位**，`0x15`+**32 位** | 20 位 | 已改 32 位 |
| MemberDetails uid | `0x15`+**32 位** | 20 位 | 已改 32 位 |
| MemberDetails 槽位 tag | **`0x02`（5 位）**+8 位 ×15 | `write_bits(2,2)`＝2 位 | 已改 5 位 |
| Ready | `0x01`(5位)+**1 位**布尔；真时再 `0x01`+8 位 `0xFF` | tag 写成 `0x10`、直接 8 位数据 | 已重写 |
| ChangeTeam | `0x15`+32 / `0x15`+8 / `0x15`+32 / `0x15`+64 | 8 位+8 位 | 已重写 |
| RoomInfo | 内联 `0x624510`：16 位长度串 ×6 + `3:`/`15:` 混合字段 | 只有 2 个 blob | 已按字段序重写 |

**最致命的是消息头那 1 位**：`BitWriter(True)` 在 bit 0 先写了一位
`m_useDataTypes`，而客户端 `serialize`（如 `0x625BFA` / `0x627EB7` / `0x6285C7`）
第一条写指令就是 `push 3; call writeBits`，`deserialize`（`0x625CF1`）第一条
读指令同样是 `readBits(3)`。多出这一位 ⇒ 整条消息从 bit 0 起全错。

## 二、逐位对拍器（离线、可复跑）

```
python -I tools/verify_room_msgs.py run_codol_001/kit_roommsg_20261028
```

用**独立的** LSB-first 位读器按客户端 `deserialize` 的读序回读服务端编码，
不复用服务端的写器（避免自己验自己）。当前 **5/5 通过**：
RoomStateUpdated / Ready / StartCountingDown / MemberDetails / ChangeTeam。

## 三、"点开始没反应"的直接原因：mmstart 分支从不推 mmbook accepted

本地实证对照（同一套大厅服）：

| run | 客户端发的 | 我们回的 | 战斗服 |
|---|---|---|---|
| `ONCE_20261026_220815` | `6/14 mmbook` | **98B `mmbook accepted`** | NAT→DTLS→getchallenge→connect **全链跑通** |
| `ONCE_20261028_*`（四轮） | `6/14 mmstart ...` | 只推自造的 `dwRoomMessageStartGame` | 日志停在启动那 7 行、**零收包** |

客户端在房间里点"开始"时发的是 `mmstart sv_resetServer; ... playlist 37;
start_map_rotate_once N; roomChatChannelID ...`，而 `mmstart` 分支只推了
自造的 109B StartGame，**从未推 `mmbook accepted`**。
`mmbook accepted` 才是让客户端去连 UDP 28960 的放行信号。

已在 `mmstart` 分支补上该推送（置于 StartGame 之前）。

## 四、尚未解决（需要实机验证才能定）

1. **房间消息的信封**。目前仍用 `build_room_push()`（自造 type-8 信封）。
   客户端真实上行 `11/4` 批次是另一种容器：
   `10000000 | 02 | 02000000 | 18000000 | d0000000 | 000000`，
   其中 `0xd0`(208) 落在 `dwRoomMessageRoomStateUpdated` 的 type 常量附近。
   这个容器格式尚未逐字段定死，**属未验证**，不得当作已对齐。
2. **战斗服地图硬编码** `mp_firingrange`（`CODOL_SERVER_319_20261021/src/main.c:64`），
   而房间选的是 `mp_raid`。进图后能不能跑对地图依赖这一步。
3. 网关 A/B（`dvar 3291`）与状态机计时器两条旧账仍在（见既有文档）。

## 五、本次改动（隔离 kit，未触碰受保护基线）

- 源：`run_codol_001/runs/ONCE_20261028_202928/runtime_kit`（整目录复制）
- 目标：`run_codol_001/kit_roommsg_20261028/`
- 只改 `lobby_server.py` 的 `BitWriter` 与房间消息构造器 + `mmstart` 推送分支。
- `REF_LOBBY_KIT` 与 `CODOL_VERIFIED_GOLDEN_20261019` **未改动**。

## 工具（全部只读可复跑）

```
CODOLServer/_mainline/dump_room_chain.py        房间推送链完整反汇编
CODOLServer/_mainline/dump_room_recv.py         接收端 deserialize
CODOLServer/_mainline/dump_room_exact.py        我们要推的消息的精确字段序
CODOLServer/_mainline/dump_bitstream_prims.py   位流原语
CODOLServer/_mainline/decode_room_batch.py      客户端 11/4 批次解码
tools/room_msg_spec.py                          41 条消息的 serialize 规格
tools/verify_room_msgs.py                       逐位对拍器
```
