# CODOL 本地写死协议 / 组件清单

日期：2026-09-25

## 0. 核心结论

**服务器协议 schema 本地写死，endpoint（host:port）运行时下发。**

`GDPOpenProtocol.tdr` 是完整游戏服务器/大厅协议定义，明文：

```text
文件       COD OL\GDPOpenProtocol.tdr
大小       438,856 B
magic      0x000b02d6
内含       343 条命令，592 个类型，39 个常量
```

索引产物：

```text
CODOLServer\GDP_PROTOCOL_INDEX.md
CODOLServer\GDP_COMMANDS.csv
```

## 1. 关键命令（GDPOpenProtocol.tdr）

```text
GDP_CF_REQ_ENTERSERVER / GDP_CF_RES_ENTERSERVER
GDP_CF_REQ_SCROLLSERVERLIST / GDP_CF_RES_SCROLLSERVERLIST
GDP_CF_NOTIFY_GAMESERVERPORTINFO
GDP_CF_NOTIFY_LOGIN
GDP_CF_NOTIFY_LOBBY_LEAVED
GDP_CF_REQ_CREATEROOM / RES_CREATEROOM
GDP_CF_REQ_ENTERROOM / RES_ENTERROOM
GDP_CF_REQ_JOIN_MATCH / RES_JOIN_MATCH
GDP_CF_REQ_START_MATCH / RES_START_MATCH
GDP_CF_NOTIFY_ROOMCREATED / ROOMOWNERCHANGED
GDP_CF_NOTIFY_MATCH_EVENT
GDP_CF_NOTIFY_SERVERSECTIONIDANDUIN
GDP_CF_NOTIFY_CHANNEL_ENTERED / ROOM_ENTERED
```

## 2. 其它本地协议文件

```text
TCLS\config\gic_cs.tdr
  GIC4TCLS2CS
  DirSvrHostList / DirSvrPortList
  VerSvrHostList / VerSvrPortList
  GameLoginRep / MacAddr / ZoneId / LoginCIP

TCLS\config\tacc_client_protocol.tdr
  AccCliProtocol
  TACCCliPkg / TACCCliPkgHead / TACCCliPkgBody
  Magic / Version / CmdID / ServerID / PublicData / PrivateData

TCLS\mmog_data.tdr
  VersionUpdateData / WorldID / ServerCheckList / ServerConf

Cross\Apps\VideoEditor\plat_proto.tdr
  TQosFlag / LoginAreaReq / RptTQosReq
  TCrsReqRptTQos / TCrsResRptTQos

TCLS\tacc_datadef.tdr
  tacc_public_info / tacc_private_info / roleinfo
```

## 3. 运行时组件归属

```text
游戏进程 codoMP_client_shipRetail.exe
  codoMP_client_shipRetailBase.dll   VM 宿主、平台 bootstrap
  GameRpcs.dll / TenRpcs.dll         RPC 层
  GDPOpenProtocol.tdr                服务器协议 schema

平台进程 TQMCenter.exe
  SSOPlatform.dll                    完整 AES（正向+逆向 S-box）
  SSOCommon.dll                      SSO 公共层

平台进程 IIPSHostApp.exe
  IIPSHost.dll / iips.dll / p2papp.dll   QoS/资源配置
  June.dll / ScriptManager.dll          脚本/组件宿主

网络代理 CrossProxy.exe / CrossShell.dll
  CrossShell.dll                      含 QoS + 字面 "8081"
  ProtocalHandler.dll                 含 QoS 协议表 + AES 解密侧
                                       SetKey @0x63DF0, KeyExpansion @0x78258

腾讯电脑管家组件 components\tclsqmfix\
  QMNetworkMgr.dll    POST http://masterconn.qq.com/q.cgi
                      CreateEncryptEngine / GetKeyArrayLen / QMGetTdMacID
  QMGreenPacket.dll   master.etl.desktop.qq.com / InstallGreenPacket
```

## 4. 重要排除

**8081 加密 UDP 不是 CODOL 大厅。**

```text
发送方组件 = components\tclsqmfix\QMNetworkMgr.dll / QMGreenPacket.dll
目标       = masterconn.qq.com/q.cgi（腾讯电脑管家服务）
用途       = QM/GreenPacket 遥测、设备指纹、加密上报
```

这解释了 8081 加密、无客户端可读响应、且对 `[100]` 无影响。

## 5. 下一步自动路线

```text
1. 解析 GDPOpenProtocol.tdr 的字段表（magic 0x000b02d6 同源容器）
2. 提取 GDP_CF_NOTIFY_GAMESERVERPORTINFO / ENTERSERVER / SCROLLSERVERLIST
   的字段顺序与类型
3. 按该 schema 生成服务器骨架（Python/C++）
4. 用 suspend_host_redirect harness 劫持 endpoint，验证客户端错误码推进
```
