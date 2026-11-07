import struct
# 0xC781C0 body: esi = arg7 (ctx). key copy writes [esi+8 .. esi+8+len)
# caller A (0xC73B5D): ecx = edi+0xC  -> ctx = provider+0xC -> key at provider+0x14
# caller B (0xC74C33): esi = edi+8    -> ctx = provider+8   -> key at provider+0x10
print("caller A ctx = provider+0x0C -> key copy at provider+0x14 (len 16)")
print("caller B ctx = provider+0x08 -> key copy at provider+0x10 (len 24)")
print()
print("=> 0xC78212 patch (xor dl,dl) affects BOTH paths, since both")
print("   funnel through 0xC781C0's copy loop at 0xC78212.")
print("   So provider+0x14 should have become zero...")
print()
print("Unless the observed +0x14 value is written by something else entirely:")
print("  e.g. a memcpy of a whole struct, or the provider object being")
print("  reallocated and filled elsewhere.")
