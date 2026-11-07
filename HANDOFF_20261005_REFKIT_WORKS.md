# ★★ 决定性进展：第三方完整实现跑通（2026-10-05 15:55）

> 承接 `HANDOFF_20261005_BREAKTHROUGH.md`。
> **换用第三方完整实现（可进大厅→商城→靶场的版本），服务端链路全通。**

---

## 0. 一句话

```
不再自己拼协议。把 F: 盘「已经进过大堂」的整套脚本
(F:\桌面\ol\新建文件夹\scripts\，比 F:\桌面\ol\大厅\ 那份更新)
复制到 REF_LOBBY_KIT\，只改 GAME_ROOT 指向本机沙箱, 跑 run_all.py。

结果: 大厅连接建立, 解出 34 条跨 service 任务, hmac 全 OK,
      seq 连续到 34, 连接稳定维持 ~3 分钟(直到 200s 到期)。
```

对照：我们自己那套 `CODOLServer\` 只能解出 **4 条**（且 seq=2 就是 `71/3` 错误上报）。

---

## 1. 为什么之前 4 条就断

参考实现成功轮（`REF_LOBBY_KIT\lobby_srv.log`）的真实序列：

```
seq=1  71/4  declared=84   payload="nQloP0oCVWR6RDJS" + "++++++++++++++++"
seq=2  71/10 declared=4    payload=00          ← 正常流程（我们是 71/3 错误上报！）
seq=3  10/12 declared=27   -> 下发 user_files/the.json
seq=4  80/70 declared=37   -> marketplace 空应答
seq=5  12/6  declared=4
seq=6  6/5   declared=16
seq=7  8/1   declared=13   -> profile public.result (33428 B)
seq=8  8/2   declared=4    -> profile secure.result (32983 B)
seq=9+ 10/21 ×N            -> publisher_files/*.info
... 一路到 seq=34，connection 保持
```

我们的 4 条：`71/4(declared=212)` → `71/3` → `71/7` → `71/9`（错误上报后就断）。

**决定性差异**：

| 维度 | 参考（能进） | 我们（卡住） |
|---|---|---|
| `71/4` declared | **84** | **212** |
| `71/4` field1 | `"nQloP0oCVWR6RDJS"` (16B) | 全零 |
| seq=2 | **71/10** 正常流程 | 71/3 UserWarning |
| 会话密钥来源 | **`kdf-session`**（hook `0xBA0D20` 抓 KDF） | 从 provider `+0x9C` 读 |
| challenge | `9acd25c0bd5d0820`（与客户端完全一致） | 快照值 |
| 任务总数 | 34 | 4 |

---

## 2. 关键机制（参考实现独有）

### 2.1 KDF 会话密钥由 hook 抓取，不是从内存读

`nt10.py` 在 `0x00BA0D20`（KDF 函数）下 hook，抓到：

```
[kdf] ★HMAC 命中#1 ret=0xBA1E9B
[kdf] transcriptHash(20B)=35 28 7f ab ...
[kdf] sessionKey(24B)    =7b 28 58 90 ...
secrets_kdf.txt: challenge=9acd25c0bd5d0820 aes_out=8aaee35c2f477ee1e3b720091b974dc9
```

用它与客户端握手，`challenge` 完全匹配 → `0x83` 一次成功。

### 2.2 它容忍 `71/3` 遥测（不当错误）

`CodolLocalLobbyServer.cs:1251`：

```csharp
if ((b3 == 71 && b4 == 3) || (b3 == 68 && b4 == 3))
    // 只回 ACK，不改状态  -> RAW_TELEMETRY_ACK
```

### 2.3 主动 push（我们不做的）

`BuildPushFrame` service=11 / 21，在客户端发 ready(subtype=0x15) 时
push `RAW_GAME_START`（136 字节，含 mission params）。

---

## 3. REF_LOBBY_KIT 是什么 / 怎么用

```
D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\
  ← 从 F:\桌面\ol\新建文件夹\scripts\ 复制（22:27 那版较新）
  改动:  run_all.py 的 GAME_ROOT 指向本机沙箱
         run_all.py 给 nt10.py 补了 --root（原版没传，会去 E: 盘找游戏）
  配置:  tas_off.flag（TAS 必须关）, lobby/tas/late/patch_spec.txt
         data/ (publisher_files, player_profiles, user_files)
         证书 _ca.pem/_leaf2.cer + make_local_ca.ps1
```

### 跑法（必须管理员 —— 要写 hosts + 装根证书）

```powershell
cd "D:\BaiduNetdiskDownload\使命召唤OL"
# 用提权代理跑（agent 监听 127.0.0.1:18428）
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\run_all.py" `
  --secs 300 --out n10run.txt
```

或先起服务，再单独跑 nt10（省时）：

```powershell
python -X utf8 "CODOLServer\_mainline\agent_client.py" run python -X utf8 `
  "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\nt10.py" `
  --root "D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929" `
  --secs 300 --delay 0 --out "D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\n10run.txt" `
  --apis OpenFileMappingW,CreateFileMappingW,MapViewOfFile,connect,sendto
```

产物：`REF_LOBBY_KIT\lobby_srv.log`（大厅）、`auth3074.log`、`n10run.txt`（注入/观测）。

---

## 4. 已知待补（不影响连接，只是空应答）

`lobby_srv.log` 里几处 `缺 xxx` ：

| 缺失 | 影响 |
|---|---|
| `mp_playlists_shipRetail_1.0.0.info` | 播放列表配置（有 `mp_playlists_shipRetail_release.info`，名字不同） |
| `80/*` 商城若干 | marketplace 空应答（ol-mod 同款语义） |

---

## 4.5 ★ 弹窗仍然复现 —— 而且与任务数无关（2026-10-05 16:00 更新）

用参考实现跑通后**用眼睛确认了屏幕**：仍然弹
`[100]无法连接大厅服务！`（截图：`lobby_check.png` / `v2.png` / `v3.png`）。

### 关键否证

| 观察 | 结论 |
|---|---|
| 服务端解出 **34 条**任务、hmac 全 OK、连接保持 3 分钟 | 任务应答不是判定标准 |
| 加开 `ready_push.on` + `mirror_predicted.on` 后重跑 | **仍弹窗**，且日志里 `0B/4`（频道）**从未出现** |
| 参考成功轮里**同样有** `71/3`(seq=24) 和 `71/7`(seq=33) | `Address Fail` 上报**不是**判定标准 |

### 真正的差异：客户端卡在 34 条后不再发任务

```
共同前段: 3/53 6/5 8/1 8/2 9/14 10/12 10/21 12/6 29/10
          71/4 71/10 71/13 80/70 80/107 80/119 80/173 80/174 80/230 93/1 ...

参考继续到 69 条, 多出:
  68/3 ×3   28/4 ×2   71/18 ×2   102/7 ×2  102/5   102/1 ×3
  3/46 ×2   3/48 ×2   4/13 ×2    21/5      21/13   8/3     9/5
  80/232 ×2 10/20

我们停在 34 条（最后是 71/9），客户端不再发。
```

多出来的这批（`21/*` 房间、`68/*`、`28/*`、`102/*`、`8/3`(写档案)、`4/13`）
属于**进入房间/频道之后的阶段**。也就是说：

**客户端还没进到"房间"阶段就停了** —— 而参考那轮进到了。
这是**客户端侧**的分叉（第 34→35 条时，参考发 `71/7`，我们发 `71/9`），
不是服务端能直接改的。

## 5. 注意

* `nt10.py` 的 `watch_dialogs` 有个既有 bug：`ctypes.wintypes.LPARM` 应作 `LPARAM`，
  会刷一堆 traceback（不影响主流程，但日志很吵）。**未修**（属第三方代码）。
* `run_all.py` 的 `free_ports()` 按命令行匹配杀进程，KILL_RE 含
  `lobby_server.py`/`nt10.py` 等字面量 —— 别在自己的 shell 命令行里写这些词。
* 本轮客户端跑满 200s 被清理，**没有留屏截图**。
  "是否已进大厅 UI" 尚未用眼睛确认，但服务端侧 34 条任务全通、
  连接稳定 3 分钟、无 reset、无弹窗记录。

---

## 6. 与自建 CODOLServer 的关系

`CODOLServer\` 那套是我们自己的协议复刻，用于**理解和实验**；
`REF_LOBBY_KIT\` 是**能实际跑通的产品**。
后续若要推进到大厅/商城，应在 REF_LOBBY_KIT 上做；
`CODOLServer\` 的分析结论（密钥口径、帧格式、分派表）仍有参考价值。
