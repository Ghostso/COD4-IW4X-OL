# 下行位流重编后的实机结果（2026-10-28 第十二轮）

## 一、本轮改动

依据「上下行两套格式」的定案，把下行 body 改回**位流**：

- 新增 `_room_body_stream()`：`writeBits(3)` + `writeData(type,8)` + 字段序列
- `createRoom` 的三条推送改回 `build_roominfo_payload` /
  `build_memberdetails_payload` / `build_roomstateupdated_payload`（位流）
- **关键修正**：`build_room_payload()` 去掉 `<u32 len-4>` 嵌套前缀

### 去掉嵌套前缀的依据

`0x637000`（房间信道内层）实测：

```asm
00637009  push 0x24
0063702C  call 0xB779A0      ; 用 (ptr, nbits=len*8) 直接构造位读流
00637048  push 3;  call 0xB774E0   ; readBits(3) == 3
00637055  push 8;  call 0xB772E0   ; readData(8) = type
0063706E  cmp eax, 1               ; type==1 -> Manifold 分支
```

`0xB779A0` 把 blob 直接当位流，**不跳过任何前缀**。
上行多出的 `<u32 len-4>` 是客户端自己的包装，下行不该带。

## 二、离线验证：全部通过

`tools/verify_downlink_stream.py` —— 按客户端 `deserialize` 的读序独立回读：

```
RoomInfo(0x0F)      header tag==3 / type==0x0F / 63B
RoomStateUpdated    header tag==3 / type==0x17 / 两个 32 位字段
MemberDetails(0x1D) header tag==3 / type==0x1D / uid / 15 槽位 [1,0,1]
完整推送            push[0]==0x08 / service==11 / 含 roomId
```

样例输出：

```
body(11) = e3a2060000005400000000
push(54) = 080b0000000a01...0010"Player"00 13081a
           0a8877665544332211 13080b <body>
```

## 三、实机结果：首次出现可观测行为差异

`ONCE_20261028_224009`（客户端 pid 18088）：

| 指标 | 上一轮(223033) | 本轮(224009) |
|---|---|---|
| 大厅任务数 | 85 | **71** |
| `11/4` 上行次数 | 6 | **4** |
| 推送体大小 | 68/64/68 | 106/130/54 |
| 战斗服收包 | 0 | **0** |

上行的 `20B` 两次批次（`020200000018000000d000...`）在本轮**消失了**。

⇒ 客户端确实处理了我们推送的内容，行为发生了改变。
这是这条线上第一次出现的可观测差异。

但：**战斗服仍零收包**，房间 UI 是否点亮未确认。

## 四、当前状态

| 项 | 状态 |
|---|---|
| 上行格式 | 已解出（`02 <sub> ...` + 信封），证否位流 |
| 下行格式 | 已解出（`readBits(3)`+`readData(8)`+字段），本轮重编 |
| L2 封装 | 上行有 `<u32 len-4>`、下行无 —— 已区分 |
| 外层信封 | `instant_push_body(kind=11)` —— 已验证 |
| 战斗服收包 | **仍为 0** |

## 五、待查

1. 房间 UI 是否点亮（需要人工观察，日志无法判断）
2. 战斗服零收包是独立问题：`mmbook accepted` 在 10-26 那轮能让客户端连 28960，
   本轮同样发了却无效 —— 中间还有别的条件
3. `type 0x02`（消息分发）在客户端上行占 53/87，可能是关键：
   服务端也许应当用 `0x02` 包装要推的消息

## 六、工具

```
tools/verify_downlink_stream.py   下行位流对拍（本轮新建，全通过）
tools/room_protocol.py            三层解析库
tools/map_body_to_type.py         上行 type 分布
CODOLServer/_mainline/dump_dispatch_table.py      分发表
CODOLServer/_mainline/dump_server_only_handlers.py 39 个服务端专属 handler
```
