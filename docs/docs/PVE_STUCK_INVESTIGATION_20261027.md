# 剧情模式卡点调查 — 2026-10-27 夜间

## 已完成的分析

### 1. 网络层实证（回答用户问题）

进剧情全过程，客户端网络端点：

```
127.0.0.2:3074          ESTABLISHED    ← 大厅，正常
121.29.3.105:80         × 17 CLOSE_WAIT
121.29.3.105:443        × 7  ESTABLISHED
218.12.86.78:443        × 2
140.207.120.227:80/:443
116.128.177.166:443
UDP: 22011, 50076, 51240, 51450, 59865, 59969, 62197-62200

28960: 零次
```

**结论：客户端从未创建任何指向 28960 的 socket。**

### 2. 路由拦截实验（失败）

给 7 个外部 IP 加黑洞路由（`route add <ip> mask 255.255.255.255 192.168.5.254 metric 1`）。

**失败原因**：Windows 的 metric 是「接口 metric + 路由 metric」叠加，实测得到 21，
高于默认路由的 20 ⇒ 默认路由优先，流量照旧走外网。

`tracert` 证实仍走 `192.168.5.1`。路由已全部清理。

**副作用**：即使路由生效，也未必有用——本次连接状态从 CLOSE_WAIT 变成
ESTABLISHED（连通了），但卡点完全没变。

### 3. service=102 分析

**身份确认**：内存里找到 `services/PublisherStorageService`（Demonware 发布方存储服务）。

**请求结构**（实测）：

```
102/7 (556B):  08 <count u32 LE>  然后重复 count 次:
                 03 01 0A <idx u32 LE> <val u32 LE>     ← 11B/项
102/1 (22B):   08 00000000 | 08 <base u32> | 03 xx 0A <idx>
102/2 (1B):    00
102/5 (10B):   08 02000000 03 01 03 02 00
```

**字段表来源**：`_e1_regression\ol-mod-olfinal\tests\game_server\Fixtures\
mp_playerdata.def.1649370.bin`（build 1649370 = 我们的目标版本，22,940 B，153 个字段名）。

**关键字段索引**：

```
[44] currentMatchSelectPVEDifficulty
[45] currentMatchSelectPVEMap          ← 在 102/7 请求范围内(0..49)
[46] currentMatchSelectPVEMode
[47] currentMatchSelectPVPMatch
[48] currentMatchSelectPVPMode
[49] currentMatchSelectRootIndex
[50] currentRoomType                   ← 恰好超出请求范围
```

**实机验证：两次均失败**

| 尝试 | 应答 | 客户端反应 |
|---|---|---|
| 1 | 解析错，回显 0 字段（2B） | 每 5 秒重发 |
| 2 | 解析对，回显 50 字段（555B，对象 626B） | **仍然每 5 秒重发** |

**"每 5 秒重发"= 客户端认为应答无效。**

**为什么无关**：102 是 **ActionScript/Scaleform UI 层**的服务
（`?AVAS_GetPlayerData@@` RTTI 类，全内存有 644 个 `AS_*` 类）。
UI 层读 playerdata 不等于开局关键路径。

### 4. 连接状态机（已解出完整 11 态）

`0x005C8060` 是「状态值 → 状态名」的映射函数：

```asm
005C8060  cmp eax, 0xa
005C8065  jmp dword ptr [eax*4 + 0x5c80b4]
005C806C  mov eax, 0xdc0900   ; 0  = CA_DISCONNECTED
005C8072  mov eax, 0xdc0910   ; 1  = CA_CINEMATIC
005C8078  mov eax, 0xdc0920   ; 2  = CA_LOGO
005C807E  mov eax, 0xdc0928   ; 3  = CA_CONNECTING
005C8084  mov eax, 0xdc0938   ; 4  = CA_CHALLENGING
005C808A  mov eax, 0xdc0948   ; 5  = CA_LOADING
005C8090  mov eax, 0xdc0954   ; 6  = CA_CONNECTED
005C8096  mov eax, 0xdc0964   ; 7  = CA_SENDINGSTATS
005C809C  mov eax, 0xdc0974   ; 8  = CA_GAMESTATE
005C80A2  mov eax, 0xdc0984   ; 9  = CA_PRIMED
005C80A8  mov eax, 0xdc0990   ; 10 = CA_ACTIVE
```

`call 0x5C8060` 搜不到（两处命中是数据误报）⇒ 它通过 **vtable/间接调用**。

### 5. Demonware 服务全清单（内存实测）

```
services/CommonService          services/ChallengeService
services/CharacterLoadoutService services/InGameService
services/TutorialService         services/MatchService
services/MarketService           services/OnboardService
services/UIStencilService        services/SettingsService
services/LoginService            services/LeaderboardService
services/PublisherStorageService services/PartyService
services/WeaponLoadoutService    services/RewardService
services/CommunicationService    services/ClanService
services/CommunityService
```

另有 644 个 `AS_*` RTTI 类（ActionScript 绑定），包含：
`AS_StartMatch` / `AS_StartMatchCountDown` / `AS_JumpGame` /
`AS_LoadFastfile` / `AS_IsInGame` / `AS_IsInRoom` /
`AS_GetNewUnlockedCoopStoryMaps`

### 6. 过场动画

- 引擎日志 `_co.tlg`（304B）与 `players\config_mp.cfg` 均**加密**
- CEF 日志 `debug.log`（233KB）全是 `ssl_client_socket_openssl handshake failed
  net_error -100`（UI 浏览器连外部 HTTPS 失败，与开局无关）
- 过场视频格式：`.bk2`（Bink），路径 `%s\video\%s.bk2`
  （`0x00D6584C R_Cinematic_MakeBinkTexture`、`0x00D658D0 "%s\\video\\%s.bk2"`）
- 沙箱 `main\video\` 有 `.bk2` 文件，含 `<地图名>_load.bk2` 形式的关卡加载动画

## 用户提供的关键事实

1. 正版**进剧情后**断网仍可正常玩，**关卡结束**才报错
   ⇒ 对局本身不需要服务器，只有结算需要
2. 正版「战斗开始」**只停留一两秒**就开始播过场
   ⇒ 不是等网络超时，是等一个**快速可满足的本地条件**

## 当前判断

卡点不在网络层，也不在 `service=102`。

`CA_*` 状态机显示正常流程是：
`CA_LOADING(5) → CA_CONNECTED(6) → CA_GAMESTATE(8) → CA_PRIMED(9) → CA_ACTIVE(10)`

而客户端**连 28960 的尝试都没有** ⇒ 它停在 `CA_LOADING` 之前或之中。

## 下一步

1. 找设置 CA 状态值的代码（`[0x????] = 5` 之类的写操作）
2. 或者：直接在内存里找当前 CA 状态值
3. `AS_LoadFastfile` 可能是关卡加载入口，值得单独追
