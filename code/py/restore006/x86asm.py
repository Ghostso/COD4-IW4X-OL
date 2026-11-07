"""A tiny x86-32 machine-code emitter.

We have no C compiler and no assembler (Agent 16), so the RM provider's code is
emitted directly.  The emitter is deliberately explicit: every byte sequence is
written as it will appear, and each helper's docstring states the encoding it
produces so the output can be hand-verified.

All emitted functions use the __cdecl convention unless noted, matching the real
GetResourceManagerII / ReleaseResourceManagerII (Agent 01/02/22).
"""
import struct


def imm32(v):
    return struct.pack("<I", v & 0xFFFFFFFF)


def rel32(frm, to):
    return struct.pack("<i", to - (frm + 5))


class Asm:
    def __init__(self, base_va=0):
        self.b = bytearray()
        self.base = base_va

    # ---- address bookkeeping -------------------------------------------
    @property
    def here(self):
        """VA of the next byte to be emitted."""
        return self.base + len(self.b)

    def label(self):
        return self.here

    # ---- raw ------------------------------------------------------------
    def db(self, *bs):
        for x in bs:
            self.b.append(x & 0xFF)
        return self

    def raw(self, data):
        self.b.extend(data)
        return self

    # ---- common instructions -------------------------------------------
    def ret(self):
        """C3 - plain return (caller cleans -> cdecl)."""
        return self.db(0xC3)

    def ret_n(self, n):
        """C2 iw - return and pop n bytes (callee cleans -> stdcall /
        thiscall-with-stack-args)."""
        return self.db(0xC2).raw(struct.pack("<H", n))

    def xor_eax_eax(self):
        """33 C0 - xor eax, eax."""
        return self.db(0x33, 0xC0)

    def mov_eax_imm32(self, v):
        """B8 id - mov eax, imm32."""
        return self.db(0xB8).raw(imm32(v))

    def mov_ecx_ptr_esp(self, disp):
        """8B 4C 24 dd - mov ecx, [esp+disp]."""
        return self.db(0x8B, 0x4C, 0x24, disp & 0xFF)

    def mov_ptr_ecx_imm32(self, v):
        """C7 01 id - mov dword ptr [ecx], imm32."""
        return self.db(0xC7, 0x01).raw(imm32(v))

    def mov_eax_ptr_ecx(self):
        """8B 01 - mov eax, [ecx]."""
        return self.db(0x8B, 0x01)

    def mov_ptr_ecx_eax(self):
        """89 01 - mov [ecx], eax."""
        return self.db(0x89, 0x01)

    def mov_eax_ptr_ecx_disp(self, disp):
        """8B 41 dd - mov eax, [ecx+disp8]."""
        return self.db(0x8B, 0x41, disp & 0xFF)

    def mov_ptr_ecx_disp_imm32(self, disp, v):
        """C7 41 dd id - mov dword ptr [ecx+disp8], imm32."""
        return self.db(0xC7, 0x41, disp & 0xFF).raw(imm32(v))

    def mov_ptr_ecx_disp_eax(self, disp):
        """89 41 dd - mov [ecx+disp8], eax."""
        return self.db(0x89, 0x41, disp & 0xFF)

    def test_ecx_ecx(self):
        """85 C9 - test ecx, ecx."""
        return self.db(0x85, 0xC9)

    def test_byte_ptr_ecx_imm8(self, v):
        """F6 01 ib - test byte ptr [ecx], imm8."""
        return self.db(0xF6, 0x01, v & 0xFF)

    def test_byte_ptr_esp_disp_imm8(self, disp, v):
        """F6 44 24 dd ib - test byte ptr [esp+disp], imm8."""
        return self.db(0xF6, 0x44, 0x24, disp & 0xFF, v & 0xFF)

    def push_imm32(self, v):
        """68 id - push imm32."""
        return self.db(0x68).raw(imm32(v))

    def push_ecx(self):
        """51 - push ecx."""
        return self.db(0x51)

    def pop_ecx(self):
        """59 - pop ecx."""
        return self.db(0x59)

    def inc_ptr_ecx(self):
        """FF 01 - inc dword ptr [ecx]."""
        return self.db(0xFF, 0x01)

    def jmp_short(self, target_va):
        """EB rel8 (fallback to E9 rel32 when out of range)."""
        delta = target_va - (self.here + 2)
        if -128 <= delta <= 127:
            return self.db(0xEB, delta & 0xFF)
        self.db(0xE9).raw(rel32(self.here, target_va))
        return self

    def je_short(self, target_va):
        """74 rel8 / 0F 84 rel32."""
        delta = target_va - (self.here + 2)
        if -128 <= delta <= 127:
            return self.db(0x74, delta & 0xFF)
        self.db(0x0F, 0x84).raw(rel32(self.here, target_va))
        return self

    def jne_short(self, target_va):
        """75 rel8 / 0F 85 rel32."""
        delta = target_va - (self.here + 2)
        if -128 <= delta <= 127:
            return self.db(0x75, delta & 0xFF)
        self.db(0x0F, 0x85).raw(rel32(self.here, target_va))
        return self

    def call_abs(self, addr_imm32):
        """FF 15 id - call dword ptr [imm32].
        Used to call an imported function through the IAT slot at addr_imm32.
        """
        return self.db(0xFF, 0x15).raw(imm32(addr_imm32))

    def call_rel32_to(self, target_va):
        """E8 cd - call target_va (same-image relative call).

        rel32 is relative to the address of the NEXT instruction, i.e.
        (address of the E8 byte) + 5.  `self.here` is the address of the E8
        byte itself, so the base must be here+5.
        """
        here = self.here
        self.db(0xE8).raw(struct.pack("<i", target_va - (here + 5)))
        return self

    def jmp_abs(self, addr_imm32):
        """FF 25 id - jmp dword ptr [imm32] (IAT thunk form)."""
        return self.db(0xFF, 0x25).raw(imm32(addr_imm32))

    def align(self, n, fill=0xCC):
        while len(self.b) % n:
            self.b.append(fill)
        return self

    def size(self):
        return len(self.b)

    def bytes(self):
        return bytes(self.b)
