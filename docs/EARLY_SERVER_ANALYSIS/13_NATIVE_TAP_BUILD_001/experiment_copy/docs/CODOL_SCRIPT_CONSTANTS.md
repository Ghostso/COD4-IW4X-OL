# File-local script constants

`CODOL_LowerScriptSyntax` now expands file-local scalar literal declarations
before foreach and explicit pointer-call lowering. The retained native compiler
then compiles the literal expressions. Reference scripts are not modified.

Supported initializers are strings, decimal numbers (including signed and
exponent forms), and booleans. Declaration text is blanked while retaining CR/LF;
identifier references are case-insensitive like other script identifiers.
Comments, strings, qualified member names and script paths are left intact.
Signed numeric values are parenthesized so adjacent operators cannot become
increment/decrement tokens. Expansion precedes foreach rewriting, including
references in its collection expression. Output remains bounded.

This does not implement mutable globals, cross-file constant exports, arbitrary
constant expressions, or local shadowing of constant names. Nonliteral
initializers, duplicate declarations and detected writes fail; unsupported uses
remain compiler errors. It does not claim complete IW4/T5 grammar support.

The focused tests cover string/numeric substitutions, logical comparisons,
member/comment/string isolation, line counts, foreach integration, duplicate
declarations and writes. The initial runtime probe exposed the numeric constant
`maxSightTracedSpawnpoints = 3` in `_spawnlogic.gsc` and a mistaken rejection of
logical `&&` after a constant; both were corrected and covered by tests.
The Windows build passed (`/tmp/sh1x-script-constants-win32-final.log`).

On 2026-09-08 the isolated UDP 17758 probe at
`%TEMP%/sh1x-constants-final-vm-20260908-074952` logged
`SH1X_CLASS_PERK_VM_PASS` after a real native player script compared a profile
perk to its file-local `EXPECTED_PERK` string constant. The encrypted stats,
gamestate, checksum, movement and baseline/delta snapshot checks passed.

The full vendor/overlay probe on UDP 17757 at
`%TEMP%/sh1x-constants-final-reference-20260908-074954` advanced past the
constant declarations and stopped at missing `setClientMatchData` in
`maps/mp/_highlights.gsc:9`. Both isolated processes were stopped after
inspection. The existing C1/Python lobby were preserved. Full scripts and real
match entry remain incomplete.
