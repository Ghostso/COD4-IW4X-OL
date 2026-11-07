# EX-034 argv Gate Call Semantics and Parameter Object Source

## Final Classification

```text
ARGV_PROVIDER_PARTIAL
ARGV_DATA_SHAPE_CONFIRMED
COMMANDLINE_SOURCE_CONFIRMED
Q_QA_HANDLER_CONFIRMED
Q_QA_SEMANTICS_UNRESOLVED
SRC_TGP_HANDLER_PARTIAL
SRC_TGP_SEMANTICS_UNRESOLVED
PREDICATE_ARGV_ONLY_CONFIRMED
WIN_NO_TCLS_HISTORICAL_KEY_PARTIAL
NO_TCLS_MAPPING_REQUIRED_BY_PREDICATE
NO_PERSISTENT_WRITE_OBSERVED
```

EX-034 reconstructs the CODOL-internal argv subsystem feeding
`EXE+0x37F580`. The runtime argv representation is confirmed as a
`char **` style array: a count plus a pointer array of 4-byte pointers to
ANSI strings. The exact API name behind `0xCA827C` is still not proven,
so the provider remains partial, not fully connected to `GetCommandLineW`
or `CommandLineToArgvW`.

## Confirmed Flow

```text
process command line
  ->
0xCA827C
  ->
UTF-16 command-line string
  ->
EXE+0x852724 argv-array builder
  ->
[0x0196928C] count
[0x01969290] argv pointer array
  ->
EXE+0x37F580 predicate
  ->
WIN_NO_TCLS if no -q / -qa
```

## argv Data Shape

The writer at `EXE+0x852724`:

```asm
00C5272E call dword ptr [0xca827c]   ; receive UTF-16 command line
00C52740 cmp word ptr [ebx], si       ; test first wide char
00C52745 add eax, 2                   ; scan by 2-byte units
00C52748 cmp word ptr [eax], si
00C52755 push edi                     ; allocator call
00C5275C push esi
00C5275F sub eax, ebx
00C52762 sar eax, 1                   ; length / 2
00C52765 push eax
00C52766 push ebx
00C52769 mov [ebp-0xc], eax           ; wide length
00C5276C call [0xca8130]
```

This is a UTF-16 string scan. The parser stores a pointer array and a
count:

```asm
00C5270D mov [0x196928c], eax   ; count
00C52712 mov [0x1969290], esi   ; pointer
```

Runtime dump:

```text
ptr = 0x12352668
count = 1
argv[0] = "D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
```

Element stride observed by ex031 writer and predicate dumps:

```text
byte size = 4
element = pointer to ANSI string
```

So the shape is:

```text
char **argv
```

with the count stored separately.

## Predicate Control Flow

The predicate at `EXE+0x37F580` consists of one loop with three exact
string comparisons:

```asm
-q      -> [0x849413B] = 1
-qa     -> [esp+0xF] = 1 and [0x849B500] = 1
-src    -> [0x849B501] = 1
```

After the loop:

```asm
0077F6E8 cmp byte ptr [0x849413B], 0
0077F6EF jne continue
0077F6F1 cmp byte ptr [esp+0xF], 0
0077F6F6 jne continue
0077F6F8 push WIN_ERROR
0077F6FD call localization
0077F70B push WIN_NO_TCLS
0077F710 call localization
0077F71A call error display
0077F722 jmp fatal
```

This confirms:

```text
if (has -q || has -qa)
    continue
else
    WIN_NO_TCLS
```

No optional extra control-flow branch was observed in the runtime dump.
`-src=tgp` does not suppress the error.

## Comparison Type

The comparisons are byte-wise, case-sensitive, exact string matches on
ANSI/ASCII bytes:

```asm
movsx edx, byte ptr [edi+ecx]
movsx esi, byte ptr [ecx]
```

Encoding:

```text
ASCII/ANSI
```

Case:

```text
case-sensitive
```

This rules out `_stricmp`, wildcard, prefix, UTF-16 comparison, and
hash-table behavior at this gate.

## `0xCA827C`

Status: packed/decoded internal IAT slot.

Observed behavior:

```text
returns a UTF-16 string pointer
```

The slot is not resolved by the ordinary PE import directory. The tvm0
linear decoder output shows:

```text
GetCommandLineA call count = 1
GetCommandLineW / CommandLineToArgvW
```

but does not map either to `0xCA827C` directly. Therefore:

```text
GetCommandLineW / CommandLineToArgvW -> 0xCA827C  NOT PROVEN
```

## `EXE+0x852724` Responsibilities

Responsibilities confirmed:

```text
1. fetch UTF-16 command-line string via 0xCA827C
2. parse it into argv tokens
3. allocate argv storage
4. write count to 0x196928C
5. write argv pointer to 0x1969290
6. return success/failure
```

It is not itself the low-level OS command-line parser name; it is the
CODOL-side argv builder.

## `-q` and `-qa` Handler Status

Handlers:

```text
-q : confirmed predicate-only handler at EXE+0x37F580
-qa: confirmed predicate-only handler at EXE+0x37F580
```

Additional state effects:

```text
-q  -> [0x849413B] = 1
-qa -> [esp+0xF] = 1 and [0x849B500] = 1
```

Product semantics:

```text
Q_QA_SEMANTICS_UNRESOLVED
```

No help/usage text or option table mapping `-q` / `-qa` to named game
modes was recovered.

## `-src=tgp` Handler Status

`-src=tgp` is parsed by the same loop and sets:

```text
[0x849B501] = 1
```

It does not suppress `WIN_NO_TCLS`. Its semantic role is unresolved.

## Historical Error Key

`WIN_NO_TCLS` is documented as an old error label. The extracted Base.dll
context cluster contains adjacent tokens:

```text
-api
-q
-q:
id=
key=
ID=
```

This is consistent with an old command-line/credentials flow, but no
proof exists that `WIN_NO_TCLS` is purely historical or that it directly
means TCLS shared memory is missing at this predicate.

## Answers to Final Questions

1. Real data structure at `0xCA827C`: resolves through an internal IAT slot to a UTF-16 command-line string.
2. Who initialises it: not proven.
3. Who reads it: EXE writer at +0x852724 via `call [0xCA827C]`.
4. `EXE+0x852724` responsibility: CODOL argv builder; parses UTF-16 command line into char-pointer array.
5. Connected to `GetCommandLineW`: not proven by static xref, but consistent with runtime shape.
6. Uses `CommandLineToArgvW`: not proven.
7. Uses CRT argv: not proven.
8. Custom parser: likely, based on inline tokenization in `0xC52724`, but not fully attributed.
9. Independent handlers for `-q` / `-qa`: yes at predicate level.
10. Final state: `-q` sets `[0x849413B]`; `-qa` sets local `[esp+0xF]` plus `[0x849B500]`.
11. `-src=tgp` same parser: yes, in the same loop.
12. `-src=tgp` semantics: unresolved.
13. `WIN_NO_TCLS` old key: partially consistent, not proven.
14. Predicate really only argv condition: confirmed from runtime disassembly.
15. New L2/L3 node: L2 confirmed (`argv builder -> argv structure`), L3 partial (`0xCA827C` is command-line-style provider, API name unresolved).

## Summary

Main advance this round:

```text
ARGV_DATA_SHAPE_CONFIRMED
Q_QA_HANDLER_CONFIRMED
PREDICATE_ARGV_ONLY_CONFIRMED
```

The unresolved bottleneck remains the exact API name behind `0xCA827C`.
The next strongest target is runtime observation of the resolved slot
address without a bootstrap debugger, or static recovery of the packed
IAT entry that fills it.
