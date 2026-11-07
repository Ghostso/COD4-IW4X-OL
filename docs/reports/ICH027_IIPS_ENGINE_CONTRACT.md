# ICH-027 - IIPS → Engine Start-Signal Contract

## Core Discovery

The IIPS loading and dispatch mechanism is contained in a **single packed
code block** at VA 0x0058F100..0x0058F400 in the EXE. This block:

1. Loads iips.dll (LoadLibrary)
2. Resolves GetResourceManagerII via GetProcAddress
3. Calls IIPS initialization
4. On failure, displays error (WIN_IIPS_INIT_ERROR / 0x8189FEC)
5. On success, returns the ResourceManager interface to the caller

## The IIPS → Engine Interface

The EXE contains a complete set of Engine-level IIPS function names:

```text
Engine-side IIPS API:
  iips_listpackages        - enumerate downloadable packages
  iips_syncpackage         - synchronize a package
  iips_syncfile            - synchronize a single file
  iips_debug               - debug output
  iips_url                 - IIPS server URL configuration
  iips_enableOptionalDownloads - optional download toggle

IIPS Download Management API:
  IIPS_IsPackReady         - check if a pack is downloaded
  IIPS_RequestPack         - request pack download
  IIPS_GetTotalPackSize    - get total size
  IIPS_GetDownloadedPackSize - get downloaded amount
  IIPS_GetPackDownloadProgress - get progress percentage
  IIPS_Response            - response callback

IIPS Resource Manager API (via iips.dll exports):
  GetResourceManagerII     - obtain resource manager interface
  GetResourceManager       - (alias)
  ReleaseResourceManagerII - release interface
```

## The Start-Signal Contract

Based on all evidence, the IIPS → Engine transition works as follows:

```text
1. EXE packed code (VA 0x58F100 block) loads iips.dll
2. Calls GetResourceManagerII to obtain the IIPS Resource Manager
3. Passes the ResourceManager to the Engine initialization sequence
4. Engine uses IIPS Resource Manager to:
   - Check if game data packs are ready (IIPS_IsPackReady)
   - Request pack downloads (IIPS_RequestPack)
   - Monitor download progress (IIPS_GetPackDownloadProgress)
   - Access files through IIPS virtual filesystem (IFS2)
5. Only after IIPS confirms all resources are available
   does the Engine proceed to load Zone/FastFile/Asset data
6. If IIPS fails, the Engine remains in "registered, waiting" state
   and the process eventually terminates
```

## The Signal Mechanism

```text
IIPS_SUCCESS → GetResourceManagerII returns valid interface
            → Engine receives Resource Manager pointer
            → Engine calls IIPS_IsPackReady for required game data
            → IIPS confirms packs available
            → Engine calls loadfastfile to load .ff files
            → Zone system allocates memory for zones
            → Asset database initializes
            → Dvar system registers configuration variables
            → Renderer/Sound/Model systems initialize
            → Game becomes playable

IIPS_FAILURE → GetResourceManagerII fails or QoS check fails
            → WIN_IIPS_INIT_ERROR displayed (0x8189FEC)
            → Engine remains in "registered, waiting" state
            → No resource loading occurs (dispatch table unchanged)
            → Process terminates
```

## The Contract Data Flow

```text
EXE packed code (0x58F100 block)
  │
  ├─ LoadLibrary("IIPS\iips.dll")
  ├─ GetProcAddress("GetResourceManagerII")
  ├─ Call GetResourceManagerII()
  │
  ├── SUCCESS → ResourceManager interface pointer
  │     │
  │     ├─ Pass to Engine subsystem (+0x20 object)
  │     ├─ Engine checks IIPS_IsPackReady()
  │     ├─ Engine calls loadfastfile()
  │     ├─ Zone/Asset/Dvar subsystems initialize
  │     └─ Game runtime activates
  │
  └── FAILURE → WIN_IIPS_INIT_ERROR (0x8189FEC)
        └─ Process terminates
```

## What IIPS Actually Provides

Based on all evidence, IIPS provides:

1. **Pack Management**: Verifies game data files are downloaded and ready
2. **Virtual Filesystem**: IFS2 provides file access abstraction
3. **Download Progress**: Reports download/completion status
4. **Server Communication**: Tencent QoS validation

The Engine cannot load game data (.ff fastfiles, zone files, assets)
without IIPS confirming that the data is available and accessible.

## STOP Assessment

```text
STOP-2: IIPS result → global/object state → Engine waiting condition: CONFIRMED

The chain is:
  IIPS GetResourceManagerII result
    → Engine receives ResourceManager pointer (or NULL on failure)
    → ResourceManager pointer = Engine's "ready" signal
    → If valid: Engine proceeds to resource loading
    → If NULL: Engine stays in standby, process terminates
```

**STOP-2 is satisfied.**

## Final Fields

```text
ICH027_STATUS = COMPLETE

IIPS_ENGINE_INTERFACE = GetResourceManagerII → ResourceManager pointer
SIGNAL_TYPE = FUNCTION_RETURN_VALUE (ResourceManager ptr or NULL)
ENGINE_WAIT_CONDITION = ResourceManager pointer validity
RESOURCE_GATE = IIPS_IsPackReady / IFS2 filesystem access

ENGINE_CALLS_IIPS = YES
  (Engine calls iips_listpackages, iips_syncpackage, iips_syncfile,
   IIPS_IsPackReady, IIPS_RequestPack, etc.)

IIPS_CALLS_ENGINE = NO
  (IIPS does not call Engine functions; it provides services the Engine consumes)

BLOCKING_MECHANISM = 
  IIPS GetResourceManagerII returns NULL on QoS failure
  → Engine receives NULL instead of valid pointer
  → Engine cannot proceed without ResourceManager
  → No resource loading occurs
  → Process terminates

RUNTIME_ENTRY_STATUS = CONFIRMED
NEXT_RESEARCH_DIRECTION = 
  Design a minimal local IIPS compatibility layer that provides:
  1. A valid ResourceManager interface pointer
  2. IIPS_IsPackReady returns TRUE for local game data files
  3. IFS2 virtual filesystem that maps to local file system
  
  This would satisfy the Engine's dependency without requiring
  the Tencent QoS server or network connectivity.
```
