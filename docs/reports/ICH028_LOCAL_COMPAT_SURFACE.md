# ICH-028 - Resource Manager Compatibility Surface

## Local IIPS Compatibility Layer Design

### Minimum Viable ResourceManager

Based on the 48-entry vtable and object layout analysis, the minimum
local implementation needs:

```cpp
// VTable with 48 entries (all must be valid function pointers)
static void* localRM_vtable[48] = {
    (void*)LocalRM_Destructor,      // +0x00: vtable[0]
    (void*)LocalRM_Init,            // +0x04: vtable[1]
    (void*)LocalRM_CheckState,      // +0x08: vtable[2] - returns TRUE
    (void*)LocalRM_Process,         // +0x0C: vtable[3] - no-op
    // ... remaining 44 entries can be stubs that return 0/1
};

// Object layout (0x480 bytes)
struct LocalResourceManager {
    void* vtable;          // +0x000: points to localRM_vtable
    uint8_t padding[0x68]; // +0x004..+0x06B: zero-filled
    uint32_t counter;      // +0x06C: set to 0
    void* nested;          // +0x070: pointer to nested object
    uint8_t rest[0x34C];   // +0x074..+0x3BF: zero-filled
    uint8_t flag_3BC;      // +0x3BC: set to 0 or 1
    // ... remaining bytes
};

// Nested object at +0x70 (minimum)
struct LocalNestedObject {
    void* vtable;          // needs at least 3 methods
    uint8_t padding[0x2C];
    uint32_t field_8;      // accessed by vtable[2] of nested
};
```

### Required Method Behaviors

```text
vtable[0] (Destructor): Accept flag parameter, free if flag=1
vtable[1] (Init): Accept context, return success
vtable[2] (CheckState): Read nested->vtable[2], return TRUE (non-zero)
vtable[3] (Process): Check flags, perform no-op or minimal processing
Remaining 44: Return 0 or 1 depending on typical getter/setter semantics
```

### Critical Values

```text
RM object size:      0x480 bytes (GetResourceManager) or 0x410 (GetResourceManagerII)
VTable entries:      48
Nested object:       at RM+0x70, needs its own vtable
Key flag:            RM+0x3BC (checked before processing)
Global singleton:    iips.dll 0x1004EB6C (II) / 0x1004EB74 (I)
```

### Compatibility Strategy

Rather than implementing all 48 methods, use this approach:

1. **Return TRUE from all boolean methods** (check state, is ready, etc.)
2. **Return 0 from all size/progress methods** (no downloads needed)
3. **No-op all processing methods** (process, sync, download)
4. **Return valid data for getter methods** based on local file system
5. **Start with the 3 confirmed methods** and add more as Engine calls
   reveal additional requirements

### First Call Prediction

Based on the Engine's resource loading pattern:
```text
1. RM_METHOD_02 (CheckState) → must return TRUE
2. RM_METHOD_03 (Process) → must not crash
3. RM_METHOD_01 (Init) → must return success
4. Then: Engine calls loadfastfile → Zone → Asset
```
