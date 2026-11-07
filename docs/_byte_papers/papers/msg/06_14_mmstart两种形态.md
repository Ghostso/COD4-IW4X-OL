# 报文 `6/14` 的 `mmstart` 两种命令形态

> 补充卷：同一 task 的两套完全不同的启动指令
> 证据：`u64` 会话 ID 为 `0x1100001DEADC0DE` 的样本

---

## 1. 两种 `mmstart`

### 形态 A（`u64 = 1`，约 60 条）

```
mmstart sv_resetServer; 2486 0; 3265 18; 2489 0; 2574 0; 2500 0;
        g_gametype coop;  g_difficulty 1; ;
        map coop_train_mp_firingrange;2654 ;
        roomChatChannelID 0;
```

| 项 | 值 |
|---|---|
| `g_gametype` | `coop` |
| `g_difficulty` | `1` |
| `map` | `coop_train_mp_firingrange` |
| `roomChatChannelID` | `0` |

### 形态 B（`u64 = 0x1100001DEADC0DE`）

```
mmstart sv_resetServer; 2486 1; 3265 6; 2489 1; 2574 2;
        playlist 37; start_map_rotate_once 6;
        roomChatChannelID 1800154382;
```

| 项 | 值 |
|---|---|
| `2486` | **1** |
| `3265` | **6** |
| `2489` | **1** |
| `2574` | **2** |
| `playlist` | **37** |
| `start_map_rotate_once` | **6** |
| `roomChatChannelID` | **1800154382** |

**形态 B 没有 `map`，而是用 `playlist 37`。**

---

## 2. 形态差异的意义

| 项 | 形态 A | 形态 B |
|---|---|---|
| 会话 ID | `1` | `0x1100001DEADC0DE` |
| 地图指定 | 具体地图名 | **playlist 37** |
| dvar 值 | 固定 | 变化 |

**形态 A 是"打指定地图"（靶场），
形态 B 是"按 playlist 匹配"（正常匹配）。**

---

## 3. ★ 会话 ID 里的两个已知常量

`0x1100001DEADC0DE` 拆开：

```
0x1100001     0xDEADC0DE
   ↑              ↑
```

- **`0x1100001` = 17825793 = `0x1100001`**
- **`0xDEADC0DE`** = 经典的 "dead code" 调试哨兵

而 `ROOM_HOST_UID = 1000001`（项目常量）。

`0x1100001` 的十进制是 **17825793**，不是 1000001。
但 **`0x1100001` 的十六进制写法里含 `1100001`**，
如果把 `1100001` 当十进制读就是 1100001。

**这是一个非常可疑的巧合**：

- 项目常量 `ROOM_HOST_UID = 1000001`（十进制）
- 客户端会话 ID 高 32 位 = `0x01100001`

如果客户端写的是"`1100001` 十进制 + `DEADC0DE` 十六进制"，
拼起来就是 `0x00000000_1100001` 和 `DEADC0DE`……

**需要更仔细地核对。**

---

## 4. `playlist 37`

`playlist 37` 出现于形态 B。

项目里 `resolve_playlist37.py` 这个工具名就暗示了 37 的重要性。

**37 是某个 playlist 的编号。**

---

## 5. `roomChatChannelID`

- 形态 A：`0`
- 形态 B：**`1800154382`**

`1800154382 = 0x6B4C2D0E`。

**这与第 5 卷里 `0x07` 的 `0x0E2D4C6B`（在 `11/4` 的另一个会话 ID）
是字节反转关系！**

- `11/4` 的会话 ID 之一：`0e 2d 4c 6b`（小端 u64 = `0x6B4C2D0E00000000`？）
- `roomChatChannelID` = `1800154382` = `0x6B4C2D0E`

**这两个值相等。**

---

## 6. 这说明了什么

`roomChatChannelID` 与某个会话/房间标识相关，
且这个标识在 `11/4` 和 `6/14` 里以不同形态出现。

**这是"两条报文互证"的又一个实例。**

---

## 7. 未解

1. 会话 ID `0x1100001DEADC0DE` 的构造规则
2. `playlist 37` 对应哪个 playlist
3. `start_map_rotate_once 6` 的 6 是什么
4. 5 个 dvar 编号（2486/3265/2489/2574/2500）的含义
5. `1800154382` 与 `0x0E2D4C6B` 的关系（字节顺序？）
