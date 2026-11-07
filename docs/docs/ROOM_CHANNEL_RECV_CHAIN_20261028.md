# 房间信道：接收链路已完整解出（2026-10-28 第四轮）

## 一、链路全貌（全部来自本地内存转储）

```
lobby 推送到达
   └─ dwLobbyEventHandler (vtable 0x00DE07A4, RTTI 已解出类名)
        ├─ 槽4  0x7F1040  (ret 0xc)  3 参数
        ├─ 槽6  0x7F1060  (ret 0x20) 8 参数 → 调 0x7E7C90 路由
        ├─ 槽7  0x7F10C0  (ret 0xc) 3 参数 → 调 0x7E79C0
        └─ 槽8  0x7F1110  (ret 0x14) 5 参数 → **"是不是我自己"判断**

0x7E7970(key_hi, key_lo)  —— 纯查表
    表 0xE374660 .. 0xE379200, stride 0x25D0
    byte[ecx-0x10] != 0  (启用标志)
    [ecx]   == key_hi
    [ecx+4] == key_lo
    命中返回表项

0x7E79C0(obj, a, b)  —— 房间信道消息接收
    [obj+8]  == 表项 key_hi     ← 消息携带的 roomId 高 32
    [obj+0xc]== 表项 key_lo     ← 消息携带的 roomId 低 32
    通过后把 [obj+0x18]/[obj+0x1c] 写进表项，再调表项里的回调

0x6371F0  —— 房间信道处理器（建房后注册为表项回调，handler 已实测）
    调 0x7E7970(key_hi, key_lo) 找信道
    再用位流读消息体 → 0x634870 按 type 分发
```

## 二、关键约定：`obj+8` / `obj+0xc` 是身份的固定槽位

两处独立的消费者用了同一布局：

| 消费者 | 比对目标 | 代码 |
|---|---|---|
| `0x7E79C0` | roomId 高低 32 | `cmp [edi+8],[esi]` / `cmp [edi+0xc],[esi+4]` |
| `0x7F1110` | **本地玩家 id** 高低 32 | `call 0xb9a0f0` 取玩家 → `cmp [edx+8],[eax+0x20]` |

`0xb9a0f0` 返回的玩家对象，`+0x20`/`+0x24` 是玩家 id 的高低 32 位
（这与 `0x637000` 里 `cmp [esi+8],ecx` 那套 sender 校验是同一套布局）。

⇒ 我们推送时 `sender_id = 1` 是**错的**：既不是 roomId，也不是玩家 id。

## 三、已确认的容器格式（客户端上行 `11/4` 实测）

```
u32 total | u8 flag | payload        (total == len(body)，精确成立)
```

样本：
```
10000000 02 02000000 18000000 d0 00000000000000     (20B, flag=0x02)
0c000000 02 02000000 08000000 800800                (16B, flag=0x02)
3b000000 02 06000000 30000000 e068ab5b...          (63B, flag=0x02)
```

**这些不是 Demonware 位流**：按 `readBits(3)` 起始解，没有一条能得出 tag==3。

## 四、尚未解决 —— 信封的确切线格式

现在的缺口很具体：我们推送的**外层信封**里，没有让客户端解出
"一个 `+8`/`+0xc` 等于 roomId 的对象"。两种现有构造都不满足：

| 构造 | roomId 位置 | 能否满足 `obj+8` |
|---|---|---|
| `build_room_push` | offset 25（第 4 个字段） | 否 |
| `instant_push_body(kind=11)` | **完全没有 roomId** | 否 |
| `channel_push_body` | `[u32][u64 sender][str][u64 channelId]` | 位置不符 |

要让 `obj+8 == roomId_hi`，信封最可能是：

```
u32 flag | u32 roomId_hi | u32 roomId_lo | ...
```

但**这一点尚未验证**，不得当作已对齐。

## 五、实机结果（本轮）

两轮均未达成目标。第二轮（`ONCE_20261028_212642`）nt10 正常、客户端进房间、
`11/4` 正常上行、推送正常加密发出、客户端无报错无断连 —— 与"消息被静默忽略"一致。

另：本轮发现发射器 `CORE` 白名单缺 `match_state_observer.py`，导致第一轮
nt10 崩溃（已修 `run_frozen_chain_once.py`）。

## 六、工具

```
CODOLServer/_mainline/resolve_vtable_class.py      vtable -> RTTI 类名（解出 dwLobbyEventHandler）
CODOLServer/_mainline/dump_chan_lookup.py          0x7E7970 / 0x7E79C0 / 槽4/7/8 反汇编
CODOLServer/_mainline/dump_lobby_handler_vtable.py dwLobbyEventHandler 全槽清单
CODOLServer/_mainline/scan_route_in_late_snap.py   在 snap_003/004 读路由表（★ 关键）
tools/split_room_container.py                      11/4 容器切分（total==len 校验）
tools/reinterpret_container.py                     容器再解释尝试
tools/check_route_key.py                           信封里 roomId 的位置
tools/verify_room_msgs.py                          消息体位宽对拍（5/5）
```
