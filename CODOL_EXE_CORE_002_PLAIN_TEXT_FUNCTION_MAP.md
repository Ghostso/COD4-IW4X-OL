# CODOL EXE-CORE-002 Plain .text Function Map
## Final Classification
EXE_PLAIN_TEXT_MAP_PARTIAL
TVM0_BOUNDARY
OBSERVER_NO_DIVERGENCE
## 1. PE / Section Map
See exe_section_map.csv.
Key facts:
- Entry RVA 0xE5DC690 in .tp3
- .tvm0 present at 0xE5D3000, not analyzed internally
- No recovered plain-text .text section with standard name
## 2. Native Function Discovery
Current coverage is partial.
Confirmed EXE plain .text nodes:
- Entry thunk at 0xE5DC690
- Custom import thunk area at 0xE5DC665
- bootstrap candidates: 0x77F580, 0x77F8B3, 0x4FD9B0, 0x4FCEE0, 0x808650, 0x7E98F0, 0x6212C0
Status: CANDIDATE until direct/indirect caller chain from EXE entry is confirmed.
## 3. Call Graph
See exe_callgraph.csv.
Known edge:
- 0xE5DC690 -> memory-indirect thunk at 0xE9DC665
Confidence: CANDIDATE because this is a custom VM/bootstrap thunk, not a normal function call.
## 4. Bootstrap Expansion
Upward:
- Who calls 0x77F580: UNKNOWN in plain-text scan so far
- Entry post-action: immediate indirect call, no confirmed CRT-style prologue before first thunk
Downward:
- 0x6212C0 return consumer: UNKNOWN
- No confirmed main-loop frame found yet
## 5. Global State Map
See exe_globals.csv.
Current state: UNKNOWN_SUBSYSTEM for most globals because plain-text reader/writer attribution is incomplete.
## 6. Strings -> Native Function
See exe_strings_refs.csv.
Current state: STRINGS_INVENTORY_PARTIAL.
No confirmed subsystem function assignment beyond candidates.
## 7. Subsystem Boundaries
Bootstrap: CANDIDATE
Command Line: CANDIDATE
Memory/Thread/Module Loader: CANDIDATE
FileSystem/Config/Localization/Window/Input/Audio/Network/Renderer/Game/Main Loop/Shutdown: UNKNOWN_SUBSYSTEM
## 8. Main Loop Candidates
MAIN_LOOP_CANDIDATE.
No confirmed while/render/present loop recovered from plain-text evidence in this pass.
## 9. External Boundary
See exe_external_boundary.csv.
Confirmed boundary so far:
- EXE -> Base ordinal_1 via custom thunk
## 10. Summary Diagram
codoMP_client_shipRetail.exe
PE
|-- Entry: CANDIDATE
|-- CRT/TLS: CANDIDATE
|-- Native Bootstrap: CANDIDATE
|-- Command Line: CANDIDATE
|-- Memory: UNKNOWN_SUBSYSTEM
|-- Threading: UNKNOWN_SUBSYSTEM
|-- Module Loader: UNKNOWN_SUBSYSTEM
|-- FileSystem: UNKNOWN_SUBSYSTEM
|-- Config: UNKNOWN_SUBSYSTEM
|-- Localization: UNKNOWN_SUBSYSTEM
|-- Window/Input: UNKNOWN_SUBSYSTEM
|-- Audio: UNKNOWN_SUBSYSTEM
|-- Network: UNKNOWN_SUBSYSTEM
|-- Renderer: UNKNOWN_SUBSYSTEM
|-- Game Initialization: UNKNOWN_SUBSYSTEM
|-- Main Loop: MAIN_LOOP_CANDIDATE
|-- Shutdown: UNKNOWN_SUBSYSTEM
|-- External DLL Boundary: CONFIRMED
Unknown key region: plain-text bootstrap dispatcher and return path from Base boundary are not yet confirmed.
