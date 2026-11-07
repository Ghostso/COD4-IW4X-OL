# 房间推送信封：路由键槽位已确定（2026-10-28 第五轮）

## 一、决定性发现：身份槽位是 `obj+0x18` / `obj+0x1c`

运行时 `dwLobbyEventHandler` 实例 `0x0E39B6E8` 的原始内容：

```
+000  00DE07A4   ← vtable（RTTI 已解出类名）
+004  3D5580C8
+008  3D5580C8
+00C  00000001
+010  00D5A0C8
+014  00D5A5B4
+018  00000000   ← ★ 房间/发送者身份 高 32
+01C  00000000   ← ★ 房间/发送者身份 低 32
```

`+0x18` / `+0x1c` **在收到推送前恒为 0**。

## 二、完整链路（每个环节都有反汇编支撑）

```
① dwLobbyEventHandler 槽6 (0x7F1060) 被调用
     参数: [ebp+8] [ebp+0xc] [ebp+0x10] [ebp+0x14] [ebp+0x18] [ebp+0x1c] [ebp+0x20] [ebp+0x24]
     先调 0x7F3440: 把 [ebp+0x18] 指向的串(strcmp 比对 "HostUser")拷进栈缓冲 edi
     再调 0x7E7C90(p1=[ebp+8], p2=[ebp+0xc], p3=edi, p4..p7)

② 0x7E7C90 按 (p1, p2) 遍历表 0xE376C08..0xE37B7A8 (stride 0x25D0)
     [esi-0x25B8] != 0 且 [esi-0x25B7] != 0        (启用)
     p1 == [esi-0x25A8]
     p2 == [esi-0x25A4]
     handler = [esi]  -> 命中则 handler(p1..p7)

③ 建房后该表项实测内容（snap_003, t=89s）：
     [esi-0x25A8] = 0x11223344   (= roomId 高 32)
     [esi-0x25A4] = 0x55667788   (= roomId 低 32)
     [esi]        = 0x006371F0   (房间信道处理器)

④ 0x6371F0 调 0x7E7970(key_hi,key_lo) 查信道 -> 位流读消息 -> 0x634870 按 type 分发
     分发表 0x636f3c，type <= 0x2e

⑤ 0x7E79C0 校验 [obj+8]==key_hi, [obj+0xc]==key_lo，
     通过后把 [obj+0x18]/[obj+0x1c] 写进表项
```

## 三、结论

房间推送的路由键 **必须等于 roomId 的高低 32 位**，这一点现在是确证，不是推测。

而我们的两种信封都不满足：

| 构造 | roomId | 位置是否符合 |
|---|---|---|
| `build_room_push` | 在 offset 25（第 4 字段） | 否 |
| `instant_push_body(kind=11)` | **完全没有** | 否 |

## 四、尚未定死的最后一步

`0x7E7C90` 的 p1/p2 来自槽6 的 `[ebp+8]`/`[ebp+0xc]`，而槽6 是被
`call dword ptr [reg+0x18]` 调的（全镜像 5421 处），静态层无法唯一定位调用者。

因此**信封的字节布局仍未定死**。已排除的：
- 不是 `(service, task)` 路由（实测表里放的是 roomId）
- 不是 Demonware 位流（客户端上行 10 条样本无一以 tag==3 开头）
- `"HostUser"` 不是校验条件，只是一个被拷贝的 payload 字段
  （`0x7F3440` 的返回值被 `0x7F1060` 丢弃）

## 五、下一步可做的事（按可行性排序）

1. **抓运行时**：在客户端建好房间后，对 `0x0E39B6E8+0x18` 下硬件写断点，
   看谁写它、写什么。这能直接给出信封解出的 key。
2. **对 `0x7E7C90` 下断点**：看 p1/p2 实际值，以及调用栈。
3. 若无法下断点（ACE 可能拦），退而求其次：**枚举 `0xE376C08` 表项在
   不同时刻的内容**，观察 key 是否恒等于 roomId，从而反推必须先发什么。

## 六、工具

```
CODOLServer/_mainline/read_lobby_handler_instance.py   读运行时实例（★ 本轮关键）
CODOLServer/_mainline/find_lobby_handler_users.py      找 vtable 引用点
CODOLServer/_mainline/dump_envelope_parse.py           槽6/0x7F3440 反汇编
CODOLServer/_mainline/dump_chan_lookup.py              0x7E7970 / 0x7E79C0
CODOLServer/_mainline/scan_route_in_late_snap.py       建房后路由表实测
tools/find_name_field.py                               上行里找标识串
```
