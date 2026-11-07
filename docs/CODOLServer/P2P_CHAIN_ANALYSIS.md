# p2papp.dll 全链路分析（方案 C：QQ 号 + 上传链）

日期：2026-09-25
目标：`COD OL\IIPS\p2papp.dll`（2,043,960 B，ImageBase 0x10000000，构建戳 0x5163E0A4 = **2013-04-09**）
方法：PE 导入/导出 + 全文件字符串 + 调用者扫描 + DNS 实测交叉核对

---

## 0. 一句话结论

`p2papp.dll` **不是 CODOL 自研组件**，而是**腾讯通用的 P2P 下载中间件**
（同一份二进制同时被 QQ音乐 / QQ直播 / WeGame / TCLS / CODOL 复用）。
它做三件事：**上报玩家 QQ 号**、**占用上传端口做种**、**从腾讯服务器拉取远程配置**。

---

## 1. 基本画像

| 项 | 值 |
|---|---|
| 导出 | IP2PApp / IP2PCore / IP2PData / IP2PDbg / IHttpFile + GetP2PDownload / GetP2PDownload2 / GetP2PDownloadEx / GetP2PDownloadWithAppTypeByNew / DeleteP2P*（共 32） |
| 导入 | **WS2_32（29 个裸 socket 函数）**、KERNEL32(171)、ADVAPI32(11)、ole32、PSAPI、WINMM、VERSION |
| 网络方式 | **自己实现的 P2P**（非 libcurl/WinHTTP），BT 风格 |

---

## 2. 调用者（7 处，含 3 份独立副本）

```
COD OL\IIPS\Download.dll                       <- IIPS 下载引擎（动态 GetProcAddress）
COD OL\IIPS\IIPSRepair.dll                     <- IIPS 修复
COD OL\TCLS\Tenio\p2papp.dll                   <- TCLS 自带副本
COD OL\TCLS\Tenio\TenioDL\p2papp.dll           <- Tenio 下载器
COD OL\TCLS\Tenio\TenioDL\TenioDL.dll / .exe / _core.dll
COD OL\WeGameLauncher\TenioDL\p2papp.dll       <- WeGame 下载器
COD OL\WeGameLauncher\TenioDL\TenioDL*
（另：QMNetworkMgr.dll、TQMCenter.exe 各自含 SetQQ，属同类上报）
```

---

## 3. 行为链（逐条有字符串证据）

```
CP2PAppEx::CreateP2PTask:%s, startType %d         <- 建 P2P 任务
CP2PAppEx::fetchTorrent:%s                        <- 取 BT 种子
CP2PAppEx::OnGetTorrent ret=%d, id=%u,tptsize=%u  <- 拿到种子
CP2PAppEx::OnFetchTorrentTimeOut() try again ...  <- 失败重试
CP2PAppEx::CheckFileMd5                           <- 下载后校验

CP2PAppEx::EnableShared(bEnable,bUse1863), try to bind 1863 port    <- 绑 1863（做种/上传）
CP2PAppEx::EnableShared(bEnable,bUse1863), try to bind 28000 port   <- 绑 28000

[p2papi] SetQQ %u                                 <- 上报玩家 QQ 号
[p2papi] SetSpeedLimit type:%d, url:%s
[p2papi] application type:%u, local data size:%2f MB
[p2papi] Cache Path %s

CP2PAppEx::ReportStatisticAtUnit GetDataMgr()->GetStatistic()   <- 定时上报
CP2PAppEx::ReportStatisticAtClose %s                             <- 关闭上报
[VASHSTAT] uConnectUsedCount/uFirstDataCount/uTimeOutNumber      <- 连接质量统计
```

**端口占用**：1863（MSN/QQ 老端口）+ 28000。

---

## 4. 服务器端点表（编译期硬编码，按应用 profile 分组）

### 4.1 CODOL 实际使用的 profile（gamedl）★重点

```
config.gamedl.qq.com                 <- P2P 配置下发（远程控制上传行为）
ps2.gamedl.qq.com                    <- peer server（找 peer）
bk.ps2.gamedl.qq.com                 <- 备份
downloadtpt.gamedl.qq.com            <- HTTP 下载
bk.downloadtpt.gamedl.qq.com         <- 备份
stat.gamedl.qq.com                   <- 统计上报
```

**DNS 实测交叉核对**

```
config.gamedl.qq.com -> 42.187.183.203 / 42.187.183.154
ps2.gamedl.qq.com    -> 81.71.56.93
stat.gamedl.qq.com   -> 42.187.183.162
```
⇒ 这些域名**在运行期确实被解析过**，链是活的（之前的 DNS 缓存里就有）。

### 4.2 同文件内的其它 profile（证明是通用中间件）

```
QQ直播 : start/stat/ps/ts/bk.ps/config/bk.tptfarm/statfarm/psfarm/tptfarm.qqlive.qq.com
         configfarm.qqlive.qq.com、stun.qqlive.qq.com、bk.downloadtpt/uploadtpt.qqlive.qq.com
QQ音乐 : uptest/push/config/start/stat/uploadtpt/bk.ps/ps.qqmusic.qq.com
通用   : stun.qq.com、ps2.p.qq.com、bk.ps2.p.qq.com
```

### 4.3 配置项键名（服务端下发，控制上传）

```
EnableP2P / Enable0Mto2MP2P / P2PChannelMode / PeerCnt0Mto6M / PeerCnt6Mto10M
P2PMaxUploadSpeed / P2PMaxUploadClientCount / P2PSlideWinIncSpeedCtl
P2PSpeedPercentForHole / P2PSpaceForHttp / P2PUpSpeedForOptimizingHttp
P2PProjReportQosMode / QQMusicP2PUploadSpeed / P2PFarmDownloadSpeed
PEER_SERVER(_EX)(_BACKUP)-domain/-tcp-port/-udp-port
DOWNLOAD_TPT / UPLOAD_TPT / STAT / STUN / P2PNET / CONFIG (-domain/-tcp-port/-udp-port)
```

实现类/日志：CQueryConfig::Uninit、loadDefaultQQLiveConfig、OnGetServerP2PConfig、[%s]CONF, iP2PMaxUploadSpeed

---

## 5. 风险评估

| 项 | 评估 |
|---|---|
| 上报 QQ 号 | **是**（[p2papi] SetQQ %u）——隐私相关 |
| 占用上传带宽 | **是**（EnableShared 绑 1863/28000 + P2PMaxUploadSpeed） |
| 远程可控 | **是**（config.gamedl.qq.com 下发上传速度/通道模式/peer 数） |
| 定时上报 | **是**（ReportStatisticAtUnit / ReportStatisticAtClose） |
| 自研后门 | **否**——2013 年的通用 P2P 中间件，跨产品复用 |
| 与大厅/[100] 的关系 | **无关**——只服务资源下载，不参与大厅连接 |

**结论**：它是"腾讯系下载器的标准件"，**不是 CODOL 专属的可疑改造**。

---

## 6. 与写服务器的关系

`p2papp` 与我们要写的大厅服务器**解耦**：

- 它连的是 `*.gamedl.qq.com`（下载/CDN 面）
- 大厅走的是 `ied-tqos.qq.com`(->116.130.224.66:8000) + GDP/Blaze

⇒ **不需要**为 p2p 写服务器；只需知道它会在后台占端口/带宽。

---

## 7. 产物

```
CODOLServer\_mainline\_c_p2p_pe.py       PE 导入导出
CODOLServer\_mainline\_c_p2p_str.py      API/行为串
CODOLServer\_mainline\_c_p2p_users.py    调用者扫描
CODOLServer\_mainline\_c_gamedl.py       gamedl profile 端点表
```
