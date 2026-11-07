# ICH-022 - Engine Bootstrap Call-Chain Recovery

## Objective

Identify who calls 0x00CA0000 and map the engine bootstrap call chain
from VM dispatch through engine initialization functions.

## Search Results: References to 0x00CA0000

### Raw code (RVA 0x1000..0x594000) search:

```text
call rel32 → 0x00CA0000:    0 results
jmp rel32 → 0x00CA0000:     0 results
push imm32 0x00CA0000:       0 results
mov reg, 0x00CA0000:         0 results
call [0x00CA0000]:           0 results
le32 0x00CA0000 in data:    16 results (all false positives / data coincidences)
```

### Data section (section 1 & 2) search:

```text
Pointers to engine gap in .data section 1:  0
Pointers to engine gap in .data section 2:  0
```

### Base.dll search:

```text
Total absolute references to engine gap: 36577
Meaningful instruction references: 14 (all data reads/writes, not calls)
```

### Conclusion: No static caller found

The function at 0x00CA0000 has NO statically recoverable caller from
the raw code or data sections. The caller must be:

1. **Inside the engine gap itself** (one decrypted function calling another)
2. **Via a function pointer computed at runtime** (VM dispatch)
3. **Via a vtable** (virtual call through an object populated at runtime)
4. **Via VM bytecode interpretation** (the VM generates the call target dynamically)

## Per-STOP-4: CALLER_NOT_STATICALLY_RECOVERED

The absence of a static caller does NOT mean 0x00CA0000 was not called.
ICH-021 confirmed it executed via global state change. The caller is
dynamically computed, most likely by the VM dispatcher in Base.dll .tvm0.

## Engine Code Function Classification

Based on ICH-020 captured bytes:

| Address | Pattern | Classification | Execution |
|---------|---------|---------------|-----------|
| 0x00994000 | Arithmetic/comparison | Computation logic | UNKNOWN |
| 0x009A0000 | test al,1 → je → call 0x9EE9B0 / call 0x9FA390 | Conditional dispatch | UNKNOWN |
| 0x00A00000 | Sequence of addresses (pointer table) | Vtable/function table | N/A (data) |
| 0x00AB4000 | Function prologue/epilogue | Standard function | UNKNOWN |
| 0x00B00000 | mov ecx,[esi+0x30] → call ecx → ret | **Virtual method dispatch** | UNKNOWN |
| 0x00C00000 | Floating point + arithmetic | Math/computation | UNKNOWN |
| **0x00CA0000** | mov eax,imm → mov [global],eax → ret | **Global initialization** | **CONFIRMED (t=6.848s)** |

### Engine-Internal Call Targets (from 0x009A0000)

The conditional dispatch at 0x009A0000 calls:
- `0x009EE9B0` (inside engine gap)
- `0x009FA390` (inside engine gap)

These are additional engine functions that can be added to the call graph.

## 0x009B9C00 Analysis

The value `0x009B9C00` stored by 0x00CA0000 into global 0xE83C18:

```text
Location: Inside the engine gap (RVA 0x5B9C00)
Address type: VA within PAGE_EXECUTE_READWRITE memory
```

Possible roles (not assigned a name per evidence discipline):

| Candidate | Likelihood | Reasoning |
|-----------|-----------|-----------|
| Object/context pointer | HIGH | Common pattern for subsystem initialization |
| Function table pointer | MEDIUM | Points into executable region |
| Subsystem descriptor | MEDIUM | Engine bootstrap stores subsystem refs |
| Static object | LOW | Would typically be in .data, not in code section |
| Vtable | LOW | Vtables usually contain multiple pointers |

## Engine Bootstrap Chain Model

```text
Base.dll .tvm0 VM Dispatcher
  |
  |  t≈5.075s: Decrypts code into 0x994000..0xCA789A
  |
  |  Runtime dispatch (mechanism: VM-generated CALL/JMP)
  |     [caller of 0xCA0000: NOT statically recovered]
  |
  +-- 0x00CA0000: Global init
  |     writes 0x009B9C00 → 0x00E83C18
  |     (t=6.848s, confirmed by ICH-021)
  |
  +-- 0x009A0000: Conditional dispatch
  |     calls 0x9EE9B0 or 0x9FA390 based on condition
  |     (execution time UNKNOWN)
  |
  +-- 0x00B00000: Virtual method dispatch
  |     calls [esi+0x30] via vtable
  |     (execution time UNKNOWN)
  |
  +-- ... (other engine functions)
  |
  |  t=7.630s: iips.dll loads (AFTER engine is already executing)
  |  t≈8.0s: IIPS QoS failure
  |  Engine remains partially initialized
```

## IIPS Position in Engine Init

```text
PRE_IIPS_ENGINE_FUNCTION_COUNT = 1 confirmed (0x00CA0000)
POST_IIPS_ENGINE_FUNCTION_COUNT = 0 confirmed

IIPS_POSITION_IN_ENGINE_INIT = 
  Engine bootstrap (global init) → IIPS load → IIPS failure
  
IIPS is NOT at the beginning of the engine init chain.
It appears AFTER initial engine bootstrap functions have executed.
IIPS likely gates a LATER stage of engine initialization
(resource loading, network, full game state).
```

## Hard Stop Assessment

```text
STOP-1 (caller of 0xCA0000 found): NOT MET
  (caller is dynamically computed, not statically recoverable)

STOP-2 (VM → Entry → ... → 0xCA0000 chain): PARTIALLY MET
  (VM → [dynamic dispatch] → 0xCA0000 is inferred but the
   intermediate steps are not statically recoverable)

STOP-3 (VM dispatcher → Engine function → 0xCA0000): NOT MET
  (same as STOP-2, intermediate dispatch not recovered)

STOP-4 (no static caller found): TRIGGERED
  CALLER_NOT_STATICALLY_RECOVERED
  Caller is likely VM-generated dispatch or runtime function pointer
```

## Final Fields

```text
ICH022_STATUS = COMPLETE

TARGET_FUNCTION = 0x00CA0000
TARGET_EXECUTION_CONFIRMED = YES (ICH-021)

DIRECT_CALLER_COUNT = 0 (static search)
INDIRECT_CALLER_COUNT = 0 (static search)
FIRST_RECOVERED_CALLER = NOT_RECOVERED (CALLER_NOT_STATICALLY_RECOVERED)

ENGINE_BOOTSTRAP_CANDIDATE = 0x00CA0000 (global init, writes subsystem pointer)
ENGINE_BOOTSTRAP_CHAIN = PARTIAL (VM → [dynamic dispatch] → 0xCA0000 → 0x9B9C00 stored)

VM_TO_ENGINE_STATIC_CHAIN = NOT_RECOVERED (no static path from VM to engine)
VM_TO_ENGINE_DYNAMIC_CHAIN = CONFIRMED (via ICH-020/021 causal evidence)

GLOBAL_009B9C00_ROLE = UNKNOWN (engine-internal pointer, likely object/context)
GLOBAL_00E83C18_ROLE = SUBSYSTEM_POINTER_STORAGE (stores engine subsystem ref)
GLOBAL_00E83C1C_ROLE = COMPANION_SLOT (zeroed by same function)

PRE_IIPS_ENGINE_FUNCTION_COUNT = 1 (0x00CA0000)
POST_IIPS_ENGINE_FUNCTION_COUNT = 0

IIPS_POSITION_IN_ENGINE_INIT = AFTER_INITIAL_BOOTSTRAP
  (IIPS loads after engine global init; gates later stages)

RUNTIME_ENTRY_CONFIDENCE = CONFIRMED (0xCA0000 executed)
NEXT_RESEARCH_DIRECTION =
  Read memory at 0x009B9C00 during runtime to determine what
  data structure it points to. This will reveal the first engine
  subsystem object and its type, enabling further bootstrap chain
  recovery through object analysis rather than code xref analysis.
```
