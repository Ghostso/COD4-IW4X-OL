# CODOL 项目重构级节点剖析

生成日期：2026-10-04

范围：`D:\BaiduNetdiskDownload\使命召唤OL`

目标：把此前分散在逆向手册、阶段报告、CSV/JSON 证据、运行日志和实现代码中的
工程节点统一成一套可追溯模型，覆盖当前主链、已闭合旁链、未闭合分支、
工具链与证据链。

---

## 0. 结论摘要

整个项目不是单一大厅问题，而是六个相互依赖的工程域：

1. **客户端启动与平台交接域**
2. **反作弊 / TCLS / IIPS 环境域**
3. **`.ff` / `.ifs` 资源解密域**
4. **大厅协议域**
5. **本地服务端与网络重定向域**
6. **观测、实验与证据域**

当前真实主阻塞链已经收敛为：

```
客户端启动成功
  -> TCLS / IIPS / ACE 环境满足
  -> 本地认证与 3074 明文大厅通道建立
  -> 0x81 / 0x82 / 0x83 / 0x85 握手闭合
  -> st=5，DW 泵每帧运行
  -> [0xE59D20]=5 长期等待
  -> 0x622220 返回 0
  -> 0x7EF1FF 不写 [0x849BA34]=3
  -> DW 泵停在 index 1
  -> gate / cfgobj 不建立
  -> 大厅 UI 不进入
```

因此项目距离“进入大厅”不是一个单点补丁，而是：

**已闭合：环境启动、认证、大厅连接、握手密码学。**
**未闭合：等待态 `[0xE59D20]=5` 的外部推进事件，以及其后的配置对象与大厅 UI 链。**

---

## 1. 节点总览

本剖析把全部工程节点分为 9 层：

| 层 | 节点数 | 说明 |
|---|---:|---|
| L0 目标与边界 | 6 | 任务目标、停服前提、禁令、授权、验收判据、证据等级 |
| L1 外部进程与服务 | 12 | TCLS、IIPS、ACE、TQMCenter、GameRpcs、本地认证/大厅/平台服务 |
| L2 客户端二进制与模块 | 14 | 主 EXE、Base.dll、TCLS.dll、iips.dll、IFS/IFS2、ACE 系列、OpenSSL 等 |
| L3 启动与平台交接 | 16 | 命令行、共享内存、TAS/SHELL、TCLS 启动、DWAUTH、DNS、hosts、证书 |
| L4 大厅协议 | 28 | 0x81/0x82/0x83/0x85、帧格式、AES、HMAC、seq、arm、复位、看门狗 |
| L5 DW / 配置 / UI 状态机 | 22 | `st`、`dw`、`ui`、gate、cfg、cfgobj、`E59D20`、弹窗出口 |
| L6 资源与格式 | 18 | `.ff` 层一/层二、`.ifs`、`.tpa`、`.tp3`、`.tvm0`、`.tls`、zone 清单 |
| L7 服务端实现 | 16 | 认证、队列、明文大厅、TLS、证书、响应模板、SHM 发布、重定向 |
| L8 观测与实验工具 | 20 | AboProbe、主实验驱动、多轮驱动、抓包、状态采样、反汇编、注入探针 |
| L9 证据与交接产物 | 20 | 主手册、总报告、交接页、CSV、JSON、运行日志、镜像、节点报告、Canvas |

合计：**172 个工程节点**。

---

## 2. L0 目标与边界节点

| ID | 节点 | 状态 | 依据 |
|---|---|---|---|
| L0-01 | 复活 CODOL 至可进入大厅 | 未完成 | 总报告 §二 |
| L0-02 | 官方已停服，不存在官方应答样本 | 已确认 | 交接页 §一 |
| L0-03 | 禁止修改本机网络配置 | 硬边界 | 主手册 §1 |
| L0-04 | 禁止关闭 / 配置 / 规避 ACE、TenProtect | 硬边界 | 交接页 §二 |
| L0-05 | 允许运行内存写入、`.text` patch、断点、调试器 | 已授权 | 主手册 §1 |
| L0-06 | 验收判据：无断线弹窗且 `lobReq5ec` 递增 | 已定义 | 主手册 §6.5 |

---

## 3. L1 外部进程与服务

| ID | 节点 | 角色 | 状态 | 证据 |
|---|---|---|---|---|
| L1-01 | `codoMP_client_shipRetail.exe` | 游戏主进程 | 可稳定运行 110 s | 运行日志 |
| L1-02 | `TCLS` / `tcls_core.exe` | 启动、共享内存、配置交接 | 已补回，环境前置 | 总报告 §六 |
| L1-03 | `IIPSHostApp.exe` | IIPS 宿主 | 可启动 | 运行日志 |
| L1-04 | `iips.dll` / `IFS.dll` / `IFS2.dll` | 资源与平台桥 | 已恢复 | ICH/EX 系列 |
| L1-05 | `TQMCenter.exe` | 腾讯管家中心 | 启动但非主阻塞 | 运行日志 |
| L1-06 | `VSDDrvDll.dll` | ACE VSD 驱动对象 | 已加载 | 总报告 §六 |
| L1-07 | `ACE-DRV32.dll` | ACE 驱动 | 已加载 | 总报告 §六 |
| L1-08 | `ace-ats32.dll` | ACE ATS | 已加载 | 总报告 §六 |
| L1-09 | `tersafe.dll` / `policyprobe.dll` | ACE 辅助 | 已加载 | 总报告 §六 |
| L1-10 | `TenRpcs.dll` / `TenProxy.dll` | 腾讯平台 RPC / 代理 | 已加载 | 总报告 §六 |
| L1-11 | 本地认证服务 `127.0.0.1:3074` | `/auth/`、`/queue/` | 可用 | 最新交接 §6 |
| L1-12 | 本地明文大厅探针 `127.0.0.2:8446` | 大厅 TCP 应答 | 可用 | 最新交接 §6 |

---

## 4. L2 客户端二进制与模块

| ID | 节点 | 基址 / 文件 | 状态 | 说明 |
|---|---|---|---|---|
| L2-01 | 主 EXE | `0x00400000` | 运行时解密 | `.tp3` 加密，镜像 `image_best.bin` |
| L2-02 | `Base.dll` | `0x10000000` | 部分可分析 | 60.3 MB，含 OpenSSL |
| L2-03 | `TCLS.dll` | `0x10000000` 族 | 已反汇编 | 启动模板、KSA |
| L2-04 | `iips.dll` | 独立模块 | 已恢复 | 平台契约 |
| L2-05 | `IFS.dll` / `IFS2.dll` | 独立模块 | 已恢复 | 资源桥 |
| L2-06 | `IFS.dll` 原始版本 | 备份 | 已保存 | 恢复记录 |
| L2-07 | 主 EXE 内嵌 RSA 私钥 | VA `0xDAC4B0` | 已确认 | 1191 B DER |
| L2-08 | OpenSSL 1.1.1 / 0.9.8zg | Base.dll | 已识别 | AES / SHA1 |
| L2-09 | AES S-box / Te0 | Base.dll | 已定位 | `0x9CB670` 等 |
| L2-10 | `.tp3` | 主 EXE | 部分截断 | 仅含 0x62000 |
| L2-11 | `.tvm0` | 主 EXE | 未证明 VM | 高熵数据块 |
| L2-12 | `.tls` | Base.dll | 未解析 | 15.5 MB |
| L2-13 | `localization.txt` | 文本 | 已解析 | 弹窗字符串 |
| L2-14 | 反作弊栈完整性 | 5 模块 | 已闭合 | 补 TCLS 后 5/5 |

---

## 5. L3 启动与平台交接

| ID | 节点 | 状态 | 地址 / 文件 |
|---|---|---|---|
| L3-01 | TCLS 启动命令行模板 | 已还原 | `0x103C53CC` |
| L3-02 | `CreateProcessW` 调用点 | 已还原 | `0x10044AE4` |
| L3-03 | `TCLS_TASMEMORY_<pid>` | 已还原 | 0x7AC 加密 |
| L3-04 | `TCLS_SHELLMEMORY_<pid>` | 已还原 | 0x224 明文 |
| L3-05 | 客户端实际读取名 `TCLS_SHAREDMEMEMORY<pid>` | 已确认 | 拼写含 MEMEMORY |
| L3-06 | Tenio KSA | 已实现 | `tas_crypt.py` |
| L3-07 | TAS 密钥来源 | 已确认 | EXE 文件时间 |
| L3-08 | 离线启动器 | 已实现 | `codol_launch.py` |
| L3-09 | 共享内存发布器 | 已实现 | `_z7_publish_shm.py` |
| L3-10 | DWAUTH.INI | 已接管 | `formal-zone-*` |
| L3-11 | DNS 路由 | 已接管 | hosts + 本地服务 |
| L3-12 | `TCLS\` 172 文件 | 已补回 | ACE 栈前置 |
| L3-13 | `buildconfig.ini` | 缺失但非当前阻塞 | 旧分析 |
| L3-14 | `stun.ini` | 已分析 | STUN |
| L3-15 | 平台 TLS 证书 | 已生成 | `lobby_*.pem/key` |
| L3-16 | 启动 flake 清理 | 已固化 | `_z7_cleanup.py` |

---

## 6. L4 大厅协议节点

| ID | 节点 | 状态 | 地址 / 证据 |
|---|---|---|---|
| L4-01 | 0x81 握手 | 已闭合 | `LOBBY_READY_ONLY` |
| L4-02 | 0x82 / `+0x5FC` | 已闭合 | `LOBBY_5E8_READY` |
| L4-03 | 0x83 回显 | 已闭合 | `LOBBY_ECHO_READY` |
| L4-04 | 0x85 帧结构 | 已闭合 | 长度/类型/op/seq/IV/密文/tag |
| L4-05 | 发送侧 HMAC | 已闭合 | `codec_0420(obj+0x60C)` |
| L4-06 | 接收侧 AES | 已闭合 | `codec_02A0(obj+0x620)[4:20]` |
| L4-07 | codec 表 `0x02A0` | 已还原 | 20 B 表 + 索引 |
| L4-08 | codec 表 `0x0420` | 已还原 | 20 B 表 + 索引 |
| L4-09 | 连接对象 | 已确认 | `[[0x8269774]+0x4F4]` |
| L4-10 | 分发器 | 已定位 | `0xBA4430` |
| L4-11 | 接收校验器 | 已定位 | `0xBA3710` |
| L4-12 | 发送组帧 | 已定位 | `0xBA2A60` |
| L4-13 | 复位例程 | 已定位 | `0xBA3420` |
| L4-14 | 0x87 arm | 已定位 | `0xBA3590` |
| L4-15 | 0x89 业务 | 已定位 | `0xBA3600` |
| L4-16 | 内层解析器 | 已定位 | `0xBA0FF0` |
| L4-17 | `obj+0xC8` | 已确认 | 2 就绪 / 4 复位 |
| L4-18 | `obj+0x5E8` | 已确认 | 3 = 0x83 完成 |
| L4-19 | `obj+0x5EC` | 已确认 | 收包计数 |
| L4-20 | `obj+0x5FC` | 已确认 | 0x83 回显 |
| L4-21 | `obj+0x604` | 已确认 | 发送 provider |
| L4-22 | `obj+0x608` | 已确认 | 接收 provider |
| L4-23 | `obj+0x60C` | 已确认 | 发送 codec 源 |
| L4-24 | `obj+0x620` | 已确认 | 接收 codec 源 |
| L4-25 | `obj+0x640` | 已确认 | 分发判据 0xDC |
| L4-26 | `obj+0x644` | 未闭合 | arm 标志 0/1/2/3 |
| L4-27 | 内层首字节 0x87 | 未闭合 | 当前读到错误源 |
| L4-28 | 看门狗弹窗 | 已定位 | `0x7EF254` |

---

## 7. L5 DW / 配置 / UI 状态机

| ID | 节点 | 状态 | 地址 / 变量 |
|---|---|---|---|
| L5-01 | DW 泵 | 运行 | `0x7EF0D0` |
| L5-02 | DW 泵主循环调用点 | 已确认 | `0x808259` |
| L5-03 | DW 泵外层函数 | 已确认 | `0x808240` |
| L5-04 | 持续调用循环 | 已确认 | `0x4F8AD1` |
| L5-05 | UI 映射 | 已确认 | `0x7F25B0` |
| L5-06 | st 状态机 | 已确认 | `0x803780` |
| L5-07 | `st` | 实测 4→5 | `0x84ABA50` |
| L5-08 | `stp` | 实测 4 | `0x84ABA54` |
| L5-09 | `dw` | 停在 1 | `0x849BA34` |
| L5-10 | `idx` | 停在 1 | `0x849BA30` |
| L5-11 | `ui` | 0 | `0x849BA3D` |
| L5-12 | index 1 处理器 | 已定位 | `0x7EF1C8` |
| L5-13 | `dw=3` 写入点 | 从未执行 | `0x7EF1FF` |
| L5-14 | `0x622220` 门 | 返回 0 | 依赖 `E59D20` |
| L5-15 | `E59D20` | 停在 5 | `0x00E59D20` |
| L5-16 | `E59D20` 状态机 | 已定位 | `0x6212C0` |
| L5-17 | `E59D20` 分支块 | 已定位 | `0x621840` |
| L5-18 | 状态 5 处理 | 直接返回 | `0x6217E1` |
| L5-19 | `0x4A93E0` | 从未进入 | `0x82C4AEC` 恒 0 |
| L5-20 | gate | 恒 0 | `0x82C4A88` |
| L5-21 | cfg | 恒 0 | `0xC7AEAC0` |
| L5-22 | cfgobj | 恒 0 | `0x33E6A00` |

---

## 8. L6 资源与格式节点

| ID | 节点 | 状态 | 说明 |
|---|---|---|---|
| L6-01 | `.ff` 层一 | 已攻克 | 10/10 |
| L6-02 | XFileHeader | 已还原 | `IWff0100` |
| L6-03 | RSA-2048 块 | 已还原 | PKCS#1 v1.5 |
| L6-04 | AES-192-CTR 主体 | 已还原 | 整块小端自增 |
| L6-05 | AES 主密钥 | 已确认 | 全库唯一 |
| L6-06 | IV 结构 | 已确认 | 末两字节 00 00 |
| L6-07 | `.ff` 层二 | 未闭合 | `IWffs100` |
| L6-08 | 288 B 头扩展 | 未解 | 高熵 |
| L6-09 | zone 名偏移 | 已确认 | `+0x12C` |
| L6-10 | `.ifs` 内嵌 FF | 部分闭合 | 695/974 |
| L6-11 | `.tpa` | 已分析 | 资源包 |
| L6-12 | `.tp3` | 部分截断 | 主 EXE |
| L6-13 | `.tvm0` | 未证明 VM | 高熵 |
| L6-14 | `.tls` | 未解析 | Base.dll |
| L6-15 | zone 装载清单 | 已定位 | `0x4FCC00` / `0x4FCCA0` |
| L6-16 | `mp_playlists.ff` | 已解层一 | 样例 |
| L6-17 | 层一产物 | 已生成 | `_cleanout\ff_layer1` |
| L6-18 | 层二算法候选 | 未命中 | 压缩/AES 全否证 |

---

## 9. L7 服务端实现节点

| ID | 节点 | 状态 | 文件 |
|---|---|---|---|
| L7-01 | TLS 认证服务 | 可用 | `fake_auth_tls.py` |
| L7-02 | 队列服务 | 可用 | `/queue/` |
| L7-03 | 明文大厅探针 | 可用 | `lobby_plain_probe.py` |
| L7-04 | 大厅 socket 服务 | 可用 | `lobby_socket_server.py` |
| L7-05 | 响应模板 | 已实现 | `lobby_response.json` |
| L7-06 | 证书生成 | 已实现 | `mklobby_cert.py` |
| L7-07 | CA | 已生成 | `lobby_ca.pem` |
| L7-08 | 服务证书 | 已生成 | `lobby_server.pem` |
| L7-09 | SHM 发布 | 已实现 | `_z7_publish_shm.py` |
| L7-10 | DWAUTH 写入 | 已实现 | `_z7_dwauth.py` |
| L7-11 | hosts 管理 | 已实现 | `_z7_hosts.py` |
| L7-12 | 4 个兼容补丁 | 已实现 | `--compat4` |
| L7-13 | 0x87 方向修复 | 已实现 | `--patch-87-gate` |
| L7-14 | `644` 持续写 | 已实现 | `--poke-644-on-st5` |
| L7-15 | `g2f` 写 | 已实现 | `--poke-g2f-on-st5` |
| L7-16 | 多轮自动重试 | 已实现 | `_multiround.py` |

---

## 10. L8 观测与实验工具

| ID | 节点 | 状态 | 文件 |
|---|---|---|---|
| L8-01 | 观察器 | 核心工具 | `AboProbe.cs` |
| L8-02 | 提权包装 | 核心工具 | `elevated_ifs1_observer.ps1` |
| L8-03 | 网络抓取 | 核心工具 | `capture_elevated_network.ps1` |
| L8-04 | 主实验驱动 | 核心工具 | `_e57a5c_experiment.py` |
| L8-05 | 多轮驱动 | 核心工具 | `_multiround.py` |
| L8-06 | 提权代理 | 核心工具 | `elevated_agent.py` |
| L8-07 | 代理客户端 | 核心工具 | `agent_client.py` |
| L8-08 | 状态采样 | 已实现 | `ScanState` |
| L8-09 | EIP 采样 | 低命中 | `--eip-trace` |
| L8-10 | DW 时序采样 | 本轮新增 | `--dw-timeline` |
| L8-11 | 断点探针 | 被 ACE 阻断 | `--debug-launch` |
| L8-12 | 进程内存工具 | 已实现 | `procmem.py` |
| L8-13 | 句柄枚举 | 已实现 | `prochandles.py` |
| L8-14 | FF 解密器 | 已实现 | `ff_iw4_decrypt.py` |
| L8-15 | TAS 加密 | 已实现 | `tas_crypt.py` |
| L8-16 | 静态反汇编 | 已实现 | capstone 脚本族 |
| L8-17 | 抓包 ETW | 已实现 | AFD ETW |
| L8-18 | 网络 pktmon | 已实现 | pktmon |
| L8-19 | 清理脚本 | 已实现 | `_z7_cleanup.py` |
| L8-20 | 临时脚本库 | 保留 | `_mainline\*` 700+ |

---

## 11. L9 证据与交接产物

| ID | 产物 | 作用 |
|---|---|---|
| L9-01 | `HANDOFF_20260930_REVERSE_MANUAL.md` | 主手册 |
| L9-02 | `MASTER_REPORT_20261002.md` | 总报告 |
| L9-03 | `HANDOFF_20261002_TLDR.md` | 精简交接 |
| L9-04 | `HANDOFF_20261004_DW_PUMP_STAGE.md` | 最新 DW 卡点 |
| L9-05 | `REVERSE_ENGINEERING_SUMMARY.md` | 阶段总结 |
| L9-06 | `REVERSE_ENGINEERING_FULL.md` | 完整汇总 |
| L9-07 | `REVERSE_ENGINEERING_COMPLETE.md` | 反汇编全集 |
| L9-08 | `ICH001..ICH059` | ICH 证据系列 |
| L9-09 | `CODOL_EX001..EX068` | EX 证据系列 |
| L9-10 | `RESTORE001..006` | 恢复系列 |
| L9-11 | `run_codol_001\runs\IFS1_*` | 运行日志 |
| L9-12 | `CODOLServer\logs\E57A5C_*` | 服务端日志 |
| L9-13 | `image_best.bin` | 运行时镜像 |
| L9-14 | `ff_zonekeys.json` | FF 密钥 |
| L9-15 | `zonekey_der.hex` | RSA 私钥 |
| L9-16 | `_tcls_static_recovery_*.txt` | TCLS 反汇编 |
| L9-17 | `_tcls_focus.txt` | TCLS 聚焦 |
| L9-18 | `ICH041_FILE_CANDIDATES.csv` | 文件候选 |
| L9-19 | `ICH041_SHORTCUT_COMMANDS.json` | 命令表 |
| L9-20 | 本报告 + Canvas | 统一节点视图 |

---

## 12. 当前主链与真实缺口

### 12.1 已闭合

```
启动 -> TCLS/IIPS/ACE -> DWAUTH -> DNS/hosts
  -> 3074 auth/queue -> 0x81 -> 0x82 -> 0x83 -> 0x85
  -> 密码学（AES/HMAC/seq/IV/帧布局）
  -> st=5
```

### 12.2 未闭合

```
[0xE59D20]=5
  -> 缺少外部事件推进到 3/4/6
  -> 0x622220 返回 0
  -> 0x7EF1FF 不执行
  -> [0x849BA34] 停在 1
  -> 0x7EEBF0 -> 0x4A9850 -> 0x4A93E0 不执行
  -> gate / cfg / cfgobj 不建立
  -> 大厅 UI 不进入
```

### 12.3 未验证的下游

即使 `E59D20` 解除，仍需验证：

1. `0x4A93E0` 是否成功建立 `gate=1`。
2. `cfgobj` 是否成功解析配置。
3. 大厅 UI 资源是否加载。
4. 大厅首屏是否要求额外网络响应。

---

## 13. 风险与纪律

1. **区分已测量 / 已证伪 / 未知。**
2. **跨轮数据不可直接比较。** provider 密钥逐帧变化。
3. **不要把 `image_best.bin` 的 4.5% 覆盖外推。**
4. **不要重复已否证的加密层方案。**
5. **不要绕过 ACE / TenProtect。**
6. **不要只盯服务端应答，当前阻塞在客户端等待态。**

---

## 14. 推荐推进顺序

1. 定位 `[0xE59D20]` 从 5 到 3/4/6 的外部事件源。
2. 验证该事件是否由本地服务端某个响应触发。
3. 解除后观察 `dw=3`、`gate=1`、`cfgobj`。
4. 若仍不进入大厅，再查 UI 资源与大堂首屏。
5. 并行推进 `.ff` 层二，避免单线阻塞。

