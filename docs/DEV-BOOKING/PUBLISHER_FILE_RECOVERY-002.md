# PUBLISHER_FILE_RECOVERY-002

> DEV-PUBLISHER-RESTORE 恢复验证结果
> 2026-10-08 执行，未修改 Golden / 协议 / patch / KDF / ACE

---

## 0. 结论

```
FOUND_ORIGINAL           = CONFIRMED
RESTORED_IN_DEV          = CONFIRMED
PUBLISHER_SERVE_CONFIRMED = CONFIRMED
PUBLISHER_FAILURE_RESOLVED = CONFIRMED
BOOKING_GATE_REACHED     = CONFIRMED
```

Publisher 文件恢复后，`EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` 消失，
客户端正常进入大厅，并真正发出 `6/14 mmbook`。

---

## 1. DEV 副本路径

```
D:\BaiduNetdiskDownload\使命召唤OL\DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\
```

从 `REF_LOBBY_KIT\` 复制，排除内存转储目录（mem_*）与日志备份，
保留全部运行必需文件 + 数据目录。

复制清单（数据目录）：

```
publisher_files\   （12 个文件，含 manifest.json + release 变体）
player_profiles\   （public.result / secure.result）
user_files\        （the.json）
mkt_assets\
sku_arrays\
```

复制清单（运行必需代码）：

```
run_all.py
lobby_server.py
codol_crypto.py
battle_server.py
fake_auth_tls.py
marketplace_store.py
nt10.py
write_dwauth.py
make_local_ca.ps1
```

---

## 2. SHA-256 基线

核心代码（DEV 副本，与 Golden 冻结值一致）：

```
run_all.py           2AAA8847F112D926B996E5FD38DD26B697ADC0697C45781F520940A8256ECDA6
lobby_server.py      D7EEB4564AF05F4C71FB3391112A8BF592B74F0AA12DEC8F286B927AE046C2CF
codol_crypto.py      E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
battle_server.py     71BB7BEB85E514082B91A4925D18CB09FD07D5E8916FFA7F4FBD4A9750B47274
nt10.py              05863EBAFC7D7BB3820CCE057BC9E4E0EA07816945CA03E38A9BBFECACAB22F8
```

publisher_files（wire 格式，与源一致）：

```
activities_v1.info           58F1334B6DD5D354C32A5C530291F39D7DE2078DFCDC78CFC3278354BE264A5C
broadcast.info               8BA57F9A1D7FEDF9427BEA8B67B267D8BE19C5D8E16E0EB7BAD32E038CBCBFC5
configs_s.info               E4841FB89B0057A0717F643ADE4EDFF3607602A4BD23F538A030ABB7FEDB24FB
daily_challenge_config.info  C4B393C6ADF8093B7D1C8D04E88F46A219C4FFA743922213EDADF7BAE6D167E3
market_ui.info               0EAF09C035E20DC4B9E033A37FF2FD79936B5694202BE774DC4B9797C260E6F8
market-down.info             8B66ED53C280487E122E3A4E83C49E8637EA0AE4C036C7AEE0167ABC9BA5C734
MOTD.info                    596CA111B2AA2424C5355C31EF552D20F78232A723F0444ED7C42B7A6587EA22
mp_playlists_shipRetail_1.0.0.info   4238EA582F9474D8F63305CDE4D642826D62BC87F1ACE41E666D557DB8847C60
tlogconfig.info              BB933651A6C0358A3490B59136B244D9C1BCB20BF9F2912C88EAF7E1555F73B7
whitelist_tester.info        A3FD6A39284C8F36466D9A76E028E143424EABDC28D36B1BCB532AA152E8A538
```

---

## 3. service=10 task=21 下发记录（PUBLISHER_SERVE_CONFIRMED）

DEV 副本 lobby_srv.log（09:21:50）：

```
-> publisher mp_playlists_shipRetail_1.0.0.info (976 字节)
-> publisher activities_v1.info (30 字节)
-> publisher configs_s.info (311 字节)
-> publisher daily_challenge_config.info (67 字节)
-> publisher broadcast.info (4 字节)
-> publisher tlogconfig.info (92 字节)
-> publisher market_ui.info (16 字节)
-> publisher market-down.info (45 字节)
-> publisher whitelist_tester.info (30 字节)
-> publisher MOTD.info (29 字节)
```

10 个 publisher 文件全部成功下发，不再出现"缺"。

---

## 4. Fatal 是否消失（PUBLISHER_FAILURE_RESOLVED）

客户端窗口状态：

```
class = CODO
title = 使命召唤online    （非"致命错误"）
```

无 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` 弹窗。
客户端进程存活，正常进入大厅。

```
PUBLISHER_FAILURE = RESOLVED
```

---

## 5. 下一阶段

客户端继续执行：

```
publisher 下发
→ 大厅初始化（80/232 marketplace, 71/7 UIException, 102/1 等）
→ findSessions (playlist=10)
→ createRoom (roomId=0x1122334455667788)
→ setRoomData
→ 6/14 mmbook
```

---

## 6. 6/14 是否发送（BOOKING_GATE_REACHED）

**CONFIRMED。** 6/14 mmbook 真正发出。

时间线：

```
09:21:25  游戏进程启动
09:21:50  publisher 10 文件下发
09:23:45  首次 6/14 mmbook 命中
09:23:51  6/14 mmbook（重试）
09:23:55  6/14 mmbook（重试，连接重置后重建）
```

6/14 原始 payload（service=6 task=14 declared=48）：

```
0a 01 00 00 00 00 00 00 00
13 08 1d 00 00 00
19 00 00 00
6d 6d 62 6f 6f 6b 20 37 39 36 20 41 51 41 41 41 41 41 41 41 41 41 3d 20 30 00
```

解码：

```
0a 01                    = senderId = 1 (u64)
13 08 1d                 = blob, len 0x1d = 29
19 00 00 00              = 内层 u32 长度 25
"mmbook 796 AQAAAAAAAAA= 0"  = 命令内容
```

字段（与静态分析一致）：

```
mmbook                 = 命令名
796                    = playlist 版本
AQAAAAAAAAA=           = base64 token（8 字节全 0）
0                      = 第 4 参数
```

endpoint：`127.0.0.2:3074`（大厅 lsg 明文 TCP）。

retry state：booking 开关未开（`firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH`），
服务端仅空应答，客户端约 5 秒重试（09:23:45 → 51 → 55）。

---

## 7. 新出现的资源缺口

```
无。
```

publisher 文件恢复后，未再出现新的"缺 xxx"记录。
6/14 之后是 createRoom / setRoomData / 28/1 等正常流程。

---

## 8. Golden 完整性复核

Golden 四个核心文件哈希未变：

```
lobby_server.py  D7EEB4564AF05F4C71FB3391112A8BF592B74F0AA12DEC8F286B927AE046C2CF
codol_crypto.py  E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
battle_server.py 71BB7BEB85E514082B91A4925D18CB09FD07D5E8916FFA7F4FBD4A9750B47274
nt10.py          05863EBAFC7D7BB3820CCE057BC9E4E0EA07816945CA03E38A9BBFECACAB22F8
```

Golden 目录未做任何写入。

---

## 9. 最终状态

```
FOUND_ORIGINAL            CONFIRMED
RESTORED_IN_DEV           CONFIRMED
PUBLISHER_SERVE_CONFIRMED CONFIRMED
PUBLISHER_FAILURE_RESOLVED CONFIRMED
BOOKING_GATE_REACHED      CONFIRMED
```

验收结论：

```
核心成功：publisher .info → content initialization → 6/14 REQUEST = SENT
```

按 P3 要求，6/14 一旦出现即停止扩展 Publisher 工作。

---

## 10. 纪律核对

```
Golden 修改              = 无
Lobby Server 修改        = 无（DEV 副本，源代码未改）
Battle Server 修改       = 无
4 个 patch 修改          = 无
KDF hook 修改            = 无
客户端 EXE/DLL 修改      = 无
Booking response 发送    = 无
ACE/TenProtect 关闭      = 无
协议实现修改             = 无
```
