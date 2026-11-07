# 0xBA41A1 has 15 CC bytes.  A trampoline that fits in 15 bytes:
#   at 0xBA3A9D (6 bytes):  jmp 0xBA41A1   (5B) + 1B nop
#   at 0xBA41A1 (15 bytes):
#       88 97 D4 06 00 00     mov [edi+0x6D4], dl     6
#       8A 95 76 FC FF FF     mov dl,[ebp-0x38a]      6   (the original insn)
#       EB 05                 jmp short +5            2   -> lands at 0xBA3AA3
#   total 14 <= 15  ✓
print("trampoline plan (fits 15 bytes):")
print()
print("  patch A  @0xBA3A9D (6 bytes) :  E9 <rel32 to 0xBA41A1>  90")
print("  patch B  @0xBA41A1 (14 bytes):")
print("      88 97 D4 06 00 00   mov [edi+0x6D4], dl")
print("      8A 95 76 FC FF FF   mov dl,[ebp-0x38a]")
print("      EB 05               jmp short $+7  ->  0xBA41AF+... ")
print()
# compute the short jump target precisely
# code at 0xBA41A1: 6 + 6 = ends at 0xBA41AD; EB xx is 2 bytes -> next = 0xBA41AF
# we want to land at 0xBA3AA3.  EB rel8 only reaches +-127 -> impossible.
print("  !! EB rel8 cannot reach 0xBA3AA3 (distance ~600 bytes)")
print("  => need E9 rel32 inside the trampoline, which adds 5 bytes -> 17 > 15")
