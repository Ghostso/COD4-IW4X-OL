# 03 — 路线 A：2697 原生服务端可用性评估

> 样本：2697 服务端 `codol_dedrun.exe` `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`  
> 客户端：`codoMP_client_shipRetail.exe` `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`  
> 仅静态分析；未启动服务端。

## 1. 路线内容

直接使用 2697 原生 `codol_dedrun.exe`，满足其：
- `codol_target2697` / `codol_target2697Registration` 配置；
- 资源对象与注册对象门控；
- runtime-assets、scripts、script-overlay；
- 网络/协议写入条件；
- 必要 CVar 和启动参数。

目标不是修改二进制，而是找到**合法、可复现且不绕过安全机制**的配置路径，让它作为本地测试服务端。

## 2. 已确认的门控链

来自 E1（VERIFIED）：

```text
_Cvar_FindVar("codol_target2697Registration")
  -> _CODOL_SetTarget2697ServerResources 0xC311B
       -> _CODOL2697_ReadRegistration 0xA3EA0
          -> fopen / sscanf / CRC32
          -> stack blob +0x6408 = 1
          -> memcpy 0xC814 -> 0x14973B00

_CODOL2697_WriteNativeGamestate 0xA3DAB
  -> 资源对象 +0x78F4 != 0
  -> 注册结构 +0x6408 != 0
  -> 失败：直接 return 0（不编码、不排队、不重试）
  -> 成功：_CODOL2697_WriteGamestate 0xA21B8
              -> _CODOL2697_WriteConfigstrings 0xA0468
```

关键事实：
- `client-registration2697.txt` 是真实文件格式，由 `fopen/sscanf/CRC32` 消费：VERIFIED。
- 默认不会读取；只有 `codol_target2697Registration` CVar 非空时才读取：VERIFIED。
- 2697 新通道有实际调用者，不是死代码：VERIFIED。
- 门控失败的运行时概率/完整配置路径：NOT-OBSERVED。

## 3. 启动配置依赖

现有脚本给出的 2697 初始化参数（源码证据，未运行）：

| 参数 | 作用 | 证据 |
|---|---|---|
| `codol_target2697=1` | 选择 2697 目标/archive 逻辑 | `run_native_connection.py`、`room_host2697.py` |
| `codol_target2697Registration=...\client-registration2697.txt` | 触发注册读取 | 同上 |
| `codol_clientExe=...\codol2697-static-candidate.bin` | 指定客户端/目标镜像资源 | 同上 |
| `fs_basepath` / `fs_homepath` | 资源与本地状态根 | 同上 |
| `codol_zonePath=...\runtime-assets\chinese` | 地图/模式 FF 资源 | 同上 |
| `codol_scriptPath` / `codol_scriptOverlay` / `codol_scriptNativeOverlay` | GSC 脚本与覆盖 | 同上 |
| `net_ip=127.0.0.1` / `net_port=28969` | 本地监听 | 同上 |
| `codol_profilePath`、`codol_admissionRequired` 等 | 本地 profile/准入 | 同上 |

`runtime-assets` 有 11,033 文件、约 1.797 GB；`scripts` 有 1,341 个 GSC 文件、约 19.15 MB；`script-overlay2697` 有 99 个文件、约 1.73 MB。它们与 2697 服务端目录配套：VERIFIED。

## 4. 2697 协议路径

服务端内同时存在：
- 2697 gamestate/configstrings：`0x03/0x04/0x06`；
- legacy：`0x02/0x03/0x05`；
- reliable 2697：`0x02 + long + short + data`；
- reliable legacy：`0x01 + long + string`；
- snapshot 外层选择 `0x05/0x06`，由 `_CODOL_Target2697ArchivesActive` 决定。

这些是服务端写入事实：VERIFIED。它们**不等于** 2.6.9.7 客户端一定走相同分支；客户端侧仍 BLOCKED。

## 5. 路线 A 的优势

- 协议实现与 2697 样本同源，不需要先把旧版协议硬改成 2697。
- 有完整的 2697 runtime-assets、scripts、附件注册表。
- 注册格式、双门控、发送链均在二进制中有直接证据。
- 适合作为**协议 oracle/对照服务端**，为路线 B 生成字段和黄金向量。

## 6. 路线 A 的依赖与风险

| 风险 | 说明 | 等级 |
|---|---|---|
| 注册门控合法配置未闭合 | 文件格式已知，但资源对象 `+0x78F4` 的来源和完整初始化时序未完全证明 | BLOCKED/NOT-OBSERVED |
| 目标 archive 激活条件 | `_CODOL_Target2697ArchivesActive` 依赖对象 `+0x34==0x16D`，业务语义未证明 | BLOCKED |
| 配置/资源初始化 | runtime-assets/GSC 加载依赖引擎内部状态；未运行验证 | NOT-OBSERVED |
| 客户端对应性 | 客户端 0x02→`0xA2E50` 分派和 0x06 读取未闭合 | BLOCKED |
| 二进制不可维护 | 无源码，修复/扩展需二进制分析 | 工程风险高 |
| 安全边界 | 不得绕过注册、保护或认证机制 | 硬约束 |

## 7. 路线 A 判定

**2697 原生服务端是最高价值协议事实源和潜在最短路径，但当前不能判定为可直接可用。**

要把它提升为可执行路线，最低需补充：
1. 完成 `codol_target2697Registration` 的完整初始化路径核对；
2. 静态确认资源对象 `+0x78F4` 的合法设置来源；
3. 在批准的前提下做隔离启动，观察是否越过初始化和 gamestate 发布门控；
4. 用真实抓包/日志确认客户端侧协议分支。

当前分类：**CANDIDATE/BLOCKED**，不作为第一实现底座。
