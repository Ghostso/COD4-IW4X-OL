# ICH-054 — Resource Trigger Validation

## 判定

```text
ICH054_STATUS          = B (Resource Trigger 位于 VM-hidden boundary)
RESOURCE_TRIGGER       = VM_HIDDEN
FF_ENTRY               = UNKNOWN (blocked by VM-hidden trigger)
ZONE_ENTRY             = UNKNOWN (blocked by VM-hidden trigger)
ASSET_ENTRY            = UNKNOWN (blocked by VM-hidden trigger)
TRIGGER_LOCATION       = Base.dll .tvm0 VM dispatch mechanism
EVIDENCE_LEVEL         = STRONG_CANDIDATE (排除法 + 30s x 多轮 runtime 一致)
RUNTIME_CORRELATION    = NOT_OBSERVED
HARD_STOP_REASON       = Trigger requires VM ISA recovery or debugger
NEXT_TARGET            = STOP
```

## 成功条件判定

### A. 找到合法 Resource Trigger → FF entry?

**NO。** 已系统排除所有可访问接口：

| Trigger 候选 | 测试方法 | 结果 |
|---|---|---|
| RM vtable[0..47] | 48 unique stubs | 0 calls in 30s (ICH-037/043) |
| IIPS_IsPackReady | passive observation | 0 calls (ICH-037/038/043/045) |
| IIPS_RequestPack | passive observation | 0 calls |
| IIPS_GetTotalPackSize | passive observation | 0 calls |
| IIPS_GetDownloadedPackSize | passive observation | 0 calls |
| IIPS_GetPackDownloadProgress | passive observation | 0 calls |
| iips_listpackages | passive observation | 0 calls |
| iips_syncpackage | passive observation | 0 calls |
| iips_syncfile | passive observation | 0 calls |
| CRITICAL_SECTION | initialized + observed | never used (ICH-037) |
| -q flag | A/B test | no difference (ICH-038) |
| WeGame/TCLS platform | module + thread observation | UI_BYPASS_CONFIRMED (ICH-045) |
| iips DllMain thread burst | thread tracking | platform init, not Engine trigger |
| Timer/waitable objects | passive observation | no evidence |
| Internal Engine state | dispatch table monitoring | 0 changes in 22s |
| Window/message | passive observation | no Engine correlation (ICH-044/045) |

### B. Resource Trigger 位于 VM-hidden boundary?

**YES。** 证据链：

1. **ICH-022**: 0x00CA0000 没有任何直接 caller（STATIC_CONFIRMED_ABSENCE）。Base.dll 36577 个 Engine gap refs 无一直接 call。
2. **ICH-026**: Dispatch table 在 IIPS Gate crossing 时原子性填充 96 entries。
3. **ICH-037~043**: Local RM gate crossed 后，RM vtable 0 calls，IIPS API 0 calls，dispatch table 0 changes，Slot 41 未执行。
4. **ICH-044**: Post-gate 的所有活动（18 modules, 16 threads）都是 WeGame platform UI 初始化，不触发 Engine Resource subsystem。
5. **ICH-045**: UI_BYPASS_CONFIRMED。Platform UI 子系统不构成 Engine initialization trigger。
6. **ICH-046**: Anchor A/B 是 VM bytecode 常量，不是 dispatch mechanism。Continuation 不可从静态 .tls 恢复。
7. **ICH-053**: Slot 41 的 caller 是 VM dispatch mechanism。没有 native caller 可恢复。

**结论**: Engine 的 Resource subsystem activation 由 VM dispatch mechanism 控制。
VM dispatch 是 Engine 所有函数的唯一调用路径。
没有可从外部（RM vtable / IIPS API / 平台回调）触发的合法 Resource Trigger。

## IIPS API ABI 记录

所有 IIPS API 在 Local RM v3 环境下的运行时状态：

| API | 调用次数 | 备注 |
|---|---|---|
| GetResourceManagerII | 1 (patched) | 返回 Local RM ptr |
| GetResourceManager | 1 (patched) | 返回 Local RM ptr |
| ReleaseResourceManagerII | 0 | Engine 未调用 |
| IIPS_IsPackReady | 0 | Engine 未调用 |
| IIPS_RequestPack | 0 | Engine 未调用 |
| IIPS_GetTotalPackSize | 0 | Engine 未调用 |
| IIPS_GetDownloadedPackSize | 0 | Engine 未调用 |
| IIPS_GetPackDownloadProgress | 0 | Engine 未调用 |
| iips_listpackages | 0 | Engine 未调用 |
| iips_syncpackage | 0 | Engine 未调用 |
| iips_syncfile | 0 | Engine 未调用 |

**ICH-027 的假设 "Engine → IIPS_IsPackReady → loadfastfile" 被运行时证据否定。**
Engine 在收到 RM 指针后不调用任何 IIPS API。

## 8189FEC 标记

```
Local RM 环境: 8189FEC = NO, Engine Gate = YES, Resource Event = NOT_OBSERVED
No Local RM:   8189FEC = YES, Engine Gate = NO, Resource Event = NOT_OBSERVED
```

8189FEC 与 Resource Event / FF / Zone / Asset 无直接关联。
它是上游 IIPS 初始化失败的诊断值。

## 硬限制确认

在不恢复 VM ISA / 不使用 debugger / 不绕过反调试的前提下：

- Engine dispatch mechanism 不可访问
- Engine subsystem activation 不可从外部触发
- 所有可访问接口（RM vtable 48 entries, IIPS API 11 函数, 平台回调）均不足以触发 Resource Event
- 这不是"缺少正确的 RM ABI"或"缺少正确的 IIPS 状态"
- 这是 **VM dispatch 是唯一入口** 的结构性限制

## 输出

- ICH054_DECISION.md
