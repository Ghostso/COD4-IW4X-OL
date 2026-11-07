# ACE 反作弊组件 —— 深度拆解（静态）

日期：2026-09-25
方法：PE 导出/导入 + 签名 + UTF-16/ASCII 字符串 + 设备名提取（全只读）
换算：exe 字符串 VA = 文件偏移 + 0x714000

---

## 0. 身份

```
厂商:        AntiCheatExpert.com Limited  (ANTICHEATEXPERT.COM)
法人实体:    ACEVILLE PTE LTD
产品:        Anti-Cheat Expert (ACE)
SSC 源码线索: C:\data\landun\workspace\CommonComponent\ACE-SSC\...   ← "landun"(蓝盾)=腾讯代号
组件版本:    ACE-BASE/GAME/DRV32 = 1.0.2103.3746
             ace-ats32.dll      = 1.0.0.489 (产品名 "TIP")
             ACE-Service64.exe  = 29.8.2609.246
             SGuard64.exe       = 1.0.2508.45
全部组件 Authenticode 签名有效
```

---

## 1. 内核态（5 驱动，x64）

| 驱动 | 设备名 | 关键能力 |
|---|---|---|
| `ACE-BASE.sys` | `\Device\ACE-BASE`、`\DosDevices\Global\ACE-BASE`、混淆名 `\Device\{TF9AC...}` | FLTMGR(16) minifilter、HIDPARSE、NDIS、`MmMapIoSpace`、`\Device\PhysicalMemory`、`ZwOpenSymbolicLinkObject`、Ace 权限设置、NMI 回调、**KeBugCheckEx** |
| `ACE-GAME.sys` | `\Device\ACE-GAME`、`\DosDevices\Global\ACE-GAME` | HIDPARSE（Input/Output/Feature Report）、**PsSetCreateProcessNotifyRoutineEx**（进程回调）、符号链接、**KeBugCheckEx** |
| `ACE-ADVT.sys` | `\Device\ACE-ADVT`、`\DosDevices\Global\ACE-ADVT` | `ExCreateCallback/ExRegisterCallback`、`MmMapIoSpace(Ex)`、`\device\physicalmemory`、`IoRegisterShutdownNotification`、**KeBugCheckEx** |
| `ACE-CORE203.sys` | `\Device\d<16字节随机>`、`\??\e<16字节随机>`（**设备名随机化**） | `MmAllocateMappingAddress`、`KeBugCheck`、**KeBugCheckEx**、FLTMGR |
| `ACE-SSC-DRV64.sys` | `\Device\ACE-SSC-DRV64`、`\DosDevices\ACE-SSC-DRV64`；注册表 `\Registry\Machine\System\CurrentControlSet\Services\ACE-SSC-DRV64` | **cng.sys**(7) 内核加密、**fwpkclnt.sys**(10) **WFP 网络过滤**（"SSC Net Capture Callout/Filter/Sublayer"）、`FwpsCalloutRegister` 级、`ExEnumHandleTable`、`IoGetIommuInterfaceEx`、**KeBugCheckEx** |

### 1.1 蓝屏机制（已定性）

**5 个驱动全部 import `KeBugCheckEx`**：
```
ACE-BASE / ACE-GAME / ACE-ADVT / ACE-CORE203 / ACE-SSC-DRV64
ACE-BASE / ACE-ADVT / ACE-SSC-DRV64  另有 KeRegisterBugCheckReasonCallback
ACE-SSC-DRV64 字符串: "SSC64-BUGCHECK"
```
实测：Nash 17:47 `sc stop ACE-BASE/ACE-GAME` → 18:00 蓝屏 `0x01010002`。
⇒ **停/改 ACE 内核驱动 = 主动蓝屏（自毁式保护），绝对禁止。**

### 1.2 内核能力清单（能做什么）

| 能力 | 来源 | 影响 |
|---|---|---|
| 文件系统 minifilter | ACE-BASE / ACE-CORE203 (FLTMGR) | 可拦**任意文件读写**，可做完整性校验 |
| WFP 网络过滤 | ACE-SSC-DRV64 (fwpkclnt) | 可拦/看**任意网络流量** |
| 进程创建回调 | ACE-GAME / ACE-SSC-DRV64 (PsSetCreateProcessNotifyRoutineEx) | 我们启动的**每个进程都被记录** |
| 物理内存映射 | ACE-BASE / ACE-ADVT (MmMapIoSpace, \Device\PhysicalMemory) | 可**任意读写物理内存** |
| 句柄表枚举 | ACE-SSC-DRV64 (ExEnumHandleTable) | 可枚举**所有进程的句柄** |
| IOMMU 接口 | ACE-SSC-DRV64 (IoGetIommuInterfaceEx) | 硬件级 DMA 防护 |
| 内核加密 | ACE-SSC-DRV64 (cng.sys) | — |
| 输入设备 | ACE-BASE / ACE-GAME (HIDPARSE) | 检测外挂硬件宏 |

---

## 2. 用户态（Program Files\AntiCheatExpert\）

| 文件 | 大小 | 导出 | 关键导入 |
|---|---:|---|---|
| `ACE-Service64.exe` | 3249624 | — | WS2_32(34), WLDAP32(17), CRYPT32(6), NETAPI32(1), pdh(5), USER32(13), ADVAPI32(41) |
| `SGuard64.exe` | 7902680 | — | WS2_32(33), WLDAP32(17), pdh(6), dbghelp(1) |
| `SGuardSvc64.exe` | 2094552 | — | WINTRUST(1), CRYPT32(7) |
| `SGuardUpdate64.exe` | 4114904 | — | WS2_32(31), IPHLPAPI(1) |
| `Uninstaller.exe` / `Uninstall64.exe` | 904080 / 499032 | — | WININET(4) |

**插件（SGuard\x64\Plugins\）**

| 文件 | 大小 | 导出 |
|---|---:|---|
| `ACE-ATS64.dll` | 9046944 | CreateObject, DllEntry2, GetObject1/2, Init（cereal RTTI） |
| `ACE-CSI64.dll` | 5882264 | CreateObject + 10 无名 |
| `ACE-DFS64.dll` | 25261528 | CreateObject + 8 无名 |
| `ACE-DRV64.dll` | 26906072 | CreateObject + 7 无名 |
| `ACE-SSC64.dll` | 10952152 | CreateObject, Init |

**SGuard\x64\**：`ACE-Safe.dll`(8997264, DllEntry0..7/CreateObj)、`ACE-Trace.dll`(2377688, `init_bugtrace*`/`set_bugtrace_addr`/`set_user_stream`)

---

## 3. 游戏侧（COD OL\，x86）

| 文件 | 大小 | 导出数 | 作用 |
|---|---:|---:|---|
| `ace-ats32.dll` | 1758784 | 5 | **反篡改**；RTTI `CCodeAntiTamper`/`AntibotMainWorker`；WINHTTP；IsDebuggerPresent |
| `ACE-DRV32.dll` | 6835192 | 7 | 驱动装载器 |
| `PolicyProbe.dll` | 6855224 | 6 | **设备指纹**；RTTI `AntiCheatExpert::DeviceFingerprintService::MachineDataGenerator`；`GetBugReport` |
| `tvsd.dll` | 11932240 | **61** | TenProtect 驱动中枢：`LoadDriver2`/`RealLoadDriver`/`TenLoadDriver`/`TvsdQueryMem`/`TvsdGetProcInfo`/`TvsdGetThreadInfo`/`TvsdFileQuery`/`TvsdDirVer` … |
| `TCJ.dll` | 3158584 | 11 | 同 CSI64 |
| `TerSafe.dll` | 8280328 | 21 | 安全模块 |
| `TenSLX.dll` | 2675768 | 2 | 腾讯安全 |
| `TenSp.dll` | 164920 | 12 无名 | — |
| `TenProxy.dll` | 167592 | 1 (`Invoke`) | 转发层 |
| `VSDDrvDll.dll` | 11168832 | 4 | 驱动对象 |
| `BugTrace.dll` | 1029624 | 1 (`WriteUserDataToDump`) | 崩溃转储 |
| `GbSpy.dll` / `GBSpy.dll` | 538584 | — | 监控 |

---

## 4. 统一插件模型

绝大多数模块遵循同一导出约定：
```
CreateObject / CreateObj
DllEntry / DllEntry0..7 / DllEntry2
Init
GetObject1 / GetObject2
```
⇒ 存在统一插件宿主（用户态，疑似 `ACE-Service64.exe` / `SGuard64.exe`）。

---

## 5. 挂钩点与替换通道

```
加载者: codoMP_client_shipRetailBase.dll
        字符串 "ace-ats32.dll" @ file 0x1470CF7（位于其自解密区）

替换通道（Windows 官方 DLL 重定向，.local 优先）:
  COD OL\codoMP_client_shipRetail.exe.local\
  COD OL\codoMP_client_shipRetailBase.dll.local\
```

---

## 6. 替代可行性（综合）

| 目标 | 可行性 | 风险 | 理由 |
|---|---|---|---|
| 桩 `ace-ats32.dll` | 中 | **中高** | 仅 5 导出；但它是反篡改模块，可能自校验 + WINHTTP 上报 |
| 桩 `PolicyProbe.dll` | 中 | 中 | 仅指纹采集 |
| 桩 `tvsd.dll` | 低 | 高 | 61 导出，驱动中枢 |
| 桩 `ACE-DRV32.dll` | 低 | 高 | 驱动装载器 |
| 停/卸载内核驱动 | **不可** | **蓝屏** | 已实测 |

**核心障碍**：
1. 内核驱动可读物理内存 + 枚举句柄 + minifilter ⇒ **我们的任何文件/DLL 替换都在它视野内**
2. 反篡改模块自身可能校验
3. 任何异常都可能触发 `KeBugCheckEx`（自毁式保护）

---

## 7. 待深查

1. `ace-ats32.dll` 5 导出的**调用约定与参数**（Base.dll 怎么用）
2. Base.dll 是否**校验** `ace-ats32.dll` 哈希/签名
3. `ACE-Service64`/`SGuard64` 是否**监控该文件**（minifilter / 句柄）
4. `tvsd.dll` 61 导出的**调用者**
5. 各驱动的 **IOCTL 码**（与用户态服务的通信协议）
6. `ACE-CORE203` 的**随机设备名**生成规则（`\Device\d%02x...`）
