# ICH-047 — Engine Resource Entry 反向恢复

## 判定

```text
ICH047_STATUS                 = CANDIDATE
FASTFILE_ENTRY                = CANDIDATE
ZONE_ENTRY                    = CANDIDATE
ASSET_ENTRY                   = CANDIDATE
RESOURCE_OBJECT_LAYOUT        = PARTIAL
FF_ENTRY_PRECONDITION         = UNKNOWN
RUNTIME_RESOURCE_ACTIVITY     = NOT_OBSERVED
NEXT_TARGET                   = STOP
```

## 分析总结

### 96-entry dispatch table 完整映射

从 ICH-026 的 runtime dispatch table capture 中，恢复了全部 96 个 slot 的
function address。按 ICH-025 确认的 10 个 subsystem cluster 分组：

| Cluster | Address Range | Access Pattern | Slots | Role | Resource Relevance |
|---|---|---|---|---|---|
| 1 | 0x009B9390..0x009BA700 | this+0x20 | ~26 | State/Object Access | Low |
| 2 | 0x009BA5B0..0x009C0010 | complex | 6 | Processing/Init | Low |
| **3** | **0x009C12D0..0x009C1930** | **this+0x14** | **~15** | **Resource/Zone** | **HIGH** |
| **4** | **0x009C2A40..0x009C2E30** | **this+0x14** | **2** | **Resource Ops** | **HIGH** |
| 5 | 0x009C37C0..0x009C3930 | large frame | 6 | Major Init | Low |
| **6** | **0x009C4670..0x009C4E10** | **this+0x4C** | **~10** | **Config/Dvar/FS** | **HIGH** |
| 7 | 0x009C61E0..0x009C6430 | FP | ~4 | Computation | Low |
| 8 | 0x009C6AA0..0x009C70D0 | data | ~2 | Processing | Low |
| 9 | 0x009C8350..0x009CA2C0 | extended | ~8 | Extended | Low |
| 10 | 0x009CD630..0x009DB5F0 | large frame | ~4 | Major Subsystem | Low |

### Resource/Zone/Asset 函数群

ICH-025 已确认 Cluster 3（0x009C12D0..0x009C1930，this+0x14）为
"Likely Resource/Asset/Zone manager"，Evidence: WIN_LOAD_ASSET_ERROR,
Zone_Alloc strings。

ICH-025 已确认 Cluster 6（0x009C4670..0x009C4E10，this+0x4C）为
"Likely Configuration/Dvar/FileSystem manager"，Evidence: dvar_restart,
config_mp.cfg strings。

### 字符串 → 函数空间关联

ICH-032 确认的资源相关字符串全部位于 Engine gap 内：

```
0x009B617E = "%s.ff"
0x009B61E8 = DB_AllocXZoneMemory ref
0x009B6408 = WIN_MAX_ZONE_ERROR
0x009B63B8 = WIN_LOAD_ASSET_ERROR
0x009BD0A0 = "code_pre_gfx_mp.ff"
0x009BDF74 = "%s\%s%s.ff"
```

这些字符串在地址上紧邻 Cluster 1（State Access, 0x009B9390..0x009BA700）
的函数代码。0x009BD0A0 位于 Cluster 1 和 Cluster 3 之间。

**推断**：引用这些字符串的函数在 Cluster 1 或 Cluster 3 内。
但具体的 `push 0x009BD0A0` / `mov eax, 0x009BD0A0` 等指令引用
未在本轮有限窗口内识别。

### 为什么不能升级到 STRONG_CANDIDATE

Hard Stop 条件 1：只能得到字符串，没有函数语义。

虽然 ICH-025 确认了 Cluster 3 是 "Likely Resource/Asset/Zone manager"，
但这是基于 **object access pattern**（this+0x14）和 **string proximity** 的推断。
我们尚未确认 Cluster 3 内任何一个具体函数**确实调用** LoadFastFile 或
DB_AllocXZoneMemory。

Hard Stop 条件 3：无法将 Engine function 与 Resource/Zone/Asset 建立可靠
关系超过 CANDIDATE。

具体原因：
1. 无法在 Engine gap 内搜索 `push 0x009BD0A0` 等 imm32 引用（需要反汇编 Engine gap，超出本轮范围）
2. 无法确认 dispatch table 中哪个 slot 对应 FF loader
3. 无法确认 Resource Object 的 runtime instance 地址（ICH-043 已确认无法恢复）
4. 无法建立 `vtable slot → function → FF/Zone/Asset` 的完整三级链

### Resource Object 布局

```text
RESOURCE_OBJECT_LAYOUT = PARTIAL

已确认:
  Root+0x00 = vtable → 0x00E83B00 (96-entry dispatch)
  Root+0x14 = Resource/Asset/Zone subsystem (accessed by Cluster 3+4)
  Root+0x20 = State Object (accessed by Cluster 1)
  Root+0x4C = Config/Dvar/FileSystem subsystem (accessed by Cluster 6)

未确认:
  +0x14 指向的对象的具体 layout
  +0x4C 指向的对象的具体 layout
  Root Object runtime instance address (ICH-043 确认不可恢复)
```

### FF Entry Precondition

```text
FF_ENTRY_PRECONDITION = UNKNOWN

原因: 无法识别 LoadFastFile 的 caller 及其条件分支。
需要反汇编 Engine gap 中引用 0x009BD0A0 的函数，
这超出本轮"有限窗口分析"的范围。
```

### Runtime Resource Activity

```text
RUNTIME_RESOURCE_ACTIVITY = NOT_OBSERVED

Post-gate 22s 内:
  Dispatch table changes = 0
  RM vtable calls = 0
  IIPS IsPackReady = 0
  loadfastfile = 0
  FF/Zone/Asset operations = 0
```

## 输出文件

- ICH047_FUNCTION_TABLE.csv (96 entries, cluster 分类)
- ICH047_RESOURCE_ENTRY.csv (resource subsystem candidates)
- ICH047_ZONE_ASSET_ENTRY.csv (zone/asset/FF entry candidates)
- ICH047_CALLCHAIN.md (static callchain structure)
- ICH047_DECISION.md
