# ICH-018 - QoS Helper Static Analysis

## Objective

Determine why iips.dll+0x6D20 returns 0 by performing limited-depth
static disassembly of the QoS helper function and its dependency chain.

## Function Boundary

```text
QOS_FUNCTION_START = iips.dll + 0x6D20 (VA 0x10006D20)
QOS_FUNCTION_END   = iips.dll + 0x6E3C (VA 0x10006E3C, ret 4)
Function size:     0x11C bytes (284 bytes)
Calling convention: __thiscall (ECX = this pointer, stack arg at [esp+4])
```

## Complete Disassembly (annotated)

```text
; === Function entry / SEH setup ===
0x6D20: push -1                     ; SEH try
0x6D22: push 0x1003255B             ; SEH handler scope
0x6D27: mov eax, fs:[0]             ; get SEH chain
0x6D2D: push eax
0x6D2E: sub esp, 0x408              ; allocate 0x408 stack
0x6D34: mov eax, [0x10042020]       ; stack cookie
0x6D39: xor eax, esp
0x6D3B: mov [esp+0x404], eax        ; store cookie
0x6D42: push ebx
0x6D43: push edi

; === EnterCriticalSection ===
0x6D59: lea edi, [esi+0xC]          ; this->CriticalSection
0x6D5C: push edi
0x6D61: call [0x10033028]           ; KERNEL32!EnterCriticalSection

; === Read byte from caller's stack ===
0x6D67: mov al, [esp+0x424]         ; read a byte (parameter)
0x6D6E: xor ebx, ebx                ; ebx = 0

; === Check if already initialized ===
0x6D77: cmp [esi], ebx              ; this->initialized == 0?
0x6D79: mov [esi+8], al             ; store parameter byte
0x6D7C: jne 0x6E0E                  ; already init: goto success_exit

; === FIRST TIME INITIALIZATION ===
0x6D82: push 0x3FF                  ; buffer size
0x6D87: lea ecx, [esp+0x15]         ; error buffer
0x6D8B: push ebx                    ; 0
0x6D8C: push ecx
0x6D8D: mov [esp+0x1C], bl
0x6D91: call 0x1002F638             ; memset error buffer

; === KEY CALL: Create QoS handle ===
0x6D96: push 0x1F90                 ; size = 8080 bytes
0x6D9B: push esi                    ; this pointer
0x6D9C: lea eax, [esp+0x24]         ; error buffer
0x6DA0: call 0x1002ACC0             ; *** tqos_create() ***
0x6DA5: add esp, 0x14

; === BRANCH: test result ===
0x6DA8: test eax, eax               ; eax = tqos_create return
0x6DAA: jge 0x6DB9                  ; eax >= 0: SUCCESS path
                                      ; eax < 0: FAILURE path

; === FAILURE PATH (AL=0) ===
0x6DAC: push edi
0x6DAD: mov [esi], ebx              ; this->initialized = 0
0x6DAF: call [0x1003302C]           ; LeaveCriticalSection
0x6DB5: xor al, al                  ; *** RETURN 0 ***
0x6DB7: jmp 0x6E17                  ; goto return

; === SUCCESS PATH (AL=1) ===
0x6DB9: push 0x4EA8                 ; allocate 20136 bytes
0x6DBE: call 0x1002BE34             ; malloc
0x6DC3: push 0x4EA8
0x6DC8: push ebx
0x6DC9: push eax
0x6DCA: mov [esi+4], eax            ; this->qos_data = allocated
0x6DCD: call 0x1002F638             ; memset to 0
0x6DD2: mov edx, [esi+4]
0x6DD5: mov [edx], 0x64             ; qos_data->field_0 = 100
... (initialize QoS data structure fields)
0x6E0E: push edi                    ; (also the "already init" path)
0x6E0F: call [0x1003302C]           ; LeaveCriticalSection
0x6E15: mov al, 1                   ; *** RETURN 1 ***

; === Function return ===
0x6E17: mov ecx, [esp+0x414]        ; SEH cleanup
0x6E1E: mov fs:[0], ecx
0x6E25: pop ecx
0x6E26: pop edi
0x6E27: pop ebx
0x6E28: mov ecx, [esp+0x404]        ; stack cookie check
0x6E2F: xor ecx, esp
0x6E31: call 0x1002BEF1             ; __security_check_cookie
0x6E36: add esp, 0x414
0x6E3C: ret 4                       ; return (stdcall, 4 byte arg)
```

## Q1-Q8 Answers

```text
Q1 QOS_FUNCTION_START = iips.dll + 0x6D20

Q2 QOS_FUNCTION_END = iips.dll + 0x6E3C (ret 4)

Q3 QOS_CALL_TARGETS:
  0x1002F638  (memset helper)
  0x1002ACC0  (tqos_create - KEY dependency)
  0x1002BE34  (malloc)
  0x1002BEF1  (__security_check_cookie)

Q4 QOS_IMPORTS:
  [0x10033028] = KERNEL32.dll::EnterCriticalSection
  [0x1003302C] = KERNEL32.dll::LeaveCriticalSection

Q5 QOS_GLOBAL_READS:
  [0x10042020] = stack cookie value
  [esi+0] = this->initialized (internal object state)
  [esp+0x424] = caller-provided byte parameter

Q6 QOS_GLOBAL_WRITES:
  [esi+0] = this->initialized = 0 (on failure) or 1 (on success)
  [esi+4] = this->qos_data (allocated pointer)
  [esi+8] = this->byte_param (from caller)

Q7 QOS_RETURN_VALUE_SOURCE:
  AL is determined by the return value of 0x1002ACC0 (tqos_create):
    tqos_create() >= 0 → AL = 1 (success)
    tqos_create() < 0  → AL = 0 (failure)

Q8 QOS_RETURN_ZERO_BRANCH:
  0x6DA8: test eax, eax
  0x6DAA: jge 0x6DB9      ; if eax >= 0: success
                           ; if eax < 0: fall through to failure
  0x6DB5: xor al, al       ; AL = 0
```

## Dependency Chain: 0x1002ACC0 (tqos_create)

This is the function that determines whether QoS helper returns 0 or 1.

```text
0x2ACC0 (tqos_create):
  ├─ calloc(1, 0x13C)                      ; allocate QoS context
  │    if NULL → "calloc err" → return -1
  │
  ├─ _time64(0)                            ; get current time
  ├─ srand(time)                           ; seed random number generator
  ├─ rand()                                ; generate instance ID
  │
  ├─ call 0x1002CF90                       ; internal setup
  │
  ├─ call 0x1002A240                       ; tqos_create_protohandle
  │    ├─ Registers protocol handlers:
  │    │    "QOSCSPkg", "QOSCSPkgHead", "QOSCSPkgBody"
  │    │    "QOSSSPkg", "QOSSSPkgHead", "QOSSSPkgBody"
  │    ├─ if any registration fails → return -1
  │    └─ if success → returns handle
  │    if <0 → "tqos_create_protohandle err" → return -1
  │
  ├─ call 0x1002C770                       ; register callback/lock
  │
  ├─ call 0x1002A7A0                       ; tqos_get_qosconnd_iplist
  │    ├─ Builds URI: "udp://%s:%d" using hostname and port
  │    ├─ Parses URI to find protocol type (tcp/udp/etc.)
  │    ├─ Calls WSOCK32!select() to test connection
  │    ├─ if select() fails → "tqos_get_qosconnd_iplist fail" → return -1
  │    └─ if success → returns connection list
  │    if <0 → "tqos_get_qosconnd_iplist fail" → return -1
  │
  ├─ call 0x1002A9B0                       ; tqos_find_connd_by_ip
  │    if <0 → "tqos_find_connd_by_ip fail" → return -1
  │
  ├─ call 0x1002ABF0                       ; additional setup
  └─ call 0x1002AC80                       ; final check
       if <0 → "tqos_find_connd_by_ip fail" → return -1

  Return value:
    >= 0: success (context created, connections established)
    < 0: failure (any of the above steps failed)
```

## Key Error Strings (decoded from binary)

```text
RVA 0x3B094: "calloc err"
RVA 0x3B0A0: "tqos_create_protohandle err"
RVA 0x3B0BC: "tqos_get_qosconnd_iplist fail"
RVA 0x3B0DC: "tqos_find_connd_by_ip fail"
RVA 0x3B028: "QOSCSPkg"       (Tencent QoS protocol package)
RVA 0x3B034: "QOSCSPkgHead"
RVA 0x3B044: "QOSCSPkgBody"
RVA 0x3B054: "QOSSSPkg"
RVA 0x3B060: "QOSSSPkgHead"
RVA 0x3B070: "QOSSSPkgBody"
RVA 0x3B080: "udp://%s:%d"    (QoS connection URI format)
```

## QoS Protocol Registration Table

The QoS system supports 7 connection types (static table at 0x42030):

```text
Index  Protocol  String RVA  Entries
0      tcp       0x3356C     "tcp"
1      udp       0x33568     "udp"
2      unix      0x33560     "unix"
3      pipe      0x33558     "pipe"
4      file      0x33550     "file"
5      shm       0x3354C     "shm"
6      thttp     0x33544     "thttp"
```

The `tqos_get_qosconnd_iplist` function builds a URI (e.g.,
`udp://hostname:port`), parses the protocol prefix, looks it up in
this table, and attempts a connection using WSOCK32!select().

## Return Value Attribution

```text
QoS helper (+0x6D20) returns AL=0 because:

  tqos_create (0x1002ACC0) returns a NEGATIVE value.
  
  The most likely failing sub-step is:
    tqos_get_qosconnd_iplist (0x1002A7A0)
    which calls WSOCK32!select() to test a UDP connection
    to a Tencent QoS server
    
  This function returns < 0 when:
    1. The hostname cannot be resolved (DNS failure)
    2. The UDP connection test times out
    3. The QoS server is unreachable
    4. WSAStartup was not called or socket subsystem unavailable
    
  Any of these network conditions cause the entire tqos_create
  to return < 0, which causes the QoS helper to return AL=0.
```

## Dependency Classification

```text
DEPENDENCY_TYPE = F (Network/QoS status)
                  OR G (Tencent platform component return value)

DEPENDENCY_TARGET = Tencent QoS server (UDP connection test)
                    via WSOCK32!select() and UDP socket operations

The QoS helper is a **Tencent QoS (Quality of Service) client** that:
1. Creates a QoS protocol handler (QOSCSPkg/QOSSSPkg)
2. Builds a UDP connection to a Tencent QoS server
3. Tests the connection with select()
4. If the server is unreachable, returns failure

This means the IIPS initialization gate fails because the
**Tencent QoS server is unreachable** from the current environment.
```
