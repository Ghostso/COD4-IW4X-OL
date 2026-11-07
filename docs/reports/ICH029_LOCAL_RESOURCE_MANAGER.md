# ICH-029 — LocalResourceManager Minimal Compatibility

## A. Object Size Resolution: 0x410 is Sufficient

Static analysis of all 48 vtable methods confirms:

```text
Maximum field offset accessed: 0x3BC
Accesses beyond 0x410: 0
Accesses beyond 0x480: 0
```

The difference between 0x410 (GetResourceManagerII) and 0x480
(GetResourceManager) is **excess allocation padding**. No vtable
method accesses any field beyond 0x3BC.

```text
RESOURCE_MANAGER_ALLOC_SIZE = 0x410 (sufficient)
RESOURCE_MANAGER_REQUIRED_SIZE = 0x410 (confirmed by max offset 0x3BC)
```

## B. LocalResourceManager Design

```c
#include <string.h>
#include <stdlib.h>

// Forward declarations
static void* LocalRM_NestedVTable[4];
static void* LocalRM_VTable[48];

// Nested object (at RM+0x70)
typedef struct {
    void* vtable;           // +0x00
    uint8_t pad[0x2C];      // +0x04..0x2F
    uint32_t field_0x30;    // +0x30
} LocalNestedObject;

// VTable method stubs
static void* LocalRM_Destructor(void* this, int deleteFlag) {
    if (deleteFlag) free(this);
    return this;
}

static int LocalRM_CheckState(void* this) {
    // Read nested object and return TRUE
    // Engine checks: mov eax,[ecx+0x70] / call [eax+vtable+2]
    return 1;  // TRUE = resources ready
}

static int LocalRM_Process(void* this) {
    // No-op processing, return success
    return 0;  // 0 = no error
}

static int LocalRM_Init(void* this) {
    return 0;  // success
}

static int LocalRM_Stub(void* this) {
    return 0;
}

// Build vtable
static void* LocalRM_VTable[48] = {
    LocalRM_Destructor,   // [0]
    LocalRM_Init,         // [1]
    LocalRM_CheckState,   // [2]
    LocalRM_Process,      // [3]
    // [4..47] = LocalRM_Stub
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
    LocalRM_Stub, LocalRM_Stub, LocalRM_Stub, LocalRM_Stub,
};

static void* LocalRM_NestedVTable[4] = {
    LocalRM_Stub,  // [0]
    LocalRM_Stub,  // [1]
    LocalRM_Stub,  // [2] - this is what CheckState calls
    LocalRM_Stub,  // [3]
};

// Create the ResourceManager
void* CreateLocalResourceManager(void) {
    void* obj = calloc(1, 0x410);
    if (!obj) return NULL;
    
    // Set vtable
    *(void**)obj = LocalRM_VTable;
    
    // Set string at +0x04 (copy "ResourceManager")
    strcpy((char*)obj + 4, "ResourceManager");
    
    // Set counter at +0x6C
    *(uint32_t*)((uint8_t*)obj + 0x6C) = 0;
    
    // Create nested object at +0x70
    void* nested = calloc(1, 0x40);
    if (nested) {
        *(void**)nested = LocalRM_NestedVTable;
        memcpy((uint8_t*)obj + 0x70, nested, sizeof(LocalNestedObject));
        // Note: need to track separately or embed
    }
    
    // Set flag at +0x3BC
    *(uint8_t*)((uint8_t*)obj + 0x3BC) = 0;
    
    return obj;
}
```

## C. Integration Approach

The local ResourceManager should be injected via one of:

1. **IAT hooking** (modifies the IAT entry for GetResourceManagerII)
2. **DLL proxy** (rename original iips.dll, provide our own)
3. **DLL injection** (inject a DLL that hooks GetProcAddress)
4. **Direct code modification** (patch the EXE to skip LoadLibrary)

**Recommended: DLL proxy approach** — simplest, non-invasive to EXE.

```text
1. Rename COD OL\IIPS\iips.dll → iips_original.dll
2. Place our iips.dll proxy in the same directory
3. Proxy implements GetResourceManagerII returning our local object
4. Proxy forwards all other exports to iips_original.dll
```

## D. Observation Plan

After GetResourceManagerII returns our local object:

```text
Monitor:
  1. Is vtable[2] (CheckState) called?
  2. Is vtable[3] (Process) called?
  3. Are any vtable[4..47] called? (log which index)
  4. Does the Engine dispatch table change after CheckState?
  5. Do any new global variables change?
  6. Does the process survive past the IIPS gate?
```

## Expected Results

```text
If CheckState=TRUE is sufficient:
  → Engine proceeds past IIPS gate
  → New engine functions execute
  → Resource loading begins

If CheckState=TRUE is NOT sufficient:
  → Engine calls Process() or other methods
  → Need to implement additional methods

If Engine calls unimplemented method:
  → Log which vtable index → implement that method → retry
  → Iterative approach, one method at a time
```

## E. Implementation Notes

The nested object at RM+0x70 is initialized by iips.dll function
0x10011F20 (a 0xC8-byte stack frame function with SEH). The nested
object's vtable is used by RM_METHOD_02 (CheckState) which calls
`[nested->vtable+8]`. Our local nested vtable[2] must return
a non-zero value for CheckState to return TRUE.

## F. Safety Considerations

- The Engine may call ReleaseResourceManagerII which calls vtable[0]
  with delete flag — our destructor must handle this safely
- The Engine may call methods not in our implementation — log and
  return 0 to avoid crashes
- Do NOT free the singleton object on Release if the Engine might
  call GetResourceManagerII again (singleton pattern)
