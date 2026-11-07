# CODOL STANDALONE-CORE-004
## EXE Static Analysis Toolchain Recovery

## Final status

```text
TOOLCHAIN_STATUS = LEVEL_3
WORKING_TOOL = Python stdlib/manual PE parser; pefile 2024.8.26; Capstone 5.0.7; cdb 10.0.29617.1000
FAILED_TOOL = Ghidra / IDA / Binary Ninja / rizin / radare2 / objdump / LLVM tools / dumpbin not found
PRIMARY_FAILURE_LAYER = FUNCTION_AND_CFG_AUTOMATION_NOT_AVAILABLE
SAMPLE_STATUS = SAMPLE_MATCH_CONFIRMED
PE_MAPPING_STATUS = PE_MAPPING_CONFIRMED
DISASSEMBLY_STATUS = X86_DISASSEMBLY_CONFIRMED
FUNCTION_RECOVERY_STATUS = NOT_PERFORMED
CFG_STATUS = NOT_PERFORMED
NEXT_STEP = CORE-005-style bounded CFG recovery; do not infer Game Init/Main Loop yet
```

## Sample identity

```text
Sample = COD OL\codoMP_client_shipRetail.exe
SHA-256 = 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
PE32 = YES
I386 = YES
ImageBase = 0x00400000
Entry RVA = 0x0E5DC690
Entry VA = 0x0E9DC690
Sections = 7
```

## Results

- Manual DOS/PE/COFF/PE32 parsing succeeded.
- `.tp3` section headers and RVA-to-file-offset mapping were read from the section table; `RVA == file offset` was not assumed.
- Entry begins with `FF 15 65 C6 9D 0E`, decoded as `call dword ptr [0x0E9DC665]`. The slot is recorded as `EXTERNAL_BOUNDARY`; Base.dll was not entered.
- Smoke test rows: `30`; windows with at least one decoded instruction: `15`; `VIRTUAL_ONLY` windows: `12`.
- Indirect-site rows: `3`. These come from a raw-linear identification pass and are not a CFG or function proof.
- `detail=False is usable; operand access requires detail=True`. A previous `CS_ERR_DETAIL` is a Capstone configuration/access-mode issue, not proof that the sample is undecodable.

## Function boundary status

No automatic function-boundary engine is available in this environment. Prologue-like bytes, strings, direct targets, and linear decode output are not promoted to confirmed functions. A CFG-derived boundary method is required for the next stage.

## `.tvm0` and external boundaries

`.tvm0` was excluded from the executable scan. No VM decoding, dispatcher recovery, Base.dll analysis, or other DLL analysis was performed.

## Negative findings

- This run does not prove a complete function database.
- This run does not prove a complete CFG.
- It does not classify Game Init, Main Loop, Renderer, Filesystem, or State Machine behavior.
- `VIRTUAL_ONLY` addresses are not reconstructed as file code.
- Indirect targets other than the Entry boundary remain `UNKNOWN`.

## Delivered artifacts

- `exe_core004_toolchain_matrix.csv`
- `exe_core004_section_map.csv`
- `exe_core004_entry_bytes.txt`
- `exe_core004_disassembly_smoke_test.csv`
- `exe_core004_indirect_call_sites.csv`

The CORE-004 capability ceiling is `LEVEL_3`: sample read, PE mapping, and x86 disassembly are confirmed. Function recovery and CFG recovery remain future work.
