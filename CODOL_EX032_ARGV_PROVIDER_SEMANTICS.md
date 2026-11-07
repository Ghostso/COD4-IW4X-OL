# EX-032 argv Provider and `-q/-qa` Semantics

## Final Classification

```text
ARGV_PROVIDER_PARTIAL
COMMANDLINE_SOURCE_CONFIRMED
Q_QA_SEMANTICS_UNRESOLVED
SRC_TGP_SEMANTICS_UNRESOLVED
PREDICATE_ARGV_ONLY_CONFIRMED
CLIENT_CONTEXT_CHECK_PARTIAL
```

The runtime array behind `EXE+0x37F580` is confirmed to be an argv-style
array sourced from the Windows command line. The provider slot
`0xCA827C` is a packed/decoded command-line provider; no direct import
name was mapped to that slot. The exact API name behind `0xCA827C` is
therefore not statically proven, but the data it produces matches the
process command line and the parser behavior seen at `EXE+0x852724`.

`-q` and `-qa` are treated by the predicate as two distinct argv matches.
Their semantic meaning outside this predicate remains unresolved, as does
the semantic role of `-src=tgp`.

## Evidence

### EX-031 live argv array

During normal direct launch, live memory contained:

```text
count = 1
ptr   = 0x12352668
argv[0] = "D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
```

This exactly matches the command line supplied by `CreateProcessW` in the
probe.

### EXE static command line imports

The EXE contains runtime-visible imports for command-line processing:

```text
KERNEL32.dll
  GetCommandLineW           IAT 0x004c6088
  GetCommandLineA           IAT 0x004c608c

SHELL32.dll
  CommandLineToArgvW        IAT 0x004c6440
```

CRT startup exports are also present:

```text
__p___argc
__p___argv
_configure_narrow_argv
_initialize_narrow_environment
```

These are consistent with a CRT/Windows command-line based argv system.

### Launcher behavior

The WeGame/TGP companion launcher binaries use the same command-line
family. Observed static evidence includes:

```text
GetCommandLineW -> parser -> CreateProcessW
CommandLineToArgvW
"wegame://action=StartFor&game_id="
"cmd_launcher_info.ini"
```

This supports the idea that TGP/WeGame passes a command line to the game,
but it does not prove whether `-q` / `-qa` are added by `Client.exe`.

### Provider chain

The recovered chain remains:

```text
EXE+0x852724
  -> internal slot 0xCA827C
  -> argv-style array (UTF-16 parsed into ANSI strings)
  -> EXE+0x37F580
```

The writer at `EXE+0x852724` receives a 16-bit string through
`0xCA827C`, parses it into `argv` elements, and stores:

```text
[0x196928C] = count
[0x1969290] = pointer to string pointer array
```

### Predicate checks, not a process/parent check

At `EXE+0x37F580`, the code loops over the runtime argv array and performs
byte-wise string comparisons:

```asm
-q       -> sets [0x849413B]=1
-qa      -> sets [esp+0xF]=1 and [0x849B500]=1
-src=tgp -> sets [0x849B501]=1
```

The fatal `WIN_NO_TCLS` branch is taken when:

```text
[0x849413B] == 0
[esp+0xF]  == 0
```

No additional process-tree, window, IPC, or persistent file condition was
observed in the predicate body. Therefore the predicate is argv-only as
observed.

## Semantic Status

### `-q`

```text
PREDICATE_EFFECT_CONFIRMED
SEMANTICS_UNRESOLVED
```

`-q` suppresses `WIN_NO_TCLS` at runtime. No handler/option table was
recovered that maps `-q` to a named game behavior.

### `-qa`

```text
PREDICATE_EFFECT_CONFIRMED
SEMANTICS_UNRESOLVED
```

`-qa` suppresses `WIN_NO_TCLS` and sets an additional flag at
`0x849B500`. The meaning of that extra flag is unresolved.

### `-q` vs `-qa`

The code compares against two separate literal strings:

```asm
compare argv[i] with "-q"
compare argv[i] with "-qa"
```

This is not a prefix match. A token equal to `-qa` sets the `-qa` branch,
not the `-q` branch.

### `-src=tgp`

```text
SELF_SUFFICIENT_PREDICATE_EFFECT_UNRESOLVED
```

`-src=tgp` sets a separate global at `0x849B501`. It does not set the
flags that suppress `WIN_NO_TCLS`. No handler or semantic meaning was
recovered.

## Module Access to `0xCA827C`

Existing cross-reference scans did not find static imports or module
access into `0xCA827C` because the location is a packed/decoded internal
slot. The runtime dump confirms reads by EXE code around the writer
function; no project DLL access was proven in the available logs.

## Summary

```text
COMMANDLINE_SOURCE_CONFIRMED
ARGV_PROVIDER_PARTIAL
Q_QA_SEMANTICS_UNRESOLVED
SRC_TGP_SEMANTICS_UNRESOLVED
PREDICATE_ARGV_ONLY_CONFIRMED
CLIENT_CONTEXT_CHECK_PARTIAL
NO_NEW_NODE=NO
```

The next useful step would be a separate experiment to map historical
TCLS/WeGame launch command construction, but that was outside the bounds
of this observation-only pass.
