# dwauth.ini 全盘取证报告（原始大厅域名/地址线索）

- 日期：2026-09-25
- 范围：`C:\ D:\ E:\ F:\ G:\`、工作区 `D:\BaiduNetdiskDownload\使命召唤OL`、`E:\CODOL_SANDBOX`、
  `E:\IW4X`、`G:\SteamLibrary\...\Call of Duty Modern Warfare 2`
- 约束：全程只读。未删除/移动/改名任何文件，未改网络配置，未运行游戏。
- 产出物：本报告、`dwauth_candidates.json`、`_hunt_archives.py`、`_hunt_text.py`
  （脚本纯 ASCII）、中间结果 `_hunt_archives_result.json`、`_hunt_text_result.json`

---

## 0. 结论摘要（先看这里）

1. **全盘 `dwauth.ini` 命中数 = 0。** 五个盘符逐一递归搜索，全部 0。
2. **压缩包内 `dwauth.ini` 命中数 = 0。** 全盘 4,623 个压缩包，名称匹配 263 个，其中可打开的 zip 41 个，
   全部 0；22 个 `GameCooperation.zip` 内也 0。
3. **日志里没有 `dwauth` 读取报错。** `run_codol_001\runs\**\*.txt|*.log` = 0；`CODOLServer\logs\*` = 0。
4. **EXE 内没有硬编码大厅地址。** 只有格式串 `https://%s:%d/auth/`（VA `0x00D5A2CC`），
   即 host/port 在运行时由 `dwauth.ini` 的字段 3 / 字段 4 填入。**这解释了为什么全盘搜不到原始值。**
5. **本机找不到任何可归因于 `dwauth.ini` 字段 3/字段 4 的原始取值。**
   所有找到的 QQ 域名都属于 TCLS / IIPS / 统计 / 更新等**其它子系统**，不是 Demonware 大厅。
6. 因此：**原始 `dwauth.ini` 在本机不可恢复。** 候选文件里的条目全部标注为低/无置信度参考，
   不是原始值。

---

## 1. 全盘 `dwauth.ini` 文件名搜索

命令（每盘一次）：
```
Get-ChildItem -LiteralPath 'X:\' -Filter dwauth.ini -Recurse -Force -ErrorAction SilentlyContinue
```

| 盘符 | 命中数 | 耗时（秒） | 说明 |
|---|---|---|---|
| `C:\` | **0** | 143.75 | 全盘递归完成，未超时 |
| `D:\` | **0** | 17.11 | 全盘递归完成 |
| `E:\` | **0** | 1.11 | 全盘递归完成 |
| `F:\` | **0** | 23.69 | 全盘递归完成 |
| `G:\` | **0** | 12.57 | 全盘递归完成 |

补充（更宽的模式，覆盖被改名的情况）：
```
Get-ChildItem 'D:\BaiduNetdiskDownload\使命召唤OL' -Recurse -Force -File | Where {$_.Name -eq 'dwauth.ini' -or $_.Name -like 'dwauth*'}
```
- 命中数：**1**，唯一命中是 `CODOLServer\DWAUTH_ORIGIN_FINAL.md`（本项目自己的报告，不是配置）。

```
buildconfig.ini（与 dwauth.ini 同批被 WinMain 读取）
```
- 命中数：**0**。

---

## 2. 压缩包内容搜索

命令：`python CODOLServer\_subagents\_hunt_archives.py`

- 全盘压缩包总数（`.zip/.rar/.7z/.tar/.gz`）：**4,623**
- 名称/路径含 `cod` / `ol` / `iw4` / `使命召唤`：**263**

工具可用性：本机**没有 7z**（`7z`、`7za` 均未安装）；`.rar` / `.7z` / `.gz` 无法解压，
`.zip` 用 Python `zipfile` 处理。

| 类别 | 数量 | 结果 |
|---|---|---|
| 可打开的 zip | 41 | 全部列出条目 → `dwauth.ini` **0 命中** |
| 未打开（rar/7z/gz，无 7z 工具） | 222 | 无法检查，已在脚本结果中标记 `not-opened` |
| `GameCooperation.zip` | 22 | 每个 38 条条目，`dwauth.ini` **0 命中** |
| 与 CODOL 直接相关的压缩包 | 24 | `dwauth.ini` **0 命中** |

命中样例（均无 `dwauth.ini`）：
```
D:\...\COD OL\TCLS\plugins\GameCooperation.zip                  ok, 38 entries, dwauth=0
D:\...\run_codol_001\sandbox\TCLS\plugins\GameCooperation.zip   ok, 38 entries, dwauth=0
E:\CODOL_SANDBOX\RUN001\TCLS\plugins\GameCooperation.zip        ok, 38 entries, dwauth=0
F:\下载\COD5_1.4_CHS_GBT.7z                                     not-opened (无 7z)
F:\下载\Compressed\COD8最新联机补丁2.8.0.4.7.rar                 not-opened (无 7z)
```
说明：`F:\下载` 下的 COD5/8/10/12 压缩包是**其它使命召唤作品**，与 CODOL 无关，
即便打开也不含 CODOL 的 `dwauth.ini`。

---

## 3. Steam 正版 MW2 目录

路径：`G:\SteamLibrary\steamapps\common\Call of Duty Modern Warfare 2`（存在）

一层结构：
```
main\  zone\
bink2w64.dll  CoDCleaner.exe  installscript_10190.vdf  iw4mp.exe  4901944
localization.txt  logo.bmp  splash.bmp  steam_api64.dll  SteamAPIUpdater.dll
UpdateDLLWrapper.dll
```

递归找 `*.ini / *.cfg / *.txt / *.log / *.vdf` 及名称含 host/server/config 的文件：
- 命中数：**2**
  - `installscript_10190.vdf`（223 B，Steam 安装脚本）
  - `localization.txt`（2680 B，本地化文本）
- `dwauth.ini`：**0**（正版 MW2 是 Steam 版，用 Steam 后端，本来就不使用 CODOL 的
  `dwauth.ini`+Demonware 私有大厅配置）
- 含 host 的配置：**0**

---

## 4. IW4X 目录

| 目录 | 存在 | 结果 |
|---|---|---|
| `D:\BaiduNetdiskDownload\使命召唤OL\IW4X` | 是 | 只有 `启动器\` 与 `Client核心代码\`（iw4x-client 源码）。源码里只有 `ConfigStrings.cpp`、`ServerList.cpp`、`Server.cpp` 等**源码文件**，没有部署用 `dwauth.ini`；`dwauth.ini` 命中 **0** |
| `E:\IW4X` | 是 | 只有 `iw4x\ miles\ zone\ binkw32.dll iw4x.exe mss32.dll Unlinker.exe zonebuilder.exe`。递归找 `*.ini/*.cfg/*.txt/*.log` 及 host/server/config 名 → **命中数 0**；`dwauth.ini` **0** |

IW4X 使用自己的 `iw4x` 配置（服务器浏览器 / 直连），不走 CODOL 的 Demonware 大厅配置链，
因此这里不含原始 `dwauth.ini`。

---

## 5. 内容级搜索（小文本文件）

命令：`python CODOLServer\_subagents\_hunt_text.py`
范围：`CODOL` 工作区、`D:\BaiduNetdiskDownload\使命召唤OL`、`E:\CODOL_SANDBOX`、
`E:\IW4X`、Steam MW2。扩展名 `.ini .cfg .txt .log .xml .dat .json .jsonl .md .lst .vdf .key`，
只搜 <2MB 且非二进制的内容。

- 扫描文件数：**15,157**

| 关键词 | 命中数 |
|---|---|
| `dwauth` | **38** |
| `/auth/` | **24** |
| `DW-Ticket` | **4** |
| `auth_host` | **0** |
| `lobby` | **1,504** |
| `dirlobby` | **0** |
| `xxx.qq.com` 形式主机名 | **7,499**（去重后 224 个不同主机） |

### 5.1 `dwauth` 命中的真实性质（38 行）

按文件汇总：
```
15 | CODOLServer\SESSION_RECORD_20260925_DWAUTH.md      （本项目报告）
12 | CODOLServer\DWAUTH_ORIGIN_FINAL.md                 （本项目报告）
 5 | CODOLServer\KEY_CONTEXT_20260925.txt               （EXE 字符串 dump）
 2 | backups\CODOL_UNATTENDED_...\evidence\hits.jsonl   （EXE 字符串 dump）
 2 | run_codol_001\runs\EARLY_HANDLE_SCAN\hits.jsonl    （EXE 字符串 dump）
 1 | ...\UNATTENDED_SESSION_20260925.md                 （本项目报告）
 1 | CODOLServer\UNATTENDED_SESSION_20260925.md         （本项目报告）
```
**没有一行是配置文件内容**，全部是本项目自己生成的报告或 EXE 字符串转储。

其中最有价值的一条（EXE 内 VA `0x00DDBDBC`，来自 `_hunt_text_result.json`）：
```
online..dwauth.ini..%59s....%hu.....%x..stun.ini....buildconfig.ini
```
这直接证明：EXE 里只有**文件名 + 格式符**，没有地址字面量。

### 5.2 `/auth/` 与 `DW-Ticket`（大厅协议证据）

```
VA 0x00D5A2CC  https://%s:%d/auth/          ← 大厅鉴权 URL 模板（host/port 是占位符）
VA 0x00D5A158  DW-Ticket-Seed               ← Demonware 票据
0xD5A228       auth_task
```
命中均来自 EXE 字符串 dump / 本项目报告，**不含具体主机名或端口**。

### 5.3 关于 7,499 条 `.qq.com` 主机名

全部是 TCLS / IIPS / 统计 / 更新 / 安全组件 / 浏览器组件的域名，例如
`tcls.qq.com`、`tcls.rail.qq.com`、`down.qq.com`、`dump.gamesafe.qq.com`、
`stat.gamedl.qq.com`、`ctrl.iips.qq.com`、`stun1-tub.codol.qq.com`、
`plat.tgp.qq.com`、`ptlogin2.qq.com` 等。

> **没有任何一个是 Demonware 大厅主机名。** 已在 EXE 中显式搜索并确认零命中：
> `dwlobbyhost` / `dwlobbyip` / `blazehost` / `blazeip` / `lobbyhost` / `lobbyip` /
> `dirlobby` / `auth_host`（见 `CODOLServer\MAINLINE_RUNTIME_REVERSE_20260925.md`
> 第 23 行、`SUBAGENT_PROTOCOL_SPEC.md` 第 179 行）。

---

## 6. 已有抓包 / 日志

| 位置 | 命令 | 命中数 |
|---|---|---|
| `run_codol_001\runs\**\*.txt`、`*.log` | `Select-String -SimpleMatch 'dwauth'` | **0** |
| `CODOLServer\logs\*`（83 个文件） | `Select-String -SimpleMatch 'dwauth'` | **0** |

结论：**游戏在这些运行记录里从未报告过读取 `dwauth.ini` 的失败或路径错误。**
（原因见 `dwauth.ini` 的读取失败路径：fopen 失败后 7 个 sscanf 全不执行，
全局 `0x81A76A8` 保持空，后续只表现为 DNS 阶段失败 + `[100] 无法连接大厅服务`，
不会打印文件名。）

### 6.1 抓包里的 8080 会话不是大厅

`CODOLServer\_subagents\pcap_report.md` 中确实存在高流量 8080 会话，但均已排除：

| 目标 | DNS 归属 | 判定 |
|---|---|---|
| `116.130.228.169:8080` | 在 `pcap_dns_ipv6.json` 中**无任何域名映射** | 大流量传输，无 CODOL 大厅归属 → 排除 |
| `42.187.183.162:8080` | `stat.gamedl.qq.com` | P2P/统计 → 排除 |
| `111.206.149.85:8080/14000` | 无 CODOL 归属 | 通用流量 → 排除 |
| 8081 TQoS 通道 | 见 `SUBAGENT_QOS_KEY.md` | 与 `/auth/` 无关 → 排除 |

同时 `CODOLServer\TCLS_DIR_PROTOCOL.md` 已实测确认：
> 「**目录内容里没有 CODOL 大厅地址。** 774 字节里出现的唯一 URL 是 `www.qq.com:443;1004`，
> 这是网络质量测试用的公共 URL。」

---

## 7. TCLS / WeGame 配置（完整键值）

### 7.1 `COD OL\TCLS\config\dirserver.xml`（目录服务器 —— 不是大厅）
```xml
<DirServer count="5" SuccessfulServerID="1" SuccessfulPort="8080">
    <Server1 Catalog="" host="tcls.qq.com" />
    <Server2 Catalog="" host="123.151.176.103" />
    <Server3 Catalog="" host="119.84.150.46" />
    <Server4 Catalog="" host="183.61.224.121" />
    <Server5 Catalog="" host="101.91.63.192" />
    <portlist count="3" port1="8080" port2="5223" port3="10009">0</portlist>
</DirServer>
<RoleServer count="1" SuccessfulServerID="1" SuccessfulPort="">
    <Server1 Catalog="" host="" />
    <portlist count="1" port1=""></portlist>
</RoleServer>
```
`COD OL\TCLS\config\dirserverdynamic.ini`：
```ini
[DirServer]
successfulserverid=1
successfulport=5223
```

### 7.2 `COD OL\TCLS\config\VersionServerConfig.xml`（版本服务器 —— 不是大厅）
```xml
<versionserver version="1" count="13" SuccessfulServerID="1" SuccessfulPort="8001;9001;10001;8002;9002;10002">
  <Server1 host="tcls.rail.qq.com"/>
  <Server2 host="223.167.104.26"/>
  <Server3 host="220.249.243.189"/>
  <Server4 host="183.194.234.198"/>
  <Server5 host="183.192.199.25"/>
  <Server6 host="180.163.25.22"/>
  <Server7 host="14.215.138.14"/>
  <Server8 host="123.151.72.67"/>
  <Server9 host="123.126.122.65"/>
  <Server10 host="120.241.190.12"/>
  <Server11 host="116.128.163.239"/>
  <Server12 host="111.13.34.177"/>
  <Server13 host="101.89.38.73"/>
  <portlist port1="8001" port2="9001" port3="10001" port4="8002" port5="9002" port6="10002" count="6"/>
</versionserver>
```
`COD OL\TCLS\config\versionserverconfigdynamic.ini`：
```ini
[versionserver]
successfulserverid=10
successfulport=8002
```

### 7.3 `COD OL\TCLS\TenProtect\config\VersionServerConfig.xml`
```xml
<versionserver version="1" count="1" SuccessfulServerID="1" SuccessfulPort="8080">
    <server1 host="tasver.gamesafe.qq.com" />
    <portlist count="1" port1="80" />
</versionserver>
```

### 7.4 `COD OL\iips.ini`（本地资源端口 —— 不是大厅）
```ini
enable_iips=1
iips_url="http://127.0.0.1:8080/"
```

### 7.5 `COD OL\stun.ini`（与 dwauth.ini 并列被 WinMain 读取的另一个文件）
```
stun1-tub.codol.qq.com
stun2-tub.codol.qq.com
stun3-tub.codol.qq.com
```

### 7.6 WeGame TCLS（WeGame 平台自身，与 CODOL 大厅无关）
`WeGame\tcls\config\VersionServerConfig.xml`：
```xml
<versionserver version="1" count="4" SuccessfulServerID="1" SuccessfulPort="19080">
    <server1 host="dir-update.wegame.com.cn" />
    <server2 host="101.226.144.84" />
    <server3 host="183.194.190.113" />
    <server4 host="140.207.176.24" />
    <portlist count="2" port1="19080" port2="443"/>
</versionserver>
```
`WeGame\tcls\config\VersionServerConfigdynamic.ini`：
```ini
[versionserver]
successfulserverid=1
successfulport=19080
```
`WeGame\tcls\Tenio\vfs_config.ini`：`[QOS] PROJ_ID=0`
`WeGame\Tenio.ini`（WeGame 平台自身的 connd 服务器，**不是 CODOL 大厅**）：
```ini
pub_server_url_1=dir-update.wegame.com.cn:8865
pub_server_url_2=dir-update.wegame.com.cn:80
candidate_tgpsvr_1=101.91.92.149:443
```
`WeGame\WGLoginConfig.ini`：
```ini
HTTPS_HOST="https://www.wegame.com.cn/api/middle"
HTTP_HOST="http://www.account-auth.wegame.com.cn/api/middle"
```

### 7.7 TCLS 全部 ini 清单（共 45 个）
`COD OL\TCLS` 下 26 个 + `WeGame\tcls` 下 19 个，均已枚举；
其中 `.cfg`（`commonconfig.cfg` / `updateconfig.cfg` / `dirsystemconfig.cfg`）
为加密/压缩二进制，明文不可读，但**文件名与密钥已确认不含大厅地址**。
`COD OL\TCLS\config\prompt.ini` 中出现的唯一 URL 是官网 `http://codol.qq.com/index.shtml`
和 `http://fcm.qq.com/` —— 均为网页链接，不是服务器地址。

---

## 8. 综合判定：为什么原始取值不可恢复

```
WinMain VA 0x77EE40
  └ fopen("dwauth.ini","r")        @0x77EF64     ← 读取 EXE 同目录的本地部署文件
       ├ 字段3 "%59s" -> [0x81A76A8]   = 大厅 HOST
       └ 字段4 "%hu"  -> [0x81A9EC4]   = 大厅 PORT
            └ sprintf("https://%s:%d/auth/")   @0xD5A2CC   ← EXE 内只有模板
```

1. 地址**只在运行时从 `dwauth.ini` 读入**，EXE / DLL 内**没有**该值。
2. `dwauth.ini` 是**本地部署文件**，交付时随安装产生；删除即无痕，不进安装包，
   所以压缩包内也搜不到。
3. 本机五个盘符、24 个 CODOL 相关压缩包、全部沙箱/备份、全部日志与抓包，
   均无该文件、无该值。
4. 抓到的 8080 会话、TCLS 目录响应、IIPS 通道**全部**已排除，不是大厅。

> **最终判定：原始 `dwauth.ini`（字段 3 大厅 HOST、字段 4 大厅 PORT）在本机不可恢复。**
> 只能确认其**格式与语义**，不能确认真实取值。

---

## 9. 复现命令清单

```powershell
# 1) 全盘文件名
Get-ChildItem -LiteralPath 'C:\' -Filter dwauth.ini -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath 'D:\' -Filter dwauth.ini -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath 'E:\' -Filter dwauth.ini -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath 'F:\' -Filter dwauth.ini -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath 'G:\' -Filter dwauth.ini -Recurse -Force -ErrorAction SilentlyContinue

# 2) 压缩包
python CODOLServer\_subagents\_hunt_archives.py

# 3) 内容级
python CODOLServer\_subagents\_hunt_text.py

# 4) 日志
Get-ChildItem 'run_codol_001\runs' -Recurse -Force -File |
  Where-Object {$_.Extension -in '.txt','.log'} |
  Select-String -SimpleMatch 'dwauth'
Select-String -Path 'CODOLServer\logs\*' -SimpleMatch 'dwauth'
```

---

## 10. 附带产出
- `CODOLServer\_subagents\dwauth_candidates.json` —— 候选主机/端口，含来源、行号、置信度与理由
  （所有条目均标注为低/无置信度参考，**没有一条是原始值**）
- `CODOLServer\_subagents\_hunt_archives.py` / `_hunt_text.py` —— 纯 ASCII 搜索脚本
- `CODOLServer\_subagents\_hunt_archives_result.json` —— 263 个压缩包逐条结果
- `CODOLServer\_subagents\_hunt_text_result.json` —— 15,157 个文件、约 9,000 条命中逐条明细
