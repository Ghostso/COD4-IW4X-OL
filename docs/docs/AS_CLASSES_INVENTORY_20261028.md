# 房间 UI 的 Scaleform API 全清单（2026-10-28 第十七轮）

## 一、突破：RTTI 暴露了完整的 AS_* 类

在 `EARLIEST2_20261027_132645/snap_003`（createRoom 之后 t=89s）的
`0x00E76800` 一带，发现运行时构造的 RTTI 类型名表：

```
.?AVAS_IsFirstLogin@@
.?AVAS_UIViewer_SetModelOffset@@
.?AVAS_SetPlayerData@@
.?AUAS_GetFakeClientObjs@@
.?AUAS_GetTeamType@@
.?AVAS_IsEverBeKickedByRoom@@
.?AVAS_GetMaxRoomNameLength@@
.?AVAS_MouseClicked3DAreaInLobby@@
.?AVAS_SelectTeamMemberItemInPanel@@
.?AVAS_QueryRoomTeammateStats@@
.?AVAS_SetStatsForRoom@@
.?AVAS_SetFinalVoting@@              ← 投票
.?AVAS_VoteMap@@                     ← 换图
.?AVAS_SetPilot@@
.?AVAS_IsPilot@@
.?AVAS_GetRankedMatchState@@
.?AVAS_GetRoomDLCLevel@@
.?AVAS_IsRoomFull@@
.?AVAS_IsRankedMatch@@
.?AVAS_GetRoomInfo@@
.?AVAS_ChangeRoomOptions@@
.?AVAS_ChangeRoomInfo@@
.?AVAS_ChangeTeam@@                  ← 换阵营
.?AVAS_CheckTeamAvatar@@
.?AVAS_ListDedicatedServer@@
.?AVAS_EnableVoiceTalk@@
.?AVAS_EnableInRoomEvent@@
.?AVAS_MarketDataReceivedInRoom@@
.?AVAS_RefreshInRoom@@
.?AVAS_IsRoomHost@@
.?AVAS_GetReadyState@@               ← 读准备状态
.?AVAS_SetReadyState@@               ← ★ 准备按钮
.?AVAS_StartMatchCountDown@@         ← 倒计时
.?AVAS_StartMatch@@                  ← 开始对局
```

**房间界面所有按钮，一一对应一个 `AS_*` 类。**

## 二、这些类的性质

命名规则 `. ?A V AS_xxx @@` = `V` 表示 class、`U` 表示 struct。
每个 `AS_*` 是一个 **Scaleform ExternalInterface 处理类**，
Flash（按钮）调 `SetReadyState` → 引擎实例化 `AS_SetReadyState` → 执行。

## 三、静态分析在这里到头

对每个类名做完整的三步追溯：

```
1. 名字 → TypeDescriptor      ✓ 找到（如 SetReadyState TD @0xE76C8F）
2. TD   → COL                 ✗ 引用 0 处
3. 名字 → 代码/数据引用        ✗ 引用 0 处
```

**TypeDescriptor 存在，但没有 Complete Object Locator 指向它，
也没有任何代码引用这些名字。**

⇒ 这些是**未被实例化的类型描述符**。RTTI 名字是编译期生成的，
但对应的类和注册代码在本次运行中**从未被激活**。

## 四、这解释了什么

如果 `AS_SetReadyState` 这个处理类**从未被注册到 Scaleform**，
那么 Flash 里的准备按钮回调就找不到后端实现 —— **点了当然没反应**，
而且连本地 UI 状态都不会变（因为没有任何 AS 代码被执行）。

这与用户观察到「按下去没有任何反应，连已准备状态都不变」完全吻合。

## 五、但有一个矛盾

`0xDDD5xx` 处还有另一份名字副本（`SetReadyState @0x00DDD504`），
那份在 `MEMDUMP`（较早的快照）里也存在。
两份副本的存在说明：
- `0xDDD5xx` 那份是**静态数据**（编译进 .rdata）
- `0xE76Cxx` 那份是**运行时构造的 RTTI**（在堆上）

静态那份在代码段也是零引用。

## 六、尚不能确定

1. 注册是否真的没发生 —— 也可能是注册表用**哈希/ID**而非名字字符串，
   名字只是调试用的 RTTI 残留。
2. 若是哈希注册，静态层看不到是正常的，不代表功能缺失。

⇒ **「AS 类未注册」是当前最合理的假设，但证据不足以定论。**

## 七、下一步可做的事（都受限）

| 方案 | 障碍 |
|---|---|
| 运行时验证注册表 | ACE 拦内存（t+0.01s 起 err=5） |
| 反编译 .gfx | 需要 Scaleform 专用工具，若没有则不可行 |
| 查 .ff 里的 gfx 资源 | `ui_mp.ff` 加载失败（version 461），解包工具不兼容 |

## 八、工具

```
CODOLServer/_mainline/dump_dynamic_api_table.py   运行时 AS_* 名表（★ 本轮关键）
CODOLServer/_mainline/find_scaleform_in_snaps.py  名字存在性 + 引用统计
CODOLServer/_mainline/resolve_as_classes.py       RTTI → COL → vtable（未成功）
CODOLServer/_mainline/trace_as_registration.py    名字引用追溯（零命中）
CODOLServer/_mainline/find_scaleform_bindings.py  绑定名清单
```
