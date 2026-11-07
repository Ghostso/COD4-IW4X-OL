# ★★★ 已进入大厅（2026-10-05 16:36）

> 承接 `HANDOFF_20261005_REFKIT_WORKS.md`。
> **本轮真正把客户端推进到了大厅 UI，并用截图确认。**

---

## 0. 一句话

```
REF_LOBBY_KIT 起服务 + nt10 注入这套固定启动链,
只需要补一个文件名别名 —— 客户端就跨过 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE,
从 34 条任务推进到 47 条, 窗口变成可见的 CODO/使命召唤online, 大厅界面渲染完成。
```

证据截图：`REF_LOBBY_KIT\lobby_window.png`（1920x1080，可见左侧好友/公告/福利/任务、
右上玩家等级 70 与货币、底部多人游戏入口）。

---

## 1. 两个真实修复

### 1.1 握手竞态：`0x83` 用了过期 challenge（本轮修）

**现象**：大厅服务已经起来，客户端也连上了（`0x81`/`0x82` 都正常），
但服务端回 `0x83` 后客户端**立刻断开**，解出任务 0 条。

**根因**：`0x82` 到达时 nt10 的 KDF hook 还没把本会话记录写进 `kdf_sessions.txt`
（16:01:52 那次晚约 1 秒）。服务端于是退回 `secrets.txt` 里的**上一会话**快照，
challenge 用成了旧的 `9acd25c0bd5d0820`，而真实值是 `09ac31d14c07bd30`。

**修复**（`REF_LOBBY_KIT\lobby_server.py` 的 `0x82` 分支）：
票据里带的 24B 会话密钥拿来配对，**最多等 5 秒**本会话 KDF 记录；
拿到就用它的 challenge 回 `0x83`，等不到才退回全局快照。

**验证**：
```
[multi] 本连接会话密钥=638bff...; kdf_sessions.txt 里有 1 个候选密钥组 (等待 0.15s)
[keys] 本会话 KDF challenge=44612fac6b273efc ...
-> 0x83 ... [challenge 来源: kdf-session, 等待 0.15s]
★ 解密成功 #1 seq=1 hmac=OK service=71 task=4 declared=84
     payload(81): ... 6e 51 6c 6f 50 30 6f 43 56 57 52 36 52 44 4a 53 ...  ("nQloP0oCVWR6RDJS")
★ 解密成功 #2 seq=2 ... task=10 declared=4      ← 正常流程, 不再是 71/3 错误上报
```

这正是 `HANDOFF_20261005_BREAKTHROUGH.md` §4.6 里那个"唯一剩余的结构性差异"
（参考 field1=`nQloP0oCVWR6RDJS` / declared=84，我们全零 / declared=212）。
修复后我们的首帧与参考**逐字段一致**。

### 1.2 缺失发行方文件：`EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` 的直接原因

**现象**：34 条任务后客户端弹出致命错误框 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`。

**根因**：客户端连续 3 次请求 `10/21` 的
`mp_playlists_shipRetail_1.0.0.info`，而套件里只有
`mp_playlists_shipRetail_release.info`（内容相同）；我们回空应答 → 客户端弹框。

**修复**：在 `lobby_server.py` 里给这个文件名加同义名回退，指向
`mp_playlists_shipRetail_release.info`；同时已经把实体别名文件
`publisher_files\mp_playlists_shipRetail_1.0.0.info` 复制到位（SHA256 一致）。

**验证**：
```
-> publisher mp_playlists_shipRetail_1.0.0.info (262 字节)
... 客户端继续: 68/3  28/4  71/18  102/7  102/1  3/46  3/48  80/232  9/5  21/*
任务总数从 34 -> 47, 连接持续 keepalive, 无 reset, 无致命弹窗
窗口类 CODO 可见, 标题 "使命召唤online"
```

---

## 2. 当前状态

```
服务端    REF_LOBBY_KIT\lobby_server.py (127.0.0.2:3074) 运行中
认证      REF_LOBBY_KIT\fake_auth_tls.py (127.0.0.1:3074) 运行中
客户端    codoMP_client_shipRetail 运行中, Responding=True
任务      47 条, hmac 全 OK
大厅 UI   已渲染 (见 lobby_window.png)
```

大厅里还浮着一个占位 `TextField` 对话框，来自本地 publisher 配置里的
占位文本（`mp_playlists_shipRetail_release.info` 本身是"parser probe"占位内容），
不影响进入大厅，属下一步内容补全项。

---

## 2.5 ★ 更正：重连失败不是密钥问题，是缺"游戏世界"

16:42 复现轮里，主连接结束后客户端立刻重连了一次，服务端日志出现：

```
[16:47:21]   对端关闭
[16:47:21] === 大厅连接结束 (127.0.0.1, 64808) (解出任务 56 条) ===
[16:47:21] === 大厅连接建立 (127.0.0.1, 65010) ===
[16:47:21]   -> 0x83 = ... 1c e1 6c f4 00 15 0c 3d
[16:47:21]   ★ 解密成功 #1 ... hmac=BAD ...
[16:47:22]   recv 异常: ConnectionResetError(10054)
```

**早先把它写成"握手密钥竞态残留"是错的。** 真实原因是：

> **本轮没有对应的游戏世界（world / 战斗实例）**，客户端在大厅里找不到可进入的
> 世界，于是正常关闭主连接并尝试重连；重连时服务端复用了同一会话的旧 challenge，
> 才留下那条 `hmac=BAD`。**BAD 是结果，不是原因。**

判据：
- 主连接 `64808` 从 16:42:40 稳定活到 16:47:21（约 4 分 40 秒），期间解出 **56 条**
  任务、hmac 全 OK、keepalive 正常，`game 仍在运行 (300s)`。
- 只有在主连接 `对端关闭` **之后**才出现重连与 BAD。
- 因此不要再去"修 0x83/BAD 竞态"当作主线阻塞点；真正的缺口是**游戏世界**。

**下一步方向**（替代原先的"重连边角修复"）：
1. 让服务端提供/发布一个可进入的游戏世界（`21/5` session / booking / 战斗实例），
   而不是只回空 ACK；
2. 或按参考实现三方的 `ready_push` + battle 流程把 world 落下来；
3. 在此之前，客户端在大厅停留属正常，重连那条路可以先忽略。

---

## 3. 复现命令

前提：提权代理 `CODOLServer\_mainline\agent_client.py` 可用
（`ping` 返回 `debug_privilege=true`）。

```powershell
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" `
  --secs 300 --out n10run_lobby.txt
```

成功判据（`REF_LOBBY_KIT\lobby_srv.log`）：

```
-> 0x83 ... [challenge 来源: kdf-session ...]
★ 解密成功 #1 ... task=4 declared=84
★ 解密成功 #2 ... task=10 declared=4
-> publisher mp_playlists_shipRetail_1.0.0.info (262 字节)
★ 解密成功 #35~47 ... service=68/28/102/3/21/71
```

---

## 4. 下一步（内容补全，不再是链路问题）

| 项 | 说明 |
|---|---|
| 占位 `TextField` | `mp_playlists_shipRetail_release.info` 是诊断占位内容，需换成真实 playlist 数据 |
| 商城 `80/*` | 仍是按 ol-mod 语义的空应答，商城页可能为空白 |
| 房间/靶场 | `21/*` `68/*` 已开始出现，可在此基础上做进房间/进对局 |
| 战斗服 | `firingrange-battle.enabled` 等开关未启用 |

---

## 5. 本轮改动文件

| 文件 | 改动 |
|---|---|
| `REF_LOBBY_KIT\lobby_server.py` | ① `0x83` 用本会话 KDF challenge；② playlist 文件名同义名回退 |
| `REF_LOBBY_KIT\publisher_files\mp_playlists_shipRetail_1.0.0.info` | 新增（复制自 release，SHA256 一致） |
| `REF_LOBBY_KIT\lobby_window.png` | 新增（进大厅截图证据） |
| `REF_LOBBY_KIT\popup_fatal_error.png` | 新增（修复前弹窗证据） |
