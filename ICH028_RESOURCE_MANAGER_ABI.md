# ICH-028 - Resource Manager ABI Recovery

## Core Discovery

The ResourceManager is a **C++ object with a 48-entry vtable**,
implemented as a singleton inside iips.dll. The vtable pointer is
`0x10035CF4`, and the object is allocated with 0x480 bytes.

## GetResourceManagerII Return Value

```text
GetResourceManagerII (iips.dll + 0x1C80):
  Singleton pattern with init flag at [0x1004EB6C]
  Allocates 0x410 bytes on first call
  Calls constructor at 0x10010200
  Returns pointer to constructed object

GetResourceManager (iips.dll + 0x1BC0):
  Singleton pattern with init flag at [0x1004EB74]
  Allocates 0x480 bytes on first call
  Calls constructor at 0x10010200
  Stores result at global [0x1004EB70]
  Returns EAX = object pointer
```

## ResourceManager Object Layout

```text
Offset   Size   Content
+0x000   4      VTable pointer → 0x10035CF4
+0x004   ...    String table / name (initialized by 0x10002AC0)
                Contains: "ResourceManager"
+0x06C   4      State/counter (initialized to 0)
+0x070   ...    Nested object (initialized by 0x10011F20)
+0x3BC   1      Flag (checked by RM_METHOD_0C)
...
Total: 0x480 bytes (GetResourceManager) / 0x410 (GetResourceManagerII)
```

## VTable: 48 Methods

```text
VTable at 0x10035CF4:

Index  Offset  Method RVA   Method Name (provisional)
  0    +0x00   0x10010280   RM_DESTRUCTOR (calls 0x100102A0, then free if flag)
  1    +0x04   0x10010DB0   RM_INIT (SEH prologue, complex init)
  2    +0x08   0x10010320   RM_CHECK_STATE (reads this+0x70 → nested call)
  3    +0x0C   0x10010380   RM_PROCESS (checks this+0x3BC flag, complex)
  4    +0x10   0x10010470   RM_METHOD_10
  5    +0x14   0x10010520   RM_METHOD_14
  6    +0x18   0x100105D0   RM_METHOD_18
  7    +0x1C   0x100106A0   RM_METHOD_1C
  8    +0x20   0x10010750   RM_METHOD_20
  9    +0x24   0x10010800   RM_METHOD_24
 10    +0x28   0x100109A0   RM_METHOD_28
 11    +0x2C   0x100108B0   RM_METHOD_2C
 12    +0x30   0x10010C40   RM_METHOD_30
 13    +0x34   0x10010960   RM_METHOD_34
 14    +0x38   0x100109E0   RM_METHOD_38
 15    +0x3C   0x10010A20   RM_METHOD_3C
 ...   ...     ...          ...
 47    +0xBC   0x10010DA0   RM_METHOD_BC (last entry)
```

VTable ends at offset +0xC0 where a non-function value (0x750025)
appears — this is the string "u%" which is adjacent data.

## Method Analysis

### RM_METHOD_00 (Destructor)
```asm
push esi / mov esi,ecx / push esi
call 0x100102A0          ; internal cleanup
test byte [esp+8],1      ; check delete flag
je skip
push esi / call free     ; free if flag set
```

### RM_METHOD_02 (Check State)
```asm
mov esi,ecx
mov eax,[esi+0x70]       ; read nested object
mov edx,[eax+8]          ; read nested vtable+8
lea ecx,[esi+0x70]       ; this = nested object
call edx                 ; virtual call on nested object
test al,al               ; boolean result
```
This method checks a boolean state via the nested object at this+0x70.

### RM_METHOD_03 (Process)
```asm
mov esi,ecx
cmp byte [esi+0x3BC],0   ; check flag
jne skip_init
cmp byte [0x1004CDD8],0  ; check global flag
...
```
This method checks a per-object flag and a global flag before processing.

## ReleaseResourceManager

```asm
mov ecx,[esp+4]          ; get RM pointer from stack
test ecx,ecx             ; null check
je done
mov eax,[ecx]            ; read vtable
mov edx,[eax]            ; read vtable[0] = destructor
push 1                   ; delete flag = true
call edx                 ; call destructor
done: ret
```

Confirms: vtable[0] is the destructor, called with delete flag.

## Engine Consumer Model

When Engine receives the ResourceManager pointer:

```text
RM = GetResourceManagerII()  → pointer to 0x480-byte object
Engine stores RM pointer
Engine calls [RM→vtable+X] for various operations

First likely call: RM_METHOD_02 (Check State)
  → reads nested object at RM+0x70
  → calls nested vtable method
  → returns boolean "ready" status

If ready → Engine proceeds to resource loading
If not ready → Engine calls RM_METHOD_03 (Process) to trigger download
```

## Compatibility Surface (Minimum)

To satisfy the Engine's dependency, a local implementation needs:

```text
1. Allocate a 0x480-byte object
2. Set [obj+0x00] = pointer to a vtable with at least 48 entries
3. Implement at minimum:
   - vtable[0]: destructor (can be no-op)
   - vtable[2]: check state (return TRUE)
   - vtable[3]: process (no-op or minimal)
4. Initialize [obj+0x70] with a nested object that has its own
   vtable with at least 3 methods
5. Return the object pointer from GetResourceManagerII

Additional methods may be needed as the Engine calls them,
but these 3 methods are the minimum to pass the initial gate.
```
