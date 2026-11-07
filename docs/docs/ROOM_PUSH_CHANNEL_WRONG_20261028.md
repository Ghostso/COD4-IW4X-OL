# 房间推送为什么不生效 —— 信道选错（2026-10-28 第三轮）

## 一、最重要的发现：路由键是 roomId，不是 (service, task)

在 `EARLIEST2_20261027_132645/snap_003`（t=89s，**createRoom 之后**）里重读
`0x7E7C90` 的路由表 `0xE376C08`：

```
esi=0x0E376C08 flags=(1,1)
    entry+0x10 = 0x11223344      <- ROOM_ID 高 32 位
    entry+0x14 = 0x55667788      <- ROOM_ID 低 32 位
    [esi]      = 0x006371F0      <- 房间信道处理器
```

`0x1122334455667788` 正是我们 `createRoom` 回的 roomId。

**此前两轮我按 `(service, task)` 去读这张表，读到的全是 0，于是误判"未注册"。**
真实语义是：房间信道的路由键 = **roomId 拆成的两个 dword**（高32 / 低32）。

## 二、由此推翻前两轮的结论

| 我之前的判断 | 实测 |
|---|---|
| `0x82E1458` 是"type→类"注册表，未注册就丢弃 | **错**。该表在 `.tp3` 里、文件无初值、运行期才填；而且 `0x634870` 在 `esi==0` 时是 `jmp 0x63494A` **跳过前置拦截继续走跳转表**，不是丢弃 |
| type 常量 `0x0F/0x17/0x1D` 未被接受 | **错**。真正的分发表是 `0x636f3c`（`jmp dword ptr [eax*4+0x636f3c]`，type ≤ 0x2e），这些 type 都在表内 |
| 字段位宽是主因 | **不是主因**。位宽确实修对了（离线 5/5），但消息根本没进到解析这一步 |

## 三、我们发的两种信封，都不匹配这条信道

```
A build_room_push     : 08 08 00 00 00 | 0a <u64> | 10 "HostUser\0" | 0a <roomId> | 13 08 <len> <payload> | 08 00 00 00 00
                         └ 带 tag 的信封, roomId 在 offset 25（第 4 个字段）

B instant_push_body   : 08 0b 00 00 00 | 0a <u64> | 10 "...\0" | 13 08 <len> <payload>
                         └ kind=11 即时消息, **完全不含 roomId**
```

而客户端建好房间后注册的信道处理器 `0x6371F0` 接收的是
**`(u32 hiy, u32 loy, …)` 形式的两个路由 dword**。A 把 roomId 塞在第 4 个字段，
既不是函数参数的前两个，也不在信封头部。

⇒ **房间消息必须作为"路由键 = roomId 高低 32 位"的信道消息送达**，
即 `instant_push_body` 的 `kind` 参数（信封第一个 u32）应当携带 roomId 的一半，
或者需要用另一种信封形态。这一点尚未定死，**属未验证**。

## 四、已验证的部分（离线）

`tools/verify_room_msgs.py`：按客户端 `deserialize` 的读序回读，**5/5 通过**。
消息体本身（去掉信封）的位宽是对的：

- 头部：`writeBits(3)`(5 位) + `writeData(type, 8)`，**无前导位**
- RoomStateUpdated：`0x15`+32 / `0x15`+32
- MemberDetails：`0x15`+32、`×15 [0x02(5位)+8]`、`0x08`+8、`0x15`+32 …
- Ready：`0x01`(5位)+1 位；真时 `0x01`+8 位 `0xFF`
- ChangeTeam：`0x15`+32 / `0x15`+8 / `0x15`+32 / `0x15`+64

## 五、实机两轮的结果（均未达成目标）

| run | 结果 |
|---|---|
| `ONCE_20261028_212339` | nt10 崩在 `ModuleNotFoundError: match_state_observer`（发射器 CORE 白名单漏项，已修） |
| `ONCE_20261028_212642` | nt10 正常、客户端进房间、`11/4` 批次正常上行；战斗服**仍零收包** |

第二轮里 `mmbook accepted` 和修正后的房间消息都发出去了，客户端无 reset、
无报错，但按钮依旧无反应 —— 与"信道不对、消息被静默忽略"一致。

## 六、尚未解决

1. **信封形态**：需要确定房间信道消息的确切外层格式（详见 §三）。
2. **战斗服地图**硬编码 `mp_firingrange`（`src/main.c:64`），房间选的是 `mp_raid`。
3. 网关 A/B（dvar 3291）与状态机计时器两条旧账仍在。

## 七、工具（只读可复跑）

```
CODOLServer/_mainline/scan_route_in_late_snap.py   在 snap_003/004 里读路由表（★ 关键）
CODOLServer/_mainline/dump_msg_class_table.py       读 0x82E1458（结论已被推翻, 留档）
CODOLServer/_mainline/trace_room_chan_callers.py    找 0x6371F0 的调用者
CODOLServer/_mainline/find_room_gate_writes.py      房间状态闸门字节的写入点
tools/check_route_key.py                            检查信封里 roomId 的位置
tools/verify_room_msgs.py                           消息体位宽对拍（5/5）
```
