# ICH-043 — Local RM Gate 后 Engine State Gate 定位

## 执行结果

### Baseline（Run A）

```text
Process lifetime      = 30.1s (stable, timeout)
Gate crossed          = YES (96 entries)
Dispatch confirmed    = 0xE83C18 = 0x9B9C00 (first cycle)
RM vtable calls       = 0
IIPS IsPackReady      = 0
IIPS RequestPack      = 0
loadfastfile calls    = 0
FF/Zone/Asset ops     = 0
Modules               = 149
Threads               = 64+ (implied by prior rounds)
Root Object address   = NOT_RECOVERED
Root +0x20/+0x14/+0x4C = NOT_WATCHED (root not recovered)
```

### Root Object 恢复尝试

Method 1：FUNC_TABLE 内部扫描，查找指向 TABLE_BASE (0x00E83B00) 自身的指针。
结果：不存在自引用。

Method 2：EXE .data 段定向搜索 dword == 0x00E83B00，共扫到 0 个候选。
根本原因：EXE 没有 .data 段。EXE 全部 section 均为 .tp3 / .tvm0：

```text
EXE sections (ImageBase 0x00400000):
  .tp3   VA=0x00001000  VS=0x008A689A
  .tp3   VA=0x008A8000  VS=0x0016DA70
  .tp3   VA=0x00A16000  VS=0x0DBB1CC0
  .tp3   VA=0x0E5C8000  VS=0x00000031
  .tp3   VA=0x0E5C9000  VS=0x00009228
  .tvm0  VA=0x0E5D3000  VS=0x00004000
  .tp3   VA=0x0E5D7000  VS=0x00082000
```

Root Object 的构造发生在 VM 侧，其地址在运行时由 VM 内部计算产生，
不落在任何可静态定位的 .data 段。因此无法在无 debugger / 不扩大扫描
范围的前提下恢复 Root Object 的运行时地址。

### Base.dll 侧静态分析（不扩展至运行时扫描）

在 Base.dll 静态文件中定位到 Engine dispatch table 地址的仅有的两处引用：

```text
Anchor A (dword 0x00E83B00, dispatch base):
  Section.VirtualAddress    = 0x00B0A000
  Section.PointerToRawData  = 0x00AFF800
  RVA                       = 0x018AE194
  RawOffset                 = 0x018A3994
  VA                        = 0x118AE194
  上下文                    = 孤立 dword，前后 ±0x100 无相关引用

Anchor B (dword 0x00E83C00, dispatch base+0x100):
  Section.VirtualAddress    = 0x00B0A000
  Section.PointerToRawData  = 0x00AFF800
  RVA                       = 0x015EC784
  RawOffset                 = 0x015E1F84
  VA                        = 0x115EC784
  上下文                    = Engine gap 地址密集序列
```

Anchor A 与 Anchor B 的 RVA 距离 = 0x2C1A10（约 2.76 MB）。
两处均位于 Base.dll 的 .tls 段（VM-generated 数据），且不在 .reloc 中，
因此静态上不具备运行时重定位。

## 相关状态变化

在 FUNC_TABLE / GLOBAL_E83C18 / RM_3BC 全部可 watch 的指定采样对象上，
30s 窗口内没有任何 DWORD/WORD/BYTE 差分事件。

Root Object 及其 +0x20 / +0x14 / +0x4C 子系统字段因无法恢复运行时地址，
未纳入本采样。

## FF / Zone / Asset 前置条件

仅能给出静态候选（STATIC_CANDIDATE），无 runtime correlation。
依据 Hard Stop 条件，不得升级。

## IIPS API 被动观测

```text
GetResourceManagerII        = patched (local return, 1 call)
GetResourceManager          = patched (local return, 1 call)
ReleaseResourceManagerII    = 0
IIPS_IsPackReady            = 0
IIPS_RequestPack            = 0
IIPS_GetTotalPackSize       = 0
IIPS_GetDownloadedPackSize  = 0
IIPS_GetPackDownloadProgress= 0
iips_listpackages           = 0
iips_syncpackage            = 0
iips_syncfile               = 0
```

## Hard Stop 判定

满足以下 Hard Stop 条件，立即停止：

1. Root Object 运行时地址无法恢复（禁止 debugger，禁止全 VM 扫描）。
2. 30s baseline 中没有任何与 FF/Zone/Asset 前置链相关的状态变化。
3. 只能得到静态候选，没有 runtime correlation。

## 最终字段

```text
ICH043_STATUS                 = COMPLETE
ENGINE_STATE_GATE             = NOT_LOCATED
BASELINE_REPRODUCED           = YES
ROOT_OBJECT_CONFIRMED         = NO
RESOURCE_OBJECT_CONFIRMED     = NO
CONFIG_OBJECT_CONFIRMED       = NO
RELEVANT_STATE_CHANGE         = NONE
FF_PRECONDITION               = NOT_LOCATED
ZONE_PRECONDITION             = NOT_LOCATED
ASSET_PRECONDITION            = NOT_LOCATED
IIPS_RUNTIME_ACTIVITY         = NONE
NEXT_TARGET                   = STOP_NO_FURTHER_SCAN
```
