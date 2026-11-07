# CODOL EXE-CORE-001 codoMP_client_shipRetail.exe Full Native Architecture Reconstruction
## Final Classification
EXE_CUSTOM_BOOTSTRAP_CONFIRMED
TVM0_BOUNDARY
OBSERVER_NO_DIVERGENCE
SECOND_NATIVE_BOOT_NONE
## 1. Scope
Single object of study: codoMP_client_shipRetail.exe.
This report focuses on EXE-native architecture, loader/bootstrap, plain-text evidence, and runtime state machine.
It does not treat dependent DLLs as separate research objects except as EXE-observed modules.
## 2. PE / Section Architecture
ImageBase: 0x400000
EntryPoint: 0xE5DC690 / VA 0x0E9DC690
Subsystem: 2 GUI
Security: PE signature at 0x777048, 0x35F8 bytes
PDB: D:\projects\AutoBuilder.rel2\iw4\game\pc\codoMP_client_shipRetail.pdb
Sections:
- .tp3 0x1000 VS 0x8A689A RAW 0x1000 RS 0x593000
- .tp3 0x8A8000 VS 0x16DA70 RAW 0x594000 RS 0x16E000
- .tp3 0xA16000 VS 0xDBB1CC0 RAW 0x702000 RS 0x62000
- .tp3 0xE5C8000 VS 0x31 RAW 0x764000 RS 0x1000
- .tp3 0xE5C9000 VS 0x9228 RAW 0x765000 RS 0xA000
- .tvm0 0xE5D3000 VS 0x4000 RAW 0x76F000 RS 0x2000
- .tp3 0xE5D7000 VS 0x82000 RAW 0x771000 RS 0x6000
Data directories present: EXPORT, IMPORT, SECURITY, DEBUG, TLS
Not present: LOAD_CONFIG, BOUND_IMPORT, DELAY_IMPORT, EXCEPTION, RELOCATION
## 3. Entry / TLS / Export
Entry bytes: ff 15 65 c6 9d 0e -> call [0x0E9DC665]
Custom import thunk -> Base+0x1D6582C -> Base export ordinal 1
Base entry: 0x149C -> jmp Base+0x1AA13B0 VM boundary
TLS StartAddressOfRawData: 0xE9C8000
TLS EndAddressOfRawData: 0xE9C8030
TLS AddressOfCallBacks: 0xCADA3C
Callback array RVA: 0x8ADA3C
Callback count: 0
No TLS callback execution evidence.
## 4. Bootstrap State Machine
BOOT-0 Process Created
BOOT-1 EXE Entry -> Base ordinal_1
BOOT-2 Base/VM boundary
BOOT-3 Thread/CRT activity
BOOT-4 Platform/TCLS/IPC not confirmed
BOOT-5 Engine initialization NOT REACHED
BOOT-6 FS/resource initialization NOT REACHED
BOOT-7 Renderer NOT REACHED
BOOT-8 Game/main loop NOT REACHED
Observed stop points: Base+0x306A valid state, then ecx=3; KERNEL32!IsBadReadPtr+0x5a in crash-report context
## 5. Plain Text / Native Function Map Status
Known plain .text areas:
- EXE entry thunk area
- small helper regions outside .tvm0
Known VM/protected areas:
- .tvm0
- large Base .tvm0/code-blob regions
Current function-map coverage:
- confirmed: EXE entry, Base ordinal_1, Base+0x149C, Base+0x1AA13B0
- partial: Base+0x306A reached from non-tvm0 code
- unresolved: full caller/callee map across VM boundary
Next step: build incremental function catalog from plain sections only; do not synthesize fake symbols from VM blobs.
## 6. Conclusion
The EXE is a custom bootstrap client whose first native action is Base ordinal_1, followed quickly by a VM boundary.
No recovered native second boot path leads to Engine/Game from EXE alone.
Stop here unless new plain-text evidence appears.
