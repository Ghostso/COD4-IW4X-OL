# RESTORE-005 — Group B / Group C Engine-side Semantic Recovery

## 判定

```text
RESTORE005_STATUS             = C (对象关系恢复成功，语义保持 UNKNOWN)
GROUP_B_ROLE                  = UNKNOWN (query/state accessor chain, possibly GFx)
GROUP_B_OBJECT                = CONFIRMED (nested: +0x14→+0x40→+0x90→+0x08)
GROUP_B_VTABLE                = NOT_LOCATED
GROUP_B_RESOURCE_RELATION     = UNKNOWN

GROUP_C_ROLE                  = UNKNOWN (bitfield + handler dispatch, possibly GFx)
GROUP_C_OBJECT                = CONFIRMED (+0x4C→+0x68 bitfield, +0x20 handler array)
GROUP_C_VTABLE                = CANDIDATE (slot 93: call [handler_array+index*4])
GROUP_C_FS_DVAR_RELATION      = UNKNOWN

B_C_RELATIONSHIP              = SIBLING (same composite object, different sub-objects)
COMPOSITE_OBJECT_MODEL        = CONFIRMED

TABLE_SEMANTIC_MAP            = PARTIAL (A=GFx confirmed, B/C=UNKNOWN, D=helpers)
RESOURCE_ENTRY                = NOT_LOCATED
ZONE_ENTRY                    = NOT_LOCATED
ASSET_ENTRY                   = NOT_LOCATED
GAME_INIT_ENTRY               = NOT_LOCATED

NEXT_TARGET                   = STOP (静态分析已到边界)
```

## Group B 语义分析 (13 functions)

### 统一访问链

所有 13 个函数通过相同的 4 层间接链访问：
```
this+0x14 → [+0x40] → [+0x90] → [+0x08]
```

### 功能分类

| Pattern | 函数数 | 行为 |
|---|---|---|
| GET/QUERY | 1 | 获取值并存入 arg1 (0x009C1660) |
| IS_READY (boolean) | 2 | 获取布尔状态 (0x009C1680, 0x009C16B0) |
| IS_NULL_CHECK | 1 | 检查 +0x1DC 字段 (0x009C37C0) |
| DEEP_OPERATION | 2 | 访问 +0x1D4 深层字段 (0x009C1880, 0x009C1920) |
| WRITE_OPERATION | 1 | 写入操作 (0x009C37F0) |
| MAJOR_OPERATION | 1 | 大 stack frame (0x009C3920) |
| STATE_SYNC | 1 | 复杂处理 + GFx event (0x009C2E30) |
| TABLE_LOOKUP | 1 | 有字符串引用 (0x009C14E0) |
| VARIANT_ACCESS | 2 | 不同的 offset 路径 (0x009C3860, 0x009C1580) |
| COMPLEX_HELPER | 1 | 不同的 callee (0x009BEAE0) |

### Group B 结论

所有函数操作同一个嵌套对象链，但具体语义（GFx 或 Engine Resource）不确定。

支持 GFx 的证据：
- RESTORE-002 确认 Cluster 3 的部分函数（同组）push GFx format strings
- 0x00831DF0 (Base.dll query helper) 可能是 GFx value accessor

支持 Engine 的证据：
- 无 GFx 字符串在 Group B 函数本身中
- 操作模式（query/set/check）符合状态管理接口

**无法区分。保持 UNKNOWN。**

## Group C 语义分析 (7 functions)

### 统一访问模式

```
this+0x4C = State/Config Object
+0x68 = DWORD bitfield
+0x3E = BYTE flag
+0x20 = pointer to handler array
+0x41 = BYTE index into handler array
```

### 功能分类

| Pattern | 函数数 | 行为 |
|---|---|---|
| GET_BIT (bit 4 of +0x68) | 1 | 读取 bitfield (0x009C8990) |
| BIT_MANIPULATION | 1 | 复杂位操作 on +0x3E/+0x68 (0x009C8350) |
| SET_FLAG (0x4000 on +0x68) | 1 | 设置/清除标志 (0x009C8FE0) |
| SET_FLAG (0x10 on +0x68) | 1 | 设置/清除标志 (0x009C8FA0) |
| TABLE_LOOKUP | 2 | 索引查表 (0x009DB1B0, 0x009DB0E0) |
| **VIRTUAL_DISPATCH** | 1 | call [handler_array+index*4] (0x009D61D0) |

### Group C 关键发现

0x009D61D0 (slot 93) 实现了一个 **virtual function dispatch**：
```
[this+0x4C] → [+0x20] = handler array pointer
[+0x41] = handler index (BYTE)
call [handler_array + index * 4]
```

这类似 GFx 的 event handler dispatch 或 Dvar 的 callback dispatch。

其余函数操作 +0x68 bitfield 的特定位（0x4000, 0x10），
这可能是 GFx display state flags 或 Engine 状态标志。

**无法区分 GFx 或 Engine Dvar/Config。保持 UNKNOWN。**

## Group B / Group C 关系

两者是同一复合对象的兄弟子对象：
```
Composite Object (ECX for all 96 functions)
 ├── +0x00  vtable = 0x00E83B00 (96 entries)
 ├── +0x14  → SUBOBJECT_A (Group B 访问) — 13 functions
 │            ├── +0x40 → Nested → +0x90 → +0x08
 │            └── +0x90 (direct)
 ├── +0x20  → State Object (Group A 访问) — 26 functions
 │            └── +0x14 → GFx Event Dispatcher
 ├── +0x24  → 另一个子对象 (少量函数访问)
 └── +0x4C  → SUBOBJECT_B (Group C 访问) — 7 functions
              ├── +0x68 → bitfield
              ├── +0x3E → byte flag
              └── +0x20 → handler array
```

## 最终 96-entry Semantic Map

| Group | Access Pattern | Slots | 语义 | 置信度 |
|---|---|---|---|---|
| A | this+0x20 → [State+0x14] → vtable[1] | ~26 | **Scaleform/GFx event dispatch** | CONFIRMED |
| B | this+0x14 → [+0x40] → [+0x90] | 13 | **UNKNOWN** (query/state accessor) | UNKNOWN |
| C | this+0x4C → bitfield/handler | 7 | **UNKNOWN** (flags + dispatch) | UNKNOWN |
| D | FP/array/misc | ~44 | helpers, arithmetic | UNKNOWN |

**96-entry table = COMPOUND INTERFACE 的分类得到进一步确认。**
它是一个包含多个子接口的复合对象的 vtable，
不是单一 Engine Root 或单一 GFx 对象的 vtable。

## 对项目方向的建议

RESTORE-001~005 五轮 Engine-side 分析的结果：

1. 96-entry table 是 **compound interface**（不是单一 Engine Root）
2. Group A (~26 slots) = GFx/Scaleform（CONFIRMED）
3. Group B (13 slots) = 嵌套 query/state accessor（UNKNOWN）
4. Group C (7 slots) = bitfield + handler dispatch（UNKNOWN）
5. Group D (~44 slots) = helpers（UNKNOWN）
6. 没有找到明确的 Resource/Zone/Asset/FF entry
7. 没有找到明确的 Game Init entry
8. 没有找到 Root Object 的 runtime address

**Engine-side 静态分析也已到达边界。**

96-entry compound interface 的语义在不使用 debugger 的情况下
无法进一步从 prologue 级别恢复。

要继续推进需要：
- 使用 debugger 理解 runtime 状态（已禁止）
- 恢复 PRCL 以让 Engine 自然执行到 Game Init（ICH-054~059 确认不可行）
- 或者找到新的分析角度

## 输出

- RESTORE003_ALL_FUNCTIONS.csv
- RESTORE005_DECISION.md
