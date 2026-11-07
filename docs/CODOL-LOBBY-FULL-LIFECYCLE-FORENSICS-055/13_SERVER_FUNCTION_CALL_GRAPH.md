# 13 — 服务端函数调用图（大厅）

> 文件：`CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`（88,162 B，SHA `ff473204…`）
> 行号已核对。

---

## 1. 总入口

```
handle_lobby(conn, addr)            :1303
  └ 帧循环
      ├ 解密/加密（KDF 试解、HMAC 校验）
      └ reply_objects(service, task, plain)   :731
           ├ ack(note)                        :734  空应答
           └ 按 service/task 分派
```

---

## 2. 分派表（按源码行）

| 行 | 条件 | 作用 |
|---|---|---|
| 737 | `service==10 and task==21` | 发行方配置（含 `mp_playlists_shipRetail_1.0.0.info` 同义名回退） |
| 752 | `service==10 and task==12` | 用户文件 |
| 761 | `service==8 and task in (1,2)` | 档案 public/secure |
| 768 | `service==8 and task==3` | 客户端上传档案 |
| 782 | `80 in (32,130) or 93/1` | 钱包 |
| **789** | **`service in (0x15,0x8A) and task in (5,16)`** | **21/5 findSessions** |
| 851 | `service in (0x15,0x8A) and task==1` | session 相关 |
| 859 | `service in (0x15,0x8A) and task in (2,3,9,12)` | session 相关 |
| 862 | `service in (0x15,0x8A) and task==10` | session 相关 |
| 865 | `service==0x47 and task==2` | Tencent/2 |
| 873 | `80 in (70,107,119,154,173,174,203,230,232) or 93/131` | 商城 |
| **987–988** | **`service==11`** | **房间服务（旧映射）** |
| 989 | `task==13` | **createRoom** |
| 1008 | `task==2` | leaveRoom |
| 1010 | `task==4` | **setRoomData** |
| 1068 | `task==5` | publishChannelMessage |
| 1070 | `task==10` | 未定位 |
| 1074–1075 | `service==6` | **瞬时消息（mmbook/mmstart）** |
| 1158 | — | **UNMAPPED → 空 ACK** |
| 1166 | `service==28 and task==1` | 任务参数 |
| 1181–1226 | `service==0x66` (102) | playerdata |
| 1193/1194 | `task==7` | **102/7 批量读** |
| 1227/1228 | `task==1` | 102/1 频道订阅（客户端强校验 ≥1 对象） |
| 1235 | `task==5` | 102/5 |

---

## 3. 关键函数

### 3.1 `findSessions`（21/5）

```python
# :789-849
if service in (0x15, 0x8A) and task in (5, 16):
    ...
    if os.path.exists(FR_SESSION_FLAG):        # firingrange-session.enabled
        _vals = 解析请求里的 0x08/0x07 变长整数
        _pl = _vals[2]                         # ★ 第 3 个 u32 = playlist
        _map_name, _gt, _is_fr, _max_p = _resolver.resolve(_pl, explicit_map=_exp_map)
        # 写 active_room.json（战斗服用）
        objs = [cc.build_mission_session_object(True, playlist=_pl,
                    map_override=_map_name, game_type_override=_gt_id,
                    address67=True)]           # ★ 67 B 地址块在这里
        return objs, ...
```

| 项 | 值 |
|---|---|
| 输入 | 客户端请求（35 B 或 75 B） |
| 输出 | 261–281 B 的对象（含 67 B 地址块） |
| 副作用 | 写 `active_room.json` |
| 与断裂点的关系 | **地址在这里给到客户端**（早于 mmbook/mmstart） |

### 3.2 `createRoom`（11/13）

```python
# :989-1006
if task == 13:
    ob.u64(ROOM_ID); ob.u32(1); ob.u32(1); ob.u64(ROOM_SECOND_ID)
    ob.bool_(False); ob.bool_(False); ob.u32(1)
    return [ob.data()], ...
```

| 项 | 值 |
|---|---|
| 请求 | 4 B（无参） |
| 输出 | 37 B |
| **memberCount 的演变** | 10-26 kit: `0` + 第3个u32=`18`；10-27 起: `1` + `1` |

### 3.3 `setRoomData`（11/4）

```python
# :1010-1067
if task == 4:
    # 回显频道推送（"三方同款"）
    # 若 ready_push.on 存在且是 16B ready 批次 → 额外推 Ready + RoomStateUpdated
```

### 3.4 `mmbook / mmstart`（6/14）

```python
# :1074-1150
if service == 6:
    m = re.search(rb"mmstart[^\x00]{0,512}", body)
    if m:
        _map = re.search(r"\bmap\s+([^;\s]+)", _cmd_txt)
        _gt  = re.search(r"\bg_gametype\s+([^;\s]+)", _cmd_txt)
        log("★ mmstart 完整命令: %s" % _cmd_txt)
        log("★ mmstart 选择: gametype=%s map=%s" % (...))
        if _map and _gt:                      # ★ 两个都非空才写 coop_map.txt
            ...写 coop_map.txt / active_room.json...
```

| 项 | 值 |
|---|---|
| `_map`/`_gt` 都空时 | **静默跳过**，只打 `?` |
| 这是房间路径的形态 | ⇒ 不会更新 `coop_map.txt` |

### 3.5 `102/7`（playerdata）

```python
# :1193-1226
if service == 0x66 and task == 7:
    cnt = ...
    out = bytearray()
    for i in range(cnt):
        ...                          # val 恒写 0
    return [bytes(out)], ...
```

**实现里没有任何从真实状态读值的路径。**

---

## 4. 服务端"从不主动发"的部分

| 能力 | 状态 |
|---|---|
| 主动推送房间信息让客户端建房 | ❌ 不存在 |
| 主动推送 20 个 MM 事件 | ❌ 不存在 |
| 主动开始对局 | ❌ 不存在（全部由客户端 mmstart 触发） |

---

## 5. UNMAPPED 兜底

```python
# :1238
return [], "UNMAPPED service=%d task=%d payload=%dB -> 空 ACK (功能未实现)" % (...)
```

最新一轮（`ONCE_20261029_002046`）里命中该分支的：
`71/4`、`71/10`、`12/6`、`9/14`、`3/53`、`29/10`、`71/13`、`10/20`、`71/7`、`71/3`、
`68/3`、`28/4`、`4/13`（早期）、`71/18`、`3/46`、`3/48`、`9/5`、`4/4`。

> 注意：`4/13` 在旧 kit 里落 UNMAPPED，在新 kit 里有专门分支 —— 这是 **kit 版本差异**，
> 引用时必须注明用的是哪一份。
