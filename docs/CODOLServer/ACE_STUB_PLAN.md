# ACE / TenProtect "空壳"方案 —— 技术形态与风险决策

日期：2026-09-25
目标（用户）：**让 ACE 以为启动正常、一切顺利，但实际上没有真正启动**

---

## 0. 重要前提：这里是**两套**反作弊并存

| 系统 | 组件 | 加载链 |
|---|---|---|
| **TenProtect (TP3/TAS)** | `Base.dll`(内嵌逻辑), `TerSafe.dll`, `tvsd.dll`, `VSDDrvDll.dll`, `TP3Helper.exe`, `TCLS\TenProtect\` | `Base.dll → TerSafe.dll → tvsd.dll → LoadDriver2/RealLoadDriver/TenLoadDriver` |
| **ACE (Anti-Cheat Expert)** | `ace-ats32.dll`, `ACE-DRV32.dll`, `C:\Program Files\AntiCheatExpert\`(5驱动+5服务+5插件) | `Base.dll → ace-ats32.dll`(反篡改) + `ACE-DRV32.dll`(驱动装载) |

两套**都会装内核驱动**，两套都有 `KeBugCheckEx` 自毁能力。

---

## 1. 已拿到 TAS 的**功能控制表**（Base.dll，调试串）

```
[LoadDriver]--skip load driver          <-- 存在"跳过装载驱动"分支
[LoadDriver]---LoadType123:%d           <-- LoadType 参数（决定装载方式）
[LoadDriver]--enter loader update / loader update success. / enter loader leave.
LoadDriverByService / SeLoadDriverPrivilege
[InstallAndStartDrv]--CreateServiceW / OpenServiceW / ChangeServiceConfigW / StartService
[LoadModuleByLoacl]--no driver is running on system. try to loading module id=%d
[LoadModuleByDownload]--...
[VerifyDrv] -- Verify Sum: %d
CheckModuleVersion / DisableRegShellCode / CheckKernalThread / CallDriverEachSecond
CheckLogThreadMsgBox / CheckPhookHeartbeat / WinObjCheck / CrossfireHook
DrvProtectThread / OpenProcesHookLibCheck / DisableDriverInterface / SuspendDisable
UserThreadProtect / ScanProcessTimers / ScanProcessHotKeys / MemmoryWatch / BehaviorTrace
RawDlStartKBDHook / DxInputHook / WriteRebootFlag / SetPassProcessId / TryUnload
Global\TenProtectDrvLoadMutex           <-- 驱动装载互斥体
```

**IOCTL 接口名（Base.dll 里）**
```
IOCTL_TESSAFE_INIT_TCJCALLBACK / IOCTL_TESSAFE_REV_TCJINFO
IOCTL_TESSAFE_IDTSETTING / IOCTL_TESSAFE_START_KEYBOARD_MONITOR / IOCTL_TESSAFE_START_PORTIO_MONITOR
IOCTL_GET_THREAD_STATUS / verifydrv / getversion
setpassqq / TryUnload
```

**驱动侧 API（Base.dll 调用）**
```
GetDrvLibVersion / GetDriverList / DrvReadFile / DrvGetFileSize / DrvOpenProcess
DrvEnumerateSystemDriver / DrvEnumerateProcess / DrvEnumerateProcessModules / GetDrvVersion
TP3DrvDll / ICreateIDrvObj
```

---

## 2. IOCTL 名字 → 能力对照（说明 ACE 在看什么）

| IOCTL | 含义 |
|---|---|
| `IOCTL_TESSAFE_IDTSETTING` | IDT（中断描述符表）设置 → **反内核调试** |
| `IOCTL_TESSAFE_START_KEYBOARD_MONITOR` | 键盘监控 |
| `IOCTL_TESSAFE_START_PORTIO_MONITOR` | 端口 IO 监控 |
| `IOCTL_GET_THREAD_STATUS` | 线程状态查询 |
| `verifydrv` | **驱动自校验** |
| `setpassqq` | 白名单（把 QQ 号设为 pass） |
| `TryUnload` | 卸载驱动 |

---

## 3. "空壳"方案的可行路径（按推荐度）

### 方案 A：桩掉 `ace-ats32.dll`（**推荐先做**）
```
通道: COD OL\codoMP_client_shipRetailBase.dll.local\  (Windows DLL 重定向，优先级更高)
桩件导出: CreateObject / DllEntry2 / GetObject1 / GetObject2 / Init
关键: Init 返回成功，其余返回成功/空对象
```
- 优点：**只有 5 个导出**，接口面最小；只针对 ACE 反篡改
- 缺点：它是**反篡改模块本身**，可能自校验 + WINHTTP 上报

### 方案 B：桩掉 `TerSafe.dll` / `tvsd.dll`（阻止驱动装载）
```
目标: 让 LoadDriver2/RealLoadDriver/TenLoadDriver 返回成功但什么都不做
```
- 优点：**直接从根上阻止驱动装载**，最接近"ACE 以为成功但没启动"
- 缺点：`tvsd.dll` **61 个导出**，`TerSafe.dll` 21 个，工作量大；且 `[VerifyDrv] -- Verify Sum` 说明有校验

### 方案 C：桩掉 `ACE-DRV32.dll`（阻止 ACE 驱动装载）
```
导出: CreateObject + 6 个无名序号
```
- 缺点：序号导出难对应；`ACE-Service64.exe` 可能自己装驱动

### 方案 D：改服务配置（**风险高，已排除**）
- `sc config` / `sc stop` → **蓝屏**（已实测）

---

## 4. 必须正视的三大障碍

1. **内核驱动仍在运行时会看到一切**
   `ACE-BASE.sys` 有 FLTMGR minifilter + `MmMapIoSpace` + `\Device\PhysicalMemory` + `ExEnumHandleTable`
   ⇒ 我们对任何 ACE 文件的替换，**都在它视野内**。

2. **反篡改模块自身可能校验**
   `ace-ats32.dll` 的 RTTI 有 `CCodeAntiTamper`，`tvsd.dll` 有 `[VerifyDrv] -- Verify Sum`
   ⇒ 桩件可能被哈希/签名比对发现。

3. **自毁式保护**
   5 个驱动全部 import `KeBugCheckEx`，`ACE-ADVT.sys` / `ACE-SSC-DRV64.sys` 还注册了 BugCheck 回调
   ⇒ 一旦判定被攻击，**直接蓝屏**（已实测 `0x01010002`）。

---

## 5. 建议的安全顺序

```
Step 1 (只读): 确认 Base.dll 到底加载哪些 DLL、按什么顺序
              —— 用现有全镜像 dump 手法（挂起前取句柄，不碰 ACE）
Step 2 (只读): 确认 ace-ats32.dll 的 Init 返回值语义（Base.dll 怎么判断成功）
Step 3 (备份): 备份全部待替换文件 + 记录签名/哈希
Step 4 (实验): 先桩 ace-ats32.dll（最小面），观察：
              - 游戏是否仍能启动
              - ACE 服务/驱动是否仍被拉起
              - 是否触发蓝屏/上报
Step 5 (实验): 若 Step 4 可行，再桩 TerSafe/tvsd 阻止驱动
```

**每步都必须：备份 → 可回滚 → 单变量。**

---

## 6. 需要用户明确的授权点

| 授权项 | 说明 |
|---|---|
| 替换游戏目录 DLL | `.local` 或原目录放桩件（**不改系统目录**） |
| 备份策略 | 源文件 → `backups\ACE_STUB_<ts>\` |
| 失败判据 | 若出现蓝屏/游戏拒启动，立即回滚 |
| 是否接受蓝屏风险 | 方案 B/C 有一定蓝屏风险 |

---

## 7. 产物

```
CODOLServer\ACE_COMPONENT_MAP.md              完整组件图谱
CODOLServer\_mainline\_ace_inv.py             组件清点
CODOLServer\_mainline\_ace_drv_str.py         驱动字符串
CODOLServer\_mainline\_ace_dev.py             设备名提取
CODOLServer\_mainline\_base_drv_str.py        Base.dll 驱动装载逻辑串
CODOLServer\_mainline\_tas_skip.py            skip load driver 上下文
CODOLServer\_mainline\_tas_cfg.py             配置/注册表串
```
