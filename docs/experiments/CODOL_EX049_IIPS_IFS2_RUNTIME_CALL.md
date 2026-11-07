# EX-049 IIPS to IFS2 Runtime CALL / Return Verification

## Final Classification

```text
IFS2_RUNTIME_LOAD_UNCONFIRMED
CREATE_IFS_RESOLUTION_UNCONFIRMED
CREATE_IFS_EXECUTION_UNCONFIRMED
CREATE_IFS_RETURN_UNRESOLVED
8189FEC_IFS2_CAUSALITY_UNCONFIRMED
IIPS_GATE_NOT_CROSSED
NEW_EXECUTION_NODE_NONE
OBSERVER_NO_DIVERGENCE
```

Normal `-q` runs reach the IIPS fatal popup and load `iips.dll`, but no
runtime evidence was captured for `IFS2.dll` load, `CreateIFSLibDll`
resolution, or execution. The chain therefore remains static L2.

## Method

Normal unattended `-q` run:

```text
launch command: codoMP_client_shipRetail.exe -q
working dir:   工具/EX035_DIR
observer:      CreateProcess + module/dialog enumeration
end:           terminate after popup capture
```

No debugger, no hook, no patch, no human click.

## P0: IFS2 LoadLibrary

```text
IFS2_RUNTIME_LOAD_UNCONFIRMED
```

`IFS2.dll` was not seen in the final module list. No LoadLibrary/Unload
event was captured by the non-invasive observer.

This does not prove IFS2 was never loaded; it may have been loaded and
unloaded before the snapshot.

## P1: GetProcAddress

```text
CREATE_IFS_RESOLUTION_UNCONFIRMED
```

Static evidence:

```text
GetProcAddress(CreateIFSLibDll) inside iips.dll
```

No runtime `GetProcAddress` event was captured.

## P2: CreateIFSLibDll CALL

```text
CREATE_IFS_EXECUTION_UNCONFIRMED
```

Static callsite:

```asm
0x10009770 mov esi, [0x10033014]      ; GetProcAddress
0x10009776 push 0x10034964            ; "CreateIFSLibDll"
0x1000977b push eax
0x1000977c call esi
0x1000977e test eax, eax
...
0x100097a1 lea ecx, [ebp+0x50]
0x100097a4 push ecx
0x100097a5 call eax                   ; call CreateIFSLibDll
0x100097a7 test eax, eax
```

Runtime execution was not captured.

## Parameter and Calling Convention

Static shape:

```text
argument: one stack/object pointer at [ebp+0x50]
call: indirect via EAX
return: EAX tested immediately
```

Calling convention not resolved from runtime behavior:

```text
CALLING_CONVENTION_UNRESOLVED
```

Address and pointers:

```text
iips.dll ImageBase 0x10000000
call site RVA ~0x9777
```

## P3: Return Value

```text
CREATE_IFS_RETURN_UNRESOLVED
```

No runtime EAX captured. The static branch shape is:

```asm
test eax, eax
jne continue
```

If EAX were zero, code would report:

```text
Failed to create ifs lib
```

No runtime path was observed.

## P4: DestoryIFSLibDll

Not reached in observed runtime evidence. Static resolution path exists:

```text
GetProcAddress("DestoryIFSLibDll")
```

Runtime resolution not confirmed.

## Module Timeline

```text
TenRpcs
GameRpcs
tcj
policyprobe
TenProxy
GbSpy
iips.dll
IFS2.dll NOT OBSERVED
iipsinit window
WIN_IIPS_INIT_ERROR / 8189FEC
```

This is not proof of causality.

## `8189FEC`

Continues to be classified:

```text
8189FEC = PACKED_OR_RUNTIME_GENERATED
```

No direct runtime link to IFS2 was established.

## Answer to Core Question

In normal `-q` runtime observation:

```text
IIPS did not provably resolve or call IFS2!CreateIFSLibDll.
```

The static chain exists in `iips.dll`, but the runtime chain remains
unconfirmed.

## Final Classification

```text
IFS2_RUNTIME_LOAD_UNCONFIRMED
CREATE_IFS_RESOLUTION_UNCONFIRMED
CREATE_IFS_EXECUTION_UNCONFIRMED
CREATE_IFS_RETURN_UNRESOLVED
8189FEC_IFS2_CAUSALITY_UNCONFIRMED
IIPS_GATE_NOT_CROSSED
NEW_EXECUTION_NODE_NONE
OBSERVER_NO_DIVERGENCE
```
