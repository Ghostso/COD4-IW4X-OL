# 交接：ACE 组件彻底逆向（备份静态拆解，含内核）

时间：2026-09-25
交接给：下一个对话
工作目录：D:\BaiduNetdiskDownload\使命召唤OL

---

## 0. 任务

**在备份副本上做 ACE 全套组件的彻底静态逆向，包括内核驱动。**

目标（用户原话）：**让 ACE 以为启动正常一切顺利，但实际上没有启动。**

纪律：
- 子代理**不得复用**（一个代理一个任务）
- **禁止** `sc stop/config/delete` ACE 驱动或服务（**实测会蓝屏 `0x01010002`**）
- 禁止改系统网络；禁止下载安装；禁止删除文件
- 脚本必须 **ASCII 纯文本**（PS 5.1 按 GBK 读 .ps1；**中文字面量会乱码，路径走参数传**）
- 提权代理：`python -X utf8 CODOLServer\_mainline\agent_client.py ping`（本会话末 pid 252 在线）
- 换算：**exe 字符串 VA = 文件偏移 + 0x714000**

---

## 1. 备份（已完成，可直接用）

```
backups\ACE_FULL_20260925_184421\
  files\     58 个文件（扁平命名：路径中 \ / : * ? " < > | 替换为 _）
  manifest.json    src/dst/size/mtime/sha256/copy_ok/verify_match
  service_config.txt
  services.txt
```
**58 个文件，COPY FAILED=0，VERIFY MISMATCH=0，共 215.9 MB**
（另有 21 个文件的旧备份 `backups\ACE_FULL_20260925_184223`，可忽略）

组成：AntiCheatExpert(18) + system32\drivers(3) + COD OL 根(19) + TGuard(6) + TenProtect(7) + Cross(1) + Tenio(1)

---

## 2. 保护壳分布（已识别，重要）

| 壳 | 文件 |
|---|---|
| **`.tvm0`**（TenProtect VM v0） | 多数 ACE 组件、TerSafe.dll、TenSLX.dll、ace-ats32.dll、ACE-BASE.sys、ACE-ADVT.sys、SGuard*、ACE-ATS64/CSI64/SSC64/DFS64、ACE-CORE203.sys |
| **`.tvm40`/`.tvm41`**（TP VM v4.x） | `tvsd.dll`、`TGuard\tvsd.dll` |
| **`.vmp0`/`.vmp1`**（**VMProtect**） | `ACE-DRV32.dll`、`VSDDrvDll.dll`、`TCJ.dll`、`PolicyProbe.dll` |
| 无壳（明文） | `TP3Helper.exe`、`ProtocalHandler.dll`、`TenProxy.dll`、`BugTrace*.dll`、`GbSpy.dll`、`SGuardSvc64.exe`、`Uninstaller.exe` |

**⇒ 磁盘上代码基本是加密/虚拟化的，capstone 反汇编不可信。**
**⇒ 要拿真代码必须做运行期 dump（但那是另一条路）。**

### 关键结论（已由本会话验证）
- 对 `ace-ats32.dll` 直接反汇编导出：得到**垃圾**（它是 `.tvm0` 保护）
- 对 `COD OL\codoMP_client_shipRetail.exe` 的 `.tp3` 直接反汇编：同样垃圾

---

## 3. 已确认事实（不用重查）

### 3.1 ACE 全组件（签名全部有效）
```
厂商: AntiCheatExpert.com Limited (ANTICHEATEXPERT.COM) / 法人 ACEVILLE PTE LTD
版本: ACE-BASE/GAME/DRV32 = 1.0.2103.3746
      ace-ats32.dll      = 1.0.0.489 (产品名 "TIP")
      ACE-Service64.exe  = 29.8.2609.246
      SGuard64.exe       = 1.0.2508.45
SSC 源码线索: C:\data\landun\workspace\CommonComponent\ACE-SSC\... ("landun"=腾讯蓝盾)
```

### 3.2 内核驱动（5 个，全 import KeBugCheckEx）
| 驱动 | 设备名 | 能力 |
|---|---|---|
| `ACE-BASE.sys` | `\Device\ACE-BASE`、混淆名 `\Device\{TF9AC...}` | FLTMGR(16) minifilter、HIDPARSE、NDIS、`MmMapIoSpace`、`\Device\PhysicalMemory`、NMI 回调、`KeRegisterBugCheckReasonCallback` |
| `ACE-GAME.sys` | `\Device\ACE-GAME` | HIDPARSE、`PsSetCreateProcessNotifyRoutineEx` |
| `ACE-ADVT.sys` | `\Device\ACE-ADVT` | `ExCreateCallback/Register`、`IoRegisterShutdownNotification`、`MmMapIoSpace(Ex)` |
| `ACE-CORE203.sys` | `\Device\d<16B随机>`、`\??\e<16B随机>` | `MmAllocateMappingAddress`、`KeBugCheck`、设备名**随机化** |
| `ACE-SSC-DRV64.sys` | `\Device\ACE-SSC-DRV64` | **fwpkclnt(10) WFP 网络过滤**（"SSC Net Capture Callout/Filter/Sublayer"）、cng.sys、`ExEnumHandleTable`、`IoGetIommuInterfaceEx`、`SSC64-BUGCHECK` |

服务：`AntiCheatExpert Service` → `SGuardSvc64.exe -autorun`（LocalSystem, Manual）
驱动服务：`ACE-BASE`/`ACE-GAME`/`ACE-ADVT`/`ACE-SSC-DRV64`（DEMAND_START）

### 3.3 游戏侧（x86）导出面
```
ace-ats32.dll   5 导出: CreateObject, DllEntry2, GetObject1, GetObject2, Init
ACE-DRV32.dll   7 导出: CreateObject + 6 无名序号
PolicyProbe.dll 6 导出: CreateObject, GetBugReport + 4 无名
tvsd.dll       61 导出: LoadDriver2/PleaseLoadDriver/RealLoadDriver/TenLoadDriver/
                        TvsdDirVer/TvsdFileQuery/TvsdGetModHandle/TvsdGetProcInfo/
                        TvsdGetThreadInfo/TvsdQueryCurThreadId/TvsdQueryMem/TvsdSetInfo ...
TCJ.dll        11 导出   TerSafe.dll 21 导出   TenSLX.dll 2   TenSp.dll 12   TenProxy.dll 1(Invoke)
VSDDrvDll.dll   4 导出: CreateVSDIDrvObj/ReleaseVSDIDrvObj
BugTrace.dll    1 导出: WriteUserDataToDump
```
**统一插件模型**：`CreateObject` + `DllEntry*` + `Init` + `GetObject*`

### 3.4 挂钩点
```
codoMP_client_shipRetailBase.dll 含串 "ace-ats32.dll" @ file 0x1470CF7（位于其自解密区）
DLL 重定向目录已存在:
  COD OL\codoMP_client_shipRetail.exe.local\
  COD OL\codoMP_client_shipRetailBase.dll.local\
```

### 3.5 TenProtect(TAS) 功能表（Base.dll 调试串，明文可读）
```
[LoadDriver]--skip load driver      [LoadDriver]---LoadType123:%d
LoadDriverByService / SeLoadDriverPrivilege
[InstallAndStartDrv]--CreateServiceW/OpenServiceW/ChangeServiceConfigW/StartService
[LoadModuleByLoacl]/[LoadModuleByDownload]  [VerifyDrv] -- Verify Sum: %d
CheckModuleVersion / DisableRegShellCode / CheckKernalThread / CallDriverEachSecond
CheckLogThreadMsgBox / CheckPhookHeartbeat / WinObjCheck / CrossfireHook
DrvProtectThread / OpenProcesHookLibCheck / DisableDriverInterface / SuspendDisable
UserThreadProtect / ScanProcessTimers / ScanProcessHotKeys / MemmoryWatch / BehaviorTrace
RawDlStartKBDHook / DxInputHook / WriteRebootFlag / SetPassProcessId / TryUnload
Global\TenProtectDrvLoadMutex
IOCTL_TESSAFE_INIT_TCJCALLBACK / REV_TCJINFO / IDTSETTING /
START_KEYBOARD_MONITOR / START_PORTIO_MONITOR / GET_THREAD_STATUS / verifydrv / getversion / setpassqq
DrvReadFile / DrvGetFileSize / DrvOpenProcess / DrvEnumerateSystemDriver/Process/ProcessModules
```

### 3.6 `[100]` 弹窗调用链（已定案，与 ACE 无关但同属项目）
```
VA 0x007EF210  cmp esi, 4                    ; dwLobby 状态==4
VA 0x007EF21E  push 0x00DE0610               ; "DW_DUPLICATE_LOGIN"
VA 0x007EF22E  call 0x774710                 ; 检查函数
VA 0x007EF23C  test eax,eax / jne 0x7EF253
VA 0x007EF253  push 0x00DE0640               ; "@SF_UI_DW_LIVE_CONNECTING_FAILED"
VA 0x007EF258  call 0x771240                 ; Scaleform 投递
```
取证 dump：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
（10,899,456 B = 覆盖 VA 0x400000..0xE65000，`read_fail_pages=0`）

---

## 4. 可用工具

```
CODOLServer\_mainline\agent_client.py              提权代理客户端
CODOLServer\_mainline\_dyn100_mem.py              pre-ACE 挂起取句柄 + 单模块内存采样
CODOLServer\_mainline\_pop3_live_dump.py          同上（另一个实现）
CODOLServer\_mainline\_dyn100_*.py                反汇编/字符串/指针/跳转表/弹窗表 分析
CODOLServer\_mainline\_ace_inv.py                  组件清点
CODOLServer\_mainline\_ace_drv_str.py             驱动字符串
CODOLServer\_mainline\_ace_dev.py                 设备名
CODOLServer\_mainline\_base_drv_str.py            Base.dll 驱动装载串
CODOLServer\_mainline\_ace_bk_layout.py           ★ 备份 PE 结构/区段熵（本会话新写）
CODOLServer\_mainline\_ace_bk_verify.py           备份完整性抽查

报告：
  CODOLServer\ACE_COMPONENT_MAP.md       组件图谱
  CODOLServer\ACE_STUB_PLAN.md           空壳方案（**注意：此文档含未验证推断，慎用**）
  CODOLServer\TQOS_SCHEMA_FULL.md        TQoS schema
  CODOLServer\MASTER_CALL_CHAIN.md       端到端调用链
```

---

## 5. 下一步（建议）

**关键问题：ACE 的"启动成功"是怎么判定的？**
不知道判据，就谈不上"骗过"。要回答：
1. `Base.dll` 到底**加载哪些 ACE DLL**、**什么顺序**（静态导入 or LoadLibrary）
2. `ace-ats32.dll` 的 `Init` **返回值语义**（Base.dll 怎么判断成功）
3. 失败时的**降级路径**（有没有"跳过但继续"）
4. 各驱动的 **IOCTL 码**与用户态服务的通信协议

**方法建议（按可靠性排序）**
1. **优先**：`Base.dll` 是**明文无壳**（本会话已确认），直接静态反汇编它的 `LoadLibrary`/`GetProcAddress`/`DeviceIoControl` 调用链 → **这条最可行**
2. 其次：各 ACE DLL 的**导入表**（导入表通常明文）+ 导出桩
3. 运行期 dump：需 pre-ACE 挂起取句柄（`_dyn100_mem.py` 已有能力），但**要扩展成多模块**（现在只 dump 主 exe）

---

## 6. 血泪教训（务必遵守）

1. **停/改 ACE 内核驱动 → 蓝屏 `0x01010002`**（ACE 自带 `KeBugCheckEx` 自毁）
2. **中文字面量写进 .ps1 会乱码**（PS 5.1 GBK）→ 路径一律走**参数**传，脚本纯 ASCII
3. **`.tvm0`/`.vmp0` 段的代码是加密的** → capstone 反汇编一律垃圾，**不要基于它下结论**
4. **字符串存在 ≠ 有分支可走**（"skip load driver"只是字符串，未验证能否触发）
5. **子代理不得复用**；一个代理一个任务

---

## 7. 勘误（必须看）

### 7.1 `Base.dll` **也是加壳的**（本会话末修正）

```
codoMP_client_shipRetailBase.dll  60,327,992 B  ImageBase 0x10000000
  .text   VA 0x00001000 vsize 0x742000  ent 7.22   开头: jmp 0x11A8AE9D  ← 跳到壳桩
  .rdata  VA 0x00743000 vsize 0x26C000  ent 5.63   ← 明文
  .data   VA 0x009AF000 vsize 0x153000  ent 5.35   ← 明文
  .tls    VA 0x00B0A000 vsize 0xED3000  ent 7.78   ← 加密
  .tvm0   VA 0x019DD000 vsize 0x1F5E000 ent 7.29   ← VM
  .reloc  VA 0x0393B000 vsize 0x56000
```

⇒ **代码区不可直接反汇编**；只有 `.rdata`/`.data` 的字符串可信。
⇒ 所以第 5 节"优先静态反汇编 Base.dll 的调用链"**不可行**，必须先做**运行期 dump**。

### 7.2 更正后的方法优先级

1. **各 ACE DLL / 驱动的导入表**（导入表通常明文）→ 可静态得到依赖关系
2. **运行期 dump**（pre-ACE 挂起取句柄）→ **唯一能拿到真代码的路径**，必须扩展成**多模块**
3. 关键字/字符串面分析（仅作线索，**不可作为结论**）

### 7.3 本会话未完成的验证（新对话别当成已知）

- `[LoadDriver]--skip load driver` 只是**字符串**，**未验证**能否触发/什么条件触发
- `LoadType123` 的取值语义 **未知**
- `ace-ats32.dll` 的 `Init` 返回值语义 **未知**
- `Base.dll` 加载 ACE DLL 的**确切调用点** **未反汇编验证**（已知只有字符串 `ace-ats32.dll` @ file 0x1470CF7）
- ACE "启动成功"的**判定条件** **未知** ← 这是"空壳"方案的核心未知
