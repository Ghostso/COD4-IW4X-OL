# CODOL STANDALONE-CORE-004A
## Toolchain Exhaustive Discovery & Minimal Disassembly Verification

## Final Status

```text
TOOLCHAIN_STATUS = LEVEL_3
FILE_READ_STATUS = FILE_READABLE
PE_PARSE_STATUS = PE_MANUAL_PARSE_CONFIRMED
RVA_MAPPING_STATUS = RVA_MAPPING_PARTIAL
TP3_STATUS = TP3_MAPPING_PARTIAL
X86_DECODER_STATUS = X86_DISASSEMBLY_SMOKE_TEST_CONFIRMED
FUNCTION_RECOVERY_STATUS = NOT_PERFORMED
CFG_STATUS = NOT_PERFORMED
WORKING_TOOL = Python 3.11.9 stdlib manual PE parser; pefile 2024.8.26; Capstone 5.0.7; cdb 10.0.29617.1000
PRIMARY_FAILURE_LAYER = AUTOMATIC_FUNCTION_AND_CFG_RECOVERY_NOT_AVAILABLE
NEXT_REQUIRED_TOOL = Ghidra/IDA/Binary Ninja/rizin, or a validated recursive-descent CFG recovery implementation
```

## Sample Identity

```text
Path = COD OL\codoMP_client_shipRetail.exe
SHA256 = 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
Expected SHA256 = 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
ImageBase = 0x00400000
Entry RVA = 0x0E5DC690
Entry VA = 0x0E9DC690
Machine = 0x014C (I386)
PE type = PE32
Sections = 7
```

## Confirmed Capabilities

- The sample is readable and its SHA-256 matches.
- DOS, PE, COFF, PE32 optional header, and all section headers were parsed with Python `struct`.
- `.tp3` section selection works for Entry and all requested addresses.
- File-backed bytes are available for 6/10 requested locations; 4 locations are `VIRTUAL_ONLY` because their RVA exceeds the first executable `.tp3` section's raw-data extent.
- Capstone decodes real x86 instructions from 32-byte and 64-byte windows.
- `detail=False` disassembly works; accessing `insn.operands` in that mode raises `CS_ERR_DETAIL` by design.
- `detail=True` and `disasm_lite` both work in the smoke tests.
- Local `cdb.exe` exists and reports version `10.0.29617.1000`.
- Entry begins with `FF 15 65 C6 9D 0E`, decoded as `call dword ptr [0x0E9DC665]`. The operand is slot VA `0x0E9DC665`, corresponding to slot RVA `0x0E5DC665`; it is recorded only as the established external boundary.

## Tool Discovery

- Python modules working: `capstone`, `pefile`, `keystone`, `unicorn`.
- Python modules missing: `lief`, `iced_x86`, `zydis`, `distorm3`.
- Project tools found: `工具\windbg_x86\cdb.exe`, `COD OL\scripts\disasm.py`, and related analysis scripts.
- `Ghidra`, `IDA`, `Binary Ninja`, `rizin`, `radare2`, `objdump`, LLVM tools, and `dumpbin` were not found in PATH, targeted common installation directories, project files, or pip cache.
- WSL executable exists, but no installed Linux distribution was available for an `objdump` test.

## Capstone Diagnosis

`CS_ERR_DETAIL` observed in prior work was caused by reading operand details while `detail=False`; it does not prove that disassembly failed. This run produced 30 successful smoke-test rows. Expected detail-disabled operand-access failures: 10.

The 64-byte window at RVA `0x004FD9B0` decodes successfully. The file-backed window at RVA `0x004FCEE0` begins with bytes that Capstone cannot decode from offset zero, so it is recorded as `NO_INSTRUCTION_DECODED_FROM_WINDOW_START`, not as evidence that the entire sample is undecodable.

## Capability Boundary

The machine can correctly map file-backed `.tp3` bytes and decode x86 instructions, so `TOOLCHAIN_MISSING` is false. The verified level is `LEVEL_3`: minimal x86 disassembly works. Function boundary recovery and trustworthy CFG recovery were deliberately not claimed or performed in CORE-004A.

## Not Analyzed

- Game Init
- Main Loop
- State Machine
- IIPS, TCLS, Base.dll internals
- `.tvm0` internals
- EXE patching, hooks, or debugger control-flow modification

## Delivered Artifacts

- `exe_core004a_toolchain_matrix.csv`
- `exe_core004a_section_map.csv`
- `exe_core004a_entry_bytes.txt`
- `exe_core004a_address_map.csv`
- `exe_core004a_disassembly_smoke_test.csv`
