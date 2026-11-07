# CODOL 从原版本体到大厅：固化复现记录

版本：2026-10-19。本文是新环境的唯一操作记录：原版 COD OL 只作为文件源，启动必须使用独立沙箱和固化套件。

## 1. 入口结论

不要双击原版 COD OL\codoMP_client_shipRetail.exe 作为大厅入口。直接启动已复现：初始化IIPS错误：8189fec。正式链为：原版文件 -> 独立沙箱 -> 本地 auth/Lobby 服务 -> nt10.py 注入启动 -> 大厅。

本链不修改原版，不替换 ACE/TenProtect，不使用 TAS，不劫持 down.qq.com 或 intldlgs.qq.com。

## 2. 前置环境

~~~powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
python -m pip install pefile capstone
~~~

需要 Windows 10/11 x64、Python 3.10+、管理员权限、原版 3.19 零售客户端和至少 2 GB 空闲空间。

## 3. 原版本体检查

~~~powershell
$Game = 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
Test-Path "$Game\codoMP_client_shipRetail.exe"
Test-Path "$Game\codoMP_client_shipRetailBase.dll"
Test-Path "$Game\IIPS\iips.dll"
Test-Path "$Game\IIPS\IIPSDownload\ff_init_common_mp_V111.ifs"
Test-Path "$Game\IIPS\IIPSDownload\ff_init_common_marketplace_V95.ifs"
Get-FileHash -Algorithm SHA256 -LiteralPath "$Game\codoMP_client_shipRetail.exe","$Game\codoMP_client_shipRetailBase.dll","$Game\IIPS\iips.dll","$Game\iips.ini","$Game\dwauth.ini"
~~~

五项 Test-Path 都必须是 True。当前基线：

~~~text
codoMP_client_shipRetail.exe       7841344  36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
codoMP_client_shipRetailBase.dll 60327992  EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20
IIPS\iips.dll                       347704  72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348
iips.ini                                48  2EB27C03261CB1603AE817DF15F79B6CC7561A435AB0D1C39874A97FC471B952
dwauth.ini                              79  92203E1E32C0D9A45A246B58B388D013F8DD1F0C246F5EA4039BDA9168E40CF0
~~~

## 4. 从原版重建独立沙箱

已修正脚本：run_codol_001\rebuild_datafix_sandbox.ps1。它拒绝覆盖已有目标，创建独立 main 普通目录，从两个 IFS 容器重新解出 6 个大厅 fastfile，并生成 sandbox_rebuild.json。

~~~powershell
$Root = 'D:\BaiduNetdiskDownload\使命召唤OL'
$Name = 'sandbox_repro_20261019'
powershell -NoProfile -ExecutionPolicy Bypass -File "$Root\run_codol_001\rebuild_datafix_sandbox.ps1" -Root $Root -Name $Name
$SB = "$Root\run_codol_001\$Name"
Get-Item "$SB\main" | Format-List FullName,LinkType,Target,Attributes
Get-FileHash -Algorithm SHA256 -LiteralPath "$SB\main\common_loadscreen.ff","$SB\main\common_mp.ff","$SB\main\localized_common_mp.ff","$SB\main\common_marketplace_lite.ff","$SB\main\common_marketplace_lite1.ff","$SB\main\localized_common_marketplace_lite.ff"
~~~

main 的 LinkType 和 Target 必须为空，不能是 Junction。六个确定哈希：

~~~text
common_loadscreen.ff                 24885     9D275F71ED28F26C66F3EA93D335FB5D072738CF857F3613E4C5A5154EE75B1E
common_mp.ff                      77605093     0E334EA875BCE6A114B1FBD16B1CBD3421697465847209769C149E7B643A7B2D
localized_common_mp.ff              192434     7D8C9C26BF47964CB2BF9B3198EBDEAFC67D972D6688916C3C476BEE96ADDD0F
common_marketplace_lite.ff        29594085     FAEBB5209B760317D3C99FC01B06C5CF2933BCBCC9C881B1A569227FBA3FC35C
common_marketplace_lite1.ff        3436085     CFDC61FDBD824BA007DF81FE48EA015A7496864A4C526FB86FE1A3215841F312
localized_common_marketplace_lite.ff 66671     B3A71A198AD0BCA75848709C7A51DF682BAA22585A276315FE7FBA015884FA6B
~~~

## 5. 固化套件和业务数据

REF_LOBBY_KIT 必须包含 run_all.py、nt10.py、lobby_server.py、fake_auth_tls.py、codol_crypto.py、battle_server.py、marketplace_store.py、make_local_ca.ps1、write_dwauth.py，以及 publisher_files、player_profiles、user_files、mkt_assets、sku_arrays。

必需文件：

~~~text
publisher_files\activities_v1.info
publisher_files\broadcast.info
publisher_files\configs_s.info
publisher_files\daily_challenge_config.info
publisher_files\market-down.info
publisher_files\market_ui.info
publisher_files\MOTD.info
publisher_files\tlogconfig.info
publisher_files\whitelist_tester.info
publisher_files\mp_playlists_shipRetail_1.0.0.info
publisher_files\manifest.json
player_profiles\public.result
player_profiles\secure.result
user_files\the.json
player-account.json
marketplace-inventory.json
~~~

关键数据：mp_playlists_shipRetail_1.0.0.info 21412 B SHA256 AD2EE85A81E59D1171E2ABFCF030F7BE5B9C847C6F8BD8AE649806650146634E；public.result 33428 B SHA256 66AB0D61A76A25C4B19EA87B94A799A0B31AD4110EF9CEC302BA83E89C9D2615；secure.result 32983 B SHA256 FD97A4B875D7CF9238DFD63C4C30692ADD4362933EAB784AE78CB63FA40CC656。

不要使用 GOLDEN-LOBBY-001\REF_LOBBY_KIT 的空数据副本，否则会出现 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE。

核心脚本哈希：

~~~text
run_all.py        2AAA8847F112D926B996E5FD38DD26B697ADC0697C45781F520940A8256ECDA6
nt10.py           05863EBAFC7D7BB3820CCE057BC9E4E0EA07816945CA03E38A9BBFECACAB22F8
lobby_server.py   D7EEB4564AF05F4C71FB3391112A8BF592B74F0AA12DEC8F286B927AE046C2CF
fake_auth_tls.py  E638E96FE420D66D1D52C26F3E413A15126818E4491AE30196A806CBCDD265BE
codol_crypto.py   E836C63AF75DD82EF6F3B07EF63FAE48B044B3B5047336127093C92B07644607
make_local_ca.ps1 F89E314E717A38A393FD31EA9BD0DBF69648F682D7FE14B000C68FC764DFE103
write_dwauth.py   8991C6A44A73897DF12A28B78E8CB43331B2B2DD001B22263EBD28379516AD60
~~~

## 6. 新沙箱运行副本

不要修改冻结的 REF_LOBBY_KIT。复制代码、数据目录和开关到新运行目录，再把副本 run_all.py 的 GAME_ROOT 改成新沙箱：

~~~powershell
$Project = 'D:\BaiduNetdiskDownload\使命召唤OL'
$Src = Join-Path $Project 'REF_LOBBY_KIT'
$Run = Join-Path $Project 'run_codol_001\LOBBY_RUN_20261019'
$SB = Join-Path $Project 'run_codol_001\sandbox_repro_20261019'
if (Test-Path $Run) { throw '运行副本已存在，请换目录名' }
New-Item -ItemType Directory -Path $Run | Out-Null
$Files = @('run_all.py','nt10.py','lobby_server.py','fake_auth_tls.py','codol_crypto.py','battle_server.py','battle_selftest.py','marketplace_store.py','make_local_ca.ps1','write_dwauth.py','coop_map.txt','patch_spec.txt','tas_spec.txt','lobby_spec.txt','late_spec.txt','player-account.json','marketplace-inventory.json','marketplace-catalog.json','marketplace-catalog-merged.json','marketplace-catalog-client.json','tas_off.flag','poke_off.flag','firingrange-session.enabled','firingrange-battle.enabled','firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH','ready_push.on','playlists-include-pve.on','marketplace-catalog-client.on','marketplace-catalog-merged.on','marketplace-currency-lenient.on','catalog-include-sku-table.on','push_seq_offset.txt')
foreach ($f in $Files) { $p=Join-Path $Src $f; if (Test-Path $p -PathType Leaf) { Copy-Item $p (Join-Path $Run $f) -Force } }
foreach ($d in @('publisher_files','player_profiles','user_files','mkt_assets','sku_arrays')) { Copy-Item (Join-Path $Src $d) (Join-Path $Run $d) -Recurse -Force }
attrib -R (Join-Path $Run 'run_all.py') 2>$null
$ra = Join-Path $Run 'run_all.py'
$t = [IO.File]::ReadAllText($ra)
$t = [regex]::Replace($t, '(?m)^GAME_ROOT\s*=\s*r?".*?"\s*$', ('GAME_ROOT = r"' + $SB + '"'))
[IO.File]::WriteAllText($ra, $t, (New-Object Text.UTF8Encoding($false)))
Select-String -LiteralPath $ra -Pattern '^GAME_ROOT'
~~~

## 7. 开关终态

~~~text
tas_off.flag                                  存在
poke_off.flag                                 存在
firingrange-session.enabled                   存在
firingrange-battle.enabled                   存在
firingrange-booking-push.enabled              不存在
firingrange-booking-push.enabled.OFF_CONFIRMED_CRASH 存在
ready_push.on                                 存在
playlists-include-pve.on                      存在
marketplace-catalog-merged.on                 存在
marketplace-catalog-client.on                 存在
marketplace-currency-lenient.on               存在
catalog-include-sku-table.on                  存在
push_seq_offset.txt                           内容为 1000
~~~

booking push 曾经 9/9 触发连接断开，严禁启用。

## 8. 提权代理和清理

~~~powershell
$py = (Get-Command python).Source
Start-Process -FilePath $py -ArgumentList '-X','utf8','-u','D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py' -Verb RunAs -WindowStyle Hidden
python -X utf8 'CODOLServer\_mainline\agent_client.py' ping
Get-Content 'CODOLServer\logs\elevated_agent.json' -Raw
python -X utf8 'CODOLServer\_mainline\agent_client.py' run powershell -NoProfile -Command "Get-Process codoMP_client_shipRetail,IIPSHostApp,TP3Helper -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
~~~

必须看到 ok=true、debug_privilege=true。

## 9. 正式启动

~~~powershell
netstat -ano | Select-String ':3074|:28960'
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'
python -X utf8 'CODOLServer\_mainline\agent_client.py' run python -X utf8 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\LOBBY_RUN_20261019\run_all.py' --secs 600 --out n10_repro_20261019.txt --no-battle
~~~

不要加 --tas，不要手工双击沙箱 EXE，不要启动旧的 8443/8446 方案。必要端口是 127.0.0.1:3074 TLS /auth/ 和 127.0.0.2:3074 明文 Lobby。

## 10. 成功判据

运行副本中检查 auth3074.log、lobby_srv.log、n10_repro_20261019.txt。必须同时满足：

1. auth 日志有 TLS 就绪、200 task=10->11、TLS close-notify 已发。
2. Lobby 日志有 大厅连接建立 和 [keys] 试解命中。
3. 首批任务有 hmac=OK marker=0x86，持续有 0x85 应答。
4. 等待期间有 keepalive。
5. 没有 hmac=BAD。
6. n10 日志有 4/4 补丁回读成功和 secrets 快照。
7. 客户端与 IIPSHostApp.exe 存活，窗口标题为 使命召唤online，窗口类为 CODO。

当前新沙箱正式回归已观察到 HTTP 200 task=10->11、127.0.0.2:3074 ESTABLISHED、连续 0x85 任务 hmac=OK、keepalive、客户端和 IIPSHostApp 存活。

## 11. 补丁和版本边界

~~~text
AuthGate       @ 0x00B9A78E   74 -> 75
ClientTicket   @ 0x00B9A7C5   75 -> EB
ParseFallback  @ 0x00B9A7C7   E8 -> E9（跳到 0x00B9A7F1）
LsgNonceCheck  @ 0x00BA3C1C   85 C0 75 44 -> 85 C0 90 90
KDF hook       @ 0x00BA0D20
~~~

这些地址只对本文 EXE/Base DLL 哈希有效。任一回读不符时停止，不要把 RVA 当作其他版本的绝对地址。

## 12. 闪退、IIPS 错误和准确基址

~~~powershell
python -X utf8 'CODOLServer\_mainline\agent_client.py' run powershell -NoProfile -Command "Get-Process codoMP_client_shipRetail,IIPSHostApp,TP3Helper -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
python -X utf8 'CODOLServer\_mainline\agent_client.py' run python -X utf8 'run_codol_001\capture_iips_fatal_bases.py'
~~~

结果在 run_codol_001\runs\IIPS_FATAL_BASES_YYYYMMDD_HHMMSS\capture.json，包含每次采样的退出码、窗口、进程列表，以及 EXE、Base DLL、iips.dll 的精确 base、size、entry。

历史一次 8189fec 样本：主 EXE 0x00400000、Base DLL 0x788B0000、iips.dll 0x16440000。该值只是历史样本；ASLR 下新故障必须以同一次 capture.json 为准。

## 13. 故障表

| 现象 | 处理 |
|---|---|
| 初始化IIPS错误 8189fec | 不要直接启动原版；检查 enable_iips=1；重建沙箱并确认 6 个 fastfile |
| 进程几秒退出 | 清理客户端、TP3Helper、IIPSHostApp；核对 EXE/Base DLL 哈希和 4 处补丁回读 |
| EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE | 恢复 publisher_files，尤其 mp_playlists_shipRetail_1.0.0.info |
| 没有 TLS 200 | 检查 127.0.0.1:3074、证书、hosts、dwauth.ini |
| 没有 Lobby 连接 | 检查 127.0.0.2:3074 和 dwauth.ini 的 lsg 行 |
| hmac=BAD | 停止客户端，清掉运行副本旧 secrets.txt/kdf_sessions.txt，重跑；不要硬解 BAD 帧 |
| 建连后立刻断开 | 确认 booking push 启用文件不存在；确认只有一份 lobby/battle 服务 |
| 没有 KDF 快照 | 确认 ping 的 debug_privilege=true，再检查 nt10.py 和依赖 |
| 基址不一致 | 重新采集 capture.json；核对文件哈希；不要套用历史绝对地址 |

## 14. 回滚和证据

~~~powershell
python -X utf8 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\LOBBY_RUN_20261019\run_all.py' --restore-hosts
python -X utf8 'CODOLServer\_mainline\agent_client.py' run powershell -NoProfile -Command "Get-Process codoMP_client_shipRetail,IIPSHostApp,TP3Helper -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
Get-FileHash -Algorithm SHA256 -LiteralPath 'COD OL\codoMP_client_shipRetail.exe','COD OL\codoMP_client_shipRetailBase.dll','COD OL\IIPS\iips.dll'
~~~

固化证据：backups\GOLDEN_RUNTIME_20261019_1721\MANIFEST.json、REF_LOBBY_KIT\auth3074.log、REF_LOBBY_KIT\lobby_srv.log、REF_LOBBY_KIT\n10_datafix_repaired_20261019.txt、run_codol_001\rebuild_datafix_sandbox.ps1、CODOLServer\_mainline\_ifs_extract.py、run_codol_001\capture_iips_fatal_bases.py。

失败时至少保留 auth3074.log、lobby_srv.log、n10_*.txt 和 capture.json；这四类证据足以区分 IIPS、注入器、认证、Lobby 协议和 Publisher 数据层。
