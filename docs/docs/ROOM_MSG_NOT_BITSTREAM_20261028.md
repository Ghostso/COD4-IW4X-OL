# 房间消息不走位流 —— 决定性负面结果（2026-10-28 第九轮）

## 一、穷举位偏移扫描：零命中

工具：`tools/scan_bit_offsets.py`

对客户端 `11/4` 上行的每一条批次，在**前 160 个 bit 偏移**上逐一尝试
`readBits(3) == 3` 后再读 `readData(8)`，检查解出的 type 是否落在
已知的 13 个 dwRoomMessage type 集合 `{0x03,0x0F,0x10,0x11,0x14,0x15,0x17,
0x1A,0x1D,0x1E,0x1F,0x25,0x2D}` 内。

样本（7 条，来自 `ONCE_20261028_220445`）：

```
#4  63B  3b000000020600000030000000e068ab5b...      无匹配
#5  21B  11000000181c5a98d6145391cf0172580100...   无匹配
#6  16B  0c000000020200000008000000800800          无匹配
#7  20B  10000000020200000018000000d0000000...     无匹配
#8  20B  10000000020200000018000000d0100000...     无匹配
#9  20B  10000000020200000018000000d0000000...     无匹配
#10 29B  190000006d6d626f6f6b2037393620...         无匹配（这是 mmbook 命令文本）
```

**全部无匹配。**

## 二、结论

`dwRoomMessage*::serialize` 那套位流格式（`writeBits(3)` + `writeData(8)` + 带 tag 的字段）
**不是房间消息在 11/4 通道上的线上格式**。

此前基于"房间消息是位流"做的所有编码工作（`build_roominfo_payload` 等）虽然
在位流层自洽（离线对拍 5/5 通过），但**可能根本用错了通道**。

## 三、容器真实结构（已确认部分）

```
u32 total | u8 flag | payload        (total == len(payload+flag)，精确成立)
```

样本 `#7`：`10 00 00 00 | 02 | 02 00 00 00 | 18 00 00 00 | d0 | 00 00 00 00 00 00 00`

`#{7,8}` 仅第 13 字节不同（`d0` vs `d0 10`），像是某种状态值。

## 四、参考实现给出的线索（C#，可信度最低，仅作线索）

`REF_LOBBY_KIT/_ref/CodolLocalLobbyServer.cs:1399-1412`：

```csharp
else if (b3 == 11 && b4 == 4) {
    byte[] reply = BuildTaskReply(localSecrets, b4, num8++, ++num9, null);
    // array18 有 8 字节内部头; 真正的 TLV 消息从 offset 8 开始
    byte[] pushData = new byte[num14];
    if (array18.Length >= 8 + pushData.Length)
        Buffer.BlockCopy(array18, 8, pushData, 0, pushData.Length);
    byte[] push = BuildPushFrameWithSender(localSecrets, num8++, 11u, pushData, 1, "Player");
}
```

该实现在 `11/4` 上**只做回显**（把客户端发的原样推回），且认为
offset 8 之后是 TLV 消息。这与我们的 `_parse_set_room_data` 剥离方式一致。

**它没有实现任何"服务端主动构造房间消息"的代码** —— 也就是说，
这条路该实现也没走通，不能作为权威依据。

## 五、当前状态

| 项 | 状态 |
|---|---|
| 房间消息走位流 | **已证否**（穷举 7 条样本 × 160 bit 偏移，零命中） |
| 容器结构 `u32 total \| flag \| payload` | 已确认 |
| 房间对象的 roomId 排布 | 已确认（`+8`=lo, `+0xC`=hi） |
| 信封里对象的字节位置 | **仍未定死** |
| 实机进对局 | 未达成，战斗服零收包 |

## 六、尚存的证据源

1. **客户端发送端**：找产生 `11/4` 批次的序列化函数，从代码直接读格式。
   这需要先定位发送路径（`0x634870` 是接收端，发送端尚未解）。
2. **更早的转储窗口**：`dump_early` 在 t+23.8s 前可读，若能让客户端
   更早建房（或让 lobby 在更早的应答里带上房间信息），可捕获初始写入。
3. **上行字节本身**：已穷举位偏移，无果。但可以试"非位流"的其它解释
   （如 protobuf 变长编码）——`#6`/`#7` 的长度字段与 TLV 模式更像后者。

## 七、工具

```
tools/scan_bit_offsets.py      穷举位偏移找 tag=3（★ 本轮关键，零命中）
tools/split_room_container.py  容器 u32 total 切分
tools/reinterpret_container.py 容器多种切法尝试
```
