#include <windows.h>

// Forward declarations
struct RMObject;
struct NestedObject;

// RM object structure (0x410 bytes)
struct RMObject {
    void* vptr; // +0x000
    char padding1[0x68]; // +0x004 to +0x6B
    int stateCounter; // +0x06C
    NestedObject nestedObject; // +0x070 (in-place nested object)
    int processFlag; // +0x3BC
    char padding2[0x410 - sizeof(void*) - 0x68 - sizeof(int) - sizeof(NestedObject) - sizeof(int)];
};

// Nested object structure
struct NestedObject {
    void* vptr1; // +0x00 (vtable1)
    void* vptr2; // +0x04 (vtable2)
    char padding3[0x24]; // +0x08 to +0x2B (for CRITICAL_SECTION placeholder)
    void* vptr3; // +0x44 (vtable3)
    char padding4[0x58 - 0x48]; // +0x48 to +0x57
    HANDLE handle; // +0x58
    char padding5[0x94 - 0x5C]; // +0x5C to +0x93
    void* functionPointer; // +0x94
    // Assume the nested object size is 0xA0 for example
    char padding6[0xA0 - 0x98]; // +0x98 to +0x9F
};

// Global instance of RMObject (singleton)
static RMObject g_rmObject = {0};

// Function prototypes for RM vtable
typedef int (*RM_CheckState)(RMObject* this);
typedef int (*RM_Process)(RMObject* this);
typedef void (*RM_Destructor)(RMObject* this);
typedef int (*RM_Initialize)(RMObject* this);

// Function prototypes for nested object vtable1
typedef int (*Nested_VTable1_Method2)(NestedObject* this); // CheckState calls this
typedef int (*Nested_VTable1_Method4)(NestedObject* this); // Process calls this

// Function prototypes for nested object vtable2
typedef int (*Nested_VTable2_Method0)(NestedObject* this); // Initialize calls this

// RM vtable (48 entries)
static void* g_rmVTable[48] = {
    (void*)[](RMObject* this) { }, // vtable[0] destructor
    (void*)[](RMObject* this) { return 0; }, // vtable[1] initialize
    (void*)[](RMObject* this) { return 1; }, // vtable[2] CheckState
    (void*)[](RMObject* this) { return 0; }, // vtable[3] Process
    // Fill the rest with nullptrs (safe stubs)
    nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr,
    nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr,
    nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr,
    nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr,
    nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr
};

// Nested object vtable1 (12 entries)
static void* g_nestedVTable1[12] = {
    nullptr, nullptr, (void*)[](NestedObject* this) { return 1; }, // vtable1[2] CheckState
    nullptr, (void*)[](NestedObject* this) { return 0; }, // vtable1[4] Process
    nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr
};

// Nested object vtable2 (8 entries)
static void* g_nestedVTable2[8] = {
    (void*)[](NestedObject* this) { return 0; }, // vtable2[0] Initialize
    nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr
};

// Nested object vtable3 (let's say 4 entries for example)
static void* g_nestedVTable3[4] = {
    nullptr, nullptr, nullptr, nullptr
};

// Initialize the singleton object
void InitializeRMObject() {
    // Set the vptr for the RM object
    g_rmObject.vptr = g_rmVTable;
    // Initialize the nested object's vptrs
    g_rmObject.nestedObject.vptr1 = g_nestedVTable1;
    g_rmObject.nestedObject.vptr2 = g_nestedVTable2;
    g_rmObject.nestedObject.vptr3 = g_nestedVTable3;
    // Initialize the state counter to 0
    g_rmObject.stateCounter = 0;
    // Initialize the process flag to 0
    g_rmObject.processFlag = 0;
    // Initialize the nested object's fields to zero/safe values
    ZeroMemory(&g_rmObject.nestedObject, sizeof(NestedObject));
    // Reset the vptrs after zeroing
    g_rmObject.nestedObject.vptr1 = g_nestedVTable1;
    g_rmObject.nestedObject.vptr2 = g_nestedVTable2;
    g_rmObject.nestedObject.vptr3 = g_nestedVTable3;
    g_rmObject.nestedObject.handle = NULL;
    g_rmObject.nestedObject.functionPointer = NULL;
}

// Exported functions
extern "C" __declspec(dllexport) RMObject* __stdcall GetResourceManagerII() {
    static BOOL initialized = FALSE;
    if (!initialized) {
        InitializeRMObject();
        initialized = TRUE;
    }
    return &g_rmObject;
}

extern "C" __declspec(dllexport) void __stdcall ReleaseResourceManagerII(RMObject* obj) {
    // For the singleton, we do nothing. The object is not deleted.
    // This is safe because the object has static storage duration.
}

// DllMain
BOOL APIENTRY DllMain(HMODULE hModule, DWORD  ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}