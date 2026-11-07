# ROUND 2026-10-22 晚：listen server 枚举 / 对局接口定位

证据：`run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin`（241,537,024 B，基址 0x400000）

## 1. listen server 硬件枚举能否反推服务器？不能

`0x478100` 只做本地化字符串注册：

```asm
0x4781F3  call 0xBD9C00                  ; push 3 / push str / call
0x4781FF  mov [0x762EFB8], eax
0x478210  mov [0x762EFBC], eax
0x478221  mov [0x762EFC0], eax
0x478232  mov [0x762EFC4], eax
0x478243  mov [0x762EFCC], eax
0x47824D  mov [0x762EFD0], eax
```

6 条字符串：

```
0xDC5C80  server_hardware_linux_dedicated
0xDC5CA0  server_hardware_win_dedicated
0xDC5CC0  server_hardware_mac_dedicated
0xDC5CE0  server_hardware_win_listen
0xDC5CFC  server_hardware_mac_listen
```

没有端口、没有包结构、没有握手、没有超时、没有 socket 调用。
只是服务器浏览器的 server_hardware 显示文案。

## 2. 但它确定了一条协议事实

这 6 个 token 是服务器上报字段（IW4 serverinfo 的 server_hardware）。
客户端承认 dedicated / listen，且带 linux / mac 分支——在 Windows-only 的腾讯服里毫无用处。

⇒ 这是 IW4 原版引擎代码，不是 CODOL 自研。
⇒ 客户端的服务器发现与连接层 = IW4 原版 netchan；IW4X / CoD4x 源码可作权威参照。

## 3. 客户端真正与战斗服通信的三处

### 3.1 全 exe 唯一的 UDP socket

```asm
0x77FC11  call [0xCA8548]   socket(AF_INET, SOCK_DGRAM, 0)
0x77FC3F  call [0xCA854C]   ioctlsocket(FIONBIO)
0x77FC8F  call [0xCA8554]   bind(s, {port, 0.0.0.0}, 14)
```

UDP 不用 connect()，走 sendto()。
⇒ 此前 hook `ws2_32!connect` 只看到 BugTrace / iips / libcef 的 TCP，永远看不到游戏流量。

### 3.2 出站命令队列 0x5C0F50

```asm
0x5C0F71  mov esi, [0x331C0C8]
0x5C0F77  xor esi, 0xD362501F        ; CL 对象（异或解引用）
0x5C0F7F  mov eax, [esi+0x140]       ; 写索引
0x5C0F8E  cmp eax, 0x200             ; 512 条
0x5C0FB0  and eax, 0x1FF
0x5C0FB5  shl eax, 0xA               ; x 0x400
0x5C0FB8  lea edi, [eax+esi+0x148]   ; 命令槽
0x5C0FC1  call 0x675840              ; 写入
```

CL 基址（dump 实测）= `0x1C830E14`
布局：`+0x140` 写索引，`+0x144` 读索引，`+0x148` 起 512 x 0x400 字节槽

### 3.3 入站分发器 0x5C0FD0（strcmp 0x7745E0）

```
0xDBFF40  disconnect_ack
0xDBFF50  （第二条，未读全）
0xDBCE80  EXE_SERVER_DISCONNECTED
```

## 4. 与现有 OOB 命令集对齐

`battle_service.c` 已处理：`stats / getchallenge / connect / heartbeat / gamestateupdate`
—— 正好是 IW4 / CoD4x OOB 全集。
加上 server_hardware 枚举，可判定：客户端对局协议 = IW4 原版 netchan，无 CODOL 私有改动。

## 5. 下一步

在 `0x5C0F50` 下断，抓客户端发往 UDP 28960 的真实命令序列。

## 6. 本轮附带确认

### 6.1 0x32AD060 是被我们的 CS[0] 清空的

表头 `valid=0 / count=0 / textLen=0`，但 names/values 仍留着上次成功解析的 12 组指针：

```
targetname        = lobby_player_pos
classname         = script_origin
angles            = 0 180 0
origin            = -5054 -9 -47
model             = cha_quartermaster
script_noteworthy = lobby_stand_05
```

`0x4E8660` 入口无条件清零表头（`0x4E867D / 0x4E8680 / 0x4E8683`）后再解析。
CS[0] 以 `0x5C` 开头而非 `0x7B`，解析失败，把大厅阶段填好的表覆盖成空。

### 6.2 northyaw 其实被读到了

`[0x32AF42C] = 1.0`，`[0x32AF430] = 0.0`
⇒ `0x4EC27C` 的初始化执行过，小地图空不是 northyaw 缺失导致的。

### 6.3 listen server 网络日志串

```
0xD90B4C  unable to listen socket
0xD90BE8  no hostname specified
0xD90D0C  bad hostname lookup
0xD950F8  listen
```

引用点：`0xE4A7C4` / `0xE4A784` / `0xE4A714` / `0xE4C414`
