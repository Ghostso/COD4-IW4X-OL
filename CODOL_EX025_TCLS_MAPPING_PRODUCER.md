# EX-025 TCLS_SHAREDMEMEMORY Producer Call Reconstruction

## Result

```text
Producer call reconstructed at L2 (static)
Dynamic CreateFileMappingW hook: NOT CAPTURED
Security descriptor: reconstructed at L2
Mapping bytes: not available dynamically
```

The strongest static producer path is:

```text
COD OL\TCLS\Tenio\TCLS.dll
  0x100406E0 mapping function
  -> name buffer starts with "TCLS_SHAREDMEMEMORY"
  -> [ebp+8] suffix argument
  -> 0x10040822 CreateFileMappingW
```

The parallel producer path in `WeGame\tcls\tcls_core.exe` is:

```text
0x4078F0 "TCLS_SHAREDMEMEMORY" + "%s%lu"
  -> 0x407D10 mapping helper
  -> 0x407D81 CreateFileMappingW
```

## Producer

### TCLS.dll (primary static candidate)

Mapping function:

```text
start:   0x100406E0
signature: thiscall, one DWORD argument at [ebp+8]
return:  CreateFileMappingW handle
```

Function body:

```text
0x10040717 InitializeSecurityDescriptor
0x10040723 SetSecurityDescriptorDacl
0x10040761 buffer += "TCLS_SHAREDMEMEMORY"
0x100407C8 [ebp+8] used as suffix argument
0x10040822 CreateFileMappingW
```

No direct `E8` caller, no VA/RVA function-table reference, and no export for this function was recovered. It is therefore invoked indirectly, and the concrete caller remains L2/L3-unknown.

### tcls_core.exe (second static candidate)

```text
0x4078F0 TCLS_SHAREDMEMEMORY + %s%lu
  -> 0x4079B0 0x407D10
0x407D81 CreateFileMappingW
```

`0x4078F0` has no direct static caller either. `tcls_core.exe` exports nothing in this PE scan.

## CreateFileMappingW Callers

```text
TCLS.dll      0x10040822
tcls_core.exe 0x407D81
```

## lpName

Static construction:

```text
TCLS.dll:
  wide buffer starts with "TCLS_SHAREDMEMEMORY"
  suffix comes from [ebp+8]

tcls_core.exe:
  format strings "TCLS_SHAREDMEMEMORY" + "%s%lu"

ClientBase.dll:
  format strings "TCLS_SHAREDMEMEMORY" + "%s%d"
```

Expected runtime form:

```text
TCLS_SHAREDMEMEMORY+<decimal PID>
```

This is L2 inference, not a dynamic string capture.

## PID Dataflow

In `TCLS.dll`, the mapping function does not call `GetCurrentProcessId`. It receives the suffix as a function parameter:

```text
[ebp+8] -> suffix -> lpName
```

The eight `GetCurrentProcessId` callers in TCLS.dll are in unrelated command-line/process-log paths, not in the mapping function.

Historical consumer evidence:

```text
game GetCurrentProcessId = 13600
mapping suffix = 13600
```

Therefore:

```text
consumer PID = game PID = mapping suffix
```

The producer PID is expected to be a launcher/TCLS-side process, but this is not dynamically confirmed.

## Mapping Parameters

Static reconstruction at both call sites:

```text
hFile                  = INVALID_HANDLE_VALUE (-1)
lpFileMappingAttributes = SECURITY_ATTRIBUTES at stack
flProtect              = PAGE_READWRITE (4)
dwMaximumSizeHigh      = 0
dwMaximumSizeLow       = 0x80000
lpName                 = TCLS_SHAREDMEMEMORY + suffix
```

## Security Attributes

At `0x10040717`:

```text
InitializeSecurityDescriptor(
  lpSecurityDescriptor,
  SECURITY_DESCRIPTOR_REVISION = 1
)
```

At `0x10040723`:

```text
SetSecurityDescriptorDacl(
  lpSecurityDescriptor,
  fDaclPresent = TRUE,
  pDacl = NULL,
  fDaclDefaulted = TRUE
)
```

Resulting SECURITY_ATTRIBUTES:

```text
nLength          = 0xC
bInheritHandle   = FALSE
lpSecurityDescriptor = descriptor with null DACL
```

Interpretation:

```text
null DACL with DACL_PRESENT grants broad access
the game/TenProxy process should be able to OpenFileMappingW
```

This is L2 static evidence. No runtime ACL access test was performed.

## Mapping Lifetime

Observed dynamic chain:

```text
Client.exe -> launcher.exe -> tgp_daemon.exe
  -> TASLogin.exe / wegame_env.exe / browser.exe / tcls_core.exe
```

Objects observed:

```text
<pid>TPF_Share_Mem
TCLSHOST_MUTEX_59C1948BC1838E7654172E7D2F159D64
```

Not observed in a 35-second window:

```text
TCLS_SHAREDMEMEMORY+PID
```

Conclusion:

```text
TCLS_SHAREDMEMEMORY is created at game-start dispatch, not launcher startup.
```

## First 0x1000 Bytes

No dynamic mapping was available, so no read-only dump of the first 0x1000 bytes was obtained.

Static producer-side observation in `tcls_core.exe`:

```text
[view+0x00] = 0x40
[view+0x04] = view+4
[view+0x08] = view+0x104
[view+0x0C] = view+0x104
```

This is L2 wrapper initialization, not a confirmed shared-memory protocol header.

## Q1. Real Producer

```text
STATIC: both TCLS.dll and tcls_core.exe contain equivalent producer code
L3: unresolved without dynamic hook
```

The direct name+CreateFileMapping pair in `TCLS.dll` is the primary static candidate.

## Q2. CreateFileMappingW Caller RVA

```text
TCLS.dll      0x10040822
tcls_core.exe 0x407D81
```

## Q3. Mapping Name Construction

```text
wide buffer initialized with "TCLS_SHAREDMEMEMORY"
  + decimal suffix from [ebp+8] / "%s%lu" / "%s%d"
=> TCLS_SHAREDMEMEMORY+<decimal>
```

## Q4. PID Source

The suffix is a caller-provided DWORD argument, not `GetCurrentProcessId` inside the mapping function. The caller is indirect and not statically resolved.

## Q5. Producer PID / Suffix / Game PID / Consumer PID

```text
consumer PID = game PID = mapping suffix (historic L3)
producer PID = unknown
```

## Q6. Mapping Creation Stage

Game-start dispatch. The 35-second launcher replay produced no `TCLS_SHAREDMEMEMORY`.

## Q7. Security Descriptor Impact

Static:

```text
null DACL + DACL_PRESENT
```

This is consistent with TenProxy opening the mapping from the game process. No runtime ACL denial/success test was captured.

## Q8. Mapping +0x0000

No dynamic bytes were captured. Static tcls_core writes `0x40` at `+0x0000` after mapping, but this is not confirmed as the consumer-visible protocol.

## Success Criteria

```text
SUCCESS-D (L2 static): security descriptor reconstructed
SUCCESS-A/B/C (L3): not achieved, no dynamic hook
```

## Evidence Levels

| Item | Level |
|---|---|
| TCLS.dll CreateFileMappingW call | L2 static |
| tcls_core CreateFileMappingW call | L2 static |
| lpName format strings | L2 static |
| suffix = [ebp+8] | L2 static |
| consumer OpenFileMappingW + game PID | L3 historic log |
| mapping size 0x80000 | L2 static |
| null DACL | L2 static |
| first 0x1000 bytes | unavailable |

## Remaining Unknowns

```text
Indirect caller that passes [ebp+8] into TCLS.dll mapping function
Producer process PID
Exact runtime lpName string capture
Mapping content consumed by TenProxy
Dynamic CreateFileMappingW hook
```

## Deliverables and Logs

Main reconstruction log:

```text
工具/logs/ex025_tcls_mapping_producer_20260917-100901.log
```

Name-builder scan:

```text
工具/logs/ex025_tcls_name_builder_20260917-105348.log
```

Module-load probe:

```text
工具/logs/ex025_module_load_probe_20260917-105557.log
```

Reproducible scripts:

```text
_dyn_stage1/ex025_producer_reconstruct.py
_dyn_stage1/ex025_name_builder.py
_dyn_stage1/ex025_module_load_probe.py
```
