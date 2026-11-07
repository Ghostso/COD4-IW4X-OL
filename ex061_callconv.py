# EX-061: resolve the true calling convention of initIfsLib and the exact
# meaning of its [esp+0xA0] `this` load.
import json

import capstone as cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG
from capstone.x86_const import X86_REG_EBP, X86_REG_ECX, X86_REG_ESP

from ex060_iips_cfg import Image, DLL
from ex060_cfg_engine import Function


def main():
    img = Image(DLL)
    fi = Function(img, 0x9570, "initIfsLib").run().build_bbs()

    print("=" * 78)
    print("frame math for initIfsLib (0x9570)")
    print("=" * 78)
    print("""  entry          : ret_addr at [esp]
  0x9570 push -1 : [esp-4] = -1
  0x9572 push hdl: [esp-8] = handler
  0x9577 mov eax,fs:[0] ; push eax   -> [esp-12]
  0x957E sub esp,0x7c                -> [esp-0x88]
  0x9581 mov eax,cookie ; xor eax,esp ; mov [esp+0x78],eax
  0x958C push ebx  -> esp -= 4
  0x958D push ebp  -> esp -= 4
  0x958E push esi  -> esp -= 4
  0x958F push edi  -> esp -= 4
  0x9590 mov eax,cookie ; xor eax,esp ; push eax -> esp -= 4
  0x9598 lea eax,[esp+0x90] ; mov fs:[0],eax
  0x95A5 mov ebp,[esp+0xA0]

  offset from entry [esp] to the instruction's [esp]:
    12 (3 pushes) + 0x7C (sub) + 4*4 (4 pushes) + 4 (seh push)
      = 0x0C + 0x7C + 0x10 + 0x04 = 0x9C

  so [esp+0xA0] = [entry_esp + 0xA0 - 0x9C] = [entry_esp + 0x04]
                                                ^^^^^^^^^^^^^^
  =>  [esp+0xA0] is the FIRST STACK ARGUMENT of the caller.
""")

    print("=" * 78)
    print("the caller pushes exactly one dword before the call")
    print("=" * 78)
    print("""  0x99D1  push ebp     ; arg1 = CNIFS this  (the same `this` of
                       ;   InitInGameApp, loaded at 0x989B mov ebp,ecx)
  0x99D2  call 0x10009570
  0x99DB  (failure path)  <-- cleanup
  0x99D7  test al,al ; jne 0x9A2B

  initIfsLib reads NO register parameter other than the stack arg.
  -> it is __cdecl-like with a single pointer arg, OR a __thiscall whose
     ECX the compiler happens to also load from the stack.
  Either way:  arg1 (EDI/EBP at 0x95A5) == the CNIFS object.
""")

    print("=" * 78)
    print("confirm: does initIfsLib use ECX at all before clobbering it?")
    print("=" * 78)
    for rva in sorted(fi.insns):
        insn = fi.insns[rva]
        if insn.mnemonic == "call" and insn.operands:
            continue
        # find any read of ecx
        if "ecx" in insn.op_str and insn.mnemonic in (
                "mov", "lea", "cmp", "test", "push", "add", "sub"):
            if insn.operands and insn.operands[0].type == X86_OP_REG \
                    and insn.operands[0].reg == X86_REG_ECX \
                    and len(insn.operands) > 1 \
                    and insn.operands[1].type == X86_OP_REG \
                    and insn.operands[1].reg == X86_REG_ECX:
                continue  # ecx = ecx (nop)
            # only report if ECX is READ as a source or used as base/index
            used_as_src = any(
                (o.type == X86_OP_REG and o.reg == X86_REG_ECX) or
                (o.type == X86_OP_MEM and (o.mem.base == X86_REG_ECX
                                           or o.mem.index == X86_REG_ECX))
                for o in insn.operands[1:])
            if used_as_src:
                print("  0x%05X  %-24s %s %s" % (
                    rva, insn.bytes.hex(), insn.mnemonic, insn.op_str))


if __name__ == "__main__":
    main()
