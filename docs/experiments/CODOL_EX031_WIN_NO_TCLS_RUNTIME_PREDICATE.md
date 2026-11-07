# EX-031 WIN_NO_TCLS Runtime Predicate

## Final Classification

```text
ERROR_UI_CALL_CONFIRMED
COMMANDLINE_CHECK_CONFIRMED
CLIENT_CONTEXT_CHECK_PARTIAL
NO_TCLS_MAPPING_OBSERVED
NO_PERSISTENT_WRITE_OBSERVED
FATAL_PREDICATE_RESOLVED
```

The runtime predicate that triggers the `WIN_NO_TCLS` fatal dialog is
reconstructed from live memory and decoded EXE code. The deciding check is
command-line argument context, not a parent-process or `Client.exe`
lookup. No persistent writes were observed.

## Method

Observation-only probes, no patches, no DLL injection, no fake TCLS, no
process-tree spoofing. CDB was not used to collect this evidence.

Probe scripts:

```text
_dyn_stage1/ex030_string_scan.py
_dyn_stage1/ex030_window_probe.py
_dyn_stage1/ex031_memory_probe.py
_dyn_stage1/ex031_runtime_dump.py
_dyn_stage1/ex031_predicate_dump.py
_dyn_stage1/ex031_array_dump.py
```

Logs are preserved under `工具/logs/`:

```text
ex031_memory_probe_20260917-123224.log
ex031_runtime_dump_20260917-124024.log
ex031_predicate_dump_20260917-124307.log
ex031_array_dump_20260917-124710.log
ex031_writer_dump_20260917-124950.log
```

## Runtime Symbol Map

All decoded addresses are runtime memory addresses from the normal direct
launch. The same RVAs on disk are packed/encrypted and do not disassemble
identically.

```text
EXE base               = 0x00400000
WIN_NO_TCLS token      = EXE+0x009DBF80
WIN_ERROR token        = EXE+0x009DBF74
"-q"                   = EXE+0x009DBF60
"-qa"                  = EXE+0x009DBF64
"-src=tgp"             = EXE+0x009DBF68
predicate function     = EXE+0x0037F580
localization lookup    = EXE+0x0037B0E0
error display          = EXE+0x0037FA70
cherry-picked caller   = EXE+0x0037F71A
argv array count       = 0x0196928C
argv array pointer     = 0x01969290
command-line producer  = EXE+0x00852724
internal IAT slot      = 0x00CA827C
```

## Predicate Disassembly

The selection function at `EXE+0x37F580` first scans the runtime argument
array for three tokens.

```asm
; scan argv array against "-q"
0077f5d7 mov ecx, 0xddbf60
...
0077f5f7 mov byte ptr [0x849413b], 1   ; -q found

; scan argv array against "-qa"
0077f632 mov eax, 0xddbf64
...
0077f657 mov byte ptr [esp+0xf], 1     ; -qa found
0077f65c mov byte ptr [0x849b500], 1

; scan argv array against "-src=tgp"
0077f69b mov eax, 0xddbf68
...
0077f6ca mov byte ptr [0x849b501], 1   ; -src=tgp found
```

The fatal branch is reached only when both command-line flags are missing.

```asm
0077f6e8 cmp byte ptr [0x849413b], 0
0077f6ef jne 0x77f727
0077f6f1 cmp byte ptr [esp+0xf], 0
0077f6f6 jne 0x77f727
0077f6f8 push 0xddbf74                ; "WIN_ERROR"
0077f6fd call 0x77b0e0                ; localization lookup
0077f70b push 0xddbf80                ; "WIN_NO_TCLS"
0077f710 call 0x77b0e0
0077f71a call 0x77fa70                ; error display
0077f722 jmp 0x77ee87                 ; fatal path
```

Observation during the fatal dialog:

```text
[0x849413B] = 0x00
```

## Runtime Argument Array

The runtime array is populated by `EXE+0x00852724`, which writes:

```asm
00c5270d mov dword ptr [0x196928c], eax   ; count
00c52712 mov dword ptr [0x1969290], esi   ; pointer
```

The source is a UTF-16 string fetched through internal IAT slot
`0x00CA827C`. That slot does not resolve through static PE imports; the
probe observed it as a runtime ABI call that returns the 16-bit command
line string. The writer then parses it into an argv-style array, matching
the launched executable string exactly. The exact API name behind
`0x00CA827C` was not proven; it behaves as a command-line/argv provider.

Live array dump during direct launch:

```text
count = 1
ptr   = 0x12352668
argv[0] = "D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
```

There are no `-q`, `-qa`, or `-src=tgp` arguments, so the flags default to
zero and the fatal branch executes.

## Error Display Path

`EXE+0x37FA70` is the error display function. In the path used by the fatal
dialog it constructs two localized strings and calls through internal
userspace slots:

```asm
0077fae8 call dword ptr [0xca8404]
0077faf2 call dword ptr [0xca8434]

0077fb09 push 0x400
0077fb0e lea eax, [ebp-0xa04]
...
0077fb25 call dword ptr [0xca8134]
...
0077fb4e call dword ptr [0xca8404]
0077fb55 call dword ptr [0xca8458]
```

The resolved `#32770` dialog confirms the standard dialog display. The
exact imported `MessageBoxW` slot was not proven without a debugger hook;
the call chain is internally consistent with the observed dialog.

## Client-Context Interpretation

The error text says to launch from `TCLS文件夹内的Client.exe`, but the
runtime predicate is not a `Client.exe` process check. It checks whether
the current command line contains `-q` or `-qa` before showing
`WIN_NO_TCLS`. `-src=tgp` alone does not satisfy the predicate.

The historical loader/model likely launched CODOL with `-q` or `-qa`.
That mapping is not proven by this experiment and remains outside the
current observation surface.

## Summary

```text
ERROR_STRING_SOURCE_CONFIRMED          EX-030
ERROR_UI_CALL_CONFIRMED                decoded display path -> #32770
COMMANDLINE_CHECK_CONFIRMED            argv array -> -q / -qa -> fatal branch
CLIENT_CONTEXT_CHECK_PARTIAL           no direct Client.exe parent proof
NO_TCLS_MAPPING_OBSERVED               no TCLS mapping producer tied to -q / -qa
NO_PERSISTENT_WRITE_OBSERVED           no filesystem writes from fatal path
FATAL_PREDICATE_RESOLVED               WIN_NO_TCLS when -q and -qa absent
```

## Evidence Files

The supporting runtime logs are preserved under:

```text
工具/logs/
```
