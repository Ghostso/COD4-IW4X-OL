# CODOL_EX065_TCLS_UPSTREAM_BOUNDARY

## Scope and Constraints Observed

Offline static analysis only.

Not performed:

```text
hook
API detour
IAT patch
inline patch
debugger attach
Frida
target memory modification
IAT/export/vtable modification
fake return
bypass
parameter tampering
CODOL / TCLS / IIPS binary modification
fake IIPS success state
```

No process was started, attached to, or instrumented.

Allowed and used:

```text
PE parsing, disassembly, CFG, xref, dataflow,
import/export analysis, string analysis, read-only file analysis
```

### Evidence vocabulary

```text
STATIC_CONFIRMED       literal instruction/byte evidence
STATIC_REACHABLE       a static CFG path exists
STATIC_DATAFLOW_CONFIRMED  a register/memory dataflow chain is literal
STATIC_BOUNDARY        a boundary is proven but only by its absence
PACKED_UNRESOLVED      packed region prevents resolution
UNKNOWN                insufficient evidence
HISTORICAL_DYNAMIC     a pre-existing runtime log from the target tree
                       (used ONLY at module/API-name level)
```

`DYNAMIC_CONFIRMED`, `RUNTIME_CONFIRMED`, `SUCCESS` are NOT used.

---

## EXECUTIVE ANSWER

```text
TCLS_ENTRY                  = tcls_core.exe  PE entry 0xB2A18
TCLS_ENTRY_TO_SUB8D2A2      = STATIC_REACHABLE (through the TCLSHostApp
                              message/protocol layer, not a single CALL chain)
CREATEIIPSREPAIR_RESOLUTION = STATIC_CONFIRMED
CREATEIIPSREPAIR_CALL       = STATIC_CONFIRMED

IIPSLAUNCHRESTORE_ENTRY     = STATIC_CONFIRMED (exports CreateIIPSRepair /
                              RealeaseIIPSRepair)
TCLS_TO_IIPS                = STATIC_CONFIRMED

TCLS_IPC                    = STATIC_CONFIRMED
                              named shared memory + named mutex +
                              named window + window messages
GAMEPID_FLOW                = STATIC_CONFIRMED (game PID embedded in the
                              shared-memory name)
TCLS_SHARED_MEMORY_FLOW     = STATIC_CONFIRMED
CODOL_PROCESS_DISCOVERY     = STATIC_CONFIRMED (the shared-memory name
                              is keyed by the game PID)

TCLS_PROCESS_CREATION       = STATIC_BOUNDARY
TCLS_UPSTREAM_CALLER        = STATIC_BOUNDARY

NATIVE_BOOTSTRAP_TO_TCLS    = STATIC_BOUNDARY
TCLS_TO_NATIVE_BOOTSTRAP    = STATIC_BOUNDARY

STATIC_BOOTSTRAP_LINK       = HOST_PROCESS_BOUNDARY
STATIC_BOOTSTRAP_LINK_TYPE  = TCLS_HOST_UNRESOLVED
                              + NAMED_OBJECT_PROTOCOL

RUNTIME_GETRESOURCE_CALL    = UNKNOWN
RUNTIME_INITINGAMEAPP       = UNKNOWN
RUNTIME_IFS2_LOAD           = UNKNOWN
RUNTIME_CREATEIFS           = UNKNOWN
RUNTIME_FIRST_FAILURE       = UNKNOWN
```

The key discovery of this round:

**The CODOL native bootstrap and TCLS are not joined by a CALL. They are
joined by a NAMED-OBJECT PROTOCOL whose name embeds the game process ID.**

---

## PHASE 1 - `tcls_core.exe` process entry

### 1.1 PE header facts

```text
module           WeGame\tcls\tcls_core.exe
size             1971248
image base       0x400000
image size       0x1E6000
subsystem        2  (GUI)
DllCharacteristics 0x8100
entry point RVA  0xB2A18  (VA 0x4B2A18)
sections
   .text   VA 0x001000  vsize 0x154906
   .rdata  VA 0x156000  vsize 0x04FB10
   .data   VA 0x1A6000  vsize 0x014970
   .rsrc   VA 0x1BB000  vsize 0x02AAA0
directories
   IMPORT   0x1A3FEC     TLS       0x182420
   RESOURCE 0x1BB000     LOADCFG   0x182378
   IAT      0x156000     SECURITY  0x1DEA00
```

```text
EVIDENCE  STATIC_CONFIRMED
```

### 1.2 TLS callbacks

```text
TLS directory RVA 0x182420
   StartAddressOfRawData   0x58AA24
   EndAddressOfRawData     0x58AA2C
   AddressOfIndex          0x5B7B30
   AddressOfCallBacks      0x55659C

callback table at RVA 0x15659C:
   0x15659C : 00 00 00 00 00 00 00 00 2d 49 4b 00 ...
              ^^^^^^^^^^^
              first entry = NULL  ->  THE TABLE IS EMPTY
```

```text
=> tcls_core.exe registers ZERO TLS callbacks.
EVIDENCE  STATIC_CONFIRMED
```

### 1.3 Entry stub

```text
0xB2A18  e8 f0 06 00 00   call 0x4B310D
0xB2A1D  e9 25 fe ff ff   jmp  0x4B2847

0x4B310D  (__security_init_cookie)
   0xB310D  mov ecx, [0x5A60A4]
   0xB3113  push esi
   0xB3114  push edi
   0xB3115  mov edi, 0xBB40E64E
   0xB311A  mov esi, 0xFFFF0000
   0xB311F  cmp ecx, edi
   0xB3121  je 0x4B3127
   0xB3123  test esi, ecx
   0xB3125  jne 0x4B314D
   0xB3127  call 0x4B30C0              ; GetSystemTimeAsFileTime pair
   0xB3147  mov [0x5A60A4], ecx
   0xB314D  not ecx
   0xB3150  mov [0x5A60A0], ecx
   0xB3157  ret

0x4B2847  (__scrt_common_main_seh)
   0xB2847  push 0x14
   0xB2849  push 0x5A0A78
   0xB284E  call 0x4B2CD0              ; __security_init_cookie guard
   0xB2853  push 1
   0xB2855  call 0x4B218E              ; __scrt_initialize_crt
   0xB285B  test al, al
   0xB285D  je 0x4B29AD
   0xB2863  xor bl, bl
   0xB2865  mov [ebp-0x19], bl
   0xB2868  and dword [ebp-4], 0
   0xB286C  call 0x4B2093              ; __scrt_acquire_startup_lock
   0xB2871  mov [ebp-0x24], al
   0xB2874  mov eax, [0x5B7AE4]        ; __scrt_current_native_startup_state
   0xB2879  xor ecx, ecx
   0xB287B  inc ecx
   0xB287C  cmp eax, ecx
   0xB287E  je 0x4B29AD
   0xB2884  test eax, eax
   0xB2886  jne 0x4B28D1
   0xB2888  mov [0x5B7AE4], ecx
   0xB288E  push 0x556594
   0xB2893  push 0x556570
   0xB2898  call 0x5060D7              ; __scrt_initialize_onexit_tables
   0xB289F  test eax, eax
   0xB28A1  je 0x4B28B4
   0xB28AA  mov eax, 0xFF
   0xB28AF  jmp 0x4B299D
   0xB28B4  push 0x55656C
   0xB28B9  push 0x5564AC
   0xB28BE  call 0x50607B              ; _initterm
   0xB28C5  mov dword [0x5B7AE4], 2
   0xB28D1  mov bl, cl
   0xB28D6  push [ebp-0x24]
   0xB28D9  call 0x4B2300              ; __scrt_release_startup_lock
   0xB28DF  call 0x4B31D7              ; __scrt_get_dyn_tls_init_callback
   0xB28E4  mov esi, eax
   0xB28E8  cmp dword [esi], edi
   0xB28EA  je 0x4B2907
   0xB28ED  call 0x4B226C
   0xB28F2  test al, al
   0xB28F5  je 0x4B2907
   0xB28F7  mov esi, [esi]
   0xB28FD  mov ecx, esi
   0xB28FF  call dword [0x5564A8]
   0xB2905  call esi                    ; _initterm_e / dyn tls init
   0xB2907  call 0x4B31DD
   0xB290C  mov esi, eax
   0xB2910  cmp dword [esi], edi
   0xB2912  je 0x4B2925
   0xB2913  call 0x4B226C
   0xB2919  test al, al
   0xB291B  je 0x4B2925
   0xB291D  push dword [esi]
   0xB291F  call 0x504610              ; __scrt_common_main_seh loop
   0xB2925  call 0x4B2FEC              ; __scrt_get_show_window_mode
   0xB292A  movzx eax, ax
   0xB292D  push eax
   0xB292E  call 0x506035
   0xB2933  push eax
   0xB2934  push edi
   0xB2935  push 0x400000
   0xB293A  call 0x44E5BD              ; *** invoke the application entry ***
   0xB293F  mov esi, eax
   0xB2941  call 0x4B3025              ; __scrt_is_managed_app
   0xB2946  test al, al
   0xB2948  je 0x4B29B4
   0xB294A  test bl, bl
   0xB294C  jne 0x4B2953
   0xB294E  call 0x5045E5              ; _cexit
   0xB2953  push edi
   0xB2954  push 1
   0xB2956  call 0x4B231D
   0xB2964  mov eax, esi
   0xB2966  jmp 0x4B299D
```

```text
=> tcls_core.exe uses the modern MSVC CRT
   (__scrt_common_main_seh), not the legacy WinMain thunk.

The application entry is invoked indirectly at 0xB293A through the CRT's
entry table (push 0x400000 = the default hInstance argument, then the
entry pointer).
EVIDENCE  STATIC_CONFIRMED
```

### 1.4 Path from the entry to `sub_8D2A2`

```text
0xB2A18  entry
   -> 0xB310D  __security_init_cookie
   -> 0xB2847  __scrt_common_main_seh
   -> 0xB293A  invoke application entry      STATIC_CONFIRMED

the application message/protocol layer is:

0x5EA87  sub_5EA87   (a TCLSHostApp protocol method; 9+ direct callers)
0x5F4A3  sub_5F4A3   (a second protocol method; 8+ direct callers)
   |
   +-- 0x5EB8B / 0x5EE3D / 0x5F30A  call sub_89EEE (register the
   |                                  handler table)
   +-- 0x5F5E5                     call sub_8A082 (unregister)

0x89EEE  handler-table ctor
   0x89F4C  mov [eax],   0x56A4DC
   0x89F55  mov [eax+4], 0x56A524
   0x89F5F  mov [eax+8], 0x56A538

.rdata table 0x16A4DC .. (command handlers)
   0x16A4DC -> sub_901E5
   0x16A4E0 -> sub_9062B
   0x16A4E4 -> sub_8DBEB          <=== command 0x63 handler
   0x16A4E8 -> sub_8E9BB
   0x16A4F4 -> sub_8DE6E
   0x16A504 -> sub_8D9EF          <=== state 0x18/0x11 handler
   0x16A510 -> sub_8DB11
   0x16A518 -> sub_8EA06
   0x16A51C -> sub_8EA46
   ...

0x8DBEB  handler  (gated on [this+0x30]==0x63 && [this+0x34]==0)
   0x8DCA8  compares [this+0x30] against 0x18 / 0x11
   0x8DE3C  call 0x48D2A2        <=== the CreateIIPSRepair caller (2)

0x8D9EF  handler  (gated on [this+0x18], [this+0x24])
   0x8DA49  call 0x48D2A2        <=== the CreateIIPSRepair caller (1)

0x8D2A2  LoadLibraryW(IIPSLaunchRestore.dll)
         GetProcAddress("CreateIIPSRepair")
         call eax
```

```text
STATIC_REACHABLE  : entry -> protocol layer -> handler table -> sub_8DBEB
                    / sub_8D9EF -> sub_8D2A2

there is NO single CALL chain from 0xB2A18 to 0x8D2A2; the path crosses
the TCLSHostApp message/command layer, whose callers were not exhaustively
enumerated this round.
EVIDENCE          : STATIC_CONFIRMED (0x8D2A2 has exactly 2 direct callers)
                    + STATIC_REACHABLE (the upstream layer)
```

---

## PHASE 2 - `CreateIIPSRepair` contract

### A. GetProcAddress

```text
0x8D2A2  function entry
0x8D2E1  call sub_8C8CF                    ; build the DLL path (runtime)
0x8D348  call sub_A631                     ; -> wide string pointer
0x8D34D  mov [ebp-0x44], eax
0x8D350  push [ebp-0x44]
0x8D353  call dword ptr [0x556058]         ; KERNEL32!LoadLibraryW
0x8D359  mov ecx, [ebp-0x2C]
0x8D35C  mov [ecx+0x5268], eax             ; store hMod
0x8D365  cmp dword [eax+0x5268], 0
0x8D36C  je 0x48D430                       ; failure exit
0x8D375  mov eax, [eax+0x5268]
0x8D37B  mov [ebp-0x48], eax               ; hMod
0x8D382  push 0x56A4B0                     ; "CreateIIPSRepair"
0x8D387  push [ebp-0x48]
0x8D38A  call dword ptr [0x556044]         ; KERNEL32!GetProcAddress
0x8D390  mov [ebp-0x30], eax               ; fn ptr storage
0x8D397  jne 0x48D39F
0x8D399  and dword [ebp-0x38], 0
0x8D39F  call dword ptr [ebp-0x30]         ; *** the call ***
0x8D3A2  mov [ebp-0x38], eax
0x8D3A5  mov eax, [ebp-0x2C]
0x8D3AB  mov [eax+0x526C], ecx             ; store the result object
```

| item | value |
|---|---|
| HMODULE | from `LoadLibraryW` at `0x8D353` (IAT `0x556058`) |
| name | `"CreateIIPSRepair"` at VA `0x56A4B0` |
| resolver | `GetProcAddress` IAT `0x556044` at `0x8D38A` |
| fn-ptr storage | `[ebp-0x30]` (stack), then invoked at `0x8D39F` |
| stack arguments | the callee takes none that are pushed here |
| `ECX`/`EDX` | `ECX = this` (the CallBackThread-like object); EDX unused |
| return value | `EAX` -> `[ebp-0x38]` -> `[this+0x526C]` |
| post-call state | `[this+0x5268]` = HMODULE, `[this+0x526C]` = result |

```text
EVIDENCE  STATIC_CONFIRMED
```

### B. `IIPSLaunchRestore.dll` export

```text
exports
   CreateIIPSRepair     RVA 0x11590
   RealeaseIIPSRepair   RVA 0x11600   (sic, original spelling)

image base 0x10000000  size 0x9B000
imports   KERNEL32, USER32, SHELL32, ole32, OLEAUT32, SHLWAPI, WS2_32
```

Release path in `tcls_core.exe`:

```text
0x8D51F  push 0x56A4C4        ; "RealeaseIIPSRepair"
0x8D524  push [ebp-0x20]
0x8D527  call dword ptr [0x556044]   ; GetProcAddress
0x8D53F  call dword ptr [ebp-0x18]   ; RealeaseIIPSRepair(obj)
0x8D545  and dword [eax+0x526C], 0
0x8D54F  push dword [eax+0x5268]
0x8D555  call dword ptr [0x556040]   ; KERNEL32!FreeLibrary
```

### C. `CreateIIPSRepair` internal (IIPSLaunchRestore.dll)

The exported function reaches the restore object whose method chain was
recovered in EX-064:

```text
CreateIIPSRepair (0x11590)
   -> the CallBackThread / IIPSRestoreManager object
        sub_3AF0  CallBackThread::StartLauchRestore
          0x3C48  call KERNEL32!LoadLibraryW        ; iips.dll
          0x3C89  push "GetResourceManagerII"
          0x3C8F  call KERNEL32!GetProcAddress
          0x3C99  call eax                          ; manager*
          0x3CA1  mov [esi+0xA8], eax
          0x3CB2  mov edx, [edx+0x68]               ; manager slot 26
          0x3CDC  mov edx, [eax+4]                  ; manager slot 1
          0x3CE4  call edx                          ; -> sub_197F0
```

Also present:

```text
thread creation   KERNEL32!CreateThread at 0x1146B8, 0x114791 (in
                  IIPSLaunchRestore.dll)
worker / timer    SetTimer at 0x5C83, WaitForSingleObject at 0x5C96
rollback helper   sub_19820 (invoked from sub_197F0 on failure)
```

```text
EVIDENCE  STATIC_CONFIRMED
```

### D. Slot-1 dispatch - complete caller map

```text
callers of sub_8D2A2 (the function that resolves CreateIIPSRepair):
   direct CALL : 2   (0x8DA49 in sub_8D9ED, 0x8DE3C in sub_8DBEB)
   function pointer : 0

callers of sub_197F0 (the iips.dll manager slot 1):
   direct CALL : 0
   function pointer : 1  (.rdata RVA 0x39350 = manager vtable slot 1)
   indirect dispatch : 0x3CE4 / 0x7490 in IIPSLaunchRestore.dll
```

```text
EVIDENCE  STATIC_CONFIRMED
```

---

## PHASE 3 - The TCLS <-> CODOL context boundary

This phase produced the decisive new result of EX-065.

### 3.1 The context artifacts exist and are shared

Full-tree scan (10257 files) for the context strings:

| string | encoding | modules that contain it |
|---|---|---|
| `TCLS_SHAREDMEMEMORY` | ascii + utf16 | `tcls_core.exe` (utf16), `codoMP_client_shipRetailBase.dll` (both), `TCLS.dll` (utf16), `ClientBase.dll` (both), `tpsvcBase.dll` (both), `TenProxy.dll` (utf16), `TerSafe.dll`, `TGuardBase.dll`, `wgcore.dll`, `ACE-Base32.dll`, `CODOLLauncher.exe` (utf16) |
| `GamePID` | utf16 | **`COD OL\TCLS\Tenio\TCLS.dll` ONLY** |
| `tcls_core.exe` | ascii | **`codoMP_client_shipRetailBase.dll`**, `TGuardBase.dll` |
| `CreateIIPSRepair` | ascii | `tcls_core.exe`, `IIPSLaunchRestore.dll`, `IIPSRepair.dll` |

```text
EVIDENCE  STATIC_CONFIRMED (byte scan across the whole tree)
```

### 3.2 The shared-memory name embeds the GAME PID (producer side)

`tcls_core.exe`, function containing RVA 0x798E:

```text
0x7985  lea eax, [ebp-0x418]              ; destination buffer
0x798B  push dword ptr [ebp+0xC]          ; *** the game PID argument ***
0x798E  push 0x5822E8                     ; L"TCLS_SHAREDMEMEMORY"
0x7993  push 0x582310                     ; L"%s%lu"
0x7998  push 0x104                        ; buffer length 260
0x799D  push eax
0x799E  call 0x4077F0                     ; sprintf(dst,260,"%s%lu",base,pid)
0x79A3  add esp, 0x14
0x79A6  lea eax, [ebp-0x418]
0x79AC  lea ecx, [ebx+0x2C]
0x79AF  push eax
0x79B0  call 0x407D10                     ; open/create the mapping
```

An identical construction exists at `0x40B9`:

```text
0x407F  push 0x5822B4   ; L"RAIL_TCLS_SHARED"
0x4084  push 0x5822D8   ; L"%s%llu"
0x4093  call 0x4077F0   ; sprintf -> "RAIL_TCLS_SHARED<id>"
...
0x40B6  push dword ptr [ebp+0xC]     ; the game PID
0x40B9  push 0x5822E8   ; L"TCLS_SHAREDMEMEMORY"
0x40BE  push 0x582310   ; L"%s%lu"
0x40C9  call 0x4077F0   ; sprintf -> "TCLS_SHAREDMEMEMORY<pid>"
0x40D1  lea eax, [esp+0x220]
0x40D8  lea ecx, [ebx+0x2C]
0x40DB  push eax
0x40DC  call 0x407D10   ; open/create the mapping
```

So:

```text
TCLS_SHARED_MEMORY_NAME = "TCLS_SHAREDMEMEMORY" + decimal(game PID)
buffer                   = 260 bytes (0x104)
constructor              = sprintf at 0x4077F0 (iips-provided CRT helper
                           signature: (dst, len, fmt, ...))
open/create              = sub_7D10 at 0x79B0 / 0x40DC
EVIDENCE                 = STATIC_CONFIRMED + STATIC_DATAFLOW_CONFIRMED
```

### 3.3 The consumer side (`TenProxy.dll` inside the game)

```text
TenProxy.dll  base 0x10000000  size 0x29000

UTF-16 strings:
   0x020F70  "TCLS_SHAREDMEMEMORY"
   0x020E42  "[CTclsProxy::Initialize] OpenFileMapping TCLS_SHAREDMEMEMORY+%d Success!"
   0x020EF2  "[CTclsProxy::Initialize] OpenFileMapping TCLS_SHAREDMEMEMORY+%d fail!Error code = %d "
   0x02191C  "[CTclsProxy::NotifyExit]Post TCLS_GMAE_EXIT Message Fail!"
   0x0219A8  "[CTclsProxy::NotifyExit]Post TCLS_GMAE_EXIT Message Success!"
   0x021E18  "[CTclsProxy::TenPostMessage]Post TCLS_TENPROXY_RESULT Message Fail!"
   0x021EBC  "[CTclsProxy::TenPostMessage]Post TCLS_TENPROXY_RESULT Message Success!"

imports used:
   KERNEL32!MapViewOfFile          IAT 0x10026394
   KERNEL32!OpenFileMappingW       IAT 0x10026398
   KERNEL32!GetCurrentProcessId    IAT 0x100263A0
   KERNEL32!LoadLibraryW           IAT 0x100263A4
   KERNEL32!CreateFileW            IAT 0x100263B8
   USER32!FindWindowW              IAT 0x10026514
   USER32!PostMessageW             IAT 0x10026518
   USER32!FindWindowExW            IAT 0x1002651C
```

```text
EVIDENCE  STATIC_CONFIRMED
```

### 3.4 Historical runtime confirmation (module/API-name level only)

`工具\EX035_DIR\TenproxyLog\20201216_215111.log` (a pre-existing log in the
target tree, not produced by this round):

```text
[P4540][T18500][Trace][T:InitlizeLog] tenproxy Path:d:\wegameapps\使命召唤ol
[P4540][T18500][Trace]CTclsProxy::CTclsProxy()
[P4540][T18500][Trace][CTclsProxy::Initialize] VerifyCertInfo sucess!
[P4540][T18500][Trace][CTclsProxy::Initialize] LoadLibrary GbSpy.dll sucess!
[P4540][T18500][Trace][CTclsProxy::Initialize] InitializeSecurityDescriptor
[P4540][T18500][Trace][CTclsProxy::Initialize] SetSecurityDescriptorDacl
[P4540][T18500][Trace][CTclsProxy::Initialize] GetCurrentProcessId = 4540
[P4540][T18500][Trace][CTclsProxy::Initialize] OpenFileMapping TCLS_SHAREDMEMEMORY+4540 Success!
[P4540][T18500][Trace][CTclsProxy::Initialize] MapViewOfFile Success!
[P4540][T18500][Trace]TCLS版本64兼容Proxy64
[P4540][T18500][Trace][CTclsProxy::TenPostMessage]Post TCLS_TENPROXY_RESULT Message Success!
[P4540][T18500][Trace][CTclsProxy::Initialize] GetGameSignatrue Success!
[P4540][T18500][Trace][CTclsProxy::Initialize] GetJumpSignatrue Success!
```

```text
This confirms, at the MODULE and API-NAME level:
   - TenProxy.dll loads inside the game process
   - the process id used is the GAME process id (4540, == [P4540])
   - the object name is TCLS_SHAREDMEMEMORY + that id
   - the IPC surface uses window messages

It does NOT establish, at the function level, that any specific
instruction executed, nor that the IIPS path ran.

CLASSIFICATION  HISTORICAL_DYNAMIC (module/API-name level)
NOT USED        DYNAMIC_CONFIRMED / RUNTIME_CONFIRMED
```

### 3.5 Other named objects in the TCLS protocol

| object | format string | module | RVA |
|---|---|---|---|
| TCLS core shared memory | `"TCLS_CORE_SHARE_MEMORY_%s%s"` | tcls_core.exe | `0xC629` |
| TCLS core mutex | `"TCLS_CORE_MUTEX_%s%s"` | tcls_core.exe | `0xC77F` |
| TCLS core window | `"TCLS_CORE_WND_%u"` | tcls_core.exe | `0x18F57` |
| TCLS exit event | `"TCLS_EXIT_EVENT"` | tcls_core.exe | `0x157B24` |
| rail shared memory | `"RAIL_TCLS_SHARED"` + `"%s%llu"` | tcls_core.exe | `0x407D` |
| netbar launch shared mem | `"TCLS_SHAREDMEMEMORY"` + `"NETBAR_LAUNCHGAMESHAREDMEM"` | tcls_core.exe | `0x1636B0` |
| TCLS shared shell memory | `"TCLS_SHELLMEMORY_"` | TCLS.dll | `0x3C24F4` |
| TCLS TAS memory | `"TCLS_TASMEMORY_"` | TCLS.dll | `0x3C2DF0` |
| TCLS netbar machine | `"TCLS_NETBARMACHINE_"` | TCLS.dll | `0x3C29CC` |
| TAS shared memory | `"TCLS_SHAREDMEMEMORY.%.s%.d"` | ClientBase.dll / tpsvcBase.dll / Base.dll | `0x1D3C8C` / `0x1D368C` / `0x88F108` |
| message box window | `"TCLS_MESSAGEBOX_PARENTWINDOW"`, `"TCLS_MESSAGEBOX_KEYNAME"` | TCLS.dll | `0x3BE844` |

```text
EVIDENCE  STATIC_CONFIRMED
```

### 3.6 GamePID handling (reverse direction)

```text
COD OL\TCLS\Tenio\TCLS.dll (only module containing the literal "GamePID")

  0x3C37C6  "[Clauncher::GetRealGamePID]. RealGamePID is: %d;"
  0x3C37E0  "[Clauncher::GetRealGamePID]. RealGamePID is: %d;"
  0x3C3852  "[Clauncher::GetRealGamePID]. MapViewOfFile failed: ..."
  0x3C38EE  "[Clauncher::GetRealGamePID]. open filemapping failed..."
  0x3C39CA  "[Clauncher::GetRealGamePID]. size of TPShellmemory ..."
```

So the launcher side also READS a game PID from a mapping
(`GetRealGamePID`), i.e. the PID flows in both directions through named
shared memory.

```text
GAMEPID_FLOW = STATIC_CONFIRMED (via the named-object name and the
               GetRealGamePID reader)
EVIDENCE     = STATIC_CONFIRMED
```

### 3.7 The CODOL-side peer

```text
codoMP_client_shipRetailBase.dll (the EXE's only import)

   ASCII  0x88EFFC  "TCLS_SHAREDMEMEMORY"
   UTF16  0x88F108  "TCLS_SHAREDMEMEMORY" + "%.s%.d" + "TCLS_TASMEMORY_"
   ASCII  0x88EB44  "tcls_core.exe"   (+ nearby obfuscated literals)
   ASCII  0x1470D11 "codoMP_client_shipRetailBase" + other module names
```

```text
=> the CODOL side knows both the shared-memory NAME and the literal
   file name "tcls_core.exe", but contains NO CALL, function pointer or
   import that reaches tcls_core.exe.

EVIDENCE  STATIC_CONFIRMED (2 direct-call scan + 0 le32 pointer
          occurrences for any tcls_core.exe address in the CODOL set)
```

---

## PHASE 4 - Who starts `tcls_core.exe`?

### 4.1 What was searched

Every PE in the CODOL/WeGame tree for:

```text
CreateProcessA / CreateProcessW / ShellExecute* / WinExec /
RtlCreateUserProcess
the literals "tcls_core.exe", "IIPSLaunchRestore.dll", "CreateIIPSRepair"
the exported entry names
```

### 4.2 Result

```text
files containing the literal "tcls_core.exe":
   WeGame\tcls\tcls_core.exe            (self, in its own error strings)
   COD OL\codoMP_client_shipRetailBase.dll   (ascii, 0x88EB44)
   COD OL\TGuard\TGuardBase.dll              (ascii)
   (plus the artefacts of earlier rounds)

NO module contains a CreateProcess*/ShellExecute*/WinExec call whose
argument is a plaintext "tcls_core.exe".
```

### 4.3 The TCLS host layer

`tcls_core.exe` itself implements the launcher role:

```text
class names present in .data RTTI:
   .?AVGameLauncher4TCLS_1_0@Tenio@@
   .?AV?$TTenio@VGameLauncher4TCLS_1_0@Tenio@@@Tenio@@
   .?AVTCLSHostApp@Tenio@@
   .?AVTCLS_Launcher@Tenio@@
   .?AVCTCLSLogger@Tenio@@
   .?AVCTCLS4TPFSeting@Tenio@@

methods present (log format strings):
   [TCLSHostApp::LaunchGame()]
   [TCLSHostApp::FixGame()]
   [TCLSHostApp::CancelFix()]
   [TCLSHostApp::AddGame()]
   [TCLSHostApp::RemoveGame()]
   [TCLSHostApp::CheckLocalVer()]
   [TCLSHostApp::ShowZoneUI()]
   [TCLSHostApp::CloseZoneUI()]
   [TCLSHostApp::DetectNetSpeedReport()]
   [TCLSHostApp::KillAllProcess(TclsGameID)]
   [TCLSHostApp::CheckAndTerminateTGMProcess]
   [TCLSApp::SetOpenID] / [TCLSApp::GetOpenID]
   [TCLSApp::SetNetbarInfo] / [TCLSApp::GetNetbarInfo]
   [TCLSApp::SetLoaderArguments]
   [GameLauncher4TCLS_1_0]::launchGameByTGP()
   [GameLauncher4TCLS_1_0]::launchGameByNetbar()
   [GameLauncher4TCLS_1_0]::RealLaunchGameByNetbar()
   [GameLauncher4TCLS_1_0]::[on_repair_success]
   [GameLauncher4TCLS_1_0]::[on_repair_fail]
   [RailLaunchYiLeUI]
```

### 4.4 The launch command line (decisive)

```text
tcls_core.exe  UTF-16 at VA 0x558D24:
   '"%s" -q %u'          (launchGameByTGP path)

tcls_core.exe  UTF-16 at VA 0x558E10:
   '"%s" %s'             (launchGameByNetbar path)

nearby context strings:
   'GameLauncher4TCLS_1_0::launchGameByTGP(), laun...'
   'GameLauncher4TCLS_1_0::launchGameByNetbar(),...'

and the exit event:
   'TCLS_EXIT_EVENT'
   'TCLS\EXIT_EVENT_%lu_%s'
```

The `"%s" -q %u` form is exactly the launch form used in EX-035
(`codoMP_client_shipRetail.exe -q`), with a numeric argument appended by
this launcher path.

```text
EVIDENCE  STATIC_CONFIRMED (literal format string)
```

### 4.5 Result

```text
TCLS_PROCESS_CREATION   = STATIC_BOUNDARY
TCLS_UPSTREAM_CALLER    = STATIC_BOUNDARY

tcls_core.exe is the process that LAUNCHES the game and that resolves
CreateIIPSRepair.  The process that launches tcls_core.exe is the
WeGame TCLS launcher (TGP / Netbar / Rail), which is NOT present as a
caller inside any module that names tcls_core.exe.

most precise boundary:
   MODULE   : the WeGame TCLS launcher (host of tcls_core.exe)
   FUNCTION : the code that CreateProcess()'s tcls_core.exe
   RVA      : UNKNOWN (outside the analysed tree)
   IMPORT   : none
   EXPORT   : none
   KIND     : process-creation boundary
```

---

## PHASE 5 - Native bootstrap <-> TCLS

### 5.1 What was searched

```text
for the CODOL native bootstrap (0x77F580 0x77F8B3 0x4FD9B0 0x4FCEE0
0x808650 0x7E98F0 0x6212C0):
   - immediate operands in tcls_core.exe
   - imports/exports linking the two module sets
   - function pointers / vtables
   - shared data
```

### 5.2 Result

```text
NATIVE_BOOTSTRAP_TO_TCLS = STATIC_BOUNDARY
TCLS_TO_NATIVE_BOOTSTRAP = STATIC_BOUNDARY

There is NO CALL, no function pointer, no vtable slot, no import and no
export that joins the CODOL native bootstrap to tcls_core.exe.

What DOES exist is a PROTOCOL boundary:

   codoMP_client_shipRetail.exe
        |
        |  (the game process owns a TCLS_SHAREDMEMEMORY+<pid> mapping)
        v
   TCLS_SHAREDMEMEMORY + <GamePID>
        ^
        |
        |  (tcls_core.exe creates/opens the same named mapping and
        |   posts window messages)
        |
   tcls_core.exe

plus the named window messages:
   TCLS_TENPROXY_RESULT
   TCLS_GMAE_EXIT
and the named event:
   TCLS_EXIT_EVENT
```

```text
the two halves are joined by a NAMED-OBJECT / WINDOW-MESSAGE protocol,
NOT by a call chain.

EVIDENCE
  STATIC_CONFIRMED for the absence of any CALL / pointer / import link
  STATIC_CONFIRMED for the presence of the named-object protocol on both
  sides
```

---

## PHASE 6 - Host-side launcher and GamePID/context source

### 6.1 The context object

```text
name pattern : "TCLS_SHAREDMEMEMORY" + decimal(game PID)
producer     : tcls_core.exe  (sprintf at 0x798E / 0x40B9, open at
               0x79B0 / 0x40DC)
consumer     : TenProxy.dll inside the game (OpenFileMappingW with
               GetCurrentProcessId)
reader of PID: TCLS.dll  [Clauncher::GetRealGamePID]

the same pattern also appears in:
   codoMP_client_shipRetailBase.dll   "TCLS_SHAREDMEMEMORY" + "%.s%.d"
   ClientBase.dll / tpsvcBase.dll     "TCLS_SHAREDMEMEMORY.%.s%.d"
```

### 6.2 How the game is discovered

```text
CODOL_PROCESS_DISCOVERY = STATIC_CONFIRMED

the discovery key IS the game process id, and it is embedded in the
object name.  Whoever knows the PID can open the mapping:

   tcls_core.exe launches the game     -> knows the PID
   the game itself                     -> knows its own PID
   TenProxy.dll (inside the game)      -> GetCurrentProcessId()
   TCLS.dll                            -> reads RealGamePID back out
```

### 6.3 Result

```text
STATIC_BOOTSTRAP_LINK      = HOST_PROCESS_BOUNDARY
STATIC_BOOTSTRAP_LINK_TYPE = TCLS_HOST_UNRESOLVED
                             + NAMED_OBJECT_PROTOCOL

the last unresolved node is the WeGame TCLS launcher that starts
tcls_core.exe.  Everything below it is closed:

   tcls_core.exe
     -> (message layer) -> handler table 0x16A4DC
     -> sub_8DBEB / sub_8D9EF
     -> sub_8D2A2
     -> LoadLibraryW(IIPSLaunchRestore.dll) + GetProcAddress
        ("CreateIIPSRepair") + call
     -> IIPSLaunchRestore.dll
     -> LoadLibraryW(iips.dll) + GetProcAddress("GetResourceManagerII")
     -> manager slot 26 / slot 1
     -> sub_197F0 -> sub_12760 -> CNIFS -> InitInGameApp
```

---

## Q1 - Q7 Answers

### Q1 - Who imports `GetResourceManagerII`?

```text
NONE.  (from EX-064, reconfirmed)
It is resolved dynamically by IIPSLaunchRestore.dll via GetProcAddress.
```

### Q2 - Who is the actual caller?

```text
MODULE   : IIPSLaunchRestore.dll
FUNCTION : sub_3AF0  (CallBackThread::StartLauchRestore)
RVA      : 0x3C99        (second site: 0x745F)
INSN     : call eax      ; eax = GetProcAddress(hMod, "GetResourceManagerII")
```

### Q3 - Who creates/starts `tcls_core.exe`?

```text
UNKNOWN inside the analysed tree.
STATIC_BOUNDARY: the WeGame TCLS launcher (TGP / Netbar / Rail).

evidence that tcls_core.exe is a launcher rather than a launched child:
  - it builds the game command line '"%s" -q %u'
  - it creates/opens TCLS_SHAREDMEMEMORY+<gamePID>
  - it implements TCLSHostApp::LaunchGame() / FixGame() / KillAllProcess()
  - it resolves and calls CreateIIPSRepair in IIPSLaunchRestore.dll
```

### Q4 - How does TCLS obtain the CODOL/GamePID/context?

```text
STATIC_CONFIRMED, by name, not by a call:

  1. tcls_core.exe constructs "TCLS_SHAREDMEMEMORY" + decimal(gamePID)
     (sprintf at 0x798E / 0x40B9) and opens/creates that mapping
     (sub_7D10 at 0x79B0 / 0x40DC).
  2. The game side (TenProxy.dll) opens the SAME name using its own
     GetCurrentProcessId().
  3. TCLS.dll reads "RealGamePID" back out via [Clauncher::GetRealGamePID].
  4. Additional context moves over window messages
     (TCLS_TENPROXY_RESULT, TCLS_GMAE_EXIT) and the TCLS_EXIT_EVENT.

there is no parameter-passing CALL for the context.
```

### Q5 - Does `TCLS -> IIPSLaunchRestore -> iips -> CNIFS` hold?

```text
YES, and every hop is STATIC_CONFIRMED:

  tcls_core.exe 0x8D353  LoadLibraryW(IIPSLaunchRestore.dll)
  tcls_core.exe 0x8D38A  GetProcAddress("CreateIIPSRepair")
  tcls_core.exe 0x8D39F  call CreateIIPSRepair()
  IIPSLaunchRestore.dll 0x3C48  LoadLibraryW(iips.dll)
  IIPSLaunchRestore.dll 0x3C8F  GetProcAddress("GetResourceManagerII")
  IIPSLaunchRestore.dll 0x3C99  call GetResourceManagerII()
  iips.dll manager slot 1 -> sub_197F0
  sub_197F0 -> sub_12760 -> CNIFS -> InitInGameApp
```

### Q6 - Does the external caller connect to the known native bootstrap?

```text
NOT by any CALL / pointer / import / vtable.

NATIVE_BOOTSTRAP_TO_TCLS = STATIC_BOUNDARY
TCLS_TO_NATIVE_BOOTSTRAP = STATIC_BOUNDARY

the connection that DOES exist is a named-object + window-message
protocol keyed by the game PID.
```

### Q7 - Where is the last un-crossable boundary?

```text
MODULE   : WeGame TCLS launcher (host of tcls_core.exe)
FUNCTION : the code that CreateProcess()'s tcls_core.exe
RVA      : UNKNOWN
IMPORT   : none
EXPORT   : none
IAT      : none
GetProcAddress : none

the last RECOVERED node in this line is:
   tcls_core.exe  sub_8D2A2 @ 0x8D353  LoadLibraryW

and the protocol boundary (fully recovered) is:
   TCLS_SHAREDMEMEMORY + GamePID  (named shared memory)
   TCLS_EXIT_EVENT / TCLS_TENPROXY_RESULT / TCLS_GMAE_EXIT
                                   (named event + window messages)
```

---

## Final Status

```text
TCLS_ENTRY                  = tcls_core.exe PE entry 0xB2A18
                              (__security_init_cookie -> __scrt_common_main_seh)
                              TLS callbacks: NONE (empty table at 0x15659C)
TCLS_ENTRY_TO_SUB8D2A2      = STATIC_REACHABLE
                              (through the TCLSHostApp message layer and the
                               handler table at 0x16A4DC; sub_8D2A2 has
                               exactly 2 direct callers)
CREATEIIPSREPAIR_RESOLUTION = STATIC_CONFIRMED
CREATEIIPSREPAIR_CALL       = STATIC_CONFIRMED

IIPSLAUNCHRESTORE_ENTRY     = STATIC_CONFIRMED
TCLS_TO_IIPS                = STATIC_CONFIRMED

TCLS_IPC                    = STATIC_CONFIRMED
GAMEPID_FLOW                = STATIC_CONFIRMED
TCLS_SHARED_MEMORY_FLOW     = STATIC_CONFIRMED
CODOL_PROCESS_DISCOVERY     = STATIC_CONFIRMED

TCLS_PROCESS_CREATION       = STATIC_BOUNDARY
TCLS_UPSTREAM_CALLER        = STATIC_BOUNDARY

NATIVE_BOOTSTRAP_TO_TCLS    = STATIC_BOUNDARY
TCLS_TO_NATIVE_BOOTSTRAP    = STATIC_BOUNDARY

STATIC_BOOTSTRAP_LINK       = HOST_PROCESS_BOUNDARY
STATIC_BOOTSTRAP_LINK_TYPE  = TCLS_HOST_UNRESOLVED
                              + NAMED_OBJECT_PROTOCOL

RUNTIME_GETRESOURCE_CALL    = UNKNOWN
RUNTIME_INITINGAMEAPP       = UNKNOWN
RUNTIME_IFS2_LOAD           = UNKNOWN
RUNTIME_CREATEIFS           = UNKNOWN
RUNTIME_FIRST_FAILURE       = UNKNOWN
```

## Final Classification

```text
EX065_TCLS_UPSTREAM_BOUNDARY

TCLS_PE_ENTRY_RECOVERED             STATIC_CONFIRMED
TLS_CALLBACKS_ABSENT                STATIC_CONFIRMED
CRT_STARTUP_TRACED                  STATIC_CONFIRMED
SUB8D2A2_CALLERS_FOUND_2            STATIC_CONFIRMED
HANDLER_TABLE_RECOVERED             STATIC_CONFIRMED (0x16A4DC)
CREATEIIPSREPAIR_CONTRACT_RECOVERED STATIC_CONFIRMED
TCLS_IPC_PROTOCOL_RECOVERED         STATIC_CONFIRMED
SHARED_MEMORY_NAME_PATTERN_RECOVERED STATIC_DATAFLOW_CONFIRMED
GAMEPID_EMBEDDED_IN_OBJECT_NAME     STATIC_CONFIRMED
LAUNCH_COMMAND_LINE_RECOVERED       STATIC_CONFIRMED
NAMED_OBJECT_PROTOCOL_BOUNDARY      STATIC_CONFIRMED
HOST_PROCESS_BOUNDARY               STATIC_BOUNDARY
PACKED_CALLER_UNRESOLVED            (EXE side, unchanged)

RUNTIME_GETRESOURCE_CALL            UNKNOWN
RUNTIME_INITINGAMEAPP               UNKNOWN
RUNTIME_IFS2_LOAD                   UNKNOWN
RUNTIME_CREATEIFS                   UNKNOWN
RUNTIME_FIRST_FAILURE               UNKNOWN

NO_HOOK
NO_API_DETOUR
NO_IAT_PATCH
NO_INLINE_PATCH
NO_DEBUGGER_ATTACH
NO_FRIDA
NO_TARGET_MEMORY_MODIFICATION
NO_IAT_EXPORT_VTABLE_MODIFICATION
NO_FAKE_RETURN
NO_BYPASS
NO_PARAMETER_TAMPERING
NO_BINARY_MODIFICATION
NO_FAKE_IIPS_SUCCESS
NO_DYNAMIC_CONFIRMED
NO_RUNTIME_CONFIRMED
NO_SUCCESS_CLAIM
```

## STATIC_UNKNOWN

```text
U01  The upstream launcher module/function that CreateProcess()'s
     tcls_core.exe.
U02  The exact runtime value of the numeric argument in '"%s" -q %u'.
U03  Whether the observed -q runs used the TGP or the Netbar launch path.
U04  The complete TCLSHostApp message-number -> handler mapping
     (only 0x63 / 0x18 / 0x11 gates were recovered).
U05  The full caller set of sub_5EA87 / sub_5F4A3.
U06  The layout of the 0x5268-byte TCLSHostApp object.
U07  The meaning of the state values 0x63 / 0x18 / 0x11 in sub_8DBEB /
     sub_8D9EF.
U08  Whether TCLS_SHAREDMEMEMORY<pid> and TCLS_SHAREDMEMEMORY+<pid> are
     the same object or two objects (the + appears only in TenProxy's
     log/message text; tcls_core builds without it).
U09  The content structure of the shared memory (mmog_data.xml,
     VersionUpdateData, NETBAR_LAUNCHGAMESHAREDMEM are the only names
     recovered).
U10  Whether the EXE's packed .tp3 copy of "GetResourceManagerII" is
     used by any code path.
U11  Whether the TCLS path is exercised in a normal -q launch, or only
     in repair / pre-download flows.
U12  Whether tcls_core.exe is launched per-run or resident.
U13  The exact PID-to-object-name separator (tcls_core uses none;
     TenProxy's message shows a '+'; Base.dll uses a '.').
U14  Whether the CODOL base.dll "tcls_core.exe" literal is used to
     launch/attach the process (no CreateProcess argument match found).
```

## Verification Artifacts

```text
ex065_tcls_entry.csv             9 rows: entry -> sub_8D2A2 chain
ex065_createiipsrepair.csv       9 rows: the CreateIIPSRepair contract
ex065_tcls_ipc.csv              20 rows: the named-object protocol
ex065_tcls_callers.csv           9 rows: sub_8D2A2 / handler-table callers
ex065_host_process_edges.csv     7 rows: host-process edges
ex065_bootstrap_boundary.csv     7 rows: bootstrap boundary classification
ex065_loader_edges.csv           7 rows: dynamic loader edges
ex065_entry.txt                       : PE header / TLS
ex065_startup.txt                     : entry stub + TLS
ex065_crt.txt / ex065_mainptr.txt     : CRT startup trace
ex065_callers_8d2a2.txt               : the two sub_8D2A2 callers
ex065_registration.txt                : handler-table registration
ex065_upstream.txt                    : callers of the protocol methods
ex065_ipc.txt / ex065_ipc_sites.txt   : all IPC API call sites
ex065_protocol.txt                    : the full protocol string dump
ex065_exact_fmt.txt                   : exact name format strings
ex065_sharemem.txt                    : shared-memory name construction
ex065_tenproxy.txt                    : TenProxy protocol strings
ex065_tree_scan.txt                   : whole-tree context-artifact scan
```
