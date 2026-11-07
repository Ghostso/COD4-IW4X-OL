# PUBLISHER_FILE_RECOVERY-001

> Publisher Files 恢复阶段 001
> 目标：定位原始 .info，建立恢复矩阵
> 只读搜索 + 静态证据，未修改任何文件

---

## 0. 结论摘要

```
ORIGINAL_PUBLISHER_FILES = FOUND_ORIGINAL
```

10 个 publisher `.info` 文件全部已经存在，位于：

```
D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\publisher_files\
```

失败 `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` 的真正原因不是文件丢失，
而是 Golden 冻结副本缺少 3 个数据目录：

```
GOLDEN-LOBBY-001\REF_LOBBY_KIT\
    publisher_files\   （缺失）
    player_profiles\   （缺失）
    user_files\        （缺失）
```

即 Golden 冻结时只冻结了"运行核心文件"，漏掉了服务端读取 publisher
配置所需的数据目录。

---

## 1. 文件来源定位

搜索覆盖：

```
COD OL\main\
COD OL\IIPS\IIPSDownload\
COD OL\ 根目录
CODOL_ML\
CODOLLauncher\
WeGame\
WeGameInstaller\
run_codol_001\
REF_LOBBY_KIT\                       ★ 命中
GOLDEN-LOBBY-001\REF_LOBBY_KIT\      （缺失数据目录）
backups\
backup_reverse_engineering\
```

命中位置：

```
REF_LOBBY_KIT\publisher_files\
  activities_v1.info
  broadcast.info
  configs_s.info
  daily_challenge_config.info
  market_ui.info
  market-down.info
  MOTD.info
  mp_playlists_shipRetail_1.0.0.info
  mp_playlists_shipRetail_release.info
  tlogconfig.info
  whitelist_tester.info
  manifest.json
```

`publisher_files\manifest.json` 对每个文件记录 name / encoding /
wireBytes / plainBytes / plainSha256 / wireSha256 / evidence。
其中 evidence 是反汇编地址（如 0x50dc10、0x50e500、0x50eb80、
0x66d1f0），说明这套文件是此前已经过静态逆向验证的 wire 格式
发行方配置，不是临时生成。

---

## 2. 客户端期望路径

这些文件由大厅服务在 `service=10 task=21`（发行方配置）时下发。
lobby_srv.log 明确记录请求顺序与文件名（10 个 .info）。

服务端读取路径（lobby_server.py）：

```
OUTDIR = os.path.dirname(os.path.abspath(__file__))          # line 257
p = os.path.join(OUTDIR, "publisher_files", basename(nm))    # line 533
if not os.path.exists(p):
    return ack("缺 %s" % nm)
```

因此：

```
EXPECTED_PUBLISHER_PATH =
    <lobby_server.py 所在目录>\publisher_files\<name>.info
```

成功/失败对比（决定性证据）：

- 根目录 `REF_LOBBY_KIT\lobby_srv.log`（18:11:07 成功基线）：
  `-> publisher mp_playlists_shipRetail_1.0.0.info (976 字节)`
  ... 全部 10 个成功下发
- Golden 目录 `GOLDEN-LOBBY-001\REF_LOBBY_KIT\lobby_srv.log`（20:02:22）：
  `-> 缺 mp_playlists_shipRetail_1.0.0.info` ... 全部缺失

结论：

```
EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 根因 =
    Golden 冻结副本缺少 publisher_files/ 数据目录
    （同时缺 player_profiles/ 与 user_files/）
```

---

## 3. 恢复矩阵

| File | Requested | Found | Source | SHA256(wire) | Restore Status |
|---|---|---|---|---|---|
| mp_playlists_shipRetail_1.0.0.info | YES | YES | REF_LOBBY_KIT\publisher_files | 4238EA58...B8847C60 | FOUND_ORIGINAL |
| activities_v1.info | YES | YES | 同上 | 58F1334B...BE264A5C | FOUND_ORIGINAL |
| broadcast.info | YES | YES | 同上 | 8BA57F9A...CBCBFC5 | FOUND_ORIGINAL |
| tlogconfig.info | YES | YES | 同上 | BB933651...5F73B7 | FOUND_ORIGINAL |
| market_ui.info | YES | YES | 同上 | 0EAF09C0...C260E6F8 | FOUND_ORIGINAL |
| market-down.info | YES | YES | 同上 | 8B66ED53...BA5C734 | FOUND_ORIGINAL |
| whitelist_tester.info | YES | YES | 同上 | A3FD6A39...2E8A538 | FOUND_ORIGINAL |
| MOTD.info | YES | YES | 同上 | 596CA111...587EA22 | FOUND_ORIGINAL |
| daily_challenge_config.info | YES | YES | 同上 | C4B393C6...E6D167E3 | FOUND_ORIGINAL |
| configs_s.info | YES | YES | 同上 | E4841FB8...FEDB24FB | FOUND_ORIGINAL |
| mp_playlists_shipRetail_release.info | 回退别名 | YES | 同上 | 4238EA58...B8847C60 | FOUND_ORIGINAL |

SHA256 与 manifest.json 的 wireSha256 完全一致，证明是原始 wire 文件。

同时缺失的其它数据目录（导致缺 the.json / public.result / secure.result）：

```
REF_LOBBY_KIT\player_profiles\
    public.result   33,428 B
    secure.result   32,983 B
REF_LOBBY_KIT\user_files\
    the.json            17 B
```

---

## 4. 为什么 Golden 冻结目录缺数据

Golden 手册 §0 明确写着："本 Golden 只冻结运行所需的那一部分"。
因此冻结时只保留核心代码文件，遗漏了业务数据目录
（publisher_files / player_profiles / user_files）。

```
PUBLISHER_FAILURE 根因 = GOLDEN_DATA_DIR_INCOMPLETE（CONFIRMED）
```

不是 publisher 文件本身丢失。

---

## 5. 恢复方案（未执行）

按纪律，本阶段不修改 Golden，也不擅自复制文件。

拟议 DEV-PUBLISHER-RESTORE 方案：

```
1. 复制根 REF_LOBBY_KIT 完整目录到 DEV-PUBLISHER-RESTORE\
   （含 publisher_files/ player_profiles/ user_files/）
2. 从 DEV-PUBLISHER-RESTORE\run_all.py 启动
3. 验证 publisher error 消失，10 个 .info 成功下发
4. 继续观察是否进入 playlist/content init，是否发出 6/14
```

待用户确认后执行。

---

## 6. 成功标准对齐

定位结果已满足"找到原始文件"；恢复动作尚未执行（需用户批准
建立 DEV 副本并启动）。

---

## 7. 纪律核对

```
Golden 修改              = 无
Lobby Server 修改        = 无
Battle Server 修改       = 无
4 个 patch 修改          = 无
KDF hook 修改            = 无
Booking response 发送    = 无
伪造 publisher 文件      = 无
ACE 绕过/关闭            = 无
TenProtect 关闭          = 无
文件复制/替换            = 无（仅只读搜索）
```
