# 房间协议方向性突破：上下行格式不同（2026-10-28 第十一轮）

## 一、决定性发现

**客户端上行和服务端下行，用的是两套不同格式。**

这一条推翻了此前「房间消息不走位流」的片面结论——
那个结论只对**上行**成立。

### 上行（客户端 → 服务端）

```
L1 08 0b | 0a <sid> | 10 "Player" | 13 08 <len>
L2 0a <roomId> | 13 08 <len> | <u32 len-4> | <body> | 08 <1>
L3 body 首字节 = type
```

实测：87 条样本，只出现两种首字节 —— **`0x02`（53 次）、`0x18`（34 次）**。
按 160 bit 偏移穷举证否位流格式。

### 下行（服务端 → 客户端）

`type 0x0F`（RoomInfo）的 handler `0x635968` 实测：

```asm
cmp byte [ebx+0x278], 0      ; 闸门1
cmp edi, [eax+0x20]          ; roomId 高32 校验
cmp ecx, [eax+0x24]          ; roomId 低32 校验
cmp byte [ebx+0x283], 0      ; 闸门2
call 0x627ee0                ; ★ dwRoomMessageRoomInfo::deserialize（位流！）
```

**服务端下行走位流**，由各消息类的 `deserialize` 读取。

## 二、分发表全貌

`0x636f3c` 共 47 项（type 0..0x2E），41 个有效 handler。

客户端上行只触发过 `0x02` 和 `0x18`。
**其余 39 个 type 从未在客户端的上行里出现** —— 它们就是服务端该推的。

其中 **26 个 handler 做 roomId 校验**（`cmp edi,[eax+0x20]` / `cmp ecx,[eax+0x24]`），
即"带房间身份的消息"：

```
0x07 0x08 0x09 0x0A 0x0C 0x0D 0x0E 0x0F 0x12 0x13 0x15 0x16 0x17
0x1B
```

（另 13 个含同样比较但位置不同的，需逐个确认。）

## 三、`type 0x02` 的含义

handler `0x63495A`：

```asm
lea edx,[ebx+0x10798]    ; 房间对象内的容器
call 0x4a3af0            ; 查找匹配
mov edx,[edi+0x18]       ; ★ 虚函数槽 +0x18
call edx                 ; 分发到具体消息类
```

⇒ `0x02` 是**"消息分发/转发"** 类型：把收到的消息按 `[obj+0x18]` 虚槽
转给已注册的处理器。这也解释了为什么它出现最频繁（53 次）。

## 四、这解释了本轮实机为什么没效果

上一轮我按**上行格式**（`02 <sub> ...` A 类 body + `08 0b` 信封）构造推送。

- 信封部分（`08 0b | 0a <sid> | 10 name | 13 08 len`）**是对的**
- body 部分**错了**：服务端下行 body 应是被 `deserialize`（位流）读取的内容，
  不是上行那种 `02 <sub> ...` 容器

因此客户端即便收到，`0x627ee0` 那位流解析也会失败或读出垃圾，
房间状态不变 —— 与实测"无报错、无断连、行为不变"一致。

## 五、下一步

正确定义应当是：

```
下行 body = dwRoomMessage<X>::serialize 的输出（位流）
```

而 `serialize` 的规格此前已经从转储里自动提取过
（`tools/room_msg_spec.py`，41 条消息的 `B(tag)/D(bits)` 序列）。

之前我判定"位流格式错了"是因为拿它去对**上行**，方向搞反了。

## 六、待办

1. 把 `tools/room_msg_spec.py` 的 41 条 serialize 规格作为**下行 body 的权威格式**
2. 按 RoomInfo/Ready/RoomStateUpdated/MemberDetails 的 serialize 重新编码
3. 外层信封保持 `instant_push_body`（这部分已验证正确）
4. 实机验证

## 七、工具

```
CODOLServer/_mainline/dump_dispatch_table.py        分发表 + handler 特征
CODOLServer/_mainline/dump_server_only_handlers.py  39 个服务端专属 handler
tools/map_body_to_type.py                           上行 body 首字节分布（★ 本轮关键）
tools/room_msg_spec.py                              41 条 serialize 规格（下行权威）
```
