# ICH-047 — Engine Resource Entry 反向恢复 — Callchain

## Engine 资源链静态结构

```
Engine dispatch table (0x00E83B00, 96 slots, 8 bytes each)
    │
    ├── Cluster 1 (0x009B9390..0x009BA700, ~26 slots)
    │     Access pattern: this+0x20 (State/Object)
    │     包含 0x009B9C00 (confirmed state getter)
    │     地址范围紧邻 FF/Zone 字符串数据 (0x009B617E..0x009B6408)
    │
    ├── Cluster 2 (0x009BA5B0..0x009C0010, ~6 slots)
    │     Complex ops / Processing / Init
    │
    ├── Cluster 3 (0x009C12D0..0x009C1930, ~15 slots)  ★ Resource/Zone
    │     Access pattern: this+0x14
    │     ICH-025 将此标为 "Secondary Subsystem"
    │     ICH-025 将此标为 "Likely Resource/Asset/Zone manager"
    │     Evidence: WIN_LOAD_ASSET_ERROR, Zone_Alloc strings
    │
    ├── Cluster 4 (0x009C2A40..0x009C2E30, 2 slots)
    │     this+0x14 (Secondary Operations)
    │
    ├── Cluster 5 (0x009C37C0..0x009C3930, 6 slots)
    │     Large frames / Major Init
    │
    ├── Cluster 6 (0x009C4670..0x009C4E10, ~10 slots)  ★ Config/Dvar/FS
    │     Access pattern: this+0x4C
    │     ICH-025 将此标为 "Tertiary Subsystem"
    │     ICH-025 将此标为 "Likely Configuration/Dvar/FileSystem manager"
    │     Evidence: dvar_restart, config_mp.cfg strings
    │
    ├── Cluster 7 (0x009C61E0..0x009C6430, ~4 slots)
    │     FP operations
    │
    ├── Cluster 8 (0x009C6AA0..0x009C70D0, ~2 slots)
    │     Data processing
    │
    ├── Cluster 9 (0x009C8350..0x009CA2C0, ~8 slots)
    │     Extended operations
    │
    └── Cluster 10 (0x009CD630..0x009DB5F0, ~4 slots)
          Large frames / Major Subsystem
```

## 字符串 ↔ 函数空间关联

```
Engine gap (0x00994000..0x00CA789A)

字符串数据:
  0x009B617E = "%s.ff"            (FF extension)
  0x009B61E8 = DB_AllocXZoneMemory (Zone allocation ref)
  0x009B6408 = WIN_MAX_ZONE_ERROR
  0x009B63B8 = WIN_LOAD_ASSET_ERROR
  0x009BD0A0 = "code_pre_gfx_mp.ff" (first FF)
  0x009BDF74 = "%s\%s%s.ff"        (FF search path)

函数群:
  Cluster 1: 0x009B9390..0x009BA700  ← 紧邻 0x009B6xxx 字符串
  Cluster 3: 0x009C12D0..0x009C1930  ← 0x009BD0A0 在两者之间
  Cluster 6: 0x009C4670..0x009C4E10
```

**推断**：FF/Zone 字符串数据（0x009B617E~0x009B63B8）在地址上紧邻
Cluster 1（State Access，this+0x20）的函数代码。这说明 FF/Zone 的
错误处理和分配逻辑与 State Access subsystem 在同一函数群内。

**推断**：0x009BD0A0（code_pre_gfx_mp.ff）位于 Cluster 1 和 Cluster 3
之间。引用它的函数（即 FF loader）很可能在 Cluster 1 或 Cluster 3 内。

## Resource Object 布局

```
Root Object (runtime instance UNKNOWN)
 │
 ├── +0x00  vtable → 0x00E83B00 (96-entry dispatch table)
 ├── +0x14  Resource/Asset/Zone subsystem pointer
 │            → accessed by Cluster 3 (0x009C12D0..0x009C1930)
 │            → accessed by Cluster 4 (0x009C2A40..0x009C2E30)
 ├── +0x20  State Object pointer
 │            → accessed by Cluster 1 (0x009B9390..0x009BA700)
 ├── +0x4C  Config/Dvar/FileSystem subsystem pointer
 │            → accessed by Cluster 6 (0x009C4670..0x009C4E10)
```

## 静态证据等级

| 目标 | 等级 | 原因 |
|---|---|---|
| FF loader function | CANDIDATE | 字符串存在但具体引用函数未识别 |
| Zone init function | CANDIDATE | DB_AllocXZoneMemory ref 存在但 caller 未识别 |
| Asset DB entry function | CANDIDATE | error string 存在但 init function 未识别 |
| Resource Object layout | PARTIAL | +0x14/+0x20/+0x4C 分组确认，vtable 确认，runtime instance 未知 |
| FF_ENTRY_PRECONDITION | NOT_LOCATED | 需要识别 LoadFastFile caller 及其条件分支 |

## Runtime Activity

```text
RUNTIME_RESOURCE_ACTIVITY = NOT_OBSERVED
  Dispatch table 0 changes (post-gate 22s)
  RM vtable 0 calls
  IIPS IsPackReady 0 calls
  loadfastfile 0 calls
  FF/Zone/Asset operations = 0
```

## Hard Stop 判定

满足 Hard Stop 条件 1（只能得到字符串，没有函数语义升级到 CONFIRMED）
和 Hard Stop 条件 3（无法将 Engine function 与 Resource/Zone/Asset 建立可靠关系超过 CANDIDATE）。

不得扩大到全 Engine gap 扫描或全 VM 扫描。
