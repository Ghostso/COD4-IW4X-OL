# EX-036 IIPS `0x8189FEC` Failure Source and Global Consumers

## Final Classification

```text
IIPS_FAILURE_NODE_CONFIRMED
IIPS_FAILURE_SOURCE_UNRESOLVED
IIPS_MODULE_CHAIN_PARTIAL
NO_NEW_GLOBAL_CONSUMER_NODE
IIPS_FAILURE_NODE_SHARED
NO_TCLS_MAPPING_REQUIRED_BY_IIPS
```

The `0x8189FEC` failure is confirmed as a post-gate IIPS initialization
error node. The exact source inside IIPS is not closed because the callsite
is packed/encrypted and the observable error value is produced in a path
not fully resolvable with static raw-binary scanning.

## Observed Failure

Same in `-q` and `-qa`:

```text
WIN_NO_TCLS bypassed
IIPS initialization starts
iipsinit window
WIN_IIPS_INIT_ERROR
    text  : 初始化IIPS错误：8189fec
    title : 致命错误
    class : #32770
```

This confirms:

```text
IIPS_FAILURE_NODE_SHARED
```

## Static IIPS Cluster in EXE

The packed EXE contains the IIPS error-reporting cluster at file offset
`0x6B53A8`:

```text
WIN_IIPS_INIT_ERROR
WIN_IIPS_PREDOWNLOAD_ERROR
WIN_IIPS_INIT_FAILED
IIPS\iips.dll
0x%x
WIN_IIPS_DLL_ERROR
This program requires Windows NT!
Environment List Box
```

Address mapping:

```text
IIPS\iips.dll         RVA 0x9C93F5 VA 0xDC93F5
WIN_IIPS_INIT_ERROR   RVA 0x9C93A8 VA 0xDC93A8
WIN_IIPS_INIT_FAILED  RVA 0x9C93D8 VA 0xDC93D8
WIN_IIPS_DLL_ERROR    RVA 0x9C9408 VA 0xDC9408
Environment List Box  RVA 0x9C9294 VA 0xDC9294
```

The EXE also references:

```text
WIN_IIPS_DLL_ERROR     at file offset 0x18F35E
Environment List Box   at file offset 0x18F229
```

These are raw packed-data references and do not disassemble cleanly in
the on-disk EXE.

## IIPS DLL

`COD OL/IIPS/iips.dll`:

```text
base  = 0x10000000
entry = 0x2C288
```

Exports:

```text
0x1BC0 GetResourceManager
0x1C80 GetResourceManagerII
0x1C60 ReleaseResourceManager
0x1C60 ReleaseResourceManagerII
```

Static strings inside `iips.dll` that are relevant to the failure path:

```text
Global\IIPSShareState_MMF_
Global\IIPSShareState_Mutex_
ResourceManagerII
IIPSHostApp.exe
IFS2\\ifs2.dll
CreateIFSLibDll
IIPSERR_CACHE_INIT
IIPSERR_ERROR_INIT
LaunchIIPSHostApp failed
```

These identify the module’s internal resource manager and IFS/IFS2 init
subsystem, but do not by themselves map to `0x8189FEC`.

## IIPS vs IIPSClient.ini

`COD OL/IIPS/IIPSClient.ini` has an error table, for example:

```text
38=初始化失败, 正在修复中, 修复后请再重试初始化
39=初始化失败, 打开Host进程的共享内存出错
40=FileList出错导致的IFS加载失败
41=IFS DLL加载失败
42=IFS DLL加载后没找到需要的导出函数
```

Those values are not `0x8189FEC`, so the observed code is a different
error encoding from this simple table.

## `0x8189FEC`

No exact static `8189FEC` constant was found in the packed EXE or in
`iips.dll` byte scans. Therefore:

```text
0x8189FEC is likely a packed/VM-returned internal status code,
not a simple hardcoded constant in plaintext.
```

No `GetLastError`, `HRESULT`, or `NTSTATUS` mapping could be proven this
round.

## Global Consumers

Only the gate writes were confirmed from EX-031/EX-034 and EX-035:

```text
0x849413B = 1  after -q
0x849B500 = 1  after -qa
0x849B501 = 1  after -src=tgp
```

No additional runtime consumer/branch was observed before the IIPS
failure dialog. The static raw EXE is packed, and the consumer scan did
not produce a new plaintext reader list.

## Answers

1. Real IIPS init callsite: not statically confirmed; EXE has IIPS UI strings and `iips.dll` is the likely loaded resource manager module.
2. Where `0x8189FEC` is produced: unresolved; likely inside `iips.dll` or packed EXE VM path.
3. Direct return or wrapped code: unresolved; no direct `8189FEC` constant found.
4. Last successful external API before failure: unproven.
5. Key IIPS init parameters: unproven.
6. `-q` vs `-qa` before IIPS: no observed control-flow difference before IIPS failure.
7. First real consumer of `0x849413B`: not found this round.
8. First real consumer of `0x849B500`: not found this round.
9. First real consumer of `0x849B501`: not found this round.
10. `-src=tgp` effect after IIPS: no difference observed before the same IIPS failure.
11. New DLL/thread/native node: IIPS resource manager path indicated by `iips.dll` and `iipsinit` window, but module load at failure time was not captured in detail.
12. TCLS mapping required: not observed; no TCLS shared-memory mapping is needed to reach this failure.

## Final Line

```text
IIPS_FAILURE_NODE_CONFIRMED
IIPS_FAILURE_SOURCE_UNRESOLVED
NO_NEW_GLOBAL_CONSUMER_NODE
```

The next productive step is not more parameter enumeration. It is a
runtime observer for the `iips.dll` entry/export calls and the IIPSHostApp
pipe/shared-memory startup flow in the `-q` context.
