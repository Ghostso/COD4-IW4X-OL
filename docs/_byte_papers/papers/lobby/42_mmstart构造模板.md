# `mmstart` 命令的构造模板（EXE 明文）

> 承接 `lobby/41`
> EXE 里能找到构造这个命令的**格式串**，字段序完全确定。

---

## 1. 模板原文

在 `codoMP_client_shipRetail.exe` 偏移 `0xdc6990` 附近：

```
"mmstart sv_resetServer; 2486 %d; 3265 %d; 2489 %d; 2574 %d; "
"0; 2500 0; %s; %s 2810 %d; sv_post_options %s; map %s; roomC..."
"2634 1; start_map_rotate"
"start_map_rotate_once"
```

**拼接后是：**

```
mmstart sv_resetServer;
2486 %d; 3265 %d; 2489 %d; 2574 %d;
2500 0;
%s;                      ← 可能是 "g_gametype xxx"
%s 2810 %d;              ← 可能是 "g_difficulty N"
sv_post_options %s;
map %s;
roomChatChannelID %llu;  ← 推测
2634 1;
start_map_rotate[_once] %d;
```

**⇒ 字段顺序是硬编码在格式串里的。**

---

## 2. 四个可变数字的位置

```
2486 %d     ← 参数 1
3265 %d     ← 参数 2
2489 %d     ← 参数 3
2574 %d     ← 参数 4
```

**与实测完全吻合：**

| 形态 | 2486 | 3265 | 2489 | 2574 |
|---|---|---|---|---|
| 靶场 | 0 | 18 | 0 | 0 |
| coop 地图 | 1 | 1 | 0 | 0 |
| playlist 形态 | 1 | 6 | 1 | 2 |

**⇒ 这四个数是同一个结构体的四个字段，按固定顺序写入。**

---

## 3. `2634 1` 这一条

```
2634 1; start_map_rotate...
```

**在实测样本里我没见过 `2634`**（`lobby/41` 的 16 个键里没有）。

**说明：**

- 要么这个分支（带 `2634`）在我的语料里没触发
- 要么 `2634` 是个可选字段

**而 `start_map_rotate` 和 `start_map_rotate_once` 是两个不同键名 ——
模板里可能是二选一。**

---

## 4. ★ 同时找到的控制台命令族

紧挨着模板后面：

```
room.create
room.list
room.join
room.leave
room.startgame
room.say
room.say2team
room.test
```

**这是一整套 `room.*` 控制台命令。**

**与 `memory: codol-myhandler-never-created-root-cause` 里记的
"三个 room.match.* 是控制台命令不是自动路径" 吻合，但这里列出了 8 个。**

**⇒ 客户端内置了完整的房间操作命令，可以从控制台调用。**

---

## 5. 其他相关命令

```
mmbook accepted
mmbook timedout
mp_trainingground
MESSAGE_JOIN_REQUEST Accepted
mmrespondinvitecmd %u %llu %u
mminvite %u %llu %llu %s %d %d %d
friend.sendinvite
friend.getinvited
jr %llu
1120 %08x %08x
1102 %d %d
```

**`mminvite` 的格式串：**

```
mminvite %u %llu %llu %s %d %d %d
           ↑   ↑     ↑    ↑   ↑  ↑  ↑
         类型 player room  名字  ?  ?  ?
```

**⇒ 邀请命令的字段序也是固定的。**

---

## 6. 一串数字 dvar 名

```
3031 3032 3033 3048 3351 3049 2942 2941 3014 3015 3024 3023 3021 3323
```

**这些和 `mmstart` 里的 `2486/2489/2500/2574/3265` 同一类 —— 数字 dvar 名。**

**相邻出现的还有 `dw_room_partyInvitationTimeout`（真名）。**

**⇒ 这串数字 dvar 里，有些是房间相关的。**

---

## 7. 结论：`playlist 37` 的来源

**模板里 `playlist` 不在固定的 `%d` 序列里，而是作为 `%s;` 的一部分。**

**⇒ `playlist 37` 是拼进 `%s` 那段的一个值。**

**而 37 在 `mp_playlists` 的表里不存在
（三份 playlist 全都没有 37）。**

**两种可能：**

1. **37 是 "playlist 数组的索引"**（第 37 个，从 0 或 1 数），
   而不是 `playlist <ID>` 里的 ID
2. **37 来自另一张表**（例如服务端下发的 "可选 playlist 列表"）

**第 1 种更可能：**

**`mp_playlists` 有 123 条，第 37 条（1-based）是：**

按排序后的列表 `[1,2,4,6,10,12,13,14,15,16,19,21,23,30,67,...]`，
第 37 个是 **`140`**。

**需要验证：`playlist 140` 定义的是什么对局。**

---

## 8. 下一步

1. 查 `mp_playlists` 的第 37 条（= ID 140）的定义
2. 确认 `start_map_rotate_once N` 与第 37 条里的地图列表对应
3. 追 `room.*` 控制台命令的实现（可能能直接调）
