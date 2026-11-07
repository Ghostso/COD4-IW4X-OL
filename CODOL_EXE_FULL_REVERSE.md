# CODOL_EXE_FULL_REVERSE.md

## EXE facts

ImageBase: 0x400000.
EntryPoint: 0xE5DC690 (VA 0x0E9DC690).
Subsystem: 2 (GUI).
Security: PE signature at 0x777048, 0x35F8 bytes.
PDB: `D:\projects\AutoBuilder.rel2\iw4\game\pc\codoMP_client_shipRetail.pdb`.

Sections:
- .tp3 0x1000 / 0x8A689A, raw 0x1000
- .tp3 0x8A8000, raw 0x594000
- .tp3 0xA16000, raw 0x702000
- .tp3 0xE5C8000, raw 0x764000
- .tp3 0xE5C9000, raw 0x765000
- .tvm0 0xE5D3000, raw 0x76F000
- .tp3 0xE5D7000, raw 0x771000

Data directories:
- Export: 0xA155B0 / 0x4C0
- Import: 0xE5DC635 / SIZE=0
- Resource: 0xE5C9000 / 0
- Security: 0x777048 / 0x35F8
- Debug: 0x8ADA60 / 0x1C
- TLS: 0x9E8EB8 / 0x18

Import directory size 0 but pefile reports the first import entry because the RVA points at a thunk. This is a custom/VM binding pattern, not standard import resolution.

## TLS

TLS StartAddressOfRawData: 0xE9C8000.
TLS EndAddressOfRawData: 0xE9C8030.
TLS AddressOfCallBacks: 0xCADA3C.
Callback array at RVA 0x8ADA3C: first dword 0, callback count 0.
No TLS callback execution evidence.

## Entry execution

Entry byte: `ff 15 65 c6 9d 0e`, `call dword ptr [0x0E9DC665]`.
[0x0E9DC665] resolves to `Base+0x1D6582C` (Base export ordinal 1).

Base DLL: entry `0x149C` -> jmp `0x1AA13B0`, which is VM boundary.

## Evidence quality

- L3/L4: EXE Entry executed, Base ordinal_1 entered, VM boundary hit.
- L4: Base ordinal_1 did not return to EXE in observed runs.
- L3: first exception in crash-report thread was `KERNEL32!IsBadReadPtr+0x5a`; other runs reached `Base+0x306A`.
- L2: static custom import resolver, non-standard PE layout, VM thunk entry.
