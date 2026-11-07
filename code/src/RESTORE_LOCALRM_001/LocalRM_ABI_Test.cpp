#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

// Function pointer types
typedef RMObject* (__stdcall *PFN_GetResourceManagerII)();
typedef void (__stdcall *PFN_ReleaseResourceManagerII)(RMObject*);

// Structure definitions (must match the DLL)
struct NestedObject {
    void* vptr1;
    void* vptr2;
    char padding3[0x24];
    void* vptr3;
    char padding4[0x14];
    HANDLE handle;
    char padding5[0x38];
    void* functionPointer;
    char padding6[0x8];
};

struct RMObject {
    void* vptr;
    char padding1[0x68];
    int stateCounter;
    NestedObject nestedObject;
    int processFlag;
    char padding2[0x410 - sizeof(void*) - 0x68 - sizeof(int) - sizeof(NestedObject) - sizeof(int)];
};

// Helper to check if a pointer is valid (not null and within user space)
BOOL IsValidPointer(const void* ptr) {
    if (ptr == NULL) return FALSE;
    // Simple check: not in the first 64KB and not above 0x7FFFFFFF
    uintptr_t uptr = (uintptr_t)ptr;
    return (uptr > 0x10000 && uptr < 0x7FFFFFFF0000);
}

// Main test function
int main() {
    printf("LocalRM ABI Test\\n");
    printf("================\\n");

    // Load the DLL
    HMODULE hMod = LoadLibraryA("LocalRM.dll");
    if (hMod == NULL) {
        printf("FAIL: Could not load LocalRM.dll\\n");
        return 1;
    }
    printf("PASS: LoadLibrary succeeded\\n");

    // Get function pointers
    PFN_GetResourceManagerII pGet = (PFN_GetResourceManagerII)GetProcAddress(hMod, "GetResourceManagerII");
    PFN_ReleaseResourceManagerII pRelease = (PFN_ReleaseResourceManagerII)GetProcAddress(hMod, "ReleaseResourceManagerII");
    if (pGet == NULL) {
        printf("FAIL: GetResourceManagerII not found\\n");
        FreeLibrary(hMod);
        return 1;
    }
    if (pRelease == NULL) {
        printf("FAIL: ReleaseResourceManagerII not found\\n");
        FreeLibrary(hMod);
        return 1;
    }
    printf("PASS: GetProcAddress for both exports succeeded\\n");

    // Test A: object allocation
    RMObject* p1 = pGet();
    if (p1 == NULL) {
        printf("FAIL: GetResourceManagerII returned NULL\\n");
        FreeLibrary(hMod);
        return 1;
    }
    printf("PASS: GetResourceManagerII returned non-NULL pointer: %p\\n", p1);

    // Test B: object size/layout
    // Check vtable pointer
    if (!IsValidPointer(p1->vptr)) {
        printf("FAIL: vptr is invalid: %p\\n", p1->vptr);
        FreeLibrary(hMod);
        return 1;
    }
    printf("PASS: vptr is valid: %p\\n", p1->vptr);

    // Check nested object area (we can check that the nested object's vptrs are valid)
    if (!IsValidPointer(p1->nestedObject.vptr1) ||
        !IsValidPointer(p1->nestedObject.vptr2) ||
        !IsValidPointer(p1->nestedObject.vptr3)) {
        printf("FAIL: nested object vptrs are invalid\\n");
        FreeLibrary(hMod);
        return 1;
    }
    printf("PASS: nested object vptrs are valid\\n");

    // Check +0x3BC is accessible (processFlag)
    int processFlag = p1->processFlag;
    printf("INFO: processFlag (at +0x3BC) = %d\\n", processFlag);

    // Test C: repeated Get
    RMObject* p2 = pGet();
    if (p2 == NULL) {
        printf("FAIL: second GetResourceManagerII returned NULL\\n");
        FreeLibrary(hMod);
        return 1;
    }
    if (p1 != p2) {
        printf("FAIL: second Get returned different pointer: %p vs %p\\n", p1, p2);
        FreeLibrary(hMod);
        return 1;
    }
    printf("PASS: repeated Get returns the same pointer\\n");

    // Test D: vtable[2] (CheckState)
    // We need to call the function via the vtable
    // Note: This is unsafe if the vtable is not set up correctly, but we have checked the vptr.
    typedef int (__stdcall *PFN_CheckState)(RMObject*);
    PFN_CheckState pCheckState = (PFN_CheckState)(*(void**)((uintptr_t)p1->vptr + 2 * sizeof(void*)));
    if (!IsValidPointer(pCheckState)) {
        printf("FAIL: CheckState function pointer is invalid\\n");
        FreeLibrary(hMod);
        return 1;
    }
    int checkStateResult = pCheckState(p1);
    printf("INFO: CheckState returned %d\\n", checkStateResult);
    // We don't fail on the return value, just that the call didn't crash
    printf("PASS: CheckState call did not crash\\n");

    // Test E: vtable[3] (Process)
    typedef int (__stdcall *PFN_Process)(RMObject*);
    PFN_Process pProcess = (PFN_Process)(*(void**)((uintptr_t)p1->vptr + 3 * sizeof(void*)));
    if (!IsValidPointer(pProcess)) {
        printf("FAIL: Process function pointer is invalid\\n");
        FreeLibrary(hMod);
        return 1;
    }
    int processResult = pProcess(p1);
    printf("INFO: Process returned %d\\n", processResult);
    printf("PASS: Process call did not crash\\n");

    // Test F: Release
    pRelease(p1);
    printf("INFO: ReleaseResourceManagerII called\\n");
    // Check that the process is still alive (we are still here)
    printf("PASS: Release did not crash the process\\n");

    // Test G: second lifecycle
    RMObject* p3 = pGet();
    if (p3 == NULL) {
        printf("FAIL: GetResourceManagerII after Release returned NULL\\n");
        FreeLibrary(hMod);
        return 1;
    }
    printf("PASS: GetResourceManagerII after Release returned non-NULL: %p\\n", p3);
    // Note: We don't check if p3 is the same as p1 or not, because the implementation may choose to reuse or not.

    // Clean up
    FreeLibrary(hMod);
    printf("SUCCESS: All tests passed\\n");
    return 0;
}