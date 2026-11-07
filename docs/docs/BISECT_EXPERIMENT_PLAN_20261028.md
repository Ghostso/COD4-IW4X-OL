# dwRoomMatch::Init 二分实验设计

## 目标

找出哪条大厅应答会让 `dwRoomMatch::Init()` 执行。

## 已确认的事实（见 READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md）

```
dwRoomMatch::Init()                 static void，无参
  └─ 内部定义局部类 MyEventHandler
     vtable = 0x00DC78E8
       slot[0] = 0x004F7590  (空)
       slot[1] = 0x0063B500  ← 建房回调
       slot[2] = 0x004F7590

实测：MyEventHandler 实例数 = 0  ⇒ Init 从未执行过
```

`Init` 的函数体在加密节（`.tp3` @ 0x00A16000，VSize 219MB / RawSize 401KB），
**静态看不到调用点**。

⇒ 只能靠**行为二分**：逐组关闭大厅应答，看按钮是否变成可点。

## 工具

`lobby_server.py` 的 `reply_objects()` 开头加了开关：

```
bisect-disable.txt   每行一个 "service/task"，被列入的回空 ACK
bisect-only.txt      只放行列出的条目，其余全禁
```

## 分组（按可疑度）

### 第 1 组：玩家数据类

```
102/7      playerdata 批量读（50 个字段，曾回全 0）
102/1      playerdata 段读
102/2      playerdata
102/5      playerdata
```

**为什么可疑**：字段表索引 [44..49] 是 PVEMap/PVEMode/PVPMatch/PVPMode/RootIndex。
若客户端用这些字段判断"能不能组房间"，回全 0 会让房间功能自我禁用。

### 第 2 组：匹配/会话类

```
21/5       findSessions
21/1       findSessions（另一 queryKind）
28/1       任务参数
28/4       任务参数
```

### 第 3 组：房间服务本体

```
11/13      createRoom
11/4       setRoomData
```

### 第 4 组：配置/发行

```
10/12      用户文件
10/20      配置
10/21      发行方配置（mp_playlists / mp_playerdata）
```

### 第 5 组：其余（71/x 遥测、80/x 商城、8/x profile 等）

这些是 TLog 上报和商城，理论上无关，但要排除。

## 实验步骤

1. **基线**（无开关）：确认按钮不动 ✓ 进行中
2. **全禁**（bisect-only.txt 为空）：所有应答回空 ACK。
   - 若客户端能进房间且按钮可点 ⇒ 说明我们的某个应答**反而阻碍**了 Init
   - 若进不了房间 ⇒ 二分不可行（必需依赖太多），改用逐组
3. **逐组禁用**：每次只禁一组，看按钮。
4. 定位到组后，组内逐条二分。

## 判定标准（需要用户配合）

每轮结束后问用户：

- 按钮是灰的还是能点？
- 点了之后"已准备"状态变不变？
- 地图/成员列表显示是否正常？

**只有"能点 + 状态变"才算找到。**

## 现实约束

- 每轮约 4 分钟（启动 + 登录 + 建房）
- 单个二分路径：基线 + 全禁 + 5 组 + 组内细化 ≈ 8-10 轮
- 需要用户每轮手动进房间并反馈

## 备选：更快的方法

如果全禁导致进不了房间，说明依赖太多，二分不成立。

那就改成**对比法**：找一份"房间功能正常"的历史 run（若存在），
逐项 diff 它的日志与我们现在的。但据目前掌握，
**从未有过房间功能正常的记录**（10-26 的 8 轮成功走的是 PvE 剧情入口，
没进过 BOT 房间界面）。
