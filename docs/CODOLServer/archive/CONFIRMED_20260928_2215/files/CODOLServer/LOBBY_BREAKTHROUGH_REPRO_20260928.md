# CODOL 大厅突破 · 复现手册

`[100] 无法连接大厅服务!` 弹窗已消除，客户端主状态机走到终态
`DWLOBBY_PUMP_SUCCESS`。本文件记录可重复的操作步骤与三轮连续复现证据。

## 1. 结果

四次运行全部到达终态，状态序列逐字一致：

```text
dwLogonStart -> DW_DNS_COMPLETE -> DW_ACCOUNT_LOGIN_COMPLETE
             -> DW_LOBBY_CONNECTED -> DWLOBBY_PUMP_SUCCESS
```

| run tag | DW_LOBBY_CONNECTED | DWLOBBY_PUMP_SUCCESS | 末帧 uA50 |
|---|---|---|---|
| IFS1_ELEVATED_20260928_183320 | t=37.043 | t=84.076 | 5 |
| IFS1_ELEVATED_20260928_184705 | t=37.484 | t=84.609 | 5 |
| IFS1_ELEVATED_20260928_184933 | t=37.046 | t=84.081 | 5 |
| IFS1_ELEVATED_20260928_185158 | t=37.279 | t=84.304 | 5 |

`uA50=5` 是主状态机终态，`00F7EF1C2` 之后不再进入
`@SF_UI_DW_LIVE_CONNECTING_FAILED` 弹窗分支。

## 2. 复现步骤

### 2.1 启动明文大厅探针（必须持续持有连接）

```text
cd /d D:\BaiduNetdiskDownload\使命召唤OL
python -X utf8 CODOLServer\lobby_server\lobby_plain_probe.py ^
  --bind 127.0.0.1 --port 8446 ^
  --log CODOLServer\logs\PLAIN\repro.jsonl
```

`serve_conn` 在 20 秒 recv 超时后必须 `continue` 而不是 `break`。
旧版本超时就关连接，客户端会在 `DW_LOBBY_CONNECTED` 阶段直接
崩溃（`exitcode=0xFFFFFFFF`）；保持连接后可稳定跨过 `uA50=4 -> 5`。

### 2.2 运行提权链

```text
python -X utf8 CODOLServer\_mainline\auto_lobby_loop.py --rounds 3 ^
  --seconds 120 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 ^
  --poke-lobby-globals
```

成功判定行：

```text
SUCCESS: client reported DW_LOBBY_CONNECTED
```

### 2.3 前置条件

```text
提权代理巚在运行：python agent_client.py ping -> ok
run_codol_001/sandbox_ifs1_20260923/iips.ini  enable_iips=1
iips.dll 为历史成功版本
                      SHA256 E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
```

## 3. `--poke-lobby-globals` 到底做了什么

```text
t >= 20 s   写 0x081A76A8 / 0x081A7F34 / 0x081A9784 = "127.0.0.1"
            写 0x081A9EC4 = 8443   (账号 / 队列 HTTPS 端口)
            写 0x081A9780 = 8446   (大厅明文端口)
            写 0x081A9EC0 = 8446

持续监视   当 [0x08269774+0x4F4+0xC8] == 2（真实 TCP 已连上）时
            写 [req+0x644] = 1
            写 [[0x08269774]+0x4F8] = 1
```

两个状态字段的作用：

```asm
; 0x00BA0780  需要 644!=0 且 C8==2 才返回 2
00BA0780  cmp dword ptr [ecx+0x644], 0
00BA078A  mov eax, dword ptr [ecx+0xC8]
00BA078F  cmp eax, 2
00BA0799  mov eax, 2

; 0x00B7A670  4F8==0 时把 2 降级为 1
00B7A686  cmp byte ptr [esi+0x4F8], 0
00B7A68F  cmp eax, 2
00B7A694  mov eax, 1
```

`0x007F3800` 拿到 2 才会把 `[0x84ABA7C]` 置 2，主状态机才能推进到 5。

注意：`reqC8==2` 是客户端自己在 `0x00BA4127` 写的，它只在
`0x00C73900` 返回 1（真实连接成功）才会执行。而连接成功的
前提是 `0x081A7F34` 必须是合法主机（见下）。

## 4. 为什么以前不行

### 4.1 大厅主机全局从未被填充

`0x00641600` 把分号分隔的配置串解析成 4 组 host/port：

```text
f0 host 0x081A76A8   f1 port 0x081A9EC4
f2 host 0x0E51184    f3 port 0x0E513D4
f4 host 0x081A7F34   f5 port 0x081A9780   <- 大厅用
f6 host 0x081A9784   f7 port 0x081A9EC0
```

`0x007F34E0` 为 f0 和 f4 各建一个 DNS 解析对象；`0x007F3600`
把它们的地址写进 `0x0E3ECA10`（f0）和 `0x0E3EC988`（f4）。
`0x007F3800` 用 `0x0E3EC988` 组大厅请求。

`0x081A7F34` 没人写 -> f4 域名槽为空 -> 解析失败 -> 地址缓冲
保持 BSS，退回逻辑从主 URL 缓冲尾部取到 `00 00 03 EC`
（`0x0E3EC000` 的 BSS 基址常量），于是“IP”变成 `236.3.0.0`。

修复前后实测：

```text
修复前 tplB(0x0E3EC988) = 00 00 03 ec ...  -> 236.3.0.0
修复后 tplB(0x0E3EC988) = 7f 00 00 01 ...  -> 127.0.0.1
```

### 4.2 大厅信道是明文 TCP，不是 TLS

修复主机后 HTTPS 探针立即报：

```text
{"event": "tls_fail", "error": "SSLError(1, '[SSL: WRONG_VERSION_NUMBER] ...')"}
```

客户端在该连接上发裸字节。`/auth/` 走 TLS，大厅走明文，
两者不同。

## 5. 大厅第一个包（28 字节，已捕获）

```text
c8 00 00 00  c8 00 00 00  d2 00 00 00  dc 00 00 00
00 00 08 00  <rand32>     <rand32>
```

前 4 字节是 little-endian 长度前缀。后续为位打包负载。
对照实验（回送不同长度）：

| 回送 | 结果 |
|---|---|
| 无 | `req9c` 停在 1 |
| 28B 回声 | 接受，进入 `sub-state 3` |
| 24B (`18 00 00 00`) | **拒绝**，立即 RST |
| 200B / 204B | 接受，但负载字段非法后仍失败 |

即客户端要求负载 **>= 200 字节**。载荷解析在 `0x00BA20A0`，
内部用 `0x00B78350`（位写入）与 `0x00B9BEB0`（位读取器），属位打包格式。

## 6. 下一步

客户端在 `uA50=5` 之后会真实驱动 IIPS TPFUI，但本安装缺少相应
PNG 资源：

```text
COD OL\IIPS\TPFUI\IIPSRes\back\SystemSetting  20 个文件全部是 69 字节 1x1 占位
下载器设定底图.png                      全盘不存在
back\1_1.png                                     2954 字节，完好
back\Icon_Image_TPF                               4398 字节，完好
```

同时主状态机达到 5 后仍会弹出引擎通用 `WIN_ERROR`
（本地化表里即“致命错误”），它与大厅无关。

## 7. 相关文件

```text
CODOLServer/CONFIRMED_RESULTS_20260928.md      第 20–21 节
CODOLServer/lobby_server/lobby_plain_probe.py  明文 TCP 探针
restore_iips_contract_001/observer2/AboProbe.cs 观察器与 poke
CODOLServer/_mainline/auto_lobby_loop.py       轮次驱动
CODOLServer/archive/CONFIRMED_20260928_2045    本轮归档
```
