# EX-063 TASK F/K/Q5/Q6: assemble the final chain and state the boundary.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

from ex060_iips_cfg import Image, DLL, build_imports
from ex061_revalidate import find_entries, grow


def main():
    img = Image(DLL)
    base = img.base
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_32)
    md.detail = True

    print("=" * 78)
    print("FINAL CHAIN (inside iips.dll)")
    print("=" * 78)
    print("""
  [EXTERNAL CALLER]
        |  calls the EXPORTED entry
        v
  GetResourceManagerII   iips.dll export @ 0x1C80
        |  0x1CA1  test byte [0x1004EB6C], 1     ; idempotency flag
        |  0x1CAA  or   dword [0x1004EB6C], 1
        |  0x1CB1  push 0x410                    ; sizeof(MANAGER) = 1040
        |  0x1CBE  call operator new (sub_2BE34)
        |  0x1CD4  call sub_11F20                ; MANAGER CTOR
        |  0x1CD9  mov [0x1004EB68], eax         ; PUBLICATION (global)
        v
  sub_11F20  MANAGER CTOR  (this = [esp+0x??], ret 4)
        |  0x11F66  [this+0x00] = 0x1003929C     ; base vt (superseded)
        |  0x11F7A  [this+0x04] = 0x1003926C
        |  0x11F93  [this+0x20] = 0x100344E4
        |  0x11FAA  [this+0x44] = 0x10039290
        |  0x11FB1  [this+0x00] = 0x1003934C     ; *** FINAL primary vt ***
        |  0x11FB8  [this+0x04] = 0x1003940C
        |  0x11FBF  [this+0x20] = 0x10039430
        |  0x11FC6  [this+0x44] = 0x10039438
        |  0x122AC  [this+0x19C] = 0            ; init to NULL
        v
  [MANAGER OBJECT, vtable 0x1003934C, sizeof 0x410]
        |
        |  later, a manager method runs (slot 5 = sub_1A270):
        |  0x1A285  mov esi, ecx                ; this = MANAGER
        |  0x1A29C  cmp [esi+0x19C], 0
        |  0x1A2FC  mov ecx, [esi+0x19C]        ; a MANAGER stored at +0x19C
        |  0x1A302  mov eax, [ecx]
        |  0x1A304  mov edx, [eax+4]            ; slot 1
        |  0x1A309  call edx                    ; ==> sub_197F0
        v
  sub_197F0   (MANAGER vtable 0x1003934C slot 1)
        |  0x197F0  mov edx, [esp+4]
        |  0x197F5  mov esi, ecx                ; this = the nested MANAGER
        |  0x197F7  call sub_12760              ; *** THE FACTORY ***
        |  0x197FC  test al, al
        |  0x197FE  jne 0x1980D                 ; success
        |  0x19800  mov ecx, esi
        |  0x19802  call sub_19820              ; cleanup on failure
        |  0x19807  xor al, al
        |  0x1980A  ret 4
        v
  sub_12760   THE FACTORY  (this = the nested MANAGER)
        |  0x12CD3  push 0x1F0
        |  0x12CD8  call operator new           ; sizeof(CNIFS) = 496
        |  0x12CF1  call sub_90D0               ; CNIFS ctor
        |  0x12D06  mov [esi+0x19C], edi        ; publish CNIFS* into +0x19C
        |  0x12F40  mov ecx, [ebx+0x19C]        ; read it back
        |  0x12F48  mov edx, [eax+0x50]         ; CNIFS slot 20
        |  0x12F56  call edx                    ; ==> InitInGameApp
        v
  CNIFS::InitInGameApp  0x9860
        |  0x99D2  call initIfsLib
        v
  CNIFS::initIfsLib  0x9570
        |  0x95D0  cmp [this+0x60], 0
        v
  LoadLibraryW(<iipsdir> + L"/ifs2.dll")  @ 0x96E9
""")

    print("=" * 78)
    print("verification: the +0x410 allocation equals the manager sizeof")
    print("=" * 78)
    b1 = grow(img, 0x11F20, md)
    mx = max(o.mem.disp for i in b1.values() for o in i.operands
             if o.type == X86_OP_MEM and o.mem.base
             and md.reg_name(o.mem.base) == "ebp")
    b2 = grow(img, 0x124D0, md)
    mx2 = max(o.mem.disp for i in b2.values() for o in i.operands
              if o.type == X86_OP_MEM and o.mem.base
              and md.reg_name(o.mem.base) == "edi")
    print("   GetResourceManagerII allocates 0x410")
    print("   sub_11F20 max field offset : +0x%X" % mx)
    print("   sub_124D0 max field offset : +0x%X" % mx2)
    print("   0x410 > all of them        : %s" % (0x410 > max(mx, mx2)))
    print("   GetResourceManager   allocates 0x480 (a LARGER sibling class)")

    print()
    print("=" * 78)
    print("TWO DISTINCT USES OF THE +0x19C OFFSET")
    print("=" * 78)
    print("""
  (A) sub_12760's parent  (`esi` at 0x12D06)
         [parent+0x19C] := CNIFS*           <- written by 0x12D06
         then read at 0x12F40 and dispatched at CNIFS slot +0x50

  (B) sub_1A270's `this`  (a MANAGER, `esi` at 0x1A2FC)
         [manager+0x19C] := ?               <- NOT written in sub_1A270
         read at 0x1A2FC and dispatched at MANAGER slot +0x04 = sub_197F0

  Both are "the +0x19C field of a manager-family object".
  In (A) it holds a CNIFS*; in (B) it holds another MANAGER*.
""")


if __name__ == "__main__":
    main()
