# EX-061 TASK 6/F: build the full [this+0x60] dataflow chain and the
# +0x95D0 decision tree with per-edge evidence levels.
import json
from collections import OrderedDict

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBX, X86_REG_EAX

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import grow


def main():
    img = Image(DLL)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True
    imp = build_imports(img)

    print("=" * 78)
    print("FULL CHAIN: constructor -> +0x60 -> +0x95D0 -> initIfsLib")
    print("            -> CreateIFSLibDll -> +0x60 -> later state -> dtor")
    print("=" * 78)
    print("""
[1] FACTORY / CONSTRUCTOR                              EVIDENCE: STATIC-DIRECT
    sub_197F0 (0x197F0)   tiny init wrapper, callee-cleaned ret 4
        no static callers -> reached via vtable/export boundary
        |
        v
    sub_12760 (0x12760)   CNIFS factory, 819 insns
        0x12CD3  push 0x1F0              ; sizeof(CNIFS) = 496
        0x12CD8  call operator new       ; sub_2BE34
        0x12CEE  je 0x12CFA              ; alloc fail -> edi = 0
        0x12CF0  push eax                ; arg1 = raw memory
        0x12CF1  call 0x100090D0         ; ==> CNIFS::ctor
        0x12CF6  mov edi, eax            ; CNIFS*
        0x12D06  mov [esi+0x19C], edi    ; parent keeps CNIFS*
        |
        v
    sub_90D0 (0x90D0)     CNIFS::ctor   ret 4 (one stack arg)
        0x90F4  mov ebp, [esp+0x24]      ; arg1 = this
        0x90FF  xor ebx, ebx             ; ebx = 0
        ...
        0x91CF  mov [ebp+0x60], ebx      ; *** [this+0x60] = 0 ***
        0x91D2  mov [ebp+0x58], ebx      ; CreateIFSLibDll slot = 0
        0x91D5  mov [ebp+0x5C], ebx      ; DestoryIFSLibDll slot = 0
        0x91D8  mov [ebp+0x54], ebx      ; HMODULE = 0
        0x91DB  mov [ebp+0xCC], ebx      ; status = 0
        0x91F9  mov [ebp+0x100], ebx
        0x91FF  mov eax, ebp             ; return this
        0x9214  ret 4

[2] FIRST ENTRY INTO InitInGameApp                        EVIDENCE: STATIC-UNKNOWN
    CNIFS::InitInGameApp (0x9860) has ZERO immediate callers in iips.dll.
    It is reached through a vtable/export boundary (the 0x100353xx /
    0x100354xx vtables installed by the constructor).
        |
        v
    ecx = CNIFS*      (__thiscall)
    0x989B  mov ebp, ecx             ; this
    0x98AC  lea ebx, [ebp+0x120]     ; critical section
    0x98B7  call EnterCriticalSection

[3] THE DECISION AT +0x95D0                            EVIDENCE: STATIC-REACHABLE
    0x98CD  call sub_6D20            ; QoS helper (not a gate)
    0x98E6  cmp [esp+0x118],0 / je 0x995B
    0x995B  cmp [esp+0x11C],0x10 / jae 0x9977
    0x9977  test eax,eax / je 0x99BA
    0x99BA  ... build std::string arg ...
    0x99D1  push ebp                 ; arg1 = CNIFS this
    0x99D2  call 0x10009570          ; ==> CNIFS::initIfsLib
        |
        v
    CNIFS::initIfsLib (0x9570)   __cdecl-like, ONE stack arg (ret 0x20)
        0x95A5  mov ebp, [esp+0xA0]      ; arg1 == CNIFS this
        0x95B2  mov [esp+0x98], 0
        0x95BD  push ebx / call EnterCriticalSection
        0x95D0  cmp dword ptr [ebp+0x60], 0
        0x95D4  jne 0x10009818           ; *** THE DECISION ***

[4] THE TWO OUTCOMES OF +0x95D0

    (A) [this+0x60] != 0  ->  TAKE the jne
        0x9818  push ebx
        0x9819  call LeaveCriticalSection
        0x9837  mov al, 1
        0x9839  ... ret 0x20
        => initIfsLib returns TRUE without loading ifs2.dll.
        => CreateIFSLibDll and DestoryIFSLibDll are NOT re-resolved.

    (B) [this+0x60] == 0  ->  FALL THROUGH
        0x95DA  cmp [esp+0xB8], 0
        0x95E2  je 0x9649                ; skips only the path seed
        0x96A1  ... build <iipsdir> + L"/ifs2.dll"
        0x96E8  push eax
        0x96E9  call [0x10033010]        ; KERNEL32!LoadLibraryW
        0x96EF  test eax,eax
        0x96F1  mov [ebp+0x54], eax      ; HMODULE
        0x96F4  jne 0x9770               ; NULL -> error path E1
        0x9770  mov esi, [0x10033014]    ; GetProcAddress
        0x977C  call esi                 ; "CreateIFSLibDll"
        0x9780  mov [ebp+0x58], eax
        0x9783  jne 0x97A1               ; NULL -> error path E2
        0x97A1  lea ecx, [ebp+0x50]
        0x97A4  push ecx
        0x97A5  call eax                 ; *** CreateIFSLibDll(out [this+0x50]) ***
        0x97A9  mov [ebp+0x60], eax      ; *** [this+0x60] = RESULT ***
        0x97AC  jne 0x97C3               ; 0 -> error path E3
        0x97CC  call esi                 ; "DestoryIFSLibDll"
        0x97D0  mov [ebp+0x5C], eax
        0x97D3  jne 0x97F4               ; NULL -> error path E4
        0x97F4  ... cleanup ...
        0x9818  push ebx / call LeaveCriticalSection
        0x9837  mov al, 1
        0x9839  ret 0x20
        => initIfsLib returns TRUE with [this+0x60] = CreateIFSLibDll result.

[5] CONSUMERS OF [this+0x60] IN InitInGameApp            EVIDENCE: STATIC-DIRECT
    Reached only when 0x99D9 jne 0x9A2B (initIfsLib returned TRUE), i.e.
    only on outcome (B).

    0x9A2B  mov ecx, [ebp+0x60]      ; the interface pointer
    0x9A2E  mov eax, [ecx]           ; vtable
    0x9A30  mov edx, [eax+0x2C]      ; slot +0x2C
    0x9A33  push 1
    0x9A35  call edx                 ; vtable(1)
            ... HostApp.ini read ...
    0x9B51  mov ecx, [ebp+0x60] ; slot+0x2C ; push 5 ; call
    0x9B66  mov ecx, [ebp+0x60] ; slot+0x2C ; push 3 ; call
    0x9B7B  mov ebp, [ebp+0x60] ; slot+0x2C ; push 4 ; call
            (0x9B7B OVERWRITES ebp with the interface pointer)

[6] LATER STATE / DESTRUCTION                          EVIDENCE: STATIC-DIRECT
    sub_9240 (0x9240)  CNIFS::dtor  __thiscall (mov esi,ecx)
        0x9299  xor ebx, ebx
        0x929F  mov ecx, [esi+0x60]
        0x92A2  cmp ecx, ebx / je 0x92C0
        0x92A6  cmp byte [esi+0x13C], bl
        0x92AC  mov edx, [ecx]           ; vtable
        0x92B2  sete bl
        0x92B5  push ebx
        0x92B6  push eax                 ; [esi+0x138]
        0x92B7  mov eax, [edx+8]
        0x92BA  call eax                 ; vtable slot +8
        0x92C6  cmp [esi+0x60], ebx / je 0x92DA
        0x92C9  lea edi, [esi+0x60]
        0x92CE  mov eax, [esi+0x5C]      ; DestoryIFSLibDll
        0x92D1  cmp eax, ebx / je 0x92D8
        0x92D5  push edi                 ; &[this+0x60]
        0x92D6  call eax                 ; *** DestoryIFSLibDll(&[this+0x60]) ***
        0x92D8  mov [edi], ebx           ; [this+0x60] = 0
        0x92DA  mov eax, [esi+0x54]
        0x92E1  push eax
        0x92E2  call [0x10033018]        ; KERNEL32!FreeLibrary
        0x92E8  mov [esi+0x54], ebx      ; HMODULE = 0
""")

    print("=" * 78)
    print("G. IIPS state machine that the static evidence CAN explain")
    print("=" * 78)
    print("""
    State 0  UNCONSTRUCTED
                no object; no field.

    State 1  CONSTRUCTED, NOT INITIALISED
                [this+0x50] = 0   (out slot)
                [this+0x54] = 0   (HMODULE)
                [this+0x58] = 0   (CreateIFSLibDll)
                [this+0x5C] = 0   (DestoryIFSLibDll)
                [this+0x60] = 0   (create result / interface ptr)
                [this+0xCC] = 0   (status)
              produced by sub_90D0 @ 0x91CF

    State 2  IFS INITIALISED
                [this+0x50] = <ifs object handle>
                [this+0x54] = HMODULE(ifs2.dll)
                [this+0x58] = CreateIFSLibDll
                [this+0x5C] = DestoryIFSLibDll
                [this+0x60] = <CreateIFSLibDll return, non-NULL>
                [this+0xCC] = 0
              produced by sub_9570 success path (0x97F4 -> 0x9837)

    State 3  IFS INIT FAILED (four sub-states by [this+0xCC])
                [this+0xCC] = 1   LoadLibraryW NULL            (0x971C)
                [this+0xCC] = 2   GetProcAddress Create NULL   (0x9795)
                [this+0xCC] = 1   CreateIFSLibDll == 0         (0x971C via 0x97BE)
                [this+0xCC] = 3   GetProcAddress Destory NULL  (0x97E5)
              [this+0x60] state on failure:
                - E1 (+0x96F6): not written -> stays 0
                - E2 (+0x9785): not written -> stays 0
                - E3 (+0x97AE): WRITTEN to 0 at 0x97A9 (result was 0)
                - E4 (+0x97D5): already non-NULL from 0x97A9
              returns AL = 0

    State 4  TEARDOWN
                DestoryIFSLibDll(&[this+0x60]); [this+0x60] = 0
                FreeLibrary([this+0x54]); [this+0x54] = 0
              produced by sub_9240
""")


if __name__ == "__main__":
    main()
